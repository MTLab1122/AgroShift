# Data Sources, Parameter Catalog & Scientific Provenance

**AgroShift — Module 02: NASA Earth Observation & Climate Data Engine**  
**Team InCir (Innovation Circle), Abasyn University Peshawar**  
**NASA Space Apps Challenge 2026**

---

## 1. Executive Summary & Module Mission

The mission of Module 02 is to retrieve, validate, normalize, and aggregate NASA Earth Observation and climate data for any registered farm location (`latitude`, `longitude`) over an arbitrary ISO date interval (`start_date`, `end_date` in `YYYY-MM-DD`). 

This document defines the primary live data source, exact parameter identifiers, physical units, assimilation models, temporal coverage, spatial resolution caveats, missing-data sentinel protocols, and the integration evaluation of stretch data sources (SMAP, GPM).

---

## 2. Primary Live Data Source: NASA POWER Daily API

### 2.1 Service Overview
- **Service Name:** NASA Prediction of Worldwide Energy Resources (POWER)
- **API Endpoint:** `https://power.larc.nasa.gov/api/temporal/daily/point`
- **Documentation:** [https://power.larc.nasa.gov/docs/services/api/temporal/daily/](https://power.larc.nasa.gov/docs/services/api/temporal/daily/)
- **Target Community:** Agroclimatology (`AG`)
- **Output Format:** JSON (`format=JSON`)
- **Temporal Resolution:** Daily (`temporal/daily`)
- **Spatial Subsetting:** Single Point (`point`) via Decimal Degree Coordinates

### 2.2 Standard Request Template
```http
GET https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M,PRECTOTCORR,RH2M,ALLSKY_SFC_SW_DWN&community=AG&longitude=71.5249&latitude=34.0151&start=20240501&end=20241031&format=JSON HTTP/1.1
Host: power.larc.nasa.gov
Accept: application/json
```

### 2.3 Query Parameter Specifications
| Parameter | Type | Required | Description & Constraints |
|:---|:---|:---|:---|
| `community` | string | Yes | Must be `AG` (Agroclimatology community, providing agricultural units). |
| `parameters` | string | Yes | Comma-delimited list of verified parameter codes (e.g., `T2M,PRECTOTCORR,RH2M,ALLSKY_SFC_SW_DWN`). |
| `latitude` | float | Yes | Decimal degrees north/south: `[-90.0, 90.0]`. **Never swap with longitude.** |
| `longitude` | float | Yes | Decimal degrees east/west: `[-180.0, 180.0]`. |
| `start` | string | Yes | Start date in `YYYYMMDD` format (minimum: `19810101`). |
| `end` | string | Yes | End date in `YYYYMMDD` format (must be `>= start` and within archive coverage). |
| `format` | string | Yes | Must be `JSON`. |

---

## 3. Verified Parameter Catalog

| Parameter Code | Full Description | Official Unit | Primary Underlying Dataset / Sensor | Downstream Agronomic Role |
|:---|:---|:---|:---|:---|
| `T2M` | Temperature at 2 Meters | `°C` | MERRA-2 (Global Modeling and Assimilation Office - GMAO) / GEOS-5 FP-IT | Thermal stress, Growing Degree Days (GDD), crop suitability windows. |
| `PRECTOTCORR` | Precipitation Corrected | `mm/day` | MERRA-2 bias-corrected reanalysis precipitation | Crop water balance, soil moisture recharge, drought risk indexing. |
| `RH2M` | Relative Humidity at 2 Meters | `%` | MERRA-2 / GEOS-5 (derived from 2m specific humidity & temperature) | Evaporative demand, pest & fungal pathogen incubation pressure. |
| `ALLSKY_SFC_SW_DWN` | All Sky Surface Shortwave Downward Irradiance | `MJ/m²/day` | CERES SYN1deg / FlashFlux / MERRA-2 solar assimilation | Photosynthetic active radiation (PAR), canopy energy balance, solar drying. |
| `T2M_MIN` *(Aux)* | Minimum Temperature at 2 Meters | `°C` | MERRA-2 / GEOS-5 FP-IT daily minimum | Frost risk assessment for winter/Rabi transition crops. |
| `T2M_MAX` *(Aux)* | Maximum Temperature at 2 Meters | `°C` | MERRA-2 / GEOS-5 FP-IT daily maximum | Heat stress thresholds during pollination/flowering. |

---

## 4. Scientific Integrity, Missing Data & Sentinel Values

### 4.1 Missing-Data Sentinel Protocol
- **NASA POWER Convention:** The NASA POWER API returns `-999.0` (or `-999`) for dates, hours, or locations where observational or assimilation data is missing, corrupted, or unavailable.
- **Strict Transformation Rule:** Every occurrence of `-999.0` MUST be converted strictly to `null` (`None` in Python).
- **Zero Fabrication Principle:**
  - **Never replace missing precipitation with `0.0 mm`** (which falsely implies dry weather).
  - **Never replace missing temperature with `0.0 °C`** (which falsely implies freezing conditions).
  - **Never interpolate synthetic numbers without explicit caller opt-in and audit logging.**
- **Missing Data Bookkeeping:**
  All normalized responses produce a `MissingDataSummary` reporting:
  - Total elapsed calendar days.
  - Count of missing days per parameter.
  - Boolean `has_gaps`.
  - Explanatory audit notes.

---

## 5. Spatial Resolution & Provenance Disclosure

### 5.1 Grid Cell Resolution Caveats
NASA POWER provides meteorological variables derived from NASA's Modern-Era Retrospective analysis for Research and Applications, Version 2 (**MERRA-2**) and the GEOS atmospheric assimilation system, combined with **CERES** satellite solar data:
- **Spatial Resolution:** Approximately **0.5° latitude × 0.5° longitude** (~50 km × 50 km at mid-latitudes). Solar radiation is provided on a **1.0° × 1.0°** CERES grid.
- **Gridded vs. In-Situ Measurement:** The data represents spatial averages over large grid cells. It does NOT capture microclimates created by local tree canopy cover, localized valley drainage, or specific farm soil beds.
- **Mandatory Coverage Note:**
  Every response emitted by Module 02 carries the following explicit statement:
  > *"Gridded NASA satellite and reanalysis data represents regional grid cells (~0.5° × 0.5° / ~50km × 50km resolution), not direct on-farm in-situ sensor measurements. Use for regional decision support and agro-climatic context."*

### 5.2 Temporal Coverage & Update Latency
- **Historical Archive:** Continuous daily records available from **January 1, 1981** onwards.
- **Near-Real-Time (NRT) Latency:** MERRA-2 and FP-IT assimilation data has a latency of approximately **2 to 5 days** behind real-time. Requests for today's date will not have completed daily records and must be validated before upstream calls.

---

## 6. Evaluation of Stretch Data Sources

During initial architecture planning, SMAP and GPM were identified as candidate stretch datasets. Following rigorous evaluation against hackathon delivery constraints and API stability criteria, their status is documented below:

### 6.1 NASA SMAP (Soil Moisture Active Passive)
- **Product:** L3/L4 Surface and Root-Zone Soil Moisture (e.g., SPL4SMAU).
- **Access Protocol:** NASA Earthdata Login (OAuth2 Bearer Tokens), NASA CMR API / OPeNDAP / Harmony subsetting services.
- **Spatial Resolution:** 9 km (Level 4 assimilations) or 36 km (Level 3 radiometer).
- **Status for MVP:** **Deferred (Stretch Goal Only).** Access requires mandatory Earthdata credentials, binary HDF5/NetCDF file handling, and irregular orbit revisit cycles (2–3 days). To ensure the hackathon MVP remains robust, deterministic, and dependency-light, SMAP integration will be evaluated only as an optional post-MVP enhancement.

### 6.2 NASA GPM IMERG (Global Precipitation Measurement)
- **Product:** IMERG Early/Late/Final Run (0.1° × 0.1° gridded precipitation).
- **Access Protocol:** NASA GES DISC with Earthdata credentials.
- **Status for MVP:** **Deferred (Stretch Goal Only).** While IMERG provides finer spatial resolution than MERRA-2, NASA POWER's `PRECTOTCORR` parameter already incorporates calibrated multi-source precipitation estimates without requiring NASA Earthdata OAuth2 complexity or custom HDF5 processing.

---

## 7. Demo Farm Reference Coordinates

For local testing, validation, and the hackathon demonstration, the following agreed farm profile is used:
- **Farm Identifier:** `farm-peshawar-001`
- **Location:** Peshawar Valley, Khyber Pakhtunkhwa, Pakistan
- **Coordinates:** `Latitude: 34.0151° N`, `Longitude: 71.5249° E`
- **Agro-Ecological Context:** Irrigated alluvial plains of Khyber Pakhtunkhwa; primary seasons are Kharif (summer: maize, rice, sugarcane, pulses) and Rabi (winter: wheat, mustard, chickpea).
- **Demo Fixture Location:** `data/demo/climate.mock.json`
