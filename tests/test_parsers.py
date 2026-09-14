from decimal import Decimal

from app.scraper.parsers import ListingVehicle, normalize_text, parse_detail, parse_listing


def test_listing_parser():
    html = """
    <div class="vehicle-card vehicle-card-horizontal">
      <a class="title-wrapper" href="/volkswagen/golf/rabljena-vozila/golf-123"><h2>Volkswagen Golf</h2></a>
      <ul class="vehicle-info"><li class="info-item">Rabljeno</li><li class="info-item">03/2022</li>
      <li class="info-item">99.900 km</li><li class="info-item">110 kW / 150 KM</li>
      <li class="info-item">Ročni 6</li><li class="info-item">Dizelski</li></ul>
      <div class="full-price"><div class="price-group"><span class="price-group__value">18.000 €</span></div>
      <div class="current-price price-group"><span class="price-group__value">20.000 €</span></div></div>
    </div><ul class="pagination"><li><a aria-label="Stran: 48">48</a></li></ul>
    """
    items, pages = parse_listing(html)
    assert pages == 48
    assert items[0].mileage_km == 99900
    assert items[0].power_kw == 110
    assert items[0].fuel == "Dizelski"
    assert items[0].regular_price_eur == Decimal(20000)


def test_detail_parser_equipment_warranty_and_images():
    html = """
    <div class="vehicle-header"><h1 class="title">VW Golf</h1><div class="vehicle-card-badge">TAKOJ NA VOLJO</div>
    <div class="dealership-name">Lokacija: Porsche Ljubljana, Testna 1</div></div>
    <ol class="breadcrumb"><li class="breadcrumb-item">Vsa</li><li class="breadcrumb-item">Volkswagen</li><li class="breadcrumb-item">Golf</li></ol>
    <input name="vehicleID" value="123">
    <a class="element image" href="https://example.test/images_hd/1.jpg"></a>
    <div class="vehicle-equipment"><div class="equipment-group"><button class="equipment-header-title">Uporabnost</button>
    <li class="equipment-item">Vlečna kljuka</li></div></div>
    <div class="financing-card-header"><h3>24 mesečno jamstvo</h3></div>
    """
    result = parse_detail(html, ListingVehicle("https://example.test/car", "VW Golf", transmission="Ročni 6"))
    assert result.brand == "Volkswagen"
    assert result.transmission_type == "manual"
    assert result.has_tow_hitch is True
    assert result.warranty_available is True
    assert result.warranty_max_months == 24
    assert result.images == ["https://example.test/images_hd/1.jpg"]
    assert normalize_text("Vlečna kljuka") == "vlecna kljuka"


def test_tow_hitch_abbreviation_in_title():
    html = '<div class="vehicle-header"><h1 class="title">Citan - VL.KLJUKA</h1><div class="vehicle-card-badge">TAKOJ NA VOLJO</div></div>'
    result = parse_detail(html, ListingVehicle("https://example.test/car", "Citan - VL.KLJUKA"))
    assert result.has_tow_hitch is True
