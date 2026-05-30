# タウンワーク バックグラウンドAPI 解析仕様書

> 解析日: 2026-05-30  
> 対象: https://townwork.net/

---

## 1. アーキテクチャ概要

- **フレームワーク**: Next.js (App Router ではなく Pages Router)
- **レンダリング**: SSR（サーバーサイドレンダリング）
- **ボット対策**: AWS WAF (`aws-waf-token` Cookie) + WebSSO リダイレクト
- **CDN**: Amazon CloudFront (`via: 1.1 xxx.cloudfront.net`)
- **バックエンド**: Indeed ジョブプラットフォーム (indeedJobKey, jobResultTK など)

### WAF 対策について

`curl` や `httpx` などの通常の HTTP クライアントでは `/session/destroy/?type=webSSO` にリダイレクトされてデータ取得不可。  
**必ず Playwright のヘッドレスブラウザを経由すること。**

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url)  # wait_until 指定なし (デフォルト "load") が必須
    raw = page.evaluate("() => document.getElementById('__NEXT_DATA__')?.textContent")
```

> **重要**: `wait_until="domcontentloaded"` を使うと WAF リダイレクト途中で止まり失敗する。

---

## 2. 求人データ取得 API

### 2-1. メイン: HTML ページから __NEXT_DATA__ を抽出

求人一覧データはページの `<script id="__NEXT_DATA__">` タグに JSON で埋め込まれている。

**URL パターン**:
```
https://townwork.net/prefectures/{prefecture}/job_search/{...path}/
```

**例**:
```
# キーワード検索
https://townwork.net/prefectures/tokyo/job_search/kw/カフェ/

# エリア検索
https://townwork.net/prefectures/tokyo/job_search/ma-013001/sa-013001004/

# 駅検索 (ma/sa が必須)
https://townwork.net/prefectures/tokyo/job_search/ma-013001/sa-013001004/st-3975/

# 複合条件
https://townwork.net/prefectures/tokyo/job_search/ma-013001/emp-01/prf-0401/
```

**クエリパラメータ**:
| パラメータ | 説明 | 例 |
|---|---|---|
| `sc` | ソート順 | `1`=新着順, `3`=関連度順 |
| `sa` | 小地域コード（sa- を除いた数字） | `013001004` |
| `smn` | 給与下限コード | `101`〜`116`(時給), `201`〜`216`(日給), `301`〜`316`(月給) |
| `smx` | 給与上限コード | 同上 |
| `p` | ページ番号 (0-indexed) | `0`, `1`, `2`... |
| `cursor` | ページネーションカーソル | 前ページの `pageInfo.nextPages[N].cursor` |

**取得できる `pageProps.data` の主要フィールド**:
```json
{
  "pageInfo": {
    "currentPage": 0,
    "nextPages": [
      { "pageNum": 1, "cursor": "ABQAAQAUAAAAx..." },
      { "pageNum": 2, "cursor": "ABQAAgAoAAAAx..." }
    ],
    "prevPages": []
  },
  "recordInfo": {
    "totalCount": "2,343件"
  },
  "sortCondition": "1",
  "jobCardsJobSearchTK": "5-nrt1-0-xxxxxxxxxx",
  "jobCards": [ ... ],
  "searchConditionData": "{ ... }",
  "apiArgsQuery": { "sa": ["013001004"], "sc": "1" },
  "what": "",
  "filters": "[ ... ]"
}
```

### 2-2. Next.js データ API (補助的な利用)

Next.js の内部データ取得エンドポイント。buildId が必要。

```
GET https://townwork.net/_next/data/{buildId}/prefectures/{prefecture}/job_search/{...path}.json
```

**注意**: このエンドポイントも WAF トークンが必要。ブラウザコンテキスト内の `fetch()` から呼ぶか、Playwright 経由で使う。

`buildId` はホームページの HTML または `__NEXT_DATA__` から取得:
```python
import re, json
match = re.search(r'"buildId"\s*:\s*"([^"]+)"', html)
build_id = match.group(1)  # 例: "NZii8p8Ne7_Y-lpjKhhHy"
```

> buildId はデプロイのたびに変わるため毎回動的取得が必要。

---

## 3. URL パスセグメント (検索条件)

複数のセグメントを `/` で連結して組み合わせ可能。

| セグメント形式 | 説明 | 例 |
|---|---|---|
| `ma-{code}` | 市区町村コード | `ma-013001` (東京23区) |
| `sa-{code}` | 小地域（区・市）コード | `sa-013001004` (新宿区) |
| `st-{code}` | 駅コード | `st-3975` (新宿駅) |
| `kw/{keyword}` | キーワード (URL エンコード) | `kw/カフェ` |
| `emp-{code}` | 雇用形態 | `emp-01` (アルバイト) |
| `oc-{code}` | 職種カテゴリ | `oc-001` (飲食) |
| `omc-{code}` | サブ職種 | `omc-0001` (ホールスタッフ) |
| `prf-{code}` | 条件 | `prf-0401` (日払いOK) |

**重要**: 駅検索 (`st-`) は単体では 404。必ず `ma-` + `sa-` との組み合わせが必要。

---

## 4. 補助 API エンドポイント

### 4-1. キーワードサジェスト
```
GET https://townwork.net/api/containers/pc/KeywordAutoCompletePf/
  ?keyword={キーワード}
  &seqId={連番}
  &UUID={任意のUUID}
