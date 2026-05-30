"""タウンワーク CLI"""

import click
from rich.console import Console
from rich.table import Table
from rich import box
from rich.text import Text
from . import api

console = Console()

PREFECTURE_NAMES = {
    "hokkaido": "北海道", "aomori": "青森", "iwate": "岩手", "miyagi": "宮城",
    "akita": "秋田", "yamagata": "山形", "fukushima": "福島", "ibaraki": "茨城",
    "tochigi": "栃木", "gunma": "群馬", "saitama": "埼玉", "chiba": "千葉",
    "tokyo": "東京", "kanagawa": "神奈川", "niigata": "新潟", "toyama": "富山",
    "ishikawa": "石川", "fukui": "福井", "yamanashi": "山梨", "nagano": "長野",
    "gifu": "岐阜", "shizuoka": "静岡", "aichi": "愛知", "mie": "三重",
    "shiga": "滋賀", "kyoto": "京都", "osaka": "大阪", "hyogo": "兵庫",
    "nara": "奈良", "wakayama": "和歌山", "tottori": "鳥取", "shimane": "島根",
    "okayama": "岡山", "hiroshima": "広島", "yamaguchi": "山口", "tokushima": "徳島",
    "kagawa": "香川", "ehime": "愛媛", "kochi": "高知", "fukuoka": "福岡",
    "saga": "佐賀", "nagasaki": "長崎", "kumamoto": "熊本", "oita": "大分",
    "miyazaki": "宮崎", "kagoshima": "鹿児島", "okinawa": "沖縄",
}


@click.group()
@click.version_option("1.1.0")
def main():
    """タウンワーク CLI - コマンドラインで求人を検索"""
    pass


@main.command()
@click.option("--prefecture", "-p", default="tokyo", show_default=True,
              help="都道府県 (例: tokyo, osaka, kanagawa)")
@click.option("--keyword", "-k", default=None, help="検索キーワード (例: カフェ, IT)")
@click.option("--area", "-a", default=None, help="市区町村コード (例: 013001 / ma-013001)")
@click.option("--sub-area", "-s", default=None, help="小地域コード (例: 013001004 / sa-013001004)")
@click.option("--station", default=None,
              help="駅コード (例: 8714=東京駅 / st-8714)。tw stations で検索")
@click.option("--employment", "-e", default=None,
              help="雇用形態: 01=アルバイト 02=正社員 03=契約 04=派遣 05=委託")
@click.option("--occupation", "-o", default=None,
              help="職種コード (例: 001=飲食 006=事務 013=IT)。tw list-filters で一覧表示")
@click.option("--sub-occupation", default=None,
              help="サブ職種コード (例: 0001=ホール 0002=キッチン)。tw list-filters で一覧表示")
@click.option("--preference", default=None,
              help="条件コード (例: 0401=日払い 0602=学生歓迎)。tw list-filters で一覧表示")
@click.option("--min-salary", "-m", type=int, default=None,
              help="給与下限: 時給は円(例: 1200), 日給(例: 8000), 月給(例: 200000)")
@click.option("--max-salary", type=int, default=None,
              help="給与上限: 時給は円(例: 2000), 日給(例: 15000), 月給(例: 300000)")
@click.option("--sort", default="1", show_default=True,
              type=click.Choice(["1", "3"]), help="ソート: 1=新着順 3=関連度順")
