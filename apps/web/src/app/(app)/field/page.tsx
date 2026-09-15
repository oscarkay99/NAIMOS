"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Topbar } from "@/components/Topbar";
import { VoiceRecorder } from "@/components/VoiceRecorder";
import { FileCaptureList } from "@/components/FileCaptureList";
import { MarkdownLite } from "@/components/MarkdownLite";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { IncidentType, ReportOut, VoiceExtraction, VoiceReportTranscribeOut } from "@/lib/types";

const INCIDENT_TYPES: IncidentType[] = [
  "SUSPECTED_ILLEGAL_MINING",
  "LAND_DISTURBANCE",
  "WATER_POLLUTION",
  "VEGETATION_LOSS",
  "UNAUTHORIZED_EQUIPMENT",
  "OTHER",
];

export default function FieldReportingPage() {
  return (
    <>
      <Topbar title="Field Reporting" />
      <div className="p-4 sm:p-6 max-w-2xl mx-auto w-full">
        <Suspense fallback={null}>
          <FieldCaptureForm />
        </Suspense>
      </div>
    </>
  );
}

interface SubmissionResult {
  incidentId: string;
  referenceNumber: string;
  evidenceUploaded: number;
  evidenceFailed: number;
  preliminaryReport: ReportOut | null;
}

