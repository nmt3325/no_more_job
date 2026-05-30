"""マイナビバイト MCP サーバー"""

from typing import Optional
from fastmcp import FastMCP
import api

mcp = FastMCP("mynavi-baito")

# ── 都道府県ID ────────────────────────────────────────────────
PREFECTURE_IDS = {
    "北海道": 1, "青森": 2, "岩手": 3, "宮城": 4, "秋田": 5,
    "山形": 6, "福島": 7, "茨城": 8, "栃木": 9, "群馬": 10,
    "埼玉": 11, "千葉": 12, "東京": 13, "神奈川": 14, "新潟": 15,
    "富山": 16, "石川": 17, "福井": 18, "山梨": 19, "長野": 20,
    "岐阜": 21, "静岡": 22, "愛知": 23, "三重": 24, "滋賀": 25,
    "京都": 26, "大阪": 27, "兵庫": 28, "奈良": 29, "和歌山": 30,
    "鳥取": 31, "島根": 32, "岡山": 33, "広島": 34, "山口": 35,
    "徳島": 36, "香川": 37, "愛媛": 38, "高知": 39, "福岡": 40,
    "佐賀": 41, "長崎": 42, "熊本": 43, "大分": 44, "宮崎": 45,
    "鹿児島": 46, "沖縄": 47,
}

# ── 給与wageId変換 ──────────────────────────────────────────
# 時給(wage1st=1): 閾値→wageId のマッピング（降順）
_HOURLY_THRESHOLDS = [
    (3000, "1-19"), (2500, "1-18"), (2000, "1-17"), (1500, "1-16"),
    (1400, "1-15"), (1300, "1-14"), (1250, "1-13"), (1200, "1-12"),
    (1100, "1-10"), (1000, "1-8"), (900, "1-6"), (800, "1-4"),
    (700, "1-2"),
]
_DAILY_THRESHOLDS = [
    (20000, "2-13"), (15000, "2-12"), (12000, "2-11"), (10000, "2-9"),
    (9000, "2-7"), (8000, "2-5"), (7000, "2-3"),
]
_MONTHLY_THRESHOLDS = [
    (250000, "3-12"), (200000, "3-7"), (170000, "3-4"), (150000, "3-2"),
]


def _salary_to_wage_id(salary_min: int, salary_type: str) -> Optional[str]:
    if salary_type == "hourly":
        table = _HOURLY_THRESHOLDS
    elif salary_type == "daily":
        table = _DAILY_THRESHOLDS
    elif salary_type == "monthly":
        table = _MONTHLY_THRESHOLDS
    else:
        return None
    for threshold, wage_id in table:
        if salary_min >= threshold:
            return wage_id
    return None


def _label(val) -> str:
    """LabelId dict ({"id":.., "label":..}) または文字列から表示文字列を取り出す"""
    if isinstance(val, dict):
        return val.get("label", "")
    return val or ""


def _format_job(job: dict) -> dict:
    wage = job.get("wage", {})
    shop = job.get("shopList", [{}])[0]
    access = shop.get("accessList", [{}])[0] if shop.get("accessList") else {}
    station = access.get("routeStation", {}).get("name", "")
    line = access.get("routeLine", {}).get("label", "")
    minutes = access.get("timeRequired", "")
    access_text = f"{line} {station}駅 徒歩{minutes}分" if station else ""

    return {
        "source": "マイナビバイト",
        "job_id": job.get("jobStockCd", ""),
        "title": job.get("recruitmentOccupationName", ""),
        "company": job.get("clientName", ""),
        "salary": wage.get("specialWageAmount", ""),
        "salary_amount": wage.get("wageAmount", 0),
        "salary_unit": {1: "hourly", 2: "daily", 3: "monthly"}.get(wage.get("id"), ""),
        "job_type": job.get("employeeFigure", {}).get("label", ""),
        "location": f"{_label(shop.get('locationPrefecture'))}{_label(shop.get('locationSikugun'))}",
        "access": access_text,
        "description": job.get("jobOfferContent", "") or job.get("recruitmentAppealPoint", ""),
        "url": f"https://baito.mynavi.jp/rec/{job.get('jobStockCd', '')}/",
    }


