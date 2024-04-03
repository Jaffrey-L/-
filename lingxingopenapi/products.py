import asyncio
from lingxing_login import lingxing_openapi


@lingxing_openapi
async def product_list(access_token, op_api):
    products_url = "/erp/sc/routing/data/local_inventory/productList"
    product_info_url = "/erp/sc/routing/data/local_inventory/batchGetProductInfo"
    req_body = {
        "offset": 0,
        "length": 100
    }
    resp = await op_api.request(access_token, products_url, "POST",
                                req_body=req_body)
    if resp.code == 0:

        data = resp.data
        ids = [d["id"] for d in data]
        req_body = {
            "productIds": ids
        }
        resp_info = await op_api.request(access_token, product_info_url, "POST", req_body=req_body)
        if resp_info.code == 0:
            print(resp_info.data)


if __name__ == "__main__":
    asyncio.run(product_list())
