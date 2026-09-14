from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import distinct, extract, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db import get_db, init_db
from app.models import Vehicle, VehicleConsumptionProfile, VehicleEquipment, VehicleSpecProfile
from app.schemas import VehicleConsumptionOut, VehicleOut, VehiclePage, VehicleSpecOut
from app.scraper.parsers import normalize_text
from app.specs import best_consumption, best_spec

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    settings.image_dir.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="Porsche Inter Auto Vehicle API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])
app.mount("/media", StaticFiles(directory=str(settings.image_dir), check_dir=False), name="media")


def spec_match_conditions():
    registration_year = extract("year", Vehicle.first_registration)
    return (
        func.lower(VehicleSpecProfile.brand) == func.lower(Vehicle.brand),
        func.lower(VehicleSpecProfile.model) == func.lower(Vehicle.model),
        or_(VehicleSpecProfile.body_type.is_(None), func.lower(VehicleSpecProfile.body_type) == func.lower(Vehicle.body_type)),
        or_(Vehicle.first_registration.is_(None), VehicleSpecProfile.year_from.is_(None), registration_year >= VehicleSpecProfile.year_from),
        or_(Vehicle.first_registration.is_(None), VehicleSpecProfile.year_to.is_(None), registration_year <= VehicleSpecProfile.year_to),
    )


