import httpx
import airbyte_api
from airbyte_api import api, models




async def sync(payload):
    url = "http://192.168.1.143:8000/api/v1/connections/sync"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Basic YWRtaW46dmF5aTEyMzQ1Ng=='
    }
    async with httpx.AsyncClient(headers=headers) as client:
        response = await client.post(url, json=payload)
        return response.json()


async def list_con():
    s = airbyte_api.AirbyteAPI(
        server_url="http://192.168.1.143:8006/v1",
        security=models.Security(
            basic_auth=models.SchemeBasicAuth(
                username="admin",
                password="vayi123456"

            ),
        ),
    )
    res = s.connections.list_connections(request=api.ListConnectionsRequest())

    if res.connections_response is not None:
        # handle response
        print(res.connections_response.data)


if __name__ == "__main__":
    import asyncio

    asyncio.run(list_con())
