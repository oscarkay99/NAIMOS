export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center py-16 text-sm text-slate-400">
      <span className="inline-block w-4 h-4 mr-2 border-2 border-slate-300 border-t-navy-700 rounded-full animate-spin" />
      {label}
    </div>
  );
}

export function EmptyState({ label = "No data found." }: { label?: string }) {
  return (
    <div className="flex items-center justify-center py-16 text-sm text-slate-400 border border-dashed border-border rounded-lg">
      {label}
    </div>
  );
}

export function ErrorState({ label = "Something went wrong.", detail }: { label?: string; detail?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-sm text-red-600 border border-red-200 bg-red-50 rounded-lg gap-1">
      <span className="font-medium">{label}</span>
      {detail && <span className="text-xs text-red-500">{detail}</span>}
    </div>
  );
}

export function PermissionDenied() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-sm text-slate-500 border border-dashed border-border rounded-lg gap-1">
      <span className="font-medium">Access restricted</span>
      <span className="text-xs">Your role does not have permission to view this section.</span>
    </div>
  );
}
