"use client";

import React, { useEffect, useState, useMemo } from "react";
import { motion } from "framer-motion";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from "recharts";
import {
  Activity, Target, Users, TrendingUp, AlertCircle, Package,
  ShieldAlert, Cpu, RefreshCw, DollarSign, Clock, Boxes,
  ArrowRight, CheckCircle2, Flame, History
} from "lucide-react";
import AppShell from "@/components/AppShell";
import { Card, Button } from "@/components/ui";
import {
  TechModulAPI,
  type DashboardV1Response,
  type DashboardV2Response,
  type GlobalSystemSummary,
} from "@/services/api";
import clsx from "clsx";
import Link from "next/link";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmt(v?: number | null, decimals = 0): string {
  if (typeof v !== "number" || !Number.isFinite(v)) return "—";
  return v.toFixed(decimals).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
}

function fmtMoney(v?: number | null): string {
  if (typeof v !== "number" || !Number.isFinite(v)) return "—";
  return `${v.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, " ")} zł`;
}

// ─── Stat Card ───────────────────────────────────────────────────────────────

function KpiCard({
  label, value, icon: Icon, tone = "neutral", href,
}: {
  label: string; value: string | number; icon: any;
  tone?: "good" | "warn" | "danger" | "neutral"; href?: string;
}) {
  const toneRing = {
    good: "border-emerald-500/25 bg-emerald-500/8",
    warn: "border-amber-500/25 bg-amber-500/8",
    danger: "border-red-500/25 bg-red-500/8",
    neutral: "border-white/8 bg-white/3",
  }[tone];
  const iconTone = {
    good: "text-emerald-400", warn: "text-amber-400",
    danger: "text-red-400", neutral: "text-sky-400",
  }[tone];

  const inner = (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className={clsx(
        "group relative flex flex-col gap-2 rounded-2xl border p-4 transition-all hover:border-white/20",
        toneRing
      )}
    >
      <div className="flex items-center gap-2">
        <Icon className={clsx("h-4 w-4 shrink-0", iconTone)} />
        <span className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">{label}</span>
      </div>
      <div className="text-2xl font-black text-white tabular-nums">{value}</div>
      {href && <ArrowRight className="absolute right-3 bottom-3 h-3.5 w-3.5 text-white/20 group-hover:text-white/50 transition-colors" />}
    </motion.div>
  );

  return href ? <Link href={href}>{inner}</Link> : inner;
}

// ─── Section Header ──────────────────────────────────────────────────────────

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[10px] font-black uppercase tracking-[0.22em] text-slate-600 mb-2">{children}</div>
  );
}

// ─── Mini stat ───────────────────────────────────────────────────────────────

function MiniStat({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded-xl border border-white/8 bg-black/20 p-3">
      <div className="text-[10px] text-slate-500">{label}</div>
      <div className={clsx("mt-1 text-base font-black", tone || "text-white")}>{value}</div>
    </div>
  );
}

// ─── Colors for pie ───────────────────────────────────────────────────────────

const PIE_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#6366f1"];

