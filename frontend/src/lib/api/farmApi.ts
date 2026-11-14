/**
 * Module 01 API client with a clearly identified browser-local demo fallback.
 */

import { FarmProfile, CropHistoryRecord, SupportedLanguage } from "@/types/farm";
import { DEMO_FARMS, DEMO_CROPS } from "@/lib/demoData";

const FARMS_STORAGE_KEY = "agroshift_farms_v1";
const CROPS_STORAGE_KEY = "agroshift_crops_v1";
const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(
  /\/$/,
  ""
);

export interface ApiResponse<T> {
  data: T;
  source: "backend" | "local_demo_store";
  isDemoData: boolean;
  message?: string;
}

export interface AssistantChatResponse {
  session_id: string;
  reply_message: string;
  language: SupportedLanguage;
  extracted_farm: Partial<FarmProfile>;
  missing_fields: string[];
  is_ready_for_confirmation: boolean;
}

export class BackendUnavailableError extends Error {
  constructor(message: string) {
    super(`Backend is unavailable: ${message}`);
    this.name = "BackendUnavailableError";
  }
}

export class FarmApiError extends Error {
  constructor(
    message: string,
    public readonly status: number
  ) {
    super(message);
    this.name = "FarmApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, init);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Network request failed.";
    throw new BackendUnavailableError(message);
  }

  if (!response.ok) {
    const responseText = await response.text();
    let message = responseText || `Request failed with status ${response.status}.`;
    if (responseText) {
      try {
        const body: unknown = JSON.parse(responseText);
        if (typeof body === "object" && body !== null) {
          const errorBody = body as { message?: unknown; detail?: unknown };
          if (typeof errorBody.message === "string") {
            message = errorBody.message;
          } else if (typeof errorBody.detail === "string") {
            message = errorBody.detail;
          }
        }
      } catch {
        // Keep the response text when the server does not return JSON.
      }
    }
    throw new FarmApiError(message, response.status);
  }

  return (await response.json()) as T;
}

function readLocalFarms(): FarmProfile[] {
  if (typeof window === "undefined") return [...DEMO_FARMS];
  const stored = localStorage.getItem(FARMS_STORAGE_KEY);
  if (!stored) {
    localStorage.setItem(FARMS_STORAGE_KEY, JSON.stringify(DEMO_FARMS));
    return [...DEMO_FARMS];
  }

  const farms: unknown = JSON.parse(stored);
  if (!Array.isArray(farms)) {
    throw new Error("Saved local farm data is not a list. Clear or restore browser storage to continue.");
  }
  return farms as FarmProfile[];
}

function writeLocalFarms(farms: FarmProfile[]): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(FARMS_STORAGE_KEY, JSON.stringify(farms));
  }
}

function readLocalCrops(): CropHistoryRecord[] {
  if (typeof window === "undefined") return [...DEMO_CROPS];
  const stored = localStorage.getItem(CROPS_STORAGE_KEY);
  if (!stored) {
    localStorage.setItem(CROPS_STORAGE_KEY, JSON.stringify(DEMO_CROPS));
    return [...DEMO_CROPS];
  }

  const crops: unknown = JSON.parse(stored);
  if (!Array.isArray(crops)) {
    throw new Error("Saved local crop data is not a list. Clear or restore browser storage to continue.");
  }
  return crops as CropHistoryRecord[];
}

function writeLocalCrops(crops: CropHistoryRecord[]): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(CROPS_STORAGE_KEY, JSON.stringify(crops));
  }
}

function localResponse<T>(data: T, message?: string): ApiResponse<T> {
  return {
    data,
    source: "local_demo_store",
    isDemoData: true,
    message,
  };
}

function backendResponse<T>(data: T, message?: string): ApiResponse<T> {
  return {
    data,
    source: "backend",
    isDemoData: false,
    message,
  };
}

export function getApiErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return "An unexpected error occurred. Please try again.";
}

