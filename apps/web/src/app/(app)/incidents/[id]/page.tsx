"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Topbar } from "@/components/Topbar";
import { StatusBadge } from "@/components/StatusBadge";
import { RiskBadge } from "@/components/RiskBadge";
import { LoadingState, ErrorState } from "@/components/States";
import { MarkdownLite } from "@/components/MarkdownLite";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { EvidenceOut, IncidentDetail, IncidentStatus, ReportOut, RiskScoreOut } from "@/lib/types";

const STATUS_OPTIONS: IncidentStatus[] = [
  "NEW",
  "UNDER_REVIEW",
  "FIELD_VERIFICATION_REQUIRED",
  "VERIFIED",
  "UNVERIFIED",
  "CLOSED",
  "ARCHIVED",
];

export default function IncidentDetailPage() {
  const params = useParams<{ id: string }>();
  const { hasPermission } = useAuth();
  const [incident, setIncident] = useState<IncidentDetail | null>(null);
  const [risk, setRisk] = useState<RiskScoreOut | null>(null);
  const [evidence, setEvidence] = useState<EvidenceOut[]>([]);
  const [preliminaryReport, setPreliminaryReport] = useState<ReportOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showRiskDetail, setShowRiskDetail] = useState(false);

  const load = useCallback(async () => {
    try {
      const inc = await api.get<IncidentDetail>(`/api/incidents/${params.id}`);
      setIncident(inc);
      const ev = await api.get<EvidenceOut[]>(`/api/evidence/incident/${params.id}`);
      setEvidence(ev);
      try {
        const r = await api.get<RiskScoreOut>(`/api/risk/incidents/${params.id}`);
        setRisk(r);
      } catch {
        setRisk(null);
      }
      if (hasPermission("report:generate_preliminary")) {
        try {
          const pr = await api.get<ReportOut | null>(`/api/incidents/${params.id}/preliminary-report`);
          setPreliminaryReport(pr);
        } catch {
          setPreliminaryReport(null);
        }
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load incident");
    }
  }, [params.id, hasPermission]);

  useEffect(() => {
    load();
  }, [load]);

  if (error) return <div className="p-6"><ErrorState detail={error} /></div>;
  if (!incident) return <LoadingState />;

  return (
    <>
      <Topbar title={incident.reference_number} />
      <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 space-y-5">
          <div className="bg-surface border border-border rounded-lg p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-navy-900">{incident.title}</h2>
                <p className="text-xs text-slate-400 mt-1">
                  {incident.incident_type.replaceAll("_", " ")} · Reported {incident.created_at.slice(0, 10)}
                </p>
              </div>
              <div className="flex flex-col items-end gap-1.5">
                <StatusBadge status={incident.status} />
                {incident.risk_score != null && risk && <RiskBadge category={risk.category} score={risk.score} />}
              </div>
            </div>
            <p className="text-sm text-slate-600 mt-4">{incident.description || "No description provided."}</p>

            <dl className="grid grid-cols-2 gap-x-6 gap-y-2 mt-5 text-xs">
              <DetailRow label="Coordinates" value={`${incident.latitude.toFixed(4)}, ${incident.longitude.toFixed(4)}`} />
              <DetailRow label="Priority" value={incident.priority} />
              <DetailRow label="Water body affected" value={incident.water_body_affected ? "Yes" : "No"} />
              <DetailRow label="Protected area affected" value={incident.protected_area_affected ? "Yes" : "No"} />
              <DetailRow label="Equipment observed" value={incident.equipment_observed || "-"} />
              <DetailRow
                label="Estimated people present"
                value={incident.estimated_people_present != null ? String(incident.estimated_people_present) : "-"}
              />
              <DetailRow label="Verification status" value={incident.verification_status.replaceAll("_", " ")} />
              <DetailRow label="Classification" value={incident.classification} />
            </dl>
          </div>

          {risk && (
            <div className="bg-surface border border-border rounded-lg p-5">
              <button
                onClick={() => setShowRiskDetail((v) => !v)}
                className="flex items-center justify-between w-full text-left"
              >
                <h3 className="text-sm font-semibold text-navy-900">
                  RISK SCORE: {risk.score} · Why is this area {risk.category.toLowerCase()} risk?
                </h3>
                <span className="text-xs text-navy-700">{showRiskDetail ? "Hide" : "Show breakdown"}</span>
              </button>
              {showRiskDetail && (
                <div className="mt-4 space-y-2">
                  {risk.factors.length === 0 && (
                    <p className="text-xs text-slate-400">No contributing risk signals recorded.</p>
                  )}
                  {risk.factors.map((f, idx) => (
                    <div key={idx} className="flex items-center justify-between text-xs border-b border-border pb-2">
                      <div>
                        <p className="font-medium text-navy-900">{f.label}</p>
                        {f.detail && <p className="text-slate-400">{f.detail}</p>}
                      </div>
                      <span className="font-semibold text-risk-high">+{f.points}</span>
                    </div>
                  ))}
                  <p className="text-[11px] text-slate-400 pt-2">
                    Operational Risk / Investigation Priority Score - not confirmation of illegal activity. Model{" "}
                    {risk.model_version}, calculated {risk.calculated_at.slice(0, 10)}.
                  </p>
                </div>
              )}
            </div>
          )}

          <StatusHistoryPanel incident={incident} />

          <EvidencePanel incidentId={incident.id} evidence={evidence} onChange={load} />

          {hasPermission("report:generate_preliminary") && (
            <PreliminaryReportPanel incidentId={incident.id} report={preliminaryReport} onGenerated={setPreliminaryReport} />
          )}
        </div>

        <div className="space-y-5">
          {hasPermission("incident:change_status") && <StatusChangePanel incident={incident} onChange={load} />}
        </div>
      </div>
    </>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-slate-400">{label}</dt>
      <dd className="text-navy-900 font-medium mt-0.5">{value}</dd>
    </div>
  );
}

