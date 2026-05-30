# バイトル バックエンドAPI 解析ドキュメント

> 解析日: 2026-05-30  
> 対象サイト: https://www.baitoru.com/kanto/

---

## アーキテクチャ概要

バイトルはサーバーサイドレンダリング（SSR）+ jQuery AJAX のハイブリッド構成。

- **求人一覧**: HTMLページとして返却（スクレイピングが必要）
- **件数・レコメンド等**: `/noscreen/ajax/` への POST で JSON 取得
- **検索URL生成**: `/noscreen/createurl/` への POST でリダイレクトURLを生成

---

## エンドポイント一覧

### 1. 検索URL生成 `POST /noscreen/createurl/`

フォームパラメータ → 検索結果URLへのリダイレクト (HTTP 303) を返す。  
URLを直接構築するより**このエンドポイントをURL生成器として使うのが正解**（URLセグメントの内部コードが非連番のため）。

**必須ヘッダー:**
```
User-Agent: Mozilla/5.0 ...
Content-Type: application/x-www-form-urlencoded
Referer: https://www.baitoru.com/{region}/
```

**フォームパラメータ:**

| パラメータ      | 説明                        | 例              |
|--------------|---------------------------|----------------|
| `reqType`    | 常に `33`                  | `33`           |
| `midAreaCd`  | エリアコード（下表参照）      | `31`           |
| `tab_kbn`    | 常に `1`                   | `1`            |
| `redirect`   | `true` でリダイレクト        | `true`         |
| `keyword`    | フリーワード                 | `カフェ`        |
| `salaryType` | 給与種別コード（下表参照）    | `3`            |
| `salary`     | 最低給与額（下表の有効値）    | `1200`         |
| `baitTypes[]`| 雇用形態（複数可）           | `normal`       |
| `period[]`   | 期間・シフト・時間帯（複数可）| `85_trm_4`     |
| `jobsort`    | ソート順                    | `osusume`      |

**Locationヘッダーから取得したURLパターン例:**
```
/kanto/jlist/nsu2/tst3/stp4-sly5/btp1/wrdカフェ/srt2/
       ─────────────────────────────────────────────
       ↑ フィルターがURLセグメントとして埋め込まれる
```

---

### 2. AJAX汎用API `POST /noscreen/ajax/`

**必須ヘッダー:**
```
X-Requested-With: XMLHttpRequest
Content-Type: application/x-www-form-urlencoded
```

`ajax_type` パラメータで処理を切り替える。

#### ajax_type 一覧

| ajax_type                  | 説明                        | レスポンス |
|---------------------------|---------------------------|---------|
| `real_job_count_search`   | 求人件数・平均給与取得         | JSON    |
| `get_recommend_bd_async`  | レコメンド求人（ByteDance連携）| JSON    |
| `get_spot_baitoru_joblist`| スポットバイトル求人リスト      | JSON    |
| `get_spot_fjlist_link`    | スポット求人リンク            | JSON    |
| `set_search_night`        | 夜間検索フラグ設定            | JSON    |
| `area_layer_asp`          | エリアレイヤー（ASP用）       | HTML    |
| `ensn_layer_asp`          | 沿線レイヤー（ASP用）        | HTML    |
| `get_scout_memhistory`    | スカウト閲覧履歴             | JSON    |

#### real_job_count_search 詳細

```
POST /noscreen/ajax/
ajax_type=real_job_count_search
&mid_area_cd=31        ← エリアコード（midAreaCdではなくmid_area_cd）
&freeword=カフェ        ← キーワード
&area_cd=tdfk[]-13    ← 都道府県絞り込み（例: 東京都）
&salary_kbn=3         ← 給与種別
&min_salary=1200      ← 最低給与
&period_cd=85_trm_4   ← 期間・シフトコード
&shok1_cd=            ← 大職種コード
&tokucho_cd=          ← 特徴コード
```

**レスポンス例:**
```json
{
  "status": {"code": 200},
  "count_all": "33,909",
  "avg_salary": "1,604",
  "count_result": "0",
  "results": [],
  "recommend": []
}
```

