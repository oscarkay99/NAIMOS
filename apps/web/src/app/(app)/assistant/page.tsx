"use client";

import { useState } from "react";
import { Topbar } from "@/components/Topbar";
import { api, ApiError } from "@/lib/api";
import type { AssistantResponse } from "@/lib/types";

const SUGGESTIONS = [
  "Which districts had the most verified incidents?",
  "Show emerging hotspots",
  "Which high-risk areas have not been field verified?",
  "What incidents are near water bodies?",
  "Summarize Western region activity",
  "Show incidents that have been open for more than 5 days",
  "Generate a briefing for today's operations meeting",
];

interface Turn {
  question: string;
  response?: AssistantResponse;
  error?: string;
}

export default function AssistantPage() {
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [loading, setLoading] = useState(false);

  async function ask(q: string) {
    if (!q.trim() || loading) return;
    setLoading(true);
    setQuestion("");
    setTurns((prev) => [...prev, { question: q }]);
    try {
      const response = await api.post<AssistantResponse>("/api/ai/query", { question: q });
      setTurns((prev) => prev.map((t, i) => (i === prev.length - 1 ? { ...t, response } : t)));
    } catch (err) {
      setTurns((prev) =>
        prev.map((t, i) => (i === prev.length - 1 ? { ...t, error: err instanceof ApiError ? err.message : "Failed" } : t))
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Topbar title="NAIMOS Intelligence Assistant" />
      <div className="p-6 max-w-3xl mx-auto w-full flex flex-col gap-5">
        <div className="bg-navy-950 text-white rounded-lg p-4 text-xs leading-relaxed">
          This assistant answers strictly from verified database records using a fixed set of supported query
          intents - it never runs free-form AI-generated SQL and never invents figures. If a question has no
          matching data, it will say so.
        </div>

        {turns.length === 0 && (
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => ask(s)}
                className="text-xs bg-surface border border-border rounded-full px-3 py-1.5 hover:border-navy-700 hover:text-navy-700"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        <div className="flex-1 space-y-4">
          {turns.map((t, i) => (
            <div key={i} className="space-y-2">
              <div className="flex justify-end">
                <div className="bg-navy-800 text-white text-sm rounded-lg px-4 py-2 max-w-[80%]">{t.question}</div>
              </div>
              <div className="flex justify-start">
                <div className="bg-surface border border-border rounded-lg px-4 py-3 max-w-[85%] text-sm space-y-2">
                  {!t.response && !t.error && <p className="text-slate-400">Thinking…</p>}
                  {t.error && <p className="text-red-600">{t.error}</p>}
                  {t.response && (
                    <>
                      <pre className="whitespace-pre-wrap font-sans text-navy-900">{t.response.answer}</pre>
                      <p className="text-[11px] text-slate-400 pt-1 border-t border-border">
                        {t.response.model_name} {t.response.model_version} · intent: {t.response.detected_intent} ·{" "}
                        {t.response.row_count} row(s)
                      </p>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            ask(question);
          }}
          className="flex gap-2 sticky bottom-4"
        >
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask about verified incidents, hotspots, or field activity…"
            className="flex-1 rounded-md border border-border bg-surface px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-navy-700"
          />
          <button
            type="submit"
            disabled={loading}
            className="rounded-md bg-navy-800 text-white text-sm font-medium px-4 py-2.5 hover:bg-navy-700 disabled:opacity-50"
          >
            Ask
          </button>
        </form>
      </div>
    </>
  );
}
