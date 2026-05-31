"""バイトル APIクライアント"""

import re
import threading
import requests
from bs4 import BeautifulSoup
from typing import Optional

BASE_URL = "https://www.baitoru.com"
CREATEURL = f"{BASE_URL}/noscreen/createurl/"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Referer": "https://www.baitoru.com/kanto/",
}

REGIONS = {
    "kanto": ("関東", "31"),
    "kansai": ("関西", "32"),
    "tokai": ("東海", "33"),
    "tohoku": ("東北", "34"),
    "koshinetsu": ("甲信越・北陸", "35"),
    "chushikoku": ("中国・四国", "36"),
    "kyushu": ("九州・沖縄", "37"),
}

# 各地域の駅データキャッシュ: region -> {name -> [eki_code]}
_station_cache: dict[str, dict[str, list[str]]] = {}
_cache_lock = threading.Lock()

# 給与種別コード
SALARY_TYPE_MAP = {"hourly": "3", "daily": "2", "monthly": "1"}

# 給与額の有効オプション (各種別の最小値以上で最近傍に丸める)
SALARY_OPTIONS = {
    "3": [800, 850, 900, 950, 1000, 1050, 1100, 1200, 1300, 1400, 1500, 1800, 2000, 2200, 2500],
    "2": [6499, 6500, 7000, 7500, 8000, 9000, 10000, 11000, 12000, 15000, 20000],
    "1": [149999, 150000, 180000, 210000, 220000, 230000, 240000, 250000, 260000, 270000, 280000, 290000, 300000],
}

# こだわり条件コード
CONDITION_MAP = {
    "short": "84_trm_X",       # 短期
    "spot": "83_trm_0",        # 単発
    "long": "85_trm_4",        # 長期
    "shift_free": "5_sft_5",   # シフト自由
    "morning": "90_tst_0",     # 朝
    "daytime": "89_tst_1",     # 昼
    "evening": "92_tst_4",     # 夕方
    "night": "91_tst_5",       # 夜
    "late_night": "87_tst_2",  # 深夜
    "early": "88_tst_3",       # 早朝
    "weekdays_only": "24_smr_24",  # 平日のみ
    "weekend_only": "22_smr_22",   # 土日祝のみ
    "week1": "23_nsu_23",      # 週1
    "week2": "6_nsu_6",        # 週2〜3
}

# 雇用形態
EMPLOYMENT_MAP = {
    "part": "normal",
    "full": "regular",
    "contract": "contract",
    "dispatch": "haken",
}


def _nearest_salary(salary_type_code: str, amount: int) -> int:
    opts = SALARY_OPTIONS.get(salary_type_code, [])
    return min(opts, key=lambda x: abs(x - amount)) if opts else amount


def build_search_url(
    keyword: Optional[str] = None,
    region: str = "kanto",
    salary_type: Optional[str] = None,
    salary_min: Optional[int] = None,
    employment: Optional[str] = None,
    conditions: Optional[list[str]] = None,
    sort: str = "osusume",
    page: int = 1,
    eki_codes: Optional[list[str]] = None,
) -> str:
    _, mid_area_cd = REGIONS.get(region, ("関東", "31"))
    region_name, _ = REGIONS.get(region, ("関東", "31"))

    params: dict = {
        "reqType": "33",
        "midAreaCd": mid_area_cd,
        "mid_area_name": region_name,
        "tab_kbn": "1",
        "redirect": "true",
        "jobsort": sort,
    }
    if keyword:
        params["keyword"] = keyword

    if salary_type and salary_min is not None:
        code = SALARY_TYPE_MAP.get(salary_type, "3")
        params["salaryType"] = code
        params["salary"] = str(_nearest_salary(code, salary_min))

    if employment:
        emp_code = EMPLOYMENT_MAP.get(employment, employment)
        params["baitTypes[]"] = emp_code

    if conditions:
        params["period[]"] = [CONDITION_MAP.get(c, c) for c in conditions]

    if eki_codes:
        params["eki[]"] = eki_codes

    resp = requests.post(CREATEURL, data=params, headers=_HEADERS, timeout=15, allow_redirects=False)
    location = resp.headers.get("Location", "")
    if not location:
        return ""
    url = (BASE_URL + location) if location.startswith("/") else location

    if page > 1:
        # ページ番号はパス末尾に "/pageN/" を付加する（クエリ文字列の手前）
        # 例: /kanto/jlist/wrdカフェ/page2/?pname=search_fw
        path, sep, query = url.partition("?")
        path = path.rstrip("/") + f"/page{page}/"
        url = path + (sep + query if query else "")

    return url


