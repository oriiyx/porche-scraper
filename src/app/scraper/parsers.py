import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

BASE_URL = "https://www.porscheinterauto.net"
LISTING_URL = f"{BASE_URL}/vozila/?filter=status:1&uredi=asc&uredi_po=cena_eur"
BODY_TYPES = {
    22: "cabriolet",
    8: "coupe",
    12: "dostavno",
    6: "enoprostorec",
    4: "karavan",
    1: "kombilimuzina",
    2: "limuzina",
    24: "SUV",
    3: "terenec/šasija s kabino",
}


def clean(value: str | None) -> str:
    return " ".join((value or "").split())


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.lower())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return clean(re.sub(r"[^a-z0-9]+", " ", value))


def integer(value: str | None) -> int | None:
    digits = re.sub(r"\D", "", value or "")
    return int(digits) if digits else None


def price(value: str | None) -> Decimal | None:
    number = integer(value)
    return Decimal(number) if number is not None else None


def registration(value: str | None) -> date | None:
    match = re.fullmatch(r"\s*(\d{1,2})/(\d{4})\s*", value or "")
    return date(int(match.group(2)), int(match.group(1)), 1) if match else None


def transmission_type(value: str | None) -> str | None:
    normalized = normalize_text(value or "")
    if normalized.startswith("rocni"):
        return "manual"
    if "polavtom" in normalized:
        return "semiautomatic"
    if normalized and any(token in normalized for token in ("avtom", "tiptronic", "steptronic", "dsg", "stronic")):
        return "automatic"
    return None


@dataclass
class ListingVehicle:
    source_url: str
    title: str
    condition: str | None = None
    first_registration: date | None = None
    mileage_km: int | None = None
    power_kw: int | None = None
    power_hp: int | None = None
    fuel: str | None = None
    transmission: str | None = None
    regular_price_eur: Decimal | None = None
    financing_price_eur: Decimal | None = None


@dataclass
class VehicleData:
    source_url: str
    title: str
    brand: str | None = None
    model: str | None = None
    body_type: str | None = None
    source_vehicle_id: str | None = None
    condition: str | None = None
    first_registration: date | None = None
    mileage_km: int | None = None
    power_kw: int | None = None
    power_hp: int | None = None
    fuel: str | None = None
    transmission: str | None = None
    transmission_type: str | None = None
    regular_price_eur: Decimal | None = None
    financing_price_eur: Decimal | None = None
    vin: str | None = None
    internal_number: str | None = None
    dealership: str | None = None
    location: str | None = None
    origin: str | None = None
    description: str | None = None
    is_available: bool = True
    warranty_available: bool = False
    warranty_max_months: int | None = None
    has_tow_hitch: bool = False
    images: list[str] = field(default_factory=list)
    equipment: list[tuple[str | None, str, str]] = field(default_factory=list)


def parse_listing(html: str) -> tuple[list[ListingVehicle], int]:
    soup = BeautifulSoup(html, "html.parser")
    last_page = 1
    for link in soup.select("ul.pagination a[aria-label^='Stran:']"):
        match = re.search(r"(\d+)", link.get("aria-label", ""))
        if match:
            last_page = max(last_page, int(match.group(1)))

    vehicles = []
    for card in soup.select(".vehicle-card.vehicle-card-horizontal"):
        title_link = card.select_one("a.title-wrapper[href]")
        if not title_link:
            continue
        title = clean(title_link.get_text(" "))
        values = [clean(item.get_text(" ")) for item in card.select(".vehicle-info .info-item")]
        item = ListingVehicle(source_url=urljoin(BASE_URL, title_link["href"]), title=title)
        for value in values:
            normalized = normalize_text(value)
            power_match = re.search(r"(\d+)\s*kW\s*/\s*(\d+)\s*KM", value, re.I)
            if re.fullmatch(r"\d{1,2}/\d{4}", value):
                item.first_registration = registration(value)
            elif re.fullmatch(r"[\d. ]+\s*km", value, re.I):
                item.mileage_km = integer(value)
            elif power_match:
                item.power_kw, item.power_hp = map(int, power_match.groups())
            elif normalized in {"novo", "novo vozilo", "rabljeno", "rabljeno vozilo", "sluzbeno vozilo", "testno sluzbeno"}:
                item.condition = value
            elif any(word in normalized for word in ("dizel", "diesel", "bencin", "elektr", "hibrid", "plin")):
                item.fuel = value
            elif transmission_type(value):
                item.transmission = value
        regular = card.select_one(".current-price .price-group__value")
        financing = card.select_one(".full-price > .price-group:not(.current-price):not(.discount) .price-group__value")
        item.regular_price_eur = price(clean(regular.get_text()) if regular else None)
        item.financing_price_eur = price(clean(financing.get_text()) if financing else None)
        if item.fuel is None:
            title_normalized = normalize_text(title)
            if any(token in title_normalized for token in ("tdi", "cdti", "cdi", "dci", "turbodiesel", "diesel", "dizel")):
                item.fuel = "Dizelski"
            elif "hibrid" in title_normalized or "hybrid" in title_normalized:
                item.fuel = "Hibridni"
            elif any(token in title_normalized for token in ("bencin", "tsi", "tfsi", "mpi", "ecoboost")):
                item.fuel = "Bencinski"
        vehicles.append(item)
    return vehicles, last_page


