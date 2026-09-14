from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    source_vehicle_id: Mapped[str | None] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    brand: Mapped[str | None] = mapped_column(String(100), index=True)
    model: Mapped[str | None] = mapped_column(String(160), index=True)
    condition: Mapped[str | None] = mapped_column(String(64), index=True)
    first_registration: Mapped[date | None] = mapped_column(Date, index=True)
    mileage_km: Mapped[int | None] = mapped_column(Integer, index=True)
    power_kw: Mapped[int | None] = mapped_column(Integer, index=True)
    power_hp: Mapped[int | None] = mapped_column(Integer)
    fuel: Mapped[str | None] = mapped_column(String(80), index=True)
    transmission: Mapped[str | None] = mapped_column(String(100), index=True)
    transmission_type: Mapped[str | None] = mapped_column(String(32), index=True)
    regular_price_eur: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), index=True)
    financing_price_eur: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    vin: Mapped[str | None] = mapped_column(String(32), index=True)
    internal_number: Mapped[str | None] = mapped_column(String(100))
    dealership: Mapped[str | None] = mapped_column(String(160), index=True)
    location: Mapped[str | None] = mapped_column(Text)
    origin: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    warranty_available: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    warranty_max_months: Mapped[int | None] = mapped_column(Integer, index=True)
    has_tow_hitch: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    images: Mapped[list["VehicleImage"]] = relationship(back_populates="vehicle", cascade="all, delete-orphan", order_by="VehicleImage.position")
    equipment: Mapped[list["VehicleEquipment"]] = relationship(back_populates="vehicle", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_vehicle_common_filter", "is_available", "fuel", "transmission_type", "power_kw", "mileage_km"),
    )


class VehicleImage(Base):
    __tablename__ = "vehicle_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    local_path: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    vehicle: Mapped[Vehicle] = relationship(back_populates="images")

    __table_args__ = (UniqueConstraint("vehicle_id", "position"),)


class VehicleEquipment(Base):
    __tablename__ = "vehicle_equipment"

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_name: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    vehicle: Mapped[Vehicle] = relationship(back_populates="equipment")

    __table_args__ = (UniqueConstraint("vehicle_id", "category", "normalized_name"),)

