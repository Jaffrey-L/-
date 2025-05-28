from app.lingxing_login import before_call_login
import asyncio
import httpx
from pymongo.collection import Collection
from pymongo import UpdateOne
from app.mongodb import db



@before_call_login
async def set_header(login_info):
    headers = {
        'Content-Type': 'application/json',
        # 'X-Ak-Language': 'zh',
        # 'X-Ak-Request-Source': 'erp',
        # 'X-Ak-Platform': '1',
        # 'X-Ak-Env-Key': 'vayi',
        'origin': 'https://vayi.lingxing.com',
        'Ak-Origin': 'https://vayi.lingxing.com',
        'Auth-Token': login_info['token'],
        'X-Ak-Company-Id': login_info['companyId'],
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0',
        'X-Ak-Uid': '10486000',
        'X-Ak-Version': '3.5.7.3.0.001',



    }
    return headers


async def bulk_update_collection(collection: Collection, items: list, id_field: str = "id", details: str = None,
                                 additional_info: callable = None):
    """
       异步批量更新MongoDB集合中的文档。

       参数:
       - collection (Collection): 要更新的MongoDB集合，提供了进行数据操作的接口。
       - items (list): 一个包含要更新的文档数据的列表。每个元素都是一个字典，代表要更新或插入的文档。
       - id_field (str, 可选): 用于从每个项目中提取文档ID的字段名称，默认为 "id"。这个ID用于匹配MongoDB中的文档。
       - details (str, 可选): 如果提供，这将是在文档中添加额外信息的键名。这个参数与 `additional_info` 函数返回的数据一起使用，将额外信息嵌套在此键下。
       - additional_info (callable, 可选): 一个可调用的异步函数，它接收一个 `item_id` 参数并返回一个字典。这个字典包含了要添加到更新数据中的额外信息。如果 `details` 参数被指定，额外信息将被添加到该键下；否则，它将直接被合并到文档数据中。

       作用:
       - 该函数遍历 `items` 列表中的每个元素，对每个元素执行更新操作。
       - 如果提供了 `additional_info` 函数，该函数会被异步调用，并将其返回的数据根据 `details` 参数的值合并到更新数据中。
       - 使用 `UpdateOne` 操作构建一个操作列表，并通过 `bulk_write` 方法批量执行这些操作。这种批量操作比逐一更新文档更高效。

       执行流程:
       1. 遍历 `items` 列表中的每个字典（每个字典代表一个文档）。
       2. 对于每个字典，使用 `id_field` 参数指定的键名从字典中提取文档ID。
       3. 如果 `additional_info` 参数被提供，异步获取每个文档的额外信息并将其合并到更新数据中。
       4. 根据提供的文档ID和更新数据构建 `UpdateOne` 操作，添加到操作列表中。
       5. 使用 `bulk_write` 执行列表中的所有更新操作。
       6. 打印操作结果，包括匹配、修改和插入的文档数量。

       注意:
       - `bulk_write` 方法的执行结果可以用于监控批量更新操作的效果，比如确定有多少文档被更新或插入。
       - 这个函数适用于需要对大量文档执行复杂更新逻辑的场景，特别是当更新操作包括添加额外信息时。
       """
    operations = []
    for item in items:
        item_id = item.get(id_field)
        if additional_info:
            details_data = await additional_info(item_id)
            operations.append(UpdateOne({'_id': item_id}, {'$set': {**item, details: details_data}}, upsert=True))
        else:
            operations.append(UpdateOne({'_id': item_id}, {'$set': item}, upsert=True))
    if operations:
        result = await collection.bulk_write(operations)
        print(
            f"正在更新集合：{collection.name},批量写入/更新完成，匹配{result.matched_count}，修改{result.modified_count}，插入{result.upserted_count}")


