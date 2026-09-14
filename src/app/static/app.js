const PAGE_SIZE = 24;
const form = document.querySelector("#filtersForm");
const grid = document.querySelector("#vehiclesGrid");
const statusEl = document.querySelector("#status");
const emptyState = document.querySelector("#emptyState");
const pagination = document.querySelector("#pagination");
const totalEl = document.querySelector("#vehicleTotal");
const filterCountEl = document.querySelector("#activeFilterCount");
const mobileFilterCount = document.querySelector("#mobileFilterCount");
const sortEl = document.querySelector("#sort");
const dialog = document.querySelector("#vehicleDialog");
const dialogContent = document.querySelector("#dialogContent");
let offset = 0;
let requestNumber = 0;
let debounceTimer;

const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, c => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
}[c]));

const money = value => value == null ? "Cena ni navedena" : new Intl.NumberFormat("sl-SI", {
  style: "currency", currency: "EUR", maximumFractionDigits: 0
}).format(Number(value));
const number = value => value == null ? "—" : new Intl.NumberFormat("sl-SI").format(value);
const date = value => value ? value.slice(5, 7) + "/" + value.slice(0, 4) : "—";
const imageUrl = image => image?.local_path ? `/media/${image.local_path}` : image?.source_url;

function queryParams() {
  const values = new FormData(form);
  const params = new URLSearchParams({ limit: PAGE_SIZE, offset, sort: sortEl.value });
  for (const [key, value] of values.entries()) {
    if (value !== "") key === "brand" ? params.append(key, value) : params.set(key, value);
  }
  for (const checkbox of form.querySelectorAll('input[type="checkbox"]')) {
    if (checkbox.checked && checkbox.name !== "brand") params.set(checkbox.name, "true");
  }
  return params;
}

function activeFilterCount() {
  let count = 0;
  for (const field of form.elements) {
    if (!field.name) continue;
    if (field.type === "checkbox" ? field.checked : field.value !== "") count++;
  }
  filterCountEl.textContent = count;
  mobileFilterCount.textContent = count;
  return count;
}

function skeletons() {
  grid.innerHTML = Array.from({ length: 6 }, () => '<div class="skeleton"></div>').join("");
  emptyState.hidden = true;
  pagination.innerHTML = "";
}

function card(vehicle) {
  const img = imageUrl(vehicle.images?.[0]);
  const badges = [
    vehicle.has_tow_hitch ? '<span class="badge accent">Vlečna kljuka</span>' : "",
    vehicle.warranty_available ? `<span class="badge">Jamstvo${vehicle.warranty_max_months ? ` do ${vehicle.warranty_max_months} mes.` : ""}</span>` : ""
  ].join("");
  return `
    <article class="vehicle-card">
      <div class="vehicle-image">
        ${img ? `<img src="${escapeHtml(img)}" alt="${escapeHtml(vehicle.title)}" loading="lazy">` : ""}
        <div class="card-badges">${badges}</div>
      </div>
      <div class="vehicle-content">
        <div class="vehicle-kicker">${escapeHtml(vehicle.brand || "Vozilo")} · ${escapeHtml(vehicle.model || "")}</div>
        <h3>${escapeHtml(vehicle.title)}</h3>
        <ul class="vehicle-specs">
          <li><b>${number(vehicle.mileage_km)}</b> km</li>
          <li><b>${number(vehicle.power_kw)}</b> kW</li>
          <li>${escapeHtml(vehicle.fuel || "—")}</li>
          <li>${escapeHtml(vehicle.transmission || "—")}</li>
          <li>Registracija <b>${date(vehicle.first_registration)}</b></li>
          <li>${escapeHtml(vehicle.dealership || "—")}</li>
        </ul>
        <div class="card-footer">
          <div class="price"><small>Redna cena</small>${money(vehicle.regular_price_eur)}</div>
          <button class="details-button" data-id="${vehicle.id}" type="button">Podrobnosti</button>
        </div>
      </div>
    </article>`;
}

function renderPagination(total) {
  const pages = Math.ceil(total / PAGE_SIZE);
  const current = Math.floor(offset / PAGE_SIZE) + 1;
  if (pages <= 1) { pagination.innerHTML = ""; return; }
  const candidates = [...new Set([1, current - 1, current, current + 1, pages])].filter(p => p >= 1 && p <= pages);
  let html = `<button data-page="${current - 1}" ${current === 1 ? "disabled" : ""}>←</button>`;
  let previous = 0;
  for (const page of candidates) {
    if (page - previous > 1) html += "<span>…</span>";
    html += `<button data-page="${page}" class="${page === current ? "active" : ""}">${page}</button>`;
    previous = page;
  }
  html += `<button data-page="${current + 1}" ${current === pages ? "disabled" : ""}>→</button>`;
  pagination.innerHTML = html;
}