def serialize_vehicle(item: Vehicle, profiles: list[VehicleSpecProfile], consumption_profiles: list[VehicleConsumptionProfile]) -> VehicleOut:
    profile = best_spec(item, profiles)
    consumption = best_consumption(item, consumption_profiles)
    result = VehicleOut.model_validate(item)
    return result.model_copy(update={
        "specs": VehicleSpecOut.model_validate(profile) if profile else None,
        "consumption": VehicleConsumptionOut.model_validate(consumption) if consumption else None,
    })


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/vehicles", response_model=VehiclePage)
async def vehicles(
    db: Annotated[AsyncSession, Depends(get_db)],
    brand: list[str] = Query(default=[]),
    body_type: str | None = None,
    model: str | None = None,
    fuel: str | None = None,
    transmission_type: Literal["manual", "automatic", "semiautomatic"] | None = None,
    min_mileage_km: int | None = Query(None, ge=0),
    max_mileage_km: int | None = Query(None, ge=0),
    power_kw: int | None = Query(None, ge=0),
    min_power_kw: int | None = Query(None, ge=0),
    max_power_kw: int | None = Query(None, ge=0),
    min_price_eur: int | None = Query(None, ge=0),
    max_price_eur: int | None = Query(None, ge=0),
    min_boot_liters: int | None = Query(None, ge=0),
    min_rear_space_rating: int | None = Query(None, ge=1, le=5),
    has_tow_hitch: bool | None = None,
    warranty_available: bool | None = None,
    equipment: list[str] = Query(default=[]),
    available_only: bool = True,
    sort: Literal["price_asc", "price_desc", "mileage_asc", "power_desc", "newest"] = "price_asc",
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> VehiclePage:
    filters = []
    if available_only:
        filters.append(Vehicle.is_available.is_(True))
    if brand:
        filters.append(func.lower(Vehicle.brand).in_([value.lower() for value in brand]))
    if body_type:
        filters.append(func.lower(Vehicle.body_type) == body_type.lower())
    if model:
        filters.append(func.lower(Vehicle.model).contains(model.lower()))
    if fuel:
        filters.append(func.lower(Vehicle.fuel).contains(fuel.lower()))
    if transmission_type:
        filters.append(Vehicle.transmission_type == transmission_type)
    if power_kw is not None:
        filters.append(Vehicle.power_kw == power_kw)
    for column, lower, upper in (
        (Vehicle.mileage_km, min_mileage_km, max_mileage_km),
        (Vehicle.power_kw, min_power_kw, max_power_kw),
        (Vehicle.regular_price_eur, min_price_eur, max_price_eur),
    ):
        if lower is not None:
            filters.append(column >= lower)
        if upper is not None:
            filters.append(column <= upper)
    if has_tow_hitch is not None:
        filters.append(Vehicle.has_tow_hitch.is_(has_tow_hitch))
    if warranty_available is not None:
        filters.append(Vehicle.warranty_available.is_(warranty_available))
    for item in equipment:
        needle = normalize_text(item)
        filters.append(
            select(VehicleEquipment.id)
            .where(VehicleEquipment.vehicle_id == Vehicle.id, VehicleEquipment.normalized_name.contains(needle))
            .exists()
        )
    if min_boot_liters is not None:
        filters.append(
            select(VehicleSpecProfile.id)
            .where(*spec_match_conditions(), VehicleSpecProfile.boot_liters >= min_boot_liters)
            .exists()
        )
    if min_rear_space_rating is not None:
        filters.append(
            select(VehicleSpecProfile.id)
            .where(*spec_match_conditions(), VehicleSpecProfile.rear_space_rating >= min_rear_space_rating)
            .exists()
        )

    sort_column = {
        "price_asc": Vehicle.regular_price_eur.asc().nullslast(),
        "price_desc": Vehicle.regular_price_eur.desc().nullslast(),
        "mileage_asc": Vehicle.mileage_km.asc().nullslast(),
        "power_desc": Vehicle.power_kw.desc().nullslast(),
        "newest": Vehicle.first_registration.desc().nullslast(),
    }[sort]
    total = await db.scalar(select(func.count()).select_from(Vehicle).where(*filters))
    query = (
        select(Vehicle)
        .where(*filters)
        .options(selectinload(Vehicle.images), selectinload(Vehicle.equipment))
        .order_by(sort_column, Vehicle.id)
        .limit(limit)
        .offset(offset)
    )
    result = (await db.scalars(query)).all()
    profiles = list((await db.scalars(select(VehicleSpecProfile))).all())
    consumption_profiles = list((await db.scalars(select(VehicleConsumptionProfile))).all())
    return VehiclePage(items=[serialize_vehicle(v, profiles, consumption_profiles) for v in result], total=total or 0, limit=limit, offset=offset)


@app.get("/vehicles/{vehicle_id}", response_model=VehicleOut)
async def vehicle(vehicle_id: int, db: Annotated[AsyncSession, Depends(get_db)]) -> VehicleOut:
    item = await db.scalar(
        select(Vehicle).where(Vehicle.id == vehicle_id).options(selectinload(Vehicle.images), selectinload(Vehicle.equipment))
    )
    if not item:
        raise HTTPException(404, "Vehicle not found")
    profiles = list((await db.scalars(select(VehicleSpecProfile))).all())
    consumption_profiles = list((await db.scalars(select(VehicleConsumptionProfile))).all())
    return serialize_vehicle(item, profiles, consumption_profiles)


@app.get("/spec-profiles", response_model=list[VehicleSpecOut])
async def spec_profiles(db: Annotated[AsyncSession, Depends(get_db)]) -> list[VehicleSpecOut]:
    profiles = (await db.scalars(select(VehicleSpecProfile).order_by(VehicleSpecProfile.brand, VehicleSpecProfile.model))).all()
    return [VehicleSpecOut.model_validate(profile) for profile in profiles]


@app.get("/facets")
async def facets(db: Annotated[AsyncSession, Depends(get_db)]) -> dict:
    async def values(column):
        return list((await db.scalars(select(distinct(column)).where(Vehicle.is_available.is_(True), column.is_not(None)).order_by(column))).all())

    return {
        "brands": await values(Vehicle.brand),
        "models": await values(Vehicle.model),
        "body_types": await values(Vehicle.body_type),
        "fuels": await values(Vehicle.fuel),
        "transmissions": await values(Vehicle.transmission_type),
        "dealerships": await values(Vehicle.dealership),
    }


# Keep this mount last so API routes above take precedence.
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="frontend")
