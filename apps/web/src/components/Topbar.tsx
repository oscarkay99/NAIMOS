"use client";

import { useSidebar } from "@/lib/sidebar-context";

export function Topbar({ title }: { title: string }) {
  const { toggle } = useSidebar();
  return (
    <header className="h-14 border-b border-border bg-surface flex items-center justify-between px-4 sm:px-6 sticky top-0 z-10">
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={toggle}
          aria-label="Toggle navigation menu"
          className="lg:hidden shrink-0 w-8 h-8 flex items-center justify-center rounded-md border border-border text-navy-900"
        >
          <span className="sr-only">Menu</span>
          <div className="space-y-1">
            <span className="block w-4 h-0.5 bg-current" />
            <span className="block w-4 h-0.5 bg-current" />
            <span className="block w-4 h-0.5 bg-current" />
          </div>
        </button>
        <h1 className="text-sm font-semibold text-navy-900 truncate">{title}</h1>
      </div>
      <div className="flex items-center gap-3 shrink-0">
        <span className="hidden sm:inline text-xs text-slate-400">
          {new Date().toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })}
        </span>
      </div>
    </header>
  );
}
