#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""OpenAPI HTTP helper with shared session pooling."""
import asyncio
import logging
from typing import Optional
from urllib.parse import urlencode

import aiohttp
import orjson

from lingxingopenapi.resp_schema import ResponseResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HttpBase(object):
    _shared_session: Optional[aiohttp.ClientSession] = None
    _session_lock = asyncio.Lock()

    def __init__(self, default_timeout=180):
        self.default_timeout = default_timeout

    @classmethod
    async def _get_session(cls) -> aiohttp.ClientSession:
        async with cls._session_lock:
            if cls._shared_session is None or cls._shared_session.closed:
                connector = aiohttp.TCPConnector(limit=100, ttl_dns_cache=300)
                cls._shared_session = aiohttp.ClientSession(connector=connector)
            return cls._shared_session

    async def request(
        self,
        method: str,
        req_url: str,
        params: Optional[dict] = None,
        json: Optional[dict] = None,
        headers: Optional[dict] = None,
        **kwargs,
    ) -> ResponseResult:
        resp = await self.request_without_retry(
            method=method,
            req_url=req_url,
            params=params,
            json=json,
            headers=headers,
            **kwargs,
        )
        return ResponseResult(**resp)

    async def request_without_retry(
        self,
        method: str,
        req_url: str,
        params: Optional[dict] = None,
        json: Optional[dict] = None,
        headers: Optional[dict] = None,
        **kwargs,
    ) -> dict:
        timeout = kwargs.pop("timeout", self.default_timeout)
        data = orjson.dumps(json, option=orjson.OPT_SORT_KEYS) if json else None
        session = await self._get_session()

        async with session.request(
            method=method,
            url=req_url,
            params=params,
            data=data,
            timeout=timeout,
            headers=headers,
            **kwargs,
        ) as resp:
            log_params = urlencode(params) if params else "no-params"
            logger.info(f"{method}--{req_url}?{log_params}")
            if data is not None:
                logger.info(data.decode("utf-8"))
            else:
                logger.info("No data to display.")

            if resp.status != 200:
                error_text = await resp.text()
                logger.error(f"HTTP error, status: {resp.status}, body: {error_text}")
                raise ValueError(f"response error, status: {resp.status}, body: {error_text}")

            return await resp.json()

