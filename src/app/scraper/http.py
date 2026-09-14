import asyncio
import random

import aiohttp

from app.config import settings


class HttpClient:
    def __init__(self, concurrency: int):
        self.semaphore = asyncio.Semaphore(concurrency)
        timeout = aiohttp.ClientTimeout(total=settings.request_timeout_seconds)
        connector = aiohttp.TCPConnector(limit=concurrency, ttl_dns_cache=300)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={"User-Agent": "Mozilla/5.0 (compatible; PIA-vehicle-indexer/1.0; personal-use)"},
        )

    async def close(self):
        await self.session.close()

    async def get(self, url: str, *, binary: bool = False) -> str | bytes:
        async with self.semaphore:
            await asyncio.sleep(random.uniform(settings.request_min_delay_seconds, settings.request_max_delay_seconds))
            last_error = None
            for attempt in range(settings.request_retries):
                try:
                    async with self.session.get(url) as response:
                        if response.status in {429, 500, 502, 503, 504}:
                            raise aiohttp.ClientResponseError(response.request_info, response.history, status=response.status)
                        response.raise_for_status()
                        return await response.read() if binary else await response.text()
                except (aiohttp.ClientError, asyncio.TimeoutError) as error:
                    last_error = error
                    if attempt + 1 < settings.request_retries:
                        await asyncio.sleep(2**attempt + random.random())
            raise RuntimeError(f"Request failed after {settings.request_retries} attempts: {url}") from last_error

