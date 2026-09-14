from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models import Base
from app.specs import seed_vehicle_consumption, seed_vehicle_specs

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        # create_all intentionally does not alter existing tables. Keep this
        # additive migration here so an existing scraped database is preserved.
        await connection.execute(text("ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS body_type VARCHAR(64)"))
        await connection.execute(text("CREATE INDEX IF NOT EXISTS ix_vehicles_body_type ON vehicles (body_type)"))
        await connection.execute(text("ALTER TABLE vehicle_spec_profiles ADD COLUMN IF NOT EXISTS consumption_fuel VARCHAR(40)"))
        await seed_vehicle_specs(connection)
        await seed_vehicle_consumption(connection)


async def get_db():
    async with SessionLocal() as session:
        yield session
