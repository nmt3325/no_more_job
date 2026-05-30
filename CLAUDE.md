# バイト求人 MCP サーバー 実装計画

# 最終目標
AIがバイト求人サイト（バイトル・マイナビバイト・タウンワーク）を検索できるMCPサーバーを作る。
最優先目標: AIが自然な言語でサイトを検索できること。実装はなるべくクリーンに。

## このドキュメントについて
常に最終目標に従ってコードを書いてください。その上でこのファイルについて修正が必要である場合は方針を変更してください。
実装を進める中で判明した事実・より良い方針があれば、このファイル自体を適宜修正してよい。

---

> セットアップ手順・Claude Desktop設定・ツール一覧は [mcp/README.md](mcp/README.md) を参照。

---

## 検討・決定すべき事項リスト

### ✅ 決定済み
- MCPとして実装（CLIは参考実装として残す）
- **3サーバー分割**: `baitoru-mcp / mynavi-mcp / townwork-mcp`（タウンワークのPlaywright依存を隔離、障害の局所化、Claude Desktopに3つ登録）
- サイト間の重複排除は実装しない
- 駅検索: `search_station(名前)` → 候補選択の2ステップ固定
- 対応サイト: バイトル・マイナビバイト・タウンワーク
- フィルターは公式サイトで実装されているもののみ
- 共通キーは同じ名前で統一

---

#### 2. Playwrightの起動戦略（タウンワーク）
**現状**: 毎コマンドでPlaywrightを起動 → MCP化すると遅すぎる

**推奨**: MCPサーバー起動時に1回だけブラウザを起動し、プロセスが生きている間は保持する
```python
# server起動時
browser = playwright.chromium.launch(headless=True)
page = browser.new_page()
# 以降はこのpageを使い回す
```
注意: 長時間使用でセッション切れの可能性。再接続ロジックが必要。

#### 3. MCP フレームワーク
**推奨: `fastmcp`（Python）**
- FastAPI風のデコレータでツール定義が簡潔
- 既存コードがPythonなので親和性が高い
- 型ヒント + Pydantic でAIへのスキーマ提示が自動生成される

```python
from fastmcp import FastMCP
mcp = FastMCP("mynavi-baito")

@mcp.tool()
def search(keyword: str, prefecture_id: int = None, salary_min: int = None) -> list[Job]:
    """マイナビバイトで求人を検索する"""
    ...
```

#### 4. 既存CLIコードの扱い
- `baitoru/`, `mynavi-baito/`, `townwork/` 配下のCLIツールは**調査過程で生成した中間成果物**であり、最終成果物ではない
- 変更・削除・完全な作り直しを自由に行ってよい
- API仕様の調査結果（`API_ANALYSIS.md`, `API_REFERENCE.md`, `API_SPEC.md`）は参考資料として残すが、**内容が実態と異なる可能性**があるため鵜呑みにしない
- 実装時に不明点があればPlaywright MCPを使ってサイトの通信を再解析すること

#### 5. 給与フィルターの正規化（要設計）
各サイトで給与指定方式が異なる。AIには統一インターフェースを提供すべき。

| AI入力 | バイトル変換 | マイナビ変換 | タウンワーク変換 |
|---|---|---|---|
| `salary_min=1250, type="hourly"` | 最近似値に丸め(`1200`) | wageId変換(`"1-13"`) | smnコード変換(`103`) |

実装: 各アダプターに変換関数を持たせる。

#### 6. ページネーション設計
各サイトでページネーション方式が違う:
- バイトル: URLパスに `/pageN/`
- マイナビ: `page` パラメータ（1始まり）
- タウンワーク: `p` パラメータ（**0始まり**）。`pageInfo.nextPages[].{pageNum, cursor}` で次ページ情報を取得。
  `p` だけでもページ送りは可能。cursor はサーバー内部で `pageNum→cursor` をキャッシュし併用する。
  ※ 当初「純粋なカーソルベース」と記載していたが、実態はページ番号ベース（実装で確認・修正済み）。

**推奨**: MCPツールは `page` 番号（1始まり）で統一し、タウンワークの 0始まり変換とカーソル管理はサーバー内部で吸収する。
AIに「カーソルを渡してください」とさせるのは不自然。

#### 7. 検索結果の正規化（共通出力スキーマ）
```python
class Job(BaseModel):
    source: str        # "バイトル" | "マイナビバイト" | "タウンワーク"
    job_id: str
    title: str
    company: str
    salary: str        # 表示文字列 "時給1,200円〜"
    salary_amount: int # 数値（フィルタリング・比較用）
    salary_unit: str   # "hourly" | "daily" | "monthly"
    job_type: str      # 雇用形態
    location: str      # 勤務地テキスト
    access: str        # 最寄り駅
    description: str   # 仕事内容
    url: str
    # マイナビのみ: lat, lon, phone
    # タウンワークのみ: lat, lon
```

#### 8. バイトルの駅フィルター ✅ 実装・検証済み（Playwright解析 2026-05-30）
- サジェストAPIは存在しない（`ensn_layer_asp` は `{"type":"NG"}` を返すだけ）
- **全駅・沿線データが `/{region}/` の生HTML（JS不要）に埋め込まれている**（関東：228沿線・2,541駅、実測一致）
- 埋め込み形式（検証済み）:
  ```html
  <input name="eki[]" value="2_172_010" data-org-str="東京駅">   <!-- 駅 -->
  <input name="ensn[]" value="2_172"     data-org-str="山手線">  <!-- 沿線 -->
  ```
  → 駅名は **`data-org-str` 属性**から取得するのが確実（`mcp/baitoru/api.py` 実装済み）
