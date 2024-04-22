import asyncio


from lingxing_login import lingxing_openapi


@lingxing_openapi
async def product_list(access_token, op_api):
    req_body = {
        "offset": 0,
        "length": 10
    }
    resp = await op_api.request(access_token, "/erp/sc/routing/data/local_inventory/productList", "POST",
                                req_body=req_body)
    print(resp.dict())


if __name__ == "__main__":
    asyncio.run(product_list())