```
レスポンス:
```json
{ "seqId": "1", "suggestion": ["カフェ", "カフェ アルバイト", ...] }
```

### 4-2. 求人件数（概算）
```
GET https://townwork.net/api/containers/pc/JobSearchHitCount/
  ?kw={キーワード}
  &prefecture_id={3桁コード}
```
レスポンス:
```json
{
  "estimatedTotalResultsCount": 1278,
  "estimatedTotalResultsCountType": "AT_LEAST"
}
```

### 4-3. お気に入り求人リスト（要認証）
```
POST https://townwork.net/api/containers/pc/FavoriteJobList/
Content-Type: application/json
csrf-token: {CSRFトークン}
```

### 4-4. ジョブアラート件数（要認証）
```
POST https://townwork.net/api/containers/jobAlert/newJobCount/
Content-Type: application/json
```

### 4-5. トラッキング（無視可）
```
POST https://townwork.net/api/lettice/collect/
POST https://townwork.net/api/containers/pc/UILJobSearchResultsShownPf/
POST https://townwork.net/api/containers/pc/UILJobSeenPf/
```

---

## 5. jobCard データ構造

```json
{
  "indeedJobKey": "fde3552dcfdb8623",
  "jobResultTK": "5-nrt1-0-...-SoAy6_...",
  "title": "寿司屋の深夜キッチン調理スタッフ",
  "subTitle": "＜入社祝い金2万円有！＞...",
  "employerName": "きづなすし 新宿歌舞伎町店",
  "photoUrl": "https://c74.s3.indeed.com/xxx@w800",
  "access": "アクセス 西武新宿線 西武新宿正面口徒歩約3分...",
  "salary": "時給1,750円以上",
  "jobType": ["アルバイト・パート"],
  "workLocation": "東京都東京23区新宿区",
  "workHours": "勤務時間 シフトサイクル：1ヶ月 ...",
  "jobDescriptionContent": "仕事内容\n...",
  "preferences": ["制服あり", "扶養内勤務OK", "社員登用あり", ...],
  "favoriteButton": { "isFavorite": false },
  "newArrival": false,
  "isInvitation": false,
  "lettice": {
    "datePublished": 1772220302414,
    "location": { "lat": 35.694748, "lon": 139.7017 },
    "isRemoteJob": false,
    "isCrawled": false,
    "employmentTypes": ["75GKK"],
    "baseSalary": {
      "min": 1750, "max": null,
      "code": "JPY", "unit": "HOUR"
    }
  },
  "companyId": "8gcGd...",
  "placementId": "recruit-townwork-serp",
  "isPlacement": false,
  "matchingTagLabel": [],
  "minimumCount": 2
}
```

---

## 6. フィルターコード一覧

### 都道府県コード (prefecture)
| コード | 都道府県 | 3桁ID |
|---|---|---|
| `hokkaido` | 北海道 | 001 |
| `aomori` | 青森 | 002 |
| `iwate` | 岩手 | 003 |
| `miyagi` | 宮城 | 004 |
| `akita` | 秋田 | 005 |
| `yamagata` | 山形 | 006 |
| `fukushima` | 福島 | 007 |
| `ibaraki` | 茨城 | 008 |
| `tochigi` | 栃木 | 009 |
| `gunma` | 群馬 | 010 |
| `saitama` | 埼玉 | 011 |
| `chiba` | 千葉 | 012 |
| `tokyo` | 東京 | 013 |
| `kanagawa` | 神奈川 | 014 |
| `niigata` | 新潟 | 015 |
| `toyama` | 富山 | 016 |
| `ishikawa` | 石川 | 017 |
| `fukui` | 福井 | 018 |
| `yamanashi` | 山梨 | 019 |
| `nagano` | 長野 | 020 |
| `gifu` | 岐阜 | 021 |
| `shizuoka` | 静岡 | 022 |
| `aichi` | 愛知 | 023 |
| `mie` | 三重 | 024 |
| `shiga` | 滋賀 | 025 |
| `kyoto` | 京都 | 026 |
| `osaka` | 大阪 | 027 |
| `hyogo` | 兵庫 | 028 |
| `nara` | 奈良 | 029 |
| `wakayama` | 和歌山 | 030 |
| `tottori` | 鳥取 | 031 |
| `shimane` | 島根 | 032 |
| `okayama` | 岡山 | 033 |
| `hiroshima` | 広島 | 034 |
| `yamaguchi` | 山口 | 035 |
| `tokushima` | 徳島 | 036 |
| `kagawa` | 香川 | 037 |
| `ehime` | 愛媛 | 038 |
| `kochi` | 高知 | 039 |
| `fukuoka` | 福岡 | 040 |
| `saga` | 佐賀 | 041 |
| `nagasaki` | 長崎 | 042 |
| `kumamoto` | 熊本 | 043 |
| `oita` | 大分 | 044 |
| `miyazaki` | 宮崎 | 045 |
| `kagoshima` | 鹿児島 | 046 |
| `okinawa` | 沖縄 | 047 |

### 東京の市区町村コード (ma)
| コード | 地域 |
|---|---|
| `013001` | 東京23区 |
| `013002` | 東京市部 |
| `013003` | 八王子市 |
| `013004` | 立川市 |
| `013005` | 武蔵野市 |
| `013006` | 三鷹市 |
| `013007` | 青梅市 |
| (013008〜013037) | その他市部・島部 |

### 東京23区の小地域コード (sa)
| コード | 区名 |
|---|---|
| `013001001` | 千代田区 |
| `013001002` | 中央区 |
| `013001003` | 港区 |
| `013001004` | 新宿区 |
| `013001005` | 文京区 |
| `013001006` | 台東区 |
| `013001007` | 墨田区 |
| `013001008` | 江東区 |
| `013001009` | 品川区 |
| `013001010` | 目黒区 |
| `013001011` | 大田区 |
| `013001012` | 世田谷区 |
| `013001013` | 渋谷区 |
| `013001014` | 中野区 |
| `013001015` | 杉並区 |
| `013001016` | 豊島区 |
| `013001017` | 北区 |
| `013001018` | 荒川区 |
| `013001019` | 板橋区 |
| `013001020` | 練馬区 |
| `013001021` | 足立区 |
| `013001022` | 葛飾区 |
| `013001023` | 江戸川区 |

### 主要駅コード (st) ※東京
| コード | 駅名 | 路線例 | ma | sa |
|---|---|---|---|---|
| `8714` | 東京駅 | JR山手線 | 013001 | 013001001 |
| `3975` | 新宿駅 | JR山手線 | 013001 | 013001004 |
| `6683` | 渋谷駅 | JR山手線 | 013001 | 013001013 |
| `3035` | 池袋駅 | JR山手線 | 013001 | 013001016 |
| `2099` | 新橋駅 | JR東海道本線 | 013001 | 013001003 |
| `7780` | 品川駅 | JR山手線 | 013001 | 013001009 |
| `4050` | 秋葉原駅 | JR山手線 | 013001 | 013001001 |
| `6967` | 上野駅 | JR山手線 | 013001 | 013001006 |
| `5171` | 有楽町駅 | JR山手線 | 013001 | 013001001 |
| `6136` | 西武新宿駅 | 西武新宿線 | 013001 | 013001004 |

> 全1529駅は `tw stations` コマンドで取得可。各駅の ma/sa は `stationState.items[].stProps` に含まれる。

### 雇用形態コード (emp)
| コード | 名称 |
|---|---|
| `emp-01` | アルバイト・パート |
| `emp-02` | 正社員 |
| `emp-03` | 契約社員 |
| `emp-04` | 派遣社員 |
| `emp-05` | 業務委託 |

### 職種カテゴリコード (oc)
| コード | 名称 |
|---|---|
| `oc-001` | 飲食・フードサービス |
| `oc-002` | 営業・販売 |
| `oc-003` | 旅行・レジャー・イベント |
| `oc-004` | 倉庫・物流管理 |
| `oc-005` | 警備・保安 |
| `oc-006` | 経営・事業企画・人事・事務 |
| `oc-007` | マーケティング・広告・宣伝 |
| `oc-008` | 保育士・教員・講師 |
| `oc-009` | ドライバー・引越し・配送 |
| `oc-010` | 介護・福祉 |
| `oc-011` | 医療・看護師・薬剤師 |
| `oc-012` | メディア・クリエイター |
| `oc-013` | IT・Web・ゲームエンジニア |
| `oc-014` | エンジニアリング・設計開発 |
| `oc-015` | 整備・修理 |
| `oc-016` | 清掃・美化 |
| `oc-017` | ビューティー・生活サービス |
| `oc-018` | 建設・土木・施工 |
| `oc-019` | 製造・工場 |
| `oc-020` | 金融・財務・会計 |
| `oc-021` | 法務・法律 |
| `oc-022` | 研究 |
| `oc-023` | 農林漁業 |

### サブ職種コード (omc) ※抜粋
| コード | 名称 | 親職種 |
|---|---|---|
| `omc-0001` | ホールスタッフ | oc-001 |
| `omc-0002` | キッチンスタッフ | oc-001 |
| `omc-0003` | 皿洗い・洗い場 | oc-001 |
| `omc-0004` | 精肉・鮮魚加工 | oc-001 |
| `omc-0005` | 給食調理 | oc-001 |
| `omc-0006` | パン屋（ベーカリー） | oc-001 |
| `omc-0007` | フードカウンター販売員 | oc-001 |
| `omc-0008` | バー（BAR）・バーテンダー | oc-001 |
| `omc-0009` | 飲食店補助 | oc-001 |
| `omc-0010` | 飲食店（店長・マネージャー） | oc-001 |
| `omc-0011` | 営業 | oc-002 |
| `omc-0012` | テレフォンアポインター | oc-002 |
| `omc-0013` | ルートセールス | oc-002 |
| `omc-0014` | コンビニ | oc-002 |
| `omc-0015` | アパレル | oc-002 |
| `omc-0016` | 家電量販店・携帯販売 | oc-002 |
| `omc-0017` | 販売店（店長・マネージャー） | oc-002 |
| `omc-0019` | その他販売 | oc-002 |
| `omc-0024` | ピッキング | oc-004 |
| `omc-0025` | 検品 | oc-004 |
| `omc-0026` | 梱包 | oc-004 |
| `omc-0027` | 倉庫内仕分け | oc-004 |
| `omc-0028` | 在庫管理・商品管理 | oc-004 |
| `omc-0029` | フォークリフト | oc-004 |
| `omc-0037` | 営業事務 | oc-006 |
| `omc-0039` | その他事務 | oc-006 |
| `omc-0040` | データ入力・PC入力 | oc-006 |
| `omc-0041` | 受付 | oc-006 |
| `omc-0042` | コールセンター・テレオペ | oc-006 |
| `omc-0043` | 秘書 | oc-006 |

> 全151コード。サイトのURLに出現するものは `omc-0001`〜`omc-0151`。

### 条件コード (prf)

**期間 (01xx)**
| コード | 名称 |
|---|---|
| `prf-0101` | 短期 |
| `prf-0102` | 単発・1日OK |
| `prf-0103` | 長期 |
| `prf-0104` | 期間限定（春夏冬休み等） |

**曜日・日数 (02xx)**
| コード | 名称 |
|---|---|
| `prf-0201` | 土日祝のみOK |
| `prf-0202` | 平日のみOK |
| `prf-0203` | 週1日からOK |
| `prf-0204` | 週2・3日からOK |
| `prf-0205` | 週4日以上OK |
| `prf-0206` | 時間や曜日が選べる・シフト自由 |
| `prf-0207` | 固定時間・固定シフト制 |
| `prf-0208` | シフト制 |
| `prf-0209` | 月1シフト提出 |
| `prf-0210` | 隔週シフト提出 |
| `prf-0211` | 週1シフト提出 |
| `prf-0212` | 変形労働時間制 |

**時間帯 (03xx)**
| コード | 名称 |
|---|---|
| `prf-0301` | 早朝・朝の仕事 |
| `prf-0302` | 昼の仕事 |
| `prf-0303` | 夕方からの仕事 |
| `prf-0304` | 夜からの仕事 |
| `prf-0305` | 深夜の仕事 |
| `prf-0306` | 1日4時間以内OK |
| `prf-0307` | フルタイム歓迎 |
| `prf-0308` | 残業なし |

**給与 (04xx)**
| コード | 名称 |
|---|---|
| `prf-0401` | 日払いOK |
| `prf-0402` | 週払いOK |
| `prf-0403` | ボーナス・賞与あり |
| `prf-0404` | 給料前払いOK |
| `prf-0405` | 現金払いOK |
| `prf-0406` | 完全歩合制 |
| `prf-0407` | 昇給あり |
| `prf-0408` | 扶養内勤務OK |

**待遇・環境 (05xx)**
| コード | 名称 |
|---|---|
| `prf-0501` | 交通費支給 |
| `prf-0502` | まかない・食事補助あり |
| `prf-0503` | 社割あり |
| `prf-0504` | 研修あり |
| `prf-0505` | 資格取得支援または手当あり |
| `prf-0506` | 社員登用あり |
| `prf-0507` | 送迎あり |
| `prf-0508` | 寮・社宅・住宅手当あり |
| `prf-0509` | 託児所あり |
| `prf-0510` | 育児サポートあり |
| `prf-0511` | 家庭都合休OK |
| `prf-0512` | 産休・育休取得制度あり |
| `prf-0513` | 長期休暇あり |
| `prf-0514` | 無期雇用派遣 |
| `prf-0515` | 転勤なし |
| `prf-0516` | 職種変更なし |
| `prf-0517` | 社会保険あり |

**対象者 (06xx)**
| コード | 名称 |
|---|---|
| `prf-0601` | 高校生歓迎 |
| `prf-0602` | 学生歓迎 |
| `prf-0603` | フリーター歓迎 |
| `prf-0604` | 未経験・初心者OK |
| `prf-0605` | 経験者・有資格者歓迎 |
| `prf-0606` | 主婦・主夫歓迎 |
| `prf-0607` | 副業・WワークOK |
| `prf-0608` | ブランクOK |
| `prf-0609` | 学歴不問 |
| `prf-0612` | 60代（シニア）も応募可 |
| `prf-0613` | 70代（シニア）も応募可 |
| `prf-0614` | 留学生・外国人活躍中 |

**服装・働き方・その他 (07xx)**
| コード | 名称 |
|---|---|
| `prf-0701` | オープニングスタッフ |
| `prf-0702` | 駅チカ・駅ナカ |
| `prf-0703` | バイク通勤OK |
| `prf-0704` | 車通勤OK |
| `prf-0705` | リゾート |
| `prf-0706` | 英語が活かせる |
| `prf-0707` | 中国語が活かせる |
| `prf-0708` | フルリモート（完全在宅） |
| `prf-0709` | 在宅OK |
| `prf-0710` | 髪型・髪色自由 |
| `prf-0711` | 服装自由 |
| `prf-0712` | 制服あり |
| `prf-0713` | ひげOK |
| `prf-0714` | ネイルOK |
| `prf-0715` | ピアスOK |

**応募 (08xx)**
| コード | 名称 |
|---|---|
| `prf-0801` | 履歴書不要 |
| `prf-0802` | 面接なし |
| `prf-0803` | 入社祝い金あり |
| `prf-0804` | 即日勤務OK |
| `prf-0805` | 大量募集 |
| `prf-0806` | 急募 |
| `prf-0807` | 友達と応募OK |
| `prf-0808` | 職場見学可 |

### 給与コード (smn / smx)

同一の `smn` / `smx` パラメータで時給・日給・月給を区別。

**時給 (typeId: 1)**
| smn/smx コード | 金額 |
|---|---|
| `101` | 1,000円 |
| `102` | 1,100円 |
| `103` | 1,200円 |
| `104` | 1,300円 |
| `105` | 1,400円 |
| `106` | 1,500円 |
| `107` | 1,600円 |
| `108` | 1,700円 |
| `109` | 1,800円 |
| `110` | 1,900円 |
| `111` | 2,000円 |
| `112` | 2,100円 |
| `113` | 2,200円 |
| `114` | 2,300円 |
| `115` | 2,400円 |
| `116` | 2,500円 |

**日給 (typeId: 2)**
| smn/smx コード | 金額 |
|---|---|
| `201` | 6,500円 |
| `202` | 7,000円 |
| `203` | 7,500円 |
| `204` | 8,000円 |
| `205` | 9,000円 |
| `206` | 10,000円 |
| `207` | 11,000円 |
| `208` | 12,000円 |
| `209` | 13,000円 |
| `210` | 14,000円 |
| `211` | 15,000円 |
| `212` | 16,000円 |
| `213` | 17,000円 |
| `214` | 18,000円 |
| `215` | 19,000円 |
| `216` | 20,000円 |

**月給 (typeId: 3)**
| smn/smx コード | 金額 |
|---|---|
| `301` | 15万円 |
| `302` | 16万円 |
| `303` | 17万円 |
| `304` | 18万円 |
| `305` | 19万円 |
| `306` | 20万円 |
| `307` | 21万円 |
| `308` | 22万円 |
| `309` | 23万円 |
| `310` | 24万円 |
| `311` | 25万円 |
| `312` | 26万円 |
| `313` | 27万円 |
| `314` | 28万円 |
| `315` | 29万円 |
| `316` | 30万円 |

---

## 7. ページネーション

カーソルベースのページネーション。

```python
# 1ページ目取得
data = fetch_page(url)
next_pages = data["pageInfo"]["nextPages"]
# next_pages = [
#   {"pageNum": 1, "cursor": "ABQAAQAUAAAAAx..."},
#   {"pageNum": 2, "cursor": "ABQAAgAoAAAAx..."},
# ]

