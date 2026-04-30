"use client";

import { useEffect, useMemo, useState, type ComponentType, type ReactNode } from "react";
import clsx from "clsx";
import {
  AlertTriangle,
  Boxes,
  ChevronDown,
  ChevronUp,
  Factory,
  HardHat,
  Landmark,
  Loader2,
  Package,
  Wrench,
} from "lucide-react";
import { TechModulAPI, type DashboardV1Response, type GlobalSystemSummary } from "@/services/api";

function formatMoney(value?: number | null): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "brak";
  return `${value.toFixed(2)} zl`;
}

function formatHours(value?: number | null): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "0 h";
  return `${value.toFixed(1)} h`;
}

function toneClass(mode: "good" | "warn" | "danger" | "info"): string {
  if (mode === "good") return "border-emerald-500/30 bg-emerald-500/10 text-emerald-200";
  if (mode === "warn") return "border-amber-500/30 bg-amber-500/10 text-amber-200";
  if (mode === "danger") return "border-red-500/30 bg-red-500/10 text-red-200";
  return "border-cyan-500/30 bg-cyan-500/10 text-cyan-200";
}

function MiniBar({
  label,
  value,
  max,
  className,
}: {
  label: string;
  value: number;
  max: number;
  className: string;
}) {
  const width = max > 0 ? Math.max(6, Math.min(100, Math.round((value / max) * 100))) : 6;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[11px] text-slate-300">
        <span>{label}</span>
        <span className="font-black text-slate-100">{value}</span>
      </div>
      <div className="h-2 rounded-full bg-black/25">
        <div className={clsx("h-2 rounded-full", className)} style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}

function PulseCard(props: {
  title: string;
  subtitle: string;
  value: string;
  tone: "good" | "warn" | "danger" | "info";
  icon: ComponentType<{ className?: string }>;
  children?: ReactNode;
}) {
  const Icon = props.icon;
  return (
    <section className="rounded-2xl border border-white/10 bg-[#0d172c]/90 p-4 shadow-[0_18px_40px_rgba(2,8,23,0.32)]">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <div className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">{props.title}</div>
          <div className="mt-1 text-xl font-black text-slate-50">{props.value}</div>
          <div className="mt-1 text-xs text-slate-400">{props.subtitle}</div>
        </div>
        <div className={clsx("rounded-xl border p-2.5", toneClass(props.tone))}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
      {props.children}
    </section>
  );
}