@click.option("--page", default=0, show_default=True, help="ページ番号 (0始まり)")
@click.option("--limit", "-l", default=20, show_default=True, help="表示件数 (最大20)")
@click.option("--json", "output_json", is_flag=True, help="JSON形式で出力")
def search(prefecture, keyword, area, sub_area, station, employment, occupation,
           sub_occupation, preference, min_salary, max_salary, sort, page, limit,
           output_json):
    """求人を検索する"""

    def _normalize(val, prefix):
        if val and not val.startswith(prefix):
            return f"{prefix}{val}"
        return val

    with console.status("[bold green]検索中...[/]"):
        try:
            result = api.search(
                prefecture=prefecture,
                keyword=keyword,
                area=_normalize(area, "ma-"),
                sub_area=_normalize(sub_area, "sa-"),
                station=_normalize(station, "st-"),
                employment=_normalize(employment, "emp-"),
                occupation=_normalize(occupation, "oc-"),
                sub_occupation=_normalize(sub_occupation, "omc-"),
                preference=_normalize(preference, "prf-"),
                min_salary=min_salary,
                max_salary=max_salary,
                sort=sort,
                page=page,
            )
        except Exception as e:
            console.print(f"[red]エラー: {e}[/]")
            raise SystemExit(1)

    jobs = result.get("jobCards", [])[:limit]
    total = result.get("recordInfo", {}).get("totalCount", "不明")
    current_page = result.get("pageInfo", {}).get("currentPage", page)
    next_pages = result.get("pageInfo", {}).get("nextPages", [])

    if output_json:
        import json as json_mod
        click.echo(json_mod.dumps(result, ensure_ascii=False, indent=2))
        return

    pref_name = PREFECTURE_NAMES.get(prefecture, prefecture)
    console.print(f"\n[bold]タウンワーク求人検索[/] - {pref_name}", highlight=False)
    if keyword:
        console.print(f"キーワード: [cyan]{keyword}[/]")
    console.print(f"検索結果: [bold yellow]{total}[/]  ページ: {current_page + 1}")
    console.print()

    if not jobs:
        console.print("[yellow]求人が見つかりませんでした。[/]")
        return

    table = Table(box=box.ROUNDED, expand=True, show_lines=True)
    table.add_column("#", style="dim", width=3, no_wrap=True)
    table.add_column("タイトル", style="bold", min_width=20)
    table.add_column("会社名", min_width=15)
    table.add_column("給与", style="green", min_width=12)
    table.add_column("勤務地", min_width=12)
    table.add_column("雇用形態", min_width=8)

    for i, job in enumerate(jobs, 1):
        title = job.get("title", "")
        subtitle = job.get("subTitle", "")
        employer = job.get("employerName", "")
        salary = job.get("salary", "")
        location = job.get("workLocation", "").replace("東京都東京23区", "東京23区")
        job_types = ", ".join(job.get("jobType", []))

        title_cell = Text(title, overflow="fold")
        if subtitle:
            title_cell.append(
                f"\n{subtitle[:60]}{'...' if len(subtitle) > 60 else ''}",
                style="dim",
            )

        table.add_row(str(i), title_cell, employer, salary, location, job_types)

    console.print(table)

    if next_pages:
        nums = [str(p["pageNum"] + 1) for p in next_pages[:3]]
        console.print(f"\n次のページ: {', '.join(nums)}  (--page オプションで指定)")
    console.print()


@main.command()
@click.argument("keyword")
@click.option("--prefecture", "-p", default="tokyo", show_default=True)
def suggest(keyword, prefecture):
    """キーワードのサジェストを表示する"""
    with console.status("[bold green]サジェスト取得中...[/]"):
        try:
            suggestions = api.suggest(keyword, prefecture)
        except Exception as e:
            console.print(f"[red]エラー: {e}[/]")
            raise SystemExit(1)

    if not suggestions:
        console.print("[yellow]サジェストが見つかりませんでした。[/]")
        return

    console.print(f"\n[bold]「{keyword}」のサジェスト:[/]\n")
    for s in suggestions:
        console.print(f"  • {s}")
    console.print()


@main.command()
@click.argument("keyword")
@click.option("--prefecture", "-p", default="tokyo", show_default=True)
def count(keyword, prefecture):
    """キーワードの求人件数を表示する"""
    with console.status("[bold green]件数取得中...[/]"):
        try:
            result = api.hit_count(keyword, prefecture)
        except Exception as e:
            console.print(f"[red]エラー: {e}[/]")
            raise SystemExit(1)

    total = result.get("estimatedTotalResultsCount", 0)
    count_type = result.get("estimatedTotalResultsCountType", "")
    prefix = "約" if count_type == "AT_LEAST" else ""
    pref_name = PREFECTURE_NAMES.get(prefecture, prefecture)
    console.print(
        f"\n[bold]{pref_name}[/] の「[cyan]{keyword}[/]」求人件数: "
        f"[bold yellow]{prefix}{total:,}件[/]\n"
    )


@main.command()
@click.argument("query", required=False, default=None)
@click.option("--prefecture", "-p", default="tokyo", show_default=True,
              help="都道府県")
