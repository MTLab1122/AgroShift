import React from 'react';
import { CloudRain, Thermometer, ShieldAlert, CheckCircle2, AlertTriangle, Info, Satellite, Radio } from 'lucide-react';

export default function NasaComparisonCard({ comparison, generatedAt }) {
  if (!comparison) return null;

  const {
    observed_rainfall_mm,
    expected_crop_water_need_mm,
    water_balance_status,
    thermal_stress_days,
    irrigation_adequacy_note,
    data_mode
  } = comparison;

  const coveragePct = Math.min(100, Math.round((observed_rainfall_mm / (expected_crop_water_need_mm || 1)) * 100));

  // Status badge styling
  const statusConfig = {
    severe_deficit: {
      label: 'Severe Deficit',
      color: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
      icon: ShieldAlert,
      barColor: 'bg-rose-500'
    },
    moderate_deficit: {
      label: 'Moderate Deficit',
      color: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
      icon: AlertTriangle,
      barColor: 'bg-amber-500'
    },
    balanced: {
      label: 'Balanced Moisture',
      color: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
      icon: CheckCircle2,
      barColor: 'bg-emerald-500'
    },
    excess_moisture: {
      label: 'Excess Moisture',
      color: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40',
      icon: CloudRain,
      barColor: 'bg-cyan-500'
    }
  };

  const currentStatus = statusConfig[water_balance_status] || statusConfig.balanced;
  const StatusIcon = currentStatus.icon;

  return (
    <div className="glass-card p-6 mb-6 glow-cyan border-cyan-500/30">
      {/* Top Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-4 pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-cyan-500/10 border border-cyan-500/30 rounded-lg text-cyan-400">
            <Radio size={18} className="animate-pulse" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-white flex items-center gap-2">
              Farm Inputs vs. Live NASA Observation Comparison
              <span className={`text-xs px-2.5 py-0.5 rounded-full border font-mono ${currentStatus.color} flex items-center gap-1`}>
                <StatusIcon size={12} />
                {currentStatus.label}
              </span>
            </h3>
            <p className="text-xs text-slate-400">
              Diagnostic reconciliation of user crop requirements with NASA POWER reanalysis (MERRA-2/CERES).
            </p>
          </div>
        </div>

        {/* Provenance Badge */}
        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="px-2.5 py-1 rounded-md bg-slate-900 border border-slate-700 text-slate-300">
            Mode: <strong className={data_mode === 'live' ? "text-cyan-400" : "text-amber-400"}>
              {data_mode.toUpperCase()}
            </strong>
          </span>
          <span className="text-slate-500 hidden sm:inline">|</span>
          <span className="text-slate-400 hidden sm:inline">
            Retrieved: {new Date(generatedAt).toLocaleTimeString()}
          </span>
        </div>
      </div>

      {/* Main Metric Gauges */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
        {/* Metric 1: Precipitation vs Crop Demand */}
        <div className="bg-slate-900/80 rounded-xl p-4 border border-slate-800">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span className="flex items-center gap-1.5 font-medium">
              <CloudRain size={14} className="text-cyan-400" />
              Precipitation vs Demand
            </span>
            <span className="font-mono text-cyan-300 font-semibold">{coveragePct}% met by rain</span>
          </div>

          <div className="flex items-baseline gap-2 mb-2">
            <span className="text-2xl font-bold font-mono text-white">
              {observed_rainfall_mm.toFixed(1)}
            </span>
            <span className="text-xs text-slate-400">mm rain / {expected_crop_water_need_mm.toFixed(0)} mm needed</span>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${currentStatus.barColor}`}
              style={{ width: `${Math.max(5, coveragePct)}%` }}
            />
          </div>
        </div>

        {/* Metric 2: Thermal Stress Days */}
        <div className="bg-slate-900/80 rounded-xl p-4 border border-slate-800">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span className="flex items-center gap-1.5 font-medium">
              <Thermometer size={14} className={thermal_stress_days > 0 ? "text-rose-400" : "text-emerald-400"} />
              Thermal Heat-Stress Days
            </span>
            <span className="font-mono text-xs text-slate-500">T2M_MAX &gt; Critical Threshold</span>
          </div>

          <div className="flex items-baseline gap-2">
            <span className={`text-2xl font-bold font-mono ${thermal_stress_days > 0 ? "text-rose-400" : "text-emerald-400"}`}>
              {thermal_stress_days}
            </span>
            <span className="text-xs text-slate-400">
              {thermal_stress_days === 0 ? "No critical heat events recorded" : "Days exceeding crop limit"}
            </span>
          </div>
          <p className="text-[11px] text-slate-500 mt-2">
            Monitored against daily NASA MERRA-2 maximum surface air temperature.
          </p>
        </div>

        {/* Metric 3: Water Balance Status */}
        <div className="bg-slate-900/80 rounded-xl p-4 border border-slate-800 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span className="font-medium">Water Balance Assessment</span>
            <span className="font-mono text-[11px] text-slate-400">Irrigation Reconciled</span>
          </div>
          <div className="my-1">
            <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-md border font-mono ${currentStatus.color}`}>
              <StatusIcon size={14} />
              {currentStatus.label.toUpperCase()}
            </span>
          </div>
          <p className="text-[11px] text-slate-400 line-clamp-2">
            Includes declared irrigation infrastructure and water availability quota.
          </p>
        </div>
      </div>

      {/* Narrative Note */}
      <div className="bg-slate-950/60 rounded-xl p-4 border border-slate-800/80 mb-4 text-xs leading-relaxed text-slate-300">
        <strong className="text-white font-medium block mb-1 flex items-center gap-1">
          <Info size={14} className="text-cyan-400" />
          Agronomic Reconciliation Analysis:
        </strong>
        {irrigation_adequacy_note}
      </div>

      {/* Scientific Honesty Disclaimer Banner */}
      <div className="p-3 bg-blue-950/20 border border-blue-900/30 rounded-lg flex items-start gap-2 text-[11px] text-blue-300/90 leading-tight">
        <Satellite size={16} className="text-blue-400 shrink-0 mt-0.5" />
        <div>
          <strong>NASA Earth Observation Provenance Note:</strong> Gridded satellite and assimilation reanalysis data (NASA POWER AG, MERRA-2, CERES) represents regional grid cells (~0.5° × 0.5° ≈ 50 km × 50 km), not direct on-farm in-situ sensor measurements. Use for regional decision support and agro-climatic adaptation planning.
        </div>
      </div>
    </div>
  );
}
