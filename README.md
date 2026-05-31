# no_more_job

バイトル・マイナビバイト・タウンワークをAIが自然言語で検索できる MCP サーバー。

## クイックスタート

```bash
cd mcp
docker compose up
```

Claude Desktop に登録:

```json
{
  "mcpServers": {
    "baito": { "url": "http://localhost:8000/mcp" }
  }
}
```

## 使い方

Claude に自然言語で話しかけるだけ:

```
渋谷駅周辺でカフェのバイトを探して。時給1200円以上、週2〜3日希望。

東京で深夜のコンビニバイトを探して。日払いOKで。

大阪で未経験OKのホールスタッフを探して。マイナビとタウンワーク両方で。
```

## 構成

```
mcp/          # MCPサーバー本体 → 詳細は mcp/README.md
baitoru/      # バイトル調査用CLIツール
mynavi-baito/ # マイナビバイト調査用CLIツール
townwork/     # タウンワーク調査用CLIツール
```

対応サイト: **バイトル** / **マイナビバイト** / **タウンワーク**

詳細なセットアップ・ツール一覧は [mcp/README.md](mcp/README.md) を参照。