async def fetch_data_list(request_url: str, payload: dict,
                          data_path: str = "data", list_key: str = "list", total_key: str = "total",
                          retries: int = 3):
    """
    异步从给定的URL获取数据集合，并返回相关信息。支持重试逻辑处理请求超时。

    :param request_url: 请求的URL地址，从该地址获取数据。
    :param payload: 作为POST请求体发送的JSON负载。
    :param data_path: 在响应的JSON中，包含目标数据列表和总数的键路径。默认为"data"。
    :param list_key: 在`data_path`指定的数据中，列表数据的键名。默认为"list"。
    :param total_key: 在`data_path`指定的数据中，表示总数据量的键名。默认为"total"。
    :param retries: 如果请求超时，重试的最大次数。默认为3次。

    :returns: 返回一个三元组(total_items, list_length, items_list)，其中：
              - total_items (int): 总数据量。
              - list_length (int): 返回列表中的元素数量。
              - items_list (list): 实际的数据列表。如果没有数据或请求失败，则为None。

    :raises httpx.ReadTimeout: 如果重试次数用尽后仍然超时，则抛出此异常。

    该函数通过POST请求向指定的URL发送负载，解析返回的JSON响应以提取数据列表和总数据量信息。
    如果请求超时，函数会等待3分钟后重试，直到达到最大重试次数。
    """
    try:
        headers = await set_header()
        async with httpx.AsyncClient(headers=headers) as client:
            response = await client.post(request_url, json=payload)
            response_data = response.json()

            if data_path is not None:
                data = response_data.get(data_path, {})
            else:
                data = response_data

            items_list = data.get(list_key, [])
            if items_list:
                total_items = data.get(total_key, 0)
                return total_items, len(items_list), items_list
            else:
                # 处理没有指定键或数据结构不同的情况。
                return 0, 0, None

    except httpx.ReadTimeout:
        if retries > 0:
            print("请求超时，暂停3分钟...")
            await asyncio.sleep(180)  # 暂停3分钟
            return await fetch_data_list(request_url, payload, data_path, list_key, total_key,
                                         retries - 1)
        else:
            raise


async def test_listing():
    """
    该函数演示了如何调用API并处理返回的JSON数据，特别是如何处理以下结构的响应数据：
    {
    "code": 1,
    "msg": "\u6210\u529f",
    "data": {
        "total": 42254,
        "list": [{}]
    }
    data_path 如果为设置，则默认从 data 节点取数据
    """

    request_url = 'https://gw.lingxingerp.com/listing-api/api/product/showOnline'
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
    total_items, total_count, items_list = await fetch_data_list(request_url, payload)
    print(total_items, total_count, items_list)


async def _test_additional_info1(product_id, retries=3):
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
            await _test_additional_info1(product_id, retries - 1)
    else:
        raise


async def test_products():
    """
        测试从'https://vayi.lingxing.com/api/product/lists'获取产品列表的异步函数。

        该函数演示了如何调用API并处理返回的JSON数据，特别是如何处理以下结构的响应数据：
        {
            "code": 1,  // 状态码，1表示操作成功
            "msg": "操作成功",  // 响应消息
            "require_id": "21D9B719-E434-183F-33E3-61BBD223E0F9",  // 请求ID
            "total": 17389,  // 数据总数
            "list": [{}]  // 产品列表，实际使用中列表中将包含具体的产品信息
        }
        为正确处理此结构，调用`fetch_data_list`时，`data_path`参数被设置为None，
        意味着数据直接位于响应的顶级，而不是嵌套在另一个字段内。

        使用指定的payload发起POST请求，然后从响应中解析出产品总数、当前响应的产品数量和产品列表本身。
        最后，打印出这些信息。

        :param request_url: 请求的URL地址。
        :param payload: 发送到API的POST请求的负载，包含了查询参数和其他控制信息。
        """
    request_url = 'https://vayi.lingxing.com/api/product/lists'
    payload = {"search_field_time": "create_time", "sort_field": "create_time", "sort_type": "desc",
               "search_field": "sku", "attribute": [], "status": [], "open_status": "", "gtag_ids": "",
               "senior_search_list": "[]", "is_matched_alibaba": "", "is_matched_listing": "", "relation_aux": "",
               "cg_package": "", "cg_product_gross_weight": {"left": "", "right": "", "symbol": "gt"},
               "cg_transport_costs": {"left": "", "right": "", "symbol": "gt", "country_code": "US"},
               "cg_price": {"left": "", "right": "", "symbol": "gt"}, "offset": 0, "is_combo": "", "length": 10,
               "is_aux": 0, "product_type": [1, 2], "selected_product_ids": "",
               "req_time_sequence": "/api/product/lists$$1"}
    total_items, total_count, items_list = await fetch_data_list(request_url, payload, None)
    print(total_items, total_count, items_list)
    await bulk_update_collection(db["items"], items_list, "id", "info", _test_additional_info1)
    total_pages = (total_items + payload["length"] - 1) // payload["length"]
    for page in range(1, total_pages):
        payload["offset"] = page * payload["length"]
        payload["req_time_sequence"] = f"/api/product/lists$${page}"  # 更新序列号
        _, _, items_list2 = await fetch_data_list(request_url, payload, None)
        await bulk_update_collection(db["items"], items_list2, "id", "info", _test_additional_info1)


if __name__ == '__main__':
    asyncio.run(test_products())

