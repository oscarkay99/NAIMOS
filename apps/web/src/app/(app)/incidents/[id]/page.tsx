import { readFileSync } from "node:fs";
import { join } from "node:path";
import IncidentDetailPage from "./IncidentDetailClient";

// Only the static demo build (output: "export") needs the ids up front; the
// normal server build renders any id on demand.
export function generateStaticParams() {
  if (process.env.NEXT_PUBLIC_DEMO_MODE !== "true") return [];
  const snap = JSON.parse(readFileSync(join(process.cwd(), "public/demo-data/snapshot.json"), "utf8"));
  return snap.incidents.map((i: { id: string }) => ({ id: i.id }));
}

export default function Page() {
  return <IncidentDetailPage />;
}