#### get_spot_baitoru_joblist 詳細

```
POST /noscreen/ajax/
ajax_type=get_spot_baitoru_joblist
&tdfkCds=13,14,12,11,08,09,10    ← 都道府県コード（カンマ区切り）
&maxJobs=8
```

**レスポンス:** `{"jobs": [...]}` 形式のJSON

---

### 3. 求人一覧ページ (HTML)

```
GET https://www.baitoru.com/{region}/jlist/{filters}/
```

**ページネーション:** `/page{N}/` をパス末尾に付加

**レスポンス:** HTMLの `<article class="list-jobListDetail">` 要素に求人が格納されている

---

## エリアコード

### midAreaCd / createurl 用

| region (CLI)  | midAreaCd | 日本語名        |
|--------------|-----------|--------------|
| `kanto`      | `31`      | 関東           |
| `kansai`     | `32`      | 関西           |
| `tokai`      | `33`      | 東海           |
| `tohoku`     | `34`      | 東北           |
| `koshinetsu` | `35`      | 甲信越・北陸    |
| `chushikoku` | `36`      | 中国・四国      |
| `kyushu`     | `37`      | 九州・沖縄      |

### mid_area_cd / AJAX用 (real_job_count_search)

`real_job_count_search` では `mid_area_cd`（アンダースコア）を使い、値は `midAreaCd` と同じ。

---

## フィルターパラメータ詳細

### 給与種別 `salaryType` / `salary_kbn`

| 値  | 意味         |
|----|------------|
| `3` | 時給        |
| `2` | 日給        |
| `1` | 月給        |
| `0` | 年俸        |
| `6` | 完全出来高制 |

### 給与額 `salary` / `min_salary` の有効値

**時給 (salaryType=3):**
`800, 850, 900, 950, 1000, 1050, 1100, 1200, 1300, 1400, 1500, 1800, 2000, 2200, 2500`

**日給 (salaryType=2):**
`6499, 6500, 7000, 7500, 8000, 9000, 10000, 11000, 12000, 15000, 20000`

**月給 (salaryType=1):**
`149999, 150000, 180000, 210000, 220000, 230000, 240000, 250000, 260000, 270000, 280000, 290000, 300000`

**年俸 (salaryType=0):**
`1499999, 1500000, 1800000, 2000000, 2500000, 3000000, 3500000, 4000000, 4500000, 5000000`

> ⚠️ 上記以外の値を渡してもサーバー側で無視される（結果が0件になる）。  
> CLIでは最近似値に自動丸めする実装にしている。

### 雇用形態 `baitTypes[]`

| 値               | 意味          |
|----------------|-------------|
| `normal`       | アルバイト・パート |
| `regular`      | 正社員         |
| `contract`     | 契約社員        |
| `haken`        | 派遣           |
| `nlim_ehaken`  | 無期雇用派遣     |
| `syokai_rhaken`| 紹介予定派遣    |
| `outsg`        | 業務委託        |

### 期間・シフト・時間帯 `period[]`

**勤務期間:**

| 値            | 意味        |
|-------------|-----------|
| `83_trm_0`  | 単発(1日のみ) |
| `84_trm_X`  | 短期        |
| `81_trm_1`  | 1週間以内    |
| `80_trm_2`  | 1ヵ月以内    |
| `82_trm_3`  | 3ヵ月以内    |
| `85_trm_4`  | 長期        |

**シフト:**

| 値             | 意味              |
|-------------- |-----------------|
| `5_sft_5`    | シフト自由・相談OK    |
| `69_sft_69`  | シフト提出(1〜2週毎) |
| `70_sft_70`  | シフト提出(月毎)     |
| `111_sft_111`| 時間固定シフト制      |

**週の日数:**

| 値           | 意味         |
|------------|------------|
| `23_nsu_23`| 週1日からOK  |
| `6_nsu_6`  | 週2・3日からOK|
| `42_nsu_42`| 週4日以上OK  |

**時間帯:**

| 値           | 意味  |
|------------|-----|
| `88_tst_3` | 早朝  |
| `90_tst_0` | 朝   |
| `89_tst_1` | 昼   |
| `92_tst_4` | 夕方  |
| `91_tst_5` | 夜   |
| `87_tst_2` | 深夜  |

