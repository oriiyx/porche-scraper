from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    source_url: str
    local_path: str | None
    position: int


class EquipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    category: str | None
    name: str


class VehicleSpecOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    generation: str | None
    body_type: str | None
    year_from: int | None
    year_to: int | None
    boot_liters: int | None
    boot_liters_folded: int | None
    boot_length_cm: Decimal | None
    boot_width_cm: Decimal | None
    boot_height_cm: Decimal | None
    rear_legroom_cm: Decimal | None
    rear_headroom_cm: Decimal | None
    rear_seat_width_cm: Decimal | None
    isofix_positions: int | None
    child_occupant_score: int | None
    rear_space_rating: int | None
    consumption_l_100km_min: Decimal | None
    consumption_l_100km_max: Decimal | None
    consumption_fuel: str | None
    source_url: str
    source_name: str
    data_quality: str
    notes: str | None


class VehicleConsumptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    fuel_match: str | None
    power_kw: int | None
    transmission_type: str | None
    liters_100km_min: Decimal | None
    liters_100km_max: Decimal | None
    kwh_100km_min: Decimal | None
    kwh_100km_max: Decimal | None
    test_standard: str | None
    source_url: str
    source_name: str
    notes: str | None


class VehicleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source_url: str
    source_vehicle_id: str | None
    title: str
    brand: str | None
    model: str | None
    body_type: str | None
    condition: str | None
    first_registration: date | None
    mileage_km: int | None
    power_kw: int | None
    power_hp: int | None
    fuel: str | None
    transmission: str | None
    transmission_type: str | None
    regular_price_eur: Decimal | None
    financing_price_eur: Decimal | None
    vin: str | None
    internal_number: str | None
    dealership: str | None
    location: str | None
    origin: str | None
    description: str | None
    is_available: bool
    warranty_available: bool
    warranty_max_months: int | None
    has_tow_hitch: bool
    scraped_at: datetime
    last_seen_at: datetime
    images: list[ImageOut]
    equipment: list[EquipmentOut]
    specs: VehicleSpecOut | None = None
    consumption: VehicleConsumptionOut | None = None


class VehiclePage(BaseModel):
    items: list[VehicleOut]
    total: int
    limit: int
    offset: int
