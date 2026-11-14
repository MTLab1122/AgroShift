"use client";

import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Polygon, useMapEvents } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Button } from "@/components/ui/button";
import { MapPin, Trash2, CheckCircle2, AlertCircle } from "lucide-react";

// Fix standard Leaflet default icon paths in Next.js bundle
const customIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

interface InteractiveMapProps {
  initialLat?: number;
  initialLng?: number;
  initialBoundary?: number[][]; // [[lng, lat], ...]
  onLocationChange?: (lat: number, lng: number) => void;
  onBoundaryChange?: (coords: number[][], estimatedHectares: number) => void;
  readOnly?: boolean;
}

// Approximate polygon area using Spherical Excess (Geodesic approximation)
function calculatePolygonAreaHectares(coords: [number, number][]): number {
  if (coords.length < 3) return 0;
  const radius = 6378137; // Earth radius in meters
  let area = 0;

  for (let i = 0; i < coords.length; i++) {
    const j = (i + 1) % coords.length;
    const lat1 = (coords[i][0] * Math.PI) / 180;
    const lat2 = (coords[j][0] * Math.PI) / 180;
    const lon1 = (coords[i][1] * Math.PI) / 180;
    const lon2 = (coords[j][1] * Math.PI) / 180;
    area += (lon2 - lon1) * (2 + Math.sin(lat1) + Math.sin(lat2));
  }
  area = Math.abs((area * radius * radius) / 2.0);
  // Convert square meters to hectares (1 ha = 10,000 sq m)
  return Math.round((area / 10000) * 100) / 100;
}

// Map Event click listener component
function MapEventsHandler({
  mode,
  onMapClick,
}: {
  mode: "pin" | "draw" | "idle";
  onMapClick: (lat: number, lng: number) => void;
}) {
  useMapEvents({
    click(e) {
      if (mode !== "idle") {
        onMapClick(e.latlng.lat, e.latlng.lng);
      }
    },
  });
  return null;
}

