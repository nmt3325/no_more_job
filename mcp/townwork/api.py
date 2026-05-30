"""タウンワーク APIクライアント (Playwright ベース)"""

import json
import urllib.parse
from typing import Optional, Any
from playwright.async_api import Browser, Page

BASE_URL = "https://townwork.net"

PREFECTURE_IDS = {
    "hokkaido": "001", "aomori": "002", "iwate": "003", "miyagi": "004",
    "akita": "005", "yamagata": "006", "fukushima": "007", "ibaraki": "008",
    "tochigi": "009", "gunma": "010", "saitama": "011", "chiba": "012",
    "tokyo": "013", "kanagawa": "014", "niigata": "015", "toyama": "016",
    "ishikawa": "017", "fukui": "018", "yamanashi": "019", "nagano": "020",
    "gifu": "021", "shizuoka": "022", "aichi": "023", "mie": "024",
    "shiga": "025", "kyoto": "026", "osaka": "027", "hyogo": "028",
    "nara": "029", "wakayama": "030", "tottori": "031", "shimane": "032",
    "okayama": "033", "hiroshima": "034", "yamaguchi": "035", "tokushima": "036",
    "kagawa": "037", "ehime": "038", "kochi": "039", "fukuoka": "040",
    "saga": "041", "nagasaki": "042", "kumamoto": "043", "oita": "044",
    "miyazaki": "045", "kagoshima": "046", "okinawa": "047",
}

PREFECTURE_NAMES_JP = {
    "東京": "tokyo", "大阪": "osaka", "神奈川": "kanagawa", "愛知": "aichi",
    "埼玉": "saitama", "千葉": "chiba", "兵庫": "hyogo", "福岡": "fukuoka",
    "北海道": "hokkaido", "京都": "kyoto", "静岡": "shizuoka", "茨城": "ibaraki",
    "広島": "hiroshima", "宮城": "miyagi", "新潟": "niigata", "長野": "nagano",
    "栃木": "tochigi", "岐阜": "gifu", "群馬": "gunma", "岡山": "okayama",
    "三重": "mie", "熊本": "kumamoto", "鹿児島": "kagoshima", "沖縄": "okinawa",
    "滋賀": "shiga", "山口": "yamaguchi", "愛媛": "ehime", "長崎": "nagasaki",
    "奈良": "nara", "青森": "aomori", "岩手": "iwate", "石川": "ishikawa",
    "大分": "oita", "宮崎": "miyazaki", "富山": "toyama", "秋田": "akita",
    "香川": "kagawa", "和歌山": "wakayama", "山形": "yamagata", "福島": "fukushima",
    "福井": "fukui", "徳島": "tokushima", "高知": "kochi", "島根": "shimane",
    "鳥取": "tottori", "佐賀": "saga", "山梨": "yamanashi",
}

# smn コード: 時給101〜, 日給201〜, 月給301〜
_SALARY_CODES = [
    (1000, "101"), (1100, "102"), (1200, "103"), (1300, "104"),
    (1400, "105"), (1500, "106"), (1600, "107"), (1700, "108"),
    (1800, "109"), (1900, "110"), (2000, "111"), (2100, "112"),
    (2200, "113"), (2300, "114"), (2400, "115"), (2500, "116"),
    (6500, "201"), (7000, "202"), (7500, "203"), (8000, "204"),
    (9000, "205"), (10000, "206"), (11000, "207"), (12000, "208"),
    (150000, "301"), (160000, "302"), (170000, "303"), (180000, "304"),
    (190000, "305"), (200000, "306"), (210000, "307"), (220000, "308"),
]


def resolve_prefecture(prefecture: str) -> str:
    """都道府県名(日本語 or 英語)→英語コード"""
    if prefecture in PREFECTURE_NAMES_JP:
        return PREFECTURE_NAMES_JP[prefecture]
    return prefecture


def salary_code(amount: int) -> Optional[str]:
    for threshold, code in sorted(_SALARY_CODES, reverse=True):
        if amount >= threshold:
            return code
    return None


