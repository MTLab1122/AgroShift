# Module 02: NASA Earth Observation & Climate Data Engine

**AgroShift — Team InCir (Innovation Circle), Abasyn University Peshawar**  
**NASA Space Apps Challenge 2026**  
**Module Owner:** Muhammad Talha (Team Lead)  
**Branch:** `feature/nasa-data` | **Target Integration Branch:** `develop`

---

## 1. Module Overview & Responsibilities

Module 02 is the meteorological foundation for AgroShift. Given a `FarmProfile` (`farm_id`, `latitude`, `longitude`) from Module 01 and an ISO date interval (`start_date`, `end_date`), Module 02:
1. Validates coordinate bounds (`[-90, 90]`, `[-180, 180]`) and temporal integrity *before* initiating any network connection.
2. Interrogates the **NASA POWER Daily API** (`https://power.larc.nasa.gov/api/temporal/daily/point`, Agroclimatology `AG` community) with exponential backoff and retry policies.
3. Normalizes daily readings into canonical `DailyRecord` entries, converting NASA `-999.0` sentinel fill values strictly into `null` (`None` in Python) without 0-imputation.
4. Computes calendar **monthly** and agro-ecological **seasonal** (Kharif / Rabi) aggregates with per-parameter methodology documentation (`mean` for temperature, `sum` for precipitation).
5. Returns the canonical `ClimateSummary` schema or a structured `ApiError` envelope for downstream recommendation (Module 03) and visualization (Module 04).

---

## 2. API Endpoints

All backend routes are prefixed with `/api/v1` (with root `/health` available for service orchestration):

| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/health` | Service health status and in-memory cache metric. |
| `GET` | `/api/v1/climate/summary` | Canonical `ClimateSummary` with aggregates, missing-data audit, and provenance. |
| `GET` | `/api/v1/climate/history` | Chronological daily series and monthly aggregates for chart rendering. |
| `GET` | `/api/v1/nasa/power` | Diagnostic inspector for cache hits and upstream NASA POWER status. |

### Query Parameters for `/api/v1/climate/summary`:
- `farm_id` (string, required): Stable farm identifier from Module 01.
- `latitude` (float, required): Decimal degrees `[-90.0, 90.0]`.
- `longitude` (float, required): Decimal degrees `[-180.0, 180.0]`.
- `start_date` (string, required): ISO `YYYY-MM-DD` (minimum `1981-01-01`).
- `end_date` (string, required): ISO `YYYY-MM-DD` (`>= start_date`).
- `parameters` (string, optional): Comma-separated parameter codes (e.g., `T2M,PRECTOTCORR,RH2M,ALLSKY_SFC_SW_DWN`).
- `include_daily` (boolean, optional, default `false`): Include full daily records list.
- `demo` (boolean, optional, default `false`): Force instant loading of Peshawar demo fixture.

---

## 3. Verified Parameter Catalog

| Code | Label | Unit | Aggregation Method | Underlying Dataset |
|:---|:---|:---|:---|:---|
| `T2M` | Temperature at 2 Meters | `°C` | `mean` (with min/max) | MERRA-2 / GEOS-5 FP-IT |
| `PRECTOTCORR` | Precipitation Corrected | `mm/day` | `sum` (cumulative mm/period) | MERRA-2 assimilation |
| `RH2M` | Relative Humidity at 2 Meters | `%` | `mean` | MERRA-2 / GEOS-5 derived |
| `ALLSKY_SFC_SW_DWN` | Solar Irradiance | `MJ/m²/day` | `mean` | CERES SYN1deg / FlashFlux |

---

## 4. Setup, Run & Test Instructions

### 4.1 Prerequisites
- Python 3.11+
- Virtual environment (`venv`)

### 4.2 Installation
```bash
# Clone and enter repo
git clone https://github.com/MTLab1122/AgroShift.git
cd AgroShift
git checkout feature/nasa-data

# Initialize virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt  # Or pip install -e .
```

### 4.3 Running the Local Development Server
```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```
Interactive Swagger API documentation is available at:
`http://localhost:8000/docs`

### 4.4 Running Test Suite
```bash
pytest -v
```

---

## 5. Sample Payloads

