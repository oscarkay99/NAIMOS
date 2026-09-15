"use client";

import { useEffect, useRef, useState } from "react";

type RecorderState = "idle" | "requesting" | "recording" | "recorded" | "unsupported" | "denied";

/** Live in-browser voice recording via MediaRecorder - not a file upload
 * picker. Falls back gracefully (still offers a file-upload input) if the
 * browser/device denies microphone access or doesn't support the API,
 * since that's a real possibility on some mobile browsers/permissions. */
export function VoiceRecorder({
  onRecordingReady,
  disabled,
}: {
  onRecordingReady: (file: File | null) => void;
  disabled?: boolean;
}) {
  const [state, setState] = useState<RecorderState>("idle");
  const [seconds, setSeconds] = useState(0);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined" && (!navigator.mediaDevices || !window.MediaRecorder)) {
      setState("unsupported");
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  async function startRecording() {
    setState("requesting");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];

      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        const url = URL.createObjectURL(blob);
        setAudioUrl(url);
        const ext = (recorder.mimeType || "audio/webm").includes("mp4") ? "m4a" : "webm";
        onRecordingReady(new File([blob], `field-voice-note.${ext}`, { type: blob.type }));
        setState("recorded");
        stream.getTracks().forEach((t) => t.stop());
      };

      recorder.start();
      setState("recording");
      setSeconds(0);
      timerRef.current = setInterval(() => setSeconds((s) => s + 1), 1000);
    } catch {
      setState("denied");
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    if (timerRef.current) clearInterval(timerRef.current);
  }

  function reRecord() {
    setAudioUrl(null);
    onRecordingReady(null);
    setState("idle");
  }

  function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) {
      setAudioUrl(URL.createObjectURL(file));
      onRecordingReady(file);
      setState("recorded");
    }
  }

  const timeLabel = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;

  if (state === "unsupported" || state === "denied") {
    return (
      <div className="space-y-2">
        <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-3 py-2">
          {state === "denied"
            ? "Microphone access was denied. You can still upload an audio file instead."
            : "Live recording isn't supported in this browser. You can still upload an audio file instead."}
        </p>
        <input type="file" accept="audio/*" onChange={handleFileUpload} className="text-sm" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-3">
        {state === "idle" && (
          <button
            type="button"
            onClick={startRecording}
            disabled={disabled}
            className="flex items-center gap-2 rounded-md bg-red-600 text-white text-sm font-medium px-4 py-2 hover:bg-red-700 disabled:opacity-50"
          >
            <span className="w-2.5 h-2.5 rounded-full bg-white" />
            Record voice narrative
          </button>
        )}
        {state === "requesting" && <p className="text-sm text-slate-500">Requesting microphone access…</p>}
        {state === "recording" && (
          <button
            type="button"
            onClick={stopRecording}
            className="flex items-center gap-2 rounded-md bg-navy-800 text-white text-sm font-medium px-4 py-2 hover:bg-navy-700"
          >
            <span className="w-2.5 h-2.5 rounded-sm bg-white animate-pulse" />
            Stop ({timeLabel})
          </button>
        )}
        {state === "recorded" && (
          <>
            <audio controls src={audioUrl || undefined} className="h-9" />
            <button type="button" onClick={reRecord} className="text-xs text-navy-700 font-medium hover:underline">
              Re-record
            </button>
          </>
        )}
      </div>
      {state === "idle" && (
        <p className="text-[11px] text-slate-400">
          Or{" "}
          <label className="text-navy-700 hover:underline cursor-pointer">
            upload an audio file
            <input type="file" accept="audio/*" onChange={handleFileUpload} className="hidden" />
          </label>{" "}
          instead.
        </p>
      )}
    </div>
  );
}
