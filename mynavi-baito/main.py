#!/usr/bin/env python3
"""マイナビバイト CLI

使い方:
  python3 main.py search --pref 13 --occupation 1
  python3 main.py search --pref 13 --word カフェ --sort WAGE_HOURLY
  python3 main.py search --pref 13 --wage-id 14 --period 201
  python3 main.py detail J0134106676
  python3 main.py areas --pref 13
  python3 main.py occupations
  python3 main.py routes --pref 13
  python3 main.py brands --keyword タリーズ
  python3 main.py kodawari
  python3 main.py suggest カフェ
"""

import sys
import json
import argparse

import api as mynavi


# ── フォーマットヘルパー ─────────────────────────────────────

def fmt_wage(wage: dict) -> str:
    if not wage:
        return "情報なし"
    special = wage.get("specialWageAmount")
    if special:
        return special
    label = wage.get("label", "")
    amount = wage.get("wageAmount", 0)
    return f"{label}{amount:,}円"


def fmt_access(access: dict) -> str:
    company = access.get("routeCompany", {}).get("label", "")
    line = access.get("routeLine", {}).get("label", "")
    station = access.get("routeStation", {}).get("name", "")
    traffic = access.get("trafficFacilitiesDiv", {}).get("label", "")
    minutes = access.get("timeRequired", "")
    parts = [p for p in [company, line, f"{station}駅", f"{traffic}{minutes}分"] if p.strip()]
    return " ".join(parts)


def print_job_summary(job: dict, idx: int = None) -> None:
    prefix = f"[{idx}] " if idx is not None else ""
    cd = job.get("jobStockCd", "")
    name = job.get("recruitmentOccupationName", "")
    appeal = job.get("recruitmentAppealPoint", "")
    wage = fmt_wage(job.get("wage", {}))
    new_flg = "🆕 " if job.get("newFlg") else ""
    close_soon = "⚠️  " if job.get("closeSoonFlg") else ""

    shops = job.get("shopList", [])
    client = job.get("clientName", "")
    location = ""
    access = ""
    if shops:
        shop = shops[0]
        area2 = shop.get("area2nd", {}).get("label", "")
        area3 = shop.get("area3rd", {}).get("label", "")
        location = f"{area2} {area3}".strip()
        if shop.get("accessList"):
            access = fmt_access(shop["accessList"][0])

    print(f"{prefix}{new_flg}{close_soon}{name}")
    print(f"  求人CD  : {cd}")
    print(f"  店舗    : {client}")
    print(f"  場所    : {location}")
    print(f"  アクセス: {access}")
    print(f"  給与    : {wage}")
    if appeal:
        print(f"  アピール: {appeal[:80]}{'…' if len(appeal) > 80 else ''}")
    print()


# ── コマンド: search ────────────────────────────────────────

def cmd_search(args):
    occupation_ids = args.occupation.split(",") if args.occupation else None
    area_ids = args.area.split(",") if args.area else None
    route_ids = args.route.split(",") if args.route else None
    kodawari_ids = [int(x) for x in args.kodawari.split(",")] if args.kodawari else None
    period_ids = [int(x) for x in args.period.split(",")] if args.period else None
    timezone_ids = [int(x) for x in args.timezone.split(",")] if args.timezone else None
    employee_ids = [int(x) for x in args.employee.split(",")] if args.employee else None
    season_ids = [int(x) for x in args.season.split(",")] if args.season else None
    words = args.word.split(",") if args.word else None
    excluded = args.exclude.split(",") if args.exclude else None

    result = mynavi.search_jobs(
        # 場所
        prefecture_id=args.pref,
        area_id_list=area_ids,
        route_id_list=route_ids,
        # 職種・ブランド
        occupation_id_list=occupation_ids,
        brand_id=args.brand,
        client_cd=args.client,
        # フリーワード
        words=words,
        excluded_words=excluded,
        # こだわり
        wage_id=args.wage_id,
        prefecture_high_wage=args.high_wage,
        kodawari_id_list=kodawari_ids,
        period_id_list=period_ids,
        working_timezone_id_list=timezone_ids,
        shift_id=args.shift,
        employee_id_list=employee_ids,
        season_id_list=season_ids,
        # その他
        exclude_no_highschool=args.no_highschool,
        # リクエスト
        page=args.page,
        sort=args.sort,
        reserve_flg=args.reserve,
    )

    total = result.get("searchCount", 0)
    jobs = result.get("jobList", [])
    print(f"=== 検索結果: {total:,}件 (表示: {len(jobs)}件, page={args.page}) ===\n")

    for i, job in enumerate(jobs, 1):
        print_job_summary(job, i)

    if args.json:
        print("\n--- JSON出力 ---")
        print(json.dumps(result, ensure_ascii=False, indent=2))


