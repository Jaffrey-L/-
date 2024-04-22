import asyncio
from mongodb import db
from lingxing import bulk_update_collection, fetch_data_list


async def listing_inc_sync(open_date_start, open_date_end):
    """
    根据创建日期进行增量同步，日期格式必须为："2024-03-29"
    """
    payload = {
        "open_date_start": open_date_start,
        "open_date_end": open_date_end,
        "offset": 0,
        "length": 200,
        "search_field": "msku",
        "sort_field": "open_date_time",
        "sort_type": "desc",
        "exact_search": 1,
        "sids": "",
        "status": "",
        "is_pair": "",
        "fulfillment_channel_type": "",
        "global_tag_ids": "",
        "req_time_sequence": "/listing-api/api/product/showOnline$$1"
    }
    await _sync(payload)


async def listing_full_sync():
    """
    完全同步
    """
    payload = {
        "offset": 0,
        "length": 200,
        "search_field": "msku",
        "sort_field": "open_date_time",
        "sort_type": "desc",
        "exact_search": 1,
        "sids": "",
        "status": "",
        "is_pair": "",
        "fulfillment_channel_type": "",
        "global_tag_ids": "",
        "req_time_sequence": "/listing-api/api/product/showOnline$$1"
    }
    await _sync(payload)


async def _sync(payload):
    request_url = "https://gw.lingxingerp.com/listing-api/api/product/showOnline"
    collection = db['listing']  # 确保db已正确初始化
    total, _, items_list = await fetch_data_list(request_url, payload)
    await bulk_update_collection(collection, items_list)
    total_pages = (total + payload["length"] - 1) // payload["length"]
    for page in range(1, total_pages):
        payload["offset"] = page * payload["length"]
        payload["req_time_sequence"] = f"/listing-api/api/product/showOnline$${page}"  # 更新序列号
        total, _, items_list = await fetch_data_list(request_url, payload)
        await bulk_update_collection(collection, items_list)


if __name__ == "__main__":
    # asyncio.run(listing_full_sync())
    asyncio.run(listing_inc_sync("2024-03-20", "2024-03-30"))