function FieldCaptureForm() {
  const { hasPermission } = useAuth();
  const searchParams = useSearchParams();
  const prefillLat = searchParams.get("lat");
  const prefillLon = searchParams.get("lon");

  // Voice narrative
  const [voiceFile, setVoiceFile] = useState<File | null>(null);
  const [transcribing, setTranscribing] = useState(false);
  const [voiceResult, setVoiceResult] = useState<VoiceReportTranscribeOut | null>(null);
  const [editedTranscript, setEditedTranscript] = useState("");
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [statementApplied, setStatementApplied] = useState(false);

  // Structured fields
  const [title, setTitle] = useState(prefillLat ? "AI-flagged area - pending verification" : "");
  const [description, setDescription] = useState(
    prefillLat ? "Pre-filled from a satellite AI change-detection scan. Verify on site before confirming details." : ""
  );
  const [lat, setLat] = useState(prefillLat || "");
  const [lon, setLon] = useState(prefillLon || "");
  const [incidentType, setIncidentType] = useState<IncidentType>("SUSPECTED_ILLEGAL_MINING");
  const [waterBody, setWaterBody] = useState(false);
  const [protectedArea, setProtectedArea] = useState(false);
  const [equipment, setEquipment] = useState("");
  const [people, setPeople] = useState("");

  // Media
  const [photos, setPhotos] = useState<File[]>([]);
  const [videos, setVideos] = useState<File[]>([]);

  // Submission
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SubmissionResult | null>(null);

  function useMyLocation() {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition((pos) => {
      setLat(pos.coords.latitude.toFixed(6));
      setLon(pos.coords.longitude.toFixed(6));
    });
  }

  async function transcribeVoice() {
    if (!voiceFile) return;
    setTranscribing(true);
    setVoiceError(null);
    try {
      const form = new FormData();
      form.append("file", voiceFile);
      const resp = await api.postForm<VoiceReportTranscribeOut>("/api/field-reports/voice", form);
      setVoiceResult(resp);
      setEditedTranscript(resp.transcript);
      setStatementApplied(false);
    } catch (err) {
      setVoiceError(err instanceof ApiError ? err.message : "Failed to transcribe voice note");
    } finally {
      setTranscribing(false);
    }
  }

  function applyVoiceStatement() {
    setDescription(editedTranscript);
    if (voiceResult) {
      const ex = voiceResult.extraction;
      if (!equipment && ex.equipment_mentioned.length > 0) setEquipment(ex.equipment_mentioned.join(", "));
      if (ex.water_body_mentioned) setWaterBody(true);
    }
    setStatementApplied(true);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const created = await api.post<{ id: string; reference_number: string }>("/api/incidents", {
        title,
        description,
        latitude: parseFloat(lat),
        longitude: parseFloat(lon),
        incident_type: incidentType,
        water_body_affected: waterBody,
        protected_area_affected: protectedArea,
        equipment_observed: equipment || null,
        estimated_people_present: people ? parseInt(people, 10) : null,
      });

      if (voiceResult) {
        try {
          await api.post("/api/field-reports/voice/approve", {
            field_report_id: voiceResult.field_report_id,
            edited_transcript: editedTranscript,
            incident_id: created.id,
          });
        } catch {
          // Non-fatal: the incident and its structured fields are already saved.
        }
      }

      let uploaded = 0;
      let failed = 0;
      for (const file of [...photos, ...videos]) {
        try {
          const form = new FormData();
          form.append("incident_id", created.id);
          form.append("file", file);
          await api.postForm("/api/evidence", form);
          uploaded += 1;
        } catch {
          failed += 1;
        }
      }

      let preliminaryReport: ReportOut | null = null;
      if (hasPermission("report:generate_preliminary")) {
        try {
          preliminaryReport = await api.post<ReportOut>(`/api/incidents/${created.id}/preliminary-report`);
        } catch {
          preliminaryReport = null;
        }
      }

      setResult({
        incidentId: created.id,
        referenceNumber: created.reference_number,
        evidenceUploaded: uploaded,
        evidenceFailed: failed,
        preliminaryReport,
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to submit field report");
    } finally {
      setSubmitting(false);
    }
  }

  function resetForm() {
    setResult(null);
    setVoiceFile(null);
    setVoiceResult(null);
    setEditedTranscript("");
    setStatementApplied(false);
    setTitle("");
    setDescription("");
    setEquipment("");
    setPeople("");
    setPhotos([]);
    setVideos([]);
  }

  if (result) {
    return (
      <div className="bg-surface border border-border rounded-lg p-5 space-y-4">
        <div className="rounded-md bg-emerald-50 border border-emerald-200 px-3 py-2 text-sm text-emerald-800">
          ✓ Incident <strong>{result.referenceNumber}</strong> created
          {result.evidenceUploaded > 0 && ` · ${result.evidenceUploaded} evidence file(s) attached`}
          {result.evidenceFailed > 0 && ` · ${result.evidenceFailed} file(s) failed to upload`}
        </div>

        {result.preliminaryReport ? (
          <div className="border border-border rounded-lg p-4">
            <p className="text-[11px] font-semibold text-purple-700 uppercase tracking-wide mb-2">
              AI-Generated Preliminary Report
            </p>
            <MarkdownLite content={result.preliminaryReport.content_markdown} />
          </div>
        ) : (
          <p className="text-xs text-slate-400">
            Preliminary report not generated automatically - open the incident to generate one.
          </p>
        )}

        <div className="flex gap-3">
          <Link
            href={`/incidents/${result.incidentId}`}
            className="flex-1 text-center rounded-md bg-navy-800 text-white text-sm font-medium py-2 hover:bg-navy-700"
          >
            Open full incident record
          </Link>
          <button
            onClick={resetForm}
            className="flex-1 rounded-md border border-border text-navy-800 text-sm font-medium py-2 hover:bg-slate-50"
          >
            Submit another report
          </button>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-5">
      {prefillLat && (
        <div className="rounded-md bg-purple-50 border border-purple-200 px-3 py-2 text-xs text-purple-800">
          Coordinates pre-filled from a Satellite Monitoring AI detection. Review and confirm all fields on site.
        </div>
      )}

      <div className="bg-surface border border-border rounded-lg p-5 space-y-3">
        <label className="block text-xs font-medium text-slate-500">Voice narrative (optional)</label>
        <VoiceRecorder onRecordingReady={setVoiceFile} disabled={transcribing} />

        {voiceFile && !voiceResult && (
          <button
            type="button"
            onClick={transcribeVoice}
            disabled={transcribing}
            className="rounded-md bg-navy-800 text-white text-sm font-medium px-4 py-2 hover:bg-navy-700 disabled:opacity-50"
          >
            {transcribing ? "Transcribing…" : "Transcribe voice narrative"}
          </button>
        )}
        {voiceError && <p className="text-xs text-red-600">{voiceError}</p>}

        {voiceResult && (
          <div className="space-y-3 border-t border-border pt-3">
            <div className="rounded-md bg-purple-50 border border-purple-200 px-3 py-1.5 text-[11px] text-purple-800 font-medium">
              AI-GENERATED DRAFT ({voiceResult.model_name} {voiceResult.model_version}) - REVIEW BEFORE USING
            </div>
            <textarea
              rows={3}
              value={editedTranscript}
              onChange={(e) => setEditedTranscript(e.target.value)}
              className="w-full rounded-md border border-border px-3 py-2 text-sm"
            />
            <ExtractionSummary extraction={voiceResult.extraction} />
            <button
              type="button"
              onClick={applyVoiceStatement}
              className="text-xs text-navy-700 font-medium hover:underline"
            >
              {statementApplied ? "✓ Applied to officer statement below" : "Use as officer statement & autofill fields →"}
            </button>
          </div>
        )}
      </div>

      <div className="bg-surface border border-border rounded-lg p-5 space-y-4">
        <Field label="Title">
          <input required value={title} onChange={(e) => setTitle(e.target.value)} className="input" />
        </Field>
        <Field label="Officer Statement / Narrative">
          <textarea rows={4} value={description} onChange={(e) => setDescription(e.target.value)} className="input" />
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Latitude">
            <input required value={lat} onChange={(e) => setLat(e.target.value)} className="input" placeholder="5.3200" />
          </Field>
          <Field label="Longitude">
            <input required value={lon} onChange={(e) => setLon(e.target.value)} className="input" placeholder="-2.2270" />
          </Field>
        </div>
        <button type="button" onClick={useMyLocation} className="text-xs text-navy-700 font-medium hover:underline">
          📍 Use my current GPS location
        </button>

        <Field label="Incident Type">
          <select value={incidentType} onChange={(e) => setIncidentType(e.target.value as IncidentType)} className="input">
            {INCIDENT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t.replaceAll("_", " ")}
              </option>
            ))}
          </select>
        </Field>

        <div className="flex gap-5">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={waterBody} onChange={(e) => setWaterBody(e.target.checked)} className="accent-navy-700" />
            🌊 River/water body affected
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={protectedArea}
              onChange={(e) => setProtectedArea(e.target.checked)}
              className="accent-navy-700"
            />
            🌳 Forest/protected area affected
          </label>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Field label="🚜 Equipment observed">
            <input value={equipment} onChange={(e) => setEquipment(e.target.value)} className="input" placeholder="2 excavators" />
          </Field>
          <Field label="👥 Estimated people present">
            <input value={people} onChange={(e) => setPeople(e.target.value)} className="input" type="number" min={0} />
          </Field>
        </div>
      </div>

      <div className="bg-surface border border-border rounded-lg p-5 space-y-4">
        <FileCaptureList label="📸 Photos" accept="image/*" capture="environment" files={photos} onChange={setPhotos} disabled={submitting} />
        <FileCaptureList label="🎥 Video" accept="video/*" capture="environment" files={videos} onChange={setVideos} disabled={submitting} />
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        type="submit"
        disabled={submitting}
        className="w-full rounded-md bg-navy-800 text-white text-sm font-medium py-2.5 hover:bg-navy-700 disabled:opacity-50"
      >
        {submitting ? "Submitting…" : "Submit incident report"}
      </button>

      <style jsx global>{`
        .input {
          width: 100%;
          border-radius: 6px;
          border: 1px solid var(--border);
          padding: 8px 12px;
          font-size: 14px;
        }
      `}</style>
    </form>
  );
}

function ExtractionSummary({ extraction }: { extraction: VoiceExtraction }) {
  return (
    <div className="grid grid-cols-2 gap-3 text-sm">
      <ExtractField label="Time mentioned" value={extraction.time_mentioned || "-"} />
      <ExtractField label="Equipment mentioned" value={extraction.equipment_mentioned.join(", ") || "-"} />
      <ExtractField label="Water body mentioned" value={extraction.water_body_mentioned || "-"} />
      <ExtractField label="Status" value={extraction.status} />
    </div>
  );
}

function ExtractField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[11px] text-slate-400">{label}</p>
      <p className="font-medium text-navy-900">{value}</p>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-slate-500 mb-1">{label}</label>
      {children}
    </div>
  );
}
