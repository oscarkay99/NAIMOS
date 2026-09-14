import clsx from "clsx";

export function MetricCard({
  label,
  value,
  sublabel,
  accent,
}: {
  label: string;
  value: string | number;
  sublabel?: string;
  accent?: "default" | "critical" | "high";
}) {
  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">{label}</p>
      <p
        className={clsx(
          "text-2xl font-semibold mt-1.5",
          accent === "critical" ? "text-risk-critical" : accent === "high" ? "text-risk-high" : "text-navy-900"
        )}
      >
        {value}
      </p>
      {sublabel && <p className="text-xs text-slate-400 mt-1">{sublabel}</p>}
    </div>
  );
}