const ORDER_STATE_LABELS: Record<string, string> = {
  new: "Nowe", quoted: "Wycenione", confirmed: "Potwierdzone",
  in_production: "W produkcji", ready: "Gotowe", delivered: "Dostarczone",
  cancelled: "Anulowane",
};

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function OverviewPage() {
  const [v1, setV1] = useState<DashboardV1Response | null>(null);
  const [v2, setV2] = useState<DashboardV2Response | null>(null);
  const [global, setGlobal] = useState<GlobalSystemSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshedAt, setRefreshedAt] = useState<Date>(new Date());

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [r1, r2, rg] = await Promise.all([
        TechModulAPI.getDashboardV1(30, 6),
        TechModulAPI.getDashboardV2(),
        TechModulAPI.getGlobalFinanceSummary(),
      ]);
      setV1(r1); setV2(r2); setGlobal(rg);
      setRefreshedAt(new Date());
    } catch (e: any) {
      setError(e?.message ?? "Błąd ładowania danych");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  // ─── Derived data ──────────────────────────────────────────────────────────

  const orderPieData = useMemo(() => {
    if (!v1?.operational_summary?.orders_by_state) return [];
    return Object.entries(v1.operational_summary.orders_by_state)
      .filter(([, val]) => Number(val) > 0)
      .map(([name, value]) => ({
        name: ORDER_STATE_LABELS[name] ?? name,
        value: Number(value),
      }));
  }, [v1]);

  const workstationData = useMemo(() => {
    if (!v1?.production_risk?.workstation_task_load) return [];
    return v1.production_risk.workstation_task_load
      .map(item => ({
        name: item.task_type.split("_").pop()?.toUpperCase() ?? item.task_type,
        count: item.count,
      }))
      .slice(0, 8);
  }, [v1]);

  const readiness = v1?.operational_summary?.mvp_readiness_distribution;
  const totalReadiness = (readiness?.ready ?? 0) + (readiness?.risk ?? 0) + (readiness?.critical ?? 0);
  const readinessPct = totalReadiness > 0
    ? Math.round(((readiness?.ready ?? 0) / totalReadiness) * 100)
    : 0;

  const cnc = v2?.production?.cnc_summary;
  const finance = global?.finance;
  const hr = global?.hr;
  const costs = global?.cost_insights;
  const profit = finance?.gross_profit ?? 0;

  const recentEvents: any[] = (v2 as any)?.recent_events ?? [];

  // ─── Loading / Error ───────────────────────────────────────────────────────

  if (loading) {
    return (
      <AppShell>
        <div className="flex h-full items-center justify-center">
          <div className="flex flex-col items-center gap-4 text-slate-500">
            <RefreshCw className="h-8 w-8 animate-spin text-sky-500" />
            <p className="text-sm font-medium">Ładowanie centrum dowodzenia...</p>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="h-full w-full overflow-y-auto custom-scrollbar p-5 space-y-6">

        {/* ── Header ── */}
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.28em] text-sky-500">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-sky-500 animate-pulse" />
              Live telemetria
            </div>
            <h1 className="mt-1 text-3xl font-black text-white tracking-tight">Centrum Dowodzenia</h1>
            <p className="mt-1 text-sm text-slate-500">
              Produkcja · Finanse · Ryzyko · Stan magazynu — odświeżono {refreshedAt.toLocaleTimeString("pl-PL")}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {error && (
              <span className="flex items-center gap-1.5 rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300">
                <AlertCircle className="h-3.5 w-3.5" /> {error}
              </span>
            )}
            <Button onClick={load} variant="secondary">
              <RefreshCw className="h-4 w-4" /> Odśwież
            </Button>
          </div>
        </div>

        {/* ── Row 1: KPI Strip ── */}
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
          <KpiCard label="Aktywne projekty" value={v1?.operational_summary?.active_projects_count ?? "—"}
            icon={Target} href="/workspace" tone="neutral" />
          <KpiCard label="Aktywne zlecenia" value={v2?.summary?.active_orders_count ?? "—"}
            icon={Activity} href="/orders/new" tone="neutral" />
          <KpiCard label="Alarmy krytyczne" value={v2?.summary?.critical_alarms_count ?? "—"}
            icon={AlertCircle} href="/kri"
            tone={(v2?.summary?.critical_alarms_count ?? 0) > 0 ? "danger" : "good"} />
          <KpiCard label="Blokady produkcji" value={v2?.summary?.blocked_production_count ?? "—"}
            icon={ShieldAlert} href="/production"
            tone={(v2?.summary?.blocked_production_count ?? 0) > 0 ? "warn" : "good"} />
          <KpiCard label="Braki materiałów" value={v2?.summary?.low_stock_count ?? "—"}
            icon={Package} href="/procurement/availability"
            tone={(v2?.summary?.low_stock_count ?? 0) > 0 ? "warn" : "good"} />
          <KpiCard label="Zysk brutto" value={fmtMoney(profit)}
            icon={TrendingUp} href="/finance"
            tone={profit > 0 ? "good" : profit < 0 ? "danger" : "warn"} />
        </div>

        {/* ── Row 2: Two columns — Finance + Production ── */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">

          {/* Finance block */}
          <div className="rounded-2xl border border-white/8 bg-[#0d1a2d]/90 p-5 space-y-4">
            <SectionLabel>Finanse</SectionLabel>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <MiniStat label="Sprzedaż netto" value={fmtMoney(finance?.total_sales_net)} />
              <MiniStat label="Koszty netto" value={fmtMoney(finance?.total_costs_net)} />
              <MiniStat label="Zysk brutto" value={fmtMoney(finance?.gross_profit)}
                tone={profit >= 0 ? "text-emerald-300" : "text-red-300"} />
              <MiniStat label="Gotówka w kasie" value={fmtMoney(finance?.cash_in_hand)} />
            </div>
            <div className="border-t border-white/8 pt-3 grid grid-cols-2 gap-2 text-xs">
              <MiniStat label="Saldo VAT" value={fmtMoney(global?.tax?.tax_balance)}
                tone={(() => {
                  const b = global?.tax?.tax_balance ?? 0;
                  return b < 0 ? "text-emerald-300" : b > 0 ? "text-red-300" : "text-amber-300";
                })()} />
              <MiniStat label="Pracownicy aktywni" value={String(hr?.active_workers ?? "—")} />
              <MiniStat label="Koszt roboczogodziny" value={fmtMoney(costs?.employee_hour_cost ?? hr?.average_hour_cost)} />
              <MiniStat label="Koszt godz. produkcji" value={fmtMoney(costs?.production_hour_cost)} />
            </div>
            <div className="border-t border-white/8 pt-3 grid grid-cols-3 gap-2 text-xs">
              <MiniStat label="Koszty stałe/mies." value={fmtMoney(costs?.fixed_overhead_monthly)} />
              <MiniStat label="Koszty zmienne/mies." value={fmtMoney(costs?.variable_overhead_monthly)} />
              <MiniStat label="Narzut/godz." value={fmtMoney(costs?.overhead_hour_cost)} />
            </div>
            <div className="pt-1">
              <Link href="/finance" className="text-[11px] text-sky-400 hover:text-sky-300 flex items-center gap-1">
                Pełne zestawienie finansowe <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </div>

          {/* Production + Risk block */}
          <div className="rounded-2xl border border-white/8 bg-[#0d1a2d]/90 p-5 space-y-4">
            <SectionLabel>Produkcja i ryzyko</SectionLabel>

            {/* CNC status */}
            <div>
              <div className="mb-2 flex items-center gap-2 text-xs font-bold text-slate-400">
                <Cpu className="h-3.5 w-3.5" /> Status CNC
              </div>
              <div className="grid grid-cols-4 gap-2 text-xs">
                {[
                  { label: "W kolejce", value: cnc?.waiting ?? 0, tone: "text-slate-300" },
                  { label: "W trakcie", value: cnc?.active ?? 0, tone: "text-sky-300" },
                  { label: "Problemy", value: cnc?.problem ?? 0, tone: (cnc?.problem ?? 0) > 0 ? "text-red-300" : "text-slate-500" },
                  { label: "Gotowe dziś", value: cnc?.done_today ?? 0, tone: "text-emerald-300" },
                ].map(item => (
                  <div key={item.label} className="rounded-xl border border-white/8 bg-black/20 p-3 text-center">
                    <div className={clsx("text-xl font-black", item.tone)}>{item.value}</div>
                    <div className="mt-1 text-[10px] text-slate-500">{item.label}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* MVP Readiness */}
            <div>
              <div className="mb-2 flex items-center justify-between text-xs font-bold text-slate-400">
                <span className="flex items-center gap-2"><CheckCircle2 className="h-3.5 w-3.5" /> Gotowość MVP</span>
                <span className="text-white font-black">{readinessPct}% gotowe</span>
              </div>
              <div className="space-y-1.5">
                {[
                  { label: "Gotowe", value: readiness?.ready ?? 0, max: totalReadiness, cls: "bg-emerald-500" },
                  { label: "Ryzyko", value: readiness?.risk ?? 0, max: totalReadiness, cls: "bg-amber-400" },
                  { label: "Krytyczne", value: readiness?.critical ?? 0, max: totalReadiness, cls: "bg-red-500" },
                ].map(item => (
                  <div key={item.label} className="space-y-0.5">
                    <div className="flex justify-between text-[10px] text-slate-400">
                      <span>{item.label}</span><span className="font-bold text-white">{item.value}</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-white/8">
                      <div
                        className={clsx("h-1.5 rounded-full", item.cls)}
                        style={{ width: `${item.max > 0 ? Math.max(4, (item.value / item.max) * 100) : 0}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Production risk */}
            <div className="border-t border-white/8 pt-3 grid grid-cols-3 gap-2 text-xs">
              <MiniStat label="Aktywne trasy" value={String(v1?.production_risk?.routes_active_count ?? "—")} />
              <MiniStat label="Trasy po terminie"
                value={String(v1?.production_risk?.routes_overdue_count ?? "—")}
                tone={(v1?.production_risk?.routes_overdue_count ?? 0) > 0 ? "text-amber-300" : "text-white"} />
              <MiniStat label="Problemy krytyczne"
                value={String(v1?.production_risk?.critical_issues_count ?? "—")}
                tone={(v1?.production_risk?.critical_issues_count ?? 0) > 0 ? "text-red-300" : "text-white"} />
            </div>
          </div>
        </div>

        {/* ── Row 3: Three columns — orders pie + cost overruns + low stock ── */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

          {/* Orders by state — pie */}
          <div className="rounded-2xl border border-white/8 bg-[#0d1a2d]/90 p-5">
            <SectionLabel>Zlecenia wg stanu</SectionLabel>
            {orderPieData.length > 0 ? (
              <>
                <div className="h-[180px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={orderPieData} innerRadius={50} outerRadius={75}
                        paddingAngle={4} dataKey="value">
                        {orderPieData.map((_, idx) => (
                          <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{ backgroundColor: "#0f172a", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "10px", fontSize: "11px" }}
                        itemStyle={{ color: "#fff" }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="grid grid-cols-2 gap-1 mt-2">
                  {orderPieData.map((item, idx) => (
                    <div key={item.name} className="flex items-center gap-1.5 text-[10px] text-slate-400">
                      <div className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: PIE_COLORS[idx % PIE_COLORS.length] }} />
                      {item.name}: <span className="font-bold text-white">{item.value}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="flex h-[180px] items-center justify-center text-xs text-slate-600">Brak danych</div>
            )}
          </div>

          {/* Cost overruns */}
          <div className="rounded-2xl border border-white/8 bg-[#0d1a2d]/90 p-5">
            <SectionLabel>Przekroczenia kosztów</SectionLabel>
            <div className="space-y-2">
              {(v2?.costs?.top_overruns ?? []).length > 0 ? (
                (v2?.costs?.top_overruns ?? []).slice(0, 6).map((item: any) => (
                  <div key={item.id} className="flex items-center justify-between text-xs border-b border-white/5 pb-2 last:border-0 last:pb-0">
                    <span className="truncate text-slate-300 max-w-[130px]" title={item.title}>{item.title}</span>
                    <span className="text-red-400 font-black shrink-0">+{fmtMoney(item.variance)}</span>
                  </div>
                ))
              ) : (
                <div className="flex h-[180px] items-center justify-center text-xs text-slate-600 flex-col gap-2">
                  <CheckCircle2 className="h-6 w-6 text-emerald-500/40" />
                  <span>Brak przekroczeń</span>
                </div>
              )}
            </div>
          </div>

          {/* Low stock */}
          <div className="rounded-2xl border border-white/8 bg-[#0d1a2d]/90 p-5">
            <SectionLabel>Krytyczne braki materiałów</SectionLabel>
            <div className="space-y-2">
              {(v1?.materials_procurement?.top_critical_low_stock ?? []).length > 0 ? (
                (v1.materials_procurement?.top_critical_low_stock ?? []).slice(0, 6).map(item => (
                  <div key={item.id} className="flex items-center justify-between text-xs border-b border-white/5 pb-2 last:border-0 last:pb-0">
                    <span className="truncate text-slate-300 max-w-[140px]" title={item.name}>{item.name}</span>
                    <span className="text-amber-400 font-black shrink-0">{fmt(item.missing_qty)} {item.unit}</span>
                  </div>
                ))
              ) : (
                <div className="flex h-[180px] items-center justify-center text-xs text-slate-600 flex-col gap-2">
                  <Package className="h-6 w-6 text-emerald-500/40" />
                  <span>Magazyn OK</span>
                </div>
              )}
            </div>
            <div className="mt-3">
              <Link href="/procurement/availability" className="text-[11px] text-sky-400 hover:text-sky-300 flex items-center gap-1">
                Dostępność materiałów <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </div>
        </div>

        {/* ── Row 4: Workstation load bar chart ── */}
        {workstationData.length > 0 && (
          <div className="rounded-2xl border border-white/8 bg-[#0d1a2d]/90 p-5">
            <SectionLabel>Obciążenie stanowisk</SectionLabel>
            <div className="h-[160px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={workstationData} layout="vertical" margin={{ left: 0 }}>
                  <XAxis type="number" hide />
                  <YAxis dataKey="name" type="category" stroke="#475569" fontSize={10}
                    width={90} tickLine={false} axisLine={false} />
                  <Tooltip
                    cursor={{ fill: "rgba(255,255,255,0.04)" }}
                    contentStyle={{ backgroundColor: "#0f172a", border: "none", borderRadius: "8px", fontSize: "11px" }}
                    itemStyle={{ color: "#fff" }}
                  />
                  <Bar dataKey="count" fill="#3b82f6" radius={[0, 4, 4, 0]} barSize={14} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* ── Row 5: Recent events ── */}
        {recentEvents.length > 0 && (
          <div className="rounded-2xl border border-white/8 bg-[#0d1a2d]/90 p-5">
            <SectionLabel>Ostatnie zdarzenia (Audit Log)</SectionLabel>
            <div className="space-y-0 divide-y divide-white/5">
              {recentEvents.slice(0, 8).map((ev: any, idx: number) => (
                <div key={idx} className="flex items-center gap-3 py-2.5 text-xs">
                  <History className="h-3.5 w-3.5 text-slate-600 shrink-0" />
                  <span className="w-32 shrink-0 text-slate-500 tabular-nums">
                    {ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString("pl-PL", { hour: "2-digit", minute: "2-digit" }) : "—"}
                  </span>
                  <span className="text-slate-400 shrink-0 w-24 truncate">{ev.user ?? ev.who ?? "—"}</span>
                  <span className="text-slate-300 truncate">{ev.action ?? ev.message ?? JSON.stringify(ev)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Footer ── */}
        <div className="text-[10px] text-slate-700 text-right pb-2">
          Dane z serwera: {v1?.generated_at ? new Date(v1.generated_at).toLocaleString("pl-PL") : "—"}
        </div>

      </div>
    </AppShell>
  );
}
