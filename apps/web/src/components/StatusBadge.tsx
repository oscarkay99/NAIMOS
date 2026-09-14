import clsx from "clsx";

const STYLES: Record<string, string> = {
  NEW: "bg-slate-100 text-slate-700 border-slate-300",
  UNDER_REVIEW: "bg-blue-50 text-blue-700 border-blue-200",
  FIELD_VERIFICATION_REQUIRED: "bg-amber-50 text-amber-800 border-amber-200",
  VERIFIED: "bg-emerald-50 text-emerald-700 border-emerald-200",
  UNVERIFIED: "bg-slate-100 text-slate-600 border-slate-300",
  PENDING_VERIFICATION: "bg-amber-50 text-amber-800 border-amber-200",
  REJECTED: "bg-red-50 text-red-700 border-red-200",
  CLOSED: "bg-slate-100 text-slate-500 border-slate-300",
  ARCHIVED: "bg-slate-100 text-slate-400 border-slate-300",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={clsx(
        "inline-block rounded border px-2 py-0.5 text-xs font-medium whitespace-nowrap",
        STYLES[status] || "bg-slate-100 text-slate-600 border-slate-300"
      )}
    >
      {status.replaceAll("_", " ")}
    </span>
  );
}
