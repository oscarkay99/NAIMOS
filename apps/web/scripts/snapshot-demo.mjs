// Records real responses from the locally running, seeded API into
// public/demo-data/snapshot.json so the static GitHub Pages build can replay them.
import { writeFileSync, mkdirSync } from "node:fs";

const API = process.env.API_URL || "http://localhost:8000";
const PASSWORD = "Demo@1234";
const ACCOUNTS = [
  "admin", "national.admin", "ops.manager", "supervisor", "officer", "officer2",
  "analyst", "env.analyst", "pro",
].map((n) => `${n}@naimos.gov.gh`);
const REPORT_TYPES = ["press_briefing", "social_media_briefing", "weekly_situation",
  "parliamentary_briefing", "media_qa", "executive_brief", "talking_points"];
const QUESTIONS = process.env.QUESTIONS ? JSON.parse(process.env.QUESTIONS) : [];

async function call(path, token, opts = {}) {
  const r = await fetch(API + path, {
    method: opts.method || "GET",
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (!r.ok) return { __status: r.status };
  const total = r.headers.get("x-total-count");
  const data = r.status === 204 ? null : await r.json();
  return total ? { __total: Number(total), data } : { data };
}

const snap = { accounts: {}, get: {}, incidents: [], post: { reports: {}, ai: {}, preliminary: {}, evidencePackage: {} }, locations: [] };

for (const email of ACCOUNTS) {
  const l = await call("/api/auth/login", null, { method: "POST", body: { email, password: PASSWORD } });
  if (!l.data) { console.warn("login failed", email); continue; }
  const me = await call("/api/auth/me", l.data.access_token);
  snap.accounts[email] = me.data;
}
const admin = (await call("/api/auth/login", null, { method: "POST", body: { email: "admin@naimos.gov.gh", password: PASSWORD } })).data.access_token;

const grab = async (path) => { const r = await call(path, admin); if (!r.__status) snap.get[path] = r.data; else console.warn(r.__status, path); return r.data; };
snap.incidents = (await call("/api/incidents?limit=200", admin)).data;
for (const p of ["/api/map/features", "/api/analytics/summary", "/api/analytics/national-situation",
  "/api/risk/leaderboard?limit=50", "/api/predictions/leaderboard?limit=50", "/api/satellite/status"]) await grab(p);
snap.get["/api/audit-logs"] = (await call("/api/audit-logs?limit=200&offset=0", admin)).data;

for (const inc of snap.incidents) {
  const id = inc.id;
  await grab(`/api/incidents/${id}`);
  await grab(`/api/evidence/incident/${id}`);
  await grab(`/api/risk/incidents/${id}`);
  await grab(`/api/incidents/${id}/preliminary-report`);
  await grab(`/api/incidents/${id}/evidence-package`);
  const li = await call(`/api/location-intelligence?lat=${inc.latitude}&lon=${inc.longitude}`, admin);
  if (li.data) snap.locations.push({ lat: inc.latitude, lon: inc.longitude, data: li.data });
}
for (const t of REPORT_TYPES) {
  const r = await call("/api/reports/generate", admin, { method: "POST", body: { report_type: t } });
  if (r.data) snap.post.reports[t] = r.data; else console.warn("report", t, r.__status);
}
for (const q of QUESTIONS) {
  const r = await call("/api/ai/query", admin, { method: "POST", body: { question: q } });
  if (r.data) snap.post.ai[q] = r.data;
}
const first = snap.incidents[0];
if (first) {
  const s = await call("/api/satellite/scan", admin, { method: "POST", body: { latitude: first.latitude, longitude: first.longitude } });
  if (s.data) snap.post.satelliteScan = s.data;
}
mkdirSync("public/demo-data", { recursive: true });
writeFileSync("public/demo-data/snapshot.json", JSON.stringify(snap));
console.log("incidents", snap.incidents.length, "keys", Object.keys(snap.get).length, "reports", Object.keys(snap.post.reports).length);