@mcp.tool()
def search(
    keyword: Optional[str] = None,
    prefecture: Optional[str] = None,
    salary_min: Optional[int] = None,
    salary_type: Optional[str] = None,
    employee_type: Optional[str] = None,
    period: Optional[str] = None,
    time_zone: Optional[str] = None,
    shift_days_per_week: Optional[int] = None,
    kodawari_ids: Optional[list[int]] = None,
    route_ids: Optional[list[str]] = None,
    area_ids: Optional[list[str]] = None,
    page: int = 1,
    sort: str = "NEW",
) -> dict:
    """マイナビバイトで求人を検索する。

    Args:
        keyword: 検索キーワード (例: "カフェ", "コンビニ 深夜")
        prefecture: 都道府県名 (例: "東京", "大阪", "神奈川")
        salary_min: 最低給与額 (例: 1200)
        salary_type: 給与種別 "hourly"=時給 | "daily"=日給 | "monthly"=月給
        employee_type: 雇用形態 "part"=アルバイト・パート | "full"=正社員 | "contract"=契約社員 | "dispatch"=派遣
        period: 勤務期間 "spot"=単発 | "short_week"=短期1週間以内 | "short_month"=短期1ヶ月以内 | "short_3month"=短期3ヶ月以内 | "long"=長期
        time_zone: 勤務時間帯 "morning"=朝 | "daytime"=昼 | "evening"=夕方 | "night"=夜 | "early_morning"=早朝 | "night_shift"=夜勤
        shift_days_per_week: 週勤務日数 (1〜10, 例: 1=週1日, 2=週1日以上, 3=週2日, 4=週2日以上...)
        kodawari_ids: こだわり条件IDリスト (get_filters()で確認可)
            代表的なID: 1=駅徒歩5分 | 6=日払い週払い | 9=未経験歓迎 | 23=シフト自由 | 39=交通費支給
            42=大学生歓迎 | 45=主婦(夫)歓迎 | 48=副業Wワーク | 68=完全週休2日 | 87=入社祝い金
        route_ids: 路線/駅IDリスト (search_station()が返す route_id を渡す。例: ["13-6-25"])
        area_ids: エリアIDリスト (例: ["13-651-35"]=東京新宿区)
        page: ページ番号 (1〜)
        sort: ソート順 "NEW"=新着 | "OSUSUME"=おすすめ | "WAGE_HOURLY"=時給高い順 | "WAGE_DAILY"=日給高い順

    Returns:
        total: 総件数, jobs: 求人リスト
    """
    prefecture_id = None
    if prefecture:
        prefecture_id = PREFECTURE_IDS.get(prefecture)
        if prefecture_id is None:
            for k, v in PREFECTURE_IDS.items():
                if prefecture in k:
                    prefecture_id = v
                    break

    words = keyword.split() if keyword else None

    wage_id = None
    if salary_min and salary_type:
        wage_id = _salary_to_wage_id(salary_min, salary_type)

    employee_id_list = None
    if employee_type:
        _emp_map = {"part": [1], "full": [2], "contract": [3], "dispatch": [4]}
        employee_id_list = _emp_map.get(employee_type)

    period_id_list = None
    if period:
        _period_map = {
            "spot": [101], "short_week": [102], "short_month": [103],
            "short_3month": [104], "long": [201],
        }
        period_id_list = _period_map.get(period)

    working_timezone_id_list = None
    if time_zone:
        _tz_map = {
            "morning": [1], "daytime": [2], "evening": [3],
            "night": [7], "early_morning": [5], "night_shift": [4],
        }
        working_timezone_id_list = _tz_map.get(time_zone)

    result = api.search_jobs(
        prefecture_id=prefecture_id,
        route_id_list=route_ids,
        area_id_list=area_ids,
        words=words,
        wage_id=wage_id,
        employee_id_list=employee_id_list,
        period_id_list=period_id_list,
        working_timezone_id_list=working_timezone_id_list,
        shift_id=shift_days_per_week,
        kodawari_id_list=kodawari_ids,
        page=page,
        sort=sort,
    )

    jobs = [_format_job(j) for j in result.get("jobList", [])]
    return {
        "total": result.get("searchCount", 0),
        "page": page,
        "count": len(jobs),
        "jobs": jobs,
    }


@mcp.tool()
def get_detail(job_id: str) -> dict:
    """求人詳細を取得する。

    Args:
        job_id: 求人コード (例: "J0134106676") - search()の結果の job_id フィールド
    """
    result = api.get_job_detail(job_id)
    job = result.get("jobDetail", {})
    formatted = _format_job(job)

    shop = job.get("shopList", [{}])[0] if job.get("shopList") else {}
    formatted.update({
        "company_name": job.get("companyName", ""),
        "address": f"{_label(shop.get('locationPrefecture'))}{_label(shop.get('locationSikugun'))}{shop.get('locationAddress1','')}{shop.get('locationAddress2','')}",
        "work_hours": _label(job.get("workingTimePerDay")),
        "work_days": " ".join(job.get("workingWeekday", {}).get("list", [])),
        "welfare": job.get("welfareNote", ""),
        "requirements": job.get("applicationRequirementsNote", ""),
        "contact_tel": shop.get("contactTel", ""),
    })
    return formatted


@mcp.tool()
def search_station(station_name: str, prefecture: str = "東京") -> list:
    """駅名でマイナビバイトの路線・駅IDを検索する。
    search()の route_id_list パラメータに使う routeId を返す。

    Args:
        station_name: 駅名 (例: "新宿", "渋谷", "梅田")
        prefecture: 都道府県名 (例: "東京", "大阪")

    Returns:
        [{station_name, line_name, route_id}] のリスト。
        route_id を search() の route_id_list に渡す。
    """
    pref_id = str(PREFECTURE_IDS.get(prefecture, 13))
    result = api.get_route_list(pref_id, depth=4)

    matches = []
    for company in result.get("routeList", [{}])[0].get("routeList", []):
        company_label = company.get("label", "")
        for line in company.get("routeList", []):
            line_label = line.get("label", "")
            for station in line.get("routeList", []):
                label = station.get("label", "")
                if station_name in label:
                    matches.append({
                        "station_name": label,
                        "line_name": f"{company_label} {line_label}",
                        "route_id": station.get("routeId", ""),
                    })
    return matches


@mcp.tool()
def get_filters() -> dict:
    """利用可能なフィルター一覧（こだわり条件・雇用形態・勤務期間など）を返す。
    search()の kodawari_id_list に渡すIDを調べるときに使う。
    """
    data = api.get_kodawari_list()
    return {
        "employee_types": [{"id": i["id"], "label": i["label"]} for i in data.get("employee", [])],
        "periods": [{"id": i["id"], "label": i["label"]} for i in data.get("period", [])],
        "shifts": [{"id": i["id"], "label": i["label"]} for i in data.get("shift", [])],
        "working_timezones": [{"id": i["id"], "label": i["label"]} for i in data.get("workingTimezone", [])],
        "kodawari": [{"id": i["id"], "label": i["label"]} for i in data.get("kodawari", [])],
        "wage": data.get("wage1st", []),
    }


def main():
    mcp.run()


if __name__ == "__main__":
    main()
