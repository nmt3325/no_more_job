"""3つのMCPサーバーを単一プロセス・単一ポートで公開するゲートウェイ。

baitoru / mynavi / townwork の各 server.py は変更せず、それぞれの FastMCP
インスタンス(`mcp`)を読み込んで Starlette の Mount でパス分割する。

  POST /baitoru/mcp   → baitoru-mcp
  POST /mynavi/mcp    → mynavi-mcp
  POST /townwork/mcp  → townwork-mcp

各サーバーは同名の `server.py` / `api.py` を持つため、そのままだと
`import api` が衝突する。サイトごとに sys.path を差し替え、`api`/`server`
モジュールのキャッシュを毎回クリアして独立ロードする。
"""

import contextlib
import importlib.util
import sys
from pathlib import Path

from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.responses import JSONResponse, PlainTextResponse

# mcp/ ディレクトリ（このファイルの1つ上）
BASE = Path(__file__).resolve().parent.parent

# 公開するサイトとマウントパスの対応
SITES = ["baitoru", "mynavi", "townwork"]


def _load_mcp(name: str):
    """サイトの server.py をロードし、その FastMCP インスタンスを返す。

    `import api` が各サイトの api.py を解決できるよう、ロード中だけ
    そのサイトのディレクトリを sys.path 先頭に置き、共有モジュール名
    (`api` / `server`) のキャッシュをクリアする。
    """
    site_dir = str(BASE / name)
    sys.path.insert(0, site_dir)
    sys.modules.pop("api", None)
    sys.modules.pop("server", None)
    try:
        spec = importlib.util.spec_from_file_location(
            f"{name}_server", BASE / name / "server.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.mcp
    finally:
        sys.path.remove(site_dir)
        sys.modules.pop("api", None)
        sys.modules.pop("server", None)


# 各サイトの FastMCP を Streamable HTTP アプリ化（エンドポイントは各Mount配下の /mcp）
_http_apps = {name: _load_mcp(name).http_app(path="/mcp") for name in SITES}


@contextlib.asynccontextmanager
async def _combined_lifespan(app):
    """全サイトの FastMCP セッションマネージャの lifespan をまとめて起動する。

    StreamableHTTP のセッション管理は lifespan 内で動くため、子アプリ
    それぞれの lifespan_context を確実に開始しないと 500 になる。
    """
    async with contextlib.AsyncExitStack() as stack:
        for http_app in _http_apps.values():
            await stack.enter_async_context(
                http_app.router.lifespan_context(http_app)
            )
        yield


async def _root(request):
    return JSONResponse({
        "service": "baito-mcp-gateway",
        "endpoints": {name: f"/{name}/mcp" for name in SITES},
    })


async def _health(request):
    return PlainTextResponse("ok")


from starlette.routing import Route

routes = [
    Route("/", _root),
    Route("/health", _health),
] + [Mount(f"/{name}", app=_http_apps[name]) for name in SITES]

app = Starlette(routes=routes, lifespan=_combined_lifespan)
