# Data Sources, Parameter Catalog & Scientific Provenance

**AgroShift — Module 02 & Module 03: NASA Earth Observation & Comparison Engine**  
**NASA Space Apps Challenge 2026: Adapting Farms with NASA Data**  
**Challenge Resources Reference:** [https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/?tab=resources](https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/?tab=resources)  
**Team InCir (Innovation Circle), Abasyn University Peshawar**

---

## 1. Challenge Alignment & Mission

AgroShift directly addresses the **NASA Space Apps Challenge 2026: Adapting Farms with NASA Data** by leveraging NASA Earth observation assets to help farmers transition toward climate-resilient practices.

The system connects user-submitted farm details (`latitude`, `longitude`, `start_date`, `end_date`, `soil_type`, `irrigation_type`, `water_availability`, `current_crop`, `crop_history`) to live NASA data. It then conducts an objective **Farm-Input vs. Live NASA Observation Comparison** to generate transparent, explainable crop-rotation recommendations.

---

## 2. Authorized NASA Challenge Datasets

### 2.1 Primary Live Source: NASA POWER Daily Agroclimatology API
- **Agency / Facility:** NASA Langley Research Center (LaRC)
- **API Endpoint:** `https://power.larc.nasa.gov/api/temporal/daily/point`
- **Agroclimatology Community:** `AG` (agricultural units)
- **Authentication:** Public open-access (NO API key required)
- **Underlying Assimilation Models:**
  - Modern-Era Retrospective analysis for Research and Applications, Version 2 (**MERRA-2**)
  - Goddard Earth Observing System Forward Processing for Instrument Teams (**GEOS-5 FP-IT**)
  - Clouds and the Earth's Radiant Energy System (**CERES SYN1deg**)
- **Spatial Resolution:** ~0.5° × 0.5° latitude/longitude grid cells (~50 km × 50 km).
- **Temporal Resolution:** Continuous daily records from January 1, 1981 to near-present (2–5 day processing latency).

#### Parameter Catalog
| Code | Parameter Label | Official Unit | Scientific Role |
|:---|:---|:---|:---|
| `T2M` | Temperature at 2 Meters | `°C` | Daily mean thermal tracking, crop development baseline. |
| `T2M_MAX` | Maximum Temperature at 2 Meters | `°C` | Pollination heat stress, canopy scorch threshold audit. |
| `T2M_MIN` | Minimum Temperature at 2 Meters | `°C` | Frost hazard identification during Rabi transition. |
| `PRECTOTCORR` | Precipitation Corrected | `mm/day` | Actual observed moisture input vs. crop water need. |
| `RH2M` | Relative Humidity at 2 Meters | `%` | Atmospheric moisture demand, fungal disease risk screening. |
| `ALLSKY_SFC_SW_DWN` | Solar Irradiance | `MJ/m²/day` | Canopy radiation absorption, photosynthetic potential. |

### 2.2 Secondary Earth Observation Hooks

#### NASA SMAP (Soil Moisture Active Passive) L4
- **Product:** SPL4SMGP (Global 9 km Surface & Root-Zone Soil Moisture)
- **Spatial Resolution:** 9 km EASE-Grid 2.0
- **Access Protocol:** NASA Earthdata Login (CMR Granule API with Bearer token)
- **Role in AgroShift:** Secondary ground-truth layer for root-zone moisture availability to validate farmer-reported irrigation adequacy.
- **Status:** Integrated via adapter hook (`earthdata_adapters.py`). When `NASA_EARTHDATA_TOKEN` is unset, the system explicitly reports `"unavailable - token not configured"` without inventing synthetic measurements.

#### NASA GPM IMERG (Global Precipitation Measurement)
- **Product:** GPM_3IMERGDF (Daily Calibrated Precipitation at 0.1° × 0.1°)
- **Spatial Resolution:** 0.1° × 0.1° (~10 km × 10 km)
- **Access Protocol:** NASA GES DISC with Earthdata credentials
- **Role in AgroShift:** Finer-scale precipitation benchmarking for localized heavy rainfall/monsoon events.
- **Status:** Integrated via modular adapter hook.

---

## 3. Farm-Input vs. NASA Comparison Methodology

When a farm profile is analyzed against NASA observations, the backend computes a structured `FarmVsNasaComparison`:

1. **Observed Rainfall vs. Crop Water Need:**
   - Aggregates live NASA `PRECTOTCORR` over the analysis window ($R_{\text{obs}}$ in mm).
   - Looks up the crop's physiological seasonal water requirement ($W_{\text{need}}$ in mm) from the agronomic catalog.
   - Categorizes **Water Balance Status**:
     - `severe_deficit`: $R_{\text{obs}} < 0.4 \times W_{\text{need}}$ (rainfed farms face severe drought stress).
     - `moderate_deficit`: $0.4 \times W_{\text{need}} \le R_{\text{obs}} < 0.8 \times W_{\text{need}}$.
     - `balanced`: $0.8 \times W_{\text{need}} \le R_{\text{obs}} \le 1.3 \times W_{\text{need}}$.
     - `excess_moisture`: $R_{\text{obs}} > 1.3 \times W_{\text{need}}$ (waterlogging / flood risk).

2. **Irrigation Adequacy Audit:**
   - Reconciles farmer's declared `irrigation_type` (e.g. `canal`, `tube_well`, `rain_fed`) and `water_availability` (`low`, `medium`, `high`) with observed NASA rainfall deficit.
   - For example, if rainfall is severely deficient but farmer has `canal` with `high` availability, irrigation buffer is confirmed. If `rain_fed`, high drought vulnerability is flagged.

3. **Thermal Stress Days:**
   - Tallies days where live NASA `T2M_MAX` exceeds crop heat threshold (e.g., $>35^\circ\text{C}$ for wheat anthesis, $>42^\circ\text{C}$ for maize), or `T2M_MIN` falls below frost threshold ($<2^\circ\text{C}$).

---

## 4. Scientific Honesty & Missing Data Rules

- **Strict Sentinel Conversion:** NASA POWER uses `-999.0` for missing or corrupted observations. All `-999.0` values are mapped strictly to `null` (`None`).
- **Zero Fabrication:** Unobserved days remain `null`. The system **never** replaces missing precipitation with `0.0 mm` or missing temperature with `0.0 °C`.
- **Spatial Caveats:** All responses and exports explicitly carry the regional resolution note:
  > *"Gridded NASA satellite and reanalysis data represents regional grid cells (~0.5° × 0.5° / ~50km × 50km resolution), not direct on-farm in-situ sensor measurements. Use for regional decision support and agro-climatic context."*
- **Demo Data Transparency:** Fallback synthetic fixtures (`data/demo/*.json`) are tagged with `"is_demo_data": true` and surface the HTTP header `X-AgroShift-Data-Mode: demo-fallback`.
