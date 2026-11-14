"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { SidebarLayout } from "@/components/layout/SidebarLayout";
import { FarmProfile } from "@/types/farm";
import { farmApiService, getApiErrorMessage } from "@/lib/api/farmApi";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertCircle, ArrowLeft, Save, CheckCircle2 } from "lucide-react";

export default function EditFarmPage() {
  const params = useParams();
  const router = useRouter();
  const farmId = (params?.farmId as string) || "farm-peshawar-001";

  const [farm, setFarm] = useState<FarmProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isDemoData, setIsDemoData] = useState(false);

  useEffect(() => {
    let isMounted = true;
    async function load() {
      setLoading(true);
      setErrorMessage(null);
      try {
        const res = await farmApiService.getFarmById(farmId);
        if (isMounted) {
          setFarm(res.data);
          setIsDemoData(res.isDemoData);
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
  }, [farmId]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!farm) return;
    setIsSaving(true);
    setErrorMessage(null);
    try {
      const result = await farmApiService.updateFarm({
        ...farm,
        updated_at: new Date().toISOString(),
      });
      setSavedSuccess(true);
      setIsDemoData(result.isDemoData);
      setSaveMessage(result.message || (result.isDemoData
        ? "Changes saved only in this browser."
        : "Changes saved to the backend database."));
      setTimeout(() => {
        router.push(`/farms/${farm.farm_id}`);
      }, 1500);
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error));
    } finally {
      setIsSaving(false);
    }
  };

  if (loading) {
    return (
      <SidebarLayout>
        <div className="h-64 bg-slate-100 animate-pulse rounded-xl" />
      </SidebarLayout>
    );
  }

  if (!farm) {
    return (
      <SidebarLayout>
        <div className="bg-white p-8 rounded-xl border text-center">
          {errorMessage ? (
            <p role="alert" className="text-sm text-red-700">{errorMessage}</p>
          ) : (
            <p>Farm not found</p>
          )}
        </div>
      </SidebarLayout>
    );
  }

  return (
    <SidebarLayout>
      <div className="max-w-4xl mx-auto space-y-6">
        <div>
          <Link
            href={`/farms/${farm.farm_id}`}
            className="text-xs font-semibold text-forest-700 hover:text-forest-900 inline-flex items-center gap-1.5 mb-2"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Cancel and Return to Farm Profile</span>
          </Link>
          <h1 className="text-2xl font-bold text-forest-950">Edit Farm Profile</h1>
          <p className="text-xs text-slate-500 mt-1">Update profile parameters for {farm.name} ({farm.farm_id})</p>
        </div>

        {savedSuccess && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-800 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>{saveMessage} Redirecting...</span>
          </div>
        )}

        {isDemoData && (
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-900">
            Backend unavailable. Edits are saved only in this browser and will not sync automatically.
          </div>
        )}

        {errorMessage && (
          <div
            role="alert"
            className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800 flex items-center gap-2"
          >
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSave}>
          <Card>
            <CardHeader>
              <CardTitle className="text-base text-forest-950">Farm Profile Information</CardTitle>
              <CardDescription className="text-xs">
                Fields conform directly to <code>farm.schema.json</code>
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-slate-600 mb-1 font-medium">Farm Name</label>
                  <input
                    type="text"
                    required
                    value={farm.name}
                    onChange={(e) => setFarm({ ...farm, name: e.target.value })}
                    className="w-full text-xs p-2 bg-slate-50 border border-slate-300 rounded focus:ring-2 focus:ring-forest-600"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 mb-1 font-medium">Owner Full Name</label>
                  <input
                    type="text"
                    required
                    value={farm.owner_name}
                    onChange={(e) => setFarm({ ...farm, owner_name: e.target.value })}
                    className="w-full text-xs p-2 bg-slate-50 border border-slate-300 rounded focus:ring-2 focus:ring-forest-600"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 mb-1 font-medium">Contact Phone</label>
                  <input
                    type="text"
                    required
                    value={farm.contact_phone}
                    onChange={(e) => setFarm({ ...farm, contact_phone: e.target.value })}
                    className="w-full text-xs p-2 bg-slate-50 border border-slate-300 rounded focus:ring-2 focus:ring-forest-600"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 mb-1 font-medium">Total Area (Hectares)</label>
                  <input
                    type="number"
                    step="0.1"
                    required
                    value={farm.total_area_hectares}
                    onChange={(e) =>
                      setFarm({ ...farm, total_area_hectares: parseFloat(e.target.value) || 0 })
                    }
                    className="w-full text-xs p-2 bg-slate-50 border border-slate-300 rounded focus:ring-2 focus:ring-forest-600"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 mb-1 font-medium">Soil Classification</label>
                  <select
                    value={farm.soil_type}
                    onChange={(e) =>
                      setFarm({ ...farm, soil_type: e.target.value as FarmProfile["soil_type"] })
                    }
                    className="w-full text-xs p-2 bg-slate-50 border border-slate-300 rounded focus:ring-2 focus:ring-forest-600"
                  >
                    <option value="alluvial_clay">Alluvial Clay</option>
                    <option value="sandy_loam">Sandy Loam</option>
                    <option value="clay_loam">Clay Loam</option>
                    <option value="silt_loam">Silt Loam</option>
                    <option value="sandy">Sandy</option>
                    <option value="other">Other</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-600 mb-1 font-medium">Irrigation Source</label>
                  <select
                    value={farm.irrigation_source}
                    onChange={(e) =>
                      setFarm({
                        ...farm,
                        irrigation_source: e.target.value as FarmProfile["irrigation_source"],
                      })
                    }
                    className="w-full text-xs p-2 bg-slate-50 border border-slate-300 rounded focus:ring-2 focus:ring-forest-600"
                  >
                    <option value="canal">Canal System</option>
                    <option value="tube_well">Tube Well</option>
                    <option value="river_lift">River Lift</option>
                    <option value="drip">Drip Irrigation</option>
                    <option value="rainfed">Rainfed</option>
                    <option value="other">Other</option>
                  </select>
                </div>
              </div>

              <div className="pt-4 flex items-center justify-end gap-3 border-t border-slate-200">
                <Link href={`/farms/${farm.farm_id}`}>
                  <Button type="button" variant="outline" size="sm">
                    Cancel
                  </Button>
                </Link>
                <Button
                  type="submit"
                  size="sm"
                  disabled={isSaving}
                  className="bg-forest-700 hover:bg-forest-800 text-white flex items-center gap-1.5"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>{isSaving ? "Saving Changes..." : "Save Changes"}</span>
                </Button>
              </div>
            </CardContent>
          </Card>
        </form>
      </div>
    </SidebarLayout>
  );
}
