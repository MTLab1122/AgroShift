# Database Integration & Deployment Guide (Module 01)

**AgroShift — Farm Management & Location Intelligence**
**Module 01: Persistent Storage & Relational Database Architecture**

---

## 1. Overview
Module 01 provides relational database persistence for registered agricultural farm parcels, geographic boundaries (GeoJSON polygons), location centroids, and seasonal crop history records.

The architecture uses **SQLAlchemy 2.x** with migration management powered by **Alembic**.

> **Verification status:** SQLite is the verified local database path. PostgreSQL URL and
> driver configuration are present, but integration against a PostgreSQL server has not
> been verified.

---

## 2. Database Engine Support

### 2.1 Production: PostgreSQL
- **Recommended Driver:** `psycopg` (Version 3 binary driver).
- **Connection URL Format:**
  ```env
  DATABASE_URL=postgresql+psycopg://username:password@localhost:5432/agroshift_db
  ```
- **Connection Pooling:**
  - `DB_POOL_SIZE`: Default `10`
  - `DB_MAX_OVERFLOW`: Default `20`
  - `DB_POOL_TIMEOUT`: Default `30.0`
  - `pool_pre_ping=True`: Active connection verification to guard against stale sockets.

### 2.2 Local Development / Testing: SQLite
- If `DATABASE_URL` is omitted, the backend automatically connects to:
  ```
  sqlite:///./data/agroshift.db
  ```
- The schema is provisioned with Alembic; run the migration command below before
  using farm-management endpoints against a new database.

---

## 3. Database Schema & Tables

### 3.1 `farms` Table
| Column | Type | Constraints / Description |
|:---|:---|:---|
| `farm_id` | `VARCHAR(64)` | Primary Key, Indexed |
| `name` | `VARCHAR(128)` | Not Null, Indexed |
| `owner_name` | `VARCHAR(128)` | Not Null |
| `contact_phone` | `VARCHAR(32)` | Not Null |
| `preferred_language` | `VARCHAR(8)` | Default `'en'` |
| `latitude` | `FLOAT` | Centroid Latitude (`[-90.0, 90.0]`) |
| `longitude` | `FLOAT` | Centroid Longitude (`[-180.0, 180.0]`) |
| `elevation_meters` | `FLOAT` | Optional elevation ASL |
| `village_or_town` | `VARCHAR(128)` | Optional village/mouza |
| `district` | `VARCHAR(64)` | Indexed administrative district |
| `province_or_region` | `VARCHAR(64)` | Administrative province |
| `country` | `VARCHAR(64)` | Default `'Pakistan'` |
| `boundary_geojson` | `TEXT` | Serialized GeoJSON Polygon/MultiPolygon |
| `total_area_hectares` | `FLOAT` | Not Null, `> 0.0` |
| `soil_type` | `VARCHAR(32)` | Indexed soil classification |
| `irrigation_source` | `VARCHAR(32)` | Canal, tube well, river lift, etc. |
| `water_availability` | `VARCHAR(32)` | Adequate, deficit, etc. |
| `salinity_level` | `VARCHAR(32)` | Optional approved salinity level |
| `current_crops_json` | `TEXT` | Standing crops array |
| `created_at` | `VARCHAR(64)` | ISO 8601 UTC timestamp |
| `updated_at` | `VARCHAR(64)` | ISO 8601 UTC timestamp |

*Composite Indexes:*
- `idx_farm_coords`: `(latitude, longitude)`
- `idx_farm_district_prov`: `(district, province_or_region)`

### 3.2 `crop_history` Table
| Column | Type | Constraints / Description |
|:---|:---|:---|
| `record_id` | `VARCHAR(64)` | Primary Key, Indexed |
| `farm_id` | `VARCHAR(64)` | Foreign Key (`farms.farm_id`, `ON DELETE CASCADE`), Indexed |
| `crop_name` | `VARCHAR(64)` | Not Null, Indexed |
| `variety` | `VARCHAR(64)` | Cultivar / Variety |
| `season` | `VARCHAR(32)` | Indexed (`Kharif`, `Rabi`, `Zaid`, etc.) |
| `year` | `INTEGER` | Indexed planting year (`1980–2100`) |
| `sowing_date` | `VARCHAR(32)` | ISO date |
| `harvest_date` | `VARCHAR(32)` | ISO date |
| `area_planted_hectares` | `FLOAT` | Planted hectares |
| `yield_amount_kg` | `FLOAT` | Harvested yield in kg |
| `status` | `VARCHAR(32)` | `planned`, `sown`, `growing`, `harvested`, `failed` |
| `notes` | `TEXT` | Agronomic observations |
| `created_at` | `VARCHAR(64)` | ISO 8601 UTC timestamp |

*Composite Indexes:*
- `idx_crop_farm_season_year`: `(farm_id, season, year)`

---

## 4. Setup & Migration Instructions

### 4.1 Prerequisites for PostgreSQL
If running with a dedicated PostgreSQL server:
```bash
# 1. Create the database in psql:
CREATE DATABASE agroshift_db;
CREATE USER agroshift_user WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE agroshift_db TO agroshift_user;
```

### 4.2 Set Environment Variable
```powershell
$env:DATABASE_URL="postgresql+psycopg://agroshift_user:secure_password_here@localhost:5432/agroshift_db"
```

The frontend defaults to `http://localhost:8000` for the backend. To point it elsewhere,
set `NEXT_PUBLIC_API_BASE_URL` in the frontend's `.env.local` file before starting Next.js.

### 4.3 Run Alembic Migrations
```powershell
# Apply latest schema migrations to head:
python -m alembic -c alembic.ini upgrade head

# WARNING: downgrade drops farm and crop data; use only with a disposable database:
python -m alembic -c alembic.ini downgrade base

# Generate a new migration revision (if models change):
python -m alembic -c alembic.ini revision --autogenerate -m "migration_description"
```

---

## 5. Startup Commands

### Start Backend (FastAPI + Uvicorn)
```powershell
$env:PYTHONPATH="."
# Run once for a new database, and after each schema migration:
python -m alembic -c alembic.ini upgrade head
python -m uvicorn backend.app.main:app --reload --port 8000
```
- Interactive API Docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### Start Frontend (Next.js)
```powershell
cd frontend
npm run dev
```
- Dashboard: `http://localhost:3000/farms`
