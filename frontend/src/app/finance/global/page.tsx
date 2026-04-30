"use client";

import AppShell from "@/components/AppShell";
import BusinessHealthStrip from "@/components/BusinessHealthStrip";
import PageHeader from "@/components/PageHeader";
import { Button, Card } from "@/components/ui";
import dynamic from "next/dynamic";
import clsx from "clsx";
import {
  TrendingUp,
  TrendingDown,
  Users,
  Package,
  ArrowUpRight,
  ArrowDownRight,
  Landmark,
  PiggyBank,
  AlertCircle
} from "lucide-react";
import { useEffect, useState } from "react";
import { TechModulAPI, type GlobalSystemSummary } from "@/services/api";
const GlobalFinanceBarChart = dynamic(() => import("@/components/finance/GlobalFinanceBarChart"), {
  ssr: false,
});

export default function GlobalFinancePage() {
  const [summary, setSummary] = useState<GlobalSystemSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    TechModulAPI.getGlobalFinanceSummary().then(data => {
      setSummary(data);
      setLoading(false);
    });
  }, []);

  const chartData = summary ? [
    { name: 'SprzedaLL (Netto)', value: summary.finance.total_sales_net, color: '#3b82f6' },
    { name: 'Koszty (Netto)', value: summary.finance.total_costs_net, color: '#ef4444' },
    { name: 'Zysk', value: summary.finance.gross_profit, color: '#10b981' },
  ] : [];

  return (
    <AppShell>
      <PageHeader
        eyebrow="Business Intelligence"
        title={<>Sytuacja <span className="text-brand-hover">Finansowa Firmy</span></>}
        subtitle="Analiza przychodow, kosztow, stanu magazynowego i rozliczen VAT."
        actions={<Button as="link" href="/finance/fixed-costs" variant="secondary">Wydatki stale</Button>}
      />

      <div className="mb-6">
        <BusinessHealthStrip
          scope="Finanse globalne i koszt godziny"
          subtitle="Koszt godziny liczony z robocizny i kosztow stalych firmy."
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {/* Sales / Profit */}
        <StatCard
          title="Przychody Netto"
          value={`${summary?.finance.total_sales_net.toLocaleString()} PLN`}
          icon={TrendingUp}
          trend="+12%"
          positive={true}
        />
        <StatCard
          title="Koszty Firmowe"
          value={`${summary?.finance.total_costs_net.toLocaleString()} PLN`}
          icon={TrendingDown}
          trend="+5%"
          positive={false}
        />
        <StatCard
          title="Saldo Kasy"
          value={`${summary?.finance.cash_in_hand.toLocaleString()} PLN`}
          icon={PiggyBank}
          detail="GotAwka w firmie"
        />
        <StatCard
          title="WartoLA Magazynu"
          value={`${summary?.inventory.total_value.toLocaleString()} PLN`}
          icon={Package}
          detail={`${summary?.inventory.materials_types} typAw plyt`}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Chart */}
        <Card className="lg:col-span-2 p-6 bg-panel-solid/40 border-brand-ring/10">
           <div className="flex items-center justify-between mb-8">
              <h3 className="eyebrow-brand">Struktura Finansowa</h3>
              <div className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Wszystkie projekty</div>
           </div>

           <GlobalFinanceBarChart chartData={chartData} loading={loading} />
        </Card>

        {/* Tax Section */}
        <Card className="p-6 bg-panel-solid/40 border-brand-ring/10">
           <div className="flex items-center gap-3 mb-6">
              <Landmark className="w-5 h-5 text-purple-400" />
              <h3 className="eyebrow-brand">Rozliczenie VAT</h3>
           </div>

           <div className="space-y-6">
              <TaxItem label="VAT Nalezny (Sprzedaz)" value={summary?.tax.vat_collected ?? 0} color="text-emerald-400" />
              <TaxItem label="VAT Naliczony (Zakupy)" value={summary?.tax.vat_paid ?? 0} color="text-orange-400" />

              <div className="pt-6 border-t border-white/5">
                 <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Saldo VAT</span>
                    <span className={clsx(
                      "px-2 py-0.5 rounded text-[8px] font-black uppercase italic",
                      (summary?.tax.tax_balance ?? 0) > 0 ? "bg-red-500/10 text-red-400" : "bg-emerald-500/10 text-emerald-400"
                    )}>
                      {summary?.tax.recommendation}
                    </span>
                 </div>
                 <div className="text-3xl font-black text-white italic tabular-nums">
                    {summary?.tax.tax_balance.toLocaleString()} <span className="text-sm font-normal not-italic text-slate-500">PLN</span>
                 </div>
              </div>

              <div className="p-4 rounded-xl bg-blue-500/5 border border-blue-500/10 flex items-start gap-3">
                 <AlertCircle className="w-4 h-4 text-blue-400 mt-0.5" />
                 <p className="text-[11px] text-slate-400 leading-relaxed">
                    Pamietaj o terminowym oplaceniu skladek do 25. dnia miesiaca. System bazuje na wprowadzonych fakturach kosztowych.
                 </p>
              </div>
           </div>
        </Card>

        {/* Employee Costs */}
        <Card className="p-6 bg-panel-solid/40 border-brand-ring/10">
           <div className="flex items-center gap-3 mb-6">
              <Users className="w-5 h-5 text-blue-400" />
              <h3 className="eyebrow-brand">Koszty Pracownicze</h3>
           </div>

           <div className="space-y-4">
              <div className="flex justify-between items-end border-b border-white/5 pb-4">
                 <div>
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Suma Godzin</div>
                    <div className="text-2xl font-black text-white">{summary?.hr.total_hours} h</div>
                 </div>
                 <div className="text-right">
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest text-emerald-500">Koszt Netto</div>
                    <div className="text-2xl font-black text-emerald-400">{summary?.hr.estimated_payroll_net.toLocaleString()} PLN</div>
                 </div>
              </div>

              <div className="grid grid-cols-2 gap-4 pt-2">
                 <div className="p-3 rounded-xl bg-white/5">
                    <div className="text-[9px] font-bold text-slate-500 uppercase mb-1">Aktywni dzisiaj</div>
                    <div className="text-lg font-black text-white">{summary?.hr.active_workers}</div>
                 </div>
                 <div className="p-3 rounded-xl bg-white/5">
                    <div className="text-[9px] font-bold text-slate-500 uppercase mb-1">Produkcja (Szt.)</div>
                    <div className="text-lg font-black text-white">{summary?.production.total_modules}</div>
                 </div>
              </div>
           </div>
        </Card>

        {/* Production Stats */}
        <Card className="p-6 bg-panel-solid/40 border-brand-ring/10 flex flex-col justify-between">
           <div>
              <div className="flex items-center gap-3 mb-6">
                 <ArrowUpRight className="w-5 h-5 text-emerald-400" />
                 <h3 className="eyebrow-brand">Skutecznosc</h3>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed mb-6">
                 Obecnie realizujesz <strong>{summary?.production.active_projects}</strong> projektow rozdzielonych na <strong>{summary?.production.total_orders}</strong> zamowienia produkcyjne.
              </p>
           </div>

           <button className="w-full py-4 rounded-xl bg-brand/10 border border-brand/20 text-brand-hover text-[10px] font-black uppercase tracking-widest hover:bg-brand/20 transition-all flex items-center justify-center gap-2">
              Generuj Raport PDF <ArrowDownRight className="w-3 h-3 rotate-[-45deg]" />
           </button>
        </Card>
      </div>
    </AppShell>
  );
}

