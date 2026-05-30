"""マイナビバイト APIクライアント"""

import time
import requests
from typing import Optional

BASE_URL = "https://baito.mynavi.jp"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=UTF-8",
    "Referer": "https://baito.mynavi.jp/",
}


def _post(path: str, body: dict) -> dict:
    resp = requests.post(f"{BASE_URL}{path}", json=body, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data and len(data) == 1:
        raise ValueError(f"APIエラー: {data['errors']}")
    return data


def search_jobs(
    prefecture_id: Optional[int] = None,
    area_id_list: Optional[list] = None,
    route_id_list: Optional[list] = None,
    occupation_id_list: Optional[list] = None,
    brand_id: Optional[int] = None,
    words: Optional[list] = None,
    wage_id: Optional[str] = None,
    kodawari_id_list: Optional[list] = None,
    period_id_list: Optional[list] = None,
    working_timezone_id_list: Optional[list] = None,
    shift_id: Optional[int] = None,
    employee_id_list: Optional[list] = None,
    page: int = 1,
    sort: str = "NEW",
) -> dict:
    condition: dict = {}
    if prefecture_id is not None:
        condition["prefectureId"] = prefecture_id
    if area_id_list:
        condition["areaIdList"] = area_id_list
    if route_id_list:
        condition["routeIdList"] = route_id_list
    if occupation_id_list:
        condition["occupationIdList"] = [str(i) for i in occupation_id_list]
    if brand_id is not None:
        condition["brandId"] = brand_id
    if words:
        condition["freeword"] = {"words": words, "excludedWords": []}

    kodawari: dict = {}
    if wage_id:
        kodawari["wageId"] = wage_id
    if kodawari_id_list:
        kodawari["kodawariIdList"] = kodawari_id_list
    if period_id_list:
        kodawari["periodIdList"] = period_id_list
    if working_timezone_id_list:
        kodawari["workingTimezoneIdList"] = working_timezone_id_list
    if shift_id is not None:
        kodawari["shiftId"] = shift_id
    if employee_id_list:
        kodawari["employeeIdList"] = employee_id_list
    if kodawari:
        condition["kodawari"] = kodawari

    return _post("/api/search/solr/list", {
        "searchCondition": condition,
        "page": page,
        "reserveFlg": False,
        "sort": sort,
    })


def get_job_detail(job_stock_cd: str) -> dict:
    return _post("/api/job/detail", {"jobStockCd": job_stock_cd})


def get_route_list(prefecture_id: str, depth: int = 4) -> dict:
    """路線・駅マスター取得 (depth=4で駅まで)"""
    return _post("/api/master/route/list", {"routeList": [{"routeId": prefecture_id, "depth": depth}]})


def get_kodawari_list() -> dict:
    return _post("/api/master/kodawari/list", {})


def suggest(keyword: str, prefecture_id: int = 13) -> dict:
    tracking_id = f"{int(time.time() * 1000)}.{int(time.time() * 1000) % 1000000}"
    return _post("/api/suggest/list", {
        "searchWord": keyword,
        "prefectureId": prefecture_id,
        "limit": 10,
        "viewRecommend": False,
        "viewPickup": False,
        "trackingId": tracking_id,
    })
