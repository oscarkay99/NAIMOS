"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Topbar } from "@/components/Topbar";
import { MapPanel, SATELLITE_STYLE } from "@/components/MapPanel";
import { RiskBadge } from "@/components/RiskBadge";
import { LoadingState } from "@/components/States";
import { api, ApiError } from "@/lib/api";
import type { Incident, MapFeature, SatelliteHistoryEntry, SatelliteScanResult } from "@/lib/types";

export default function SatelliteMonitoringPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [lat, setLat] = useState(5.32);
  const [lon, setLon] = useState(-2.227);
  const [pin, setPin] = useState<{ latitude: number; longitude: number } | null>({ latitude: 5.32, longitude: -2.227 });
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState<SatelliteScanResult | null>(null);
  const [history, setHistory] = useState<SatelliteHistoryEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<Incident[]>("/api/incidents?limit=50").then(setIncidents).catch(() => {});
  }, []);

  useEffect(() => {
    loadHistory(lat, lon);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadHistory(scanLat: number, scanLon: number) {
    try {
      const h = await api.get<SatelliteHistoryEntry[]>(`/api/satellite/history?lat=${scanLat}&lon=${scanLon}&radius_km=5`);
      setHistory(h);
    } catch {
      setHistory([]);
    }
  }

  function selectAoi(newLat: number, newLon: number) {
    setLat(newLat);
    setLon(newLon);
    setPin({ latitude: newLat, longitude: newLon });
    setResult(null);
    loadHistory(newLat, newLon);
  }

  async function runScan() {
    setScanning(true);
    setError(null);
    try {
      const r = await api.post<SatelliteScanResult>("/api/satellite/scan", { latitude: lat, longitude: lon });
      setResult(r);
      loadHistory(lat, lon);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to run change-detection scan");
    } finally {
      setScanning(false);
    }
  }

  const historyFeatures: MapFeature[] = history.map((h) => ({
    id: h.id,
    layer: "ai_detection",
    name: `${h.detection_type.replaceAll("_", " ")} (${Math.round(h.confidence * 100)}%)`,
    latitude: h.latitude,
    longitude: h.longitude,
    status: h.review_status,
    risk_score: null,
    risk_category: null,
  }));

  return (
    <>
      <Topbar title="Satellite Monitoring" />
      <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-navy-950 text-white rounded-lg p-4 text-xs leading-relaxed">
            <strong>How this works:</strong> the imagery below is a real, live satellite view of this location
            (Esri World Imagery, current pass only - no historical archive). Running a scan simulates an AI
            change-detection pass comparing a baseline and latest observation and writes a real detection record
            that flows through the same risk engine, map, and audit log as any other AI signal. Connecting a real
            time-series provider (Sentinel Hub / Google Earth Engine) would replace only the simulated comparison
            step below - everything downstream already works as shown.
          </div>

          <div className="bg-surface border border-border rounded-lg p-4">
            <div className="flex flex-wrap items-end gap-3 mb-3">
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Jump to known hotspot</label>
                <select
                  onChange={(e) => {
                    const inc = incidents.find((i) => i.id === e.target.value);
                    if (inc) selectAoi(inc.latitude, inc.longitude);
                  }}
                  className="rounded-md border border-border px-3 py-2 text-sm"
                  defaultValue=""
                >
                  <option value="" disabled>
                    Select an incident…
                  </option>
                  {incidents.map((i) => (
                    <option key={i.id} value={i.id}>
                      {i.reference_number} - {i.title}
                    </option>
                  ))}
                </select>
              </div>
              <p className="text-xs text-slate-400">or click anywhere on the imagery to choose an AOI</p>
            </div>

            <MapPanel
              features={historyFeatures}
              onMapClick={selectAoi}
              pin={pin}
              style={SATELLITE_STYLE}
              center={[lon, lat]}
              zoom={13}
              heightClass="h-[420px]"
            />

            <div className="flex items-center justify-between mt-3">
              <p className="text-xs text-slate-400 font-mono">
                AOI: {lat.toFixed(4)}, {lon.toFixed(4)}
              </p>
              <button
                onClick={runScan}
                disabled={scanning}
                className="rounded-md bg-navy-800 text-white text-sm font-medium px-4 py-2 hover:bg-navy-700 disabled:opacity-50"
              >
                {scanning ? "Analyzing satellite imagery…" : "Run AI Change Detection Scan"}
              </button>
            </div>
            {error && <p className="text-xs text-red-600 mt-2">{error}</p>}
          </div>

          {history.length > 0 && (
            <div className="bg-surface border border-border rounded-lg p-4">
              <h3 className="text-sm font-semibold text-navy-900 mb-3">Detection History for this AOI</h3>
              <div className="space-y-2">
                {history.map((h) => (
                  <div key={h.id} className="flex items-center justify-between text-xs border-b border-border pb-2">
                    <div>
                      <p className="font-medium text-navy-900">{h.detection_type.replaceAll("_", " ")}</p>
                      <p className="text-slate-400">{h.observation_date.slice(0, 10)} · {h.estimated_area_hectares} ha</p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold">{Math.round(h.confidence * 100)}%</p>
                      <p className="text-slate-400">{h.review_status}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div>
          {scanning && <LoadingState label="Analyzing before/after imagery…" />}
          {!scanning && !result && (
            <div className="bg-surface border border-dashed border-border rounded-lg p-6 text-xs text-slate-400">
              Select an AOI and run a scan to see the AI-generated risk assessment.
            </div>
          )}
          {result && !scanning && <DetectedCard result={result} />}
        </div>
      </div>
    </>
  );
}

function DetectedCard({ result }: { result: SatelliteScanResult }) {
  const isElevated = result.risk_score >= 41;
  return (
    <div className={`rounded-lg border p-5 space-y-4 ${isElevated ? "border-risk-high bg-red-50" : "border-border bg-surface"}`}>
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-wide text-risk-high">
          {isElevated ? "HIGH-RISK AREA DETECTED" : "Area scanned - low signal"}
        </p>
        <p className="text-xs text-slate-500 mt-1">AI-generated · requires field verification</p>
      </div>

      <div className="flex items-center gap-2">
        <RiskBadge category={result.risk_category} score={result.risk_score} />
      </div>

      <dl className="text-xs space-y-2">
        <Row label="Location" value={[result.district, result.region].filter(Boolean).join(", ") || "Unknown"} />
        <Row label="Coordinates" value={`${result.latitude.toFixed(4)}, ${result.longitude.toFixed(4)}`} />
        <Row label="Detected change" value={`${result.detection_type.replaceAll("_", " ")} · ${result.estimated_area_hectares} ha`} />
        <Row label="Confidence" value={`${Math.round(result.confidence * 100)}%`} />
        <Row
          label="First detected"
          value={result.first_detected_days_ago === 0 ? "Just now (first pass)" : `${result.first_detected_days_ago} days ago`}
        />
        <Row
          label="River proximity"
          value={result.nearest_water_body ? `${result.nearest_water_body.name} · ${result.nearest_water_body.distance_km} km` : "None nearby"}
        />
        <Row
          label="Forest/protected area proximity"
          value={
            result.nearest_protected_area
              ? `${result.nearest_protected_area.name} · ${result.nearest_protected_area.distance_km} km`
              : "None nearby"
          }
        />
      </dl>

      <div className="rounded-md bg-navy-950 text-white p-3">
        <p className="text-[11px] uppercase tracking-wide text-slate-400 mb-1">Recommended action</p>
        <p className="text-sm font-medium">{result.recommended_action}</p>
      </div>

      <div className="text-[11px] text-slate-500 space-y-1 border-t border-border pt-3">
        <p>Baseline pass: {result.previous_observation.acquisition_date.slice(0, 10)} ({result.previous_observation.provider})</p>
        <p>Latest pass: {result.current_observation.acquisition_date.slice(0, 10)} ({result.current_observation.provider})</p>
      </div>

      <p className="text-[10px] text-slate-400">{result.disclaimer}</p>

      <Link
        href={`/field?lat=${result.latitude}&lon=${result.longitude}`}
        className="block text-center rounded-md bg-navy-800 text-white text-xs font-medium py-2 hover:bg-navy-700"
      >
        Open Field Reporting for this location →
      </Link>
    </div>
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
