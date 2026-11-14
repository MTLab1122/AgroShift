import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import FarmForm from './components/FarmForm';
import NasaComparisonCard from './components/NasaComparisonCard';
import RecommendationScenarios from './components/RecommendationScenarios';
import { AlertCircle, ShieldAlert } from 'lucide-react';

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');

export default function App() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [recommendationSet, setRecommendationSet] = useState(null);
  const [activeDataMode, setActiveDataMode] = useState('live');

  // Check health on load
  useEffect(() => {
    if (import.meta.env.PROD && !apiBaseUrl) {
      setHealth({ status: 'unconfigured' });
      return;
    }

    fetch(`${apiBaseUrl}/health`)
      .then(res => res.json())
      .then(data => setHealth(data))
      .catch(err => {
        console.warn('Backend offline or health check failed:', err);
        setHealth({ status: 'unavailable' });
      });
  }, []);

  const handleFarmSubmit = async (formData, forceDemo) => {
    if (import.meta.env.PROD && !apiBaseUrl) {
      setError('The API is not configured for this deployment. Set the AGROSHIFT_API_URL repository variable and redeploy.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const queryParams = new URLSearchParams({
        demo: forceDemo ? 'true' : 'false'
      });

      const response = await fetch(`${apiBaseUrl}/api/v1/recommendations/generate?${queryParams.toString()}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || `Request failed with status ${response.status}`);
      }

      setRecommendationSet(data);
      if (data.farm_vs_nasa_comparison?.data_mode) {
        setActiveDataMode(data.farm_vs_nasa_comparison.data_mode);
      }
    } catch (err) {
      console.error('Submission error:', err);
      setError(err.message || 'An unexpected error occurred while contacting AgroShift backend.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between selection:bg-emerald-500 selection:text-white">
      <div className="max-w-7xl mx-auto w-full px-4 sm:px-6 py-6 flex-1">
        {/* Header */}
        <Header health={health} dataMode={activeDataMode} />

        {/* Error Banner */}
        {error && (
          <div className="mb-6 p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 flex items-start gap-3 text-sm">
            <ShieldAlert size={20} className="text-rose-400 shrink-0 mt-0.5" />
            <div>
              <strong className="block font-semibold">NASA Engine API Error:</strong>
              <p>{error}</p>
            </div>
          </div>
        )}

        {/* Input Farm Profile */}
        <FarmForm onSubmit={handleFarmSubmit} loading={loading} />

        {/* Live NASA Comparison Card */}
        {recommendationSet && (
          <>
            <NasaComparisonCard
              comparison={recommendationSet.farm_vs_nasa_comparison}
              generatedAt={recommendationSet.generated_at}
            />

            <RecommendationScenarios
              scenarios={recommendationSet.scenarios}
              limitations={recommendationSet.limitations}
            />
          </>
        )}
      </div>

      {/* Footer */}
      <footer className="mt-12 py-4 border-t border-slate-900 text-center text-xs text-slate-500 font-mono">
        AgroShift © 2026 Team InCir (Innovation Circle) • NASA Space Apps Challenge 2026: Adapting Farms with NASA Data • Zero Synthetic Data Enforced
      </footer>
    </div>
  );
}
