"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { SidebarLayout } from "@/components/layout/SidebarLayout";
import { ConversationalAssistant } from "@/components/assistant/ConversationalAssistant";
import { FarmProfile } from "@/types/farm";
import { farmApiService, getApiErrorMessage } from "@/lib/api/farmApi";
import { AlertCircle, ArrowLeft, CheckCircle2 } from "lucide-react";
import Link from "next/link";

export default function NewFarmRegistrationPage() {
  const router = useRouter();
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  const handleSaveFarm = async (farm: FarmProfile): Promise<boolean> => {
    setIsSaving(true);
    setSaveError(null);
    try {
      const res = await farmApiService.createFarm(farm);
      setSaveSuccessMsg(
        res.message || (res.isDemoData ? "Saved only in this browser." : "Farm profile saved.")
      );
      setTimeout(() => {
        router.push("/farms");
      }, 2000);
      return true;
    } catch (error) {
      setSaveError(getApiErrorMessage(error));
      return false;
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <SidebarLayout>
      <div className="space-y-6 max-w-7xl mx-auto">
        {/* Back Link & Header */}
        <div className="flex items-center justify-between">
          <div>
            <Link
              href="/farms"
              className="text-xs font-semibold text-forest-700 hover:text-forest-900 inline-flex items-center gap-1.5 mb-2"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Farm Dashboard</span>
            </Link>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-forest-950">
              Conversational Farm Registration
            </h1>
            <p className="text-xs sm:text-sm text-slate-500 mt-1">
              Interactive voice and chat intake with boundary mapping and structured parameter extraction
            </p>
          </div>
        </div>

        {/* Success Alert */}
        {saveSuccessMsg && (
          <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-3 text-emerald-900 text-sm">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <span>{saveSuccessMsg} Redirecting to Farm Dashboard...</span>
          </div>
        )}

        {saveError && (
          <div
            role="alert"
            className="p-4 bg-red-50 border border-red-200 rounded-xl flex items-center gap-3 text-red-900 text-sm"
          >
            <AlertCircle className="w-5 h-5 text-red-600 shrink-0" />
            <span>{saveError}</span>
          </div>
        )}

        {/* Conversational Assistant + Interactive Map */}
        <ConversationalAssistant onSaveFarm={handleSaveFarm} isSaving={isSaving} />
      </div>
    </SidebarLayout>
  );
}
