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


class VehicleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source_url: str
    source_vehicle_id: str | None
    title: str
    brand: str | None
    model: str | None
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


class VehiclePage(BaseModel):
    items: list[VehicleOut]
    total: int
    limit: int
    offset: int

