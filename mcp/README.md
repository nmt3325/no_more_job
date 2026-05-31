# バイト求人 MCP サーバー

バイトル・マイナビバイト・タウンワークをAIが自然言語で検索できる**統合 MCP サーバー**。

## 構成

```
mcp/
└── baito_mcp/          # 単一の FastMCP サーバー
    ├── server.py        # エントリーポイント（stdio）
    ├── web.py           # Streamable HTTP アプリ（Docker/uvicorn 用）
    ├── baitoru_api.py   /  baitoru_tools.py    # バイトル (HTML スクレイピング)
    ├── mynavi_api.py    /  mynavi_tools.py     # マイナビバイト (JSON API)
    └── townwork_api.py  /  townwork_tools.py   # タウンワーク (Playwright)
```

3サイトのツールを1つの FastMCP インスタンス (`baito`) にまとめている。
ツール名はサイト接頭辞で区別する（`baitoru_search`, `mynavi_search`, `townwork_search` …）。

利用方法は2通り:

- **ローカル (stdio)** — Claude Desktop に `server.py` を1つだけ登録する
- **Docker (Streamable HTTP)** — 単一ポートで公開する

---

## セットアップ（ローカル / stdio）

- Python 3.11 以上

```bash
cd mcp
python -m venv .venv
source .venv/bin/activate
pip install -e .
playwright install chromium   # タウンワーク (Playwright) 用
```

### Claude Desktop への登録

`~/Library/Application Support/Claude/claude_desktop_config.json` を編集:

```json
{
  "mcpServers": {
    "baito": {
      "command": "/path/to/no_more_job/mcp/.venv/bin/python",
      "args": ["-m", "baito_mcp.server"],
      "cwd": "/path/to/no_more_job/mcp"
    }
  }
}
```

設定後、Claude Desktop を再起動する。

---

## Docker（単一ポートで公開）

```bash
cd mcp
docker compose up      # ghcr.io/nmt3325/no_more_job:latest を使って起動
# ポート変更:  PORT=9000 docker compose up
```

エンドポイント:

```
http://localhost:8000/mcp      # MCP (Streamable HTTP)
http://localhost:8000/health   # ヘルスチェック
```

### Claude Desktop から HTTP で使う

```json
{
  "mcpServers": {
    "baito": { "url": "http://localhost:8000/mcp" }
  }
}
```

> ⚠️ 認証は付けていない。外部公開する場合はリバースプロキシ等で認証・レート制限を追加すること。

---

## CI（GitHub Actions）

`.github/workflows/docker-build.yml` が `mcp/**` の変更時に Docker イメージを
ビルドし、`main` への push で ghcr.io へ push する（`linux/amd64` + `linux/arm64`）。

---

## ツール一覧

すべて1つのサーバーに属する。名前のサイト接頭辞で対象サイトを指定する。

### バイトル (`baitoru_*`)

| ツール | 説明 |
|---|---|
| `baitoru_search` | キーワード・地域・給与・こだわり条件で検索 |
| `baitoru_search_with_station` | 駅名を指定して検索（駅検索と求人検索を一括実行、推奨） |
| `baitoru_search_station` | 駅名で `eki_codes` を検索 |

### マイナビバイト (`mynavi_*`)

| ツール | 説明 |
|---|---|
| `mynavi_search` | キーワード・都道府県・給与・時間帯・雇用形態・こだわり条件などで検索 |
| `mynavi_get_detail` | 求人詳細を取得 (`job_id` 指定) |
| `mynavi_search_station` | 駅名で路線/駅IDを検索 |
| `mynavi_get_filters` | こだわり条件・雇用形態などのID一覧を返す |

### タウンワーク (`townwork_*`)

| ツール | 説明 |
|---|---|
| `townwork_search` | キーワード・都道府県・給与・雇用形態・こだわりで検索 |
| `townwork_search_with_station` | 駅名を指定して検索（推奨） |
| `townwork_search_station` | 駅を検索 |
| `townwork_get_job_count` | キーワードのヒット件数を取得 |

---

## 使用例（Claude への話しかけ方）

```
渋谷駅周辺でカフェのバイトを探して。時給1200円以上、週2〜3日希望。

東京で深夜のコンビニバイトを探して。日払いOKで。

大阪で未経験OKのホールスタッフを探して。マイナビとタウンワーク両方で。
```

---

## 注意事項

- **バイトル**: 地域選択（関東/関西/東海…）が必要。都道府県単位の絞り込みは未対応。駅検索は地域ページHTML（関東で2,541駅）を初回パースしてキャッシュするため、初回呼び出しは数秒かかる。
- **タウンワーク**: 初回ツール呼び出し時にPlaywrightブラウザが起動するため数秒かかる。以降はブラウザを保持して高速に動作する。`preference`（こだわり）は検証済みの「日払い/週払い/学生歓迎」のみ対応。
- **レートリミット**: 短時間に大量のリクエストを送らないよう注意。
