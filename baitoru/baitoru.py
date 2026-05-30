#!/usr/bin/env python3
"""バイトル求人検索CLI"""

import argparse
import re
import sys
import urllib.parse
from typing import Optional

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.baitoru.com/kanto/",
}
AJAX_HEADERS = {**HEADERS, "X-Requested-With": "XMLHttpRequest"}

BASE_URL = "https://www.baitoru.com"
AJAX_URL = f"{BASE_URL}/noscreen/ajax/"
CREATEURL = f"{BASE_URL}/noscreen/createurl/"

# ─── 定数テーブル ───────────────────────────────────────────────

REGIONS = {
    "kanto":      "関東",
    "kansai":     "関西",
    "tokai":      "東海",
    "tohoku":     "東北",
    "koshinetsu": "甲信越・北陸",
    "chushikoku": "中国・四国",
    "kyushu":     "九州・沖縄",
}

# midAreaCd (createurl の midAreaCd フィールドに渡す値)
REGION_MID_AREA = {
    "kanto":      "31",
    "kansai":     "32",
    "tokai":      "33",
    "tohoku":     "34",
    "koshinetsu": "35",
    "chushikoku": "36",
    "kyushu":     "37",
}

# 雇用形態
EMPLOYMENT_TYPES = {
    "アルバイト":   "normal",
    "バイト":       "normal",
    "パート":       "normal",
    "正社員":       "regular",
    "契約社員":     "contract",
    "契約":         "contract",
    "派遣":         "haken",
    "無期雇用派遣": "nlim_ehaken",
    "紹介予定派遣": "syokai_rhaken",
    "業務委託":     "outsg",
}
EMPLOYMENT_VALUES = {
    "normal":       "アルバイト・パート",
    "regular":      "正社員",
    "contract":     "契約社員",
    "haken":        "派遣",
    "nlim_ehaken":  "無期雇用派遣",
    "syokai_rhaken":"紹介予定派遣",
    "outsg":        "業務委託",
}

# 給与種別
SALARY_TYPES = {
    "時給": "3",
    "日給": "2",
    "月給": "1",
    "年俸": "0",
    "出来高": "6",
}

# 時給オプション (円)
SALARY_OPTIONS = {
    "3": [800, 850, 900, 950, 1000, 1050, 1100, 1200, 1300,
          1400, 1500, 1800, 2000, 2200, 2500],
    "2": [6499, 6500, 7000, 7500, 8000, 9000, 10000, 11000, 12000, 15000, 20000],
    "1": [149999, 150000, 180000, 210000, 220000, 230000, 240000,
          250000, 260000, 270000, 280000, 290000, 300000],
    "0": [1499999, 1500000, 1800000, 2000000, 2500000,
          3000000, 3500000, 4000000, 4500000, 5000000],
}

# 勤務期間 (period[])
PERIOD_OPTIONS = {
    "単発":        "83_trm_0",
    "短期":        "84_trm_X",
    "1週間以内":   "81_trm_1",
    "1ヶ月以内":   "80_trm_2",
    "3ヶ月以内":   "82_trm_3",
    "長期":        "85_trm_4",
}

# シフト
SHIFT_OPTIONS = {
    "シフト自由":   "5_sft_5",
    "1〜2週毎":     "69_sft_69",
    "月毎":         "70_sft_70",
    "固定":         "111_sft_111",
}

# 週の日数
DAYS_PER_WEEK_OPTIONS = {
    "週1":   "23_nsu_23",
    "週2":   "6_nsu_6",
    "週3":   "6_nsu_6",
    "週4":   "42_nsu_42",
}

# 時間帯
TIME_OPTIONS = {
    "早朝": "88_tst_3",
    "朝":   "90_tst_0",
    "昼":   "89_tst_1",
    "夕方": "92_tst_4",
    "夜":   "91_tst_5",
    "深夜": "87_tst_2",
}

# 1日の勤務時間
HOURS_OPTIONS = {
    "2h":  "67_tim_67",
    "4h":  "4_tim_4",
    "6h":  "68_tim_68",
}

# 勤務時間帯の制限
WORKTIME_OPTIONS = {
    "9時以降":  "76_knm_76",
    "10時以降": "73_knm_73",
    "16時前":   "74_knm_74",
    "17時前":   "75_knm_75",
}