async function loadVehicles() {
  const thisRequest = ++requestNumber;
  activeFilterCount();
  skeletons();
  statusEl.textContent = "Iščem po bazi …";
  try {
    const response = await fetch(`/vehicles?${queryParams()}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    if (thisRequest !== requestNumber) return;
    totalEl.textContent = number(data.total);
    statusEl.textContent = data.total ? `Prikazujem ${data.offset + 1}–${Math.min(data.offset + data.items.length, data.total)} od ${number(data.total)} vozil` : "Ni vozil, ki ustrezajo izbranim filtrom.";
    grid.innerHTML = data.items.map(card).join("");
    emptyState.hidden = data.items.length > 0;
    renderPagination(data.total);
  } catch (error) {
    if (thisRequest !== requestNumber) return;
    grid.innerHTML = "";
    statusEl.textContent = "Podatkov ni bilo mogoče naložiti.";
    emptyState.hidden = false;
    console.error(error);
  }
}

async function loadFacets() {
  try {
    const response = await fetch("/facets");
    if (!response.ok) return;
    const data = await response.json();
    fillBrands(data.brands);
    fillSelect("bodyType", data.body_types);
    fillSelect("fuel", data.fuels);
  } catch (error) { console.error(error); }
}

function fillBrands(values = []) {
  const options = document.querySelector("#brandOptions");
  options.innerHTML = values.map(value => `
    <label class="multi-option">
      <input type="checkbox" name="brand" value="${escapeHtml(value)}">
      <span>${escapeHtml(value)}</span>
    </label>`).join("");
}

function updateBrandSummary() {
  const selected = [...form.querySelectorAll('input[name="brand"]:checked')].map(input => input.value);
  const summary = document.querySelector("#brandSummary");
  summary.textContent = selected.length === 0 ? "Vse znamke" : selected.length <= 2 ? selected.join(", ") : `${selected.length} izbrane znamke`;
}

function fillSelect(id, values = []) {
  const select = document.getElementById(id);
  const selected = select.value;
  for (const value of values) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.append(option);
  }
  select.value = selected;
}

async function showVehicle(id) {
  dialogContent.innerHTML = '<div class="skeleton"></div>';
  dialog.showModal();
  try {
    const response = await fetch(`/vehicles/${id}`);
    if (!response.ok) throw new Error();
    const v = await response.json();
    const img = imageUrl(v.images?.[0]);
    const s = v.specs;
    const c = v.consumption;
    const consumption = c?.liters_100km_min != null
      ? `${c.liters_100km_min}${c.liters_100km_max != null && c.liters_100km_max !== c.liters_100km_min ? `–${c.liters_100km_max}` : ""} l/100 km`
      : "—";
    const electricConsumption = c?.kwh_100km_min != null
      ? `${c.kwh_100km_min}${c.kwh_100km_max != null && c.kwh_100km_max !== c.kwh_100km_min ? `–${c.kwh_100km_max}` : ""} kWh/100 km`
      : "";
    const familySpecs = s ? `
      <section class="researched-specs">
        <div class="researched-heading"><h4>Družinska uporabnost</h4><span>${escapeHtml(s.generation || "profil modela")}</span></div>
        <div class="spec-grid">
          <div><b>${s.boot_liters != null ? `${number(s.boot_liters)} l` : "—"}</b><small>prtljažnik</small></div>
          <div><b>${s.boot_liters_folded != null ? `${number(s.boot_liters_folded)} l` : "—"}</b><small>s podrtimi sedeži</small></div>
          <div><b>${consumption}</b><small>objavljena poraba${c?.test_standard ? ` · ${escapeHtml(c.test_standard)}` : ""}${electricConsumption ? `<br>${escapeHtml(electricConsumption)}` : ""}</small></div>
          <div><b>${s.rear_space_rating != null ? `${s.rear_space_rating} / 5` : "—"}</b><small>prostor za otroke</small></div>
          <div><b>${s.isofix_positions ?? "—"}</b><small>ISOFIX mesti</small></div>
          <div><b>${s.child_occupant_score != null ? `${s.child_occupant_score} %` : "—"}</b><small>Euro NCAP otroci</small></div>
        </div>
        ${(s.boot_length_cm || s.boot_width_cm || s.boot_height_cm) ? `<p class="dimension-line">Mere prtljažnika: ${s.boot_length_cm ?? "—"} × ${s.boot_width_cm ?? "—"} × ${s.boot_height_cm ?? "—"} cm</p>` : ""}
        ${(s.rear_legroom_cm || s.rear_headroom_cm || s.rear_seat_width_cm) ? `<p class="dimension-line">Zadaj: noge ${s.rear_legroom_cm ?? "—"} cm · glava ${s.rear_headroom_cm ?? "—"} cm · širina klopi ${s.rear_seat_width_cm ?? "—"} cm</p>` : ""}
        ${s.notes ? `<p class="spec-note">${escapeHtml(s.notes)}</p>` : ""}
        ${c?.notes ? `<p class="spec-note">Poraba: ${escapeHtml(c.notes)}</p>` : ""}
        <a class="spec-source" href="${escapeHtml(s.source_url)}" target="_blank" rel="noreferrer">Vir: ${escapeHtml(s.source_name)} ↗</a>
        ${c && c.source_url !== s.source_url ? `<a class="spec-source" href="${escapeHtml(c.source_url)}" target="_blank" rel="noreferrer">Vir porabe: ${escapeHtml(c.source_name)} ↗</a>` : ""}
      </section>` : `<section class="researched-specs unavailable"><h4>Družinska uporabnost</h4><p>Za to generacijo še nimamo preverjenega profila.</p></section>`;
    dialogContent.innerHTML = `
      <div class="dialog-grid">
        <div class="dialog-image">${img ? `<img src="${escapeHtml(img)}" alt="${escapeHtml(v.title)}">` : ""}</div>
        <div class="dialog-info">
          <div class="vehicle-kicker">${escapeHtml(v.brand || "")} · ${escapeHtml(v.model || "")}</div>
          <h2>${escapeHtml(v.title)}</h2>
          <div class="dialog-price">${money(v.regular_price_eur)}</div>
          <div class="dialog-meta">
            <div>${number(v.mileage_km)} km</div><div>${number(v.power_kw)} kW / ${number(v.power_hp)} KM</div>
            <div>${escapeHtml(v.fuel || "—")}</div><div>${escapeHtml(v.transmission || "—")}</div>
            <div>Oblika: ${escapeHtml(v.body_type || "—")}</div>
            <div>${date(v.first_registration)}</div><div>${escapeHtml(v.dealership || "—")}</div>
            ${v.has_tow_hitch ? "<div>✓ Vlečna kljuka</div>" : ""}
            ${v.warranty_available ? `<div>✓ Jamstvo${v.warranty_max_months ? ` do ${v.warranty_max_months} mesecev` : ""}</div>` : ""}
          </div>
          ${familySpecs}
          <h4>Oprema (${v.equipment.length})</h4>
          <div class="equipment-list">${v.equipment.map(e => `<span>${escapeHtml(e.name)}</span>`).join("") || "Ni podatkov"}</div>
          <a class="source-button" href="${escapeHtml(v.source_url)}" target="_blank" rel="noreferrer">Odpri originalni oglas ↗</a>
        </div>
      </div>`;
  } catch { dialogContent.innerHTML = '<div class="empty-state"><h3>Napaka pri nalaganju</h3></div>'; }
}

function resetFilters() {
  form.reset();
  updateBrandSummary();
  offset = 0;
  loadVehicles();
}

form.addEventListener("input", () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => { offset = 0; loadVehicles(); }, 350);
});
form.addEventListener("change", () => { clearTimeout(debounceTimer); offset = 0; loadVehicles(); });
form.addEventListener("change", event => { if (event.target.name === "brand") updateBrandSummary(); });
sortEl.addEventListener("change", () => { offset = 0; loadVehicles(); });
document.querySelector("#resetFilters").addEventListener("click", resetFilters);
document.querySelector("#emptyReset").addEventListener("click", resetFilters);
grid.addEventListener("click", event => {
  const button = event.target.closest("[data-id]");
  if (button) showVehicle(button.dataset.id);
});
pagination.addEventListener("click", event => {
  const button = event.target.closest("[data-page]");
  if (!button || button.disabled) return;
  offset = (Number(button.dataset.page) - 1) * PAGE_SIZE;
  loadVehicles();
  document.querySelector(".results-panel").scrollIntoView({ behavior: "smooth" });
});
document.querySelector("#filterToggle").addEventListener("click", event => {
  const panel = document.querySelector("#filtersPanel");
  panel.classList.toggle("open");
  event.currentTarget.setAttribute("aria-expanded", panel.classList.contains("open"));
});
document.querySelector(".dialog-close").addEventListener("click", () => dialog.close());
dialog.addEventListener("click", event => { if (event.target === dialog) dialog.close(); });
document.addEventListener("click", event => {
  const picker = document.querySelector("#brandPicker");
  if (picker.open && !picker.contains(event.target)) picker.removeAttribute("open");
});

loadFacets();
loadVehicles();
