import asyncio

import httpx
from lingxing import bulk_update_collection, fetch_data_list, set_header
from mongodb import db
from pymongo import UpdateOne
from pymongo.collection import Collection


async def products_full_sync():
    """
    产品全量同步
    """
    payload = {"search_field_time": "create_time", "sort_field": "create_time", "sort_type": "desc",
               "search_field": "sku", "attribute": [], "status": [], "open_status": "", "gtag_ids": "",
               "senior_search_list": "[]", "is_matched_alibaba": "", "is_matched_listing": "", "relation_aux": "",
               "cg_package": "", "cg_product_gross_weight": {"left": "", "right": "", "symbol": "gt"},
               "cg_transport_costs": {"left": "", "right": "", "symbol": "gt", "country_code": "US"},
               "cg_price": {"left": "", "right": "", "symbol": "gt"}, "offset": 0, "is_combo": "", "length": 800,
               "is_aux": 0, "product_type": [1, 2], "selected_product_ids": "",
               "req_time_sequence": "/api/product/lists$$1"}
    await _sync(payload)


async def _additional_info(product_id, retries=3):
    request_url = f"https://vayi.lingxing.com/api/product/info?id={product_id}&req_time_sequence=%2Fapi%2Fproduct%2Finfo$$1"
    print(request_url)
    headers = await set_header()
    try:
        async with httpx.AsyncClient(headers=headers) as client:
            response = await client.get(request_url)
            data = response.json()
            if data['code'] == 1:
                return data['info']
    except httpx.ReadTimeout:
        if retries > 0:
            print("被限流了，暂停 3 分钟...")
            await asyncio.sleep(180)  # 暂停3分钟
            await _additional_info(product_id, retries - 1)
    else:
        raise


async def products_inc_sync(start_time, end_time):
    """
    根据产品的更新日期时间段进行增量同步
    :param start_time: 更新开始日期
    :param end_time: 更新结束日期
    :return:
    """
    payload = {"search_field_time": "update_time", "product_creator_uid": [], "product_developer_uid": [],
               "permission_uid": [], "cg_opt_uid": [], "supplier_id": [], "sort_field": "create_time",
               "sort_type": "desc", "search_field": "sku", "attribute": [], "status": [], "open_status": "",
               "gtag_ids": "", "start_date": start_time, "end_date": end_time, "senior_search_list": "[]",
               "is_matched_listing": "", "is_matched_alibaba": "", "relation_aux": "", "cg_package": "",
               "cg_product_gross_weight": {"left": "", "right": "", "symbol": "gt"},
               "cg_price": {"left": "", "right": "", "symbol": "gt"},
               "cg_transport_costs": {"left": "", "right": "", "symbol": "gt", "country_code": "US"}, "offset": 0,
               "is_combo": "", "length": 800, "is_aux": 0, "product_type": [1, 2], "selected_product_ids": "",
               "req_time_sequence": "/api/product/lists$$1"}
    await _sync(payload)


async def _sync(payload):
    collection = db['products']
    request_url = "https://vayi.lingxing.com/api/product/lists"
    total, _, items_list = await fetch_data_list(request_url, payload)
    if total > 0:
        await bulk_update_collection(collection, items_list, "id", "info", _additional_info)
        total_pages = (total + payload["length"] - 1) // payload["length"]
        for page in range(1, total_pages):
            payload["offset"] = page * payload["length"]
            payload["req_time_sequence"] = f"/api/product/lists$${page}"  # 更新序列号
            _, _, items_list = await fetch_data_list(request_url, payload)
            await bulk_update_collection(collection, items_list, "id", "info", _additional_info)


async def _product_info(product_id, order, retries=3):
    """
    根据产品 id 进行产品详情信息查询并且同步到对应的产品表中
    """
    request_url = f"https://vayi.lingxing.com/api/product/info?id={product_id}&req_time_sequence=%2Fapi%2Fproduct%2Finfo$${order}"
    print(request_url)
    headers = await set_header()
    # 使用httpx异步发送GET请求
    try:
        async with httpx.AsyncClient(headers=headers) as client:
            response = await client.get(request_url)
            data = response.json()
            print(data)
            # 将获取到的数据附加回products的info字段
            await db.products.update_one({'_id': product_id}, {'$set': {'info': data["info"]}}, upsert=True)
    except httpx.ReadTimeout:
        if retries > 0:
            print("被限流了，暂停 3 分钟...")
            await asyncio.sleep(180)  # 暂停3分钟
            await _product_info(product_id, order, retries - 1)
        else:
            raise


async def product_info_all_sync():
    """
    同步所有没有同步过的产品详细信息
    """
    # 从products集合获取所有文档的_id
    order = 1
    async for product in db.products.find({"info": {"$exists": False}}, {'_id': 1}):
        product_id = product['_id']
        await _product_info(product_id, order)
        order = order + 1
        if order > 10:
            order = 1


if __name__ == "__main__":
    # asyncio.run(products_full_sync())
    asyncio.run(products_inc_sync('2024-03-28', '2024-04-02'))
    # asyncio.run(product_info_all_sync())
