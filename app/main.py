import asyncio
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
from lingxingopenapi.resp_schema import ResponseResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
OPENAPI_ALLOWED_PATHS = set(Config.OPENAPI_ALLOWED_PATHS)
WEB_ALLOWED_HOSTS = set(Config.WEB_ALLOWED_HOSTS)
TABLE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
OPENAPI_ROUTE_OPTIONS = {
    # 订单利润报表耗时通常更长，单独放宽超时与重试
    "basicOpen/finance/mreport/OrderProfit": {
        "timeout": int(os.getenv("ORDER_PROFIT_TIMEOUT_SECONDS", "120")),
        "retries": int(os.getenv("ORDER_PROFIT_RETRIES", "3")),
        "total_timeout": int(os.getenv("ORDER_PROFIT_TOTAL_TIMEOUT_SECONDS", "180")),
        "lock_wait_timeout_seconds": float(os.getenv("ORDER_PROFIT_LOCK_WAIT_TIMEOUT_SECONDS", "12")),
    },
    # listing 在 ETL 中调用频繁，重点控制整体耗时，避免 FDL 读超时
    "erp/sc/data/mws/listing": {
        "timeout": int(os.getenv("MWS_LISTING_TIMEOUT_SECONDS", "25")),
        "retries": int(os.getenv("MWS_LISTING_RETRIES", "1")),
        "total_timeout": int(os.getenv("MWS_LISTING_TOTAL_TIMEOUT_SECONDS", "55")),
        "lock_wait_timeout_seconds": float(os.getenv("MWS_LISTING_LOCK_WAIT_TIMEOUT_SECONDS", "8")),
    },
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
    娴犲丢HR360閼惧嘲褰囬幍鈧張澶婃喅瀹搞儳娈戦崺鐑樻拱娣団剝浼呴妴鍌濆殰瀹稿崬鐨濈憗鍜冪礉閼奉亜鐢幒銉ュ經娑撳秷鍏樻稉鈧▎鈩冣偓褑骞忛崣鏍ㄥ閺堝鎲冲銉や繆閹垬鈧?
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
        # 濮ｅ繑顐兼径鍕倞閺堚偓婢?000娑撶嫪Ds
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
    闁俺绻冨Ο鈩冨珯閻ц缍嶉敍灞藉冀閸氭垳鍞悶鍡氼嚞濮瑰倸鍩宨hr360閿涘苯鑻熸潻鏂挎礀閸濆秴绨查妴?
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
            # 闁俺绻?httpx 閸欐垿鈧浇顕Ч鍌︾礉閸栧懏瀚?query 閸欏倹鏆熼崪宀冾嚞濮瑰倷缍?
            response = await client.request(
                method=request.method,
                url="https://openapi.ihr360.com/" + full_path,
                json=req_body,
                params=request.query_params  # 娴肩娀鈧帒甯慨瀣叀鐠囥垹寮弫?
            )
            response.raise_for_status()
            return maybe_envelope(request, response.json(), source="ihr")
        except httpx.RequestError as exc:
            # 缂冩垹绮堕梻顕€顣介幋鏍ㄦ￥閺佸牆鎼锋惔?
            raise HTTPException(status_code=500, detail=str(exc))

        # 鏉╂柨娲栨禒搴ｆ窗閺嶅槆PI閺€璺哄煂閻ㄥ嫬鎼锋惔?


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
    闁俺绻冮幓鎰返閻?openapi閻ц缍嶉敍灞藉冀閸氭垳鍞悶鍡氼嚞濮瑰倸鍩屾０鍡樻Еopenapi閿涘苯鑻熸潻鏂挎礀閸濆秴绨查敍鍫滅瑝闂団偓鐟曚浇顓荤拠渚婄礆
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
    闁俺绻冨Ο鈩冨珯閻ц缍嶉敍灞藉冀閸氭垳鍞悶鍡氼嚞濮瑰倸鍩屾０鍡樻Еweb API閿涘苯鑻熸潻鏂挎礀閸濆秴绨查妴?
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
            # 闁俺绻?httpx 閸欐垿鈧浇顕Ч鍌︾礉閸栧懏瀚?query 閸欏倹鏆熼崪宀冾嚞濮瑰倷缍?
            response = await client.request(
                method=request.method,
                url=target_url,
                json=req_body,
                params=request.query_params,  # 娴肩娀鈧帒甯慨瀣叀鐠囥垹寮弫?
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
    # 閺嶈宓佺拠閿嬬湴缁鐎锋径鍕倞鐠囬攱鐪版担?
    req_body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        if request.headers.get('Content-Type', '').startswith('application/json'):
            try:
                body = await request.body()
                req_body = json.loads(body.decode("utf-8"))
                # 閸掋倖鏌?req_body 娑擃厽妲搁崥锔芥箒 length 闁款喕绲惧▽鈩冩箒 offset 闁?
                if req_body and isinstance(req_body, dict) and "length" in req_body and "offset" not in req_body:
                    req_body["offset"] = 0
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON data received")
        else:
            raise HTTPException(status_code=415, detail="Unsupported Media Type or Missing JSON Content-Type")
    route_key = full_path.strip("/")
    if route_key == "erp/sc/data/mws/listing":
        sid = req_body.get("sid") if isinstance(req_body, dict) else None
        if not sid:
            logger.warning(
                "openapi.invalid_param request_id=%s path=%s missing=sid body=%s",
                request_id,
                full_path,
                req_body,
            )
            return ResponseResult(
                code=102,
                message="参数不合法：sid 不能为空",
                data=[],
                error_details={
                    "hint": "请在 ETL 的 listing 请求体中传入 sid（店铺ID）",
                    "example": {"sid": "123456", "offset": 0, "length": 30},
                },
                request_id=request_id,
            )
    route_options = dict(OPENAPI_ROUTE_OPTIONS.get(route_key, {}))
    total_timeout = int(route_options.pop("total_timeout", os.getenv("OPENAPI_TOTAL_TIMEOUT_SECONDS", "90")))
    try:
        resp = await asyncio.wait_for(
            op_api.request(
                access_token,
                full_path,
                request.method,
                req_params=request.query_params,
                req_body=req_body,
                **route_options,
            ),
            timeout=total_timeout,
        )
    except asyncio.TimeoutError:
        logger.error("openapi.total_timeout request_id=%s path=%s total_timeout=%ss", request_id, full_path, total_timeout)
        return ResponseResult(code=-1, message=f"request timeout(total): {total_timeout}s", data=None, request_id=request_id)
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
    print(f"鎺ユ敹鏁版嵁: {response.url}:{response.data}")
    return {"status": "success"}


allowed_tables = set(Config.ALLOWED_TABLES)


class TableNameRequest(BaseModel):
    table_name: str


"""
濞撳懘娅巔ostgresql娑擃叀銆冮柌宀勬桨閻ㄥ嫬鍞寸€?
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
    # 閸掓繂顫愰崠鏍︾娑擃亜鍨悰銊︽降鐎涙ê鍋嶇€涙顔屾穱鈩冧紖
    fields_info = {}

    try:
        # 濡偓閺?Entrys'闁款喗妲搁崥锕€鐡ㄩ崷銊ょ艾閸忓啯鏆熼幑顔昏厬
        entries = metadata['Result']['NeedReturnData']['Entrys']
    except KeyError:
        print("The expected data structure is missing in the metadata.")
        return fields_info  # 鏉╂柨娲栫粚鍝勫灙鐞?

    # 闁秴宸诲В蹇庨嚋閺夛紕娲?
    for entry in entries:
        try:
            # 閼惧嘲褰囧В蹇庨嚋閺夛紕娲版稉顓犳畱'Fields'閺佹壆绮?
            fields = entry['Fields']
        except KeyError:
            # 婵″倹鐏夐弶锛勬窗娑擃厽鐥呴張?Fields'闁款噯绱濈紒褏鐢绘径鍕倞娑撳绔存稉顏呮蒋閻?
            continue

        # 闁秴宸诲В蹇庨嚋鐎涙顔?
        for field in fields:
            try:
                # 閹绘劕褰囩€涙顔岄崥宥呮嫲鐎涙顔岄崥宥囆?
                field_name = field['FieldName']
                # 閸嬪洩顔曠拠顓♀枅娴狅絿鐖?052鐎电懓绨查惃鍕倳缁?
                human_readable_name = next((name['Value'] for name in field['Name'] if name['Key'] == 2052), None)
                # 绾喕绻氱€涙顔岄崥宥呮嫲鐎涙顔岄崥宥囆為柈钘夌摠閸?
                if field_name and human_readable_name:
                    fields_info.update({field_name: human_readable_name})
            except KeyError:
                # 婵″倹鐏夌€涙顔岀紓鍝勩亼韫囧懓顩﹂惃鍕暛閿涘矁顔囪ぐ鏇＄箹娑撯偓瀵倸鐖堕幆鍛枌楠炲墎鎴风紒?
                print(f"Missing necessary information in field: {field}")
                continue
    keys_string = ', '.join(f"{key}" for key in fields_info.keys())
    fields_info['keys_string'] = keys_string
    return maybe_envelope(request, fields_info, source="k3")


client = MongoClient(Config.MONGO_VIEW_URI)
db = client[Config.MONGO_VIEW_DB]  # 閺囨寧宕叉稉杞扮稑閻ㄥ嫭鏆熼幑顔肩氨閸?

class QueryParams(BaseModel):
    view_name: str
    conditions: Dict[str, Dict[str, Any]]
    skip: Optional[int] = 0
    limit: Optional[int] = 10


@app.post("/mongodb/view/")
async def get_items(request: Request, query_params: QueryParams = Body(...)):
    # 閺嶈宓佺憴鍡楁禈閸氬秷骞忛崣鏍肠閸?
    collection = db[query_params.view_name]

    # 閺嬪嫬缂撻弻銉嚄閺夆€叉
    query = query_params.conditions

    # 閺屻儴顕楅獮璺哄瀻妞?
    items = collection.find(query).skip(query_params.skip).limit(query_params.limit)

    # 鏉烆剚宕叉稉鍝勫灙鐞涖劌鑻熸潻鏂挎礀
    result = []
    for item in items:
        item["_id"] = str(item["_id"])  # 鐏?ObjectId 鏉烆剚宕叉稉鍝勭摟缁楋缚瑕?
        item["id"] = item["_id"]
        result.append(item)

    return maybe_envelope(request, result, source="mongodb-view")



# 閸掓稑缂撻懛顏勭暰娑斿绨ㄦ禒鍫曟尙鐎?
async def download_file(url, headers=None):
    """
    娴ｈ法鏁ttpx娑撳娴囬弬鍥︽閿涘矁顔囪ぐ?02闁插秴鐣鹃崥鎴ｇ箖缁?

    閸欏倹鏆?
    url (str): 娑撳娴囬柧鐐复
    cookies (dict): 鐠囬攱鐪伴幍鈧棁鈧惃鍒okies

    鏉╂柨娲?
    str: 娑撳娴囬弬鍥︽閻ㄥ嫯鐭惧?
    """
    logger.info(f"瀵偓婵绗呮潪? {url}")

    # 鐎规矮绠熸禍瀣╂闁解晛鐡欓崙鑺ユ殶
    def log_request(request):
        logger.debug(f"鐠囬攱鐪? {request.method} {request.url}")
        logger.debug(f"鐠囬攱鐪版径? {dict(request.headers)}")
        return request

    def log_response(response):
        logger.debug(f"閸濆秴绨查悩鑸碘偓? {response.status_code}")
        logger.debug(f"閸濆秴绨叉径? {dict(response.headers)}")

        if 300 <= response.status_code < 400:
            location = response.headers.get('location')
            logger.debug(f"闁插秴鐣鹃崥鎴濆煂: {location}")

        return response

    # 閸掓稑缂撴禍瀣╂闁解晛鐡欑€涙鍚€
    event_hooks = {
        "request": [log_request],
        "response": [log_response]
    }

    # 閸掓稑缂揾ttpx鐎广垺鍩涚粩?
    async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0,
            event_hooks=event_hooks
    ) as client:
        # 鐠佹澘缍嶉崚婵嗩潗鐠囬攱鐪?
        logger.info("Sending initial request")
        if headers:
            logger.debug(f"娴ｈ法鏁ookies: {headers}")

        # 閸欐垿鈧笩ET鐠囬攱鐪?
        try:
            headers[""]="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
            response = await client.get(url, headers=headers)

            # 濡偓閺屻儱鎼锋惔鏃傚Ц閹?
            response.raise_for_status()

            # 鐠佹澘缍嶉張鈧紒鍫㈠Ц閹?
            logger.info(f"閺堚偓缂佸牆鎼锋惔鏃傚Ц閹胶鐖? {response.status_code}")
            logger.debug(f"閺堚偓缂佸牆鎼锋惔鎿碦L: {response.url}")

            # 閼惧嘲褰囬弬鍥︽閸?
            content_disposition = response.headers.get('content-disposition')
            if content_disposition and 'filename=' in content_disposition:
                # 閹绘劕褰囬弬鍥︽閸?
                filename = content_disposition.split('filename=')[1].strip('"\'')
                logger.info(f"娴犲骸鎼锋惔鏂裤仈閼惧嘲褰囬弬鍥︽閸? {filename}")
            else:
                # 娴ｈ法鏁ゆ妯款吇閺傚洣娆㈤崥?
                filename = "downloaded_report.xlsx"
                logger.info(f"娴ｈ法鏁ゆ妯款吇閺傚洣娆㈤崥? {filename}")

            # 娣囨繂鐡ㄩ弬鍥︽
            logger.info(f"瀵偓婵绻氱€涙ɑ鏋冩禒? {filename}")
            with open(filename, 'wb') as f:
                f.write(response.content)

            file_path = os.path.abspath(filename)
            logger.info(f"閺傚洣娆㈡穱婵嗙摠鐎瑰本鍨? {file_path}")
            return file_path

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP闁挎瑨顕? {e}")
            raise
        except Exception as e:
            logger.error(f"娑撳娴囨潻鍥┾柤娑擃厼鍤柨? {e}")
            raise


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8088)


