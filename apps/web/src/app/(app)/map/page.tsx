"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Topbar } from "@/components/Topbar";
import { MapPanel } from "@/components/MapPanel";
import { RiskBadge } from "@/components/RiskBadge";
import { LoadingState, ErrorState } from "@/components/States";
import { api, ApiError } from "@/lib/api";
import type { LocationIntelligence, MapFeature } from "@/lib/types";

const LAYERS: { key: string; label: string; color: string }[] = [
  { key: "incident", label: "Incidents / Hotspots", color: "#c33f2e" },
  { key: "water_body", label: "Water Bodies", color: "#1d6fa5" },
  { key: "protected_area", label: "Protected Areas", color: "#1a7f4f" },
  { key: "forest_reserve", label: "Forest Reserves", color: "#3f7d3f" },
  { key: "ai_detection", label: "AI-Detected Changes", color: "#7a3fc9" },
];

export default function MapPage() {
  const [features, setFeatures] = useState<MapFeature[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeLayers, setActiveLayers] = useState<Set<string>>(new Set(LAYERS.map((l) => l.key)));
  const [selected, setSelected] = useState<MapFeature | null>(null);
  const [intelligence, setIntelligence] = useState<LocationIntelligence | null>(null);
  const [loadingIntel, setLoadingIntel] = useState(false);

  useEffect(() => {
    api
      .get<MapFeature[]>("/api/map/features")
      .then(setFeatures)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load map data"));
  }, []);

  function toggleLayer(key: string) {
    setActiveLayers((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  async function loadIntelligence(lat: number, lon: number) {
    setLoadingIntel(true);
    setIntelligence(null);
    try {
      const data = await api.get<LocationIntelligence>(`/api/location-intelligence?lat=${lat}&lon=${lon}`);
      setIntelligence(data);
    } catch {
      setIntelligence(null);
    } finally {
      setLoadingIntel(false);
    }
  }

  function handleFeatureClick(feature: MapFeature) {
    setSelected(feature);
    loadIntelligence(feature.latitude, feature.longitude);
  }

  function handleMapClick(lat: number, lon: number) {
    setSelected(null);
    loadIntelligence(lat, lon);
  }

  const filtered = useMemo(() => features || [], [features]);

  return (
    <>
      <Topbar title="Geospatial Intelligence" />
      <div className="flex-1 flex min-h-0">
        <div className="flex-1 relative">
          {error && (
            <div className="absolute inset-0 flex items-center justify-center bg-background z-10">
              <ErrorState detail={error} />
            </div>
          )}
          {!features && !error && (
            <div className="absolute inset-0 flex items-center justify-center bg-background z-10">
              <LoadingState label="Loading map data…" />
            </div>
          )}
          {features && (
            <MapPanel
              features={filtered}
              activeLayers={activeLayers}
              onFeatureClick={handleFeatureClick}
              onMapClick={handleMapClick}
              heightClass="h-full"
            />
          )}

          <div className="absolute top-4 left-4 bg-surface border border-border rounded-lg shadow-md p-3 space-y-1.5 z-10">
            <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Layers</p>
            {LAYERS.map((layer) => (
              <label key={layer.key} className="flex items-center gap-2 text-xs cursor-pointer">
                <input
                  type="checkbox"
                  checked={activeLayers.has(layer.key)}
                  onChange={() => toggleLayer(layer.key)}
                  className="accent-navy-700"
                />
                <span className="w-2 h-2 rounded-full" style={{ background: layer.color }} />
                {layer.label}
              </label>
            ))}
          </div>
        </div>

        <aside className="w-96 shrink-0 border-l border-border bg-surface overflow-y-auto">
          {!selected && !intelligence && !loadingIntel && (
            <div className="p-6 text-sm text-slate-400">
              Click a hotspot marker or any point on the map to view Location Intelligence for that area.
            </div>
          )}
          {loadingIntel && <LoadingState label="Analyzing location…" />}
          {intelligence && !loadingIntel && (
            <div className="p-5 space-y-4">
              <div>
                <h2 className="text-sm font-semibold text-navy-900">LOCATION INTELLIGENCE</h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  {intelligence.latitude.toFixed(4)}, {intelligence.longitude.toFixed(4)}
                </p>
                {selected && (
                  <Link href={`/incidents/${selected.id}`} className="text-xs text-navy-700 hover:underline mt-1 inline-block">
                    Open incident record →
                  </Link>
                )}
              </div>

              <div className="flex items-center gap-2">
                {intelligence.risk_category && (
                  <RiskBadge category={intelligence.risk_category} score={intelligence.risk_score} />
                )}
                <span className="text-xs text-slate-500">Trend: {intelligence.risk_trend}</span>
              </div>

              <dl className="text-xs space-y-2">
                <Row label="Region" value={intelligence.region || "—"} />
                <Row label="District" value={intelligence.district || "—"} />
                <Row
                  label="Nearest water body"
                  value={
                    intelligence.nearest_water_body_name
                      ? `${intelligence.nearest_water_body_name} (${intelligence.nearest_water_body_distance_km} km)`
                      : "—"
                  }
                />
                <Row
                  label="Nearest protected area"
                  value={
                    intelligence.nearest_protected_area_name
                      ? `${intelligence.nearest_protected_area_name} (${intelligence.nearest_protected_area_distance_km} km)`
                      : "—"
                  }
                />
                <Row label="Historical incidents (5km)" value={String(intelligence.historical_incident_count)} />
                <Row label="AI detections (5km)" value={String(intelligence.ai_detection_count)} />
                <Row label="Human-verified incidents (5km)" value={String(intelligence.human_verified_incident_count)} />
                <Row label="Last field verification" value={intelligence.last_field_verification?.slice(0, 10) || "None recorded"} />
              </dl>

              <div className="rounded-md bg-navy-950 text-white p-3">
                <p className="text-[11px] uppercase tracking-wide text-slate-400 mb-1">Recommended next step</p>
                <p className="text-sm font-medium">{intelligence.recommended_action}</p>
                <p className="text-[10px] text-slate-400 mt-1.5">
                  AI-generated operational suggestion for human review — not an autonomous instruction.
                </p>
              </div>
            </div>
          )}
        </aside>
      </div>
    </>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <dt className="text-slate-400 shrink-0">{label}</dt>
      <dd className="text-navy-900 font-medium text-right">{value}</dd>
    </div>
  );
}
