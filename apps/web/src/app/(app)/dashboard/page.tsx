"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Topbar } from "@/components/Topbar";
import { MetricCard } from "@/components/MetricCard";
import { MapPanel } from "@/components/MapPanel";
import { StatusBadge } from "@/components/StatusBadge";
import { LoadingState, ErrorState } from "@/components/States";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Incident, MapFeature } from "@/lib/types";

export default function DashboardPage() {
  const { hasPermission } = useAuth();
  const [incidents, setIncidents] = useState<Incident[] | null>(null);
  const [features, setFeatures] = useState<MapFeature[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.get<Incident[]>("/api/incidents?limit=200"),
      api.get<MapFeature[]>("/api/map/features"),
    ])
      .then(([inc, feat]) => {
        setIncidents(inc);
        setFeatures(feat);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load dashboard data"));
  }, []);

  if (error) {
    return (
      <div className="p-6">
        <ErrorState detail={error} />
      </div>
    );
  }

  if (!incidents) {
    return (
      <>
        <Topbar title="National Intelligence Command Centre" />
        <LoadingState />
      </>
    );
  }

  const verified = incidents.filter((i) => i.verification_status === "VERIFIED");
  const highRisk = incidents.filter((i) => (i.risk_score || 0) >= 61);
  const active = incidents.filter((i) => !["CLOSED", "ARCHIVED"].includes(i.status));
  const emerging = [...incidents].sort((a, b) => (b.risk_score || 0) - (a.risk_score || 0)).slice(0, 5);
  const recent = [...incidents].sort((a, b) => b.created_at.localeCompare(a.created_at)).slice(0, 6);
  const environmental = incidents.filter((i) => i.water_body_affected || i.protected_area_affected).slice(0, 6);

  return (
    <>
      <Topbar title="National Intelligence Command Centre" />
      <div className="p-6 space-y-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard label="Active Investigations" value={active.length} />
          <MetricCard label="Verified Incidents" value={verified.length} />
          <MetricCard label="High-Risk Areas" value={highRisk.length} accent={highRisk.length ? "high" : "default"} />
          <MetricCard label="Total Reports" value={incidents.length} />
        </div>

        <div className="bg-surface border border-border rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-navy-900">National Risk Map</h2>
            <Link href="/map" className="text-xs text-navy-700 font-medium hover:underline">
              Open full map →
            </Link>
          </div>
          <MapPanel features={features} heightClass="h-[420px]" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Panel title="Emerging Hotspots" href="/incidents">
            {emerging.length === 0 && <p className="text-xs text-slate-400 px-4 py-6">No high-risk locations.</p>}
            {emerging.map((i) => (
              <IncidentRow key={i.id} incident={i} showRisk />
            ))}
          </Panel>

          <Panel title="Recent Incidents" href="/incidents">
            {recent.map((i) => (
              <IncidentRow key={i.id} incident={i} />
            ))}
          </Panel>

          <Panel title="Environmental Alerts" href="/incidents">
            {environmental.length === 0 && <p className="text-xs text-slate-400 px-4 py-6">No environmental alerts.</p>}
            {environmental.map((i) => (
              <IncidentRow key={i.id} incident={i} tag={i.water_body_affected ? "Water body" : "Protected area"} />
            ))}
          </Panel>
        </div>

        {!hasPermission("analytics:view") && (
          <p className="text-xs text-slate-400">Trend analytics require analytics:view permission - see Analytics for full charts.</p>
        )}
      </div>
    </>
  );
}

function Panel({ title, href, children }: { title: string; href: string; children: React.ReactNode }) {
  return (
    <div className="bg-surface border border-border rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <h3 className="text-sm font-semibold text-navy-900">{title}</h3>
        <Link href={href} className="text-xs text-navy-700 font-medium hover:underline">
          View all →
        </Link>
      </div>
      <div className="divide-y divide-border max-h-80 overflow-y-auto">{children}</div>
    </div>
  );
}

function IncidentRow({ incident, showRisk, tag }: { incident: Incident; showRisk?: boolean; tag?: string }) {
  return (
    <Link
      href={`/incidents/${incident.id}`}
      className="flex items-center justify-between gap-3 px-4 py-2.5 hover:bg-slate-50 transition-colors"
    >
      <div className="min-w-0">
        <p className="text-xs font-medium text-navy-900 truncate">{incident.title}</p>
        <p className="text-[11px] text-slate-400">
          {incident.reference_number} {tag && `· ${tag}`}
        </p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {showRisk && incident.risk_score != null && (
          <span className="text-xs font-semibold text-risk-high">{incident.risk_score}</span>
        )}
        <StatusBadge status={incident.status} />
      </div>
    </Link>
  );
}
