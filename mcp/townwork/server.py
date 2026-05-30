"""タウンワーク MCP サーバー"""

import urllib.parse
from typing import Optional
from fastmcp import FastMCP
from playwright.async_api import async_playwright, Browser, Page
import api

# ── Playwright ブラウザの管理 ─────────────────────────────────
# MCPサーバー起動時に1回だけブラウザを起動し、プロセス終了まで保持する

_playwright = None
_browser: Optional[Browser] = None
_page: Optional[Page] = None

# ページネーション用カーソルキャッシュ: search_key -> {page -> cursor}
# AIには page 番号だけ渡せばよいよう、カーソルはサーバー内部で管理する
_cursor_cache: dict[str, dict[int, str]] = {}


async def _get_page() -> Page:
    # 注意: goto に wait_until を指定しない（デフォルト "load"）。
    # "domcontentloaded" だと AWS WAF リダイレクト途中で止まる（API_SPEC.md）。
    global _playwright, _browser, _page
    if _browser is None or not _browser.is_connected():
        if _playwright is None:
            _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(headless=True)
        _page = await _browser.new_page()
        await _page.goto(api.BASE_URL, timeout=30000)
    elif _page is None or _page.is_closed():
        _page = await _browser.new_page()
        await _page.goto(api.BASE_URL, timeout=30000)
    return _page


# ── 雇用形態・こだわり条件の日本語→コード変換 ────────────────
# コードは API_SPEC.md / 元CLI で検証済みのものに限定する。
# 検証できていない条件コードは混乱を避けるため載せない。

EMPLOYMENT_MAP = {
    "アルバイト": "01", "パート": "01", "バイト": "01",
    "正社員": "02",
    "契約社員": "03", "契約": "03",
    "派遣": "04",
    "業務委託": "05", "委託": "05",
}

# 検証済みのこだわりコードのみ（prf-）。未確認のものは含めない。
PREFERENCE_MAP = {
    "日払い": "0401", "週払い": "0401",
    "学生歓迎": "0602",
}

# sc パラメータ（検証済みは 1=新着順 / 3=関連度順 の2種のみ）
SORT_MAP = {
    "新着": "1",
    "関連度": "3",
}


# ── MCP ────────────────────────────────────────────────────────
mcp = FastMCP("townwork")


def _cache_cursors(cache_key: str, next_pages: list) -> None:
    """nextPages の {pageNum(0始まり), cursor} を内部キャッシュに保存。
    AIにはカーソルを意識させず page 番号だけで操作できるようにする。
    """
    bucket = _cursor_cache.setdefault(cache_key, {})
    for np in next_pages:
        if "pageNum" in np and "cursor" in np:
            bucket[np["pageNum"]] = np["cursor"]


@mcp.tool()
async def search(
    prefecture: str = "東京",
    keyword: Optional[str] = None,
    salary_min: Optional[int] = None,
    employment: Optional[str] = None,
    preference: Optional[str] = None,
    sort: str = "新着",
    page: int = 1,
) -> dict:
    """タウンワークで求人を検索する。

    Args:
        prefecture: 都道府県名 (例: "東京", "大阪", "神奈川", "愛知" など)
        keyword: 検索キーワード (例: "カフェ", "コンビニ 深夜")
        salary_min: 最低給与額 (例: 1200)
                   金額から自動判定: 〜2500→時給, 6500〜20000→日給, 150000〜→月給
        employment: 雇用形態
            "アルバイト" | "パート" | "正社員" | "契約社員" | "派遣" | "業務委託"
        preference: こだわり条件 (タウンワークで対応を確認済みのもののみ)
            "日払い" | "週払い" | "学生歓迎"
        sort: ソート順 "新着" | "関連度"
        page: ページ番号 (1始まり)

    Returns:
        total: 総件数, jobs: 求人リスト (次ページは page+1 で取得可能)
    """
    pref_code = api.resolve_prefecture(prefecture)
    emp_code = EMPLOYMENT_MAP.get(employment, employment) if employment else None
    pref_code_val = PREFERENCE_MAP.get(preference, preference) if preference else None
    sort_code = SORT_MAP.get(sort, "1")

    cache_key = str(sorted({
        "prefecture": pref_code, "keyword": keyword, "salary_min": salary_min,
        "employment": emp_code, "preference": pref_code_val, "sort": sort_code,
    }.items()))

    # ページは 0 始まり。page>1 のときは前回キャッシュしたカーソルがあれば併用する
    idx = page - 1
    cursor = _cursor_cache.get(cache_key, {}).get(idx) if idx > 0 else None

    url = api.build_url(
        prefecture=pref_code,
        keyword=keyword,
        employment=emp_code,
        preference=pref_code_val,
        min_salary=salary_min,
        sort=sort_code,
        page=idx,
        cursor=cursor,
    )

    pg = await _get_page()
    data = await api.fetch_next_data(pg, url)
    jobs, total, next_pages = api.extract_jobs(data)
    _cache_cursors(cache_key, next_pages)

    return {
        "total": total,
        "page": page,
        "count": len(jobs),
        "search_url": url,
        "jobs": jobs,
    }


