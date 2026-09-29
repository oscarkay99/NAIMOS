// Static-demo backend: replays responses recorded from the seeded local API
// (scripts/snapshot-demo.mjs). Only active when NEXT_PUBLIC_DEMO_MODE=true.
// Writes are not persisted - they return a plausible response for the session.

export const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true";
const BASE = process.env.NEXT_PUBLIC_BASE_PATH || "";
const PASSWORD = "Demo@1234";
const TOKEN_PREFIX = "demo-token:";

/* eslint-disable @typescript-eslint/no-explicit-any */
let snapPromise: Promise<any> | null = null;
function snapshot(): Promise<any> {
  if (!snapPromise) snapPromise = fetch(`${BASE}/demo-data/snapshot.json`).then((r) => r.json());
  return snapPromise;
}

class DemoError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function currentEmail(): string | null {
  const t = typeof window === "undefined" ? null : localStorage.getItem("naimos_access_token");
  return t && t.startsWith(TOKEN_PREFIX) ? t.slice(TOKEN_PREFIX.length) : null;
}

function distance(aLat: number, aLon: number, bLat: number, bLon: number) {
  return (aLat - bLat) ** 2 + (aLon - bLon) ** 2;
}

export async function demoRequest(
  method: string,
  fullPath: string,
  body?: any
): Promise<{ data: any; total?: number }> {
  const snap = await snapshot();
  const [path, query = ""] = fullPath.split("?");
  const q = new URLSearchParams(query);
  const ok = (data: any, total?: number) => ({ data, total });

  if (path === "/api/auth/login") {
    const acct = snap.accounts[body?.email];
    if (!acct || body?.password !== PASSWORD) throw new DemoError(401, "Invalid email or password");
    return ok({ access_token: TOKEN_PREFIX + body.email, refresh_token: TOKEN_PREFIX + body.email });
  }
  if (path === "/api/auth/refresh") {
    const email = currentEmail();
    return ok({ access_token: TOKEN_PREFIX + email, refresh_token: TOKEN_PREFIX + email });
  }
  const email = currentEmail();
  if (!email || !snap.accounts[email]) throw new DemoError(401, "Not authenticated");
  if (path === "/api/auth/me") return ok(snap.accounts[email]);

  if (method === "GET") {
    if (path === "/api/incidents") {
      let items: any[] = snap.incidents;
      const status = q.get("status");
      const minRisk = q.get("min_risk");
      const search = q.get("search")?.toLowerCase();
      if (status) items = items.filter((i) => i.status === status);
      if (minRisk) items = items.filter((i) => i.risk_score >= Number(minRisk));
      if (search)
        items = items.filter((i) => `${i.title} ${i.reference_number}`.toLowerCase().includes(search));
      const offset = Number(q.get("offset") || 0);
      const limit = Number(q.get("limit") || 200);
      return ok(items.slice(offset, offset + limit), items.length);
    }
    if (path === "/api/audit-logs") {
      const a = snap.get["/api/audit-logs"];
      const offset = Number(q.get("offset") || 0);
      const limit = Number(q.get("limit") || 25);
      return ok(a.items.slice(offset, offset + limit), a.total);
    }
    if (path === "/api/location-intelligence" || path === "/api/satellite/history") {
      const lat = Number(q.get("lat")), lon = Number(q.get("lon"));
      if (path === "/api/satellite/history") return ok([]);
      const best = [...snap.locations].sort(
        (x: any, y: any) => distance(x.lat, x.lon, lat, lon) - distance(y.lat, y.lon, lat, lon)
      )[0];
      return ok(best?.data ?? null);
    }
    if (path in snap.get) return ok(snap.get[path]);
    if (fullPath in snap.get) return ok(snap.get[fullPath]);
    if (/\/(preliminary-report|evidence-package)$/.test(path)) return ok(null);
    throw new DemoError(404, "Not available in the static demo");
  }

  // Writes: replay a recorded result, or acknowledge without persisting.
  if (path === "/api/reports/generate" && snap.post.reports[body?.report_type])
    return ok(snap.post.reports[body.report_type]);
  if (path === "/api/ai/query") {
    const hit = snap.post.ai[body?.question];
    if (hit) return ok(hit);
    return ok({
      question: body?.question, detected_intent: "unsupported", answer:
        "This static demo can only answer the suggested questions. Try one of the suggestions above.",
      data: [], row_count: 0, model_name: "demo", model_version: "static", insufficient_data: true,
    });
  }
  if (path === "/api/satellite/scan" && snap.post.satelliteScan) return ok(snap.post.satelliteScan);
  if (path === "/api/risk/recalculate" || path === "/api/predictions/recalculate")
    return ok({ recalculated: true, count: snap.incidents.length, message: "Static demo: scores unchanged." });
  const m = path.match(/^\/api\/incidents\/([^/]+)\/(preliminary-report|evidence-package)$/);
  if (m && snap.get[path]) return ok(snap.get[path]);
  if (m) throw new DemoError(400, "This report is pre-generated only for incidents that have one in the static demo.");
  if (path.endsWith("/status")) return ok({ ok: true });
  throw new DemoError(400, "This action is disabled in the static demo (changes are not saved).");
}
