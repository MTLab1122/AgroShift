/**
 * Climate and Earth Observation Types
 * Synchronized with shared/schemas/climate.schema.json (Module 02)
 */

export interface ParameterMetadata {
  code: "T2M" | "T2M_MIN" | "T2M_MAX" | "PRECTOTCORR" | "RH2M" | "ALLSKY_SFC_SW_DWN";
  label: string;
  unit: string;
}

export interface DailyRecord {
  date: string;
  values: Record<string, number | null>;
}

export interface MonthlyAggregate {
  period: string;
  aggregation_method: string;
  total_days: number;
  valid_days: number;
  coverage_ratio?: number;
  values: Record<string, {
    mean?: number | null;
    sum?: number | null;
    min?: number | null;
    max?: number | null;
    unit?: string;
  }>;
}

export interface SeasonalAggregate {
  season: string;
  period: string;
  aggregation_method: string;
  total_days: number;
  valid_days: number;
  coverage_ratio?: number;
  values: Record<string, {
    mean?: number | null;
    sum?: number | null;
    min?: number | null;
    max?: number | null;
    unit?: string;
  }>;
}

export interface AggregatesSummary {
  monthly: MonthlyAggregate[];
  seasonal: SeasonalAggregate[];
}

export interface MissingDataSummary {
  total_days: number;
  missing_days_by_parameter: Record<string, number>;
  has_gaps: boolean;
  notes?: string;
}

export interface ClimateSummary {
  farm_id: string;
  source: string;
  product_or_dataset: string;
  latitude: number;
  longitude: number;
  start_date: string;
  end_date: string;
  parameters: ParameterMetadata[];
  daily_series?: DailyRecord[] | null;
  aggregates: AggregatesSummary;
  missing_data: MissingDataSummary;
  retrieved_at: string;
  coverage_note: string;
  is_demo_data: boolean;
}
