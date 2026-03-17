# SPOOL STATION

**3D Printer Filament Inventory Manager**

A PyQt6 desktop application for managing 3D printer filament spool inventories, tracking usage, generating slicer profiles, and exposing a color-matching REST API for integration with other tools.

Built with an 80s retro neon theme (cyan/magenta/purple) matching [Logo Station](https://github.com/FearTheBeardDesigns/logo-station).

---

## Features at a Glance

- Complete vendor, filament, and spool inventory management
- 17 pre-loaded manufacturers with 1,484+ filament products
- SpoolmanDB community database integration (6,900+ filaments, 53 manufacturers)
- Weight-based consumption tracking with usage logs
- Slicer profile generation for PrusaSlicer (.ini) and OrcaSlicer (.json)
- REST API with color-matching endpoints for Logo Station integration
- Favorites system for quick access to go-to filaments
- Auto-migration for painless schema upgrades

---

## Installation

### Requirements

- Python 3.10+
- pip

### Setup

```bash
git clone https://github.com/FearTheBeardDesigns/spool-station.git
cd spool-station
pip install -r requirements.txt
python main.py
```

### Dependencies

| Package | Purpose |
|---------|---------|
| PyQt6 >= 6.6.0 | GUI framework |
| SQLAlchemy >= 2.0.0 | ORM and database |
| FastAPI >= 0.110.0 | REST API |
| uvicorn >= 0.29.0 | ASGI server |
| pydantic >= 2.6.0 | Data validation |
| numpy >= 1.26.0 | Numerical computation |
| qrcode >= 7.4 | QR code generation |
| Pillow >= 10.2.0 | Image handling |
| python-dateutil >= 2.9.0 | Date utilities |

---

## Application Layout

The app has four main tabs, each accessible from the top tab bar:

### 1. Inventory Tab

The primary spool inventory view. Shows all your physical spools in a sortable, filterable table.

**Table Columns:**
- **COLOR** -- Color swatch with hex code
- **FILAMENT** -- Product name
- **VENDOR** -- Manufacturer
- **MATERIAL** -- PLA, PETG, ABS, etc.
- **REMAINING** -- Grams remaining (computed from initial - used)
- **%** -- Percentage remaining, color-coded: green (>50%), orange (25-50%), red (<25%)
- **LENGTH** -- Estimated meters remaining (calculated from weight, density, and diameter)
- **LOCATION** -- Physical storage location
- **LAST USED** -- Date of most recent usage

**Filters:**
- Material dropdown (populated from your inventory)
- Location dropdown (populated from your spools)
- Free-text search (searches filament name, vendor, color, material, location)
- "Show Archived" checkbox to include empty/retired spools

**Actions:**
- **ADD SPOOL** -- Opens the spool creation dialog. Select a vendor, pick a filament, set initial weight and storage location.
- **EDIT** -- Modify any spool property. Double-click a row as a shortcut.
- **USE FILAMENT** -- Quick-use dialog to log consumption. Enter grams used, source (manual/prusaslicer/orcaslicer/other), and optional project name. Creates a timestamped usage log entry.
- **ARCHIVE** -- Toggle the archived flag on a spool. Archived spools are hidden by default.

### 2. Vendors Tab

Two-pane layout for managing manufacturers and their filament product lines.

**Left Pane -- Manufacturer List:**

Shows all vendors with filament count and spool count. Select a vendor to see their products on the right.

- **ADD** -- Create a custom vendor (name, website, default spool weight, notes)
- **IMPORT PRESET** -- Multi-select dialog listing all 17 pre-loaded manufacturers. Each shows the number of filaments in their catalog. Already-imported vendors are excluded.
- **UPDATE CATALOG** -- Merge new filaments from the latest seed data into an existing vendor. Only appears for vendors that match a preset name. Rules:
  - New filaments (not in DB) are added
  - Existing filaments without spools get specs updated
  - Existing filaments with active spools are skipped (preserves your data)
  - Filaments in your DB but not in seed data are kept (never deleted)
- **SPOOLMANDB** -- Fetch the community SpoolmanDB database from the internet (6,900+ filaments across 53 manufacturers). Shows a multi-select picker. For each selected manufacturer:
  - Creates the vendor if it doesn't exist
  - Merges new filaments into existing vendors using the same safe merge logic
- **EDIT** -- Modify vendor details
- **DELETE** -- Remove vendor and all associated filaments and spools (with confirmation)

**Right Pane -- Filament Table:**

Shows products for the selected vendor with filters and a favorites system.

- **Material filter** dropdown to narrow by material type
- **FAVORITES checkbox** to show only starred filaments
- **Star column** -- Click the star icon to toggle a filament as a favorite. Favorites persist across sessions.

**Table Columns:** Star, Color, Name, Material, Tensile Strength, Diameter, Density, Temperature, Price

- **ADD FILAMENT** -- Full filament creation form
- **EDIT** -- Modify any filament property
- **COPY** -- Duplicate a filament with "(Copy)" suffix, same specs
- **DELETE** -- Remove filament (and any associated spools)

### 3. Profiles Tab

Generate slicer configuration profiles from your filament database.

**Options:**
- **Target Slicer** -- Radio buttons for PrusaSlicer or OrcaSlicer
- **Filament Selection** -- Checklist of all filaments with Select All / Deselect All
- **Output Directory** -- Auto-detects slicer config paths or browse to custom directory
- **Generate Profiles** -- Writes profile files for each selected filament

**PrusaSlicer Output (.ini):**
```ini
filament_settings_id = Prusament PLA Galaxy Black
filament_type = PLA
filament_vendor = Prusament
filament_colour = #1A1A2E
filament_diameter = 1.75
filament_density = 1.24
filament_cost = 24.99
temperature = 215
first_layer_temperature = 220
bed_temperature = 60
first_layer_bed_temperature = 65
```

**OrcaSlicer Output (.json):**
```json
{
  "type": "filament",
  "name": "Prusament PLA Galaxy Black",
  "inherits": "Generic PLA",
  "filament_type": ["PLA"],
  "filament_colour": ["#1A1A2E"],
  "nozzle_temperature": ["215"],
  "hot_plate_temp": ["60"]
}
```

### 4. Settings Tab

Application configuration.

- **API Server** -- Port configuration (default 7912), status indicator, base URL display
- **Slicer Paths** -- Auto-detected or manually browsed paths for PrusaSlicer and OrcaSlicer config directories
- **Logo Station Integration** -- Enable/disable the color API endpoint
- **Database** -- Shows DB path, export/import buttons for backup

---

## Data Model

Four tables in a relational chain:

```
Vendor (1) ──> (N) Filament (1) ──> (N) Spool (1) ──> (N) UsageLog
```

### Vendor
| Field | Type | Description |
|-------|------|-------------|
| name | string | Manufacturer name |
| website | string | URL (optional) |
| empty_spool_weight_g | float | Default tare weight for this vendor's spools |
| notes | text | Free-text notes |

### Filament
| Field | Type | Description |
|-------|------|-------------|
| name | string | Product name (e.g., "PLA+ Red") |
| material | string | PLA, PLA+, PETG, ABS, ASA, TPU, Nylon, PC, etc. |
| color_hex | string | Hex color code (e.g., "#FF0000") |
| color_name | string | Human-readable color name |
| diameter_mm | float | 1.75 or 2.85 |
| density_g_cm3 | float | Material density |
| net_weight_g | float | Rated filament weight per spool |
| spool_weight_g | float | Empty spool weight |
| nozzle_temp_min/default/max | int | Nozzle temperature range |
| bed_temp_min/default/max | int | Bed temperature range |
| tensile_strength_mpa | float | Tensile strength of printed parts |
| max_print_speed | float | Maximum recommended speed (mm/s) |
| max_volumetric_flow | float | Maximum flow rate (mm3/s) |
| price | float | Cost per unit |
| price_unit | string | "per_spool" or "per_kg" |
| finish | string | Surface finish (matte, glossy, satin, silk, metallic) |
| pattern | string | Visual pattern (sparkle, marble, wood, galaxy, rainbow) |
| translucent | bool | Translucent/transparent flag |
| glow | bool | Glow-in-the-dark flag |
| multi_color_direction | string | Multi-color transition (coaxial, longitudinal) |
| color_hexes | string | Comma-separated hex codes for multi-color filaments |
| spool_type | string | Spool material (plastic, cardboard, refill) |
| external_id | string | SpoolmanDB reference ID |
| favorite | bool | User favorite flag |

### Spool
| Field | Type | Description |
|-------|------|-------------|
| initial_weight_g | float | Net weight when new |
| used_weight_g | float | Total grams consumed |
| measured_weight_g | float | Actual scale measurement (optional) |
| location | string | Physical storage location |
| lot_nr | string | Manufacturing batch number |
| purchase_date | date | When purchased |
| first_used | datetime | First usage timestamp |
| last_used | datetime | Most recent usage |
| archived | bool | Retired/empty flag |
| notes | text | Free-text notes |

**Computed Properties:**
- `remaining_weight_g` = max(0, initial - used)
- `remaining_percent` = (remaining / initial) * 100
- `remaining_length_m` = estimated meters from weight, density, and filament diameter

### UsageLog
| Field | Type | Description |
|-------|------|-------------|
| used_weight_g | float | Grams consumed |
| source | string | How tracked (manual, prusaslicer, orcaslicer, other) |
| project_name | string | What was printed |
| timestamp | datetime | When the usage occurred |

---

## Pre-Loaded Manufacturers

17 vendors with full filament catalogs, including material specs, temperatures, and pricing:

| Vendor | Filaments | Materials |
|--------|-----------|-----------|
| Prusament | 80+ | PLA, PETG, ASA, PC Blend, PVB |
| Bambu Lab | 100+ | PLA, PETG, ABS, ASA, TPU, PA, PET-CF, PA-CF |
| Elegoo | 185 | PLA, PLA+, PETG, ABS, ASA, TPU |
| Hatchbox | 100+ | PLA, PLA+, PETG, ABS, TPU, Wood |
| eSUN | 100+ | PLA+, PLA Silk, PETG, ABS, ASA, TPU, Nylon, CF |
| Polymaker | 190+ | PolyLite, PolyTerra, PolyMax, PolySmooth, ASA |
| Fiberon | 22 | ASA-CF, PETG-CF, PET-CF, PA6-CF, PA-GF, PPS-CF |
| Overture | 80+ | PLA, PLA+, PETG, ABS, TPU |
| Inland | 60+ | PLA, PLA+, PETG, ABS, TPU |
| Sunlu | 80+ | PLA, PLA+, PETG, ABS, ASA, TPU, Silk |
| Eryone | 60+ | PLA, PLA+, PETG, TPU, Silk |
| Tinmorry | 155 | PLA, Silk PLA, PETG, Metallic PETG, ABS, ASA |
| Fiberlogy | 132 | Easy PLA, Impact PLA, Easy PETG, ABS, FiberFlex TPU |
| Amazon Basics | 39 | PLA, PETG, ABS |
| MatterHackers | 50+ | Build PLA, NylonX, NylonG, PETG |
| Creality | 40+ | Hyper PLA, Hyper PETG, CR-ABS, CR-TPU |
| Jayo | 60+ | PLA, PLA+, Silk PLA, PETG, ABS, TPU |

Each filament includes material defaults for density, nozzle/bed temperature ranges, max volumetric flow, and tensile strength.

---

## SpoolmanDB Integration

[SpoolmanDB](https://github.com/Donkie/SpoolmanDB) is a community-maintained filament database with 6,900+ products from 53 manufacturers.

**How it works:**
1. Click **SPOOLMANDB** in the Vendors tab
2. The app fetches `filaments.json` from GitHub Pages (no API key needed)
3. A picker dialog shows all available manufacturers with filament counts
4. Select one or more manufacturers to import
5. New vendors are created automatically; existing vendors get merged

**Data mapped from SpoolmanDB:**
- Name, material, color hex, density, diameter, weight
- Spool weight, nozzle temperature, bed temperature
- Temperature ranges (min/max)
- Surface finish, pattern, translucent, glow flags
- Multi-color direction, spool type
- External ID for reference

---

## REST API

The app runs a FastAPI server on `localhost:7912` (configurable) that exposes a full REST API.

### Health
```
GET /api/v1/health
```
Returns status, version, and spool count.

### Vendors
```
GET    /api/v1/vendors              List all vendors
GET    /api/v1/vendors/{id}         Get vendor by ID
POST   /api/v1/vendors              Create vendor
PATCH  /api/v1/vendors/{id}         Update vendor
DELETE /api/v1/vendors/{id}         Delete vendor
```

### Filaments
```
GET    /api/v1/filaments            List filaments (filter: vendor_id, material)
GET    /api/v1/filaments/{id}       Get filament by ID
POST   /api/v1/filaments            Create filament
PATCH  /api/v1/filaments/{id}       Update filament
DELETE /api/v1/filaments/{id}       Delete filament (blocked if has spools)
```

### Spools
```
GET    /api/v1/spools               List spools (filter: filament_id, material, location, allow_archived)
GET    /api/v1/spools/{id}          Get spool by ID
POST   /api/v1/spools               Create spool
PATCH  /api/v1/spools/{id}          Update spool
DELETE /api/v1/spools/{id}          Delete spool
PUT    /api/v1/spools/{id}/use      Log filament usage (grams, source, project)
PUT    /api/v1/spools/{id}/measure  Weigh-in (set measured weight, auto-calculate used)
```

### Colors (Logo Station Integration)
```
GET /api/v1/colors
```
Returns all active spool colors with remaining amounts, materials, and vendor info.

```
GET /api/v1/colors/match?hex=FF0000&material=PLA&min_remaining_g=50
```
Find the closest filament match to a target color. Returns ranked suggestions sorted by CIE76 delta-E color distance.

```
GET /api/v1/colors/match-palette?hexes=FF0000,00FF00,0000FF
```
Match multiple colors at once. Returns suggestions for each color in the palette.

### Color Matching Algorithm

Uses CIE76 delta-E distance in Lab color space:
1. Convert hex to sRGB
2. Apply gamma correction to linear RGB
3. Transform to XYZ (D65 illuminant)
4. Convert to Lab color space
5. Calculate Euclidean distance between Lab values

Delta-E interpretation:
- < 5: Excellent match
- 5-15: Good match
- 15-30: Noticeable difference
- \> 30: Very different colors

---

## Logo Station Integration

Spool Station exposes color inventory data that [Logo Station](https://github.com/FearTheBeardDesigns/logo-station) can query for 3MF color matching.

**Discovery:** Logo Station checks `http://localhost:7912/api/v1/health`. If reachable, the 3D Print panel enables filament matching.

**Workflow:**
1. Logo Station sends the color palette from a design to `/api/v1/colors/match-palette`
2. Spool Station returns ranked filament suggestions for each color (sorted by perceptual distance)
3. The user manually picks which spool to use for each layer
4. No auto-assignment -- the user always makes the final choice

---

## Database

SQLite database stored at `~/.spool-station/spool_station.db` (or set `SPOOL_STATION_DATA` environment variable for a custom location).

**Auto-Migration:** When new columns are added to the models, `init_db()` automatically runs `ALTER TABLE ADD COLUMN` for any missing columns. No need to delete your database when upgrading.

**Backup:** Use the EXPORT DB button in Settings to save a copy. Import restores from a backup file (requires app restart).

---

## Project Structure

```
spool-station/
+-- main.py                              Entry point
+-- requirements.txt                     Python dependencies
+-- .gitignore
+-- app/
    +-- main_window.py                   Main window (tabs, header, API server)
    +-- theme.py                         Neon theme (Colors class + QSS stylesheet)
    +-- db/
    |   +-- engine.py                    SQLAlchemy engine, session factory, migrations
    |   +-- models.py                    Vendor, Filament, Spool, UsageLog ORM models
    |   +-- seed_data.py                 17 manufacturers, 1484+ filament presets
    |   +-- spoolmandb.py                Community database fetch and parsing
    +-- widgets/
    |   +-- inventory_panel.py           Spool inventory table with filters and actions
    |   +-- vendors_panel.py             Vendor/filament management (two-pane)
    |   +-- filament_detail_dialog.py    Filament creation/edit form (30+ fields)
    |   +-- spool_detail_dialog.py       Spool creation/edit form
    |   +-- vendor_detail_dialog.py      Vendor creation/edit form
    |   +-- profiles_panel.py            Slicer profile generation UI
    |   +-- settings_panel.py            App configuration (API, paths, DB)
    |   +-- color_swatch_widget.py       Color rectangle display component
    |   +-- screen_color_picker.py       Full-screen eyedropper with 8x zoom
    +-- slicer/
    |   +-- prusaslicer.py               PrusaSlicer .ini profile generator
    |   +-- orcaslicer.py                OrcaSlicer .json profile generator
    +-- api/
    |   +-- server.py                    FastAPI server (20+ endpoints)
    |   +-- schemas.py                   Pydantic request/response models
    +-- utils/
        +-- color_distance.py            CIE76 delta-E color matching
```

---

## Typical Workflows

### First-Time Setup
1. Launch the app -- database is created automatically at `~/.spool-station/`
2. Go to the **Vendors** tab and click **IMPORT PRESET**
3. Select the manufacturers you use (e.g., Elegoo, Hatchbox, Bambu Lab)
4. Their full filament catalogs are imported with specs, temperatures, and pricing
5. Switch to the **Inventory** tab and click **ADD SPOOL**
6. Select a filament, set the initial weight and storage location
7. Your spool appears in the inventory table

### Track Filament Usage
1. Select a spool in the **Inventory** tab
2. Click **USE FILAMENT**
3. Enter grams used, source (manual/prusaslicer/orcaslicer), and project name
4. A timestamped usage log is created
5. The remaining weight and percentage update immediately

### Update Catalogs
1. When new products are added to the built-in presets, select the vendor and click **UPDATE CATALOG**
2. New filaments are added, existing ones with no spools get specs updated, filaments with active spools are left untouched
3. For community updates, click **SPOOLMANDB** to fetch the latest from the internet

### Generate Slicer Profiles
1. Go to the **Profiles** tab
2. Select PrusaSlicer or OrcaSlicer
3. Check the filaments you want profiles for
4. Click **GENERATE PROFILES**
5. Profile files are written to your slicer's config directory

---

## Technical Details

- **GUI Framework:** PyQt6 with custom QSS neon theme
- **Database:** SQLite via SQLAlchemy 2.0 (mapped ORM with type annotations)
- **API:** FastAPI with CORS enabled, runs in a daemon thread on startup
- **Color Matching:** CIE76 delta-E in Lab color space (sRGB -> XYZ -> Lab)
- **Profile Formats:** PrusaSlicer .ini (flat key-value) and OrcaSlicer .json (hierarchical with inherits)
- **SpoolmanDB:** Static JSON fetch from GitHub Pages (no API key, no rate limits)
- **Screen Color Picker:** Full-screen overlay with 8x magnified preview, crosshair, and hex readout

---

## License

MIT

---

*Built by [Fear The Beard Designs](https://github.com/FearTheBeardDesigns)*