# 休日
HOLIDAY_OPTIONS = {
    "週休2日":   "72_smr_72",
    "土日祝休み": "44_smr_44",
    "家庭都合":  "71_smr_71",
    "土日祝のみ": "22_smr_22",
    "春夏冬限定": "45_smr_45",
}

# 残業
OVERTIME_OPTIONS = {
    "残業なし":   "77_otw_77",
    "残業少なめ": "78_otw_78",
    "残業多め":   "79_otw_79",
}

# ソート
SORT_OPTIONS = {
    "おすすめ": "osusume",
    "新着":     "new",
    "osusume":  "osusume",
    "new":      "new",
}

ALL_PERIOD_OPTS = {
    **PERIOD_OPTIONS, **SHIFT_OPTIONS, **DAYS_PER_WEEK_OPTIONS,
    **TIME_OPTIONS, **HOURS_OPTIONS, **WORKTIME_OPTIONS,
    **HOLIDAY_OPTIONS, **OVERTIME_OPTIONS,
}


# ─── ユーティリティ ──────────────────────────────────────────────

def resolve_salary_type(val: str) -> str:
    """'時給'→'3', '3'→'3'"""
    return SALARY_TYPES.get(val, val)


def nearest_salary(salary_type_code: str, amount: int) -> int:
    """ユーザー指定額に最も近い有効な給与額を返す"""
    opts = SALARY_OPTIONS.get(salary_type_code, [])
    if not opts:
        return amount
    return min(opts, key=lambda x: abs(x - amount))


def resolve_employment(vals: list[str]) -> list[str]:
    """'バイト,派遣' → ['normal','haken']"""
    result = []
    for v in vals:
        mapped = EMPLOYMENT_TYPES.get(v, v)
        if mapped not in result:
            result.append(mapped)
    return result


def resolve_period(vals: list[str]) -> list[str]:
    """'長期,夜' → ['85_trm_4','91_tst_5']"""
    result = []
    for v in vals:
        code = ALL_PERIOD_OPTS.get(v, v)
        if code not in result:
            result.append(code)
    return result


def build_search_url_via_createurl(params: dict) -> str:
    """
    /noscreen/createurl/ にPOSTして生成されたURLを返す。
    サーバー側でパラメータ→URLセグメントの変換を行う。
    """
    resp = requests.post(
        CREATEURL,
        data=params,
        headers=HEADERS,
        timeout=15,
        allow_redirects=False,
    )
    location = resp.headers.get("Location", "")
    if location:
        if location.startswith("/"):
            return BASE_URL + location
        return location
    return ""


def build_filter_params(args) -> dict:
    """argparse の args からフォームパラメータを構築する"""
    region = getattr(args, "region", "kanto")
    mid_area_cd = REGION_MID_AREA.get(region, "31")

    params: dict = {
        "reqType":       "33",
        "midAreaCd":     mid_area_cd,
        "mid_area_name": REGIONS.get(region, "関東"),
        "tab_kbn":       "1",
        "redirect":      "true",
        "jobsort":       "osusume",
    }

    # キーワード
    kw = getattr(args, "keyword", None)
    if kw:
        params["keyword"] = kw

    # 給与種別 + 給与額
    salary_type = getattr(args, "salary_type", None)
    salary_amount = getattr(args, "salary", None)
    if salary_type:
        code = resolve_salary_type(salary_type)
        params["salaryType"] = code
        if salary_amount and salary_amount != "X":
            nearest = nearest_salary(code, int(salary_amount))
            params["salary"] = str(nearest)

    # 雇用形態
    employment = getattr(args, "employment", None) or []
    if employment:
        resolved = resolve_employment(employment)
        for e in resolved:
            params.setdefault("baitTypes[]", [])
            if isinstance(params["baitTypes[]"], str):
                params["baitTypes[]"] = [params["baitTypes[]"]]
            params["baitTypes[]"].append(e)

    # 期間・シフト・時間帯等
    period = getattr(args, "period", None) or []
    if period:
        resolved_period = resolve_period(period)
        params["period[]"] = resolved_period

    # ソート
    sort = getattr(args, "sort", None)
    if sort:
        params["jobsort"] = SORT_OPTIONS.get(sort, sort)

    return params


