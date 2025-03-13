#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""封装Openapi基础操作"""
import asyncio
import copy
import time
from typing import Optional

from lingxingopenapi.http_util import HttpBase
from lingxingopenapi.resp_schema import AccessTokenDto, ResponseResult
from lingxingopenapi.sign import SignBase
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenApiBase(object):

    def __init__(self, host: str = "https://openapi.lingxing.com", app_id: str = "ak_dLMBP259Pb5wH",
                 app_secret: str = "BYKn4e/XVg+shbQPVbMjiQ=="):
        self.host = host
        self.app_id = app_id
        self.app_secret = app_secret

    async def generate_access_token(self) -> AccessTokenDto:
        """
        获取 access_token
        """
        path = '/api/auth-server/oauth/access-token'
        req_url = self.host + path
        req_params = {
            "appId": self.app_id,
            "appSecret": self.app_secret,
        }
        resp_result = await HttpBase().request("POST", req_url, params=req_params)
        if resp_result.code != 200:
            error_msg = f"generate_access_token failed, reason: {resp_result.message}"
            raise ValueError(error_msg)

        assert isinstance(resp_result.data, dict)
        return AccessTokenDto(**resp_result.data)

    async def refresh_token(self, refresh_token: str) -> AccessTokenDto:
        """续约access-token"""
        path = '/api/auth-server/oauth/refresh'
        req_url = self.host + path
        req_params = {
            "appId": self.app_id,
            "refreshToken": refresh_token,
        }
        resp_result = await HttpBase().request("POST", req_url, params=req_params)
        if resp_result.code != 200:
            error_msg = f"refresh_token failed, reason: {resp_result.message}"
            raise ValueError(error_msg)

        assert isinstance(resp_result.data, dict)
        return AccessTokenDto(**resp_result.data)

    async def request(self, access_token: str, route_name: str, method: str,
                      req_params: Optional[dict] = None,
                      req_body: Optional[dict] = None,
                      retries: int = 10,
                      **kwargs) -> ResponseResult:
        """
        :param access_token:
        :param route_name: 请求路径
        :param method: GET/POST/PUT,etc
        :param req_params: query参数放这里, 没有则不传
        :param req_body: 请求体参数放这里, 没有则不传
        :param retries: 重试次数
        :param kwargs: timeout 等其他字段可以放这里
        :return:
        """
        req_url = self.host + route_name
        headers = kwargs.pop('headers', {})

        retry_count = 0
        while retry_count <= retries:
            try:
                # 每次重试重新生成签名参数
                current_req_params = copy.deepcopy(req_params) if req_params else {}
                gen_sign_params = copy.deepcopy(req_body) if req_body else {}
                if current_req_params:
                    gen_sign_params.update(current_req_params)

                # 生成签名参数，每次重试使用最新的时间戳
                sign_params = {
                    "app_key": self.app_id,
                    "access_token": access_token,
                    "timestamp": f'{int(time.time())}',
                }
                gen_sign_params.update(sign_params)
                sign = SignBase.generate_sign(self.app_id, gen_sign_params)
                sign_params["sign"] = sign
                current_req_params.update(sign_params)

                # 对于带有请求体的, 需要设置默认的Content-Type
                current_headers = copy.deepcopy(headers)
                if req_body and 'Content-Type' not in current_headers:
                    current_headers['Content-Type'] = 'application/json'

                # 发送请求
                http_base = HttpBase()
                resp = await http_base.request_without_retry(method, req_url,
                                                             params=current_req_params,
                                                             headers=current_headers,
                                                             json=req_body,
                                                             **kwargs)

                # 检查业务响应码
                if str(resp.get("code")) == "3001008":
                    error_msg = f"业务错误, 错误码: {resp.get('code')}, 错误信息: {resp.get('message', '')}"
                    logger.error(error_msg)
                    if retry_count < retries:
                        retry_count += 1
                        wait_time = 2 ** retry_count  # 指数退避策略
                        logger.info(
                            f"业务错误，将在 {wait_time} 秒后重试 (剩余重试次数: {retries - retry_count})")
                        await asyncio.sleep(wait_time)
                        continue
                    raise ValueError(error_msg)
                logger.info(f"返回码: {resp.get('code','无')}, 返回信息: {resp.get('message', '无')}")
                return ResponseResult(**resp)

            except asyncio.TimeoutError as e:  # 捕获所有异常，包括HTTP错误和超时
                logger.error(f"请求异常: {str(e)}")
                if retry_count < retries:
                    retry_count += 1
                    wait_time = 2 ** retry_count  # 指数退避策略
                    logger.info(f"发生异常，将在 {wait_time} 秒后重试 (剩余重试次数: {retries - retry_count})")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("达到最大重试次数，请求失败")
                    raise

        # 这里不应该被执行到，但为了安全性添加
        raise ValueError("达到最大重试次数，请求失败")
