import json
import logging

import httpx
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel

from app.AsyncPostgres import AsyncPostgres
from app.ihr import login, fetch_all_pages
from app.lingxing import set_header
from app.lingxing_login import lingxing_openapi

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


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
    return results


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
            return response.json()
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
    resp = await lx_openapi_request(full_path=full_path, request=request)
    return resp


@app.api_route("/lx_web/{full_path:path}",
               methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH", "TRACE"])
async def lx_web_proxy_request(request: Request, full_path: str):
    """
    通过模拟登录，反向代理请求到领星web API，并返回响应。
    """
    header = await set_header()
    req_body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        if request.headers.get('Content-Type', '').startswith('application/json'):
            try:
                body = await request.body()
                req_body = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON data received")
        else:
            raise HTTPException(status_code=415, detail="Unsupported Media Type or Missing JSON Content-Type")

    async with httpx.AsyncClient(headers=header, timeout=180) as client:
        try:
            logger.info(f"Requesting {req_body}")
            # 通过 httpx 发送请求，包括 query 参数和请求体
            response = await client.request(
                method=request.method,
                url="https://" + full_path,
                json=req_body,
                params=request.query_params  # 传递原始查询参数
            )
            response.raise_for_status()
            return response.json()
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
    full_path = "/" + full_path
    # 根据请求类型处理请求体
    req_body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        if request.headers.get('Content-Type', '').startswith('application/json'):
            try:
                body = await request.body()
                req_body = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON data received")
        else:
            raise HTTPException(status_code=415, detail="Unsupported Media Type or Missing JSON Content-Type")
    resp = await op_api.request(access_token, full_path, request.method, req_params=request.query_params,
                                req_body=req_body)
    return resp


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


allowed_tables = ["lx_web_fba_inventory", "lx_inventory_by_wyt", "kd_v_just_inventory_eng"]


class TableNameRequest(BaseModel):
    table_name: str


"""
清楚postgresql中表里面的内容
"""


@app.post("/clear_table")
async def clear_table(request: TableNameRequest):
    table_name = request.table_name
    logger.info(f"Received request to clear table: {table_name}")
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8088)
