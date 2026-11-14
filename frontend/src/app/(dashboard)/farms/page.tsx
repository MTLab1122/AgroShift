"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { SidebarLayout } from "@/components/layout/SidebarLayout";
import { FarmProfile } from "@/types/farm";
import { farmApiService, ApiResponse } from "@/lib/api/farmApi";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Sprout,
  PlusCircle,
  MapPin,
  Search,
  Filter,
  CheckCircle2,
  TrendingUp,
  AlertCircle,
  Layers,
  ChevronRight,
} from "lucide-react";

export default function FarmsDashboardPage() {
  const [farms, setFarms] = useState<FarmProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterDistrict, setFilterDistrict] = useState("all");
  const [apiMeta, setApiMeta] = useState<ApiResponse<FarmProfile[]> | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let isMounted = true;
    async function load() {
      setLoading(true);
      setLoadError(null);
      try {
        const res = await farmApiService.getFarms();
        if (isMounted) {
          setFarms(res.data);
          setApiMeta(res);
        }
      } catch (error) {
        if (isMounted) {
          setLoadError(error instanceof Error ? error.message : "Unable to load farm records.");
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    load();
    return () => {
      isMounted = false;
    };
  }, [refreshKey]);

  const filteredFarms = farms.filter((f) => {
    const matchesSearch =
      f.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      f.owner_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      f.location.district.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesDistrict =
      filterDistrict === "all" ||
      f.location.district.toLowerCase() === filterDistrict.toLowerCase();
    return matchesSearch && matchesDistrict;
  });

  const totalHectares = farms.reduce((acc, f) => acc + (f.total_area_hectares || 0), 0);
  const totalAcres = Math.round(totalHectares * 2.47105 * 10) / 10;

  // Extract unique crops
  const standingCrops = Array.from(new Set(farms.flatMap((f) => f.current_crops || [])));

  return (
    <SidebarLayout>
      <div className="space-y-8">
        {/* Header with Title and Add Button */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-agrigreen-100 text-forest-800 text-xs font-semibold mb-2">
              <Sprout className="w-3.5 h-3.5 text-forest-700" />
              Module 01: Farm Management & Location Intelligence
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-forest-950">
              Farm Management Dashboard
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Registered agricultural parcels, spatial centroids, boundaries, and crop operations
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link href="/farms/new">
              <Button className="bg-forest-700 hover:bg-forest-800 text-white shadow-sm flex items-center gap-2">
                <PlusCircle className="w-4 h-4" />
                <span>Register New Farm</span>
              </Button>
            </Link>
          </div>
        </div>

        {/* Backend & Demo Data Banner */}
        {apiMeta?.isDemoData && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3 text-amber-900 text-xs">
            <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-amber-950">Showing browser-local demonstration data</p>
              <p className="text-amber-800 mt-0.5 leading-relaxed">
                The backend could not be reached. Changes made in this mode stay in this browser and will not sync automatically.
              </p>
            </div>
          </div>
        )}

        {loadError && (
          <div
            role="alert"
            className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center justify-between gap-3 text-red-900 text-xs"
          >
            <span>{loadError}</span>
            <Button type="button" size="sm" variant="outline" onClick={() => setRefreshKey((key) => key + 1)}>
              Retry
            </Button>
          </div>
        )}

        {/* Overview Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <Card className="border-forest-100 bg-white">
            <CardHeader className="pb-2">
              <CardDescription className="text-xs uppercase font-semibold text-slate-500">
                Registered Farms
              </CardDescription>
              <CardTitle className="text-2xl font-bold text-forest-950 flex items-center justify-between">
                <span>{farms.length}</span>
                <span className="p-2 bg-forest-50 text-forest-700 rounded-lg text-sm">
                  <CheckCircle2 className="w-5 h-5" />
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <span className="text-xs text-slate-500">Active parcels registered</span>
            </CardContent>
          </Card>

          <Card className="border-forest-100 bg-white">
            <CardHeader className="pb-2">
              <CardDescription className="text-xs uppercase font-semibold text-slate-500">
                Total Farm Area
              </CardDescription>
              <CardTitle className="text-2xl font-bold text-forest-950 flex items-center justify-between">
                <span>{Math.round(totalHectares * 10) / 10} ha</span>
                <span className="p-2 bg-agrigreen-50 text-agrigreen-700 rounded-lg text-sm">
                  <TrendingUp className="w-5 h-5" />
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <span className="text-xs text-slate-500">Approx. {totalAcres} acres mapped</span>
            </CardContent>
          </Card>

          <Card className="border-forest-100 bg-white">
            <CardHeader className="pb-2">
              <CardDescription className="text-xs uppercase font-semibold text-slate-500">
                Current Standing Crops
              </CardDescription>
              <CardTitle className="text-2xl font-bold text-forest-950 flex items-center justify-between">
                <span>{standingCrops.length}</span>
                <span className="p-2 bg-earth-100 text-earth-800 rounded-lg text-sm">
                  <Sprout className="w-5 h-5" />
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <span className="text-xs text-slate-500">{standingCrops.join(", ") || "None"}</span>
            </CardContent>
          </Card>

          <Card className="border-forest-100 bg-white">
            <CardHeader className="pb-2">
              <CardDescription className="text-xs uppercase font-semibold text-slate-500">
                Location Coverage
              </CardDescription>
              <CardTitle className="text-2xl font-bold text-forest-950 flex items-center justify-between">
                <span>KP Province</span>
                <span className="p-2 bg-blue-50 text-blue-700 rounded-lg text-sm">
                  <Layers className="w-5 h-5" />
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <span className="text-xs text-slate-500">Peshawar, Charsadda, Mardan</span>
            </CardContent>
          </Card>
        </div>

        {/* Filter and Search Bar */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search farms by name, owner, or district..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full text-sm bg-slate-50 border border-slate-300 rounded-lg pl-9 pr-3.5 py-2 focus:outline-none focus:ring-2 focus:ring-forest-600"
            />
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Filter className="w-3.5 h-3.5 text-slate-400" />
              <span>District:</span>
            </div>
            <select
              value={filterDistrict}
              onChange={(e) => setFilterDistrict(e.target.value)}
              className="text-xs bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-slate-700 focus:outline-none focus:ring-2 focus:ring-forest-600"
            >
              <option value="all">All Districts</option>
              <option value="peshawar">Peshawar</option>
              <option value="charsadda">Charsadda</option>
              <option value="mardan">Mardan</option>
            </select>
          </div>
        </div>

        {/* Farm Cards Grid */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-forest-950">Registered Farm Parcels ({filteredFarms.length})</h2>
          </div>

          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-64 bg-slate-200 animate-pulse rounded-xl" />
              ))}
            </div>
          ) : filteredFarms.length === 0 ? (
            <div className="bg-white border border-slate-200 rounded-xl p-12 text-center">
              <Sprout className="w-10 h-10 text-slate-400 mx-auto mb-3" />
              <h3 className="font-semibold text-slate-800">No farms match your search</h3>
              <p className="text-sm text-slate-500 mt-1">Try resetting the district filter or search query.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredFarms.map((farm) => {
                const acres = Math.round(farm.total_area_hectares * 2.47105 * 10) / 10;
                return (
                  <Card
                    key={farm.farm_id}
                    className="border-slate-200 hover:border-forest-300 hover:shadow-md transition flex flex-col justify-between"
                  >
                    <div>
                      <CardHeader className="pb-3 border-b border-slate-100">
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <span className="text-[10px] font-semibold tracking-wider uppercase text-forest-700 bg-forest-50 px-2 py-0.5 rounded">
                              {farm.farm_id}
                            </span>
                            <CardTitle className="text-base font-bold text-forest-950 mt-1.5 leading-snug">
                              {farm.name}
                            </CardTitle>
                            <CardDescription className="text-xs text-slate-500 mt-0.5">
                              Owner: {farm.owner_name}
                            </CardDescription>
                          </div>
                        </div>
                      </CardHeader>

                      <CardContent className="pt-4 space-y-3 text-xs">
                        <div className="flex items-center gap-1.5 text-slate-600">
                          <MapPin className="w-4 h-4 text-forest-600 shrink-0" />
                          <span>
                            {farm.location.village_or_town ? `${farm.location.village_or_town}, ` : ""}
                            {farm.location.district}, {farm.location.province_or_region}
                          </span>
                        </div>

                        <div className="grid grid-cols-2 gap-2 bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                          <div>
                            <span className="text-slate-400 block text-[11px]">Area</span>
                            <strong className="text-slate-800 font-medium">
                              {farm.total_area_hectares} ha ({acres} ac)
                            </strong>
                          </div>
                          <div>
                            <span className="text-slate-400 block text-[11px]">Soil Classification</span>
                            <strong className="text-slate-800 font-medium capitalize">
                              {farm.soil_type.replace("_", " ")}
                            </strong>
                          </div>
                          <div>
                            <span className="text-slate-400 block text-[11px]">Irrigation</span>
                            <strong className="text-slate-800 font-medium capitalize">
                              {farm.irrigation_source.replace("_", " ")}
                            </strong>
                          </div>
                          <div>
                            <span className="text-slate-400 block text-[11px]">Coordinates</span>
                            <span className="text-slate-700 font-mono text-[10px]">
                              {farm.location.latitude}°, {farm.location.longitude}°
                            </span>
                          </div>
                        </div>

                        {farm.current_crops && farm.current_crops.length > 0 && (
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="text-slate-400 text-[11px]">Standing Crops:</span>
                            {farm.current_crops.map((c) => (
                              <span
                                key={c}
                                className="bg-agrigreen-50 text-forest-800 px-2 py-0.5 rounded text-[11px] font-medium border border-agrigreen-200"
                              >
                                {c}
                              </span>
                            ))}
                          </div>
                        )}
                      </CardContent>
                    </div>

                    <div className="p-4 pt-0 mt-4 border-t border-slate-100 flex items-center justify-between">
                      <Link
                        href={`/farms/${farm.farm_id}`}
                        className="text-xs font-semibold text-forest-700 hover:text-forest-900 inline-flex items-center gap-1"
                      >
                        <span>View Farm Profile</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </Link>
                      <Link
                        href={`/farms/${farm.farm_id}/crop-history`}
                        className="text-xs text-slate-500 hover:text-slate-800"
                      >
                        Crop History
                      </Link>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </SidebarLayout>
  );
}
