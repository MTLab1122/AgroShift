import React from 'react';
import { Satellite, ShieldCheck, Activity, Globe } from 'lucide-react';

export default function Header({ health, dataMode }) {
  const isHealthy = health?.status === 'healthy';

  return (
    <header className="glass-card mb-6 px-6 py-4 flex flex-wrap items-center justify-between gap-4 border-b border-slate-800">
      <div className="flex items-center gap-3">
        <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400">
          <Satellite size={28} className="animate-pulse" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              AgroShift
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-mono border border-emerald-500/40">
                NASA Space Apps 2026
              </span>
            </h1>
          </div>
          <p className="text-xs text-slate-400">
            Team InCir (Innovation Circle) • Abasyn University Peshawar • Adapting Farms with NASA Data
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3 text-xs">
        {/* System Health Indicator */}
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 font-mono">
          <Activity size={14} className={isHealthy ? "text-emerald-400" : "text-amber-400"} />
          <span>Backend:</span>
          <span className={isHealthy ? "text-emerald-400 font-semibold" : "text-amber-400 font-semibold"}>
            {isHealthy ? "ONLINE (FastAPI)" : "CHECKING..."}
          </span>
        </div>

        {/* Data Mode Indicator */}
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 font-mono">
          <Globe size={14} className={dataMode === 'live' ? "text-cyan-400" : "text-amber-400"} />
          <span className="text-slate-400">Mode:</span>
          <span className={dataMode === 'live' ? "text-cyan-300 font-semibold" : "text-amber-300 font-semibold"}>
            {dataMode === 'live' ? "LIVE NASA POWER" : "DEMO FALLBACK"}
          </span>
        </div>

        {/* Scientific Integrity Tag */}
        <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-950/40 border border-emerald-800/40 text-emerald-300 font-mono">
          <ShieldCheck size={14} />
          <span>Zero-Fabrication Enforced</span>
        </div>
      </div>
    </header>
  );
}