# ── コマンド: detail ────────────────────────────────────────

def cmd_detail(args):
    result = mynavi.get_job_detail(args.job_cd)
    job = result.get("jobDetail", {})

    if args.json:
        print(json.dumps(job, ensure_ascii=False, indent=2))
        return

    print(f"=== 求人詳細: {args.job_cd} ===\n")
    print(f"職種名  : {job.get('recruitmentOccupationName', '')}")
    print(f"店舗名  : {job.get('clientName', '')}")
    print(f"給与    : {fmt_wage(job.get('wage', {}))}")

    wage = job.get("wage", {})
    if wage.get("note"):
        for line in wage["note"].strip().splitlines():
            print(f"  {line}")

    print(f"\n【アピールポイント】")
    print(job.get("recruitmentAppealPoint", ""))

    content = job.get("jobOfferContent") or job.get("recruitmentDescription", "")
    if content:
        print(f"\n【仕事内容】")
        print(content[:500] + ("…" if len(content) > 500 else ""))

    shift = job.get("shift", {})
    if shift:
        lists = shift.get("list", [])
        labels = ", ".join(s.get("label", "") for s in lists)
        print(f"\n【シフト】{labels}")
        if shift.get("note"):
            print(f"  {shift['note']}")

    period = job.get("period", {})
    if period:
        labels = ", ".join(p.get("label", "") for p in period.get("list", []))
        print(f"\n【期間】{labels}")
        if period.get("note"):
            print(f"  {period['note']}")

    wt = job.get("workingTimePerDay")
    if wt and wt.get("note"):
        print(f"\n【勤務時間】{wt['note']}")

    employee = job.get("employeeFigure", {})
    if employee:
        print(f"\n【雇用形態】{employee.get('label', '')}")

    travel = job.get("travelExpensesSupply", {})
    if travel:
        print(f"\n【交通費】{travel.get('label', '')}")
        if travel.get("note"):
            print(f"  {travel['note']}")

    kodawari = job.get("kodawariList", [])
    if kodawari:
        labels = " / ".join(k.get("label", "") for k in kodawari)
        print(f"\n【こだわり】{labels}")

    shops = job.get("shopList", [])
    for shop in shops:
        print(f"\n【店舗】{shop.get('clientShopName', '')}")
        addr_parts = [shop.get("locationPrefecture", ""), shop.get("locationSikugun", ""),
                      shop.get("locationAddress1", "")]
        addr = " ".join(p for p in addr_parts if p)
        if addr:
            print(f"  住所: {addr}")
        for acc in shop.get("accessList", []):
            print(f"  アクセス: {fmt_access(acc)}")


# ── コマンド: areas ─────────────────────────────────────────

def cmd_areas(args):
    result = mynavi.get_area_list(
        area_id=str(args.pref) if args.pref else None,
        depth=args.depth
    )
    areas = result.get("areaList", [])

    def print_area(a, indent=0):
        label = a.get("label", "")
        area_id = a.get("areaId", "")
        print(f"{'  ' * indent}{area_id}: {label}")
        for child in a.get("areaList", []):
            print_area(child, indent + 1)

    print("=== エリア一覧 ===")
    for area in areas:
        print_area(area)


