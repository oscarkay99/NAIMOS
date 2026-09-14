"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Topbar } from "@/components/Topbar";
import { api, ApiError } from "@/lib/api";
import type { IncidentType, VoiceExtraction, VoiceReportTranscribeOut } from "@/lib/types";

const INCIDENT_TYPES: IncidentType[] = [
  "SUSPECTED_ILLEGAL_MINING",
  "LAND_DISTURBANCE",
  "WATER_POLLUTION",
  "VEGETATION_LOSS",
  "UNAUTHORIZED_EQUIPMENT",
  "OTHER",
];

export default function FieldReportingPage() {
  const [tab, setTab] = useState<"incident" | "voice">("incident");
  return (
    <>
      <Topbar title="Field Reporting" />
      <div className="p-4 sm:p-6 max-w-2xl mx-auto w-full">
        <div className="flex gap-2 mb-5">
          <TabButton active={tab === "incident"} onClick={() => setTab("incident")} label="New Incident" />
          <TabButton active={tab === "voice"} onClick={() => setTab("voice")} label="Voice-to-Report" />
        </div>
        {tab === "incident" ? <IncidentForm /> : <VoiceReportFlow />}
      </div>
    </>
  );
}

function TabButton({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`flex-1 rounded-md px-4 py-2.5 text-sm font-medium border ${
        active ? "bg-navy-800 text-white border-navy-800" : "bg-surface text-slate-600 border-border"
      }`}
    >
      {label}
    </button>
  );
}

function IncidentForm() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const [incidentType, setIncidentType] = useState<IncidentType>("SUSPECTED_ILLEGAL_MINING");
  const [waterBody, setWaterBody] = useState(false);
  const [protectedArea, setProtectedArea] = useState(false);
  const [equipment, setEquipment] = useState("");
  const [people, setPeople] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  function useMyLocation() {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition((pos) => {
      setLat(pos.coords.latitude.toFixed(6));
      setLon(pos.coords.longitude.toFixed(6));
    });
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setSuccess(null);
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
      setSuccess(`Incident ${created.reference_number} created.`);
      setTitle("");
      setDescription("");
      setEquipment("");
      setPeople("");
      setTimeout(() => router.push(`/incidents/${created.id}`), 900);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create incident");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="bg-surface border border-border rounded-lg p-5 space-y-4">
      <Field label="Title">
        <input required value={title} onChange={(e) => setTitle(e.target.value)} className="input" />
      </Field>
      <Field label="Narrative / Description">
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
        Use my current GPS location
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
          Water body affected
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={protectedArea}
            onChange={(e) => setProtectedArea(e.target.checked)}
            className="accent-navy-700"
          />
          Protected area affected
        </label>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Field label="Equipment observed">
          <input value={equipment} onChange={(e) => setEquipment(e.target.value)} className="input" placeholder="2 excavators" />
        </Field>
        <Field label="Estimated people present">
          <input value={people} onChange={(e) => setPeople(e.target.value)} className="input" type="number" min={0} />
        </Field>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {success && <p className="text-sm text-emerald-700">{success}</p>}

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

function VoiceReportFlow() {
  const [file, setFile] = useState<File | null>(null);
  const [transcribing, setTranscribing] = useState(false);
  const [approving, setApproving] = useState(false);
  const [result, setResult] = useState<VoiceReportTranscribeOut | null>(null);
  const [editedTranscript, setEditedTranscript] = useState("");
  const [editedExtraction, setEditedExtraction] = useState<VoiceExtraction | null>(null);
  const [approved, setApproved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submitVoiceNote(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setTranscribing(true);
    setError(null);
    setApproved(false);
    try {
      const form = new FormData();
      form.append("file", file);
      const resp = await api.postForm<VoiceReportTranscribeOut>("/api/field-reports/voice", form);
      setResult(resp);
      setEditedTranscript(resp.transcript);
      setEditedExtraction(resp.extraction);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to transcribe voice note");
    } finally {
      setTranscribing(false);
    }
  }

  async function approve() {
    if (!result) return;
    setApproving(true);
    setError(null);
    try {
      await api.post("/api/field-reports/voice/approve", {
        field_report_id: result.field_report_id,
        edited_transcript: editedTranscript,
        edited_extraction: editedExtraction,
      });
      setApproved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to approve report");
    } finally {
      setApproving(false);
    }
  }

  return (
    <div className="space-y-5">
      <div className="bg-surface border border-border rounded-lg p-5">
        <p className="text-xs text-slate-500 mb-3">
          Upload a voice note (any audio file). The AI will transcribe it and draft structured fields - you must
          review and approve before it becomes part of the record. The original audio is always preserved.
        </p>
        <form onSubmit={submitVoiceNote} className="flex flex-col sm:flex-row gap-3">
          <input
            type="file"
            accept="audio/*"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="flex-1 text-sm"
          />
          <button
            type="submit"
            disabled={!file || transcribing}
            className="rounded-md bg-navy-800 text-white text-sm font-medium px-4 py-2 hover:bg-navy-700 disabled:opacity-50"
          >
            {transcribing ? "Transcribing…" : "Transcribe"}
          </button>
        </form>
        {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
      </div>

      {result && (
        <div className="bg-surface border border-border rounded-lg p-5 space-y-4">
          <div className="rounded-md bg-purple-50 border border-purple-200 px-3 py-1.5 text-[11px] text-purple-800 font-medium">
            AI-GENERATED DRAFT ({result.model_name} {result.model_version}) - REQUIRES OFFICER REVIEW
          </div>

          <div>
            <label className="text-xs font-medium text-slate-500">Transcript</label>
            <textarea
              rows={3}
              value={editedTranscript}
              onChange={(e) => setEditedTranscript(e.target.value)}
              className="w-full rounded-md border border-border px-3 py-2 text-sm mt-1"
            />
          </div>

          {editedExtraction && (
            <div className="grid grid-cols-2 gap-3 text-sm">
              <ExtractField label="Time mentioned" value={editedExtraction.time_mentioned || "-"} />
              <ExtractField label="Equipment mentioned" value={editedExtraction.equipment_mentioned.join(", ") || "-"} />
              <ExtractField label="Water body mentioned" value={editedExtraction.water_body_mentioned || "-"} />
              <ExtractField label="Status" value={editedExtraction.status} />
            </div>
          )}

          {!approved ? (
            <button
              onClick={approve}
              disabled={approving}
              className="w-full rounded-md bg-emerald-700 text-white text-sm font-medium py-2.5 hover:bg-emerald-800 disabled:opacity-50"
            >
              {approving ? "Approving…" : "Approve and finalize report"}
            </button>
          ) : (
            <p className="text-sm text-emerald-700 font-medium">
              ✓ Officer-approved. This record is now part of the field intelligence log.
            </p>
          )}
        </div>
      )}
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
