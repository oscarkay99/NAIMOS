"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Topbar } from "@/components/Topbar";
import { MapPanel } from "@/components/MapPanel";
import { LoadingState, ErrorState, EmptyState } from "@/components/States";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { MapFeature, RiskLeaderboardEntry, RiskRecalculateResult } from "@/lib/types";

export default function RiskMapPage() {
  const { hasPermission } = useAuth();
  const [entries, setEntries] = useState<RiskLeaderboardEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [recalculating, setRecalculating] = useState(false);
  const [lastRecalculated, setLastRecalculated] = useState<string | null>(null);

  useEffect(() => {
    load();
  }, []);

  function load() {
    setError(null);
    api
      .get<RiskLeaderboardEntry[]>("/api/risk/leaderboard?limit=50")
      .then(setEntries)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load risk leaderboard"));
  }

  async function recalculate() {
    setRecalculating(true);
    try {
      const result = await api.post<RiskRecalculateResult>("/api/risk/recalculate");
      setLastRecalculated(result.recalculated_at);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to recalculate risk scores");
    } finally {
      setRecalculating(false);
    }
  }

  const mapFeatures: MapFeature[] = (entries || []).map((e) => ({
    id: e.incident_id,
    layer: "incident",
    name: `${e.reference_number} - ${e.title}`,
    latitude: e.latitude,
    longitude: e.longitude,
    status: e.status,
    risk_score: e.score,
    risk_category: e.category,
  }));

  return (
    <>
      <Topbar title="AI Risk Map" />
      <div className="p-6 space-y-5">
        <div className="bg-navy-950 text-white rounded-lg p-4 text-xs leading-relaxed">
          This ranks every monitored area by <strong>operational investigation priority</strong>, not just
          &ldquo;where is mining happening.&rdquo; The score blends recent field reports, AI-detected land
          disturbance, proximity to water bodies and protected areas, historical activity, and trend - see the
          full breakdown on any incident. <strong>Change</strong> is week-over-week, computed from real risk-score
          history, not a display trick.
        </div>

        <div className="flex items-center justify-between">
          <p className="text-xs text-slate-400">
            {entries ? `${entries.length} monitored area(s), ranked by priority` : "Loading…"}
            {lastRecalculated && ` · last recalculated ${lastRecalculated.slice(0, 16).replace("T", " ")}`}
          </p>
          {hasPermission("risk:recalculate") && (
            <button
              onClick={recalculate}
              disabled={recalculating}
              className="rounded-md bg-navy-800 text-white text-sm font-medium px-4 py-2 hover:bg-navy-700 disabled:opacity-50"
            >
              {recalculating ? "Recalculating…" : "Recalculate risk scores"}
            </button>
          )}
        </div>

        {error && <ErrorState detail={error} />}
        {!entries && !error && <LoadingState />}

        {entries && (
          <div className="bg-surface border border-border rounded-lg overflow-hidden">
            <MapPanel features={mapFeatures} heightClass="h-[360px]" />
          </div>
        )}

        {entries && entries.length === 0 && <EmptyState label="No monitored areas with a calculated risk score yet." />}

        {entries && entries.length > 0 && (
          <div className="bg-surface border border-border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs text-slate-500 uppercase tracking-wide">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Area</th>
                  <th className="px-4 py-2.5 font-medium">Risk</th>
                  <th className="px-4 py-2.5 font-medium">Change (7d)</th>
                  <th className="px-4 py-2.5 font-medium">River proximity</th>
                  <th className="px-4 py-2.5 font-medium">Priority</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {entries.map((e) => (
                  <tr key={e.incident_id} className="hover:bg-slate-50">
                    <td className="px-4 py-2.5">
                      <Link href={`/incidents/${e.incident_id}`} className="text-navy-700 font-medium hover:underline">
                        {e.reference_number}
                      </Link>
                      <p className="text-xs text-slate-400 truncate max-w-xs">
                        {e.title} - {[e.district, e.region].filter(Boolean).join(", ")}
                      </p>
                    </td>
                    <td className="px-4 py-2.5 font-semibold">{e.score}/100</td>
                    <td className="px-4 py-2.5">
                      <ChangeCell pct={e.change_pct} />
                    </td>
                    <td className="px-4 py-2.5 text-xs text-slate-500">
                      {e.nearest_water_body_distance_km != null
                        ? `${e.nearest_water_body_name} · ${e.nearest_water_body_distance_km} km`
                        : "-"}
                    </td>
                    <td className="px-4 py-2.5">
                      <span className="text-sm">
                        {e.priority_emoji} {e.priority_label}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}

function ChangeCell({ pct }: { pct: number | null }) {
  if (pct == null) return <span className="text-xs text-slate-400">New</span>;
  const positive = pct > 0;
  const flat = Math.abs(pct) < 0.5;
  return (
    <span
      className={`text-sm font-medium ${flat ? "text-slate-500" : positive ? "text-risk-high" : "text-emerald-700"}`}
    >
      {flat ? "±0%" : `${positive ? "+" : ""}${pct}%`}
    </span>
  );
}
