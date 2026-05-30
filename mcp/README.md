# バイト求人 MCP サーバー

バイトル・マイナビバイト・タウンワークをAIが自然言語で検索できる MCP サーバー群。

## 構成

```
mcp/
├── mynavi/     # マイナビバイト (JSON API)
├── baitoru/    # バイトル (HTML スクレイピング)
└── townwork/   # タウンワーク (Playwright)
```

各サーバーは独立した仮想環境で動作する。

利用方法は2通り:

- **ローカル (stdio)** — Claude Desktop に各 `server.py` を直接登録する（後述）
- **Docker (Streamable HTTP)** — 3サーバーを単一コンテナ・単一ポートで公開する（後述）

---

## Docker（単一ポートで3サーバーを公開）

`gateway/gateway.py` が3つの FastMCP を読み込み、1プロセス・1ポートで
パス分割して Streamable HTTP として公開する。

```
http://localhost:8000/baitoru/mcp
http://localhost:8000/mynavi/mcp
http://localhost:8000/townwork/mcp
```

### 起動

```bash
cd mcp
docker compose up --build      # ビルドして起動
# ポート変更:  PORT=9000 docker compose up
```

`http://localhost:8000/` でエンドポイント一覧、`/health` でヘルスチェックを返す。

### 公開イメージを使う（GitHub Actions が ghcr.io にビルド済み）

```bash
IMAGE=ghcr.io/<owner>/<repo>:latest docker compose up
```

### Claude Desktop から HTTP で使う

```json
{
  "mcpServers": {
    "baitoru":  { "url": "http://localhost:8000/baitoru/mcp" },
    "mynavi":   { "url": "http://localhost:8000/mynavi/mcp" },
    "townwork": { "url": "http://localhost:8000/townwork/mcp" }
  }
}
```

> ⚠️ 認証は付けていない。外部公開する場合はリバースプロキシ等で認証・レート制限を追加すること。

---

## CI（GitHub Actions）

`.github/workflows/docker-build.yml` が `mcp/**` の変更時に Docker イメージを
ビルドし、`main` への push で ghcr.io へ push する（`linux/amd64` + `linux/arm64`）。
認証は `GITHUB_TOKEN` を使うため追加 secret は不要。PR ではビルド検証のみ。

---

## セットアップ（ローカル / stdio）

### 共通の前提

- Python 3.11 以上

### マイナビバイト

```bash
cd mcp/mynavi
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### バイトル

```bash
cd mcp/baitoru
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### タウンワーク

```bash
cd mcp/townwork
python -m venv .venv
source .venv/bin/activate
pip install -e .
playwright install chromium
```

---

## Claude Desktop への登録

`~/Library/Application Support/Claude/claude_desktop_config.json` を編集:

```json
{
  "mcpServers": {
    "mynavi-baito": {
      "command": "/Users/nmt3325/Documents/projects/no_more_job/mcp/mynavi/.venv/bin/python",
      "args": ["/Users/nmt3325/Documents/projects/no_more_job/mcp/mynavi/server.py"]
    },
    "baitoru": {
      "command": "/Users/nmt3325/Documents/projects/no_more_job/mcp/baitoru/.venv/bin/python",
      "args": ["/Users/nmt3325/Documents/projects/no_more_job/mcp/baitoru/server.py"]
    },
    "townwork": {
      "command": "/Users/nmt3325/Documents/projects/no_more_job/mcp/townwork/.venv/bin/python",
      "args": ["/Users/nmt3325/Documents/projects/no_more_job/mcp/townwork/server.py"]
    }
  }
}
```

設定後、Claude Desktop を再起動する。

---

## ツール一覧

### mynavi-baito

| ツール | 説明 |
|---|---|
| `search` | キーワード・都道府県・給与・時間帯・雇用形態・こだわり条件などで検索 |
| `get_detail` | 求人詳細を取得 (`job_id` 指定) |
| `search_station` | 駅名で路線/駅IDを検索し、`search()` の `route_ids` に渡す値を返す |
| `get_filters` | こだわり条件・雇用形態などのID一覧を返す |

### baitoru

| ツール | 説明 |
|---|---|
| `search` | キーワード・地域・給与・こだわり条件で検索 |
| `search_with_station` | 駅名を指定して検索（駅検索と求人検索を一括実行、推奨） |
| `search_station` | 駅名で `eki_codes` を検索し、`search()` に渡す値を返す |

### townwork

| ツール | 説明 |
|---|---|
| `search` | キーワード・都道府県・給与・雇用形態・こだわりで検索 |
| `search_with_station` | 駅名を指定して検索（推奨） |
| `search_station` | 駅IDを検索 |
| `get_job_count` | キーワードのヒット件数を取得 |

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