def stations(query, prefecture):
    """駅コードを検索する (QUERY: 駅名の一部)

    例: tw stations 新宿
        tw stations --prefecture osaka 梅田
    """
    pref_name = PREFECTURE_NAMES.get(prefecture, prefecture)
    with console.status(f"[bold green]{pref_name}の駅一覧を取得中...[/]"):
        try:
            station_list = api.list_stations(prefecture)
        except Exception as e:
            console.print(f"[red]エラー: {e}[/]")
            raise SystemExit(1)

    if query:
        station_list = [s for s in station_list if query in s["label"] or query in s["line"]]

    if not station_list:
        console.print(f"[yellow]「{query}」に該当する駅が見つかりませんでした。[/]")
        return

    console.print(f"\n[bold]{pref_name}の駅一覧[/]"
                  + (f" (「{query}」で絞り込み)" if query else "") + "\n")

    table = Table(box=box.SIMPLE)
    table.add_column("コード (--station)", style="cyan", no_wrap=True)
    table.add_column("駅名", style="bold")
    table.add_column("路線")
    table.add_column("市区町村(ma)", style="dim")

    for s in station_list[:200]:
        table.add_row(s["id"], s["label"], s["line"], s.get("ma", ""))

    console.print(table)
    if len(station_list) > 200:
        console.print(f"[dim]... 他 {len(station_list) - 200} 件（キーワードで絞り込んでください）[/]")
    console.print()


@main.command("list-prefectures")
def list_prefectures():
    """都道府県コード一覧を表示する"""
    console.print("\n[bold]都道府県コード一覧:[/]\n")
    table = Table(box=box.SIMPLE)
    table.add_column("コード (--prefecture)", style="cyan")
    table.add_column("都道府県")
    for code, name in PREFECTURE_NAMES.items():
        table.add_row(code, name)
    console.print(table)


@main.command("list-filters")
@click.option("--category", "-c", default=None,
              type=click.Choice(["employment", "occupation", "sub-occupation",
                                 "preference", "salary"]),
              help="特定カテゴリのみ表示")