def build_url(
    prefecture: str,
    keyword: Optional[str] = None,
    area: Optional[str] = None,
    sub_area: Optional[str] = None,
    station: Optional[str] = None,
    employment: Optional[str] = None,
    preference: Optional[str] = None,
    min_salary: Optional[int] = None,
    sort: str = "1",
    page: int = 0,
    cursor: Optional[str] = None,
) -> str:
    parts = []
    if area:
        parts.append(area if area.startswith("ma-") else f"ma-{area}")
    if sub_area:
        parts.append(sub_area if sub_area.startswith("sa-") else f"sa-{sub_area}")
    if station:
        parts.append(station if station.startswith("st-") else f"st-{station}")
    if keyword:
        parts.extend(["kw", urllib.parse.quote(keyword, safe="")])
    if preference:
        parts.append(preference if preference.startswith("prf-") else f"prf-{preference}")

    path = "/".join(parts)
    base = (
        f"{BASE_URL}/prefectures/{prefecture}/job_search/{path}/"
        if path else
        f"{BASE_URL}/prefectures/{prefecture}/job_search/"
    )

    params: dict = {"sc": sort}
    if sub_area:
        params["sa"] = sub_area.removeprefix("sa-")
    # employment はパスに入れると 400 になるためクエリパラメータで渡す
    if employment:
        params["emp"] = employment.removeprefix("emp-")
    if min_salary is not None:
        code = salary_code(min_salary)
        if code:
            params["smn"] = code
    if page > 0:
        params["p"] = page
    if cursor:
        params["cursor"] = cursor

    qs = urllib.parse.urlencode(params)
    return f"{base}?{qs}" if qs else base


async def fetch_next_data(page: Page, url: str) -> dict:
    """指定URLにアクセスして __NEXT_DATA__ を取得

    注意: wait_until は明示しない（デフォルト "load"）。
    "domcontentloaded" を指定すると AWS WAF のリダイレクト途中で止まり
    データ取得に失敗する（API_SPEC.md 参照）。
    """
    await page.goto(url, timeout=30000)
    raw = await page.evaluate(
        "() => document.getElementById('__NEXT_DATA__')?.textContent || '{}'"
    )
    data = json.loads(raw)
    # data キーが存在しても null の場合があるため or {} でフォールバック
    return data.get("props", {}).get("pageProps", {}).get("data") or {}


async def fetch_api(page: Page, api_url: str) -> Any:
    """タウンワーク上でfetchしてJSONを返す"""
    result = await page.evaluate(f"""
        async () => {{
            const r = await fetch({json.dumps(api_url)}, {{headers: {{accept: 'application/json'}}}});
            return await r.json();
        }}
    """)
    return result


def extract_jobs(data: dict) -> tuple[list[dict], Optional[str], list[dict]]:
    """__NEXT_DATA__ (props.pageProps.data) から求人リスト・総件数・次ページ情報を抽出。

    検証済みの構造（API_SPEC.md 第5節）:
      data["jobCards"]                    → 求人カード配列
      data["recordInfo"]["totalCount"]    → 総件数（"2,343件" のような文字列）
      data["pageInfo"]["nextPages"]       → [{pageNum, cursor}, ...]
    """
    job_cards = data.get("jobCards", []) or []
    total = (data.get("recordInfo") or {}).get("totalCount") or None
    next_pages = (data.get("pageInfo") or {}).get("nextPages", []) or []

    jobs = []
    for j in job_cards:
        job_types = j.get("jobType", []) or []
        jobs.append({
            "source": "タウンワーク",
            "job_id": j.get("indeedJobKey", ""),
            "title": j.get("title", ""),
            "subtitle": j.get("subTitle", ""),
            "company": j.get("employerName", ""),
            "salary": j.get("salary", ""),
            "job_type": ", ".join(job_types) if isinstance(job_types, list) else str(job_types),
            "location": j.get("workLocation", ""),
            "access": j.get("access", ""),
            "work_hours": j.get("workHours", ""),
            "description": j.get("jobDescriptionContent", ""),
        })

    return jobs, total, next_pages


async def search_stations(page: Page, keyword: str, prefecture: str = "tokyo") -> list[str]:
    """キーワードで駅サジェストを取得"""
    params = urllib.parse.urlencode({
        "keyword": keyword,
        "seqId": "1",
        "UUID": "townwork-mcp",
    })
    api_url = f"{BASE_URL}/api/containers/pc/KeywordAutoCompletePf/?{params}"
    result = await fetch_api(page, api_url)
    return result.get("suggestion", [])


async def list_stations_for_prefecture(page: Page, prefecture: str) -> list[dict]:
    """都道府県の全駅一覧を取得"""
    url = f"{BASE_URL}/prefectures/{prefecture}/job_search/"
    data = await fetch_next_data(page, url)

    scd_raw = data.get("searchConditionData")
    if not scd_raw:
        return []
    scd = json.loads(scd_raw) if isinstance(scd_raw, str) else scd_raw
    items = scd.get("defaultMastersState", {}).get("stationState", {}).get("items", [])

    seen: set[str] = set()
    result = []
    for s in items:
        sid = s["id"]
        st_props = s.get("stProps", {})
        key = f"{sid}-{st_props.get('ma', '')}-{st_props.get('sa', '')}"
        if key not in seen:
            seen.add(key)
            result.append({
                "id": sid,
                "label": s["label"],
                "line": s.get("lv1", {}).get("label", ""),
                "ma": st_props.get("ma", ""),
                "sa": st_props.get("sa", ""),
            })
    return result