export function FarmMap({
  initialLat = 34.0151,
  initialLng = 71.5249,
  initialBoundary,
  onLocationChange,
  onBoundaryChange,
  readOnly = false,
}: InteractiveMapProps) {
  const [position, setPosition] = useState<[number, number]>([initialLat, initialLng]);
  const [mode, setMode] = useState<"idle" | "pin" | "draw">("idle");
  // Boundary points stored as [lat, lng] for Leaflet Polygon rendering
  const [polygonPoints, setPolygonPoints] = useState<[number, number][]>(() => {
    if (initialBoundary && initialBoundary.length >= 3) {
      return initialBoundary.map((pt) => [pt[1], pt[0]] as [number, number]);
    }
    return [];
  });
  const [estimatedHectares, setEstimatedHectares] = useState<number>(() =>
    initialBoundary ? calculatePolygonAreaHectares(initialBoundary.map(p => [p[1], p[0]])) : 0
  );

  useEffect(() => {
    setPosition([initialLat, initialLng]);
  }, [initialLat, initialLng]);

  const handleMapClick = (lat: number, lng: number) => {
    if (mode === "pin") {
      const roundedLat = Math.round(lat * 10000) / 10000;
      const roundedLng = Math.round(lng * 10000) / 10000;
      setPosition([roundedLat, roundedLng]);
      onLocationChange?.(roundedLat, roundedLng);
    } else if (mode === "draw") {
      const newPoints: [number, number][] = [...polygonPoints, [lat, lng]];
      setPolygonPoints(newPoints);
      if (newPoints.length >= 3) {
        const area = calculatePolygonAreaHectares(newPoints);
        setEstimatedHectares(area);
        // GeoJSON uses [longitude, latitude] format
        const geoJsonCoords = [...newPoints, newPoints[0]].map((pt) => [pt[1], pt[0]]);
        onBoundaryChange?.(geoJsonCoords, area);
      }
    }
  };

  const handleClearPolygon = () => {
    setPolygonPoints([]);
    setEstimatedHectares(0);
    onBoundaryChange?.([], 0);
  };

  const estimatedAcres = Math.round(estimatedHectares * 2.47105 * 10) / 10;

  return (
    <div className="flex flex-col space-y-3">
      {/* Map Controls */}
      {!readOnly && (
        <div className="flex flex-wrap items-center justify-between gap-2 bg-slate-100 p-2.5 rounded-lg border border-slate-200">
          <div className="flex items-center gap-2">
            <Button
              type="button"
              size="sm"
              variant={mode === "pin" ? "default" : "outline"}
              onClick={() => setMode(mode === "pin" ? "idle" : "pin")}
              className={mode === "pin" ? "bg-forest-700 hover:bg-forest-800" : ""}
            >
              <MapPin className="w-4 h-4 mr-1.5" />
              {mode === "pin" ? "Click Map to Place Pin" : "Set Pin Location"}
            </Button>

            <Button
              type="button"
              size="sm"
              variant={mode === "draw" ? "default" : "outline"}
              onClick={() => setMode(mode === "draw" ? "idle" : "draw")}
              className={mode === "draw" ? "bg-agrigreen-600 hover:bg-agrigreen-700" : ""}
            >
              <CheckCircle2 className="w-4 h-4 mr-1.5" />
              {mode === "draw" ? "Click to Add Corners" : "Draw Boundary"}
            </Button>

            {polygonPoints.length > 0 && (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={handleClearPolygon}
                className="text-red-600 hover:bg-red-50 hover:text-red-700"
              >
                <Trash2 className="w-4 h-4 mr-1" />
                Clear Polygon
              </Button>
            )}
          </div>

          {/* Area Metric Badge */}
          {estimatedHectares > 0 && (
            <div className="text-xs bg-white px-3 py-1.5 rounded-md border border-slate-200 font-medium text-slate-700 flex items-center gap-1.5">
              <span className="text-slate-400">Estimated Area:</span>
              <strong className="text-forest-800">{estimatedHectares} ha</strong>
              <span className="text-slate-400">({estimatedAcres} acres)</span>
            </div>
          )}
        </div>
      )}

      {/* Notice on Area Estimation */}
      <div className="text-[11px] text-slate-500 flex items-center gap-1.5 px-1">
        <AlertCircle className="w-3.5 h-3.5 text-amber-500 shrink-0" />
        <span>
          Polygon area is an estimate derived from satellite coordinates for regional modeling, not an official land survey.
        </span>
      </div>

      {/* Map Leaflet Canvas */}
      <div className="h-[360px] w-full rounded-xl overflow-hidden border border-slate-300 shadow-inner relative">
        <MapContainer
          center={position}
          zoom={13}
          scrollWheelZoom={false}
          className="h-full w-full"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          <MapEventsHandler mode={mode} onMapClick={handleMapClick} />

          {/* Location Marker */}
          <Marker position={position} icon={customIcon} />

          {/* Drawn Boundary Polygon */}
          {polygonPoints.length >= 3 && (
            <Polygon
              positions={polygonPoints}
              pathOptions={{
                color: "#183f2d",
                fillColor: "#48a94c",
                fillOpacity: 0.35,
                weight: 2,
              }}
            />
          )}
        </MapContainer>
      </div>

      {/* Coordinate Summary */}
      <div className="flex items-center justify-between text-xs text-slate-600 bg-white p-2 rounded-lg border border-slate-200">
        <div>
          <span className="text-slate-400 mr-1">Pin Latitude:</span>
          <strong>{position[0]}° N</strong>
        </div>
        <div>
          <span className="text-slate-400 mr-1">Pin Longitude:</span>
          <strong>{position[1]}° E</strong>
        </div>
        <div>
          <span className="text-slate-400 mr-1">Boundary Points:</span>
          <strong>{polygonPoints.length} vertices</strong>
        </div>
      </div>
    </div>
  );
}
