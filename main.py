import logging
from fastapi import FastAPI
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.get("/async")
async def fetch_async():
    logger.info("Async fetch started")
    async with httpx.AsyncClient() as client:
        response = await client.get("https://httpbin.org/delay/2")
        logger.info("Async fetch finished")
    return {"Async": "Success"}

@app.get("/sync")
def fetch_sync():
    logger.info("Sync fetch started")
    response = httpx.get("https://httpbin.org/delay/2")
    logger.info("Sync fetch finished")
    return {"Sync": "Success"}