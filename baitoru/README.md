# baitoru-cli

バイトル (baitoru.com) の求人をコマンドラインから検索するCLIツール。

Playwright MCPでサイトの通信を解析し、バックグラウンドAPIをリバースエンジニアリングして実装。

---

## セットアップ

```bash
# リポジトリをクローン後
cd job-finder

# 仮想環境作成 & 依存インストール
python3 -m venv .venv
.venv/bin/pip install requests beautifulsoup4
```

---

## 使い方

### 求人を検索する

```bash
./baitoru search {キーワード} [オプション]
```

```bash
# キーワードで検索
./baitoru search カフェ

# 給与条件を指定
./baitoru search カフェ --salary-type 時給 --salary 1200

# 複数フィルターを組み合わせる
./baitoru search カフェ --salary-type 時給 --salary 1200 --period 長期 --period 昼

# 雇用形態を絞り込む
./baitoru search --employment バイト --employment 派遣

# 単発・土日のみ
./baitoru search コンビニ --period 単発 --period 土日祝のみ

# エリアとソートを指定
./baitoru search カフェ --region kansai --sort 新着

# ページを指定
./baitoru search カフェ --page 2
```

### 求人件数を取得する

```bash
./baitoru count [オプション]
```

```bash
./baitoru count カフェ
./baitoru count カフェ --salary-type 時給 --salary 1200
./baitoru count --employment 派遣 --region kansai
```

### 求人詳細を表示する

```bash
./baitoru detail {job_id}
```

```bash
# URLに含まれる数字部分がjob_id
# 例: /kanto/jlist/tokyo/.../job160163909/ → job_id は 160163909
./baitoru detail 160163909
```

### フィルター一覧を表示する

```bash
./baitoru filters
```

---

## オプション一覧

| オプション | 値 | 説明 |
|---|---|---|
| `--region` | `kanto` `kansai` `tokai` `tohoku` `koshinetsu` `chushikoku` `kyushu` | エリア（default: kanto） |
| `--salary-type` | `時給` `日給` `月給` `年俸` `出来高` | 給与種別 |
| `--salary` | 数値 | 最低給与額（有効値に自動丸め） |
| `--employment` | 下表参照 | 雇用形態（複数指定可） |
| `--period` | 下表参照 | 期間・シフト・時間帯（複数指定可） |
| `--sort` | `おすすめ` `新着` | ソート順 |
| `--page` | 数値 | ページ番号（searchのみ） |

### `--employment` の値

| 値 | 意味 |
|---|---|
| `バイト` / `アルバイト` / `パート` | アルバイト・パート |
| `正社員` | 正社員 |
| `契約社員` / `契約` | 契約社員 |
| `派遣` | 派遣 |
| `無期雇用派遣` | 無期雇用派遣 |
| `紹介予定派遣` | 紹介予定派遣 |
| `業務委託` | 業務委託 |

### `--period` の値

**勤務期間:** `単発` `短期` `1週間以内` `1ヶ月以内` `3ヶ月以内` `長期`

**シフト:** `シフト自由` `1〜2週毎` `月毎` `固定`

**週の日数:** `週1` `週2` `週3` `週4`

**時間帯:** `早朝` `朝` `昼` `夕方` `夜` `深夜`

**1日の時間:** `2h` `4h` `6h`

**勤務開始/終了:** `9時以降` `10時以降` `16時前` `17時前`

**休日:** `週休2日` `土日祝休み` `家庭都合` `土日祝のみ` `春夏冬限定`

**残業:** `残業なし` `残業少なめ` `残業多め`

### `--salary` の有効値

| 給与種別 | 有効な金額 |
|---|---|
| 時給 | 800, 850, 900, 950, 1000, 1050, 1100, 1200, 1300, 1400, 1500, 1800, 2000, 2200, 2500 |
| 日給 | 6499, 6500, 7000, 7500, 8000, 9000, 10000, 11000, 12000, 15000, 20000 |
| 月給 | 149999, 150000, 180000, 210000〜300000 (1万円刻み) |
| 年俸 | 1499999, 150万〜500万 (50万刻み) |

指定した金額が有効値でない場合は最も近い値に自動調整されます。

---

## ファイル構成

```
job-finder/
├── baitoru          # シェルラッパー（./baitoru で実行）
├── baitoru.py       # メインCLI実装
├── .venv/           # Python仮想環境
├── CLAUDE.md        # Claude Code向け指示
├── README.md        # このファイル
└── API_ANALYSIS.md  # バックエンドAPI解析ドキュメント
```

---

## API解析の概要

詳細は [API_ANALYSIS.md](API_ANALYSIS.md) を参照。

| エンドポイント | 用途 |
|---|---|
| `POST /noscreen/createurl/` | フィルターパラメータ → 検索URLへの変換 |
| `POST /noscreen/ajax/` | 件数取得・レコメンド等のJSON API |
| `GET /{region}/jlist/{filters}/` | 求人一覧HTML（スクレイピング） |
