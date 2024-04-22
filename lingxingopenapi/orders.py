import asyncio
from datetime import datetime

from dateutil.relativedelta import relativedelta

from app.lingxing import bulk_update_collection
from app.lingxing_login import lingxing_openapi
from app.mongodb import db


@lingxing_openapi
async def get_orders(access_token, op_api, start_date, end_date, offset=0, length=1000):
    """
    :param access_token: 通过 @lingxing_openapi 获取 access_token
    :param op_api: 通过 @lingxing_openapi 获取 op_api
    :param start_date:
    :param end_date:
    :param offset:
    :param length:
    :return:
    """
    orders_url = "/erp/sc/data/mws/orders"
    collection = db['orders']
    req_body = {
        "start_date": start_date,
        "end_date": end_date,
        "sort_desc_by_date_type": 2,
        "offset": offset,
        "length": length
    }
    resp = await op_api.request(access_token, orders_url, "POST", req_body=req_body)
    total = resp.total
    if resp.code == 0:
        print(total)
        await bulk_update_collection(collection, resp.data, "amazon_order_id")
        total_pages = (total + req_body["length"] - 1) // req_body["length"]
        for page in range(1, total_pages):
            req_body["offset"] = page * req_body["length"]
            resp = await op_api.request(access_token, orders_url, "POST", req_body=req_body)
            await bulk_update_collection(collection, resp.data, "amazon_order_id")


async def fetch_orders():
    # asyncio.run(get_orders("2022-11-01", "2022-12-01"))
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2024, 4, 1)
    current_date = start_date

    while current_date <= end_date:
        # 为了确保包括月份的最后一天，设置结束日期为下个月的第一天减去一天
        next_month = current_date + relativedelta(months=1)
        last_day_of_month = next_month
        # 使用月的第一天和最后一天作为开始和结束日期
        print(current_date.strftime('%Y-%m-%d'), last_day_of_month.strftime('%Y-%m-%d'))
        await get_orders(current_date.strftime('%Y-%m-%d'), last_day_of_month.strftime('%Y-%m-%d'))
        await asyncio.sleep(60)
        # 将当前日期设置为下个月的第一天，以进行下一次循环
        current_date = next_month


if __name__ == "__main__":
    asyncio.run(get_orders("2024-04-01", "2024-04-18"))
