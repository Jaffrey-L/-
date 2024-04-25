import asyncio
import logging
import time

import httpx

ihr_token_info = {
    'access_token': None,
    'expires_at': None
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def login():
    global ihr_token_info
    current_time = time.time()

    # 检查是否有有效的access_token和是否未过期
    if ihr_token_info['access_token'] and ihr_token_info['expires_at'] > current_time:
        return {
            'access_token': ihr_token_info['access_token'],
            'refresh_token': None,
            'expires_in': ihr_token_info['expires_at'] - current_time,
            'token_type': 'bearer',
            'scope': 'client'
        }

    url = "https://openapi.ihr360.com/openapi/oauth/token?grant_type=client_credentials&scope=client"
    headers = {
        'Authorization': 'Basic N2M0ZWZhMzQtZjgyMS00ODIyLWJmZjgtMGIwZmZlZDZmNWRjOjI2NWY4NjNiLTExYmEtNDc2Mi05ZWQ3LTIxYmY1YWViNWQwOQ==',
        'Content-Type': 'application/json'
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers)
        return response.json()


async def fetch_all_pages(base_url, data_list='dataList', additional_params=None, page_size=500):
    token_info = await login()
    header = {
        'Content-Type': 'application/json;charset=UTF-8;',
        'Authorization': 'Bearer ' + token_info['access_token']
    }
    # 初始化请求参数字典，设置固定的分页参数
    params = {
        'pageSize': page_size
    }

    # 如果提供了额外的参数，则合并到params字典中
    if additional_params:
        params.update(additional_params)

    # 初始化 httpx 客户端
    async with httpx.AsyncClient(headers=header, timeout=180) as client:
        logger.info(f"Fetching data from {base_url} with params: {params}")
        # 首次请求以获取总页数
        response = await client.get(base_url, params=params)
        response_data = response.json()

        # 检查初始请求是否成功
        if response.status_code != 200 or response_data.get('errorResult', True):
            logger.info(f"Failed to fetch initial data:{response_data.get('message')}")
            return []

        total_pages = response_data['data']['pageInfo']['totalPages']
        all_data = response_data['data'][data_list]

        # 循环获取剩余页面的数据
        for page in range(2, total_pages + 1):
            current_params = params.copy()
            current_params['pageNo'] = page
            response = await client.get(base_url, params=current_params)
            response_data = response.json()

            if response.status_code == 200 and not response_data.get('errorResult', False):
                all_data.extend(response_data['data'][data_list])
            else:
                logger.info(f"Failed to fetch data for page {page}: {response_data.get('message')}")

        return all_data


if __name__ == "__main__":
    print(asyncio.run(login()))