def list_filters(category):
    """フィルタコード一覧を表示する"""

    show_all = category is None

    if show_all or category == "employment":
        console.print("\n[bold cyan]雇用形態 (--employment):[/]")
        for code, name in [
            ("01", "アルバイト・パート"), ("02", "正社員"), ("03", "契約社員"),
            ("04", "派遣社員"), ("05", "業務委託"),
        ]:
            console.print(f"  {code}: {name}")

    if show_all or category == "occupation":
        console.print("\n[bold cyan]職種カテゴリ (--occupation):[/]")
        for code, name in [
            ("001", "飲食・フードサービス"), ("002", "営業・販売"),
            ("003", "旅行・レジャー・イベント"), ("004", "倉庫・物流管理"),
            ("005", "警備・保安"), ("006", "経営・事業企画・人事・事務"),
            ("007", "マーケティング・広告・宣伝"), ("008", "保育士・教員・講師"),
            ("009", "ドライバー・引越し・配送"), ("010", "介護・福祉"),
            ("011", "医療・看護師・薬剤師"), ("012", "メディア・クリエイター"),
            ("013", "IT・Web・ゲームエンジニア"), ("014", "エンジニアリング・設計開発"),
            ("015", "整備・修理"), ("016", "清掃・美化"),
            ("017", "ビューティー・生活サービス"), ("018", "建設・土木・施工"),
            ("019", "製造・工場"), ("020", "金融・財務・会計"),
            ("021", "法務・法律"), ("022", "研究"), ("023", "農林漁業"),
        ]:
            console.print(f"  {code}: {name}")

    if show_all or category == "sub-occupation":
        console.print("\n[bold cyan]サブ職種 (--sub-occupation) ※抜粋:[/]")
        for code, name in [
            # 飲食 (oc-001)
            ("0001", "ホールスタッフ"), ("0002", "キッチンスタッフ"), ("0003", "皿洗い・洗い場"),
            ("0004", "精肉・鮮魚加工"), ("0005", "給食調理"), ("0006", "パン屋（ベーカリー）"),
            ("0007", "フードカウンター販売員"), ("0008", "バー（BAR）・バーテンダー"),
            # 営業・販売 (oc-002)
            ("0011", "営業"), ("0012", "テレフォンアポインター"),
            ("0014", "コンビニ"), ("0015", "アパレル"),
            ("0016", "家電量販店・携帯販売"), ("0019", "その他販売"),
            # 倉庫 (oc-004)
            ("0024", "ピッキング"), ("0025", "検品"), ("0026", "梱包"),
            ("0027", "倉庫内仕分け"), ("0028", "在庫管理"),
            # 事務 (oc-006)
            ("0037", "営業事務"), ("0039", "その他事務"), ("0040", "データ入力・PC入力"),
            ("0041", "受付"), ("0042", "コールセンター・テレオペ"),
        ]:
            console.print(f"  {code}: {name}")
        console.print("  [dim](全151コード。oc-{コード} のサブ項目はサイトで確認)[/]")

    if show_all or category == "preference":
        console.print("\n[bold cyan]条件コード (--preference):[/]")
        groups = [
            ("期間", [
                ("0101", "短期"), ("0102", "単発・1日OK"), ("0103", "長期"),
                ("0104", "期間限定（春夏冬休み等）"),
            ]),
            ("曜日・日数", [
                ("0201", "土日祝のみOK"), ("0202", "平日のみOK"),
                ("0203", "週1日からOK"), ("0204", "週2・3日からOK"),
                ("0205", "週4日以上OK"), ("0206", "シフト自由"),
                ("0207", "固定シフト制"), ("0208", "シフト制"),
                ("0209", "月1シフト提出"), ("0210", "隔週シフト提出"),
                ("0211", "週1シフト提出"), ("0212", "変形労働時間制"),
            ]),
            ("時間帯", [
                ("0301", "早朝・朝の仕事"), ("0302", "昼の仕事"),
                ("0303", "夕方からの仕事"), ("0304", "夜からの仕事"),
                ("0305", "深夜の仕事"), ("0306", "1日4時間以内OK"),
                ("0307", "フルタイム歓迎"), ("0308", "残業なし"),
            ]),
            ("給与", [
                ("0401", "日払いOK"), ("0402", "週払いOK"),
                ("0403", "ボーナス・賞与あり"), ("0404", "給料前払いOK"),
                ("0405", "現金払いOK"), ("0406", "完全歩合制"),
                ("0407", "昇給あり"), ("0408", "扶養内勤務OK"),
            ]),
            ("待遇・環境", [
                ("0501", "交通費支給"), ("0502", "まかない・食事補助あり"),
                ("0503", "社割あり"), ("0504", "研修あり"),
                ("0505", "資格取得支援または手当あり"), ("0506", "社員登用あり"),
                ("0507", "送迎あり"), ("0508", "寮・社宅・住宅手当あり"),
                ("0509", "託児所あり"), ("0510", "育児サポートあり"),
                ("0511", "家庭都合休OK"), ("0512", "産休・育休取得制度あり"),
                ("0513", "長期休暇あり"), ("0514", "無期雇用派遣"),
                ("0515", "転勤なし"), ("0516", "職種変更なし"), ("0517", "社会保険あり"),
            ]),
            ("対象者", [
                ("0601", "高校生歓迎"), ("0602", "学生歓迎"), ("0603", "フリーター歓迎"),
                ("0604", "未経験・初心者OK"), ("0605", "経験者・有資格者歓迎"),
                ("0606", "主婦・主夫歓迎"), ("0607", "副業・WワークOK"),
                ("0608", "ブランクOK"), ("0609", "学歴不問"),
                ("0612", "60代（シニア）も応募可"), ("0613", "70代（シニア）も応募可"),
                ("0614", "留学生・外国人活躍中"),
            ]),
            ("服装・外見", [
                ("0701", "オープニングスタッフ"), ("0702", "駅チカ・駅ナカ"),
                ("0703", "バイク通勤OK"), ("0704", "車通勤OK"),
                ("0705", "リゾート"), ("0706", "英語が活かせる"),
                ("0707", "中国語が活かせる"), ("0708", "フルリモート（完全在宅）"),
                ("0709", "在宅OK"), ("0710", "髪型・髪色自由"),
                ("0711", "服装自由"), ("0712", "制服あり"),
                ("0713", "ひげOK"), ("0714", "ネイルOK"), ("0715", "ピアスOK"),
            ]),
            ("応募", [
                ("0801", "履歴書不要"), ("0802", "面接なし"),
                ("0803", "入社祝い金あり"), ("0804", "即日勤務OK"),
                ("0805", "大量募集"), ("0806", "急募"),
                ("0807", "友達と応募OK"), ("0808", "職場見学可"),
            ]),
        ]
        for group_name, codes in groups:
            console.print(f"  [dim]── {group_name} ──[/]")
            for code, name in codes:
                console.print(f"  {code}: {name}")

    if show_all or category == "salary":
        console.print("\n[bold cyan]給与コード (--min-salary / --max-salary):[/]")
        console.print("  [dim]時給 (円):[/]  1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 2000, 2100, 2200, 2300, 2400, 2500")
        console.print("  [dim]日給 (円):[/]  6500, 7000, 7500, 8000, 9000, 10000, 11000, 12000, 13000, 14000, 15000, 16000, 17000, 18000, 19000, 20000")
        console.print("  [dim]月給 (円):[/]  150000〜300000 (1万円単位)")
        console.print("  [dim]例: --min-salary 1500  --max-salary 2000[/]")
    console.print()
