"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Topbar } from "@/components/Topbar";
import { MetricCard } from "@/components/MetricCard";
import { MapPanel } from "@/components/MapPanel";
import { LoadingState, ErrorState } from "@/components/States";
import { api, ApiError } from "@/lib/api";
import type { MapFeature, NationalHotspot, NationalSituation } from "@/lib/types";

export default function ProNationalSituationPage() {
  const [data, setData] = useState<NationalSituation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<NationalHotspot | null>(null);

  useEffect(() => {
    api
      .get<NationalSituation>("/api/analytics/national-situation")
      .then((d) => {
        setData(d);
        setSelected(d.top_hotspots[0] || null);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load national situation"));
  }, []);

  if (error) {
    return (
      <div className="p-6">
        <ErrorState detail={error} />
      </div>
    );
  }

  if (!data) {
    return (
      <>
        <Topbar title="National Situation Room" />
        <LoadingState />
      </>
    );
  }

  const mapFeatures: MapFeature[] = data.top_hotspots.map((h) => ({
    id: h.incident_id,
    layer: "incident",
    name: `${h.reference_number} - ${h.title}`,
    latitude: h.latitude,
    longitude: h.longitude,
    status: null,
    risk_score: h.risk_score,
    risk_category: null,
  }));

  return (
    <>
      <Topbar title="National Situation Room" />
      <div className="p-6 space-y-6">
        <div className="bg-navy-950 text-white rounded-lg p-4 text-xs leading-relaxed">
          PRO briefing view: &ldquo;What is happening across Ghana right now?&rdquo; Every figure below is a
          real database aggregate, not a projection - use the AI Communications tools to turn this into a
          public-facing statement.
        </div>

        <div>
          <h2 className="text-sm font-semibold text-navy-900 mb-3">National Situation</h2>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
            <MetricCard label="Active Investigations" value={data.active_investigations} />
            <MetricCard label="High-Risk Locations" value={data.high_risk_locations} accent={data.high_risk_locations ? "high" : "default"} />
            <MetricCard label="Field Operations" value={data.field_operations} />
            <MetricCard label="Incidents This Month" value={data.incidents_this_month} />
            <MetricCard label="Water Bodies Affected" value={data.water_bodies_affected} />
            <MetricCard label="Forest Areas Affected" value={data.forest_areas_affected} />
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-navy-900">🚨 Top {data.top_hotspots.length} Emerging Hotspots</h2>
            <Link href="/communications" className="text-xs text-navy-700 font-medium hover:underline">
              Generate communication →
            </Link>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="bg-surface border border-border rounded-lg overflow-hidden">
              <MapPanel
                features={mapFeatures}
                heightClass="h-[420px]"
                onFeatureClick={(f) => {
                  const hotspot = data.top_hotspots.find((h) => h.incident_id === f.id);
                  if (hotspot) setSelected(hotspot);
                }}
              />
            </div>
            <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
              {data.top_hotspots.map((h, i) => (
                <button
                  key={h.incident_id}
                  onClick={() => setSelected(h)}
                  className={`w-full text-left rounded-lg border px-3 py-2.5 transition-colors ${
                    selected?.incident_id === h.incident_id
                      ? "border-navy-700 bg-navy-950/5"
                      : "border-border bg-surface hover:border-navy-300"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-navy-900">
                      Hotspot #{i + 1} · {h.reference_number}
                    </p>
                    <span className="text-xs">{h.priority_emoji} {h.priority_label}</span>
                  </div>
                  <p className="text-xs text-slate-400">{[h.district, h.region].filter(Boolean).join(", ")}</p>
                </button>
              ))}
            </div>
          </div>
        </div>

        {selected && <HotspotDetail hotspot={selected} />}
      </div>
    </>
  );
}

function HotspotDetail({ hotspot }: { hotspot: NationalHotspot }) {
  return (
    <div className="bg-surface border border-border rounded-lg p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-[11px] uppercase tracking-wide text-slate-400 font-medium">Hotspot detail</p>
          <Link href={`/incidents/${hotspot.incident_id}`} className="text-sm font-semibold text-navy-900 hover:underline">
            {hotspot.reference_number} - {hotspot.title}
          </Link>
        </div>
        <span className="text-sm font-medium">{hotspot.priority_emoji} {hotspot.priority_label}</span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs">
        <Field label="Risk" value={`${hotspot.risk_score}/100`} />
        <Field label="Region" value={[hotspot.district, hotspot.region].filter(Boolean).join(", ") || "-"} />
        <Field
          label="Estimated affected area"
          value={hotspot.estimated_affected_area_hectares != null ? `${hotspot.estimated_affected_area_hectares} ha` : "Not yet assessed"}
        />
        <Field
          label="Distance to water"
          value={hotspot.distance_to_water_m != null ? `${Math.round(hotspot.distance_to_water_m)}m (${hotspot.nearest_water_body_name})` : "-"}
        />
        <Field label="Activity change (7d)" value={hotspot.change_pct != null ? `${hotspot.change_pct > 0 ? "+" : ""}${hotspot.change_pct}%` : "New"} />
        <Field
          label="Last field verification"
          value={hotspot.last_field_verification_days_ago != null ? `${hotspot.last_field_verification_days_ago} days ago` : "Not yet verified"}
        />
      </div>
      <p className="text-xs text-slate-400 mt-4 pt-3 border-t border-border">
        AI recommendation: <span className="font-medium text-navy-800">{hotspot.priority_label.toUpperCase()} PRIORITY</span> - AI-generated
        investigation priority, not confirmation of illegal activity. Requires field verification.
      </p>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-slate-400">{label}</p>
      <p className="text-navy-900 font-semibold mt-0.5">{value}</p>
    </div>
  );
}
