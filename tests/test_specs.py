import json
from datetime import date

from app.models import Vehicle, VehicleConsumptionProfile, VehicleSpecProfile
from app.specs import CONSUMPTION_SEED_PATH, SEED_PATH, best_consumption, best_spec


def test_best_spec_uses_body_and_generation():
    vehicle = Vehicle(
        source_url="https://example.test/octavia",
        title="Skoda Octavia Combi",
        brand="Skoda",
        model="Octavia",
        body_type="karavan",
        first_registration=date(2022, 5, 1),
    )
    liftback = VehicleSpecProfile(
        spec_key="octavia-liftback",
        brand="Skoda",
        model="Octavia",
        body_type="limuzina",
        year_from=2020,
        source_url="https://example.test/liftback",
        source_name="Test",
    )
    combi = VehicleSpecProfile(
        spec_key="octavia-combi",
        brand="Skoda",
        model="Octavia",
        body_type="karavan",
        year_from=2020,
        boot_liters=640,
        source_url="https://example.test/combi",
        source_name="Test",
    )

    assert best_spec(vehicle, [liftback, combi]) is combi


def test_seed_profiles_have_sources_and_valid_ratings():
    records = json.loads(SEED_PATH.read_text(encoding="utf-8"))

    assert len(records) >= 20
    assert len({record["spec_key"] for record in records}) == len(records)
    assert all(record["source_url"].startswith("https://") for record in records)
    assert all(1 <= record.get("rear_space_rating", 1) <= 5 for record in records)


def test_consumption_prefers_exact_engine_profile():
    vehicle = Vehicle(source_url="https://example.test/passat", title="Passat", brand="Volkswagen", model="Passat Variant",
                      first_registration=date(2020, 1, 1), fuel="Dizel", power_kw=110, transmission_type="automatic")
    generic = VehicleConsumptionProfile(consumption_key="generic", brand="Volkswagen", model="Passat Variant",
        fuel_match="dizel", liters_100km_min=5.0, source_url="https://example.test/generic", source_name="Test")
    exact = VehicleConsumptionProfile(consumption_key="exact", brand="Volkswagen", model="Passat Variant",
        year_from=2019, year_to=2023, fuel_match="dizel", power_kw=110, liters_100km_min=4.1,
        source_url="https://example.test/exact", source_name="Test")

    assert best_consumption(vehicle, [generic, exact]) is exact


def test_consumption_seed_has_exact_passat():
    records = json.loads(CONSUMPTION_SEED_PATH.read_text(encoding="utf-8"))
    assert any(r["model"] == "Passat Variant" and r.get("power_kw") == 110 and r.get("fuel_match") == "dizel" for r in records)
