import asyncio

import httpx
from lingxing import set_header
from mongodb import db
from pymongo import UpdateOne


async def warehouse_full_sync():
    request_url = "https://vayi.lingxing.com/api/ware_house/newList?req_time_sequence=%2Fapi%2Fware_house%2FnewList$$2"
    headers = await set_header()
    collection = db['warehouse']
    async with httpx.AsyncClient(headers=headers) as client:
        response = await client.get(request_url)
        data = response.json()
        operations = [
            UpdateOne({'_id': item['type']}, {'$set': item}, upsert=True)
            for item in data['data']
        ]
        if operations:
            result = await collection.bulk_write(operations)
            print(
                f"批量写入/更新完成，匹配{result.matched_count}，修改{result.modified_count}，插入{result.upserted_count}")


if __name__ == "__main__":
    asyncio.run(warehouse_full_sync())
