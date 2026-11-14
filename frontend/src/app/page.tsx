"use client";

import React from "react";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { LanguageSelector } from "@/components/common/LanguageSelector";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Sprout, MapPin, Sparkles, Database, CheckCircle2 } from "lucide-react";

export default function Home() {
  const { t, isRtl } = useLanguage();

  return (
    <main className={`min-h-screen bg-slate-50 text-slate-900 ${isRtl ? "rtl" : "ltr"}`}>
      {/* Top Navigation */}
      <header className="sticky top-0 z-50 bg-white border-b border-slate-200 px-6 py-4 shadow-sm">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-3 rtl:space-x-reverse">
            <div className="bg-emerald-600 text-white p-2 rounded-lg shadow-sm">
              <Sprout className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-slate-900">{t.appName}</h1>
              <p className="text-xs text-slate-500">{t.tagline}</p>
            </div>
          </div>
          <div className="flex items-center space-x-4 rtl:space-x-reverse">
            <LanguageSelector />
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="max-w-7xl mx-auto px-6 py-10">
        <div className="mb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 text-xs font-semibold mb-3">
            <Sparkles className="w-3.5 h-3.5" />
            Module 01 Foundation Ready
          </div>
          <h2 className="text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
            {t.module01Title}
          </h2>
          <p className="mt-2 text-base text-slate-600 max-w-2xl">
            Modular architecture initialized with TypeScript, Tailwind CSS, shadcn/ui components,
            multilingual locale state (English, اردو, پښتو), and canonical schema contracts.
          </p>
        </div>

        {/* Status Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
          <Card>
            <CardHeader>
              <div className="w-10 h-10 rounded-lg bg-emerald-100 flex items-center justify-center text-emerald-700 mb-2">
                <Database className="w-5 h-5" />
              </div>
              <CardTitle>Canonical Contracts</CardTitle>
              <CardDescription>
                Synchronized with shared JSON schemas and Module 02
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="text-sm space-y-2 text-slate-600">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <code>shared/schemas/farm.schema.json</code>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <code>shared/schemas/crop.schema.json</code>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <code>shared/schemas/climate.schema.json</code> (Mod 02)
                </li>
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center text-blue-700 mb-2">
                <MapPin className="w-5 h-5" />
              </div>
              <CardTitle>Location Intelligence</CardTitle>
              <CardDescription>
                Map coordinate engine and parcel boundary foundation
              </CardDescription>
            </CardHeader>
            <CardContent className="text-sm text-slate-600 space-y-2">
              <p>Verified Reference Location: Peshawar Valley (34.0151° N, 71.5249° E).</p>
              <p>Leaflet & GeoJSON coordinate structures primed for Phase 3 polygon drawing.</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center text-purple-700 mb-2">
                <Sparkles className="w-5 h-5" />
              </div>
              <CardTitle>Multilingual System</CardTitle>
              <CardDescription>
                RTL & LTR language architecture configured
              </CardDescription>
            </CardHeader>
            <CardContent className="text-sm text-slate-600 space-y-2">
              <p>Verified native support for English & Urdu.</p>
              <p>Pashto fallback architecture configured with first-class RTL text conversation.</p>
            </CardContent>
          </Card>
        </div>

        {/* Demo Reference Farm Card */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 mb-4">
            <div>
              <span className="text-xs uppercase tracking-wider font-semibold text-emerald-600">
                Baseline Demo Profile
              </span>
              <h3 className="text-xl font-bold text-slate-900 mt-1">Peshawar Valley Agro Research Parcel</h3>
              <p className="text-sm text-slate-500">ID: farm-peshawar-001 • Khyber Pakhtunkhwa, Pakistan</p>
            </div>
            <div className="mt-4 sm:mt-0">
              <Button variant="outline" size="sm">
                View Climate Link
              </Button>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-slate-500 block text-xs">Latitude / Longitude</span>
              <span className="font-medium text-slate-800">34.0151° N, 71.5249° E</span>
            </div>
            <div>
              <span className="text-slate-500 block text-xs">Total Area</span>
              <span className="font-medium text-slate-800">12.5 Hectares (~31 Acres)</span>
            </div>
            <div>
              <span className="text-slate-500 block text-xs">Soil & Irrigation</span>
              <span className="font-medium text-slate-800">Alluvial Clay • Canal Irrigated</span>
            </div>
            <div>
              <span className="text-slate-500 block text-xs">Primary Seasons</span>
              <span className="font-medium text-slate-800">Kharif (Maize) / Rabi (Wheat)</span>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