@mcp.tool()
async def search_with_station(
    station_name: str,
    prefecture: str = "東京",
    keyword: Optional[str] = None,
    salary_min: Optional[int] = None,
    employment: Optional[str] = None,
    page: int = 1,
) -> dict:
    """駅名を指定してタウンワークで求人を検索する（駅検索と求人検索を一括実行）。

    Args:
        station_name: 駅名 (例: "新宿", "渋谷", "梅田")
        prefecture: 都道府県名 (例: "東京", "大阪")
        keyword: 検索キーワード
        salary_min: 最低給与額
        employment: 雇用形態 "アルバイト" | "パート" | "正社員" | "契約社員" | "派遣"
        page: ページ番号 (1始まり)
    """
    pref_code = api.resolve_prefecture(prefecture)
    pg = await _get_page()

    stations = await api.list_stations_for_prefecture(pg, pref_code)
    matched = [s for s in stations if station_name in s["label"]]

    if not matched:
        suggestions = await api.search_stations(pg, station_name, pref_code)
        return {
            "error": f"駅 '{station_name}' が見つかりませんでした",
            "suggestions": suggestions,
            "jobs": [],
        }

    # 完全一致（"新宿"→"新宿駅"）を優先。部分一致が複数残る場合は曖昧なので候補を返す
    exact = [s for s in matched if s["label"] in (station_name, f"{station_name}駅")]
    if exact:
        station = exact[0]
    elif len(matched) == 1:
        station = matched[0]
    else:
        return {
            "needs_disambiguation": True,
            "message": f"'{station_name}' に複数の駅が該当します。候補から駅名を選び、正確な駅名で再実行してください。",
            "candidates": [s["label"] for s in matched],
            "jobs": [],
        }
    emp_code = EMPLOYMENT_MAP.get(employment, employment) if employment else None

    cache_key = str(sorted({
        "prefecture": pref_code, "station": station["id"], "keyword": keyword,
        "salary_min": salary_min, "employment": emp_code,
    }.items()))

    idx = page - 1
    cursor = _cursor_cache.get(cache_key, {}).get(idx) if idx > 0 else None

    url = api.build_url(
        prefecture=pref_code,
        keyword=keyword,
        area=f"ma-{station['ma']}" if station.get("ma") else None,
        sub_area=f"sa-{station['sa']}" if station.get("sa") else None,
        station=f"st-{station['id']}",
        employment=emp_code,
        min_salary=salary_min,
        page=idx,
        cursor=cursor,
    )

    data = await api.fetch_next_data(pg, url)
    jobs, total, next_pages = api.extract_jobs(data)
    _cache_cursors(cache_key, next_pages)

    return {
        "matched_station": station["label"],
        "total": total,
        "page": page,
        "count": len(jobs),
        "search_url": url,
        "jobs": jobs,
    }


@mcp.tool()
async def search_station(station_name: str, prefecture: str = "東京") -> list:
    """駅名でタウンワークの駅を検索する。
    通常は search_with_station() で一括実行できるが、
    駅候補を先に確認したい場合に使う。

    Args:
        station_name: 駅名 (例: "新宿", "渋谷")
        prefecture: 都道府県名 (例: "東京", "大阪")

    Returns:
        [{id, label, line, ma, sa}] のリスト
    """
    pref_code = api.resolve_prefecture(prefecture)
    pg = await _get_page()
    stations = await api.list_stations_for_prefecture(pg, pref_code)
    return [s for s in stations if station_name in s["label"]]


@mcp.tool()
async def get_job_count(keyword: str, prefecture: str = "東京") -> dict:
    """キーワード検索のヒット件数を取得する。

    Args:
        keyword: 検索キーワード
        prefecture: 都道府県名 (例: "東京", "大阪")
    """
    pref_code = api.resolve_prefecture(prefecture)
    pref_id = api.PREFECTURE_IDS.get(pref_code, "013")
    params = urllib.parse.urlencode({"kw": keyword, "prefecture_id": pref_id})
    api_url = f"{api.BASE_URL}/api/containers/pc/JobSearchHitCount/?{params}"
    pg = await _get_page()
    return await api.fetch_api(pg, api_url)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