**1日の勤務時間:**

| 値           | 意味         |
|------------|------------|
| `67_tim_67`| 1日1・2h以内OK |
| `4_tim_4`  | 1日4h以内OK   |
| `68_tim_68`| 1日6h以内OK   |

**勤務時間制限:**

| 値           | 意味          |
|------------|-------------|
| `76_knm_76`| 9時以降勤務OK  |
| `73_knm_73`| 10時以降勤務OK |
| `74_knm_74`| 16時前退社OK  |
| `75_knm_75`| 17時前退社OK  |

**休日:**

| 値           | 意味              |
|------------|-----------------|
| `72_smr_72`| 完全週休二日制       |
| `44_smr_44`| 土日祝休み          |
| `71_smr_71`| 家庭都合のお休み調整可   |
| `22_smr_22`| 土日祝のみOK       |
| `45_smr_45`| 春夏冬休み限定       |

**残業:**

| 値           | 意味              |
|------------|-----------------|
| `77_otw_77`| 残業なし            |
| `78_otw_78`| 残業少なめ(月20h未満) |
| `79_otw_79`| 残業多め(月20h〜)   |

### ソート `jobsort`

| 値         | 意味    |
|-----------|-------|
| `osusume` | おすすめ  |
| `new`     | 新着順   |

---

## HTMLスクレイピング仕様

### 求人一覧ページ

各求人は `<article class="list-jobListDetail">` 要素内に格納。

```
<article class="list-jobListDetail">
  <div class="pt02b">
    <p>職場説明文</p>
    <ul class="ul01">
      <li>アルバイト・パート</li>  ← 雇用形態タグ
    </ul>
    <ul class="ul02">
      <li>[勤務地・面接地] 東京都港区 / 新橋駅</li>
    </ul>
    <h3><a href="/kanto/jlist/.../job{ID}/">
      <span>求人タイトル</span>
    </a></h3>
  </div>
  <div class="pt03">
    <dl>
      <dt>給与</dt>
      <dd>[ア・パ] 時給1,400円〜</dd>
    </dl>
    <dl>
      <dt>職種</dt>
      <dd>ホールスタッフ...</dd>
    </dl>
  </div>
</article>
```

**件数:** ページ内の `(\d[\d,]+)件` パターンから最初のマッチ

### 求人詳細ページURL

求人IDからURLを解決する方法（IDだけではURLを構築できない）:

```
1. GET /kanto/jlist/wrd{JOB_ID}/ でHTMLを取得
2. href から /...job{JOB_ID}/ のパターンを抽出
3. その絶対URLで詳細ページを取得
```

**応募URL:** `https://www.baitoru.com/entry/form/job{JOB_ID}/`

---

## 重要な注意点

1. **reqType の違い**: トップページのフォームは `reqType=33`、検索結果ページのフォームは `reqType=11` を使うが、どちらも `createurl` エンドポイントで動作する。統一して `reqType=33` を推奨。

2. **フィールド名の違い**: `createurl` では `midAreaCd`（キャメルケース）、AJAX APIでは `mid_area_cd`（スネークケース）と異なる。

3. **給与額の有効値**: 自由入力ではなく離散値のリスト。無効値を渡すと0件になる。

4. **URLのpname**: リダイレクト先URLに `?pname=search_fw` が付くが、検索結果の取得には不要。

5. **robots/スクレイピング**: 一般的なUser-Agentと適切なRefererヘッダーが必要。

---

## CLI ツール構成

```
job-finder/
├── baitoru.py      # メインCLI
├── baitoru         # シェルラッパー
├── .venv/          # Python仮想環境 (requests, beautifulsoup4)
└── API_ANALYSIS.md # このドキュメント
```

### コマンド一覧

```bash
# 求人検索
./baitoru search {キーワード} [オプション]

# 求人件数取得（AJAX API直接）
./baitoru count [オプション]

# 求人詳細表示
./baitoru detail {job_id}

# フィルター一覧表示
./baitoru filters
```
