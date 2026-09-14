"use client";

import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from "recharts";
import { Topbar } from "@/components/Topbar";
import { MetricCard } from "@/components/MetricCard";
import { LoadingState, ErrorState } from "@/components/States";
import { api, ApiError } from "@/lib/api";
import type { AnalyticsSummary } from "@/lib/types";

const AXIS_COLOR = "#94a3b8";

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<AnalyticsSummary>("/api/analytics/summary")
      .then(setData)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load analytics"));
  }, []);

  if (error) return <div className="p-6"><ErrorState detail={error} /></div>;
  if (!data) return <LoadingState />;

  const verificationPct = data.verification_rate.total
    ? Math.round((data.verification_rate.verified / data.verification_rate.total) * 100)
    : 0;

  return (
    <>
      <Topbar title="Analytics" />
      <div className="p-6 space-y-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard label="Verification Rate" value={`${verificationPct}%`} sublabel={`${data.verification_rate.verified} of ${data.verification_rate.total}`} />
          <MetricCard label="Regions with Activity" value={data.incidents_by_region.length} />
          <MetricCard label="Active Teams" value={data.team_workload.length} />
          <MetricCard label="Weeks Tracked" value={data.incidents_over_time.length} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ChartCard title="Incidents Over Time (weekly)">
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={data.incidents_over_time}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="week" tick={{ fontSize: 11, fill: AXIS_COLOR }} />
                <YAxis tick={{ fontSize: 11, fill: AXIS_COLOR }} allowDecimals={false} />
                <Tooltip />
                <Line type="monotone" dataKey="count" stroke="#16345a" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Incidents by Region">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={data.incidents_by_region} layout="vertical" margin={{ left: 24 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis type="number" tick={{ fontSize: 11, fill: AXIS_COLOR }} allowDecimals={false} />
                <YAxis dataKey="region" type="category" tick={{ fontSize: 11, fill: AXIS_COLOR }} width={110} />
                <Tooltip />
                <Bar dataKey="count" fill="#1e4676" radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Incidents by Status">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={data.incidents_by_status}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="status" tick={{ fontSize: 10, fill: AXIS_COLOR }} interval={0} angle={-20} textAnchor="end" height={60} />
                <YAxis tick={{ fontSize: 11, fill: AXIS_COLOR }} allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="count" fill="#c98a12" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Investigation Workload by Team">
            <div className="divide-y divide-border">
              {data.team_workload.length === 0 && <p className="text-xs text-slate-400 py-4">No assignments recorded.</p>}
              {data.team_workload.map((t) => (
                <div key={t.team} className="py-2.5 text-sm flex items-center justify-between">
                  <span className="font-medium text-navy-900">{t.team}</span>
                  <span className="text-xs text-slate-500">
                    Active {t.active} · High {t.high_priority} · Overdue {t.overdue} · Completed {t.completed}
                  </span>
                </div>
              ))}
            </div>
          </ChartCard>
        </div>
      </div>
    </>
  );
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <h3 className="text-sm font-semibold text-navy-900 mb-2">{title}</h3>
      {children}
    </div>
  );
}