def parse_detail(html: str, listing: ListingVehicle) -> VehicleData:
    soup = BeautifulSoup(html, "html.parser")
    title_node = soup.select_one(".vehicle-header h1.title")
    data = VehicleData(source_url=listing.source_url, title=clean(title_node.get_text(" ")) if title_node else listing.title)
    for name in ("condition", "first_registration", "mileage_km", "power_kw", "power_hp", "fuel", "transmission", "regular_price_eur", "financing_price_eur"):
        setattr(data, name, getattr(listing, name))

    crumbs = [clean(node.get_text(" ")) for node in soup.select("ol.breadcrumb .breadcrumb-item")]
    if len(crumbs) >= 3:
        data.brand, data.model = crumbs[1], crumbs[2]

    overview = {}
    for prop in soup.select(".vehicle-info-overview .info-property"):
        label, value = prop.select_one(".info-label"), prop.select_one(".info-value")
        if label and value:
            overview[normalize_text(label.get_text(" "))] = clean(value.get_text(" "))
    data.condition = overview.get("stanje vozila", data.condition)
    data.first_registration = registration(overview.get("1 registracija")) or data.first_registration
    data.mileage_km = integer(overview.get("kilometrina")) or data.mileage_km
    power_match = re.search(r"(\d+)\s*kW\s*/\s*(\d+)\s*KM", overview.get("motor", ""), re.I)
    if power_match:
        data.power_kw, data.power_hp = map(int, power_match.groups())
    data.transmission = overview.get("menjalnik", data.transmission)
    data.transmission_type = transmission_type(data.transmission)
    data.internal_number = overview.get("interna stevilka")
    data.vin = overview.get("vin")

    vehicle_id = soup.select_one("input[name='vehicleID']")
    data.source_vehicle_id = vehicle_id.get("value") if vehicle_id else None
    dealer = soup.select_one(".vehicle-header .dealership-name")
    data.location = clean(dealer.get_text(" ")) if dealer else None
    data.dealership = data.location.removeprefix("Lokacija:").split(",", 1)[0].strip() if data.location else None
    origin = soup.select_one(".vehicle-header .label-origin")
    data.origin = clean(origin.get_text(" ")) if origin else None
    description = soup.select_one(".vehicle-additional-description")
    data.description = clean(description.get_text(" ")) if description else None
    badge = soup.select_one(".vehicle-header .vehicle-card-badge")
    # The URL inventory comes from the site's explicit status:1 (in-stock) filter.
    # Only override it if a vehicle was sold between listing and detail requests.
    data.is_available = not (badge and "prodano" in normalize_text(badge.get_text(" ")))

    seen_images = set()
    for link in soup.select(".vehicle-gallery a.element.image[href], .gallery a.element.image[href]"):
        image_url = urljoin(BASE_URL, link["href"])
        if image_url not in seen_images:
            data.images.append(image_url)
            seen_images.add(image_url)
    if not data.images:
        for link in soup.select("a.element.image[href*='images_hd']"):
            image_url = urljoin(BASE_URL, link["href"])
            if image_url not in seen_images:
                data.images.append(image_url)
                seen_images.add(image_url)

    for group in soup.select(".vehicle-equipment .equipment-group"):
        category_node = group.select_one(".equipment-header-title")
        category = clean(category_node.get_text(" ")) if category_node else None
        for node in group.select(".equipment-item"):
            name = clean(node.get_text(" "))
            normalized = normalize_text(name)
            if name and normalized:
                data.equipment.append((category, name, normalized))

    warranty_months = []
    for heading in soup.select(".financing-card-header h3"):
        text = normalize_text(heading.get_text(" "))
        match = re.search(r"(\d+)\s*mesec", text)
        if match and "brez jamstva" not in text:
            warranty_months.append(int(match.group(1)))
    data.warranty_available = bool(warranty_months)
    data.warranty_max_months = max(warranty_months, default=None)

    haystack = " ".join([normalize_text(data.title), normalize_text(data.description or "")] + [item[2] for item in data.equipment])
    data.has_tow_hitch = any(
        term in haystack for term in ("vlecna kljuka", "vlecna naprava", "vl naprava", "vl kljuka", "towbar")
    )
    return data
