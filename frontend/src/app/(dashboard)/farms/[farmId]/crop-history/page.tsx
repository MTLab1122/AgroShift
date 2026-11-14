"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { SidebarLayout } from "@/components/layout/SidebarLayout";
import { CropHistoryRecord, FarmProfile } from "@/types/farm";
import { ApiResponse, farmApiService, getApiErrorMessage } from "@/lib/api/farmApi";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  ArrowLeft,
  PlusCircle,
  Sprout,
  Calendar,
  Scale,
  Trash2,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";

export default function CropHistoryPage() {
  const params = useParams();
  const farmId = (params?.farmId as string) || "farm-peshawar-001";

  const [farm, setFarm] = useState<FarmProfile | null>(null);
  const [crops, setCrops] = useState<CropHistoryRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [apiMeta, setApiMeta] = useState<ApiResponse<CropHistoryRecord[]> | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [operationMessage, setOperationMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [deletingRecordId, setDeletingRecordId] = useState<string | null>(null);

  // New Record Form State
  const [newCrop, setNewCrop] = useState<Partial<CropHistoryRecord>>({
    crop_name: "Wheat",
    variety: "",
    season: "Rabi",
    year: new Date().getFullYear(),
    status: "growing",
    area_planted_hectares: 5.0,
    yield_amount_kg: null,
    sowing_date: new Date().toISOString().split("T")[0],
    harvest_date: null,
    notes: "",
  });

  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let isMounted = true;
    async function load() {
      setLoading(true);
      setErrorMessage(null);
      try {
        const [farmRes, cropsRes] = await Promise.all([
          farmApiService.getFarmById(farmId),
          farmApiService.getCropsByFarm(farmId),
        ]);
        if (isMounted) {
          setFarm(farmRes.data);
          setCrops(cropsRes.data);
          setApiMeta(cropsRes);
        }
      } catch (error) {
        if (isMounted) setErrorMessage(getApiErrorMessage(error));
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    load();
    return () => {
      isMounted = false;
    };
  }, [farmId, refreshKey]);

  const handleCreateRecord = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCrop.crop_name || !newCrop.season) return;

    const record: CropHistoryRecord = {
      record_id: `crop-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
      farm_id: farmId,
      crop_name: newCrop.crop_name!,
      variety: newCrop.variety || "Standard",
      season: newCrop.season || "Rabi",
      year: Number(newCrop.year) || new Date().getFullYear(),
      sowing_date: newCrop.sowing_date || null,
      harvest_date: newCrop.harvest_date || null,
      area_planted_hectares: Number(newCrop.area_planted_hectares) || null,
      yield_amount_kg: newCrop.yield_amount_kg ? Number(newCrop.yield_amount_kg) : null,
      status: newCrop.status || "growing",
      notes: newCrop.notes || "",
    };

    setIsSaving(true);
    setErrorMessage(null);
    setOperationMessage(null);
    try {
      const result = await farmApiService.saveCropRecord(record);
      setOperationMessage(
        result.message || (result.isDemoData
          ? "Saved only in this browser."
          : "Crop record saved to the backend database.")
      );
      setShowAddModal(false);
      setRefreshKey((k) => k + 1);
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error));
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (recordId: string) => {
    if (!confirm("Are you sure you want to remove this crop history record?")) return;
    setDeletingRecordId(recordId);
    setErrorMessage(null);
    setOperationMessage(null);
    try {
      const result = await farmApiService.deleteCropRecord(farmId, recordId);
      setOperationMessage(
        result.isDemoData
          ? "Record removed from this browser only."
          : "Crop record deleted from the backend database."
      );
      setRefreshKey((k) => k + 1);
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error));
    } finally {
      setDeletingRecordId(null);
    }
  };

  return (
    <SidebarLayout>
      <div className="space-y-6 max-w-7xl mx-auto">
        {/* Navigation & Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <Link
              href={`/farms/${farmId}`}
              className="text-xs font-semibold text-forest-700 hover:text-forest-900 inline-flex items-center gap-1.5 mb-2"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Farm Details ({farm?.name || farmId})</span>
            </Link>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-forest-950 flex items-center gap-3">
              <span>Seasonal Crop History</span>
              <span className="text-xs font-semibold uppercase bg-forest-100 text-forest-800 px-2.5 py-1 rounded">
                {farmId}
              </span>
            </h1>
            <p className="text-xs sm:text-sm text-slate-500 mt-1">
              Historical rotations, sowing/harvest dates, yields, and agro-ecological season cycles
            </p>
          </div>

          {apiMeta?.isDemoData && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 flex items-center gap-2.5 text-xs text-amber-900">
              <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
              <span>Backend unavailable. Crop-history changes are stored only in this browser and will not sync automatically.</span>
            </div>
          )}

          {operationMessage && (
            <div role="status" className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 text-xs text-emerald-900">
              {operationMessage}
            </div>
          )}

          {errorMessage && (
            <div role="alert" className="bg-red-50 border border-red-200 rounded-xl p-3 text-xs text-red-900">
              {errorMessage}
            </div>
          )}

          <Button
            onClick={() => setShowAddModal(true)}
            className="bg-forest-700 hover:bg-forest-800 text-white flex items-center gap-2"
          >
            <PlusCircle className="w-4 h-4" />
            <span>Add Crop Record</span>
          </Button>
        </div>

        {/* Modal / Add Record Form Drawer */}
        {showAddModal && (
          <Card className="border-forest-400 bg-forest-50/40 shadow-md">
            <CardHeader className="py-4 border-b border-forest-100">
              <CardTitle className="text-base text-forest-950 flex items-center gap-2">
                <Sprout className="w-4 h-4 text-forest-700" />
                <span>Record New Crop Cycle</span>
              </CardTitle>
              <CardDescription className="text-xs">
                Matches schema specifications in <code>crop.schema.json</code>
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-4">
              <form onSubmit={handleCreateRecord} className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                <div>
                  <label className="block text-slate-600 mb-1 font-medium">Crop Name</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Wheat, Maize, Cotton"
                    value={newCrop.crop_name}
                    onChange={(e) => setNewCrop({ ...newCrop, crop_name: e.target.value })}
                    className="w-full p-2 bg-white border border-slate-300 rounded"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 mb-1 font-medium">Variety / Cultivar</label>
                  <input
                    type="text"
                    placeholder="e.g. Fakhr-e-Sarhad"
                    value={newCrop.variety}
                    onChange={(e) => setNewCrop({ ...newCrop, variety: e.target.value })}
                    className="w-full p-2 bg-white border border-slate-300 rounded"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 mb-1 font-medium">Agro Season</label>
                  <select
                    value={newCrop.season}
                    onChange={(e) =>
                      setNewCrop({ ...newCrop, season: e.target.value as CropHistoryRecord["season"] })
                    }
                    className="w-full p-2 bg-white border border-slate-300 rounded"
                  >
                    <option value="Kharif">Kharif (Summer)</option>
                    <option value="Rabi">Rabi (Winter)</option>
                    <option value="Zaid">Zaid</option>
                    <option value="Spring">Spring</option>
                    <option value="Autumn">Autumn</option>
                    <option value="Perennial">Perennial</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-600 mb-1 font-medium">Year</label>
                  <input
                    type="number"
                    min="1980"
                    max="2100"
                    value={newCrop.year}
                    onChange={(e) => setNewCrop({ ...newCrop, year: parseInt(e.target.value) || 2024 })}
                    className="w-full p-2 bg-white border border-slate-300 rounded"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 mb-1 font-medium">Sowing Date</label>
                  <input
                    type="date"
                    value={newCrop.sowing_date || ""}
                    onChange={(e) => setNewCrop({ ...newCrop, sowing_date: e.target.value })}
                    className="w-full p-2 bg-white border border-slate-300 rounded"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 mb-1 font-medium">Harvest Date (if completed)</label>
                  <input
                    type="date"
                    value={newCrop.harvest_date || ""}
                    onChange={(e) => setNewCrop({ ...newCrop, harvest_date: e.target.value })}
                    className="w-full p-2 bg-white border border-slate-300 rounded"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 mb-1 font-medium">Area Planted (Hectares)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0.1"
                    value={newCrop.area_planted_hectares || ""}
                    onChange={(e) =>
                      setNewCrop({ ...newCrop, area_planted_hectares: parseFloat(e.target.value) || 0 })
                    }
                    className="w-full p-2 bg-white border border-slate-300 rounded"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 mb-1 font-medium">Yield (Kilograms)</label>
                  <input
                    type="number"
                    min="0"
                    placeholder="e.g. 24000"
                    value={newCrop.yield_amount_kg || ""}
                    onChange={(e) =>
                      setNewCrop({ ...newCrop, yield_amount_kg: parseFloat(e.target.value) || null })
                    }
                    className="w-full p-2 bg-white border border-slate-300 rounded"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 mb-1 font-medium">Status</label>
                  <select
                    value={newCrop.status}
                    onChange={(e) =>
                      setNewCrop({ ...newCrop, status: e.target.value as CropHistoryRecord["status"] })
                    }
                    className="w-full p-2 bg-white border border-slate-300 rounded"
                  >
                    <option value="growing">Growing</option>
                    <option value="harvested">Harvested</option>
                    <option value="sown">Sown</option>
                    <option value="planned">Planned</option>
                    <option value="failed">Failed</option>
                  </select>
                </div>

                <div className="sm:col-span-3 flex justify-end gap-2 pt-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setShowAddModal(false)}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" size="sm" disabled={isSaving} className="bg-forest-700 text-white">
                    {isSaving ? "Saving..." : "Save Crop Cycle"}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}

        {/* Crop History Timeline Table */}
        <Card>
          <CardHeader className="py-4 border-b border-slate-100 flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-base text-forest-950">Crop Rotation Timeline ({crops.length})</CardTitle>
              <CardDescription className="text-xs">
                Historical planting cycles chronologically sorted
              </CardDescription>
            </div>
          </CardHeader>

          <CardContent className="p-0">
            {loading ? (
              <div className="p-8 text-center text-xs text-slate-400">Loading crop records...</div>
            ) : crops.length === 0 ? (
              <div className="p-12 text-center text-slate-500 text-sm">
                No crop history recorded yet for this farm.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
                      <th className="p-3.5 pl-6">Season / Year</th>
                      <th className="p-3.5">Crop & Variety</th>
                      <th className="p-3.5">Planted Area</th>
                      <th className="p-3.5">Sown / Harvested</th>
                      <th className="p-3.5">Yield</th>
                      <th className="p-3.5">Status</th>
                      <th className="p-3.5 text-right pr-6">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {crops.map((crop) => (
                      <tr key={crop.record_id} className="hover:bg-slate-50/70 transition">
                        <td className="p-3.5 pl-6">
                          <span className="font-bold text-forest-900 block">{crop.season}</span>
                          <span className="text-slate-400 text-[11px]">{crop.year}</span>
                        </td>
                        <td className="p-3.5">
                          <span className="font-semibold text-slate-800 block">{crop.crop_name}</span>
                          <span className="text-slate-500 text-[11px]">{crop.variety || "General"}</span>
                        </td>
                        <td className="p-3.5 text-slate-700">
                          {crop.area_planted_hectares ? `${crop.area_planted_hectares} ha` : "—"}
                        </td>
                        <td className="p-3.5 text-slate-600">
                          <div className="flex items-center gap-1 text-[11px]">
                            <Calendar className="w-3 h-3 text-slate-400" />
                            <span>{crop.sowing_date || "—"}</span>
                            <span>→</span>
                            <span>{crop.harvest_date || "Present"}</span>
                          </div>
                        </td>
                        <td className="p-3.5">
                          {crop.yield_amount_kg ? (
                            <span className="font-medium text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded text-[11px] border border-emerald-200">
                              <Scale className="w-3 h-3 inline mr-1" />
                              {(crop.yield_amount_kg / 1000).toFixed(1)} metric tons
                            </span>
                          ) : (
                            <span className="text-slate-400">—</span>
                          )}
                        </td>
                        <td className="p-3.5">
                          <span
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold capitalize ${
                              crop.status === "harvested"
                                ? "bg-slate-100 text-slate-700"
                                : crop.status === "growing"
                                ? "bg-agrigreen-100 text-forest-800"
                                : "bg-amber-100 text-amber-800"
                            }`}
                          >
                            <CheckCircle2 className="w-3 h-3" />
                            {crop.status}
                          </span>
                        </td>
                        <td className="p-3.5 text-right pr-6">
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(crop.record_id)}
                            disabled={deletingRecordId === crop.record_id}
                            className="text-slate-400 hover:text-red-600 hover:bg-red-50"
                          >
                            {deletingRecordId === crop.record_id ? (
                              <span className="text-[10px]">...</span>
                            ) : (
                              <Trash2 className="w-3.5 h-3.5" />
                            )}
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </SidebarLayout>
  );
}