export const farmApiService = {
  async getFarms(): Promise<ApiResponse<FarmProfile[]>> {
    try {
      return backendResponse(await request<FarmProfile[]>("/api/v1/farms"));
    } catch (error) {
      if (!(error instanceof BackendUnavailableError)) throw error;
      return localResponse(
        readLocalFarms(),
        "Backend unavailable; showing browser-local farm data."
      );
    }
  },

  async getFarmById(farmId: string): Promise<ApiResponse<FarmProfile | null>> {
    try {
      return backendResponse(
        await request<FarmProfile>(`/api/v1/farms/${encodeURIComponent(farmId)}`)
      );
    } catch (error) {
      if (error instanceof FarmApiError && error.status === 404) {
        return backendResponse(null);
      }
      if (!(error instanceof BackendUnavailableError)) throw error;
      const farms = await this.getFarms();
      const farm = farms.data.find((item) => item.farm_id === farmId) || null;
      return {
        ...farms,
        data: farm,
      };
    }
  },

  async createFarm(farm: FarmProfile): Promise<ApiResponse<FarmProfile>> {
    try {
      const created = await request<FarmProfile>("/api/v1/farms", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(farm),
      });
      return backendResponse(created, "Farm persisted to the backend database.");
    } catch (error) {
      if (!(error instanceof BackendUnavailableError)) throw error;
      const farms = readLocalFarms();
      if (farms.some((item) => item.farm_id === farm.farm_id)) {
        throw new FarmApiError(`Farm '${farm.farm_id}' already exists in local storage.`, 409);
      }
      writeLocalFarms([farm, ...farms]);
      return localResponse(farm, "Saved only in this browser because the backend is unavailable.");
    }
  },

  async updateFarm(farm: FarmProfile): Promise<ApiResponse<FarmProfile>> {
    const { farm_id, created_at, ...update } = farm;
    try {
      const updated = await request<FarmProfile>(
        `/api/v1/farms/${encodeURIComponent(farm_id)}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...update, updated_at: new Date().toISOString() }),
        }
      );
      return backendResponse(updated, "Farm changes saved to the backend database.");
    } catch (error) {
      if (!(error instanceof BackendUnavailableError)) throw error;
      const farms = readLocalFarms();
      const index = farms.findIndex((item) => item.farm_id === farm_id);
      if (index < 0) {
        throw new FarmApiError(`Farm '${farm_id}' was not found in local storage.`, 404);
      }
      const updated = { ...farm, created_at, updated_at: new Date().toISOString() };
      farms[index] = updated;
      writeLocalFarms(farms);
      return localResponse(updated, "Saved only in this browser because the backend is unavailable.");
    }
  },

  async getCropsByFarm(farmId: string): Promise<ApiResponse<CropHistoryRecord[]>> {
    try {
      const crops = await request<CropHistoryRecord[]>(
        `/api/v1/farms/${encodeURIComponent(farmId)}/crops`
      );
      return backendResponse(crops);
    } catch (error) {
      if (!(error instanceof BackendUnavailableError)) throw error;
      const crops = readLocalCrops().filter((crop) => crop.farm_id === farmId);
      return localResponse(crops, "Backend unavailable; showing browser-local crop data.");
    }
  },

  async saveCropRecord(
    record: CropHistoryRecord
  ): Promise<ApiResponse<CropHistoryRecord>> {
    try {
      const created = await request<CropHistoryRecord>(
        `/api/v1/farms/${encodeURIComponent(record.farm_id)}/crops`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(record),
        }
      );
      return backendResponse(created, "Crop history saved to the backend database.");
    } catch (error) {
      if (!(error instanceof BackendUnavailableError)) throw error;
      const crops = readLocalCrops();
      const updated = [record, ...crops.filter((crop) => crop.record_id !== record.record_id)];
      writeLocalCrops(updated);
      return localResponse(record, "Saved only in this browser because the backend is unavailable.");
    }
  },

  async deleteCropRecord(
    farmId: string,
    recordId: string
  ): Promise<ApiResponse<boolean>> {
    try {
      await request<{ status: string }>(
        `/api/v1/farms/${encodeURIComponent(farmId)}/crops/${encodeURIComponent(recordId)}`,
        { method: "DELETE" }
      );
      return backendResponse(true);
    } catch (error) {
      if (!(error instanceof BackendUnavailableError)) throw error;
      const crops = readLocalCrops();
      writeLocalCrops(crops.filter((crop) => crop.record_id !== recordId));
      return localResponse(true);
    }
  },

  async chatWithAssistant(
    sessionId: string,
    message: string,
    language: SupportedLanguage,
    currentExtracted: Partial<FarmProfile>
  ): Promise<ApiResponse<AssistantChatResponse>> {
    const result = await request<AssistantChatResponse>("/api/v1/assistant/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        message,
        language,
        current_extracted: currentExtracted,
      }),
    });
    return backendResponse(result);
  },
};
