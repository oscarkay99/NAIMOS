"use client";

import { useEffect, useState } from "react";
import { Topbar } from "@/components/Topbar";
import { LoadingState, ErrorState, EmptyState } from "@/components/States";
import { api, ApiError } from "@/lib/api";
import type { AuditLogEntry } from "@/lib/types";

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLogEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<AuditLogEntry[]>("/api/audit-logs?limit=200")
      .then(setLogs)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load audit logs"));
  }, []);

  return (
    <>
      <Topbar title="Audit Logs" />
      <div className="p-6">
        {error && <ErrorState detail={error} />}
        {!logs && !error && <LoadingState />}
        {logs && logs.length === 0 && <EmptyState label="No audit events recorded yet." />}
        {logs && logs.length > 0 && (
          <div className="bg-surface border border-border rounded-lg overflow-hidden">
            <table className="w-full text-xs">
              <thead className="bg-slate-50 text-left text-[11px] text-slate-500 uppercase tracking-wide">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Time</th>
                  <th className="px-4 py-2.5 font-medium">Action</th>
                  <th className="px-4 py-2.5 font-medium">Entity</th>
                  <th className="px-4 py-2.5 font-medium">Change</th>
                  <th className="px-4 py-2.5 font-medium">Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50">
                    <td className="px-4 py-2 text-slate-400 whitespace-nowrap">{log.created_at.slice(0, 19).replace("T", " ")}</td>
                    <td className="px-4 py-2 font-medium text-navy-900">{log.action}</td>
                    <td className="px-4 py-2 text-slate-500">
                      {log.entity_type ? `${log.entity_type}${log.entity_id ? ` · ${log.entity_id.slice(0, 8)}` : ""}` : "—"}
                    </td>
                    <td className="px-4 py-2 text-slate-500 max-w-xs truncate">
                      {log.previous_value && log.new_value
                        ? `${log.previous_value} → ${log.new_value}`
                        : log.new_value || "—"}
                    </td>
                    <td className="px-4 py-2 text-slate-500 max-w-xs truncate">{log.reason || "—"}</td>
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