# ── コマンド: occupations ───────────────────────────────────

def cmd_occupations(args):
    result = mynavi.get_occupation_list(depth=args.depth)
    occupations = result.get("occupationList", [])

    def print_occ(o, indent=0):
        label = o.get("label", "")
        occ_id = o.get("occupationId", "")
        print(f"{'  ' * indent}{occ_id}: {label}")
        for child in o.get("occupationList", []):
            print_occ(child, indent + 1)

    print("=== 職種一覧 ===")
    for occ in occupations:
        print_occ(occ)


# ── コマンド: routes ────────────────────────────────────────

def cmd_routes(args):
    result = mynavi.get_route_list(area_id=str(args.pref or 13), depth=args.depth)
    pref_list = result.get("routeList", [])

    print(f"=== 路線一覧 (都道府県ID: {args.pref or 13}) ===")
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    def print_route(r, indent=0):
        rid = r.get("routeId", "")
        label = r.get("label", "")
        print(f"{'  ' * indent}{rid}: {label}")
        for child in r.get("routeList", []):
            print_route(child, indent + 1)

    for r in pref_list:
        print_route(r)


# ── コマンド: brands ────────────────────────────────────────

def cmd_brands(args):
    result = mynavi.get_company_brand_list()
    groups = result.get("companyBrandGroupList", [])

    keyword = args.keyword.lower() if args.keyword else None
    print("=== 企業ブランド一覧 ===")
    for group in groups:
        char = group.get("initialChar", "")
        brands = group.get("companyBrandList", [])
        if keyword:
            brands = [b for b in brands if keyword in b.get("companyBrandName", "").lower()]
        if brands:
            print(f"\n【{char}】")
            for b in brands:
                print(f"  {b['companyBrandId']}: {b['companyBrandName']}")


# ── コマンド: kodawari ──────────────────────────────────────

def cmd_kodawari(args):
    result = mynavi.get_kodawari_list()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    def show_list(title, items, id_key="id", label_key="label"):
        print(f"\n【{title}】")
        for item in items:
            print(f"  {item[id_key]}: {item[label_key]}")

    show_list("雇用形態 (--employee)", result.get("employee", []))
    show_list("勤務期間 (--period)", result.get("period", []))
    show_list("シフト/週勤務日数 (--shift)", result.get("shift", []))
    show_list("勤務時間帯 (--timezone)", result.get("workingTimezone", []))
    show_list("季節限定 (--season)", result.get("season", []))

    print("\n【給与条件 (--wage-id 'WAGE1ST-WAGE2ND')】")
    for w1 in result.get("wage1st", []):
        print(f"  {w1['id']}: {w1['label']}")
        for w2 in w1.get("wage2nd", []):
            print(f"    --wage-id {w1['id']}-{w2['id']}: {w1['label']}{w2['label']}")

    print("\n【こだわり条件 (--kodawari)】")
    for k in result.get("kodawari", []):
        print(f"  {k['id']}: {k['label']}")


# ── コマンド: suggest ───────────────────────────────────────

def cmd_suggest(args):
    result = mynavi.suggest(args.keyword, prefecture_id=args.pref or 13)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    suggests = result.get("suggestList", [])
    print(f"=== サジェスト: '{args.keyword}' ===")
    for s in suggests:
        kw_list = s.get("selectedKeywordList", [])
        if kw_list:
            kw = kw_list[0].get("keyword", "")
            category = kw_list[0].get("category", "")
            print(f"  {kw}  [{category}]")


# ── コマンド: notices ───────────────────────────────────────

