# マイナビバイト CLI

マイナビバイト（https://baito.mynavi.jp）のバックグラウンドAPIをCLIから直接操作するツール。
Playwright MCPを用いた通信解析によって判明したAPIエンドポイントをラップしている。

## ファイル構成

```
mynavi-baito/
├── main.py           # CLIエントリーポイント
├── api.py            # APIクライアント関数群
├── API_REFERENCE.md  # APIの完全リファレンス（再解析不要）
└── README.md         # このファイル
```

## セットアップ

Python 3.8以上が必要。

```bash
pip3 install requests
```

## 使い方

```bash
python3 main.py <コマンド> [オプション]
```

### コマンド一覧

| コマンド | 説明 |
|---|---|
| `search` | 求人検索（全フィルター対応） |
| `detail` | 求人詳細表示 |
| `areas` | エリア一覧（IDの確認用） |
| `occupations` | 職種一覧（IDの確認用） |
| `routes` | 路線一覧（IDの確認用） |
| `brands` | 企業ブランド一覧 |
| `kodawari` | こだわり条件・給与・シフト等のID一覧 |
| `suggest` | キーワードサジェスト |
| `notices` | サイトのお知らせ一覧 |

---

## search コマンド

```bash
python3 main.py search [オプション]
```

### 場所条件

| オプション | 説明 | 例 |
|---|---|---|
| `--pref ID` | 都道府県ID | `--pref 13`（東京） |
| `--area ID[,ID...]` | エリアID（カンマ区切り） | `--area 13-651-35`（新宿区） |
| `--route ID[,ID...]` | 路線/駅ID（カンマ区切り） | `--route 13-6-25`（山手線） |

### 職種・企業条件

| オプション | 説明 | 例 |
|---|---|---|
| `--occupation ID[,ID...]` | 職種ID（カンマ区切り） | `--occupation 1-1`（カフェ） |
| `--brand ID` | 企業ブランドID | `--brand 216`（タリーズコーヒー） |
| `--client CD` | 企業コード | `--client 002988001130` |

### キーワード条件

| オプション | 説明 | 例 |
|---|---|---|
| `--word ワード[,ワード...]` | フリーワード（AND検索） | `--word カフェ,バリスタ` |
| `--exclude ワード[,ワード...]` | 除外ワード | `--exclude 深夜,夜勤` |

### こだわり条件（IDは `kodawari` コマンドで確認）

| オプション | 説明 | 例 |
|---|---|---|
| `--wage-id WAGE1ST-WAGE2ND` | 給与条件 | `--wage-id 1-14`（時給1300円以上） |
| `--high-wage` | 都道府県内高時給のみ | フラグ |
| `--kodawari ID[,ID...]` | こだわりID | `--kodawari 9,42`（未経験歓迎,大学生歓迎） |
| `--period ID[,ID...]` | 勤務期間ID | `--period 201`（長期） |
| `--timezone ID[,ID...]` | 勤務時間帯ID | `--timezone 2`（昼） |
| `--shift ID` | 週勤務日数ID | `--shift 4`（週2日以上） |
| `--employee ID[,ID...]` | 雇用形態ID | `--employee 1`（アルバイト） |
| `--season ID[,ID...]` | 季節限定ID | `--season 10`（夏休み） |

### その他・表示設定

| オプション | 説明 |
|---|---|
| `--no-highschool` | 高校生不可求人を除外 |
| `--reserve` | 直雇用のみ（派遣・業務委託除外） |
| `--page N` | ページ番号（デフォルト: 1、1ページ30件固定） |
| `--sort SORT` | ソート順（下記参照） |
| `--json` | JSON形式で出力 |

**ソート順（`--sort`）:**

| 値 | 説明 |
|---|---|
| `NEW`（デフォルト） | 新着順 |
| `OSUSUME` | おすすめ順 |
| `WAGE_HOURLY` | 時給高い順 |
| `WAGE_DAILY` | 日給高い順 |
| `WAGE_MONTHLY` | 月給高い順 |
| `DISTANCE` | 距離順 |

### 使用例

```bash
# 東京の飲食系求人を新着順で表示
python3 main.py search --pref 13 --occupation 1

# 東京のカフェ求人、時給1300円以上、時給高い順
python3 main.py search --pref 13 --occupation 1-1 --wage-id 1-14 --sort WAGE_HOURLY

# 「カフェ」「バリスタ」を含み「深夜」を除外
python3 main.py search --pref 13 --word カフェ,バリスタ --exclude 深夜

# 長期・アルバイト・未経験歓迎・週2日以上・昼
python3 main.py search --pref 13 \
  --period 201 --employee 1 --kodawari 9 --shift 4 --timezone 2

# 大阪のコンビニ・スーパー求人（2ページ目）
python3 main.py search --pref 27 --occupation 3-94 --page 2

# タリーズコーヒーの求人
python3 main.py search --brand 216

# 渋谷駅周辺（エリアID指定）
python3 main.py search --area 13-651-44-54

# 山手線沿線
python3 main.py search --route 13-6-25

# JSON出力（プログラムからの利用）
python3 main.py search --pref 13 --occupation 1-1 --json
```

---

## detail コマンド

```bash
python3 main.py detail <求人CD> [--json]
```

```bash
# 求人詳細を表示
python3 main.py detail J0134106676

# JSON形式で出力
python3 main.py detail J0134106676 --json
```

---

## マスターデータ確認コマンド

