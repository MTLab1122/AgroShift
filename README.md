# AgroShift — Climate-Resilient Agricultural Intelligence Platform

**NASA Space Apps Challenge 2026**  
**Team InCir (Innovation Circle), Abasyn University Peshawar**  
**Repository:** [https://github.com/MTLab1122/AgroShift.git](https://github.com/MTLab1122/AgroShift.git)

---

## 1. Project Overview

**AgroShift** is an open-source, decision-support platform designed to help smallholder farmers and agricultural advisors in climate-vulnerable regions (demonstrated in the Peshawar Valley, Khyber Pakhtunkhwa, Pakistan) adapt to shifting weather patterns.

By connecting farmer field context with real-time **NASA Earth Observation & Climate Data** (NASA POWER Agroclimatology, MERRA-2, and CERES), AgroShift produces transparent, evidence-grounded crop-rotation scenarios with complete scientific provenance, zero data fabrication, and deterministic agronomic scoring.

---

## 2. Team InCir & Module Ownership

AgroShift is architected as a modular monorepo developed collaboratively across 5 parallel feature streams:

| Module | Focus Area | Module Owner | Git Branch | Key Responsibilities |
|:---|:---|:---|:---|:---|
| **Module 01** | Farm Management & Location Intelligence | **Sana Jalal** | `feature/farm-module` | Farm registration, Leaflet map point picker, field characteristics (`FarmProfile`). |
| **Module 02** | NASA Earth Observation & Climate Engine | **Muhammad Talha** *(Team Lead)* | `feature/nasa-data` | NASA POWER Daily API, -999 sentinel handling, monthly/seasonal climate aggregates (`ClimateSummary`). |
| **Module 03** | Agro Intelligence & Crop Rotation Engine | **Hira Dawood** | `feature/agro-engine` | Peshawar Valley crop catalog, rotation rules, baseline/pulse/soil-cover scenarios (`RecommendationSet`). |
| **Module 04** | Analytics, Visualization & Reporting | **Aqsa Faisal** | `feature/analytics` | Interactive Recharts dashboard, PDF/CSV report exports, climate trend graphs. |
| **Module 05** | Integration, Security, QA & Deployment | **Sudais Ahmad** | `feature/integration` | Shared contracts (`shared/schemas/`), smart live-to-demo gateway, CI/CD, containerization. |

---

## 3. Monorepo Repository Structure

```text
AgroShift/
├── backend/
│   ├── app/
│   │   ├── core/                  # Module 05: Gateway, middleware, config, security
│   │   │   ├── middleware.py      # X-Request-ID, structured latency logging
│   │   │   └── gateway.py         # Smart Live-to-Demo Fallback Gateway
│   │   ├── modules/
│   │   │   ├── farm_management/   # Module 01: FarmProfile models and routes
│   │   │   ├── nasa_data/         # Module 02: NASA POWER client, normalizer, aggregates
│   │   │   ├── agro_intelligence/ # Module 03: Rotation engine & crop catalog
│   │   │   └── analytics/         # Module 04: Reporting & chart transforms
│   │   └── main.py                # FastAPI entry point & ApiError handlers
├── frontend/                      # Next.js 14, TypeScript, Tailwind CSS, Leaflet, Recharts
├── shared/
│   └── schemas/                   # Canonical JSON Schema contracts
│       ├── farm.schema.json
│       ├── climate.schema.json
│       ├── recommendation.schema.json
│       └── error.schema.json
├── data/
│   └── demo/                      # Verified demo fixtures with is_demo_data: true
│       └── climate.mock.json      # Peshawar Valley demo farm (34.0151, 71.5249)
├── docs/                          # Architecture, data sources, and integration checklists
│   └── data-sources.md
├── tests/                         # Pytest test suites across all 5 modules
├── docker-compose.yml             # Local and staging orchestration
├── pyproject.toml                 # Backend dependencies and test configuration
└── .env.example                   # Environment variable template
```

---

## 4. Quick Start & Local Setup

### 4.1 Prerequisites
- Python 3.11+
- Node.js 18+ (for frontend)
- Git

### 4.2 Clone & Environment
```bash
git clone https://github.com/MTLab1122/AgroShift.git
cd AgroShift

# Setup Python Virtual Environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install Backend Dependencies
pip install -e .
pip install fastapi httpx uvicorn pytest pytest-asyncio jsonschema

# Copy environment template
cp .env.example .env       # Windows: copy .env.example .env
```

### 4.3 Running Backend API
```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```
- Interactive Swagger UI: `http://localhost:8000/docs`
- Health Check & Readiness: `http://localhost:8000/api/v1/health`

### 4.4 Running Automated Verification Suite
```bash
pytest -v
```

---

## 5. Non-Negotiable Scientific Principles

1. **Zero Climate Fabrication:** Missing NASA satellite observations (marked with `-999.0` sentinel) are strictly converted to `null` (`None`). Missing precipitation is never converted to `0.0 mm` (which falsely implies dry weather).
2. **Provenance Disclosure:** Every climate metric includes data source attribution, underlying dataset (MERRA-2, CERES), retrieval timestamp, and an explicit spatial resolution caveat (~0.5° × 0.5° regional grid cells, not on-farm sensors).
3. **Demo Transparency:** Any synthetic fallback fixture carries `"is_demo_data": true` and sets HTTP header `X-AgroShift-Data-Mode: demo-fallback`.
4. **Decision Support, Not Agronomic Guarantees:** Recommendations provide transparent risk/benefit trade-offs and require local field verification.
