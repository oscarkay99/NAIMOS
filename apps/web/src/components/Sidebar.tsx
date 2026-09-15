"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { useAuth } from "@/lib/auth-context";
import { useSidebar } from "@/lib/sidebar-context";

interface NavItem {
  href: string;
  label: string;
  permission?: string;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/pro", label: "National Situation Room", permission: "dashboard:national_situation" },
  { href: "/map", label: "Map" },
  { href: "/risk-map", label: "AI Risk Map", permission: "risk:view" },
  { href: "/predictions", label: "Predictive Intelligence", permission: "prediction:view" },
  { href: "/satellite", label: "Satellite Monitoring", permission: "satellite:scan" },
  { href: "/incidents", label: "Incidents", permission: "incident:read" },
  { href: "/field", label: "Field Reporting", permission: "field_report:create" },
  { href: "/assistant", label: "Intelligence Assistant", permission: "ai:query" },
  { href: "/communications", label: "Communications", permission: "report:generate" },
  { href: "/analytics", label: "Analytics", permission: "analytics:view" },
  { href: "/audit", label: "Audit Logs", permission: "audit:view" },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, hasPermission, logout } = useAuth();
  const { open, close } = useSidebar();

  return (
    <>
      {open && (
        <div className="fixed inset-0 bg-black/40 z-20 lg:hidden" onClick={close} aria-hidden="true" />
      )}
      <aside
        className={clsx(
          "w-60 shrink-0 bg-navy-950 text-slate-200 flex flex-col h-screen fixed lg:sticky top-0 left-0 z-30 transition-transform duration-200",
          open ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        <div className="px-5 py-5 border-b border-white/10">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-md bg-navy-700 flex items-center justify-center text-xs font-semibold text-white">
              NI
            </div>
            <div>
              <p className="text-sm font-semibold text-white leading-tight">NAIMOS</p>
              <p className="text-[10px] text-slate-400 leading-tight">INTELLIGENCE</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          {NAV_ITEMS.filter((item) => !item.permission || hasPermission(item.permission)).map((item) => {
            const active = pathname?.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={close}
                className={clsx(
                  "block rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  active ? "bg-navy-700 text-white" : "text-slate-300 hover:bg-white/5 hover:text-white"
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="px-4 py-4 border-t border-white/10">
          <p className="text-sm font-medium text-white truncate">{user?.full_name}</p>
          <p className="text-xs text-slate-400 truncate">{user?.role.name.replaceAll("_", " ")}</p>
          <button
            onClick={logout}
            className="mt-3 w-full text-left text-xs text-slate-400 hover:text-white transition-colors"
          >
            Sign out
          </button>
        </div>
      </aside>
    </>
  );
}