function StatCard({ title, value, icon: Icon, trend, positive, detail }: any) {
  return (
    <Card className="p-5 bg-panel-solid/30 border-white/5 hover:border-brand-hover/30 transition-all">
       <div className="flex items-start justify-between mb-4">
          <div className="text-[10px] font-black text-slate-500 uppercase tracking-widest">{title}</div>
          <div className="p-2 rounded-lg bg-white/5 text-brand-hover">
             <Icon className="w-4 h-4" />
          </div>
       </div>
       <div className="text-2xl font-black text-white italic tracking-tighter mb-2">{value}</div>
       <div className="flex items-center gap-2">
          {trend ? (
            <div className={clsx(
              "flex items-center text-[10px] font-bold",
              positive ? "text-emerald-500" : "text-red-500"
            )}>
               {positive ? <ArrowUpRight className="w-3 h-3 mr-0.5" /> : <ArrowDownRight className="w-3 h-3 mr-0.5" />}
               {trend}
            </div>
          ) : null}
          <div className="text-[10px] font-medium text-slate-600 truncate">{detail}</div>
       </div>
    </Card>
  );
}

function TaxItem({ label, value, color }: any) {
   return (
      <div className="flex items-center justify-between">
         <div className="text-[10px] font-bold text-slate-400">{label}</div>
         <div className={clsx("text-sm font-black italic", color)}>{value.toLocaleString()} PLN</div>
      </div>
   );
}