- ヒットした `eki[]` コードを `createurl` の `eki[]` に渡すと駅絞り込み検索URLが生成される
  （例: `eki[]=2_172_010`+`keyword=カフェ` → `/kanto/jlist/2172tokyoeki/wrdカフェ/` で315件取得を確認）
- 注意: 地域ごとにページが分かれるため、全国対応には7地域分の取得が必要
- `search_station()` のインターフェースは他2サイトと統一できる（内部実装のみ異なる）


#### 9. サイト固有フィルターの扱い
マイナビの「こだわり条件」（90種以上）はマイナビ固有。
バイトルの「期間コード」（`83_trm_0`等）もバイトル固有。

**推奨**: 共通フィルターと固有フィルターを分けて提供
- 共通ツール引数: `keyword`, `salary_min`, `salary_type`, `job_type`, `location`
- 固有ツール引数: `filters` dict（サイト固有のフィルターをそのまま渡せる）

#### 10. AIへのツール説明文（重要）
MCPツールのdescriptionの質がAIの使いやすさに直結する。
- フィルターの有効値・型・意味を明記
- サイト固有コードはAIが自力で解決できないので列挙が必要
- 例: `job_type: "normal"(アルバイト) | "regular"(正社員) | "haken"(派遣)`

---

## 実装方針（推奨）

### ディレクトリ構成
```
no_more_job/
├── baitoru/          # 調査用CLIツール（削除・改変自由）
├── mynavi-baito/     # 調査用CLIツール（削除・改変自由）
├── townwork/         # 調査用CLIツール（削除・改変自由）
└── mcp/
    ├── baitoru/
    │   ├── server.py      # fastmcp エントリーポイント
    │   ├── api.py         # baitoru/baitoru.py から抽出
    │   ├── adapters.py    # 正規化・変換ロジック
    │   └── pyproject.toml
    ├── mynavi/
    │   ├── server.py
    │   ├── api.py         # mynavi-baito/api.py から抽出
    │   ├── adapters.py
    │   └── pyproject.toml
    └── townwork/
        ├── server.py
        ├── api.py         # townwork/townwork/api.py から抽出
        ├── adapters.py
        └── pyproject.toml
```

### 各MCPサーバーのツール一覧

#### baitoru-mcp
| ツール | 説明 |
|---|---|
| `search` | キーワード・フィルターで求人検索 |
| `get_detail` | 求人詳細取得（job_id指定） |
| `search_station` | 駅名でフィルタリング（起動時キャッシュ済みデータから検索） |
| `get_job_count` | 検索条件に合う件数取得 |

#### mynavi-mcp
| ツール | 説明 |
|---|---|
| `search` | 求人検索（最も高機能） |
| `get_detail` | 求人詳細取得 |
| `search_station` | 駅名サジェスト（`/api/suggest/list`） |
| `get_filters` | 利用可能フィルター一覧（こだわり条件含む） |

#### townwork-mcp
| ツール | 説明 |
|---|---|
| `search` | 求人検索（Playwright経由） |
| `get_detail` | 求人詳細（詳細ページが必要な場合のみ） |
| `search_station` | 駅名サジェスト（`KeywordAutoCompletePf`） |
| `get_job_count` | 件数取得 |

### 実装優先順序
1. **マイナビ MCP** — JSON APIのみ、既存コードが完成度高い
2. **バイトル MCP** — HTMLスクレイピング、複雑なURL生成
3. **タウンワーク MCP** — Playwright管理が最も複雑

---

## 未解決・確認が必要な点

- [x] バイトルの駅名サジェストAPIの有無 → **存在しない**（詳細は項目8参照）
- [x] タウンワークのPlaywrightブラウザをMCPサーバーとして起動する際のセッション管理仕様 → **グローバル変数で保持、`_get_page()`で切断時に再起動**
- [x] fastmcpのバージョン・インストール方法の確認 → **`fastmcp>=2.0`、各サーバーのpyproject.tomlに記載**
- [x] Claude Desktopへの3サーバー同時登録方法の確認 → **mcp/README.md参照**
- [x] タウンワークのget_detailは必要か → **不要。検索結果（`__NEXT_DATA__`）に仕事内容・給与・アクセスが含まれる**

> **注意**: 上記の調査済み項目も含め、既存CLIツールやAPI仕様ドキュメントの内容は調査途中のものであり不完全な可能性がある。実装時に実際の挙動と異なる点が見つかれば、Playwright MCPで通信を再解析して仕様を確認・修正すること。

---

## 見解：Notionページの方針に対するコメント

| Notionの記述 | 意見 |
|---|---|
| 「横断検索より個別サイトをAIに操作させる方が良い」 | ✅ 同意。MCPを3つ別々に実装する方針と一致 |
| 「フィルターは公式と同じものだけ」 | ✅ ただしUI階層（駅の4段階）はAI向けに平坦化を推奨 |
| 「サイトUIと同じフィルターを作っても効率的でない」 | ✅ 同意。AIには値リストより自然言語→変換の方が使いやすい |
| 「レートリミットに気をつける」 | ✅ タウンワークは特に注意。Playwrightセッションの再利用が必須 |
| 「CLIとMCPどっちがいいか→MCP」 | ✅ 既存CLIは調査用途で生成したものなので削除・改変自由 |