### Sample Success Request:
```http
GET /api/v1/climate/summary?farm_id=farm-peshawar-001&latitude=34.0151&longitude=71.5249&start_date=2024-05-01&end_date=2024-10-31&demo=true HTTP/1.1
Host: localhost:8000
```

### Sample Success Response (`ClimateSummary`):
```json
{
  "farm_id": "farm-peshawar-001",
  "source": "NASA POWER Daily API (Mock)",
  "product_or_dataset": "MERRA-2 / GEOS-5 FP-IT / CERES SYN1deg via POWER AG community",
  "latitude": 34.0151,
  "longitude": 71.5249,
  "start_date": "2024-05-01",
  "end_date": "2024-10-31",
  "parameters": [
    { "code": "T2M", "label": "Temperature at 2 Meters", "unit": "°C" },
    { "code": "PRECTOTCORR", "label": "Precipitation Corrected", "unit": "mm/day" },
    { "code": "RH2M", "label": "Relative Humidity at 2 Meters", "unit": "%" },
    { "code": "ALLSKY_SFC_SW_DWN", "label": "All Sky Surface Shortwave Downward Irradiance", "unit": "MJ/m^2/day" }
  ],
  "aggregates": {
    "monthly": [
      {
        "period": "2024-05",
        "aggregation_method": "mean for temperature/humidity/radiation, cumulative sum for precipitation",
        "total_days": 31,
        "valid_days": 31,
        "coverage_ratio": 1.0,
        "values": {
          "T2M": { "mean": 30.6, "sum": null, "min": 28.1, "max": 33.6, "unit": "°C" },
          "PRECTOTCORR": { "mean": 0.2, "sum": 7.0, "min": 0.0, "max": 3.5, "unit": "mm/period" }
        }
      }
    ],
    "seasonal": [
      {
        "season": "Kharif",
        "period": "2024-05 to 2024-10",
        "aggregation_method": "mean for temperature/humidity/radiation, cumulative sum for precipitation",
        "total_days": 184,
        "valid_days": 182,
        "coverage_ratio": 0.989,
        "values": {
          "T2M": { "mean": 28.9, "sum": null, "min": 17.5, "max": 38.4, "unit": "°C" },
          "PRECTOTCORR": { "mean": 1.2, "sum": 218.0, "min": 0.0, "max": 22.0, "unit": "mm/period" }
        }
      }
    ]
  },
  "missing_data": {
    "total_days": 184,
    "missing_days_by_parameter": {
      "T2M": 0,
      "PRECTOTCORR": 1,
      "RH2M": 2,
      "ALLSKY_SFC_SW_DWN": 0
    },
    "has_gaps": true,
    "notes": "Deliberate test gaps included: 2024-06-15 missing PRECTOTCORR & RH2M; 2024-08-20 missing RH2M. Verified sentinel -999 mapped to null."
  },
  "retrieved_at": "2026-11-13T17:30:00Z",
  "coverage_note": "Gridded NASA satellite and reanalysis data represents regional grid cells (~0.5° × 0.5° / ~50km × 50km resolution), not direct on-farm in-situ sensor measurements. Use for regional decision support and agro-climatic context.",
  "is_demo_data": true
}
```

### Sample Validation Error Response (`ApiError`):
```json
{
  "error_code": "INVALID_COORDINATES",
  "message": "Validation failed on field 'latitude': Value error, Latitude 999.0 is out of bounds. Must be between -90.0 and 90.0 decimal degrees (N/S).",
  "details": {
    "field": "latitude",
    "type": "value_error"
  },
  "request_id": "req-9af3f08f"
}
```

---

## 6. Scientific Limitations & Spatial Caveats

1. **Regional Spatial Resolution:** Gridded NASA reanalysis datasets (MERRA-2) provide values at ~0.5° × 0.5° grid cells (~50 km × 50 km). Grid cell averages represent regional meteorological trends and do not reflect microclimates, tree canopy cover, or localized irrigation spray.
2. **Assimilation Lag:** Near-Real-Time (NRT) assimilation data typically exhibits a 2 to 5-day lag. Requests for current-day data should anticipate potential latency.
3. **Decision-Support Scope:** All environmental metrics are intended for agricultural decision support, crop-rotation guidance, and climate risk screening—not guarantees of yield or precise in-situ soil moisture.