# 2ページ目取得
cursor = next_pages[0]["cursor"]
data_p2 = fetch_page(f"{url}?p=1&cursor={urllib.parse.quote(cursor)}")
```

- `currentPage` は 0-indexed
- `nextPages[N].pageNum` も 0-indexed (表示上は+1する)
- カーソルはページセッションに紐付いており使い回し可能
- 最大で4〜5ページ先のカーソルが事前提供される

---

## 8. searchConditionData の構造

`pageProps.data.searchConditionData` (JSON文字列) に全フィルターのマスターデータが入っている。

```python
scd = json.loads(data["searchConditionData"])
masters = scd["defaultMastersState"]
# masters のキー:
# - locationState       (市区町村: queryKey="ma"/"sa")
# - occupationState     (職種: queryKey="oc"/"omc")
# - stationState        (駅: queryKey="st", stProps={ma, sa})
# - jobTypeState        (雇用形態: queryKey="emp")
# - preferenceState     (条件: queryKey="prf")
# - salaryMinState      (給与下限: queryKey="smn")
# - salaryMaxState      (給与上限: queryKey="smx")
# - locationRadiusState (現在地半径: 未実装)
```

各アイテムの共通フィールド:
```json
{
  "id": "コード値",
  "label": "表示名",
  "queryKey": "URLパラメータキー",
  "lv1": { "id": "親カテゴリID", "label": "親カテゴリ名", "queryKey": "..." },
  "checked": false
}
```

駅アイテム追加フィールド:
```json
{
  "stProps": {
    "ma": "013001",
    "sa": "013001004",
    "prefectureLabel": "tokyo"
  }
}
```

---

## 9. リクエストヘッダー

Playwright 経由では自動設定されるが、fetch を直接使う場合:

```
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36
Accept: application/json
Accept-Language: ja,en;q=0.9
sec-ch-ua: "Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"
sec-ch-ua-mobile: ?0
sec-ch-ua-platform: "macOS"
```

POST リクエスト (containers API) に追加:
```
csrf-token: {トークン}  ← ページロード時にサーバーから付与
Content-Type: application/json
```

---

## 10. CLIツール実装概要

```
townwork/
├── pyproject.toml       # click, playwright, rich が依存
├── townwork/
│   ├── __init__.py
│   ├── api.py           # Playwright ベースの API クライアント
│   └── cli.py           # Click ベースの CLI
└── .venv/               # 仮想環境 (.venv/bin/tw でコマンド実行)
```

**インストール**:
```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/playwright install chromium
```

**使い方**:
```bash
# 基本検索
.venv/bin/tw search --keyword カフェ --prefecture tokyo

# 駅検索（ma/sa は自動解決）
.venv/bin/tw stations 新宿          # 駅コードを調べる
.venv/bin/tw search --station 3975  # 新宿駅周辺の求人

# 複合条件
.venv/bin/tw search --keyword バリスタ --employment 01 \
  --preference 0401 --min-salary 1500 --max-salary 2000

# JSON出力 (パイプライン向け)
.venv/bin/tw search --keyword カフェ --json | jq '.jobCards[].title'

# サジェスト・件数
.venv/bin/tw suggest カフェ
.venv/bin/tw count IT --prefecture osaka

# フィルターコード一覧
.venv/bin/tw list-filters
.venv/bin/tw list-filters --category preference
```
