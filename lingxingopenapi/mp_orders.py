import asyncio
import calendar
from datetime import datetime, timedelta

from lingxing import bulk_update_collection
from lingxing_login import lingxing_openapi
from mongodb import db


@lingxing_openapi
async def get_mp_orders(access_token, op_api, start_time: int, end_time: int, date_type: str = "global_purchase_time",
                        offset=0, length=500):
    orders_url = "/pb/mp/order/v2/list"
    collection = db['api_mp_orders']
    req_body = {
        "start_time": start_time,
        "end_time": end_time,
        "date_type": date_type,
        "offset": offset,
        "length": length
    }
    resp = await op_api.request(access_token, orders_url, "POST", req_body=req_body)
    # print(resp.data)
    total = int(resp.data["total"])
    print(total)
    if resp.code == 0:
        await bulk_update_collection(collection, resp.data["list"], "global_order_no")
        total_pages = (total + req_body["length"] - 1) // req_body["length"]
        for page in range(1, total_pages):
            req_body["offset"] = page * req_body["length"]
            resp = await op_api.request(access_token, orders_url, "POST", req_body=req_body)
            await bulk_update_collection(collection, resp.data["list"], "global_order_no")


async def fetch_mp_orders():
    # 定义起始和结束日期
    current_start_date = datetime(2024, 4, 1)
    end_date = datetime(2024, 4, 4)

    while current_start_date < end_date:
        # 计算当前段的结束日期，但不包括这一天（开区间）
        current_end_date = current_start_date + timedelta(days=29)

        # 确保结束日期不超过给定的结束日期
        if current_end_date > end_date:
            current_end_date = end_date

        # 将日期转换为时间戳（秒）
        start_timestamp = int(current_start_date.timestamp())
        end_timestamp = int(current_end_date.timestamp())  # 开区间，所以不用减1秒
        print(
            f"{current_start_date.strftime('%Y-%m-%d')}({start_timestamp}), {current_end_date.strftime('%Y-%m-%d')}({end_timestamp})")
        await get_mp_orders(start_timestamp, end_timestamp)
        await asyncio.sleep(5)
        # 更新下一段的起始日期
        current_start_date = current_end_date


if __name__ == "__main__":
    asyncio.run(get_mp_orders("2022-05-01", "2022-06-01"))
    # asyncio.run(fetch_mp_orders())
