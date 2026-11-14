# AgroShift — Adapting Farms with NASA Earth Observations

**NASA Space Apps Challenge 2026: Adapting Farms with NASA Data**  
**Challenge Resources:** [Adapting Farms with NASA Data (Challenge Resources)](https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/?tab=resources)  
**Team InCir (Innovation Circle), Abasyn University Peshawar, Pakistan**  
**Repository:** [https://github.com/MTLab1122/AgroShift.git](https://github.com/MTLab1122/AgroShift.git)

---

## 1. Executive Summary & Objective

**AgroShift** is an open-source, decision-support platform engineered to help smallholder farmers and agricultural advisors in climate-vulnerable regions (demonstrated in the Peshawar Valley, Khyber Pakhtunkhwa, Pakistan) adapt to volatile temperature swings, erratic precipitation, and declining soil fertility.

Whenever a farmer inputs their parcel parameters (coordinates, soil type, irrigation type, water availability, current crop, and crop history), the AgroShift engine:
1. **Retrieves Live NASA Earth Observations:** Connects directly to the **NASA POWER Daily API** (Agroclimatology `AG` community, MERRA-2, and CERES reanalysis at ~0.5° × 0.5° resolution) alongside NASA SMAP L4 and GPM IMERG data hooks.
2. **Performs Farm vs. NASA Reconciliation:** Directly compares user crop requirements against observed NASA environmental data (precipitation, thermal heat-stress days, and water balance).
3. **Generates Grounded Crop-Rotation Recommendations:** Dynamically scores and ranks 3 canonical crop rotation pathways:
   - **Baseline Scenario:** Current conventional cereal practice.
   - **Pulse-Inclusive Scenario:** Nitrogen-fixing, low-water legume rotation (`chickpea`, `lentil`, `mung_bean`) slashing water demand by up to 35% and fixing 45–75 kg N/ha.
   - **Soil-Cover / Climate-Resilient Scenario:** High-biomass cover and multi-cut forage (`berseem_clover`, `mustard`) restoring soil organic matter and mitigating erosion.

---

## 2. Non-Negotiable Scientific & Architecture Principles

- **Zero Data Fabrication:** Missing observations (`-999.0` sentinels) are strictly mapped to `null` (`None` in Python). AgroShift never invents or synthesizes fake climate numbers.
- **Spatial Resolution & Provenance Transparency:** Every climate response and UI screen carries a prominent disclaimer informing users that gridded satellite/reanalysis data represents regional grid cells (~50 km × 50 km), not on-farm in-situ sensors.
- **Smart Gateway & Demo Transparency:** All mock demo fallbacks carry explicit `"is_demo_data": true` metadata and an `X-AgroShift-Data-Mode` HTTP response header.
- **Decision-Support Framing:** Recommendations provide algorithmic guidance and explicitly disclaim guaranteed yields, recommending local agronomist verification prior to planting.

---

## 3. Team InCir & Module Architecture

AgroShift is architected as a modular monorepo developed collaboratively across 5 parallel feature streams:

| Module | Focus Area | Module Owner | Git Branch | Key Responsibilities |
|:---|:---|:---|:---|:---|
| **Module 01** | Farm Management & Location Intelligence | **Sana Jalal** | `feature/farm-module` | Parcel registration, coordinate capture, field characteristics (`FarmProfile`). |
| **Module 02** | NASA Earth Observation & Climate Engine | **Muhammad Talha** *(Team Lead)* | `feature/nasa-data` | NASA POWER Daily API client, normalizer, monthly/seasonal aggregations, in-memory TTL caching (`ClimateSummary`). |
| **Module 03** | Agro Intelligence & Crop Rotation Engine | **Hira Dawood** | `feature/agro-engine` | Peshawar Valley crop catalog, farm-vs-NASA comparator, explainable scoring ($S = 0.35C + 0.25W + 0.25D + 0.15P$) (`RecommendationSet`). |
| **Module 04** | Analytics, Visualization & Reporting | **Aqsa Faisal** | `feature/analytics` | Comparative scenario visualization, factor breakdown radar, climate history charting. |
| **Module 05** | Integration, Security, QA & Deployment | **Sudais Ahmad** | `feature/integration` | Canonical contracts (`shared/schemas/`), request-tracing middleware, resilient live-to-demo gateway, end-to-end acceptance tests. |

---

## 4. NASA Datasets & Technical Specifications

| Dataset | Provider / Source | Spatial Resolution | Temporal Coverage | Parameters Utilized | Role in AgroShift |
|:---|:---|:---|:---|:---|:---|
| **NASA POWER Daily API** | NASA Langley Research Center (LARC) | ~0.5° × 0.5° (~50 km) | 1981–Present | `T2M`, `T2M_MAX`, `T2M_MIN`, `PRECTOTCORR`, `RH2M`, `ALLSKY_SFC_SW_DWN` | Primary live environmental driver: temperature, precipitation, humidity, solar radiation, heat stress. |
| **NASA SMAP L4** | NASA GSFC / NSIDC DAAC | ~9 km global grid | 2015–Present | `soil_moisture_surface`, `soil_moisture_rootzone` | Surface and root-zone moisture validation. |
| **NASA GPM IMERG** | NASA GSFC / GES DISC | ~0.1° × 0.1° (~10 km) | 2000–Present | `precipitationCal` | Multi-satellite precipitation estimation and extreme flood event detection. |

---

## 5. Recommendation Scoring Formula

Crop rotation scenarios are evaluated dynamically using a multi-criteria agronomic decision function:

$$S = W_1 \cdot C + W_2 \cdot W + W_3 \cdot D + W_4 \cdot P$$

Where:
- $W_1 = 0.35$: **Climate Suitability ($C$):** Cross-compares observed NASA temperature ($T_{2M}$) and Growing Degree Days against crop physiological thresholds.
- $W_2 = 0.25$: **Water Efficiency ($W$):** Evaluates moisture deficit based on NASA precipitation (`PRECTOTCORR`) and reported irrigation delivery.
- $W_3 = 0.25$: **Soil Health & Nitrogen Benefit ($D$):** Rewards biological nitrogen fixation (e.g. 75 kg N/ha for chickpea, 140 kg N/ha for berseem) and penalizes cereal monoculture repetition.
- $W_4 = 0.15$: **Market & Economic Resilience ($P$):** Gauges local market off-take risk and input cost mitigation.

---

## 6. Monorepo Directory Structure

```text
AgroShift/
├── backend/
│   ├── app/
│   │   ├── core/                  # Middleware, NASA config, Smart Fallback Gateway
│   │   │   ├── middleware.py      # X-Request-ID, latency tracking
│   │   │   ├── nasa_config.py     # Challenge dataset registry & endpoints
│   │   │   └── gateway.py         # Live-to-demo fallback resilience
│   │   ├── modules/
│   │   │   ├── nasa_data/         # Module 02: NASA POWER client, normalizer, caching
│   │   │   └── agro_engine/       # Module 03: Crop catalog, comparator, recommendation engine
│   │   ├── schemas/               # Canonical Pydantic v2 schemas
│   │   │   ├── comparison.py      # FarmVsNasaComparison
│   │   │   ├── farm.py            # FarmProfile, CropHistoryEntry
│   │   │   └── recommendation.py  # RecommendationSet, ScenarioCatalog
│   │   └── main.py                # FastAPI entry point & exception handlers
├── frontend/                      # React 18, Vite, Lucide Icons, Glassmorphism UI
│   ├── src/
│   │   ├── components/            # Header, FarmForm, NasaComparisonCard, RecommendationScenarios
│   │   ├── App.jsx
│   │   └── index.css
│   └── vite.config.js
├── shared/
│   └── schemas/                   # Shared JSON Schema contracts
│       ├── farm.schema.json
│       ├── climate.schema.json
│       ├── recommendation.schema.json
│       └── error.schema.json
├── data/
│   └── demo/                      # Verified demo fixtures (Peshawar Valley farm)
├── docs/                          # Data source documentation and challenge resources
│   └── data-sources.md
├── scripts/                       # Live verification probes and terminal demos
│   ├── live_peshawar_probe.py
│   └── live_phase3_comparison_demo.py
├── tests/                         # 74 automated pytest integration & verification tests
├── pyproject.toml
└── README.md
```

---

## 7. Quick Start & Execution Guide

### 7.1 Backend Setup
```powershell
# 1. Activate virtual environment
.\.venv\Scripts\activate

# 2. Start FastAPI development server
uvicorn backend.app.main:app --reload --port 8000
```
- Swagger UI Documentation: `http://localhost:8000/docs`
- Health Diagnostics: `http://localhost:8000/api/v1/health`

### 7.2 Frontend Setup
```powershell
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` to interact with the mission control UI.

### 7.3 Running Live Terminal Probes
```powershell
# Probe 1: Live NASA POWER retrieval for Peshawar Valley (34.0151, 71.5249)
python scripts/live_peshawar_probe.py

# Probe 2: Live Farm vs. NASA comparison demonstration
python scripts/live_phase3_comparison_demo.py
```

### 7.4 Running Automated Test Suite
```powershell
pytest -v
# 74 passed in ~20s (100% pass rate)
```

---

## 8. Verified API Endpoints

- `GET /health` & `GET /api/v1/health`: System diagnostics and module readiness report.
- `GET /api/v1/climate/summary`: Normalized NASA POWER climate summary with aggregates.
- `GET /api/v1/climate/history`: Daily time-series and monthly aggregates for visualization.
- `GET /api/v1/nasa/power`: Diagnostic cache inspector and raw NASA payload preview.
- `POST /api/v1/recommendations/generate`: Unified pipeline taking `FarmProfile`, fetching live NASA data, reconciling moisture/temperature, and producing `RecommendationSet`.
- `POST /api/v1/analyze-farm`: Comprehensive farm analysis alias.

---

## 9. License & Attribution

Developed by **Team InCir (Innovation Circle)** at **Abasyn University Peshawar** for the **NASA Space Apps Challenge 2026**. Open source under the MIT License. NASA Earth observations courtesy of the NASA POWER Project and NASA Earth Science Data and Information System (ESDIS).
