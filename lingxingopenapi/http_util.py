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

    async def request(self, method: str, req_url: str,
                      params: Optional[dict] = None,
                      json: Optional[dict] = None,
                      headers: Optional[dict] = None,
                      retries: int = 10,
                      **kwargs) -> ResponseResult:
        timeout = kwargs.pop('timeout', self.default_timeout)
        # 需要保持与加密算法一致的请求数据传递
        data = orjson.dumps(json, option=orjson.OPT_SORT_KEYS) if json else None
        retry_count = 0
        while retry_count <= retries:
            try:
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
                            if retry_count < retries:
                                retry_count += 3
                                wait_time = 2 ** retry_count  # 指数退避策略
                                logger.info(
                                    f"请求失败，将在 {wait_time} 秒后重试 (剩余重试次数: {retries - retry_count})")
                                await asyncio.sleep(wait_time)
                                continue
                            raise ValueError(f"响应错误, 状态码: {resp.status}, 响应内容: {error_text}")

                        resp_json = await resp.json()

                        # 检查业务响应码
                        if resp_json.get("code") == 3001008:
                            error_msg = f"业务错误, 错误码: {resp_json.get('code')}, 错误信息: {resp_json.get('message', '')}"
                            logger.error(error_msg)
                            if retry_count < retries:
                                retry_count += 1
                                wait_time = 2 ** retry_count  # 指数退避策略
                                logger.info(
                                    f"业务错误，将在 {wait_time} 秒后重试 (剩余重试次数: {retries - retry_count})")
                                await asyncio.sleep(wait_time)
                                continue
                            raise ValueError(error_msg)

                        return ResponseResult(**resp_json)

            except asyncio.TimeoutError as e:
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
