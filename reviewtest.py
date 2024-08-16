import json
import re
import httpx


async def review():
    # 从 storage state 文件中读取相关信息
    with open("amazon.com.json", "r") as file:
        storage_state = json.load(file)

    # 提取 cookies
    cookies = [
        {"name": cookie["name"], "value": cookie["value"]}
        for cookie in storage_state["cookies"]
    ]

    with open("headers.json", "r") as file:
        headers = json.load(file)

    # 组成 headers

    url = "https://www.amazon.com/dp/B0BPX6DNRG"

    # 使用正则表达式提取域名和 ASIN
    match = re.match(r"https://(www.amazon.[^/]+)/dp/([^/]+)", url)
    print(match.group(1))
    if match:
        domain = match.group(1)
        asin = match.group(2)
        # 拼接新的 URL
        new_url = f"https://{domain}/hz/reviews-render/ajax/reviews/get/ref=cm_cr_arp_d_paging_btm_next_1"

        # 使用 httpx 发送 x-www-form-urlencoded 请求

        async with httpx.AsyncClient() as client:
            response = await client.post(
                new_url,
                headers=headers[-1],
                data={
                    "sortBy": "recent",
                    "reviewerType": "all_reviews",
                    "formatType": "",
                    "mediaType": "",
                    "filterByStar": "five_star",
                    "filterByAge": "",
                    "pageNumber": 2,
                    "filterByLanguage": "",
                    "filterByKeyword": "",
                    "shouldAppend": "undefined",
                    "deviceType": "desktop",
                    "canShowIntHeader": "undefined",
                    "reftag": "cm_cr_arp_d_paging_btm_next_1",
                    "pageSize": 10,
                    "asin": "B0BPX6DNRG",
                    "scope": "reviewsAjax1"
                }

            )
            print(response.text)

if __name__ == "__main__":
    import asyncio
    asyncio.run(review())


