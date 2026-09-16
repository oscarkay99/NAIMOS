interface PagerProps {
  total: number;
  limit: number;
  offset: number;
  onOffsetChange: (offset: number) => void;
  itemLabel?: string;
}

export function Pager({ total, limit, offset, onOffsetChange, itemLabel = "result" }: PagerProps) {
  if (total <= limit && offset === 0) return null;

  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + limit, total);
  const canPrev = offset > 0;
  const canNext = offset + limit < total;

  return (
    <div className="flex items-center justify-between gap-3 px-1 py-2 text-xs text-slate-500">
      <p>
        Showing <span className="font-medium text-navy-900">{from}-{to}</span> of{" "}
        <span className="font-medium text-navy-900">{total}</span> {itemLabel}
        {total === 1 ? "" : "s"}
      </p>
      <div className="flex items-center gap-2">
        <button
          onClick={() => onOffsetChange(Math.max(0, offset - limit))}
          disabled={!canPrev}
          className="rounded-md border border-border px-3 py-1.5 font-medium text-navy-800 hover:bg-slate-50 disabled:opacity-40 disabled:hover:bg-transparent"
        >
          Previous
        </button>
        <button
          onClick={() => onOffsetChange(offset + limit)}
          disabled={!canNext}
          className="rounded-md border border-border px-3 py-1.5 font-medium text-navy-800 hover:bg-slate-50 disabled:opacity-40 disabled:hover:bg-transparent"
        >
          Next
        </button>
      </div>
    </div>
  );
}