function StatusHistoryPanel({ incident }: { incident: IncidentDetail }) {
  return (
    <div className="bg-surface border border-border rounded-lg p-5">
      <h3 className="text-sm font-semibold text-navy-900 mb-4">Intelligence Timeline</h3>
      <ol className="space-y-4 border-l-2 border-border pl-4">
        {incident.status_history.map((h) => (
          <li key={h.id} className="relative">
            <span className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-navy-700 border-2 border-white" />
            <p className="text-xs text-slate-400">{h.changed_at.slice(0, 16).replace("T", " ")}</p>
            <p className="text-sm font-medium text-navy-900">
              {h.previous_status ? `${h.previous_status.replaceAll("_", " ")} → ` : ""}
              {h.new_status.replaceAll("_", " ")}
            </p>
            {h.reason && <p className="text-xs text-slate-500">{h.reason}</p>}
          </li>
        ))}
      </ol>
    </div>
  );
}

function StatusChangePanel({ incident, onChange }: { incident: IncidentDetail; onChange: () => void }) {
  const [newStatus, setNewStatus] = useState<IncidentStatus>(incident.status);
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit() {
    setSubmitting(true);
    setErr(null);
    try {
      await api.post(`/api/incidents/${incident.id}/status`, { new_status: newStatus, reason });
      setReason("");
      onChange();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Failed to change status");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="bg-surface border border-border rounded-lg p-5">
      <h3 className="text-sm font-semibold text-navy-900 mb-3">Change Status</h3>
      <select
        value={newStatus}
        onChange={(e) => setNewStatus(e.target.value as IncidentStatus)}
        className="w-full rounded-md border border-border px-3 py-2 text-sm mb-2"
      >
        {STATUS_OPTIONS.map((s) => (
          <option key={s} value={s}>
            {s.replaceAll("_", " ")}
          </option>
        ))}
      </select>
      <textarea
        placeholder="Reason for this change (required for audit log)"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        rows={3}
        className="w-full rounded-md border border-border px-3 py-2 text-sm mb-2"
      />
      {err && <p className="text-xs text-red-600 mb-2">{err}</p>}
      <button
        onClick={submit}
        disabled={submitting || !reason.trim()}
        className="w-full rounded-md bg-navy-800 text-white text-sm font-medium py-2 hover:bg-navy-700 disabled:opacity-50"
      >
        {submitting ? "Updating…" : "Update status"}
      </button>
    </div>
  );
}

function EvidencePanel({
  incidentId,
  evidence,
  onChange,
}: {
  incidentId: string;
  evidence: EvidenceOut[];
  onChange: () => void;
}) {
  const { hasPermission } = useAuth();
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState<string | null>(null);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append("incident_id", incidentId);
      form.append("file", file);
      await api.postForm(`/api/evidence`, form);
      onChange();
    } catch {
      // surfaced via lack of update; kept simple for demo
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  async function handleAnalyze(evidenceId: string) {
    setAnalyzing(evidenceId);
    try {
      await api.post(`/api/ai/analyze-image/${evidenceId}`);
      onChange();
    } finally {
      setAnalyzing(null);
    }
  }

  return (
    <div className="bg-surface border border-border rounded-lg p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-navy-900">Evidence</h3>
        {hasPermission("evidence:upload") && (
          <label className="text-xs text-navy-700 font-medium cursor-pointer hover:underline">
            {uploading ? "Uploading…" : "+ Upload evidence"}
            <input type="file" className="hidden" onChange={handleUpload} disabled={uploading} />
          </label>
        )}
      </div>

      {evidence.length === 0 && <p className="text-xs text-slate-400">No evidence uploaded yet.</p>}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {evidence.map((ev) => (
          <div key={ev.id} className="border border-border rounded-md p-3">
            <p className="text-xs font-medium text-navy-900 truncate">{ev.original_filename}</p>
            <p className="text-[11px] text-slate-400">
              {ev.file_type} · v{ev.current_version} · {(ev.file_size_bytes / 1024).toFixed(1)} KB
            </p>
            <p className="text-[11px] text-slate-400 font-mono truncate" title={ev.file_hash}>
              sha256: {ev.file_hash.slice(0, 16)}…
            </p>

            {ev.ai_analysis?.detections && (
              <div className="mt-2 space-y-1">
                <p className="text-[10px] uppercase tracking-wide text-slate-400">AI Object Detection (observation aid)</p>
                {ev.ai_analysis.detections.map((d, i) => (
                  <div key={i} className="flex items-center justify-between text-xs">
                    <span>{d.label}</span>
                    <span className="text-slate-400">{Math.round(d.confidence * 100)}%</span>
                  </div>
                ))}
              </div>
            )}

            {hasPermission("ai:analyze_image") && !ev.ai_analysis && (
              <button
                onClick={() => handleAnalyze(ev.id)}
                disabled={analyzing === ev.id}
                className="mt-2 text-[11px] text-navy-700 font-medium hover:underline"
              >
                {analyzing === ev.id ? "Analyzing…" : "Run AI image analysis"}
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function PreliminaryReportPanel({
  incidentId,
  report,
  onGenerated,
}: {
  incidentId: string;
  report: ReportOut | null;
  onGenerated: (report: ReportOut) => void;
}) {
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generate() {
    setGenerating(true);
    setError(null);
    try {
      const r = await api.post<ReportOut>(`/api/incidents/${incidentId}/preliminary-report`);
      onGenerated(r);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to generate preliminary report");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="bg-surface border border-border rounded-lg p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-navy-900">AI-Generated Preliminary Report</h3>
        <button
          onClick={generate}
          disabled={generating}
          className="text-xs text-navy-700 font-medium hover:underline disabled:opacity-50"
        >
          {generating ? "Generating…" : report ? "Regenerate" : "Generate"}
        </button>
      </div>
      {error && <p className="text-xs text-red-600 mb-2">{error}</p>}
      {report ? (
        <>
          <MarkdownLite content={report.content_markdown} />
          <p className="text-[11px] text-slate-400 mt-3 pt-3 border-t border-border">
            Generated {report.created_at.slice(0, 16).replace("T", " ")} by {report.model_name} {report.model_version}
          </p>
        </>
      ) : (
        <p className="text-xs text-slate-400">
          Not generated yet - click Generate to assemble a preliminary report from this incident&apos;s recorded
          fields and evidence.
        </p>
      )}
    </div>
  );
}
