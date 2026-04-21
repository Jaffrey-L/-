#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""封装 OpenAPI 基础操作（稳定性增强版）"""
import asyncio
import copy
import os
import random
import time
from typing import Optional

from lingxingopenapi.http_util import HttpBase
from lingxingopenapi.resp_schema import AccessTokenDto, ResponseResult
from lingxingopenapi.sign import SignBase
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OpenApiBase(object):

    def __init__(self, host: str = None, app_id: str = None, app_secret: str = None):
        if host is None:
            host = os.getenv("LINGXING_OPENAPI_HOST", "https://openapi.lingxing.com")
        if app_id is None:
            app_id = os.getenv("LINGXING_APP_ID", "ak_dLMBP259Pb5wH")
        if app_secret is None:
            app_secret = os.getenv("LINGXING_APP_SECRET", "BYKn4e/XVg+shbQPVbMjiQ==")
        self.host = host
        self.app_id = app_id
        self.app_secret = app_secret

    async def generate_access_token(self) -> AccessTokenDto:
        path = '/api/auth-server/oauth/access-token'
        req_url = self.host + path
        req_params = {
            "appId": self.app_id,
            "appSecret": self.app_secret,
        }
        token_timeout = int(os.getenv("OPENAPI_TOKEN_TIMEOUT_SECONDS", os.getenv("OPENAPI_REQUEST_TIMEOUT_SECONDS", "20")))
        resp_result = await HttpBase().request("POST", req_url, params=req_params, timeout=token_timeout)
        if resp_result.code != 200:
            raise ValueError(f"generate_access_token failed, reason: {resp_result.message}")

        assert isinstance(resp_result.data, dict)
        return AccessTokenDto(**resp_result.data)

    async def refresh_token(self, refresh_token: str) -> AccessTokenDto:
        path = '/api/auth-server/oauth/refresh'
        req_url = self.host + path
        req_params = {
            "appId": self.app_id,
            "refreshToken": refresh_token,
        }
        token_timeout = int(os.getenv("OPENAPI_TOKEN_TIMEOUT_SECONDS", os.getenv("OPENAPI_REQUEST_TIMEOUT_SECONDS", "20")))
        resp_result = await HttpBase().request("POST", req_url, params=req_params, timeout=token_timeout)
        if resp_result.code != 200:
            raise ValueError(f"refresh_token failed, reason: {resp_result.message}")

        assert isinstance(resp_result.data, dict)
        return AccessTokenDto(**resp_result.data)

    async def request(self, access_token: str, route_name: str, method: str,
                      req_params: Optional[dict] = None,
                      req_body: Optional[dict] = None,
                      retries: Optional[int] = None,
                      **kwargs) -> ResponseResult:
        req_url = self.host + route_name
        headers = kwargs.pop('headers', {})

        if retries is None:
            retries = int(os.getenv("OPENAPI_RETRIES", "1"))
        max_backoff = int(os.getenv("OPENAPI_RETRY_MAX_BACKOFF_SECONDS", "2"))
        kwargs.setdefault('timeout', int(os.getenv("OPENAPI_REQUEST_TIMEOUT_SECONDS", "20")))

        retry_count = 0
        last_resp = None

        while retry_count <= retries:
            try:
                current_req_params = copy.deepcopy(req_params) if req_params else {}
                gen_sign_params = copy.deepcopy(req_body) if req_body else {}
                if current_req_params:
                    gen_sign_params.update(current_req_params)

                sign_params = {
                    "app_key": self.app_id,
                    "access_token": access_token,
                    "timestamp": f'{int(time.time())}',
                }
                gen_sign_params.update(sign_params)
                sign = SignBase.generate_sign(self.app_id, gen_sign_params)
                sign_params["sign"] = sign
                current_req_params.update(sign_params)

                current_headers = copy.deepcopy(headers)
                if req_body and 'Content-Type' not in current_headers:
                    current_headers['Content-Type'] = 'application/json'

                http_base = HttpBase()
                resp = await http_base.request_without_retry(
                    method,
                    req_url,
                    params=current_req_params,
                    headers=current_headers,
                    json=req_body,
                    **kwargs,
                )
                last_resp = resp

                code = str(resp.get("code"))
                if code in {"3001008", "103"}:
                    error_msg = f"业务错误 code={resp.get('code')} message={resp.get('message', '')}"
                    logger.error(error_msg)
                    if retry_count < retries:
                        retry_count += 1
                        wait_time = min(2 ** retry_count, max_backoff) + random.uniform(0, 0.3)
                        logger.info(
                            f"业务错误重试，{wait_time:.2f}s 后重试 (剩余 {retries - retry_count} 次)"
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    return ResponseResult(**resp)

                logger.info(f"返回码: {resp.get('code', '无')}, 返回信息: {resp.get('message', '无')}")
                return ResponseResult(**resp)

            except asyncio.TimeoutError as e:
                logger.error(f"请求超时: {e}")
                if retry_count < retries:
                    retry_count += 1
                    wait_time = min(2 ** retry_count, max_backoff) + random.uniform(0, 0.3)
                    logger.info(f"超时重试，{wait_time:.2f}s 后重试 (剩余 {retries - retry_count} 次)")
                    await asyncio.sleep(wait_time)
                    continue
                return ResponseResult(code=-1, message=f"request timeout: {str(e)}", data=None)

            except Exception as e:
                logger.error(f"请求异常: {e}")
                if retry_count < retries:
                    retry_count += 1
                    wait_time = min(2 ** retry_count, max_backoff) + random.uniform(0, 0.3)
                    logger.info(f"异常重试，{wait_time:.2f}s 后重试 (剩余 {retries - retry_count} 次)")
                    await asyncio.sleep(wait_time)
                    continue
                return ResponseResult(code=-1, message=f"request error: {str(e)}", data=None)

        if last_resp:
            return ResponseResult(**last_resp)
        return ResponseResult(code=-1, message="max retries exceeded", data=None)