def fetch_jobs(url: str) -> tuple[list[dict], Optional[str]]:
    """URLをフェッチして求人リストと総件数を返す"""
    resp = requests.get(url, headers=_HEADERS, timeout=15)
    resp.raise_for_status()
    html = resp.text

    # 総件数は "(1～20件/315件中)" の「件中」で表す。
    # 単純な "N件" の最初の一致は表示件数セレクタ(20件/30件/40件)を拾うため不可。
    m = re.search(r"([\d,]+)件中", html)
    total = m.group(1) if m else None

    return _parse_jobs(html), total


def _parse_jobs(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    for article in soup.find_all("article", class_="list-jobListDetail"):
        job: dict = {}

        for link in article.find_all("a", href=True):
            m = re.search(r"job(\d+)", link["href"])
            if m:
                job["id"] = m.group(1)
                href = link["href"]
                job["url"] = (BASE_URL + href) if href.startswith("/") else href
                break

        h3 = article.find("h3")
        if h3:
            a_tag = h3.find("a")
            if a_tag:
                span = a_tag.find("span")
                job["title"] = (span or a_tag).get_text(strip=True)

        pt02b = article.find("div", class_="pt02b")
        if pt02b:
            p = pt02b.find("p")
            if p:
                job["description"] = p.get_text(strip=True)

        for ul in article.find_all("ul", class_="ul02"):
            for li in ul.find_all("li"):
                text = li.get_text(strip=True)
                if "勤務地" in text or "面接地" in text:
                    job["location"] = re.sub(r"^\[.+?\]\s*", "", text).strip()
                    break

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

        ul01 = article.find("ul", class_="ul01")
        if ul01:
            tags = [li.get_text(strip=True) for li in ul01.find_all("li")
                    if li.get_text(strip=True) not in ("動画あり",)]
            if tags:
                job["employment_type"] = ", ".join(tags)

        if job.get("id"):
            jobs.append(job)
    return jobs


def _load_station_cache(region: str) -> dict[str, list[str]]:
    """地域ページHTMLから駅名→eki[]コードのマッピングを構築してキャッシュする。

    検証済み（Playwright解析, 2026-05-30）:
    - `/{region}/` の生HTML（JS不要）に全駅が次の形で埋め込まれている:
        <input name="eki[]" value="2_172_010" data-org-str="東京駅">
      関東で eki[] 2,541件・ensn[] 228沿線。駅名は `data-org-str` 属性。
    - ここで得た eki[] コードを createurl の `eki[]` に渡すと
      駅で絞り込んだ検索URL（例 /kanto/jlist/2172tokyoeki/）が生成される。
    """
    with _cache_lock:
        if region in _station_cache:
            return _station_cache[region]

    url = f"{BASE_URL}/{region}/"
    resp = requests.get(url, headers=_HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # 駅名(data-org-str) → eki[]コード のマッピングを抽出
    station_map: dict[str, list[str]] = {}
    for inp in soup.find_all("input", {"name": "eki[]"}):
        code = inp.get("value", "")
        name = inp.get("data-org-str", "")
        if code and name:
            codes = station_map.setdefault(name, [])
            if code not in codes:
                codes.append(code)

    with _cache_lock:
        _station_cache[region] = station_map

    return station_map


def search_station(name: str, region: str = "kanto") -> list[dict]:
    """駅名で検索し、マッチした駅の eki[] コードを返す"""
    try:
        cache = _load_station_cache(region)
    except Exception:
        return []

    results = []
    for station_label, codes in cache.items():
        if name in station_label:
            results.append({
                "station_name": station_label,
                "eki_codes": codes,
                "region": region,
            })
    return results
