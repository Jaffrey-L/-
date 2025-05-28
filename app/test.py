import asyncio
from http.client import HTTPException
from typing import Dict, Any, List
import csv
import httpx

from lingxing_login import lingxing_openapi
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@lingxing_openapi
async def product_list(access_token, op_api):
    req_body = {
        "offset": 0,
        "length": 10
    }
    resp = await op_api.request(access_token, "/erp/sc/routing/data/local_inventory/productList", "POST",
                                req_body=req_body)
    print(resp.dict())


def extract_seller_skus(data: Dict[str, Any]) -> List[Any]:
    """
    Extract all seller_sku values from the API response data.

    Args:
        data: API response data dictionary

    Returns:
        List of seller_sku values
    """
    seller_skus = []

    # Check if the response is valid and contains the expected data structure
    if (data.get('code') == 1 and
            'data' in data and
            'list' in data['data']):

        # Iterate through each item in the list
        for item in data['data']['list']:
            # Extract seller_sku from price_list if it exists
            if 'price_list' in item and isinstance(item['price_list'], list):
                for price_item in item['price_list']:
                    if 'seller_sku' in price_item and price_item['seller_sku']:
                        dic = {"seller_sku": price_item['seller_sku'], "sid": price_item['sid']}
                        seller_skus.append(dic)
    return seller_skus


async def get_order_profit_data(
        start_date: str = "2025-03-10",
        end_date: str = "2025-03-10",
        search_field: str = "seller_sku",
        currency_type: str = "CNY",
        summary_field: str = "msku",
        length: int = 500,
        offset: int = 0
) -> dict:
    """
    Fetch order profit data from the Lingxing ERP system.

    Args:
        start_date: Start date in format 'YYYY-MM-DD'
        end_date: End date in format 'YYYY-MM-DD'
        search_field: Field to search by (default: 'seller_sku')
        currency_type: Currency type (default: 'CNY')
        summary_field: Field to summarize by (default: 'msku')
        length: Number of records to return (default: 500)

    Returns:
        JSON response data as a dictionary
    """
    url = "http://localhost:8088/lx_web/gw.lingxingerp.com/bd/orderProfit/orderProfitList/msku"

    payload = {
        "start_date": start_date,
        "end_date": end_date,
        "search_field": search_field,
        "currency_type": currency_type,
        "summary_field": summary_field,
        "length": length,
        "offset": offset
    }

    payload2 = {"mids": [], "sids": [], "start_date": "2025-03-10", "end_date": "2025-03-10", "currency_type": "CNY",
                "summary_field": "msku", "principal_uids": [], "gtag_ids": [], "cids": [], "bids": [],
                "search_field": "seller_sku", "search_value": [],"sort_field":"gross_profit","sort_type":"desc", "offset": offset, "length": length,
                "stock_fee_config": "0", "purchase_status": "0"}

    logger.info(f"Requesting {payload}")
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(url, json=payload2)
            response.raise_for_status()  # Raise exception for 4XX/5XX responses

            logger.info(f"HTTP Request: POST {url} \"{response.status_code} {response.reason_phrase}\"")
            logger.info(response.json().get("data").get("total"))
            return response.json()

    except httpx.RequestError as e:
        logger.error(f"Request error: {e}")
        raise
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise


def write_skus_to_csv(skus: List[Dict[str, Any]], filename: str = "seller_skus.csv"):
    """Write seller SKUs to a CSV file"""
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["seller_sku"])  # Header row
        for sku in skus:
            writer.writerow([sku])

    print(f"Successfully wrote {len(skus)} SKUs to {filename}")


async def main():
    response1 = await get_order_profit_data()
    skus = extract_seller_skus(response1)
    response2=await get_order_profit_data(offset=500)
    skus.extend(extract_seller_skus(response2))
    response3=await get_order_profit_data(offset=1000)
    skus.extend(extract_seller_skus(response3))
    response4=await get_order_profit_data(offset=1500)
    skus.extend(extract_seller_skus(response4))
    response5=await get_order_profit_data(offset=2000)
    skus.extend(extract_seller_skus(response5))
    response6=await get_order_profit_data(offset=2500)
    skus.extend(extract_seller_skus(response6))
    response7=await get_order_profit_data(offset=3000)
    skus.extend(extract_seller_skus(response7))
    response8=await get_order_profit_data(offset=3500)
    skus.extend(extract_seller_skus(response8))
    response9=await get_order_profit_data(offset=4000)
    skus.extend(extract_seller_skus(response9))
    print(len(skus))
    write_skus_to_csv(skus, "seller_skus6.csv")

    # If you want to deduplicate the SKUs before writing


if __name__ == "__main__":
    asyncio.run(main())
