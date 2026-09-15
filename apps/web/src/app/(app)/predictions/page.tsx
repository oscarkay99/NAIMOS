"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Topbar } from "@/components/Topbar";
import { RiskBadge } from "@/components/RiskBadge";
import { LoadingState, ErrorState, EmptyState } from "@/components/States";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { ExpansionLeaderboardEntry, ExpansionRecalculateResult } from "@/lib/types";

export default function PredictionsPage() {
  const { hasPermission } = useAuth();
  const [entries, setEntries] = useState<ExpansionLeaderboardEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [recalculating, setRecalculating] = useState(false);
  const [lastRecalculated, setLastRecalculated] = useState<string | null>(null);

  useEffect(() => {
    load();
  }, []);

  function load() {
    setError(null);
    api
      .get<ExpansionLeaderboardEntry[]>("/api/predictions/leaderboard?limit=50")
      .then(setEntries)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load expansion predictions"));
  }

  async function recalculate() {
    setRecalculating(true);
    try {
      const result = await api.post<ExpansionRecalculateResult>("/api/predictions/recalculate");
      setLastRecalculated(result.recalculated_at);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to recalculate predictions");
    } finally {
      setRecalculating(false);
    }
  }

  return (
    <>
      <Topbar title="Predictive Intelligence" />
      <div className="p-6 space-y-5 max-w-4xl mx-auto w-full">
        <div className="bg-navy-950 text-white rounded-lg p-4 text-xs leading-relaxed">
          This estimates <strong>where illegal mining is likely to expand next</strong>, not where it is
          happening today - the risk-engine&apos;s forward-looking counterpart. Every probability is built
          from named, inspectable signals (rising risk trend, new access routes, land disturbance, nearby
          prior activity, water proximity, equipment reports) and is capped below 100% - it is an
          AI-generated projection, never a certainty, and always requires field verification before action.
        </div>

        <div className="flex items-center justify-between">
          <p className="text-xs text-slate-400">
            {entries ? `${entries.length} monitored area(s), ranked by expansion probability` : "Loading…"}
            {lastRecalculated && ` · last recalculated ${lastRecalculated.slice(0, 16).replace("T", " ")}`}
          </p>
          {hasPermission("prediction:recalculate") && (
            <button
              onClick={recalculate}
              disabled={recalculating}
              className="rounded-md bg-navy-800 text-white text-sm font-medium px-4 py-2 hover:bg-navy-700 disabled:opacity-50"
            >
              {recalculating ? "Recalculating…" : "Recalculate predictions"}
            </button>
          )}
        </div>

        {error && <ErrorState detail={error} />}
        {!entries && !error && <LoadingState />}
        {entries && entries.length === 0 && <EmptyState label="No active monitored areas with a calculated prediction yet." />}

        {entries && entries.length > 0 && (
          <div className="space-y-3">
            {entries.map((e) => (
              <PredictionCard key={e.incident_id} entry={e} />
            ))}
          </div>
        )}
      </div>
    </>
  );
}

function PredictionCard({ entry }: { entry: ExpansionLeaderboardEntry }) {
  const noSignal = entry.probability === 0;
  return (
    <div className="bg-surface border border-border rounded-lg p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-wide text-slate-400 font-medium">
            {noSignal ? "Monitored area" : "⚠️ Emerging Threat"}
          </p>
          <Link href={`/incidents/${entry.incident_id}`} className="text-sm font-semibold text-navy-900 hover:underline">
            {entry.reference_number} - {entry.title}
          </Link>
          <p className="text-xs text-slate-400">{[entry.district, entry.region].filter(Boolean).join(", ")}</p>
        </div>
        <RiskBadge category={entry.category} score={entry.probability} />
      </div>

      <div className="grid grid-cols-2 gap-3 text-xs">
        <div>
          <p className="text-slate-400">Expansion probability</p>
          <p className="text-navy-900 font-semibold">{entry.probability}%</p>
        </div>
        <div>
          <p className="text-slate-400">Expected development</p>
          <p className="text-navy-900 font-semibold">{entry.expected_development}</p>
        </div>
      </div>

      {entry.factors.length > 0 && (
        <div>
          <p className="text-xs text-slate-400 mb-1">Reasoning</p>
          <ul className="text-xs text-navy-800 space-y-0.5 list-disc list-inside">
            {entry.factors.map((f, i) => (
              <li key={i}>
                {f.detail || f.label}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="text-xs bg-slate-50 border border-border rounded-md px-3 py-2 text-navy-800">
        <span className="font-medium">AI recommendation:</span> {entry.recommendation}
      </div>
    </div>
  );
}