### エリア一覧

```bash
python3 main.py areas [--pref ID] [--depth 1-4]
```

```bash
# 全都道府県
python3 main.py areas

# 東京都の市区（depth=2）
python3 main.py areas --pref 13

# 東京都のエリア（depth=3）
python3 main.py areas --pref 13 --depth 3

# 新宿区の駅周辺エリア（depth=4）
python3 main.py areas --pref 13 --depth 4
```

depth の意味：1=都道府県、2=市区、3=エリア、4=駅周辺

### 職種一覧

```bash
python3 main.py occupations [--depth 1-3]
```

```bash
# 大分類のみ
python3 main.py occupations --depth 1

# 中分類まで（デフォルト）
python3 main.py occupations

# 小分類まで
python3 main.py occupations --depth 3
```

### 路線一覧

```bash
python3 main.py routes [--pref ID] [--depth 2-4]
```

```bash
# 東京の鉄道会社一覧
python3 main.py routes --pref 13

# 東京の路線一覧
python3 main.py routes --pref 13 --depth 3

# 大阪の路線一覧
python3 main.py routes --pref 27 --depth 3
```

### 企業ブランド一覧

```bash
python3 main.py brands [--keyword キーワード]
```

```bash
# 全ブランド
python3 main.py brands

# ブランド名で絞り込み
python3 main.py brands --keyword タリーズ
python3 main.py brands --keyword マクドナルド
```

### こだわり条件ID一覧

```bash
python3 main.py kodawari [--json]
```

`--wage-id`、`--kodawari`、`--period`、`--timezone`、`--shift`、`--employee`、`--season` に渡すIDはすべてこのコマンドで確認できる。

```bash
python3 main.py kodawari
```

出力例：
```
【給与条件 (--wage-id 'WAGE1ST-WAGE2ND')】
  1: 時給
    --wage-id 1-12: 時給1200円以上
    --wage-id 1-14: 時給1300円以上
    --wage-id 1-16: 時給1500円以上
  ...

【こだわり条件 (--kodawari)】
  9: 未経験者歓迎
  42: 大学生歓迎
  45: 主婦(夫)歓迎
  ...
```

### サジェスト

```bash
python3 main.py suggest <キーワード> [--pref ID] [--json]
```

```bash
python3 main.py suggest カフェ
python3 main.py suggest カフェ --pref 27  # 大阪
```

### お知らせ

```bash
python3 main.py notices
```

---

## API からの利用（プログラマブル）

`api.py` を直接インポートして使用できる。

```python
import api as mynavi

# 検索
result = mynavi.search_jobs(
    prefecture_id=13,
    occupation_id_list=['1-1'],
    wage_id='1-14',          # 時給1300円以上
    kodawari_id_list=[9, 42], # 未経験歓迎・大学生歓迎
    shift_id=4,               # 週2日以上
    sort=mynavi.SORT_WAGE_HOURLY,
    page=1,
)

for job in result['jobList']:
    print(job['jobStockCd'], job['recruitmentOccupationName'])
    print(job['wage']['specialWageAmount'])

# 求人詳細
detail = mynavi.get_job_detail('J0134106676')
job = detail['jobDetail']

# マスターデータ
areas = mynavi.get_area_list(area_id='13', depth=3)
occupations = mynavi.get_occupation_list(depth=2)
kodawari = mynavi.get_kodawari_list()
brands = mynavi.get_company_brand_list()
```

---

## 主要なID早見表

### 都道府県ID（`--pref`）

| ID | 都道府県 | ID | 都道府県 |
|---|---|---|---|
| 13 | 東京 | 27 | 大阪 |
| 11 | 埼玉 | 28 | 兵庫 |
| 12 | 千葉 | 26 | 京都 |
| 14 | 神奈川 | 23 | 愛知 |
| 1 | 北海道 | 40 | 福岡 |

### 主要職種ID（`--occupation`）

| ID | 職種 |
|---|---|
| `1` | 飲食・フード |
| `1-1` | カフェ |
| `1-2` | 居酒屋・バー |
| `1-3` | ファーストフード・デリ |
| `1-100` | ファミリーレストラン |
| `3` | 販売・接客・サービス |
| `3-94` | コンビニ・スーパー |
| `7` | 教育 |
| `7-46` | 塾講師 |
| `9` | 医療・介護・保育 |
| `10` | オフィスワーク |
| `10-65` | コールセンター |
| `13` | 軽作業 |
| `16` | アパレル・ファッション |
| `17` | 工場・倉庫・建築・土木 |
| `18` | 警備・清掃・ビル管理 |

### よく使うこだわりID（`--kodawari`）

| ID | こだわり |
|---|---|
| 9 | 未経験者歓迎 |
| 40 | 高校生歓迎 |
| 41 | フリーター歓迎 |
| 42 | 大学生歓迎 |
| 45 | 主婦(夫)歓迎 |
| 6 | 日払い／週払い |
| 23 | シフト自由・自己申告 |
| 29 | 社員登用あり |
| 37 | 寮・社宅あり |
| 39 | 交通費支給 |
| 46 | すぐ働ける |
| 48 | 副業・Wワーク歓迎 |
| 4 | オープニングスタッフ |
| 87 | 入社祝い金あり |

---

## 詳細仕様

API全エンドポイント・スキーマ・全マスターIDの完全な仕様は [API_REFERENCE.md](API_REFERENCE.md) を参照。
