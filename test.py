
import httpx
import json
import pymongo
from lingxing_header import set_header
from lingxing_login import before_call_login
from mongodb import close_mongo_connection, db
from pymongo import UpdateOne

@before_call_login
def test(login_info):
    print(login_info)

@before_call_login
def test2(login_info):
    print(login_info)

@before_call_login
def get_goods_by_wid(login_info, widList,offset):
    request_url = "https://vayi.lingxing.com/api/storage/lists"
    req_data=f"""
                {{
                    "wid_list": "{widList}",
                    "mid_list": "",
                    "sid_list": "",
                    "cid_list": "",
                    "bid_list": "",
                    "principal_list": "",
                    "product_type_list": "",
                    "product_attribute": "",
                    "product_status": "",
                    "search_field": "sku",
                    "search_value": "",
                    "is_sku_merge_show": 0,
                    "is_hide_zero_stock": 1,
                    "offset": {offset},
                    "length": 800,
                    "sort_field": "",
                    "sort_type": "",
                    "gtag_ids": "",
                    "senior_search_list": "[]",
                    "country_code_list": "",
                    "req_time_sequence": "/api/storage/lists$$1"
                }}
                """
    print(req_data)
    headers = set_header(login_info)
    with httpx.Client(headers=headers) as client:
        response = client.post(request_url, json=json.loads(req_data))
        print(response.json())

@before_call_login
def get_products(login_info):
    request_url = "https://vayi.lingxing.com/api/product/lists"
    headers = set_header(login_info)
    json={"search_field_time":"create_time","sort_field":"create_time","sort_type":"desc","search_field":"sku","attribute":[],"status":[],"open_status":"","gtag_ids":"","senior_search_list":"[]","is_matched_alibaba":"","is_matched_listing":"","relation_aux":"","cg_package":"","cg_product_gross_weight":{"left":"","right":"","symbol":"gt"},"cg_transport_costs":{"left":"","right":"","symbol":"gt","country_code":"US"},"cg_price":{"left":"","right":"","symbol":"gt"},"offset":0,"is_combo":"","length":800,"is_aux":0,"product_type":[1,2],"selected_product_ids":"","req_time_sequence":"/api/product/lists$$1"}
    collection = db['products']
    with httpx.Client(headers=headers) as client:
        response = client.post(request_url, json=json)
        total = response.json().get('total', 0)
        operations = [
        UpdateOne({'_id': item['id']}, {'$set': item}, upsert=True)
        for item in response.json()['list']
        ]
        try:
            result = collection.bulk_write(operations)
            print(f"批量写入/更新完成，匹配{result.matched_count}，修改{result.modified_count}，插入{result.upserted_count}")
        except pymongo.errors.BulkWriteError as bwe:
            print(f"批量写入/更新错误: {bwe.details}")
        
        total_pages = (total + json["length"] - 1) // json["length"]

        # 已经获取了第一页的数据，现在获取剩余的数据
        for page in range(1, total_pages):
        # 更新offset
            json["offset"] = page * json["length"]
            response = client.post(request_url, json=json)
            operations = [
            UpdateOne({'_id': item['id']}, {'$set': item}, upsert=True)
            for item in response.json()['list']
            ]
            try:
                result = collection.bulk_write(operations)
                print(f"批量写入/更新完成，匹配{result.matched_count}，修改{result.modified_count}，插入{result.upserted_count}")
            except pymongo.errors.BulkWriteError as bwe:
                print(f"批量写入/更新错误: {bwe.details}")
    close_mongo_connection()     

if __name__ == "__main__":
    get_products()
