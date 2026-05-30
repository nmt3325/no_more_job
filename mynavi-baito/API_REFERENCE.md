# マイナビバイト バックグラウンドAPI リファレンス

Playwright MCPでの通信解析（2026-05-30）により判明した内容をまとめたもの。
再度の通信解析なしに開発できることを目的とした詳細リファレンス。

---

## 目次

1. [技術スタック・基本情報](#1-技術スタック基本情報)
2. [共通仕様](#2-共通仕様)
3. [検索API](#3-検索api)
4. [求人詳細API](#4-求人詳細api)
5. [マスターデータAPI](#5-マスターデータapi)
6. [ユーザー認証・アカウントAPI](#6-ユーザー認証アカウントapi)
7. [レコメンド・通知API](#7-レコメンド通知api)
8. [バナー・特集API](#8-バナー特集api)
9. [その他ユーティリティAPI](#9-その他ユーティリティapi)
10. [searchCondition 完全スキーマ](#10-searchcondition-完全スキーマ)
11. [マスターID一覧](#11-マスターid一覧)
12. [レスポンス スキーマ](#12-レスポンス-スキーマ)
13. [SSRページ URLパターン](#13-ssrページ-urlパターン)

---

## 1. 技術スタック・基本情報

| 項目 | 内容 |
|---|---|
| フロントエンド | Nuxt.js (SSR) + Vuex + Vue.js |
| HTTPクライアント | axios（`this.$axios`） |
| CDN | AWS CloudFront（`*.cloudfront.net`） |
| サーバー | CloudFront → ALB → バックエンド |
| GTM/計測 | sgtm.baito.mynavi.jp（サーバーサイドGTM） |
| ベースURL | `https://baito.mynavi.jp` |

**Nuxt.js の初期データ埋め込み場所：**
- `window.__NUXT__.state` — Vuex全ストアの初期状態（SSRで注入）
- 求人一覧データは `window.__NUXT__.state.search.searchSolrList` に格納

**重要：** 求人一覧ページはSSRで初回HTMLに求人データが埋め込まれる。
クライアントサイドの絞り込み・ページネーションのみAPIが呼ばれる。

---

## 2. 共通仕様

### リクエストヘッダー（必須）

```http
Content-Type: application/json;charset=UTF-8
Accept: application/json, text/plain, */*
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...Chrome/148.0.0.0 Safari/537.36
Referer: https://baito.mynavi.jp/
```

**注意点：**
- 全エンドポイントが `POST` メソッド
- ボディは JSON（空の場合も `{}` を送信）
- `Content-Type` が `application/json;charset=UTF-8` でないと 415 エラー
- 認証が不要なAPIは Cookie なしで呼び出し可能
- 認証が必要なAPI（クリップ作成・応募など）はセッションCookieが必要

### エラーレスポンス形式

```json
{
  "errors": [
    {
      "code": "MynaviRequired",
      "fieldNames": ["page"],
      "parameters": {}
    }
  ]
}
```

主なエラーコード：
- `MynaviRequired` — 必須フィールドが未指定
- `NOT_READABLE` — JSONパース不可（型ミスなど）

---

## 3. 検索API

### 3-1. 求人一覧検索（メイン）

```
POST /api/search/solr/list
```

**リクエスト：**

```json
{
  "searchCondition": { /* → 第10節参照 */ },
  "page": 1,
  "reserveFlg": false,
  "sort": "NEW"
}
```

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `searchCondition` | object | ✓（空オブジェクト可） | 検索条件（第10節参照） |
| `page` | integer | ✓ | ページ番号（1〜） |
| `reserveFlg` | boolean | ✓ | 直雇用のみ。通常は`false` |
| `sort` | string | — | ソート順（下記参照） |

**sortの値（SORT_QUERY定数）：**

| 値 | 説明 |
|---|---|
| `"NEW"` | 新着順（デフォルト） |
| `"OSUSUME"` | おすすめ順 |
| `"WAGE_HOURLY"` | 時給高い順 |
| `"WAGE_DAILY"` | 日給高い順 |
| `"WAGE_MONTHLY"` | 月給高い順 |
| `"DISTANCE"` | 距離順（位置情報必要） |

**レスポンス：**

```json
{
  "jobList": [ /* 求人オブジェクト配列（第12節参照） */ ],
  "searchCount": 10851,
  "areaBreadcrumbList": [],
  "routeBreadcrumbList": [],
  "occupationBreadcrumbList": [],
  "kodawariBreadcrumbList": [],
  "apparelBrandList": [],
  "fashionBuildingList": []
}
```

**1ページあたりの件数：** APIが返す件数は固定30件（`displayCount`パラメータは現在未対応の模様）

---

### 3-2. 検索件数取得

```
POST /api/search/count
```

**リクエスト：**

```json
{
  "searchCondition": { /* searchConditionオブジェクト */ }
}
```

**レスポンス：**

```json
{
  "searchCount": 10851,
  "lastUpdatedAt": "2026-05-30T00:00:00+09:00"
}
```

---

### 3-3. 求人コード指定検索

```
POST /api/search/job-stock-cd/solr/list
```

**リクエスト：**

```json
{
  "jobStockCdList": ["J0134106676", "J0134222403"],
  "page": 1,
  "reserveFlg": false
}
```

---

### 3-4. 類似求人検索

```
POST /api/search/similar-job/list
```

**リクエスト：**

```json
{
  "searchCondition": { /* searchConditionオブジェクト */ },
  "jobStockCd": "J0134106676"
}
```

---

### 3-5. 検索条件ラベル取得

```
POST /api/search/condition-label
```

選択中の検索条件の日本語ラベルを返す。

```json
{
  "searchCondition": { "prefectureId": 13, "occupationIdList": ["1"] }
}
```

---

### 3-6. LP変換リンク生成

```
POST /api/search/lp/conversion
```

検索条件からLP（ランディングページ）URLを生成する。

**リクエスト：**

```json
{
  "searchConditionList": [
    {
      "occupationIdList": ["1"]
    }
  ]
}
```

**レスポンス：**

```json
{
  "lpLinkList": [
    {
      "searchCondition": {
        "areaIdList": [],
        "routeIdList": [],
        "occupationIdList": ["1"],
        "apparelBrandIdList": [],
        "fashionBuildingIdList": []
      }
    }
  ]
}
```

---

### 3-7. 地図用店舗リスト

```
POST /api/search/map/shop/list
```

地図表示用の店舗座標リストを返す。

```json
{
  "searchCondition": { "prefectureId": 13 },
  "page": 1
}
```

---

### 3-8. AIサジェスト求人（DB）

```
POST /api/search/db/list
```

クリップ・履歴ベースのDB検索用（認証済みユーザー向け）。

---

## 4. 求人詳細API

### 4-1. 求人詳細取得

```
POST /api/job/detail
```

**リクエスト：**

```json
{
  "jobStockCd": "J0134106676"
}
```

**レスポンス：**

```json
{
  "jobDetail": { /* 求人詳細オブジェクト（第12節参照） */ }
}
```

---

### 4-2. 求人アクセス記録（トラッキング）

```
POST /api/job/access/create
```

求人詳細を閲覧したことを記録する（閲覧履歴）。

```json
{
  "jobStockCd": "J0134106676"
}
```

**レスポンス：** `{}` （空オブジェクト）

---

## 5. マスターデータAPI

### 5-1. エリアマスター

```
POST /api/master/area/list
```

**リクエスト例：**

```json
// 全都道府県（depth=1）
{ "areaList": [{ "depth": 1 }] }

// 東京都の市区（depth=2）
{ "areaList": [{ "areaId": "13", "depth": 2 }] }

// 東京23区のエリア（depth=3）
{ "areaList": [{ "areaId": "13-651", "depth": 3 }] }

// 新宿区の駅周辺（depth=4）
{ "areaList": [{ "areaId": "13-651-35", "depth": 4 }] }
```

**areaIdの構造：** `都道府県ID-市区グループID-市区ID-エリアID`
（例: `13-651-35-48` = 東京都 23区全体 新宿区 新宿駅東口）

**レスポンス：**

```json
{
  "areaList": [
    {
      "areaId": "13",
      "label": "東京都",
      "depth": 1,
      "areaList": [
        {
          "areaId": "13-651",
          "label": "23区全体",
          "depth": 2,
          "areaList": [ /* 再帰構造 */ ]
        }
      ]
    }
  ]
}
```

---

### 5-2. 路線マスター

```
POST /api/master/route/list
```

**リクエスト例：**

```json
// 東京の鉄道会社一覧（depth=2）
{ "routeList": [{ "routeId": "13", "depth": 2 }] }

// 東京の路線一覧（depth=3）
{ "routeList": [{ "routeId": "13", "depth": 3 }] }

// JR東日本の駅一覧（depth=4）
{ "routeList": [{ "routeId": "13-6", "depth": 4 }] }
```

**routeIdの構造：** `都道府県ID-鉄道会社ID-路線ID`
（例: `13-6-25` = 東京都 JR東日本 山手線）

**レスポンス：**

```json
{
  "routeList": [
    {
      "routeId": "13",
      "label": "東京都",
      "depth": 1,
      "routeList": [
        { "routeId": "13-6", "label": "ＪＲ東日本", "depth": 2, "routeList": [
            { "routeId": "13-6-25", "label": "山手線", "depth": 3, "routeList": [] }
        ]}
      ]
    }
  ]
}
```

**主要な路線ID（東京）：**

| routeId | 路線名 |
|---|---|
| `13-6` | ＪＲ東日本（鉄道会社） |
| `13-6-25` | 山手線 |
| `13-6-39` | 総武線 |
| `13-6-97` | 中央線 |
| `13-124` | 東京メトロ（鉄道会社） |
| `13-119` | 都営地下鉄（鉄道会社） |
| `13-126` | 東急電鉄（鉄道会社） |

---

### 5-3. 職種マスター

```
POST /api/master/occupation/list
```

**リクエスト例：**

```json
// 大分類のみ（depth=1）
{ "occupationList": [{ "depth": 1 }] }

// 中分類まで（depth=2）
{ "occupationList": [{ "depth": 2 }] }

// 小分類まで（depth=3）
{ "occupationList": [{ "depth": 3 }] }
```

**occupationIdの構造：** `大分類ID-中分類ID-小分類ID`

**レスポンス：**

```json
{
  "occupationList": [
    {
      "occupationId": "1",
      "label": "飲食・フード",
      "depth": 1,
      "occupationList": [
        {
          "occupationId": "1-1",
          "label": "カフェ",
          "depth": 2,
          "occupationList": [
            { "occupationId": "1-1-1", "label": "ホール", "depth": 3, "occupationList": [] },
            { "occupationId": "1-1-2", "label": "キッチン・調理補助", "depth": 3, "occupationList": [] }
          ]
        }
      ]
    }
  ]
}
```

**主要な職種ID：**

| occupationId | 職種名 |
|---|---|
| `1` | 飲食・フード |
| `1-1` | カフェ |
| `1-2` | 居酒屋・バー |
| `1-3` | ファーストフード・デリ |
| `1-100` | ファミリーレストラン |
| `1-4` | レストラン・専門料理店 |
| `3` | 販売・接客・サービス |
| `3-94` | コンビニ・スーパー |
| `7` | 教育 |
| `7-46` | 塾講師 |
| `9` | 医療・介護・保育 |
| `10` | オフィスワーク |
| `10-65` | コールセンター |
| `13` | 軽作業 |
| `16` | アパレル・ファッション関連 |
| `17` | 工場・倉庫・建築・土木 |
| `18` | 警備・清掃・ビル管理 |

---

### 5-4. 企業ブランドマスター

```
POST /api/master/company-brand/list
```

**リクエスト：** `{}`

**レスポンス：**

```json
{
  "companyBrandGroupList": [
    {
      "initialChar": "ア",
      "companyBrandList": [
        { "companyBrandId": 818, "companyBrandName": "アーク引越センター" }
      ]
    }
  ]
}
```

**主要ブランドID（一部）：**

| ID | ブランド名 |
|---|---|
| 12 | マクドナルド |
| 216 | タリーズコーヒー |
| 140 | ドトールコーヒー |
| 526 | モスバーガー |
| 492 | くら寿司 |
| 296 | スシロー |
| 138 | ユニクロ |
| 194 | ファミリーマート |
| 10 | セブン‐イレブン |
| 126 | ダイソー |
| 750 | Uber Eats |
| 18 | ニトリ |

---

### 5-5. こだわり条件マスター

```
POST /api/master/kodawari/list
```

**リクエスト：** `{}`

**レスポンス キー一覧：**

| キー | 説明 | searchConditionでの使用箇所 |
|---|---|---|
| `period` | 勤務期間 | `kodawari.periodIdList` |
| `employee` | 雇用形態 | `kodawari.employeeIdList` |
| `shift` | 週勤務日数 | `kodawari.shiftId`（単一値） |
| `workingTimezone` | 勤務時間帯 | `kodawari.workingTimezoneIdList` |
| `wage1st` | 給与種別・条件 | `kodawari.wageId`（"1-14"形式） |
| `kodawari` | こだわり条件 | `kodawari.kodawariIdList` |
| `season` | 季節限定 | `kodawari.seasonIdList` |
| `gaugeKeyword` | ゲージ系キーワード | — |

---

### 5-6. 市区郡マスター

```
POST /api/master/sikugun/list
```

**リクエスト：**

```json
{ "prefectureId": 13 }
```

**レスポンス：** `{ "sikugunList": [...] }`

---

### 5-7. ランドマークマスター

```
POST /api/master/landmark/list
```

商業施設・ショッピングモールなどのランドマーク一覧。

---

### 5-8. 路線ID逆引き

```
POST /api/master/routeId
```

座標から最寄り路線IDを取得する。

---

### 5-9. 求人種別マスター

```
POST /api/master/job/list
```

---

## 6. ユーザー認証・アカウントAPI

認証が必要なAPIはセッションCookie（`mbnSession`等）が必要。

### 6-1. ログイン状態確認

```
POST /api/user/login-check
```

**リクエスト：** `{}`

**レスポンス：**

```json
{
  "loginFlg": false
}
```

---

### 6-2. ログイン

```
POST /api/user/login
```

**リクエスト：**

```json
{
  "mailAddress": "user@example.com",
  "password": "password",
  "autoLoginFlg": true,
  "recaptchaToken": "..."
}
```

---

### 6-3. ログアウト

```
POST /api/user/logout
```

**リクエスト：** `{}`

---

### 6-4. ユーザー情報取得

```
POST /api/user/detail
```

**リクエスト：** `{}`

---

### 6-5. クリップ（お気に入り）一覧

```
POST /api/user/clip/list
```

```json
{ "page": 1 }
```

---

### 6-6. クリップ件数確認

```
POST /api/user/clip/count
```

**リクエスト：**

```json
{
  "jobStockCdList": ["J0134106676", "J0134222403"]
}
```

---

### 6-7. クリップ追加

```
POST /api/user/clip/create
```

```json
{ "jobStockCd": "J0134106676" }
```

---

### 6-8. 応募

```
POST /api/entry/create
```

---

### 6-9. 応募履歴

```
POST /api/entry/history/list
```

```json
{ "page": 1 }
```

---

### 6-10. ユーザー登録・編集

```
POST /api/user/pre-register   # 仮登録
POST /api/user/register       # 本登録
POST /api/user/edit           # 情報編集
POST /api/user/withdrawal     # 退会
POST /api/user/contact        # 問い合わせ
POST /api/user/password/remind  # パスワードリマインダー
POST /api/user/password/change  # パスワード変更
POST /api/user/password/update  # パスワードリセット
```

---

## 7. レコメンド・通知API

### 7-1. おすすめ求人

```
POST /api/recommend/list
```

**リクエスト：**

```json
{
  "trackingId": "1780092216962.728825500",
  "element": "personal_rcm",
  "frameId": 30002,
  "category": "1-1",
  "limit": "24"
}
```

**レスポンス：**

```json
{
  "recommendTitle": "あなたにおすすめの求人",
  "siteId": "PC",
  "recommendJobList": [ /* 求人オブジェクト配列 */ ]
}
```

---

### 7-2. レコメンド軸取得

```
POST /api/recommend/search-axis/list
```

---

### 7-3. お知らせ一覧

```
POST /api/notice/list
```

**リクエスト：** `{}`

**レスポンス：**

```json
{
  "noticeList": [
    {
      "noticeUserId": 2582686,
      "noticeDiv": 0,
      "title": "【重要なお知らせ】マイナビバイトシステムメンテナンス実施について",
      "publicationStartDateString": "2026-05-29T00:00:00+09:00"
    }
  ]
}
```

---

### 7-4. お知らせ詳細

```
POST /api/notice/detail
```

```json
{ "noticeUserId": 2582686 }
```

---

### 7-5. ランキング（職種別）

```
POST /api/ranking/occupation/list
```

```json
{ "area1stId": 13 }
```

---

### 7-6. ランキング（ブランド別）

```
POST /api/ranking/brand/list
```

---

## 8. バナー・特集API

### 8-1. バナーリスト

```
POST /api/banner/list
POST /api/banner/lp/list
```

**リクエスト（lp/list）：**

```json
{
  "searchCondition": { "occupationIdList": ["1"] }
}
```

---

### 8-2. バナーインプレッション更新

```
POST /api/banner/imp/update
```

```json
{ "bannerId": 123 }
```

---

### 8-3. バナークリック更新

```
POST /api/banner/click/update
```

---

### 8-4. バナーコンバージョン更新

```
POST /api/banner/cv/update
```

---

### 8-5. 特集リスト

```
POST /api/feature/list
POST /api/feature/search-condition
POST /api/feature/click/update
```

---

## 9. その他ユーティリティAPI

### 9-1. キーワードサジェスト

```
POST /api/suggest/list
```

**リクエスト（全必須フィールド）：**

```json
{
  "searchWord": "カフェ",
  "prefectureId": 13,
  "limit": 10,
  "viewRecommend": false,
  "viewPickup": false,
  "trackingId": "1780092216962.000000"
}
```

`trackingId` は `{unix_ms}.{random}` 形式の文字列。

**レスポンス：**

```json
{
  "suggestList": [
    {
      "selectedKeywordList": [
        {
          "id": "300100001",
          "keyword": "カフェ",
          "category": "職種 飲食・フード"
        }
      ],
      "searchCondition": {
        "areaUnitSiteId": 2,
        "prefectureId": 13,
        "occupationIdList": ["1-1"]
      }
    }
  ]
}
```

---

### 9-2. ジオコーダー（住所→座標）

```
POST /api/map/geocoder
```

```json
{ "address": "東京都新宿区新宿3-1-1" }
```

---

### 9-3. 最寄り駅ジオコーダー

```
POST /api/map/station-geocoder
```

---

### 9-4. 郵便番号検索

```
POST /api/map/zipcode
```

```json
{ "zipCode": "160-0022" }
```

---

## 10. searchCondition 完全スキーマ

`POST /api/search/solr/list` および `/api/search/count` の `searchCondition` オブジェクトの完全な定義。

```typescript
interface SearchCondition {
  // ── 場所 ──────────────────────────────
  prefectureId?: number;          // 都道府県ID (13=東京, 27=大阪など)
  areaIdList?: string[];          // エリアID配列 (例: ["13-651-35"])
  routeIdList?: string[];         // 路線/駅ID配列 (例: ["13-6-25"])

  // ── 職種・企業 ─────────────────────────
  occupationIdList?: string[];    // 職種ID配列 (例: ["1", "1-1"])
  brandId?: number;               // 企業ブランドID
  clientCd?: string;              // 企業コード

  // ── フリーワード ───────────────────────
  freeword?: {
    words: string[];              // 検索ワード（AND条件）
    excludedWords: string[];      // 除外ワード
  };

  // ── こだわり条件（ネスト） ──────────────
  kodawari?: {
    wageId?: string;              // 給与条件 ※"wage1stId-wage2ndId"形式
                                  //   例: "1-14"=時給1300円以上
                                  //       "1-16"=時給1500円以上
                                  //       "2-5"=日給8000円以上
                                  //       "3-7"=月給20万円以上
    prefectureHighWageFlg?: boolean;  // 都道府県内高時給
    kodawariIdList?: number[];    // こだわりID配列（第11節参照）
    periodIdList?: number[];      // 勤務期間ID配列（第11節参照）
    workingTimezoneIdList?: number[]; // 勤務時間帯ID配列（第11節参照）
    shiftId?: number;             // 週勤務日数ID（単一）（第11節参照）
    employeeIdList?: number[];    // 雇用形態ID配列（第11節参照）
    seasonIdList?: number[];      // 季節限定ID配列（第11節参照）
    langLevelJapanese?: number;   // 日本語レベル（外国人向け）
  };

  // ── その他 ────────────────────────────
  excludeNoHighSchoolStudentFlg?: boolean;  // 高校生不可を除外
  areaUnitSiteId?: number;        // エリア単位サイトID (内部用)

  // ── 地図検索（高度） ────────────────────
  rectangularSearchRegion?: {     // 矩形範囲検索
    northLat: number;
    southLat: number;
    eastLng: number;
    westLng: number;
  };
  circularSearchRegion?: {        // 円形範囲検索
    centerLat: number;
    centerLng: number;
    radiusKm: number;
  };
}
```

**実使用例：**

```json
{
  "prefectureId": 13,
  "areaIdList": ["13-651-35"],
  "occupationIdList": ["1-1"],
  "freeword": {
    "words": ["カフェ", "バリスタ"],
    "excludedWords": ["深夜"]
  },
  "kodawari": {
    "wageId": "1-14",
    "kodawariIdList": [9, 42],
    "periodIdList": [201],
    "workingTimezoneIdList": [2],
    "shiftId": 4,
    "employeeIdList": [1]
  },
  "excludeNoHighSchoolStudentFlg": false
}
```

---

## 11. マスターID一覧

### 都道府県ID

| ID | 都道府県 | ID | 都道府県 | ID | 都道府県 |
|---|---|---|---|---|---|
| 1 | 北海道 | 14 | 神奈川 | 27 | 大阪 |
| 2 | 青森 | 15 | 新潟 | 28 | 兵庫 |
| 3 | 岩手 | 16 | 富山 | 29 | 奈良 |
| 4 | 宮城 | 17 | 石川 | 30 | 和歌山 |
| 5 | 秋田 | 18 | 福井 | 31 | 鳥取 |
| 6 | 山形 | 19 | 山梨 | 32 | 島根 |
| 7 | 福島 | 20 | 長野 | 33 | 岡山 |
| 8 | 茨城 | 21 | 岐阜 | 34 | 広島 |
| 9 | 栃木 | 22 | 静岡 | 35 | 山口 |
| 10 | 群馬 | 23 | 愛知 | 40 | 福岡 |
| 11 | 埼玉 | 24 | 三重 | 47 | 沖縄 |
| 12 | 千葉 | 25 | 滋賀 | | |
| 13 | 東京 | 26 | 京都 | | |

---

### 雇用形態ID（`kodawari.employeeIdList`）

| ID | ラベル |
|---|---|
| 1 | アルバイト・パート |
| 2 | 正社員 |
| 3 | 契約社員 |
| 4 | 派遣社員 |
| 5 | 紹介予定派遣 |
| 7 | 業務委託 |

---

### 勤務期間ID（`kodawari.periodIdList`）

| ID | ラベル |
|---|---|
| 101 | 単発（1日） |
| 102 | 短期（1週間以内） |
| 103 | 短期（1ヶ月以内） |
| 104 | 短期（3ヶ月以内） |
| 201 | 長期（3ヶ月以上） |
| 202 | 春/夏/冬休み期間限定 |

---

### 勤務時間帯ID（`kodawari.workingTimezoneIdList`）

| ID | ラベル |
|---|---|
| 1 | 朝 |
| 2 | 昼 |
| 3 | 夕方 |
| 4 | 夜勤 |
| 5 | 早朝 |
| 7 | 夜 |
| 8 | 日勤のみ |
| 9 | 夜勤のみ |
| 10 | 交替制 |

---

### 週勤務日数ID（`kodawari.shiftId`、単一値）

| ID | ラベル |
|---|---|
| 1 | 週1日 |
| 2 | 週1日以上 |
| 3 | 週2日 |
| 4 | 週2日以上 |
| 5 | 週3日 |
| 6 | 週3日以上 |
| 7 | 週4日 |
| 8 | 週4日以上 |
| 9 | 週5日 |
| 10 | 週5日以上 |

---

### 給与条件（`kodawari.wageId` = `"wage1stId-wage2ndId"`）

**時給（wage1stId = 1）:**

| wageId | 条件 |
|---|---|
| `1-1` | 700円未満 |
| `1-2` | 700円以上 |
| `1-4` | 800円以上 |
| `1-6` | 900円以上 |
| `1-8` | 1000円以上 |
| `1-10` | 1100円以上 |
| `1-12` | 1200円以上 |
| `1-13` | 1250円以上 |
| `1-14` | 1300円以上 |
| `1-15` | 1400円以上 |
| `1-16` | 1500円以上 |
| `1-17` | 2000円以上 |
| `1-18` | 2500円以上 |
| `1-19` | 3000円以上 |

**日給（wage1stId = 2）:**

| wageId | 条件 |
|---|---|
| `2-3` | 7000円以上 |
| `2-5` | 8000円以上 |
| `2-7` | 9000円以上 |
| `2-9` | 10000円以上 |
| `2-11` | 12000円以上 |
| `2-12` | 15000円以上 |
| `2-13` | 20000円以上 |

**月給（wage1stId = 3）:**

| wageId | 条件 |
|---|---|
| `3-2` | 15万円以上 |
| `3-4` | 17万円以上 |
| `3-7` | 20万円以上 |
| `3-12` | 25万円以上 |

---

### 季節限定ID（`kodawari.seasonIdList`、2026年夏時点）

| ID | ラベル |
|---|---|
| 8 | SALEスタッフ(夏) |
| 9 | ビアガーデン |
| 10 | 夏休み |
| 11 | 夏フェス・夏イベント |
| 12 | 花火大会 |
| 13 | お中元 |

---

### こだわりID（`kodawari.kodawariIdList`）主要なもの

| ID | ラベル | ID | ラベル |
|---|---|---|---|
| 1 | 駅から5分以内 | 48 | 副業・Wワーク歓迎 |
| 2 | 服装自由 | 49 | 履歴書不要 |
| 3 | 髪型自由 | 51 | 扶養控除内勤務可 |
| 4 | オープニングスタッフ | 55 | 留学生歓迎 |
| 6 | 日払い／週払い | 56 | 髪色自由 |
| 9 | 未経験者歓迎 | 57 | ピアス可 |
| 10 | まかない(食事)あり | 58 | ネイル可 |
| 17 | 友達と応募歓迎 | 60 | バイク/自転車通勤可 |
| 21 | 昇給あり | 63 | 託児所あり |
| 23 | シフト自由・自己申告 | 66 | 産休・育休取得実績あり |
| 24 | 平日のみ可 | 68 | 完全週休2日制 (土日祝休み) |
| 25 | 土日祝のみ勤務 | 76 | 20〜30代活躍中 |
| 29 | 社員登用あり | 81 | シフト制 |
| 36 | 社会保険完備 | 82 | 土日祝休み |
| 37 | 寮・社宅あり | 84 | 賞与・報奨金あり |
| 38 | 社員割引あり | 87 | 入社祝い金あり |
| 39 | 交通費支給 | 89 | 女性活躍中 |
| 40 | 高校生歓迎 | 91 | 日払いOK |
| 41 | フリーター歓迎 | 92 | 週払いOK |
| 42 | 大学生歓迎 | 93 | 即日勤務OK |
| 45 | 主婦(夫)歓迎 | 117 | オンライン面接可能 |
| 46 | すぐ働ける | 119 | 今すぐ面接予約可能 |
| 47 | 1日4h以内可 | | |

---

## 12. レスポンス スキーマ

### 12-1. 求人リストアイテム（`/api/search/solr/list` の `jobList[]`）

```typescript
interface JobListItem {
  jobStockCd: string;           // 求人コード (例: "J0134106676")
  jobStockVersion: string;      // バージョン
  jobFrameCd: string;           // フレームコード
  goodsType: number;            // 広告種別
  clientCd: string;             // 企業コード
  clientName: string;           // 店舗名（表示用）
  newFlg: boolean;              // 新着フラグ
  closeSoonFlg: boolean;        // 締切間近フラグ
  mediumImageList: Image[];     // PC用中画像
  mediumImageSpList: Image[];   // SP用中画像
  smallImageList: Image[];      // PC用小画像
  smallImageSpList: Image[];    // SP用小画像
  recruitmentOccupationName: string;  // 職種名
  recruitmentAppealPoint: string;     // アピールポイント
  jobMessageTitle: string;      // メッセージタイトル
  jobMessageContent: string;    // メッセージ内容
  jobOfferContent: string;      // 仕事内容
  wage: Wage;                   // 給与情報
  paymentType: LabelId;         // 支払い種別
  travelExpensesSupply: LabelId; // 交通費
  shift: Shift;                 // シフト
  workingTimePerDay: { note: string }; // 1日の勤務時間
  period: { list: LabelId[], note: string }; // 期間
  workingTimezoneList: LabelId[]; // 勤務時間帯
  employeeFigure: LabelId;      // 雇用形態
  kodawariList: Kodawari[];     // こだわり
  applicationDedicatedTelNo: string;  // 応募専用電話
  applyReceptionWayDiv: LabelId;      // 応募受付方法
  publicationStartDate: string; // 掲載開始日
  publicationEndDate: string;   // 掲載終了日
  remainingDays: number;        // 残り日数
  specialEntryUrl: string;      // 特別応募URL
  shopList: Shop[];             // 店舗一覧
  relatedJob: string;           // 関連求人
  relatedJobPart: string;       // 関連求人（パート）
  relatedWord: string;          // 関連ワード
}

interface Image {
  src: string;    // 相対パス (例: "/img/uploaded/xx/xx/xxxxxxjdm.jpeg")
  caption: string;
}

interface LabelId {
  id: number;
  label: string;
}

interface Wage {
  paymentSetupDiv: number;
  id: number;           // 1=時給, 2=日給, 3=月給
  label: string;
  wageAmountId: number;
  wageAmount: number;
  wageOverFlg: boolean;
  specialWageAmount: string;  // 表示用文字列 (例: "時給1250円～+交通費")
  note: string;
}

interface Shift {
  id: number;
  label: string;
  note: string;
}

interface Shop {
  subNo: number;
  clientShopCd: string;
  clientShopName: string;
  area1st: LabelId;   // 都道府県
  area2nd: LabelId;   // 市区
  area3rd: LabelId;   // エリア
  area4th: LabelId;   // 駅周辺
  accessList: Access[];
  locationDiv: LabelId;
  locationPrefecture: string;
  locationSikugun: string;
  locationAddress1: string;
  locationAddress2: string;
  locationMapLatitude: number;
  locationMapLongitude: number;
  locationPinLatitude: number;
  locationPinLongitude: number;
  locationMapScale: number;
  contactTel: string;
  contactReceptionTime: string;
  attachCd: string;
}

interface Access {
  subNo: number;
  routeArea1st: LabelId;      // 都道府県
  routeCompany: LabelId;      // 鉄道会社
  routeLine: LabelId;         // 路線
  routeStation: { id: number; label: string; name: string }; // 駅
  trafficFacilitiesDiv: LabelId;  // 交通手段 (徒歩/バス/車)
  timeRequired: number;           // 所要時間（分）
}
```

---

### 12-2. 求人詳細（`/api/job/detail` の `jobDetail`）

リストアイテムの全フィールドに加えて以下が追加：

```typescript
interface JobDetail extends Omit<JobListItem, 'mediumImageList'|'smallImageList'|...> {
  companyName: string;
  projectContent: string;
  jobStockCount: number;
  showClientOfferSearchLinkFlg: boolean;
  targetSiteDiv: number;
  areaUnitId: number;
  closeFlg: boolean;
  applicationCompleteFlg: boolean;
  occupation1st: LabelId;
  occupation2nd: LabelId;
  occupation3rd: LabelId;
  infoPr: string;
  workingWeekday: { note: string };
  applicationRequirementsNote: string;
  welfareNote: string;
  noHighSchoolStudentFlg: boolean;
  overHighSchoolFlg: boolean;
  overSpecialSchoolFlg: boolean;
  overUniversityFlg: boolean;
  internationalRecruitmentFlg: boolean;
  jobMiddleImageList: Image[];
  jobMiddleImageSpList: Image[];
  jobSmallImageList: Image[];
  jobSmallImageSpList: Image[];
  freeSpace: string;
  freeInputJobList: any[];
  freeInputEntryList: any[];
  seasonList: LabelId[];
}
```

---

## 13. SSRページ URLパターン

Nuxt.js SSRで事前レンダリングされるURLパターン。
初回アクセス時は求人データをHTMLに埋め込んで返す。

```
/                          # トップページ
/{prefecture}/             # 都道府県トップ (例: /tokyo/)
/{prefecture}/ss-{occ}/    # 都道府県 × 職種大分類 (例: /tokyo/ss-1/)
/{prefecture}/ss-{occ}/ssm-{sub}/  # 都道府県 × 職種中分類

/shokushu/{slug}/          # 職種LP (例: /shokushu/cafe/)
/kodawari/{slug}/          # こだわりLP (例: /kodawari/jimoto/)

/rec/{jobStockCd}/         # 求人詳細 (例: /rec/J0134106676/)
/info/NewsDetail.do?noticeUserId={id}  # お知らせ詳細
/clip/ClipList.do          # クリップ一覧（要ログイン）
/clip/JobHistoryList.do    # 閲覧履歴（要ログイン）

# ※ /search/ および /kw/{keyword}/ は 404/410 を返す（廃止済み）
```

**URLと searchCondition の対応例：**
- `/tokyo/ss-1/` → `{ prefectureId: 13, occupationIdList: ["1"] }`
- `/osaka/ss-1/ssm-1/` → `{ prefectureId: 27, occupationIdList: ["1-1"] }`

---

## 補足：開発Tips

### 認証なしで利用できるAPI
- 全マスターデータ API
- `search/solr/list`, `search/count`, `job/detail`
- `notice/list`, `recommend/list`（レコメンドは匿名として動作）
- `suggest/list`

### 認証が必要なAPI
- `user/clip/create`, `user/clip/list`
- `entry/create`, `entry/history/list`
- `user/detail`, `user/edit`

### 画像URLの組み立て
```
https://baito.mynavi.jp{image.src}
例: https://baito.mynavi.jp/img/uploaded/51/46/6364633jdm.jpeg
```

### トラッキングIDの生成
`suggest/list`、`recommend/list` などで使用：
```python
import time
tracking_id = f"{int(time.time() * 1000)}.{int(time.time() * 1000) % 1000000}"
```

### ページネーション
- `page` パラメータで制御（1始まり）
- 1ページあたり30件固定
- `searchCount` で総件数を取得可能