def cmd_notices(args):
    result = mynavi.get_notice_list()
    notices = result.get("noticeList", [])
    print("=== お知らせ ===")
    for n in notices:
        date = n.get("publicationStartDateString", "")[:10]
        title = n.get("title", "")
        nid = n.get("noticeUserId", "")
        print(f"[{date}] {title} (ID: {nid})")


# ── メインパーサー ──────────────────────────────────────────

def build_parser():
    parser = argparse.ArgumentParser(
        description="マイナビバイト CLI - バックグラウンドAPIを直接操作",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  # 東京の飲食系 新着順
  python3 main.py search --pref 13 --occupation 1

  # 時給1300円以上（wage-id=14）・未経験歓迎（kodawari=9）・週2日以上（shift=4）
  python3 main.py search --pref 13 --wage-id 14 --kodawari 9 --shift 4

  # キーワード「カフェ」・除外「夜勤」・時給高い順
  python3 main.py search --pref 13 --word カフェ --exclude 夜勤 --sort WAGE_HOURLY

  # 長期（period=201）・アルバイト（employee=1）・昼（timezone=2）
  python3 main.py search --pref 13 --period 201 --employee 1 --timezone 2

  # 企業ブランド（タリーズID=216）で検索
  python3 main.py search --brand 216

  # フィルターIDを確認
  python3 main.py kodawari

  # 求人詳細
  python3 main.py detail J0134106676

  # エリア一覧（東京・3階層）
  python3 main.py areas --pref 13 --depth 3

  # 路線一覧（東京・路線レベル）
  python3 main.py routes --pref 13 --depth 3
""",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── search ──────────────────────────────────────────────
    p = sub.add_parser("search", help="求人検索（全フィルター対応）")

    loc = p.add_argument_group("場所条件")
    loc.add_argument("--pref", type=int, metavar="ID", help="都道府県ID (例: 13=東京, 27=大阪)")
    loc.add_argument("--area", metavar="ID[,ID...]",
                     help="エリアID カンマ区切り (例: 13-651-35=新宿区)")
    loc.add_argument("--route", metavar="ID[,ID...]",
                     help="路線ID カンマ区切り (例: 13-6-25=山手線)")

    job = p.add_argument_group("職種・企業条件")
    job.add_argument("--occupation", "-o", metavar="ID[,ID...]",
                     help="職種ID カンマ区切り (例: 1=飲食, 1-1=カフェ, 3=販売)")
    job.add_argument("--brand", type=int, metavar="ID",
                     help="企業ブランドID (brandsコマンドで確認)")
    job.add_argument("--client", metavar="CD",
                     help="企業コード")

    kw = p.add_argument_group("キーワード条件")
    kw.add_argument("--word", "-w", metavar="ワード[,ワード...]",
                    help="フリーワード カンマ区切り (例: カフェ,接客)")
    kw.add_argument("--exclude", metavar="ワード[,ワード...]",
                    help="除外ワード カンマ区切り")

    kd = p.add_argument_group("こだわり条件（kodawariコマンドでID確認）")
    kd.add_argument("--wage-id", metavar="WAGE1ST-WAGE2ND",
                    help='給与条件ID (例: "1-14"=時給1300円以上, "2-5"=日給8000円以上, "3-7"=月給20万円以上)')
    kd.add_argument("--high-wage", action="store_true",
                    help="都道府県内高時給のみ")
    kd.add_argument("--kodawari", "-k", metavar="ID[,ID...]",
                    help="こだわりID カンマ区切り (例: 9=未経験歓迎, 42=大学生歓迎)")
    kd.add_argument("--period", metavar="ID[,ID...]",
                    help="勤務期間ID カンマ区切り (例: 201=長期, 101=単発)")
    kd.add_argument("--timezone", metavar="ID[,ID...]",
                    help="勤務時間帯ID カンマ区切り (例: 2=昼, 4=夜勤)")
    kd.add_argument("--shift", type=int, metavar="ID",
                    help="週勤務日数ID (例: 4=週2日以上, 6=週3日以上)")
    kd.add_argument("--employee", metavar="ID[,ID...]",
                    help="雇用形態ID カンマ区切り (例: 1=アルバイト, 2=正社員)")
    kd.add_argument("--season", metavar="ID[,ID...]",
                    help="季節限定ID カンマ区切り (例: 10=夏休み)")

    oth = p.add_argument_group("その他条件")
    oth.add_argument("--no-highschool", action="store_true",
                     help="高校生不可求人を除外")
    oth.add_argument("--reserve", action="store_true",
                     help="直雇用のみ（reserveFlg=true）")

    req = p.add_argument_group("表示設定")
    req.add_argument("--page", type=int, default=1, metavar="N",
                     help="ページ番号 (デフォルト: 1)")
    req.add_argument("--sort", default="NEW",
                     choices=["NEW", "OSUSUME", "WAGE_HOURLY", "WAGE_DAILY", "WAGE_MONTHLY", "DISTANCE"],
                     help="ソート順 (デフォルト: NEW=新着順)")
    req.add_argument("--json", action="store_true", help="JSON形式で出力")
    p.set_defaults(func=cmd_search)

    # ── detail ──────────────────────────────────────────────
    p = sub.add_parser("detail", help="求人詳細")
    p.add_argument("job_cd", metavar="求人CD", help="例: J0134106676")
    p.add_argument("--json", action="store_true", help="JSON形式で出力")
    p.set_defaults(func=cmd_detail)

    # ── areas ───────────────────────────────────────────────
    p = sub.add_parser("areas", help="エリア一覧")
    p.add_argument("--pref", type=int, metavar="ID", help="都道府県ID (省略時=全都道府県)")
    p.add_argument("--depth", type=int, default=2, choices=[1, 2, 3, 4],
                   help="階層: 1=都道府県, 2=市区, 3=エリア, 4=駅周辺 (デフォルト: 2)")
    p.set_defaults(func=cmd_areas)

    # ── occupations ─────────────────────────────────────────
    p = sub.add_parser("occupations", help="職種一覧")
    p.add_argument("--depth", type=int, default=2, choices=[1, 2, 3],
                   help="階層深さ (デフォルト: 2)")
    p.set_defaults(func=cmd_occupations)

    # ── routes ──────────────────────────────────────────────
    p = sub.add_parser("routes", help="路線一覧")
    p.add_argument("--pref", type=int, default=13, metavar="ID",
                   help="都道府県ID (デフォルト: 13=東京)")
    p.add_argument("--depth", type=int, default=2, choices=[2, 3, 4],
                   help="階層: 2=鉄道会社, 3=路線, 4=駅 (デフォルト: 2)")
    p.add_argument("--json", action="store_true", help="JSON形式で出力")
    p.set_defaults(func=cmd_routes)

    # ── brands ──────────────────────────────────────────────
    p = sub.add_parser("brands", help="企業ブランド一覧")
    p.add_argument("--keyword", "-k", metavar="キーワード", help="ブランド名フィルター")
    p.set_defaults(func=cmd_brands)

    # ── kodawari ────────────────────────────────────────────
    p = sub.add_parser("kodawari", help="こだわり条件・給与・シフト等のID一覧")
    p.add_argument("--json", action="store_true", help="JSON形式で出力")
    p.set_defaults(func=cmd_kodawari)

    # ── suggest ─────────────────────────────────────────────
    p = sub.add_parser("suggest", help="キーワードサジェスト")
    p.add_argument("keyword", metavar="キーワード")
    p.add_argument("--pref", type=int, default=13, metavar="ID", help="都道府県ID")
    p.add_argument("--json", action="store_true", help="JSON形式で出力")
    p.set_defaults(func=cmd_suggest)

    # ── notices ─────────────────────────────────────────────
    p = sub.add_parser("notices", help="お知らせ一覧")
    p.set_defaults(func=cmd_notices)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except ValueError as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"予期しないエラー: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
