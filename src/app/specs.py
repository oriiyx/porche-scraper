import json
from datetime import date
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection

from app.models import Vehicle, VehicleConsumptionProfile, VehicleSpecProfile

SEED_PATH = Path(__file__).parent / "data" / "vehicle_specs.json"
CONSUMPTION_SEED_PATH = Path(__file__).parent / "data" / "vehicle_consumption.json"


async def seed_vehicle_specs(connection: AsyncConnection) -> None:
    records = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    if not records:
        return
    nullable_fields = {
        column.name
        for column in VehicleSpecProfile.__table__.columns
        if column.name not in {"id", "spec_key", "brand", "model", "source_url", "source_name", "data_quality", "updated_at"}
    }
    for record in records:
        for field in nullable_fields:
            record.setdefault(field, None)
        record.setdefault("data_quality", "official")
    statement = insert(VehicleSpecProfile).values(records)
    excluded = statement.excluded
    update_fields = {
        column.name: getattr(excluded, column.name)
        for column in VehicleSpecProfile.__table__.columns
        if column.name not in {"id", "spec_key", "updated_at"}
    }
    await connection.execute(statement.on_conflict_do_update(index_elements=["spec_key"], set_=update_fields))


async def seed_vehicle_consumption(connection: AsyncConnection) -> None:
    records = json.loads(CONSUMPTION_SEED_PATH.read_text(encoding="utf-8"))

    # Keep previously researched model ranges available as less-specific fallbacks.
    for profile in json.loads(SEED_PATH.read_text(encoding="utf-8")):
        if profile.get("consumption_l_100km_min") is None:
            continue
        records.append({
            "consumption_key": f"legacy-{profile['spec_key']}",
            "brand": profile["brand"],
            "model": profile["model"],
            "year_from": profile.get("year_from"),
            "year_to": profile.get("year_to"),
            "fuel_match": profile.get("consumption_fuel"),
            "liters_100km_min": profile["consumption_l_100km_min"],
            "liters_100km_max": profile.get("consumption_l_100km_max"),
            "test_standard": "objavljeni razpon",
            "source_url": profile["source_url"],
            "source_name": profile["source_name"],
            "notes": profile.get("notes"),
        })

    nullable_fields = {
        column.name for column in VehicleConsumptionProfile.__table__.columns
        if column.name not in {"id", "consumption_key", "brand", "model", "source_url", "source_name", "updated_at"}
    }
    for record in records:
        for field in nullable_fields:
            record.setdefault(field, None)
    statement = insert(VehicleConsumptionProfile).values(records)
    excluded = statement.excluded
    update_fields = {
        column.name: getattr(excluded, column.name)
        for column in VehicleConsumptionProfile.__table__.columns
        if column.name not in {"id", "consumption_key", "updated_at"}
    }
    await connection.execute(statement.on_conflict_do_update(index_elements=["consumption_key"], set_=update_fields))


def spec_matches(vehicle: Vehicle, profile: VehicleSpecProfile) -> bool:
    if (vehicle.brand or "").casefold() != profile.brand.casefold():
        return False
    if (vehicle.model or "").casefold() != profile.model.casefold():
        return False
    if profile.body_type and (vehicle.body_type or "").casefold() != profile.body_type.casefold():
        return False
    year = vehicle.first_registration.year if isinstance(vehicle.first_registration, date) else None
    if year is not None and profile.year_from is not None and year < profile.year_from:
        return False
    if year is not None and profile.year_to is not None and year > profile.year_to:
        return False
    return True


def best_spec(vehicle: Vehicle, profiles: list[VehicleSpecProfile]) -> VehicleSpecProfile | None:
    matches = [profile for profile in profiles if spec_matches(vehicle, profile)]
    if not matches:
        return None
    return max(
        matches,
        key=lambda profile: (
            profile.body_type is not None,
            profile.year_from is not None,
            profile.year_from or 0,
        ),
    )


def consumption_matches(vehicle: Vehicle, profile: VehicleConsumptionProfile) -> bool:
    if (vehicle.brand or "").casefold() != profile.brand.casefold():
        return False
    if (vehicle.model or "").casefold() != profile.model.casefold():
        return False
    year = vehicle.first_registration.year if isinstance(vehicle.first_registration, date) else None
    if year is not None and profile.year_from is not None and year < profile.year_from:
        return False
    if year is not None and profile.year_to is not None and year > profile.year_to:
        return False
    if profile.fuel_match and profile.fuel_match.casefold() not in (vehicle.fuel or "").casefold():
        return False
    if profile.power_kw is not None and vehicle.power_kw != profile.power_kw:
        return False
    if profile.transmission_type and vehicle.transmission_type != profile.transmission_type:
        return False
    return True


def best_consumption(vehicle: Vehicle, profiles: list[VehicleConsumptionProfile]) -> VehicleConsumptionProfile | None:
    matches = [profile for profile in profiles if consumption_matches(vehicle, profile)]
    if not matches:
        return None
    return max(matches, key=lambda profile: (
        profile.power_kw is not None,
        profile.transmission_type is not None,
        profile.fuel_match is not None,
        profile.year_from is not None,
        profile.year_from or 0,
    ))
