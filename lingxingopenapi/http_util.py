#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""封装 Openapi的 http请求"""
import asyncio
from urllib.parse import urlencode
import aiohttp
import orjson
from typing import Optional
from lingxingopenapi.resp_schema import ResponseResult
from pprint import pprint

class HttpBase(object):

    def __init__(self, default_timeout=30):
        self.default_timeout = default_timeout

    async def request(self, method: str, req_url: str,
                      params: Optional[dict] = None,
                      json: Optional[dict] = None,
                      headers: Optional[dict] = None,
                      retries: int = 3,
                      **kwargs) -> ResponseResult:
        timeout = kwargs.pop('timeout', self.default_timeout)
        # 需要保持与加密算法一致的请求数据传递
        data = orjson.dumps(json, option=orjson.OPT_SORT_KEYS) if json else None
        try:
            async with aiohttp.ClientSession() as aio_session:
                async with aio_session.request(method=method, url=req_url, params=params, data=data,
                                               timeout=timeout, headers=headers, **kwargs) as resp:
                    print(method, f"{req_url}?{urlencode(params)}")
                    print(data.decode('utf-8'))
                    if resp.status != 200:
                        raise ValueError(f"Response error, status code: {resp.status}, body: {await resp.text()}")
                    resp_json = await resp.json()
                    return ResponseResult(**resp_json)
        except asyncio.TimeoutError:
            if retries > 0:
                print(f"Timeout, retrying... ({retries} retries left)")
                await asyncio.sleep(180)  # 简单的等待策略，等待时间可以根据重试次数调整(180秒）
                return await self.request(method, req_url, params, json, headers, retries=retries - 1, **kwargs)
            else:
                raise ValueError("Maximum retries reached, request failed")
