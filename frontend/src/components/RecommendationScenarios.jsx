import React from 'react';
import { Award, Calendar, CheckCircle, AlertTriangle, ShieldCheck } from 'lucide-react';

export default function RecommendationScenarios({ scenarios, limitations }) {
  if (!scenarios) return null;

  const scenarioList = [
    { key: 'pulse_inclusive', scenario: scenarios.pulse_inclusive, badge: 'Recommended (Pulse)', badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' },
    { key: 'soil_cover', scenario: scenarios.soil_cover, badge: 'Climate Resilient (Cover)', badgeColor: 'bg-teal-500/20 text-teal-300 border-teal-500/40' },
    { key: 'baseline', scenario: scenarios.baseline, badge: 'Current Practice', badgeColor: 'bg-slate-700/40 text-slate-300 border-slate-600/40' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Award size={22} className="text-emerald-400" />
            Decision Support: Priority-Scored Crop Rotation Pathways (Module 03)
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Composite Score: S = 0.35 × Climate + 0.25 × Water + 0.25 × Soil + 0.15 × Market Resilience
          </p>
        </div>
      </div>

      {/* 3 Scenario Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {scenarioList.map(({ key, scenario, badge, badgeColor }) => {
          if (!scenario) return null;
          const { score, score_breakdown, crop_sequence, seasonal_calendar, rationale, benefits, risks } = scenario;

          return (
            <div
              key={key}
              className={`glass-card p-5 flex flex-col justify-between relative overflow-hidden transition-all duration-300 hover:border-slate-600 ${
                key === 'pulse_inclusive' ? 'border-emerald-500/40 glow-emerald' : ''
              }`}
            >
              {/* Header Badge & Title */}
              <div>
                <div className="flex items-center justify-between gap-2 mb-3">
                  <span className={`text-[11px] font-mono px-2.5 py-0.5 rounded-full border ${badgeColor}`}>
                    {badge}
                  </span>
                  <div className="flex items-baseline gap-1">
                    <span className="text-xs text-slate-400">Score:</span>
                    <span className="text-xl font-bold font-mono text-emerald-400">
                      {score?.toFixed(1) || 'N/A'}
                    </span>
                    <span className="text-[10px] text-slate-500">/100</span>
                  </div>
                </div>

                <h3 className="text-base font-semibold text-white mb-2 leading-snug">
                  {scenario.title}
                </h3>

                {/* Crop Sequence Pill Strip */}
                <div className="flex items-center gap-1.5 mb-4 flex-wrap">
                  {crop_sequence.map((crop, idx) => (
                    <React.Fragment key={idx}>
                      <span className="text-xs font-mono font-medium px-2 py-0.5 rounded-md bg-slate-800 text-slate-200 border border-slate-700">
                        {crop.toUpperCase()}
                      </span>
                      {idx < crop_sequence.length - 1 && (
                        <span className="text-xs text-slate-500 font-bold">→</span>
                      )}
                    </React.Fragment>
                  ))}
                </div>

                {/* Score Breakdown Bars */}
                <div className="bg-slate-900/90 rounded-xl p-3 border border-slate-800 mb-4 space-y-2 text-xs">
                  <div className="text-[11px] font-medium text-slate-400 pb-1 border-b border-slate-800/80">
                    Factor Breakdown:
                  </div>

                  <div>
                    <div className="flex justify-between text-[11px] mb-0.5">
                      <span className="text-slate-400">Climate Fit (C) [35%]</span>
                      <span className="font-mono text-cyan-400 font-semibold">{score_breakdown.climate_suitability}%</span>
                    </div>
                    <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                      <div className="bg-cyan-500 h-full rounded-full" style={{ width: `${score_breakdown.climate_suitability}%` }} />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-[11px] mb-0.5">
                      <span className="text-slate-400">Water Efficiency (W) [25%]</span>
                      <span className="font-mono text-blue-400 font-semibold">{score_breakdown.water_efficiency}%</span>
                    </div>
                    <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                      <div className="bg-blue-500 h-full rounded-full" style={{ width: `${score_breakdown.water_efficiency}%` }} />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-[11px] mb-0.5">
                      <span className="text-slate-400">Soil Health &amp; N (D) [25%]</span>
                      <span className="font-mono text-emerald-400 font-semibold">{score_breakdown.soil_health_benefit}%</span>
                    </div>
                    <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                      <div className="bg-emerald-500 h-full rounded-full" style={{ width: `${score_breakdown.soil_health_benefit}%` }} />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-[11px] mb-0.5">
                      <span className="text-slate-400">Market Resilience (P) [15%]</span>
                      <span className="font-mono text-amber-400 font-semibold">{score_breakdown.market_resilience}%</span>
                    </div>
                    <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                      <div className="bg-amber-500 h-full rounded-full" style={{ width: `${score_breakdown.market_resilience}%` }} />
                    </div>
                  </div>
                </div>

                {/* Seasonal Calendar Window */}
                <div className="mb-4 text-xs">
                  <div className="text-[11px] font-medium text-slate-400 mb-1.5 flex items-center gap-1">
                    <Calendar size={12} className="text-slate-400" />
                    Seasonal Timeline:
                  </div>
                  <div className="space-y-1.5">
                    {seasonal_calendar.map((cal, i) => (
                      <div key={i} className="flex justify-between items-center px-2.5 py-1.5 bg-slate-900/60 rounded-md border border-slate-800/60 text-[11px] font-mono">
                        <span className="text-white font-medium capitalize">{cal.crop}</span>
                        <span className="text-slate-400">{cal.start_month} – {cal.harvest_month} ({cal.duration_days}d)</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Key Benefits & Risks */}
                <div className="space-y-2 text-xs mb-3">
                  <div>
                    <span className="text-[11px] font-semibold text-emerald-400 flex items-center gap-1 mb-1">
                      <CheckCircle size={12} /> Key Agronomic Benefits:
                    </span>
                    <ul className="list-disc list-inside space-y-0.5 text-slate-300 text-[11px]">
                      {benefits.slice(0, 2).map((b, idx) => (
                        <li key={idx} className="line-clamp-2">{b}</li>
                      ))}
                    </ul>
                  </div>

                  <div>
                    <span className="text-[11px] font-semibold text-amber-400 flex items-center gap-1 mb-1">
                      <AlertTriangle size={12} /> Management Risks:
                    </span>
                    <ul className="list-disc list-inside space-y-0.5 text-slate-300 text-[11px]">
                      {risks.slice(0, 2).map((r, idx) => (
                        <li key={idx} className="line-clamp-2">{r}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>

              {/* Rationale Footer */}
              <div className="pt-3 border-t border-slate-800/80 text-[11px] text-slate-400 italic">
                &quot;{rationale[0]}&quot;
              </div>
            </div>
          );
        })}
      </div>

      {/* Decision Support Limitations Banner */}
      {limitations && limitations.length > 0 && (
        <div className="glass-card p-4 border-amber-500/30 bg-amber-950/10 rounded-xl text-xs text-amber-200/90 space-y-1">
          <strong className="text-amber-300 font-semibold flex items-center gap-1 mb-1">
            <ShieldCheck size={14} /> Decision-Support Verification Caveat:
          </strong>
          <ul className="list-disc list-inside space-y-0.5 text-[11px]">
            {limitations.map((lim, idx) => (
              <li key={idx}>{lim}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
