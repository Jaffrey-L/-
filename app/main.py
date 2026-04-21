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
from k3cloud_webapi_sdk.main import K3CloudApiSdk
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
    从IHR360获取所有员工的基本信息。自己封装，自带接口不能一次性获取所有员工信息。
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
        # 每次处理最多1000个IDs
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
    通过模拟登录，反向代理请求到ihr360，并返回响应。
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
            # 通过 httpx 发送请求，包括 query 参数和请求体
            response = await client.request(
                method=request.method,
                url="https://openapi.ihr360.com/" + full_path,
                json=req_body,
                params=request.query_params  # 传递原始查询参数
            )
            response.raise_for_status()
            return maybe_envelope(request, response.json(), source="ihr")
        except httpx.RequestError as exc:
            # 网络问题或无效响应
            raise HTTPException(status_code=500, detail=str(exc))

        # 返回从目标API收到的响应


@app.post("/lx_openapi/erp/sc/routing/data/local_inventory/batchGetProductInfo")
async def lx_batch_get_product_info(request: Request):
    resp = await lx_openapi_request(full_path="erp/sc/routing/data/local_inventory/productList", request=request)
    if resp.code == 0:
        product_resp = None
        resp_data = resp.data
        product_ids = [item['id'] for item in resp_data]
        chunk_size = 100
        smaller_lists = [product_ids[i:i + chunk_size] for i in range(0, len(product_ids), chunk_size)]
        i = 0
        for sublist in smaller_lists:
            productIds = {
                "productIds": sublist
            }
            product_resp = await lx_product_openapi_request(req_body=productIds)
            if i > 0:
                product_resp.data.extend(product_resp.data)
            i = i + 1
        print(f"产品数:{len(product_resp.data)}")
        return product_resp


@app.api_route("/lx_openapi/{full_path:path}",
               methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH", "TRACE"])
async def lx_api_proxy_request(request: Request, full_path: str):
    """
    通过提供的 openapi登录，反向代理请求到领星openapi，并返回响应（不需要认证）
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
    通过模拟登录，反向代理请求到领星web API，并返回响应。
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
            # 通过 httpx 发送请求，包括 query 参数和请求体
            response = await client.request(
                method=request.method,
                url=target_url,
                json=req_body,
                params=request.query_params  # 传递原始查询参数
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
    # 根据请求类型处理请求体
    req_body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        if request.headers.get('Content-Type', '').startswith('application/json'):
            try:
                body = await request.body()
                req_body = json.loads(body.decode("utf-8"))
                # 判断 req_body 中是否有 length 键但没有 offset 键
                if req_body and isinstance(req_body, dict) and "length" in req_body and "offset" not in req_body:
                    req_body["offset"] = 0
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON data received")
        else:
            raise HTTPException(status_code=415, detail="Unsupported Media Type or Missing JSON Content-Type")
    resp = await op_api.request(access_token, full_path, request.method, req_params=request.query_params,
                                req_body=req_body)
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
    print(f"接收数据：{response.url}:{response.data}")
    return {"status": "success"}


allowed_tables = set(Config.ALLOWED_TABLES)


class TableNameRequest(BaseModel):
    table_name: str


"""
清除postgresql中表里面的内容
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
    # 初始化一个列表来存储字段信息
    fields_info = {}

    try:
        # 检查'Entrys'键是否存在于元数据中
        entries = metadata['Result']['NeedReturnData']['Entrys']
    except KeyError:
        print("The expected data structure is missing in the metadata.")
        return fields_info  # 返回空列表

    # 遍历每个条目
    for entry in entries:
        try:
            # 获取每个条目中的'Fields'数组
            fields = entry['Fields']
        except KeyError:
            # 如果条目中没有'Fields'键，继续处理下一个条目
            continue

        # 遍历每个字段
        for field in fields:
            try:
                # 提取字段名和字段名称
                field_name = field['FieldName']
                # 假设语言代码2052对应的名称
                human_readable_name = next((name['Value'] for name in field['Name'] if name['Key'] == 2052), None)
                # 确保字段名和字段名称都存在
                if field_name and human_readable_name:
                    fields_info.update({field_name: human_readable_name})
            except KeyError:
                # 如果字段缺失必要的键，记录这一异常情况并继续
                print(f"Missing necessary information in field: {field}")
                continue
    keys_string = ', '.join(f"{key}" for key in fields_info.keys())
    fields_info['keys_string'] = keys_string
    return maybe_envelope(request, fields_info, source="k3")


client = MongoClient(Config.MONGO_VIEW_URI)
db = client[Config.MONGO_VIEW_DB]  # 替换为你的数据库名


class QueryParams(BaseModel):
    view_name: str
    conditions: Dict[str, Dict[str, Any]]
    skip: Optional[int] = 0
    limit: Optional[int] = 10


@app.post("/mongodb/view/")
async def get_items(request: Request, query_params: QueryParams = Body(...)):
    # 根据视图名获取集合
    collection = db[query_params.view_name]

    # 构建查询条件
    query = query_params.conditions

    # 查询并分页
    items = collection.find(query).skip(query_params.skip).limit(query_params.limit)

    # 转换为列表并返回
    result = []
    for item in items:
        item["_id"] = str(item["_id"])  # 将 ObjectId 转换为字符串
        item["id"] = item["_id"]
        result.append(item)

    return maybe_envelope(request, result, source="mongodb-view")



# 创建自定义事件钩子
async def download_file(url, headers=None):
    """
    使用httpx下载文件，记录302重定向过程

    参数:
    url (str): 下载链接
    cookies (dict): 请求所需的cookies

    返回:
    str: 下载文件的路径
    """
    logger.info(f"开始下载: {url}")

    # 定义事件钩子函数
    def log_request(request):
        logger.debug(f"请求: {request.method} {request.url}")
        logger.debug(f"请求头: {dict(request.headers)}")
        return request

    def log_response(response):
        logger.debug(f"响应状态: {response.status_code}")
        logger.debug(f"响应头: {dict(response.headers)}")

        if 300 <= response.status_code < 400:
            location = response.headers.get('location')
            logger.debug(f"重定向到: {location}")

        return response

    # 创建事件钩子字典
    event_hooks = {
        "request": [log_request],
        "response": [log_response]
    }

    # 创建httpx客户端
    async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0,
            event_hooks=event_hooks
    ) as client:
        # 记录初始请求
        logger.info("发送初始请求")
        if headers:
            logger.debug(f"使用cookies: {headers}")

        # 发送GET请求
        try:
            headers[""]="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
            response = await client.get(url, headers=headers)

            # 检查响应状态
            response.raise_for_status()

            # 记录最终状态
            logger.info(f"最终响应状态码: {response.status_code}")
            logger.debug(f"最终响应URL: {response.url}")

            # 获取文件名
            content_disposition = response.headers.get('content-disposition')
            if content_disposition and 'filename=' in content_disposition:
                # 提取文件名
                filename = content_disposition.split('filename=')[1].strip('"\'')
                logger.info(f"从响应头获取文件名: {filename}")
            else:
                # 使用默认文件名
                filename = "downloaded_report.xlsx"
                logger.info(f"使用默认文件名: {filename}")

            # 保存文件
            logger.info(f"开始保存文件: {filename}")
            with open(filename, 'wb') as f:
                f.write(response.content)

            file_path = os.path.abspath(filename)
            logger.info(f"文件保存完成: {file_path}")
            return file_path

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP错误: {e}")
            raise
        except Exception as e:
            logger.error(f"下载过程中出错: {e}")
            raise


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8088)
