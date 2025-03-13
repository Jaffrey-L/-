#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""封装 Openapi的 http请求"""
import asyncio
import logging
from urllib.parse import urlencode
import aiohttp
import orjson
from typing import Optional
from lingxingopenapi.resp_schema import ResponseResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HttpBase(object):

    def __init__(self, default_timeout=180):
        self.default_timeout = default_timeout

    async def request_without_retry(self, method: str, req_url: str,
                                    params: Optional[dict] = None,
                                    json: Optional[dict] = None,
                                    headers: Optional[dict] = None,
                                    **kwargs) -> dict:
        """无重试逻辑的基础请求方法"""
        timeout = kwargs.pop('timeout', self.default_timeout)
        # 需要保持与加密算法一致的请求数据传递
        data = orjson.dumps(json, option=orjson.OPT_SORT_KEYS) if json else None

        async with aiohttp.ClientSession() as aio_session:
            async with aio_session.request(method=method, url=req_url, params=params, data=data,
                                           timeout=timeout, headers=headers, **kwargs) as resp:
                log_params = urlencode(params) if params else "无参数"
                logger.info(f"{method}--{req_url}?{log_params}")
                if data is not None:
                    logger.info(data.decode('utf-8'))
                else:
                    logger.info("No data to display.")

                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"HTTP错误, 状态码: {resp.status}, 响应内容: {error_text}")
                    raise ValueError(f"响应错误, 状态码: {resp.status}, 响应内容: {error_text}")

                return await resp.json()
