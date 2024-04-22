import asyncio
from mongodb import db
from lingxing import bulk_update_collection, fetch_data_list


async def mp_order_full_sync():
    payload = {"sort_field": "global_purchase_time", "sort_type": "desc", "status": "", "site_code": [], "store_id": [],
               "platform_code": [], "search_field": "platform_order_name", "search_value": [""],
               "search_field_time": "global_purchase_time", "offset": 0, "length": 200, "is_pending": "0",
               "receiver_country_code": [], "order_from": "", "order_type": "", "buyer_note_status": "",
               "remark_has": "", "platform_status": [], "address_type": "", "is_marking": "", "wid": "",
               "logistics_type_id": "", "logistics_provider_id": ""}
    await _sync(payload)


async def _sync(payload):
    request_url = "https://gw.lingxingerp.com/cepf-oms-sw/list/order"
    collection = db['mp_orders']  # 确保db已正确初始化
    total, _, items_list = await fetch_data_list(request_url, payload)
    await bulk_update_collection(collection, items_list,"global_order_no")
    total_pages = (total + payload["length"] - 1) // payload["length"]
    for page in range(1, total_pages):
        payload["offset"] = page * payload["length"]
        payload["req_time_sequence"] = f"/cepf-oms-sw/list/order$${page}"  # 更新序列号
        total, _, items_list = await fetch_data_list(request_url, payload)
        await bulk_update_collection(collection, items_list,"global_order_no")


if __name__ == "__main__":
    asyncio.run(mp_order_full_sync())
