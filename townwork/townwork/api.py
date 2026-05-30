"""タウンワーク API クライアント (Playwright ベース)"""

import json
import urllib.parse
from contextlib import contextmanager
from typing import Optional

from playwright.sync_api import sync_playwright

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

# smn/smx コード: 時給101-116, 日給201-216, 月給301-316
SALARY_CODES = {
    # 時給
    1000: "101", 1100: "102", 1200: "103", 1300: "104",
    1400: "105", 1500: "106", 1600: "107", 1700: "108",
    1800: "109", 1900: "110", 2000: "111", 2100: "112",
    2200: "113", 2300: "114", 2400: "115", 2500: "116",
    # 日給
    6500: "201", 7000: "202", 7500: "203", 8000: "204",
    9000: "205", 10000: "206", 11000: "207", 12000: "208",
    13000: "209", 14000: "210", 15000: "211", 16000: "212",
    17000: "213", 18000: "214", 19000: "215", 20000: "216",
    # 月給
    150000: "301", 160000: "302", 170000: "303", 180000: "304",
    190000: "305", 200000: "306", 210000: "307", 220000: "308",
    230000: "309", 240000: "310", 250000: "311", 260000: "312",
    270000: "313", 280000: "314", 290000: "315", 300000: "316",
}


@contextmanager
def _browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            yield browser
        finally:
            browser.close()


def _extract_next_data(browser, url: str) -> dict:
    """指定URLにアクセスし __NEXT_DATA__ を返す"""
    pg = browser.new_page()
    pg.goto(url)
    raw = pg.evaluate(
        "() => document.getElementById('__NEXT_DATA__')?.textContent || '{}'"
    )
    pg.close()
    data = json.loads(raw)
    return data.get("props", {}).get("pageProps", {}).get("data", {})


def search(
    prefecture: str = "tokyo",
    keyword: Optional[str] = None,
    area: Optional[str] = None,
    sub_area: Optional[str] = None,
    station: Optional[str] = None,
    employment: Optional[str] = None,
    occupation: Optional[str] = None,
    sub_occupation: Optional[str] = None,
    preference: Optional[str] = None,
    min_salary: Optional[int] = None,
    max_salary: Optional[int] = None,
    sort: str = "1",
    page: int = 0,
    cursor: Optional[str] = None,
) -> dict:
    """求人を検索する。"""
    # 駅検索: ma/sa が未指定の場合は駅データから自動補完
    resolved_area = area
    resolved_sub_area = sub_area
    if station and not area and not sub_area:
        st_info = _lookup_station(station, prefecture)
        if st_info:
            resolved_area = f"ma-{st_info['ma']}"
            resolved_sub_area = f"sa-{st_info['sa']}"

    url = _build_url(
        prefecture, keyword, resolved_area, resolved_sub_area, station,
        employment, occupation, sub_occupation, preference,
        min_salary, max_salary, sort, page, cursor,
    )
    with _browser() as browser:
        return _extract_next_data(browser, url)


def suggest(keyword: str, prefecture: str = "tokyo") -> list[str]:
    """キーワードのサジェストを取得"""
    params = urllib.parse.urlencode({
        "keyword": keyword,
        "seqId": "1",
        "UUID": "townwork-cli",
    })
    api_url = f"{BASE_URL}/api/containers/pc/KeywordAutoCompletePf/?{params}"
    with _browser() as browser:
        pg = browser.new_page()
        pg.goto(BASE_URL)
        result = pg.evaluate(f"""
            async () => {{
                const r = await fetch({json.dumps(api_url)}, {{headers: {{accept: 'application/json'}}}});
                return await r.json();
            }}
        """)
    return result.get("suggestion", [])


def hit_count(keyword: str, prefecture: str = "tokyo") -> dict:
    """キーワード検索のヒット件数を取得"""
    pref_id = PREFECTURE_IDS.get(prefecture, "013")
    params = urllib.parse.urlencode({"kw": keyword, "prefecture_id": pref_id})
    api_url = f"{BASE_URL}/api/containers/pc/JobSearchHitCount/?{params}"
    with _browser() as browser:
        pg = browser.new_page()
        pg.goto(BASE_URL)
        result = pg.evaluate(f"""
            async () => {{
                const r = await fetch({json.dumps(api_url)}, {{headers: {{accept: 'application/json'}}}});
                return await r.json();
            }}
        """)
    return result


def list_stations(prefecture: str = "tokyo") -> list[dict]:
    """都道府県内の駅一覧を取得（id, label, line, ma, sa）"""
    url = f"{BASE_URL}/prefectures/{prefecture}/job_search/"
    with _browser() as browser:
        data = _extract_next_data(browser, url)

    scd_raw = data.get("searchConditionData")
    if not scd_raw:
        return []
    scd = json.loads(scd_raw) if isinstance(scd_raw, str) else scd_raw
    items = scd.get("defaultMastersState", {}).get("stationState", {}).get("items", [])

    # 同一駅IDは最初の出現のみ採用（路線重複を排除）
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


def _lookup_station(station_id: str, prefecture: str) -> dict:
    """駅IDからma/saを逆引きする"""
    sid = station_id.removeprefix("st-")
    stations = list_stations(prefecture)
    for s in stations:
        if s["id"] == sid:
            return s
    return {}


def _build_url(
    prefecture, keyword, area, sub_area, station, employment, occupation,
    sub_occupation, preference, min_salary, max_salary, sort, page, cursor,
) -> str:
    parts = []
    if area:
        parts.append(area if area.startswith("ma-") else f"ma-{area}")
    if sub_area:
        parts.append(sub_area if sub_area.startswith("sa-") else f"sa-{sub_area}")
    if station:
        parts.append(station if station.startswith("st-") else f"st-{station}")
    if keyword:
        parts.append("kw")
        parts.append(urllib.parse.quote(keyword, safe=""))
    if employment:
        parts.append(employment if employment.startswith("emp-") else f"emp-{employment}")
    if occupation:
        parts.append(occupation if occupation.startswith("oc-") else f"oc-{occupation}")
    if sub_occupation:
        parts.append(sub_occupation if sub_occupation.startswith("omc-") else f"omc-{sub_occupation}")
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
    if min_salary is not None:
        code = _salary_code(min_salary)
        if code:
            params["smn"] = code
    if max_salary is not None:
        code = _salary_code(max_salary)
        if code:
            params["smx"] = code
    if page > 0:
        params["p"] = page
    if cursor:
        params["cursor"] = cursor

    qs = urllib.parse.urlencode(params)
    return f"{base}?{qs}" if qs else base


def _salary_code(salary: int) -> Optional[str]:
    for threshold in sorted(SALARY_CODES.keys(), reverse=True):
        if salary >= threshold:
            return SALARY_CODES[threshold]
    return None
