"""マイナビバイト バックグラウンドAPI クライアント"""

import time
import requests
from typing import Optional

BASE_URL = "https://baito.mynavi.jp"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=UTF-8",
    "Referer": "https://baito.mynavi.jp/",
}

# ソート値（SORT_QUERY定数）
SORT_NEW = "NEW"
SORT_OSUSUME = "OSUSUME"
SORT_WAGE_HOURLY = "WAGE_HOURLY"
SORT_WAGE_DAILY = "WAGE_DAILY"
SORT_WAGE_MONTHLY = "WAGE_MONTHLY"
SORT_DISTANCE = "DISTANCE"


def _post(path: str, body: dict) -> dict:
    url = f"{BASE_URL}{path}"
    resp = requests.post(url, json=body, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data and not any(k for k in data if k != "errors"):
        raise ValueError(f"APIエラー: {data['errors']}")
    return data


def _build_kodawari(
    wage_id: Optional[str] = None,
    prefecture_high_wage: bool = False,
    kodawari_id_list: Optional[list] = None,
    period_id_list: Optional[list] = None,
    working_timezone_id_list: Optional[list] = None,
    shift_id: Optional[int] = None,
    employee_id_list: Optional[list] = None,
    season_id_list: Optional[list] = None,
    lang_level_japanese: Optional[int] = None,
) -> Optional[dict]:
    """こだわり条件オブジェクトを構築。条件がない場合はNoneを返す

    wage_id: "{wage1st_id}-{wage2nd_id}" 形式の文字列
             例: "1-14"=時給1300円以上, "2-5"=日給8000円以上, "3-7"=月給20万円以上
    """
    kodawari: dict = {}
    if wage_id is not None:
        kodawari["wageId"] = wage_id
    if prefecture_high_wage:
        kodawari["prefectureHighWageFlg"] = True
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
    if season_id_list:
        kodawari["seasonIdList"] = season_id_list
    if lang_level_japanese is not None:
        kodawari["langLevelJapanese"] = lang_level_japanese
    return kodawari if kodawari else None


# ── 求人検索 ────────────────────────────────────────────────

def search_jobs(
    # ── 場所 ──
    prefecture_id: Optional[int] = None,
    area_id_list: Optional[list] = None,
    route_id_list: Optional[list] = None,
    # ── 職種・ブランド ──
    occupation_id_list: Optional[list] = None,
    brand_id: Optional[int] = None,
    client_cd: Optional[str] = None,
    # ── フリーワード ──
    words: Optional[list] = None,
    excluded_words: Optional[list] = None,
    # ── こだわり（kodawari）──
    wage_id: Optional[str] = None,
    prefecture_high_wage: bool = False,
    kodawari_id_list: Optional[list] = None,
    period_id_list: Optional[list] = None,
    working_timezone_id_list: Optional[list] = None,
    shift_id: Optional[int] = None,
    employee_id_list: Optional[list] = None,
    season_id_list: Optional[list] = None,
    lang_level_japanese: Optional[int] = None,
    # ── その他 ──
    exclude_no_highschool: bool = False,
    # ── リクエスト ──
    page: int = 1,
    sort: str = SORT_NEW,
    reserve_flg: bool = False,
) -> dict:
    """求人リスト検索（全フィルター対応版）

    sort: "NEW"=新着順, "OSUSUME"=おすすめ, "WAGE_HOURLY"=時給高い順,
          "WAGE_DAILY"=日給高い順, "WAGE_MONTHLY"=月給高い順, "DISTANCE"=距離順
    """
    condition: dict = {}

    # 場所
    if prefecture_id is not None:
        condition["prefectureId"] = prefecture_id
    if area_id_list:
        condition["areaIdList"] = area_id_list
    if route_id_list:
        condition["routeIdList"] = route_id_list

    # 職種・ブランド
    if occupation_id_list:
        condition["occupationIdList"] = [str(i) for i in occupation_id_list]
    if brand_id is not None:
        condition["brandId"] = brand_id
    if client_cd:
        condition["clientCd"] = client_cd

    # フリーワード
    if words or excluded_words:
        condition["freeword"] = {
            "words": words or [],
            "excludedWords": excluded_words or [],
        }

    # こだわり条件
    kodawari = _build_kodawari(
        wage_id=wage_id,
        prefecture_high_wage=prefecture_high_wage,
        kodawari_id_list=kodawari_id_list,
        period_id_list=period_id_list,
        working_timezone_id_list=working_timezone_id_list,
        shift_id=shift_id,
        employee_id_list=employee_id_list,
        season_id_list=season_id_list,
        lang_level_japanese=lang_level_japanese,
    )
    if kodawari:
        condition["kodawari"] = kodawari

    # 高校生不可除外
    if exclude_no_highschool:
        condition["excludeNoHighSchoolStudentFlg"] = True

    return _post("/api/search/solr/list", {
        "searchCondition": condition,
        "page": page,
        "reserveFlg": reserve_flg,
        "sort": sort,
    })


def get_search_count(
    prefecture_id: Optional[int] = None,
    occupation_id_list: Optional[list] = None,
    area_id_list: Optional[list] = None,
    route_id_list: Optional[list] = None,
    words: Optional[list] = None,
    brand_id: Optional[int] = None,
    wage_id: Optional[str] = None,
    kodawari_id_list: Optional[list] = None,
    period_id_list: Optional[list] = None,
    working_timezone_id_list: Optional[list] = None,
    shift_id: Optional[int] = None,
    employee_id_list: Optional[list] = None,
) -> dict:
    """検索件数取得"""
    condition: dict = {}
    if prefecture_id is not None:
        condition["prefectureId"] = prefecture_id
    if area_id_list:
        condition["areaIdList"] = area_id_list
    if route_id_list:
        condition["routeIdList"] = route_id_list
    if occupation_id_list:
        condition["occupationIdList"] = [str(i) for i in occupation_id_list]
    if words:
        condition["freeword"] = {"words": words, "excludedWords": []}
    if brand_id is not None:
        condition["brandId"] = brand_id

    kodawari = _build_kodawari(
        wage_id=wage_id,
        kodawari_id_list=kodawari_id_list,
        period_id_list=period_id_list,
        working_timezone_id_list=working_timezone_id_list,
        shift_id=shift_id,
        employee_id_list=employee_id_list,
    )
    if kodawari:
        condition["kodawari"] = kodawari

    return _post("/api/search/count", {"searchCondition": condition})


# ── 求人詳細 ────────────────────────────────────────────────

def get_job_detail(job_stock_cd: str) -> dict:
    """求人詳細取得"""
    return _post("/api/job/detail", {"jobStockCd": job_stock_cd})


# ── マスターデータ ──────────────────────────────────────────

def get_area_list(area_id: Optional[str] = None, depth: int = 1) -> dict:
    """エリアマスター取得

    area_id: None=全国, '13'=東京都, '13-651'=東京23区 など
    depth: 1=都道府県, 2=市区, 3=エリア, 4=駅周辺
    """
    if area_id:
        body = {"areaList": [{"areaId": area_id, "depth": depth + 1}]}
    else:
        body = {"areaList": [{"depth": 1}]}
    return _post("/api/master/area/list", body)


def get_occupation_list(depth: int = 1) -> dict:
    """職種マスター取得"""
    return _post("/api/master/occupation/list", {"occupationList": [{"depth": depth + 1}]})


def get_route_list(area_id: str = "13", depth: int = 2) -> dict:
    """路線マスター取得

    area_id: 都道府県ID文字列 ('13'=東京 など)
    depth: 2=鉄道会社, 3=路線, 4=駅
    """
    return _post("/api/master/route/list", {"routeList": [{"routeId": area_id, "depth": depth}]})


def get_company_brand_list() -> dict:
    """企業ブランドマスター取得"""
    return _post("/api/master/company-brand/list", {})


def get_kodawari_list() -> dict:
    """こだわり条件マスター取得

    返り値のキー:
      period         - 期間: [{id, label}]
      employee       - 雇用形態: [{id, label}]
      shift          - シフト: [{id, label}]
      workingTimezone- 勤務時間帯: [{id, label}]
      wage1st        - 給与種別: [{id, label, wage2nd:[{id, label}]}]
      kodawari       - こだわり: [{id, label}]
      season         - 季節限定: [{id, label}]
    """
    return _post("/api/master/kodawari/list", {})


def get_notice_list() -> dict:
    """お知らせ一覧取得"""
    return _post("/api/notice/list", {})


def suggest(keyword: str, prefecture_id: int = 13, limit: int = 10) -> dict:
    """キーワードサジェスト"""
    tracking_id = f"{int(time.time() * 1000)}.{int(time.time() * 1000) % 1000000}"
    return _post("/api/suggest/list", {
        "searchWord": keyword,
        "prefectureId": prefecture_id,
        "limit": limit,
        "viewRecommend": False,
        "viewPickup": False,
        "trackingId": tracking_id,
    })