export default function BusinessHealthStrip({
  scope = "Przeglad firmy",
  subtitle,
}: {
  scope?: string;
  subtitle?: string;
}) {
  const [dashboard, setDashboard] = useState<DashboardV1Response | null>(null);
  const [summary, setSummary] = useState<GlobalSystemSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [collapsed, setCollapsed] = useState<boolean>(true);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const stored = window.localStorage.getItem("businessPulse.collapsed");
    setCollapsed(stored == null ? true : stored === "1");
  }, []);

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      if (typeof window !== "undefined") {
        window.localStorage.setItem("businessPulse.collapsed", next ? "1" : "0");
      }
      return next;
    });
  };

  useEffect(() => {
    let mounted = true;
    const controller = new AbortController();
    (async () => {
      setLoading(true);
      setError("");
      try {
        const [dash, sys] = await Promise.all([
          TechModulAPI.getDashboardV1(30, 5),
          TechModulAPI.getGlobalFinanceSummary(),
        ]);
        if (!mounted || controller.signal.aborted) return;
        setDashboard(dash);
        setSummary(sys);
      } catch (e: any) {
        if (!mounted || controller.signal.aborted) return;
        setError(String(e?.message || "Nie udalo sie zaladowac podsumowania firmy"));
      } finally {
        if (mounted && !controller.signal.aborted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
      controller.abort();
    };
  }, []);

  const riskCounts = useMemo(() => {
    const risk = Number(dashboard?.operational_summary?.mvp_readiness_distribution?.risk || 0);
    const critical = Number(dashboard?.operational_summary?.mvp_readiness_distribution?.critical || 0);
    const lowStock = Number(dashboard?.materials_procurement?.low_stock_materials_count || 0);
    const overdueIssues = Number(dashboard?.production_risk?.overdue_issues_count || 0);
    return { risk, critical, lowStock, overdueIssues };
  }, [dashboard]);

  const rateCoverage = useMemo(() => {
    const total = Number(summary?.hr?.workers_total || 0);
    const ready = Number(summary?.hr?.workers_with_rate || 0);
    if (total <= 0) return 0;
    return Math.round((ready / total) * 100);
  }, [summary]);

  if (collapsed) {
    return (
      <button
        type="button"
        onClick={toggleCollapsed}
        className="flex w-full items-center justify-between gap-2 rounded-md border border-cyan-500/15 bg-[#101820] px-3 py-1.5 text-left text-sm text-slate-200 transition-colors hover:bg-[#14202b]"
        title="Rozwin Business Pulse"
      >
        <span className="inline-flex items-center gap-2">
          <span className="text-[10px] font-black uppercase tracking-[0.22em] text-cyan-300/70">Business Pulse</span>
          <span className="text-sm font-bold text-white">{scope}</span>
        </span>
        <ChevronDown className="h-4 w-4 text-cyan-300/70" />
      </button>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-between rounded-md border border-cyan-500/20 bg-[#101820] px-3 py-2 text-sm text-slate-300">
        <span className="inline-flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin" /> Ladowanie pulsu firmy...
        </span>
        <button
          type="button"
          onClick={toggleCollapsed}
          className="rounded-md p-1 text-cyan-300/70 hover:bg-white/5"
          title="Zwin Business Pulse"
        >
          <ChevronUp className="h-4 w-4" />
        </button>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-between rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
        <span className="inline-flex items-center gap-2 font-bold">
          <AlertTriangle className="h-4 w-4" /> {error}
        </span>
        <button
          type="button"
          onClick={toggleCollapsed}
          className="rounded-md p-1 text-red-200 hover:bg-white/5"
          title="Zwin Business Pulse"
        >
          <ChevronUp className="h-4 w-4" />
        </button>
      </div>
    );
  }

  const finance = summary?.finance;
  const tax = summary?.tax;
  const hr = summary?.hr;
  const production = summary?.production;
  const inventory = summary?.inventory;
  const costs = summary?.cost_insights;
  const vatBalance = Number(tax?.tax_balance ?? 0);
  const vatTone: "good" | "warn" | "danger" = vatBalance < 0 ? "good" : vatBalance > 0 ? "danger" : "warn";
  const vatToneClass =
    vatTone === "good"
      ? "text-emerald-300"
      : vatTone === "danger"
      ? "text-red-300"
      : "text-amber-300";

  return (
    <section className="space-y-2 rounded-md border border-cyan-500/15 bg-[#101820] p-3 shadow-[0_10px_28px_rgba(3,10,24,0.28)]">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <div className="text-[10px] font-black uppercase tracking-[0.22em] text-cyan-300/70">Business Pulse</div>
          <h2 className="text-2xl font-black text-white">{scope}</h2>
          <p className="text-xs text-slate-400">
            {subtitle || "Widok operacyjny: pieniadze, ryzyko, produkcja, uslugi i jakosc danych kosztowych."}
          </p>
        </div>
        <div className="flex items-start gap-2">
          <div className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-right">
            <div className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Jakosc kosztow</div>
            <div className="text-base font-black text-white">
              {String(costs?.confidence || hr?.payroll_confidence || "PARTIAL").toUpperCase()}
            </div>
            <div className="text-xs text-slate-400">{rateCoverage}% pracownikow ma stawki</div>
          </div>
          <button
            type="button"
            onClick={toggleCollapsed}
            className="rounded-xl border border-white/10 bg-white/5 p-2 text-cyan-300/70 transition-colors hover:bg-white/10 hover:text-cyan-200"
            title="Zwin Business Pulse"
          >
            <ChevronUp className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-3">
        <PulseCard
          title="Finanse"
          subtitle="Pieniadze, faktury i VAT."
          value={formatMoney(finance?.gross_profit)}
          tone={(Number(finance?.gross_profit || 0) > 0 ? "good" : "warn")}
          icon={Landmark}
        >
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-xl border border-white/10 bg-black/20 p-3">
              <div className="text-slate-500">Faktury nasze (sprzedaz)</div>
              <div className="mt-1 font-black text-white">{formatMoney(finance?.total_sales_net)}</div>
              <div className="text-[10px] text-slate-500">netto</div>
            </div>
            <div className="rounded-xl border border-white/10 bg-black/20 p-3">
              <div className="text-slate-500">Faktury inne (koszty)</div>
              <div className="mt-1 font-black text-white">{formatMoney(finance?.total_costs_net)}</div>
              <div className="text-[10px] text-slate-500">netto</div>
            </div>
            <div className="rounded-xl border border-white/10 bg-black/20 p-3">
              <div className="text-slate-500">Gotowka w kasie</div>
              <div className="mt-1 font-black text-white">{formatMoney(finance?.cash_in_hand)}</div>
            </div>
            <div className="rounded-xl border border-white/10 bg-black/20 p-3">
              <div className="text-slate-500">Saldo VAT</div>
              <div className={clsx("mt-1 font-black", vatToneClass)}>{formatMoney(tax?.tax_balance)}</div>
              <div className="text-[10px] text-slate-500">{tax?.recommendation || "-"}</div>
            </div>
          </div>
          <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 p-3">
              <div className="text-cyan-300/70">VAT nasz (nalezny)</div>
              <div className="mt-1 font-black text-cyan-100">{formatMoney(tax?.vat_collected)}</div>
              <div className="text-[10px] text-slate-500">z faktur sprzedazy</div>
            </div>
            <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 p-3">
              <div className="text-cyan-300/70">VAT inne (do odliczenia)</div>
              <div className="mt-1 font-black text-cyan-100">{formatMoney(tax?.vat_paid)}</div>
              <div className="text-[10px] text-slate-500">z faktur kosztowych</div>
            </div>
          </div>
        </PulseCard>

        <PulseCard
          title="Ryzyko"
          subtitle="Czy cos blokuje pieniadze albo terminy."
          value={`${riskCounts.critical + riskCounts.overdueIssues}`}
          tone={(riskCounts.critical + riskCounts.overdueIssues) > 0 ? "danger" : "good"}
          icon={AlertTriangle}
        >
          <div className="space-y-2">
            <MiniBar label="Projekty krytyczne" value={riskCounts.critical} max={Math.max(1, riskCounts.critical + riskCounts.risk)} className="bg-red-500" />
            <MiniBar label="Projekty ryzyka" value={riskCounts.risk} max={Math.max(1, riskCounts.critical + riskCounts.risk)} className="bg-amber-400" />
            <MiniBar label="Przeterminowane problemy" value={riskCounts.overdueIssues} max={Math.max(1, riskCounts.overdueIssues + 1)} className="bg-orange-400" />
          </div>
        </PulseCard>

        <PulseCard
          title="Produkcja i magazyn"
          subtitle="Czy firma ma czym i nad czym pracowac."
          value={`${production?.active_projects || 0} proj.`}
          tone={riskCounts.lowStock > 0 ? "warn" : "info"}
          icon={Factory}
        >
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-xl border border-white/10 bg-black/20 p-3">
              <div className="text-slate-500">Zamowienia</div>
              <div className="mt-1 font-black text-white">{production?.total_orders || 0}</div>
            </div>
            <div className="rounded-xl border border-white/10 bg-black/20 p-3">
              <div className="text-slate-500">Niski stan</div>
              <div className="mt-1 font-black text-amber-300">{riskCounts.lowStock}</div>
            </div>
            <div className="rounded-xl border border-white/10 bg-black/20 p-3 col-span-2">
              <div className="text-slate-500">Wartosc materialow</div>
              <div className="mt-1 font-black text-white">{formatMoney(inventory?.total_value)}</div>
            </div>
          </div>
        </PulseCard>
      </div>

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-4">
        <PulseCard
          title="Koszt roboczogodziny"
          subtitle={`Pracownicy aktywni: ${hr?.active_workers || 0}, zapisane godziny: ${formatHours(hr?.total_hours)}`}
          value={formatMoney(costs?.employee_hour_cost ?? hr?.average_hour_cost)}
          tone={rateCoverage >= 80 ? "good" : "warn"}
          icon={HardHat}
        />
        <PulseCard
          title="Koszt godziny produkcji"
          subtitle={`Robocizna + koszty stale. Narzut staly: ${formatMoney(costs?.overhead_hour_cost)}/h`}
          value={formatMoney(costs?.production_hour_cost)}
          tone="info"
          icon={Boxes}
        />
        <PulseCard
          title="Koszt godziny uslug"
          subtitle="Montaz, serwis, transport, pomiar i praca na miejscu."
          value={formatMoney(costs?.service_hour_cost)}
          tone="info"
          icon={Wrench}
        />
        <PulseCard
          title="Koszt godziny lakierni"
          subtitle={`Stawek brak: ${hr?.workers_missing_rate || 0} prac.`}
          value={formatMoney(costs?.lacquer_hour_cost)}
          tone={(Number(hr?.workers_missing_rate || 0) > 0 ? "warn" : "good")}
          icon={Package}
        />
      </div>

      {(costs?.notes || []).length > 0 ? (
        <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-3">
          <div className="mb-2 text-[10px] font-black uppercase tracking-[0.18em] text-amber-300/80">Uwagi do danych kosztowych</div>
          <ul className="space-y-1 text-sm text-amber-100/90">
            {(costs?.notes || []).map((note) => (
              <li key={note} className="flex items-start gap-2">
                <span className="mt-1 h-1.5 w-1.5 rounded-full bg-amber-300" />
                <span>{note}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <div className="rounded-2xl border border-white/10 bg-black/15 p-3 text-sm">
          <div className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Koszty stale / miesiac</div>
          <div className="mt-1 text-xl font-black text-white">{formatMoney(costs?.fixed_overhead_monthly)}</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-black/15 p-3 text-sm">
          <div className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Koszty zmienne / miesiac</div>
          <div className="mt-1 text-xl font-black text-white">{formatMoney(costs?.variable_overhead_monthly)}</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-black/15 p-3 text-sm">
          <div className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Narzut firmy / godzina</div>
          <div className="mt-1 text-xl font-black text-cyan-200">{formatMoney(costs?.overhead_hour_cost)}</div>
        </div>
      </div>
    </section>
  );
}
