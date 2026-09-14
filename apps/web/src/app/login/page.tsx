"use client";

import { FormEvent, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/api";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-navy-950 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-lg bg-navy-700 text-white font-semibold text-lg mb-4">
            NI
          </div>
          <h1 className="text-2xl font-semibold text-white tracking-tight">NAIMOS INTELLIGENCE</h1>
          <p className="text-navy-600 text-sm mt-1 text-slate-300">
            AI-Assisted Illegal Mining Intelligence &amp; Operations Platform
          </p>
        </div>

        <form onSubmit={handleSubmit} className="bg-surface rounded-xl shadow-xl p-8 space-y-5">
          <div className="rounded-md bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-800 font-medium">
            DEMO ENVIRONMENT - DATA IS SIMULATED
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="officer@naimos.gov.gh"
              className="w-full rounded-md border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-navy-700 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Demo@1234"
              className="w-full rounded-md border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-navy-700 focus:border-transparent"
            />
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-md bg-navy-800 text-white text-sm font-medium py-2.5 hover:bg-navy-700 transition-colors disabled:opacity-60"
          >
            {submitting ? "Signing in..." : "Sign in"}
          </button>

          <p className="text-xs text-slate-500 pt-2 border-t border-border">
            Demo accounts (password <code className="font-mono">Demo@1234</code>): admin@naimos.gov.gh,
            officer@naimos.gov.gh, analyst@naimos.gov.gh, pro@naimos.gov.gh, auditor@naimos.gov.gh
          </p>
        </form>
      </div>
    </div>
  );
}
