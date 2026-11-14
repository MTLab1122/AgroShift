"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useParams } from "next/navigation";
import { SidebarLayout } from "@/components/layout/SidebarLayout";
import { FarmProfile, CropHistoryRecord } from "@/types/farm";
import { farmApiService, ApiResponse, getApiErrorMessage } from "@/lib/api/farmApi";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  ArrowLeft,
  MapPin,
  Sprout,
  Edit,
  History,
  Phone,
  Globe,
  Calendar,
  AlertCircle,
} from "lucide-react";

const FarmMap = dynamic(
  () => import("@/components/map/FarmMap").then((mod) => mod.FarmMap),
  {
    ssr: false,
    loading: () => (
      <div className="h-[360px] bg-slate-100 animate-pulse flex items-center justify-center text-slate-400 text-sm rounded-xl">
        Loading Map View...
      </div>
    ),
  }
);

export default function FarmDetailPage() {
  const params = useParams();
  const farmId = (params?.farmId as string) || "farm-peshawar-001";

  const [farm, setFarm] = useState<FarmProfile | null>(null);
  const [crops, setCrops] = useState<CropHistoryRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [meta, setMeta] = useState<ApiResponse<FarmProfile | null> | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    async function loadData() {
      setLoading(true);
      setLoadError(null);
      try {
        const [farmRes, cropsRes] = await Promise.all([
          farmApiService.getFarmById(farmId),
          farmApiService.getCropsByFarm(farmId),
        ]);
        if (isMounted) {
          setFarm(farmRes.data);
          setCrops(cropsRes.data);
          setMeta(farmRes);
        }
      } catch (error) {
        if (isMounted) setLoadError(getApiErrorMessage(error));
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    loadData();
    return () => {
      isMounted = false;
    };
  }, [farmId]);

  if (loading) {
    return (
      <SidebarLayout>
        <div className="space-y-4">
          <div className="h-8 w-48 bg-slate-200 animate-pulse rounded" />
          <div className="h-64 bg-slate-200 animate-pulse rounded-xl" />
        </div>
      </SidebarLayout>
    );
  }

  if (!farm) {
    return (
      <SidebarLayout>
        <div className="bg-white p-12 rounded-xl border border-slate-200 text-center">
          <h2 className="text-xl font-bold text-slate-900">
            {loadError ? "Unable to Load Farm" : "Farm Not Found"}
          </h2>
          <p role={loadError ? "alert" : undefined} className="text-sm text-slate-500 mt-1">
            {loadError || `Farm ID "${farmId}" could not be retrieved.`}
          </p>
          <Link href="/farms" className="mt-4 inline-block">
            <Button variant="outline">Return to Farms Dashboard</Button>
          </Link>
        </div>
      </SidebarLayout>
    );
  }

  const acres = Math.round(farm.total_area_hectares * 2.47105 * 10) / 10;
  const boundaryCoords =
    farm.boundary?.type === "Polygon"
      ? (farm.boundary.coordinates[0] as number[][])
      : undefined;

  return (
    <SidebarLayout>
      <div className="space-y-6 max-w-7xl mx-auto">
        {/* Navigation & Actions */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <Link
              href="/farms"
              className="text-xs font-semibold text-forest-700 hover:text-forest-900 inline-flex items-center gap-1.5 mb-2"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Farms Dashboard</span>
            </Link>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl sm:text-3xl font-extrabold text-forest-950">
                {farm.name}
              </h1>
              <span className="text-xs font-semibold uppercase bg-forest-100 text-forest-800 px-2.5 py-1 rounded">
                {farm.farm_id}
              </span>
            </div>
            <p className="text-xs sm:text-sm text-slate-500 mt-1">
              Owner: {farm.owner_name} • Registered in {farm.location.district}, {farm.location.province_or_region}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Link href={`/farms/${farm.farm_id}/edit`}>
              <Button variant="outline" size="sm" className="flex items-center gap-1.5">
                <Edit className="w-3.5 h-3.5" />
                <span>Edit Profile</span>
              </Button>
            </Link>
            <Link href={`/farms/${farm.farm_id}/crop-history`}>
              <Button size="sm" className="bg-forest-700 hover:bg-forest-800 text-white flex items-center gap-1.5">
                <History className="w-3.5 h-3.5" />
                <span>Crop History ({crops.length})</span>
              </Button>
            </Link>
          </div>
        </div>

        {/* Demo status alert */}
        {meta?.isDemoData && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 flex items-center gap-2.5 text-xs text-amber-900">
            <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
            <span>
              Backend unavailable. This farm is from browser-local data; local changes will not sync automatically.
            </span>
          </div>
        )}

        {/* Main Grid: Details & Map */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Details Column */}
          <div className="lg:col-span-5 space-y-6">
            <Card>
              <CardHeader className="py-4 border-b border-slate-100">
                <CardTitle className="text-base text-forest-950">Farm Profile Specifications</CardTitle>
                <CardDescription className="text-xs">
                  Canonical parameters conforming to <code>farm.schema.json</code>
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-4 space-y-3.5 text-xs">
                <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                  <span className="text-slate-500">Contact Phone</span>
                  <span className="font-semibold text-slate-800 flex items-center gap-1">
                    <Phone className="w-3.5 h-3.5 text-slate-400" />
                    {farm.contact_phone}
                  </span>
                </div>

                <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                  <span className="text-slate-500">Preferred Language</span>
                  <span className="font-semibold text-slate-800 flex items-center gap-1 uppercase">
                    <Globe className="w-3.5 h-3.5 text-slate-400" />
                    {farm.preferred_language}
                  </span>
                </div>

                <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                  <span className="text-slate-500">Total Farm Area</span>
                  <span className="font-semibold text-forest-800">
                    {farm.total_area_hectares} ha ({acres} acres)
                  </span>
                </div>

                <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                  <span className="text-slate-500">Soil Type</span>
                  <span className="font-semibold text-slate-800 capitalize">
                    {farm.soil_type.replace("_", " ")}
                  </span>
                </div>

                <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                  <span className="text-slate-500">Irrigation Method</span>
                  <span className="font-semibold text-slate-800 capitalize">
                    {farm.irrigation_source.replace("_", " ")}
                  </span>
                </div>

                <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                  <span className="text-slate-500">Elevation</span>
                  <span className="font-semibold text-slate-800">
                    {farm.location.elevation_meters ? `${farm.location.elevation_meters} m ASL` : "N/A"}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Created / Updated</span>
                  <span className="text-slate-600 flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5 text-slate-400" />
                    {new Date(farm.updated_at).toLocaleDateString()}
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* Standing Crops Card */}
            <Card>
              <CardHeader className="py-4 border-b border-slate-100">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base text-forest-950 flex items-center gap-2">
                    <Sprout className="w-4 h-4 text-agrigreen-600" />
                    <span>Current Standing Crops</span>
                  </CardTitle>
                  <Link
                    href={`/farms/${farm.farm_id}/crop-history`}
                    className="text-xs text-forest-700 hover:underline font-medium"
                  >
                    View All
                  </Link>
                </div>
              </CardHeader>
              <CardContent className="pt-4">
                {farm.current_crops && farm.current_crops.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {farm.current_crops.map((crop) => (
                      <span
                        key={crop}
                        className="px-3 py-1.5 bg-agrigreen-50 text-forest-900 border border-agrigreen-300 rounded-lg text-xs font-semibold"
                      >
                        {crop}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500">No standing crops currently recorded.</p>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Map Column */}
          <div className="lg:col-span-7">
            <Card className="h-full flex flex-col justify-between">
              <CardHeader className="py-4 border-b border-slate-100">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-base text-forest-950 flex items-center gap-2">
                      <MapPin className="w-4 h-4 text-forest-700" />
                      <span>Spatial Parcel & Boundary</span>
                    </CardTitle>
                    <CardDescription className="text-xs mt-0.5">
                      Centroid: {farm.location.latitude}° N, {farm.location.longitude}° E
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-4 flex-1">
                <FarmMap
                  initialLat={farm.location.latitude}
                  initialLng={farm.location.longitude}
                  initialBoundary={boundaryCoords}
                  readOnly={true}
                />
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </SidebarLayout>
  );
}
