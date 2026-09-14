import clsx from "clsx";
import type { RiskCategory } from "@/lib/types";

const STYLES: Record<RiskCategory, string> = {
  LOW: "bg-emerald-50 text-risk-low border-emerald-200",
  MODERATE: "bg-amber-50 text-risk-moderate border-amber-200",
  ELEVATED: "bg-orange-50 text-risk-elevated border-orange-200",
  HIGH: "bg-red-50 text-risk-high border-red-200",
  CRITICAL: "bg-rose-100 text-risk-critical border-rose-300",
};

export function RiskBadge({ category, score }: { category: RiskCategory | string; score?: number | null }) {
  const cat = (category as RiskCategory) in STYLES ? (category as RiskCategory) : "LOW";
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold",
        STYLES[cat]
      )}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {typeof score === "number" ? `${score} · ` : ""}
      {cat}
    </span>
  );
}
