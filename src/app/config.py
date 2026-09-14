from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://vehicles:vehicles@db:5432/vehicles"
    scraper_concurrency: int = 8
    scraper_page_concurrency: int = 4
    request_min_delay_seconds: float = 0.15
    request_max_delay_seconds: float = 0.45
    request_timeout_seconds: float = 30
    request_retries: int = 3
    download_images: bool = False
    image_dir: Path = Path("/data/images")


settings = Settings()

