import asyncio
from datetime import datetime, timedelta

from app.lingxing import bulk_update_collection
from app.lingxing_login import lingxing_openapi
from app.mongodb import db


@lingxing_openapi
async def get_mp_orders(access_token, op_api, start_time: str, end_time: str, date_type: str = "global_purchase_time",
                        offset=0, length=500):
    """
    多平台中的订单同步
    :param access_token: 由 @lingxing_openapi 提供
    :param op_api:  由 @lingxing_openapi 提供
    :param start_time:  开始时间
    :param end_time:    结束时间
    :param date_type: 订购时间 global_purchase_time（默认）,更新时间 update_time,发货时间 global_delivery_time,付款时间 global_payment_time
    :param offset:分页偏移量
    :param length:分页长度，上限500
    """
    date_format = "%Y-%m-%d"
    start_time = datetime.strptime(start_time, date_format)
    end_time = datetime.strptime(end_time, date_format)
    orders_url = "/pb/mp/order/v2/list"
    collection = db['api_mp_orders']
    req_body = {
        "start_time": int(start_time.timestamp()),
        "end_time": int(end_time.timestamp()),
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
    asyncio.run(get_mp_orders("2024-04-01", "2024-4-29", "update_time"))
    # asyncio.run(fetch_mp_orders())
