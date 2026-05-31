"""Streamable HTTP エントリーポイント（Docker / uvicorn 用）。

単一サーバーになったため、エンドポイントは1つだけ:
  http://localhost:8000/mcp
"""

from starlette.responses import PlainTextResponse
from starlette.routing import Route

from .server import mcp

# FastMCP の Streamable HTTP アプリ（lifespan 込み）。
app = mcp.http_app(path="/mcp")


async def _health(request):
    return PlainTextResponse("ok")


app.router.routes.append(Route("/health", _health))
