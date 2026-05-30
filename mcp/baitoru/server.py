"""バイトル MCP サーバー"""

from typing import Optional
from fastmcp import FastMCP
import api

mcp = FastMCP("baitoru")


@mcp.tool()
def search(
    keyword: Optional[str] = None,
    region: str = "kanto",
    salary_min: Optional[int] = None,
    salary_type: Optional[str] = None,
    employment: Optional[str] = None,
    conditions: Optional[list[str]] = None,
    sort: str = "osusume",
    page: int = 1,
) -> dict:
    """バイトルで求人を検索する。

    Args:
        keyword: 検索キーワード (例: "カフェ", "コンビニ")
        region: 地域コード "kanto"=関東 | "kansai"=関西 | "tokai"=東海 | "tohoku"=東北 | "koshinetsu"=甲信越・北陸 | "chushikoku"=中国・四国 | "kyushu"=九州・沖縄
        salary_min: 最低給与額 (例: 1200)
        salary_type: 給与種別 "hourly"=時給 | "daily"=日給 | "monthly"=月給
        employment: 雇用形態 "part"=アルバイト・パート | "full"=正社員 | "contract"=契約社員 | "dispatch"=派遣
        conditions: こだわり条件リスト (複数指定可)
            "short"=短期 | "spot"=単発 | "long"=長期 | "shift_free"=シフト自由
            "morning"=朝 | "daytime"=昼 | "evening"=夕方 | "night"=夜 | "late_night"=深夜 | "early"=早朝
            "weekdays_only"=平日のみ | "weekend_only"=土日祝のみ | "week1"=週1 | "week2"=週2〜3
        sort: ソート順 "osusume"=おすすめ | "new"=新着
        page: ページ番号 (1〜)

    Returns:
        total: 総件数, search_url: 検索URL, jobs: 求人リスト
    """
    url = api.build_search_url(
        keyword=keyword,
        region=region,
        salary_type=salary_type,
        salary_min=salary_min,
        employment=employment,
        conditions=conditions,
        sort=sort,
        page=page,
    )
    if not url:
        return {"error": "検索URLの生成に失敗しました", "jobs": []}

    jobs_raw, total = api.fetch_jobs(url)

    jobs = [
        {
            "source": "バイトル",
            "job_id": j.get("id", ""),
            "title": j.get("title", ""),
            "salary": j.get("salary", ""),
            "employment_type": j.get("employment_type", ""),
            "job_type": j.get("job_type", ""),
            "location": j.get("location", ""),
            "description": j.get("description", ""),
            "url": j.get("url", ""),
        }
        for j in jobs_raw
    ]

    return {
        "total": total,
        "page": page,
        "count": len(jobs),
        "search_url": url,
        "jobs": jobs,
    }


@mcp.tool()
def search_station(station_name: str, region: str = "kanto") -> list:
    """駅名でバイトルの駅コードを検索する。
    search()の eki_codes パラメータに使う値を返す。

    注意: バイトルの駅検索はサーバー起動時・初回呼び出し時にHTMLをパースするため、
    初回は数秒かかる場合があります。

    Args:
        station_name: 駅名 (例: "新宿", "渋谷")
        region: 地域コード (search()と同じ値)

    Returns:
        [{station_name, eki_codes, region}] のリスト。
        eki_codes を search()の eki_codes に渡す。
    """
    return api.search_station(station_name, region)


@mcp.tool()
def search_with_station(
    station_name: str,
    region: str = "kanto",
    keyword: Optional[str] = None,
    salary_min: Optional[int] = None,
    salary_type: Optional[str] = None,
    employment: Optional[str] = None,
    conditions: Optional[list[str]] = None,
    page: int = 1,
) -> dict:
    """駅名を指定してバイトルで求人を検索する（駅検索と求人検索を一括実行）。

    Args:
        station_name: 駅名 (例: "新宿", "渋谷")
        region: 地域コード "kanto"=関東 | "kansai"=関西 | など
        keyword: 検索キーワード
        salary_min: 最低給与額
        salary_type: "hourly"=時給 | "daily"=日給 | "monthly"=月給
        employment: "part"=アルバイト | "full"=正社員 | "contract"=契約 | "dispatch"=派遣
        conditions: こだわり条件リスト ("long", "daytime", "shift_free" など)
        page: ページ番号
    """
    stations = api.search_station(station_name, region)
    if not stations:
        return {"error": f"駅 '{station_name}' が見つかりませんでした", "jobs": []}

    # 完全一致（"東京"→"東京駅"）を優先。部分一致が複数残る場合は曖昧なので候補を返す
    exact = [s for s in stations if s["station_name"] in (station_name, f"{station_name}駅")]
    if exact:
        selected = exact
    elif len(stations) == 1:
        selected = stations
    else:
        return {
            "needs_disambiguation": True,
            "message": f"'{station_name}' に複数の駅が該当します。候補から駅名を選び、正確な駅名で再実行してください。",
            "candidates": [s["station_name"] for s in stations],
            "jobs": [],
        }

    all_eki_codes = []
    matched_names = []
    for s in selected:
        all_eki_codes.extend(s["eki_codes"])
        matched_names.append(s["station_name"])

    url = api.build_search_url(
        keyword=keyword,
        region=region,
        salary_type=salary_type,
        salary_min=salary_min,
        employment=employment,
        conditions=conditions,
        page=page,
        eki_codes=all_eki_codes,
    )
    if not url:
        return {"error": "検索URLの生成に失敗しました", "jobs": []}

    jobs_raw, total = api.fetch_jobs(url)

    jobs = [
        {
            "source": "バイトル",
            "job_id": j.get("id", ""),
            "title": j.get("title", ""),
            "salary": j.get("salary", ""),
            "employment_type": j.get("employment_type", ""),
            "job_type": j.get("job_type", ""),
            "location": j.get("location", ""),
            "description": j.get("description", ""),
            "url": j.get("url", ""),
        }
        for j in jobs_raw
    ]

    return {
        "matched_stations": matched_names,
        "total": total,
        "page": page,
        "count": len(jobs),
        "search_url": url,
        "jobs": jobs,
    }


def main():
    mcp.run()


if __name__ == "__main__":
    main()
