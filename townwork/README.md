# タウンワーク CLI

[タウンワーク](https://townwork.net/) のバイト求人をコマンドラインで検索するツール。  
Playwright MCPでバックグラウンドAPIを解析し、ヘッドレスブラウザ経由で動作する。

## インストール

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/playwright install chromium
```

## 使い方

### 求人を検索する

```bash
# キーワード検索
.venv/bin/tw search --keyword カフェ --prefecture tokyo

# エリア + 条件を組み合わせ
.venv/bin/tw search --keyword バリスタ \
  --prefecture tokyo \
  --employment 01 \
  --preference 0401 \
  --min-salary 1500

# 駅で検索（コードは tw stations で調べる）
.venv/bin/tw search --station 3975   # 新宿駅周辺

# ページを指定
.venv/bin/tw search --keyword カフェ --page 2

# JSON で出力（jq と組み合わせ可）
.venv/bin/tw search --keyword カフェ --json | jq '.[].title'
```

### 駅コードを調べる

```bash
# 駅名で絞り込み
.venv/bin/tw stations 新宿
.venv/bin/tw stations 渋谷 --prefecture tokyo

# 大阪の駅を検索
.venv/bin/tw stations 梅田 --prefecture osaka
```

### キーワード補助

```bash
# サジェスト
.venv/bin/tw suggest カフェ

# 件数を確認
.venv/bin/tw count IT --prefecture osaka
```

### フィルターコード一覧を見る

```bash
# すべて表示
.venv/bin/tw list-filters

# カテゴリを絞って表示
.venv/bin/tw list-filters --category preference   # 条件コード
.venv/bin/tw list-filters --category occupation   # 職種コード
.venv/bin/tw list-filters --category salary       # 給与コード

# 都道府県コード
.venv/bin/tw list-prefectures
```

## 主なオプション一覧

| オプション | 説明 | 例 |
|---|---|---|
| `--prefecture` `-p` | 都道府県 | `tokyo`, `osaka`, `kanagawa` |
| `--keyword` `-k` | キーワード | `カフェ`, `IT`, `データ入力` |
| `--area` `-a` | 市区町村コード | `013001`（東京23区）|
| `--sub-area` `-s` | 小地域コード | `013001004`（新宿区）|
| `--station` | 駅コード | `3975`（新宿駅）|
| `--employment` `-e` | 雇用形態 | `01`=アルバイト, `02`=正社員 |
| `--occupation` `-o` | 職種コード | `001`=飲食, `013`=IT |
| `--sub-occupation` | サブ職種コード | `0001`=ホール, `0002`=キッチン |
| `--preference` | 条件コード | `0401`=日払い, `0602`=学生歓迎 |
| `--min-salary` `-m` | 給与下限（円） | `1500`（時給）, `8000`（日給）, `200000`（月給）|
| `--max-salary` | 給与上限（円） | `2000` |
| `--sort` | ソート順 | `1`=新着順（デフォルト）, `3`=関連度順 |
| `--page` | ページ番号（0始まり） | `0`, `1`, `2` |
| `--limit` `-l` | 表示件数（最大20） | `5`, `10` |
| `--json` | JSON形式で出力 | — |

## よく使う条件コード

```
# 期間
0101=短期  0102=単発・1日OK  0103=長期

# 曜日
0201=土日祝のみ  0202=平日のみ  0203=週1からOK  0204=週2・3日からOK

# 時間帯
0301=早朝  0302=昼  0303=夕方から  0304=夜から  0305=深夜

# 給与
0401=日払い  0402=週払い  0404=給料前払い  0408=扶養内OK

# 対象者
0601=高校生歓迎  0602=学生歓迎  0603=フリーター歓迎
0604=未経験OK  0607=副業・WワークOK

# 外見・服装
0710=髪型自由  0713=ひげOK  0714=ネイルOK  0715=ピアスOK

# 応募
0801=履歴書不要  0803=入社祝い金  0804=即日勤務OK  0806=急募
```

## 技術仕様

サイトは AWS WAF によるボット対策を実施しており、`curl` や通常の HTTP クライアントではアクセス不可。  
本ツールは Playwright のヘッドレス Chromium を使い、ページの `__NEXT_DATA__` JSON からデータを取得している。

詳細なAPI仕様・全フィルターコードは [API_SPEC.md](API_SPEC.md) を参照。
