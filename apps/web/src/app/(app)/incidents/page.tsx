"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Topbar } from "@/components/Topbar";
import { StatusBadge } from "@/components/StatusBadge";
import { Pager } from "@/components/Pager";
import { LoadingState, ErrorState, EmptyState } from "@/components/States";
import { api, ApiError } from "@/lib/api";
import type { Incident, IncidentStatus } from "@/lib/types";

const PAGE_SIZE = 25;

const STATUS_OPTIONS: IncidentStatus[] = [
  "NEW",
  "UNDER_REVIEW",
  "FIELD_VERIFICATION_REQUIRED",
  "VERIFIED",
  "UNVERIFIED",
  "CLOSED",
  "ARCHIVED",
];

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<Incident[] | null>(null);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("");
  const [minRisk, setMinRisk] = useState<string>("");
  const [search, setSearch] = useState("");

  // Any filter change starts back at page one - the previous offset almost
  // certainly no longer points at a meaningful page of the new result set.
  useEffect(() => {
    setOffset(0);
  }, [status, minRisk, search]);

  useEffect(() => {
    const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset) });
    if (status) params.set("status", status);
    if (minRisk) params.set("min_risk", minRisk);
    if (search) params.set("search", search);

    setIncidents(null);
    api
      .getWithTotal<Incident[]>(`/api/incidents?${params.toString()}`)
      .then(({ items, total }) => {
        setIncidents(items);
        setTotal(total);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load incidents"));
  }, [status, minRisk, search, offset]);

  return (
    <>
      <Topbar title="Incidents" />
      <div className="p-6 space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <input
            type="text"
            placeholder="Search by title or reference number…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 min-w-[220px] rounded-md border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-navy-700"
          />
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="rounded-md border border-border px-3 py-2 text-sm"
          >
            <option value="">All statuses</option>
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s.replaceAll("_", " ")}
              </option>
            ))}
          </select>
          <select
            value={minRisk}
            onChange={(e) => setMinRisk(e.target.value)}
            className="rounded-md border border-border px-3 py-2 text-sm"
          >
            <option value="">Any risk</option>
            <option value="61">High+ (61+)</option>
            <option value="81">Critical (81+)</option>
          </select>
        </div>

        {error && <ErrorState detail={error} />}
        {!incidents && !error && <LoadingState />}
        {incidents && incidents.length === 0 && <EmptyState label="No incidents match these filters." />}

        {incidents && incidents.length > 0 && (
          <div className="bg-surface border border-border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs text-slate-500 uppercase tracking-wide">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Reference</th>
                  <th className="px-4 py-2.5 font-medium">Title</th>
                  <th className="px-4 py-2.5 font-medium">Type</th>
                  <th className="px-4 py-2.5 font-medium">Status</th>
                  <th className="px-4 py-2.5 font-medium">Risk</th>
                  <th className="px-4 py-2.5 font-medium">Reported</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {incidents.map((i) => (
                  <tr key={i.id} className="hover:bg-slate-50">
                    <td className="px-4 py-2.5">
                      <Link href={`/incidents/${i.id}`} className="text-navy-700 font-medium hover:underline">
                        {i.reference_number}
                      </Link>
                    </td>
                    <td className="px-4 py-2.5 max-w-xs truncate">{i.title}</td>
                    <td className="px-4 py-2.5 text-xs text-slate-500">{i.incident_type.replaceAll("_", " ")}</td>
                    <td className="px-4 py-2.5">
                      <StatusBadge status={i.status} />
                    </td>
                    <td className="px-4 py-2.5 text-xs font-semibold">{i.risk_score ?? "-"}</td>
                    <td className="px-4 py-2.5 text-xs text-slate-400">{i.created_at.slice(0, 10)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pager total={total} limit={PAGE_SIZE} offset={offset} onOffsetChange={setOffset} itemLabel="incident" />
          </div>
        )}
      </div>
    </>
  );
}
