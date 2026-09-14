import asyncio
import logging
import re
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db import SessionLocal, init_db
from app.models import Vehicle, VehicleEquipment, VehicleImage
from app.scraper.http import HttpClient
from app.scraper.parsers import LISTING_URL, ListingVehicle, VehicleData, parse_detail, parse_listing

logger = logging.getLogger(__name__)


def page_url(page: int) -> str:
    if page == 1:
        return LISTING_URL
    return f"https://www.porscheinterauto.net/vozila/p{page}.html?filter=status%3A1&uredi=asc&uredi_po=cena_eur"


async def download_images(client: HttpClient, vehicle: VehicleData) -> list[str | None]:
    if not settings.download_images:
        return [None] * len(vehicle.images)
    vehicle_dir = settings.image_dir / (vehicle.source_vehicle_id or re.sub(r"\W+", "-", vehicle.source_url.rsplit("/", 1)[-1]))
    vehicle_dir.mkdir(parents=True, exist_ok=True)

    async def one(position: int, url: str) -> str | None:
        suffix = Path(url.split("?", 1)[0]).suffix or ".jpg"
        path = vehicle_dir / f"{position:03d}{suffix}"
        try:
            path.write_bytes(await client.get(url, binary=True))
            return str(path.relative_to(settings.image_dir))
        except Exception:
            logger.exception("Image download failed: %s", url)
            return None

    return await asyncio.gather(*(one(i, url) for i, url in enumerate(vehicle.images)))


async def save_vehicle(data: VehicleData, local_paths: list[str | None], overwrite: bool) -> None:
    async with SessionLocal() as session:
        existing = await session.scalar(
            select(Vehicle).where(Vehicle.source_url == data.source_url).options(selectinload(Vehicle.images), selectinload(Vehicle.equipment))
        )
        scalar_fields = {key: value for key, value in asdict(data).items() if key not in {"images", "equipment"}}
        if existing:
            if not overwrite:
                existing.is_available = True
                existing.last_seen_at = datetime.now(timezone.utc)
                await session.commit()
                return
            for key, value in scalar_fields.items():
                setattr(existing, key, value)
            existing.scraped_at = datetime.now(timezone.utc)
            existing.last_seen_at = datetime.now(timezone.utc)
            existing.images.clear()
            existing.equipment.clear()
            # Remove old child rows before inserting the replacement rows so
            # their per-vehicle unique positions/names cannot collide.
            await session.flush()
            vehicle = existing
        else:
            vehicle = Vehicle(**scalar_fields)
            session.add(vehicle)
        vehicle.images.extend(
            VehicleImage(source_url=url, local_path=local_paths[position], position=position)
            for position, url in enumerate(data.images)
        )
        unique_equipment = {(category, normalized): name for category, name, normalized in data.equipment}
        vehicle.equipment.extend(
            VehicleEquipment(category=category, name=name, normalized_name=normalized)
            for (category, normalized), name in unique_equipment.items()
        )
        await session.commit()


async def run(overwrite: bool = False, limit: int | None = None, download: bool | None = None) -> dict[str, int]:
    await init_db()
    if download is not None:
        settings.download_images = download
    started_at = datetime.now(timezone.utc)
    listing_client = HttpClient(settings.scraper_page_concurrency)
    detail_client = HttpClient(settings.scraper_concurrency)
    counters = {"found": 0, "new": 0, "updated": 0, "skipped": 0, "failed": 0}
    try:
        first_html = await listing_client.get(LISTING_URL)
        first_items, pages = parse_listing(first_html)
        logger.info("Found %d listing pages", pages)
        other_html = await asyncio.gather(*(listing_client.get(page_url(page)) for page in range(2, pages + 1)))
        items = first_items
        for html in other_html:
            page_items, _ = parse_listing(html)
            items.extend(page_items)
        items_by_url = {item.source_url: item for item in items}
        items = list(items_by_url.values())
        counters["found"] = len(items)
        if limit is not None:
            items = items[:limit]

        async with SessionLocal() as session:
            existing_urls = set((await session.scalars(select(Vehicle.source_url).where(Vehicle.source_url.in_([item.source_url for item in items])))).all())
            if existing_urls:
                await session.execute(
                    update(Vehicle).where(Vehicle.source_url.in_(existing_urls)).values(is_available=True, last_seen_at=started_at)
                )
                await session.commit()
        work = items if overwrite else [item for item in items if item.source_url not in existing_urls]
        counters["skipped"] = len(items) - len(work)
        vehicle_gate = asyncio.Semaphore(settings.scraper_concurrency)

        async def scrape_one(item: ListingVehicle):
            async with vehicle_gate:
                try:
                    html = await detail_client.get(item.source_url)
                    data = parse_detail(html, item)
                    paths = await download_images(detail_client, data)
                    await save_vehicle(data, paths, overwrite)
                    counters["updated" if item.source_url in existing_urls else "new"] += 1
                except Exception:
                    counters["failed"] += 1
                    logger.exception("Failed vehicle: %s", item.source_url)

        await asyncio.gather(*(scrape_one(item) for item in work))
        # Only deactivate missing vehicles after a complete, non-limited listing run.
        if limit is None and counters["failed"] == 0:
            async with SessionLocal() as session:
                await session.execute(update(Vehicle).where(Vehicle.last_seen_at < started_at).values(is_available=False))
                await session.commit()
        return counters
    finally:
        await listing_client.close()
        await detail_client.close()
