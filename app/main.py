import json
import logging
import traceback
import uuid
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import os
import re
import httpx
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.params import Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pymongo import MongoClient
from urllib.parse import urlparse

from app.AsyncPostgres import AsyncPostgres
from app.compatibility import compatibility_routes, maybe_envelope
from app.config import Config
from app.ihr import login, fetch_all_pages
from app.kingdee import Ext_k3sdk
from app.lingxing import set_header
from app.lingxing_login import lingxing_openapi

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
OPENAPI_ALLOWED_PATHS = set(Config.OPENAPI_ALLOWED_PATHS)
WEB_ALLOWED_HOSTS = set(Config.WEB_ALLOWED_HOSTS)
TABLE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
OPENAPI_ROUTE_OPTIONS = {
    # 订单利润报表耗时通常更长，单独放宽超时与重试，提升稳定性
    "basicOpen/finance/mreport/OrderProfit": {
        "timeout": int(os.getenv("ORDER_PROFIT_TIMEOUT_SECONDS", "120")),
        "retries": int(os.getenv("ORDER_PROFIT_RETRIES", "3")),
    }
}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.exception(
        "Unhandled exception request_id=%s method=%s path=%s detail=%s\n%s",
        request_id,
        request.method,
        request.url.path,
        str(exc),
        traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": str(exc) or "Internal Server Error",
            "request_id": request_id,
        },
    )


@app.middleware("http")
async def request_trace_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    started_at = time.perf_counter()

    logger.info("request.start request_id=%s method=%s path=%s", request_id, request.method, request.url.path)
    try:
        response = await call_next(request)
    except Exception:
        raise

    cost_ms = round((time.perf_counter() - started_at) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request.end request_id=%s method=%s path=%s status=%s cost_ms=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        cost_ms,
    )
    return response


def _is_openapi_path_allowed(full_path: str) -> bool:
    if not Config.ENFORCE_OPENAPI_WHITELIST:
        return True
    if not OPENAPI_ALLOWED_PATHS:
        return False

    normalized_path = "/" + full_path.strip("/")
    for allowed_path in OPENAPI_ALLOWED_PATHS:
        normalized_allowed = "/" + allowed_path.strip("/")
        if normalized_path == normalized_allowed or normalized_path.startswith(normalized_allowed + "/"):
            return True
    return False


def _build_and_validate_web_url(full_path: str) -> str:
    target_url = "https://" + full_path.lstrip("/")
    parsed = urlparse(target_url)
    if not parsed.hostname:
        raise HTTPException(status_code=400, detail="Invalid target url")
    if Config.ENFORCE_WEB_HOST_WHITELIST and parsed.hostname not in WEB_ALLOWED_HOSTS:
        raise HTTPException(status_code=403, detail=f"Target host not allowed: {parsed.hostname}")
    return target_url


@app.get("/healthz")
async def healthz(request: Request):
    return maybe_envelope(request, {"status": "ok"}, source="internal", message="ok")


@app.get("/meta/compatibility/routes")
async def meta_compatibility_routes(request: Request):
    payload = {
        "routes": compatibility_routes(),
        "note": "Use query _compat_envelope=1 or header X-Compat-Envelope:1 to get unified envelope response.",
    }
    return maybe_envelope(request, payload, source="compatibility-meta")


@app.get("/ihr/openapi/thirdparty/api/staff/v1/staffs")
async def ihr_staffs(request: Request):
    """
    浠嶪HR360鑾峰彇鎵€鏈夊憳宸ョ殑鍩烘湰淇℃伅銆傝嚜宸卞皝瑁咃紝鑷甫鎺ュ彛涓嶈兘涓€娆℃€ц幏鍙栨墍鏈夊憳宸ヤ俊鎭€?
    """
    ids = await fetch_all_pages(base_url="https://openapi.ihr360.com/openapi/thirdparty/api/staff/v1/staffs/ids")
    token_info = await login()
    header = {
        'Content-Type': 'application/json;charset=UTF-8;',
        'Authorization': 'Bearer ' + token_info['access_token']
    }
    results = {
        "code": 0,
        "message": "SUCCESS",
        "data": []
    }
    async with httpx.AsyncClient(headers=header, timeout=180) as client:
        # 姣忔澶勭悊鏈€澶?000涓狪Ds
        batch_size = 1000
        for i in range(0, len(ids), batch_size):
            current_batch = ids[i:i + batch_size]
            response = await client.post(
                "https://openapi.ihr360.com/openapi/thirdparty/api/staff/v1/staffs/basic",
                json=current_batch
            )
            if response.status_code == 200:
                results['data'].extend(response.json()['data'])
            else:
                print(f"Error fetching data for batch starting at index {i}: {response.text}")
    return maybe_envelope(request, results, source="ihr")