# ─── HTML パーサー ───────────────────────────────────────────────

def parse_job_articles(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    for article in soup.find_all("article", class_="list-jobListDetail"):
        job: dict = {}

        # Job ID & URL
        for link in article.find_all("a", href=True):
            m = re.search(r"job(\d+)", link["href"])
            if m:
                job["id"] = m.group(1)
                href = link["href"]
                job["url"] = (BASE_URL + href) if href.startswith("/") else href
                break

        # タイトル
        h3 = article.find("h3")
        if h3:
            a_tag = h3.find("a")
            if a_tag:
                span = a_tag.find("span")
                job["title"] = (span or a_tag).get_text(strip=True)

        # 職場説明
        pt02b = article.find("div", class_="pt02b")
        if pt02b:
            p = pt02b.find("p")
            if p:
                job["description"] = p.get_text(strip=True)

        # 勤務地
        for ul in article.find_all("ul", class_="ul02"):
            for li in ul.find_all("li"):
                text = li.get_text(strip=True)
                if "勤務地" in text or "面接地" in text:
                    # "[勤務地・面接地] 東京都..." のような形式を整形
                    loc = re.sub(r"^\[.+?\]\s*", "", text)
                    job["location"] = loc.strip()
                    break

        # 給与・職種・勤務時間
        pt03 = article.find("div", class_="pt03")
        if pt03:
            for dl in pt03.find_all("dl"):
                dt = dl.find("dt")
                dd = dl.find("dd")
                if not (dt and dd):
                    continue
                key = dt.get_text(strip=True)
                val = dd.get_text(" ", strip=True)
                if "給" in key or "賃金" in key:
                    job["salary"] = val[:100]
                elif "職種" in key:
                    job["job_type"] = val[:80]
                elif "勤務時間" in key or "勤務日" in key:
                    job["work_hours"] = val[:80]

        # Happyボーナス
        for span in article.find_all("span"):
            if "Happyボーナス" in span.get_text():
                em = span.find("em")
                if em:
                    job["bonus"] = f"Happyボーナス {em.get_text(strip=True)}円"
                break

        # 雇用形態タグ
        ul01 = article.find("ul", class_="ul01")
        if ul01:
            tags = [li.get_text(strip=True) for li in ul01.find_all("li")
                    if li.get_text(strip=True) not in ("動画あり",)]
            if tags:
                job["employment_type"] = tags

        if job.get("id"):
            jobs.append(job)
    return jobs


def parse_total_count(html: str) -> Optional[str]:
    m = re.search(r"([\d,]+)件", html)
    return m.group(1) if m else None


def print_jobs(jobs: list[dict], start: int = 1):
    for i, job in enumerate(jobs, start):
        print(f"[{i}] {job.get('title', '(タイトルなし)')}")
        if job.get("employment_type"):
            print(f"    雇用形態: {', '.join(job['employment_type'])}")
        if job.get("description"):
            print(f"    職場:     {job['description']}")
        if job.get("location"):
            print(f"    場所:     {job['location']}")
        if job.get("salary"):
            print(f"    給与:     {job['salary']}")
        if job.get("job_type"):
            print(f"    職種:     {job['job_type']}")
        if job.get("bonus"):
            print(f"    ボーナス: {job['bonus']}")
        if job.get("url"):
            print(f"    URL:      {job['url']}")
        print()


# ─── コマンド ────────────────────────────────────────────────────

def cmd_search(args):
    params = build_filter_params(args)
    page = args.page

    # createurl でURLを生成
    url = build_search_url_via_createurl(params)
    if not url:
        print("エラー: 検索URLの生成に失敗しました。", file=sys.stderr)
        sys.exit(1)

    # ページネーション
    if page > 1:
        url = re.sub(r"(/wrd[^/]*/|/jlist/)", lambda m: m.group() + f"page{page}/", url, count=1)
        if f"page{page}" not in url:
            url = url.rstrip("/") + f"/page{page}/"

    print(f"検索URL: {url}\n")

    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    html = resp.text

    total = parse_total_count(html)
    jobs = parse_job_articles(html)

    if total:
        print(f"検索結果: {total}件 (ページ {page})")
    print(f"表示件数: {len(jobs)}件\n")
    print("=" * 70)
    print_jobs(jobs)

    if total and jobs:
        print(f"次ページ: baitoru search --page {page + 1} {_rebuild_args(args)}")


def _rebuild_args(args) -> str:
    """再実行用の引数文字列を組み立てる"""
    parts = []
    if args.keyword:
        parts.append(f"'{args.keyword}'")
    if getattr(args, "salary_type", None):
        parts.append(f"--salary-type {args.salary_type}")
    if getattr(args, "salary", None):
        parts.append(f"--salary {args.salary}")
    if getattr(args, "employment", None):
        for e in args.employment:
            parts.append(f"--employment {e}")
    if getattr(args, "period", None):
        for p in args.period:
            parts.append(f"--period '{p}'")
    if getattr(args, "sort", None):
        parts.append(f"--sort {args.sort}")
    if args.region != "kanto":
        parts.append(f"--region {args.region}")
    return " ".join(parts)


def cmd_count(args):
    salary_type = getattr(args, "salary_type", None)
    salary_amount = getattr(args, "salary", None)
    employment = getattr(args, "employment", None) or []
    period = getattr(args, "period", None) or []
    region = getattr(args, "region", "kanto")

    params: dict = {
        "ajax_type":  "real_job_count_search",
        "mid_area_cd": REGION_MID_AREA.get(region, "31"),
    }
    if args.keyword:
        params["freeword"] = args.keyword
    if args.area:
        params["area_cd"] = args.area
    if salary_type:
        code = resolve_salary_type(salary_type)
        params["salary_kbn"] = code
        if salary_amount:
            params["min_salary"] = str(nearest_salary(code, int(salary_amount)))
    if employment:
        resolved = resolve_employment(employment)
        # bait_flg: normal=1, regular=2, haken=3 ... APIでは単純なフラグ
        params["bait_flg"] = ",".join(resolved)
    if period:
        params["period_cd"] = ",".join(resolve_period(period))

    resp = requests.post(AJAX_URL, data=params, headers=AJAX_HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    count = data.get("count_all", "?")
    avg = data.get("avg_salary", 0)
    print(f"求人件数: {count}件")
    if avg and str(avg) not in ("0", "0.0", "-", ""):
        print(f"平均給与: {avg}円")


def cmd_detail(args):
    job_id = args.job_id
    print(f"求人URL解決中 (job_id={job_id}) ...", end=" ", flush=True)

    resp = requests.get(
        f"{BASE_URL}/kanto/jlist/wrd{job_id}/",
        headers=HEADERS, timeout=15,
    )
    links = re.findall(rf"/[^\"]*job{re.escape(job_id)}/", resp.text)
    if not links:
        print("見つかりません")
        print(f"エラー: job_id={job_id} が見つかりませんでした", file=sys.stderr)
        sys.exit(1)

    job_url = BASE_URL + links[0]
    print(f"OK\n取得中: {job_url}\n")

    resp = requests.get(job_url, headers=HEADERS, timeout=15, allow_redirects=True)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    h1 = soup.find("h1")
    if h1:
        print(f"タイトル: {h1.get_text(strip=True)}\n")

    seen: set[str] = set()
    skip = {"エリアを選択", "あなたへのお知らせ", "スカウトメールとは？", "関東", "東海", "関西",
            "北海道・東北", "甲信越・北陸", "中国・四国", "九州・沖縄"}
    for dt in soup.find_all("dt"):
        dd = dt.find_next_sibling("dd")
        if not dd:
            continue
        key = dt.get_text(strip=True)
        val = dd.get_text(" ", strip=True)
        if not key or not val or key in seen or key in skip:
            continue
        if len(val) > 300:
            continue
        seen.add(key)
        print(f"【{key}】 {val}")

    print(f"\n応募URL: {BASE_URL}/entry/form/job{job_id}/")


def cmd_filters(args):
    print("── 地域 (--region) ──")
    for k, v in REGIONS.items():
        print(f"  {k:15} ({v})")

    print("\n── 給与種別 (--salary-type) ──")
    for label, code in SALARY_TYPES.items():
        opts = SALARY_OPTIONS.get(code, [])
        if opts:
            rng = f"{opts[0]:,}〜{opts[-1]:,}円"
        else:
            rng = ""
        print(f"  {label}  (code={code})  選択肢: {rng}")

    print("\n── 雇用形態 (--employment, 複数指定可) ──")
    for v, label in EMPLOYMENT_VALUES.items():
        print(f"  {label:12} (value={v})")

    print("\n── 期間・シフト・時間帯 (--period, 複数指定可) ──")
    sections = [
        ("勤務期間", PERIOD_OPTIONS),
        ("シフト",   SHIFT_OPTIONS),
        ("週の日数", DAYS_PER_WEEK_OPTIONS),
        ("時間帯",   TIME_OPTIONS),
        ("1日の時間", HOURS_OPTIONS),
        ("勤務制限", WORKTIME_OPTIONS),
        ("休日",     HOLIDAY_OPTIONS),
        ("残業",     OVERTIME_OPTIONS),
    ]
    for section_name, opts in sections:
        print(f"  [{section_name}]")
        for label in opts:
            print(f"    {label}")

    print("\n── ソート (--sort) ──")
    print("  おすすめ  (デフォルト)")
    print("  新着")

    print("\n── 使用例 ──")
    print("  baitoru search カフェ --salary-type 時給 --salary 1200 --period 長期 --time 昼")
    print("  baitoru search --employment 派遣 --region kansai --sort 新着")
    print("  baitoru search コンビニ --period 単発 --period 土日祝のみ")
    print("  baitoru count --keyword カフェ --salary-type 時給 --salary 1200")


# ─── エントリポイント ────────────────────────────────────────────

def add_filter_args(parser: argparse.ArgumentParser):
    parser.add_argument("keyword", nargs="?", help="検索キーワード")
    parser.add_argument("--region", default="kanto",
                        choices=list(REGIONS.keys()),
                        help="地域: kanto/kansai/tokai/tohoku/koshinetsu/chushikoku/kyushu (default: kanto)")
    parser.add_argument("--salary-type", dest="salary_type",
                        choices=list(SALARY_TYPES.keys()),
                        help="給与種別 (時給/日給/月給/年俸/出来高)")
    parser.add_argument("--salary", type=int,
                        help="最低給与額 (例: 1200 → 時給1,200円以上に近い値に自動調整)")
    parser.add_argument("--employment", action="append",
                        metavar="種別",
                        help="雇用形態 (複数可: バイト/正社員/契約社員/派遣/業務委託 など)")
    parser.add_argument("--period", action="append",
                        metavar="条件",
                        help="期間・シフト・時間帯など (複数可: 長期/短期/単発/昼/夜/週1 など)")
    parser.add_argument("--sort", choices=["おすすめ", "新着"],
                        help="ソート順 (おすすめ/新着)")


def main():
    parser = argparse.ArgumentParser(
        description="バイトル求人検索CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  %(prog)s search カフェ
  %(prog)s search カフェ --salary-type 時給 --salary 1200
  %(prog)s search カフェ --salary-type 時給 --salary 1200 --period 長期 --period 昼
  %(prog)s search --employment バイト --employment 派遣 --region kansai
  %(prog)s search コンビニ --period 単発 --period 土日祝のみ --sort 新着
  %(prog)s count カフェ --salary-type 時給 --salary 1200
  %(prog)s detail 160163909
  %(prog)s filters   # 全フィルター選択肢を表示
""",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # search
    p_search = sub.add_parser("search", help="求人を検索する")
    add_filter_args(p_search)
    p_search.add_argument("--page", type=int, default=1, help="ページ番号 (default: 1)")
    p_search.set_defaults(func=cmd_search)

    # count
    p_count = sub.add_parser("count", help="求人件数を取得する")
    add_filter_args(p_count)
    p_count.add_argument("--area", help="エリアコード (例: tdfk[]-13 = 東京都)")
    p_count.set_defaults(func=cmd_count)

    # detail
    p_detail = sub.add_parser("detail", help="求人詳細を表示する")
    p_detail.add_argument("job_id", help="求人ID (例: 160163909)")
    p_detail.set_defaults(func=cmd_detail)

    # filters
    p_filters = sub.add_parser("filters", help="利用可能なフィルター一覧を表示する")
    p_filters.set_defaults(func=cmd_filters)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
