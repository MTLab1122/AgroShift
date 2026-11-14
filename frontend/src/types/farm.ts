/**
 * AgroShift TypeScript Definitions
 * Derived from canonical shared JSON schemas:
 * - shared/schemas/farm.schema.json
 * - shared/schemas/crop.schema.json
 * - shared/schemas/climate.schema.json
 */

export type SupportedLanguage = "en" | "ur" | "ps";

export type SoilType =
  | "alluvial_clay"
  | "sandy_loam"
  | "clay_loam"
  | "silt_loam"
  | "sandy"
  | "peat"
  | "other";

export type IrrigationSource =
  | "canal"
  | "tube_well"
  | "drip"
  | "sprinkler"
  | "rainfed"
  | "river_lift"
  | "other";

export interface FarmLocation {
  latitude: number;
  longitude: number;
  elevation_meters?: number | null;
  village_or_town?: string;
  district: string;
  province_or_region: string;
  country: string;
}

export interface FarmBoundary {
  type: "Polygon" | "MultiPolygon";
  coordinates: number[][][] | number[][][][];
}

export interface FarmProfile {
  farm_id: string;
  name: string;
  owner_name: string;
  contact_phone: string;
  preferred_language: SupportedLanguage;
  location: FarmLocation;
  boundary?: FarmBoundary;
  total_area_hectares: number;
  soil_type: SoilType;
  irrigation_source: IrrigationSource;
  water_availability?: string | null;
  salinity_level?: string | null;
  current_crops: string[];
  created_at: string;
  updated_at: string;
}

export type CropSeason =
  | "Kharif"
  | "Rabi"
  | "Zaid"
  | "Spring"
  | "Autumn"
  | "Perennial"
  | "Other";

export type CropStatus = "planned" | "sown" | "growing" | "harvested" | "failed";

export interface CropHistoryRecord {
  record_id: string;
  farm_id: string;
  crop_name: string;
  variety?: string;
  season: CropSeason;
  year: number;
  sowing_date?: string | null;
  harvest_date?: string | null;
  area_planted_hectares?: number | null;
  yield_amount_kg?: number | null;
  status: CropStatus;
  notes?: string;
  created_at?: string;
}
