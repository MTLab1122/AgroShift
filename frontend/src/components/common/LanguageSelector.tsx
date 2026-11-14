"use client";

import React from "react";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { Globe } from "lucide-react";

export function LanguageSelector() {
  const { locale, setLocale } = useLanguage();

  return (
    <div className="flex items-center space-x-2 rtl:space-x-reverse bg-slate-100 rounded-lg p-1 border border-slate-200">
      <Globe className="w-4 h-4 text-slate-500 mx-1.5" />
      <button
        type="button"
        onClick={() => setLocale("en")}
        className={`px-2.5 py-1 text-xs font-medium rounded-md transition ${
          locale === "en"
            ? "bg-white text-emerald-700 shadow-sm font-semibold"
            : "text-slate-600 hover:text-slate-900"
        }`}
      >
        English
      </button>
      <button
        type="button"
        onClick={() => setLocale("ur")}
        className={`px-2.5 py-1 text-xs font-medium rounded-md transition ${
          locale === "ur"
            ? "bg-white text-emerald-700 shadow-sm font-semibold"
            : "text-slate-600 hover:text-slate-900"
        }`}
      >
        اردو
      </button>
      <button
        type="button"
        onClick={() => setLocale("ps")}
        className={`px-2.5 py-1 text-xs font-medium rounded-md transition ${
          locale === "ps"
            ? "bg-white text-emerald-700 shadow-sm font-semibold"
            : "text-slate-600 hover:text-slate-900"
        }`}
      >
        پښتو
      </button>
    </div>
  );
}