@app.api_route("/ihr/{full_path:path}",
               methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH", "TRACE"])
async def ihr_proxy_request(request: Request, full_path: str):
    """
    閫氳繃妯℃嫙鐧诲綍锛屽弽鍚戜唬鐞嗚姹傚埌ihr360锛屽苟杩斿洖鍝嶅簲銆?
    """
    token_info = await login()
    header = {
        'Content-Type': 'application/json;charset=UTF-8;',
        'Authorization': 'Bearer ' + token_info['access_token']
    }
    req_body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        if request.headers.get('Content-Type', '').startswith('application/json'):
            try:
                body = await request.body()
                req_body = json.loads(body.decode("utf-8"))
                logger.info(f"Requesting {req_body}")
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON data received")
        else:
            raise HTTPException(status_code=415, detail="Unsupported Media Type or Missing JSON Content-Type")

    async with httpx.AsyncClient(headers=header, timeout=180) as client:
        try:
            logger.info(f"Requesting https://openapi.ihr360.com/{full_path}")
            # 閫氳繃 httpx 鍙戦€佽姹傦紝鍖呮嫭 query 鍙傛暟鍜岃姹備綋
            response = await client.request(
                method=request.method,
                url="https://openapi.ihr360.com/" + full_path,
                json=req_body,
                params=request.query_params  # 浼犻€掑師濮嬫煡璇㈠弬鏁?
            )
            response.raise_for_status()
            return maybe_envelope(request, response.json(), source="ihr")
        except httpx.RequestError as exc:
            # 缃戠粶闂鎴栨棤鏁堝搷搴?
            raise HTTPException(status_code=500, detail=str(exc))

        # 杩斿洖浠庣洰鏍嘇PI鏀跺埌鐨勫搷搴?


@app.post("/lx_openapi/erp/sc/routing/data/local_inventory/batchGetProductInfo")
async def lx_batch_get_product_info(request: Request):
    resp = await lx_openapi_request(full_path="erp/sc/routing/data/local_inventory/productList", request=request)
    if resp.code == 0:
        resp_data = resp.data
        product_ids = [item['id'] for item in resp_data]
        chunk_size = 100
        smaller_lists = [product_ids[i:i + chunk_size] for i in range(0, len(product_ids), chunk_size)]
        merged_data = []
        base_resp = None
        for sublist in smaller_lists:
            product_ids_req = {"productIds": sublist}
            product_resp = await lx_product_openapi_request(req_body=product_ids_req)
            if base_resp is None:
                base_resp = product_resp
            if product_resp and isinstance(product_resp.data, list):
                merged_data.extend(product_resp.data)
        if base_resp is not None:
            base_resp.data = merged_data
            print(f"product count {len(base_resp.data)}")
            return base_resp
    return resp



@app.api_route("/lx_openapi/{full_path:path}",
               methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH", "TRACE"])
async def lx_api_proxy_request(request: Request, full_path: str):
    """
    閫氳繃鎻愪緵鐨?openapi鐧诲綍锛屽弽鍚戜唬鐞嗚姹傚埌棰嗘槦openapi锛屽苟杩斿洖鍝嶅簲锛堜笉闇€瑕佽璇侊級
    """
    if not _is_openapi_path_allowed(full_path):
        raise HTTPException(status_code=403, detail=f"OpenAPI path not allowed: /{full_path.strip('/')}")
    resp = await lx_openapi_request(full_path=full_path, request=request)
    return maybe_envelope(request, resp.model_dump(), source="lingxing-openapi")

@app.get("/lx_downfile")
async def lx_downfile(request: Request):
    url = f"https://vayi.lingxing.com/api/download/downloadCenterReport/downloadResource?report_id={request.query_params.get('report_id')}"
    header = await set_header()
    await download_file(url=url, headers=header)


@app.api_route("/lx_web/{full_path:path}",
               methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH", "TRACE"])
async def lx_web_proxy_request(request: Request, full_path: str):
    """
    閫氳繃妯℃嫙鐧诲綍锛屽弽鍚戜唬鐞嗚姹傚埌棰嗘槦web API锛屽苟杩斿洖鍝嶅簲銆?
    """
    target_url = _build_and_validate_web_url(full_path)
    parsed_target = urlparse(target_url)
    header = await set_header()
    req_time_seq = parsed_target.path + "$$"
    req_body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        if request.headers.get('Content-Type', '').startswith('application/json'):
            try:
                body = await request.body()
                req_body = json.loads(body.decode("utf-8"))
                if req_body.get("offset") is not None:
                    req_time_seq = req_time_seq + str(req_body.get("offset") // req_body.get("length") + 1)
                    req_body["req_time_sequence"] = req_time_seq
                else:
                    req_body["req_time_sequence"] = req_time_seq + "1"
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON data received")
        else:
            raise HTTPException(status_code=415, detail="Unsupported Media Type or Missing JSON Content-Type")

    async with httpx.AsyncClient(headers=header, timeout=180) as client:
        logger.info(header)
        try:
            logger.info(f"Requesting {req_body}")
            # 閫氳繃 httpx 鍙戦€佽姹傦紝鍖呮嫭 query 鍙傛暟鍜岃姹備綋
            response = await client.request(
                method=request.method,
                url=target_url,
                json=req_body,
                params=request.query_params,  # 浼犻€掑師濮嬫煡璇㈠弬鏁?
            )
            response.raise_for_status()
            return maybe_envelope(request, response.json(), source="lingxing-web")
        except httpx.HTTPStatusError as exc:
            logger.info(f"HTTP error occurred: {exc.response.status_code}")
            raise HTTPException(status_code=500, detail=str(exc))
        except httpx.RequestError as exc:
            logger.info(f"An error occurred while requesting: {exc}")
            raise HTTPException(status_code=500, detail=str(exc))
        except Exception as exc:
            logger.info(f"An unexpected error occurred: {exc}")
            raise HTTPException(status_code=500, detail=str(exc))


@lingxing_openapi
async def lx_openapi_request(access_token, op_api, full_path: str, request: Request):
    request_id = getattr(request.state, "request_id", "")
    started_at = time.perf_counter()
    full_path = "/" + full_path
    # 鏍规嵁璇锋眰绫诲瀷澶勭悊璇锋眰浣?
    req_body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        if request.headers.get('Content-Type', '').startswith('application/json'):
            try:
                body = await request.body()
                req_body = json.loads(body.decode("utf-8"))
                # 鍒ゆ柇 req_body 涓槸鍚︽湁 length 閿絾娌℃湁 offset 閿?
                if req_body and isinstance(req_body, dict) and "length" in req_body and "offset" not in req_body:
                    req_body["offset"] = 0
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON data received")
        else:
            raise HTTPException(status_code=415, detail="Unsupported Media Type or Missing JSON Content-Type")
    route_key = full_path.strip("/")
    route_options = OPENAPI_ROUTE_OPTIONS.get(route_key, {})
    resp = await op_api.request(
        access_token,
        full_path,
        request.method,
        req_params=request.query_params,
        req_body=req_body,
        **route_options,
    )
    if not resp.request_id:
        resp.request_id = request_id
    logger.info(
        "openapi.result request_id=%s path=%s code=%s message=%s cost_ms=%s",
        request_id,
        full_path,
        resp.code,
        resp.message,
        round((time.perf_counter() - started_at) * 1000, 2),
    )
    return resp


@app.get("/generate_dates/")
def generate_dates(
        start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
        end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
        format: str = Query("%Y-%m-%d", description="Date format")
) -> List[Dict[str, str]]:
    """
    Generate a list of dates between specified start and end dates.

    :param start_date: Start date in YYYY-MM-DD format
    :param end_date: End date in YYYY-MM-DD format
    :param format: Date format
    :return: List of dates in the specified format
    """
    start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")

    if start_date_dt > end_date_dt:
        start_date_dt, end_date_dt = end_date_dt, start_date_dt

    days_difference = (end_date_dt - start_date_dt).days + 1
    date_list = [{"day": (start_date_dt + timedelta(days=i)).strftime(format)} for i in range(days_difference)]

    return date_list


@lingxing_openapi
async def lx_product_openapi_request(access_token, op_api, req_body):
    full_path = "/erp/sc/routing/data/local_inventory/batchGetProductInfo"
    resp = await op_api.request(access_token, full_path, "POST",
                                req_body=req_body)
    return resp


class ResponseData(BaseModel):
    url: str
    data: str


@app.post("/log_response")
async def log_response(response: ResponseData):
    print(f"接收数据: {response.url}:{response.data}")
    return {"status": "success"}


allowed_tables = set(Config.ALLOWED_TABLES)


class TableNameRequest(BaseModel):
    table_name: str


"""
娓呴櫎postgresql涓〃閲岄潰鐨勫唴瀹?
"""


@app.post("/clear_table")
async def clear_table(request: TableNameRequest):
    table_name = request.table_name
    logger.info(f"Received request to clear table: {table_name}")
    if not TABLE_NAME_PATTERN.match(table_name):
        logger.error(f"Invalid table name format: {table_name}")
        raise HTTPException(status_code=400, detail="Invalid table name")
    if table_name not in allowed_tables:
        logger.error(f"Table name {table_name} is not allowed")
        raise HTTPException(status_code=400, detail="Table name not allowed")

    async with AsyncPostgres() as conn:
        try:
            await conn.execute(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE')
            logger.info(f"Table {table_name} cleared successfully")
            return {"message": f"Table {table_name} cleared successfully"}
        except Exception as e:
            logger.error(f"Failed to clear table {table_name}: {e}")
            raise HTTPException(status_code=500, detail="Failed to clear the table")


k3api_sdk = Ext_k3sdk()
k3api_sdk.InitConfig(Config.K3_APP_ID, Config.K3_ACCOUNT, Config.K3_APP_SECRET, Config.K3_SERVICE_SECRET,
                     Config.K3_BASE_URL)


@app.post("/k3/bill_query")
async def k3_bill_query(request: Request):
    body = await request.json()
    response = k3api_sdk.BillQuery(body)
    return maybe_envelope(request, json.loads(response), source="k3")


@app.post("/k3/sys_report_query")
async def k3_sys_report_query(request: Request):
    body = await request.json()
    form_id = body.get("formId")
    data = body.get("data")
    response = k3api_sdk.getSysReportData(form_id, data)
    return maybe_envelope(request, json.loads(response), source="k3")


@app.post("/k3/stock_report")
async def k3_stock_report_query(request: Request):
    body = await request.json()

    response = k3api_sdk.stock_report(body)
    return maybe_envelope(request, json.loads(response), source="k3")


@app.post("/k3/query_bussiness_info")
async def k3_query_bussiness_info(request: Request):
    body = await request.json()

    metadata = k3api_sdk.QueryBusinessInfo(body)
    metadata = json.loads(metadata)
    # 鍒濆鍖栦竴涓垪琛ㄦ潵瀛樺偍瀛楁淇℃伅
    fields_info = {}

    try:
        # 妫€鏌?Entrys'閿槸鍚﹀瓨鍦ㄤ簬鍏冩暟鎹腑
        entries = metadata['Result']['NeedReturnData']['Entrys']
    except KeyError:
        print("The expected data structure is missing in the metadata.")
        return fields_info  # 杩斿洖绌哄垪琛?

    # 閬嶅巻姣忎釜鏉＄洰
    for entry in entries:
        try:
            # 鑾峰彇姣忎釜鏉＄洰涓殑'Fields'鏁扮粍
            fields = entry['Fields']
        except KeyError:
            # 濡傛灉鏉＄洰涓病鏈?Fields'閿紝缁х画澶勭悊涓嬩竴涓潯鐩?
            continue

        # 閬嶅巻姣忎釜瀛楁
        for field in fields:
            try:
                # 鎻愬彇瀛楁鍚嶅拰瀛楁鍚嶇О
                field_name = field['FieldName']
                # 鍋囪璇█浠ｇ爜2052瀵瑰簲鐨勫悕绉?
                human_readable_name = next((name['Value'] for name in field['Name'] if name['Key'] == 2052), None)
                # 纭繚瀛楁鍚嶅拰瀛楁鍚嶇О閮藉瓨鍦?
                if field_name and human_readable_name:
                    fields_info.update({field_name: human_readable_name})
            except KeyError:
                # 濡傛灉瀛楁缂哄け蹇呰鐨勯敭锛岃褰曡繖涓€寮傚父鎯呭喌骞剁户缁?
                print(f"Missing necessary information in field: {field}")
                continue
    keys_string = ', '.join(f"{key}" for key in fields_info.keys())
    fields_info['keys_string'] = keys_string
    return maybe_envelope(request, fields_info, source="k3")


client = MongoClient(Config.MONGO_VIEW_URI)
db = client[Config.MONGO_VIEW_DB]  # 鏇挎崲涓轰綘鐨勬暟鎹簱鍚?

class QueryParams(BaseModel):
    view_name: str
    conditions: Dict[str, Dict[str, Any]]
    skip: Optional[int] = 0
    limit: Optional[int] = 10


@app.post("/mongodb/view/")
async def get_items(request: Request, query_params: QueryParams = Body(...)):
    # 鏍规嵁瑙嗗浘鍚嶈幏鍙栭泦鍚?
    collection = db[query_params.view_name]

    # 鏋勫缓鏌ヨ鏉′欢
    query = query_params.conditions

    # 鏌ヨ骞跺垎椤?
    items = collection.find(query).skip(query_params.skip).limit(query_params.limit)

    # 杞崲涓哄垪琛ㄥ苟杩斿洖
    result = []
    for item in items:
        item["_id"] = str(item["_id"])  # 灏?ObjectId 杞崲涓哄瓧绗︿覆
        item["id"] = item["_id"]
        result.append(item)

    return maybe_envelope(request, result, source="mongodb-view")



# 鍒涘缓鑷畾涔変簨浠堕挬瀛?
async def download_file(url, headers=None):
    """
    浣跨敤httpx涓嬭浇鏂囦欢锛岃褰?02閲嶅畾鍚戣繃绋?

    鍙傛暟:
    url (str): 涓嬭浇閾炬帴
    cookies (dict): 璇锋眰鎵€闇€鐨刢ookies

    杩斿洖:
    str: 涓嬭浇鏂囦欢鐨勮矾寰?
    """
    logger.info(f"寮€濮嬩笅杞? {url}")

    # 瀹氫箟浜嬩欢閽╁瓙鍑芥暟
    def log_request(request):
        logger.debug(f"璇锋眰: {request.method} {request.url}")
        logger.debug(f"璇锋眰澶? {dict(request.headers)}")
        return request

    def log_response(response):
        logger.debug(f"鍝嶅簲鐘舵€? {response.status_code}")
        logger.debug(f"鍝嶅簲澶? {dict(response.headers)}")

        if 300 <= response.status_code < 400:
            location = response.headers.get('location')
            logger.debug(f"閲嶅畾鍚戝埌: {location}")

        return response

    # 鍒涘缓浜嬩欢閽╁瓙瀛楀吀
    event_hooks = {
        "request": [log_request],
        "response": [log_response]
    }

    # 鍒涘缓httpx瀹㈡埛绔?
    async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0,
            event_hooks=event_hooks
    ) as client:
        # 璁板綍鍒濆璇锋眰
        logger.info("Sending initial request")
        if headers:
            logger.debug(f"浣跨敤cookies: {headers}")

        # 鍙戦€丟ET璇锋眰
        try:
            headers[""]="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
            response = await client.get(url, headers=headers)

            # 妫€鏌ュ搷搴旂姸鎬?
            response.raise_for_status()

            # 璁板綍鏈€缁堢姸鎬?
            logger.info(f"鏈€缁堝搷搴旂姸鎬佺爜: {response.status_code}")
            logger.debug(f"鏈€缁堝搷搴擴RL: {response.url}")

            # 鑾峰彇鏂囦欢鍚?
            content_disposition = response.headers.get('content-disposition')
            if content_disposition and 'filename=' in content_disposition:
                # 鎻愬彇鏂囦欢鍚?
                filename = content_disposition.split('filename=')[1].strip('"\'')
                logger.info(f"浠庡搷搴斿ご鑾峰彇鏂囦欢鍚? {filename}")
            else:
                # 浣跨敤榛樿鏂囦欢鍚?
                filename = "downloaded_report.xlsx"
                logger.info(f"浣跨敤榛樿鏂囦欢鍚? {filename}")

            # 淇濆瓨鏂囦欢
            logger.info(f"寮€濮嬩繚瀛樻枃浠? {filename}")
            with open(filename, 'wb') as f:
                f.write(response.content)

            file_path = os.path.abspath(filename)
            logger.info(f"鏂囦欢淇濆瓨瀹屾垚: {file_path}")
            return file_path

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP閿欒: {e}")
            raise
        except Exception as e:
            logger.error(f"涓嬭浇杩囩▼涓嚭閿? {e}")
            raise


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8088)

