import React, { useState, useEffect } from 'react';
import { MapPin, Sparkles, RefreshCw, Layers, Droplets, BookOpen } from 'lucide-react';

export default function FarmForm({ onSubmit, loading, initialData }) {
  const [registeredFarms, setRegisteredFarms] = useState([]);
  const [formData, setFormData] = useState(initialData || {
    farm_id: 'farm-peshawar-001',
    farm_name: 'Tariq Khan Agro Parcel',
    latitude: 34.0151,
    longitude: 71.5249,
    area_value: 5.0,
    area_unit: 'acres',
    soil_type: 'sandy',
    irrigation_type: 'rain_fed',
    water_availability: 'low',
    current_crop: 'wheat',
    season: 'Rabi',
    crop_history: [
      {
        entry_id: 'hist-01',
        crop_name: 'maize',
        season: 'Kharif',
        year: 2023,
        yield_value: 28.0,
        yield_unit: 'maunds/acre',
        notes: 'Severe heat during silking'
      }
    ]
  });

  const [forceDemo, setForceDemo] = useState(false);

  // Load registered farms on mount
  useEffect(() => {
    fetch('/api/v1/farms')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) setRegisteredFarms(data);
      })
      .catch(err => console.warn('Could not load farms:', err));
  }, []);

  const handleSelectRegisteredFarm = (farmId) => {
    const selected = registeredFarms.find(f => f.farm_id === farmId);
    if (selected) {
      setFormData(selected);
    }
  };

  const handleChange = (e) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'number' ? parseFloat(value) || 0 : value
    }));
  };

  const handleQuickPreset = (presetType) => {
    if (presetType === 'barani') {
      setFormData({
        farm_id: 'farm-peshawar-barani',
        farm_name: 'Peshawar Barani (Rain-fed) Farm',
        latitude: 34.0151,
        longitude: 71.5249,
        area_value: 4.0,
        area_unit: 'acres',
        soil_type: 'sandy',
        irrigation_type: 'rain_fed',
        water_availability: 'low',
        current_crop: 'wheat',
        season: 'Rabi',
        crop_history: [
          { entry_id: 'h1', crop_name: 'maize', season: 'Kharif', year: 2023, yield_value: 28.0, yield_unit: 'maunds/acre', notes: 'Severe heat during silking' },
          { entry_id: 'h2', crop_name: 'wheat', season: 'Rabi', year: 2022, yield_value: 22.0, yield_unit: 'maunds/acre', notes: 'Drought stress' }
        ]
      });
    } else {
      setFormData({
        farm_id: 'farm-peshawar-canal',
        farm_name: 'Peshawar Warsak Canal Farm',
        latitude: 34.0151,
        longitude: 71.5249,
        area_value: 8.0,
        area_unit: 'acres',
        soil_type: 'clay_loam',
        irrigation_type: 'canal',
        water_availability: 'high',
        current_crop: 'wheat',
        season: 'Rabi',
        crop_history: [
          { entry_id: 'h1', crop_name: 'chickpea', season: 'Rabi', year: 2023, yield_value: 18.0, yield_unit: 'maunds/acre', notes: 'Legume break fixed nitrogen' }
        ]
      });
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData, forceDemo);
  };

  return (
    <div className="glass-card p-6 mb-6">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-5 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Layers size={20} className="text-emerald-400" />
            Farm Profile & Location Input (Module 01)
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Submit your parcel coordinates and agricultural practices for live NASA climate cross-comparison.
          </p>
        </div>

        {/* Quick Presets */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 font-mono">Presets:</span>
          <button
            type="button"
            onClick={() => handleQuickPreset('barani')}
            className="text-xs px-3 py-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 transition-all font-mono"
          >
            Peshawar Barani (Dry)
          </button>
          <button
            type="button"
            onClick={() => handleQuickPreset('canal')}
            className="text-xs px-3 py-1.5 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 transition-all font-mono"
          >
            Peshawar Canal (Irrigated)
          </button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Module 01 Farm Selector */}
        {registeredFarms.length > 0 && (
          <div className="p-3 bg-slate-900/90 rounded-xl border border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
            <span className="text-slate-400 font-medium flex items-center gap-1.5">
              <BookOpen size={14} className="text-emerald-400" />
              Load Registered Farm (Module 01):
            </span>
            <div className="flex items-center gap-2 flex-1 max-w-md">
              <select
                value={formData.farm_id}
                onChange={(e) => handleSelectRegisteredFarm(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-emerald-500"
              >
                {registeredFarms.map(f => (
                  <option key={f.farm_id} value={f.farm_id}>
                    {f.farm_name} ({f.soil_type}, {f.irrigation_type})
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}

        {/* Row 1: Coordinates and Name */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Farm Identifier
            </label>
            <input
              type="text"
              name="farm_id"
              value={formData.farm_id}
              onChange={handleChange}
              required
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1 flex items-center gap-1">
              <MapPin size={12} className="text-emerald-400" />
              Latitude (°N)
            </label>
            <input
              type="number"
              step="0.0001"
              name="latitude"
              value={formData.latitude}
              onChange={handleChange}
              min="-90"
              max="90"
              required
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500 font-mono"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1 flex items-center gap-1">
              <MapPin size={12} className="text-cyan-400" />
              Longitude (°E)
            </label>
            <input
              type="number"
              step="0.0001"
              name="longitude"
              value={formData.longitude}
              onChange={handleChange}
              min="-180"
              max="180"
              required
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500 font-mono"
            />
          </div>
        </div>

        {/* Row 2: Crops and Soil */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Current / Target Crop
            </label>
            <select
              name="current_crop"
              value={formData.current_crop}
              onChange={handleChange}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
            >
              <option value="wheat">Wheat (Gandum - Rabi)</option>
              <option value="maize">Maize (Makai - Kharif)</option>
              <option value="rice">Rice (Sholay - Kharif)</option>
              <option value="sugarcane">Sugarcane (Kamand - Annual)</option>
              <option value="mustard">Mustard (Sarson - Rabi)</option>
              <option value="chickpea">Chickpea (Chana - Rabi Legume)</option>
              <option value="lentil">Lentil (Masoor - Rabi Legume)</option>
              <option value="mung_bean">Mung Bean (Moong - Summer Legume)</option>
              <option value="berseem_clover">Berseem Clover (Shaftal - Fodder)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Season
            </label>
            <select
              name="season"
              value={formData.season}
              onChange={handleChange}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
            >
              <option value="Rabi">Rabi (Winter / Spring)</option>
              <option value="Kharif">Kharif (Monsoon / Summer)</option>
              <option value="Zaid">Zaid (Early Summer Catch)</option>
              <option value="Annual">Annual (Cash Crop)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Soil Type
            </label>
            <select
              name="soil_type"
              value={formData.soil_type}
              onChange={handleChange}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
            >
              <option value="loamy">Loamy (Balanced)</option>
              <option value="clay_loam">Clay Loam (Heavy & Rich)</option>
              <option value="sandy">Sandy (Well-Drained / Porous)</option>
              <option value="silty">Silty (Fine Sediment)</option>
              <option value="clay">Clay (Water-Retentive)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Cultivated Area
            </label>
            <div className="flex gap-2">
              <input
                type="number"
                step="0.5"
                min="0.1"
                name="area_value"
                value={formData.area_value}
                onChange={handleChange}
                className="w-2/3 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500 font-mono"
              />
              <select
                name="area_unit"
                value={formData.area_unit}
                onChange={handleChange}
                className="w-1/3 bg-slate-900 border border-slate-700 rounded-lg px-2 py-2 text-xs text-slate-100 focus:outline-none"
              >
                <option value="acres">Acres</option>
                <option value="kanals">Kanals</option>
                <option value="hectares">Ha</option>
              </select>
            </div>
          </div>
        </div>

        {/* Row 3: Irrigation Infrastructure */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1 flex items-center gap-1">
              <Droplets size={12} className="text-cyan-400" />
              Irrigation Infrastructure
            </label>
            <select
              name="irrigation_type"
              value={formData.irrigation_type}
              onChange={handleChange}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
            >
              <option value="canal">Canal (Gravity / Basin)</option>
              <option value="tube_well">Tube-Well (Groundwater)</option>
              <option value="rain_fed">Rain-fed (Barani / Zero Supplemental)</option>
              <option value="drip">Drip / Micro-irrigation</option>
              <option value="sprinkler">Sprinkler</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Water Availability Level
            </label>
            <select
              name="water_availability"
              value={formData.water_availability}
              onChange={handleChange}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
            >
              <option value="high">High (Continuous / Full Quota)</option>
              <option value="medium">Medium (Rotational / Moderate Deficit Risk)</option>
              <option value="low">Low (Restricted Warabandi / Dry Barani)</option>
            </select>
          </div>
        </div>

        {/* Footer controls & submit */}
        <div className="pt-3 border-t border-slate-800 flex flex-wrap items-center justify-between gap-4">
          <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-400 hover:text-slate-200">
            <input
              type="checkbox"
              checked={forceDemo}
              onChange={(e) => setForceDemo(e.target.checked)}
              className="rounded bg-slate-900 border-slate-700 text-emerald-500 focus:ring-0"
            />
            <span>Force Demo Fallback (Offline Sandbox Mode)</span>
          </label>

          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-medium text-sm transition-all shadow-lg shadow-emerald-900/30 disabled:opacity-50"
          >
            {loading ? (
              <>
                <RefreshCw size={16} className="animate-spin" />
                <span>Fetching Live NASA Observations...</span>
              </>
            ) : (
              <>
                <Sparkles size={16} />
                <span>Fetch NASA Data & Generate Recommendations</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
