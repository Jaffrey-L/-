import asyncio
from datetime import datetime
from functools import wraps
import json
import logging
import os
import uuid

import aiofiles
import httpx

from app.config import Config
from app.gen_sensors_anonymous_id import generate_sensor_id
from app.lingxingpwd import encrypt_password
from lingxingopenapi.openapi import OpenApiBase

global_auth_data = None
_token_cache = {
    "access_token": None,
    "expires_at": 0,
}
_token_lock = asyncio.Lock()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def login():
    global global_auth_data

    if global_auth_data:
        if datetime.now().timestamp() - global_auth_data["timestamp"] < Config.AUTH_CACHE_TTL_SECONDS:
            return global_auth_data

    file_path = Config.AUTH_CACHE_FILE
    if os.path.exists(file_path):
        logger.info("读取认证文件")
        async with aiofiles.open(file_path, "r") as file:
            content = await file.read()
            data = json.loads(content)
            if datetime.now().timestamp() - data["timestamp"] < Config.AUTH_CACHE_TTL_SECONDS:
                global_auth_data = data
                return global_auth_data

    logger.info("重新登录")
    get_login_seckey_url = "https://gw.lingxingerp.com/newadmin/api/passport/getLoginSecretKey"
    login_url = "https://gw.lingxingerp.com/newadmin/api/passport/login"
    user_name = Config.WEB_ACCOUNT
    password = Config.WEB_PASSWORD
    headers = {
        "Content-Type": "application/json",
        "Ak-Origin": "https://vayi.lingxing.com",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(get_login_seckey_url)

        login_json_data = {
            "account": user_name,
            "pwd": encrypt_password(password, response.json()["data"]["secretKey"]),
            "verify_code": "",
            "uuid": str(uuid.uuid4()),
            "auto_login": 1,
            "sensorsAnonymousId": generate_sensor_id(),
            "secretId": response.json()["data"]["secretId"],
        }

        try:
            login_response = await client.post(login_url, json=login_json_data, headers=headers)
            response_json = login_response.json()
            if response_json["companyId"] == "90136094793908736":
                response_json["timestamp"] = datetime.now().timestamp()
                async with aiofiles.open(file_path, "w") as file:
                    await file.write(json.dumps(response_json, indent=4))
                global_auth_data = response_json
                return response_json
            logger.info(f"登录失败: {response_json}")
        except httpx.RequestError as e:
            logger.info(f"请求过程中出现问题: {e}")
        except httpx.HTTPStatusError as e:
            logger.info(f"HTTP状态错误: {e}")
        except Exception as e:
            logger.info(f"处理响应时出现问题: {e}")


async def ensure_access_token(op_api: OpenApiBase) -> str:
    now_ts = int(datetime.now().timestamp())
    if _token_cache["access_token"] and now_ts < int(_token_cache["expires_at"]) - 300:
        return _token_cache["access_token"]

    async with _token_lock:
        now_ts = int(datetime.now().timestamp())
        if _token_cache["access_token"] and now_ts < int(_token_cache["expires_at"]) - 300:
            return _token_cache["access_token"]

        logger.info("Generating access_token from app credentials")
        token_dto = await op_api.generate_access_token()
        _token_cache["access_token"] = token_dto.access_token
        _token_cache["expires_at"] = now_ts + int(token_dto.expires_in)
        return token_dto.access_token


def lingxing_openapi(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        op_api = OpenApiBase(host=Config.OPENAPI_HOST, app_id=Config.APP_ID, app_secret=Config.APP_SECRET)
        access_token = await ensure_access_token(op_api)
        return await func(access_token, op_api, *args, **kwargs)

    return wrapper


def before_call_login(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        login_info = await login()
        return await func(login_info, *args, **kwargs)

    return wrapper


if __name__ == "__main__":
    asyncio.run(login())
    print(global_auth_data)
