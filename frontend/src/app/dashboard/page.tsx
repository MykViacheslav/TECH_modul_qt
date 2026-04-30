"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Card, StatCard, Button } from "@/components/ui";
import { 
  TechModulAPI, 
  type DashboardV2Response 
} from "@/services/api";
import { 
  Activity, 
  AlertCircle, 
  Package, 
  DollarSign, 
  Cpu, 
  Clock, 
  ArrowRight,
  ShieldAlert,
  Boxes,
  History,
  TrendingUp,
  RefreshCw,
  ExternalLink
} from "lucide-react";
import clsx from "clsx";

export default function DashboardV2Page() {
  const [data, setData] = useState<DashboardV2Response | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await TechModulAPI.getDashboardV2();
      setData(res);
    } catch (e: any) {
      setError(e?.message || "Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="flex flex-col items-center gap-4">
            <RefreshCw className="w-8 h-8 text-brand animate-spin" />
            <p className="text-slate-500 font-medium">Inicjalizacja centrum dowodzenia...</p>
          </div>
        </div>
      </AppShell>
    );
  }

  const summary = data?.summary;

  return (
    <AppShell>
      <PageHeader
        eyebrow="System Control"
        title="Dashboard V2"
        subtitle="Centrum operacyjne: produkcja, koszty, ryzyka i transparentnoÅ›Ä‡ zdarzeÅ„."
        actions={
          <div className="flex gap-2">
            <Button as="link" href="/kri" variant="secondary">
              <ShieldAlert className="w-4 h-4 mr-1" /> KRI
            </Button>
            <Button onClick={loadData}>
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        }
      />

      <div className="max-w-7xl mx-auto space-y-6 pb-20">
        {/* KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <StatCard label="Zlecenia" value={summary?.active_orders_count || 0} icon={<Boxes />} />
          <StatCard label="Alarmy" value={summary?.critical_alarms_count || 0} icon={<AlertCircle />} tone={summary?.critical_alarms_count ? "danger" : "default"} />
          <StatCard label="Blokady" value={summary?.blocked_production_count || 0} icon={<Activity />} tone={summary?.blocked_production_count ? "danger" : "default"} />
          <StatCard label="Braki" value={summary?.low_stock_count || 0} icon={<Package />} tone={summary?.low_stock_count ? "warn" : "default"} />
          <StatCard label="BudÅ¼et +" value={summary?.cost_overrun_count || 0} icon={<TrendingUp />} tone={summary?.cost_overrun_count ? "danger" : "default"} />
          <StatCard label="CNC" value={summary?.cnc_active_count || 0} icon={<Cpu />} tone={summary?.cnc_problem_count ? "danger" : "brand"} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Production Block */}
          <div className="lg:col-span-2 space-y-6">
            <Card title="Status Produkcji (CNC)" icon={<Cpu className="w-5 h-5 text-blue-400" />}>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div className="p-3 bg-white/5 rounded-xl border border-white/10">
                  <p className="text-[10px] text-slate-500 uppercase font-bold">W kolejce</p>
                  <p className="text-2xl font-black text-white">{data?.production.cnc_summary.waiting}</p>
                </div>
                <div className="p-3 bg-brand-soft/20 rounded-xl border border-brand-ring/30">
                  <p className="text-[10px] text-brand uppercase font-bold">W trakcie</p>
                  <p className="text-2xl font-black text-white">{data?.production.cnc_summary.active}</p>
                </div>
                <div className="p-3 bg-red-500/10 rounded-xl border border-red-500/20">
                  <p className="text-[10px] text-red-400 uppercase font-bold">Problemy</p>
                  <p className="text-2xl font-black text-white">{data?.production.cnc_summary.problem}</p>
                </div>
                <div className="p-3 bg-emerald-500/10 rounded-xl border border-emerald-500/20">
                  <p className="text-[10px] text-emerald-400 uppercase font-bold">Zrobione dziÅ›</p>
                  <p className="text-2xl font-black text-white">{data?.production.cnc_summary.done_today}</p>
                </div>
              </div>

              <div className="space-y-3">
                <p className="text-xs font-bold text-slate-500 uppercase">NajwaÅ¼niejsze alarmy produkcji</p>
                {data?.production.top_issues.length === 0 ? (
                  <p className="text-sm text-slate-600 italic">Brak aktywnych alarmÃ³w.</p>
                ) : (
                  data?.production.top_issues.map((issue: any) => (
                    <div key={issue.id} className="flex items-center justify-between p-3 bg-white/5 border border-white/10 rounded-lg hover:bg-white/10 transition-all">
                      <div>
                        <p className="text-sm font-bold text-white">{issue.title}</p>
                        <p className="text-[10px] text-slate-500">{issue.project_name}</p>
                      </div>
                      <Link href="/operations" className="text-brand hover:text-white transition-colors">
                        <ExternalLink className="w-4 h-4" />
                      </Link>
                    </div>
                  ))
                )}
              </div>
              <div className="mt-4 pt-4 border-t border-white/5 flex justify-end">
                <Button as="link" href="/stations/cnc" size="sm" variant="ghost">
                  OtwÃ³rz terminal CNC <ArrowRight className="w-3 h-3 ml-2" />
                </Button>
              </div>
            </Card>

            {/* Recent Audit Logs */}
            <Card title="Ostatnie Zdarzenia (Audit Log)" icon={<History className="w-5 h-5 text-slate-400" />} padded={false}>
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="bg-white/5 text-slate-500 uppercase font-bold text-[10px]">
                    <tr>
                      <th className="px-4 py-2">Czas</th>
                      <th className="px-4 py-2">Kto</th>
                      <th className="px-4 py-2">Akcja</th>
                      <th className="px-4 py-2">SzczegÃ³Å‚y</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {data?.recent_events.map((log) => (
                      <tr key={log.id} className="hover:bg-white/5">
                        <td className="px-4 py-2 whitespace-nowrap text-slate-500">{log.timestamp.split(' ')[1]}</td>
                        <td className="px-4 py-2 font-medium">{log.user_name || "System"}</td>
                        <td className="px-4 py-2 uppercase font-black tracking-tighter text-brand-light">{log.action.replace('INV_', '')}</td>
                        <td className="px-4 py-2 text-slate-400 truncate max-w-[200px]">{log.details}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="p-4 flex justify-end">
                <Button as="link" href="/admin/audit-log" size="sm" variant="ghost">
                  PeÅ‚na historia <ArrowRight className="w-3 h-3 ml-2" />
                </Button>
              </div>
            </Card>
          </div>

          {/* Right Sidebar */}
          <div className="space-y-6">
            {/* Cost Overruns */}
            <Card title="Przekroczenia KosztÃ³w" icon={<TrendingUp className="w-5 h-5 text-red-400" />}>
              <div className="space-y-3">
                {data?.costs.top_overruns.length === 0 ? (
                  <p className="text-sm text-slate-600 italic">Brak przekroczeÅ„ budÅ¼etu.</p>
                ) : (
                  data?.costs.top_overruns.map((overrun) => (
                    <Link key={overrun.id} href={`/orders/${overrun.id}/costs`} className="block p-3 bg-red-500/5 border border-red-500/10 rounded-lg hover:border-red-500/30 transition-all">
                      <div className="flex justify-between items-start">
                        <p className="text-sm font-bold text-white truncate max-w-[140px]">{overrun.title}</p>
                        <p className="text-xs font-black text-red-400">+{overrun.variance.toLocaleString()} PLN</p>
                      </div>
                      <div className="flex justify-between items-center mt-2 text-[10px]">
                        <p className="text-slate-500">Real: {overrun.real.toLocaleString()}</p>
                        <p className="text-slate-500">Est: {overrun.est.toLocaleString()}</p>
                      </div>
                    </Link>
                  ))
                )}
              </div>
            </Card>

            {/* Inventory Risks */}
            <Card title="Ryzyka Magazynowe" icon={<Package className="w-5 h-5 text-amber-400" />}>
              <div className="space-y-3">
                <div className="flex gap-2 mb-2">
                  <div className="flex-1 p-2 bg-red-500/10 rounded-lg text-center">
                    <p className="text-[8px] text-red-400 uppercase font-black">Scrap</p>
                    <p className="text-sm font-bold text-white">{data?.inventory.recent_scrap_count}</p>
                  </div>
                  <div className="flex-1 p-2 bg-amber-500/10 rounded-lg text-center">
                    <p className="text-[8px] text-amber-400 uppercase font-black">Fixes</p>
                    <p className="text-sm font-bold text-white">{data?.inventory.recent_corrections_count}</p>
                  </div>
                </div>

                {data?.inventory.top_low_stock.length === 0 ? (
                  <p className="text-sm text-slate-600 italic">Stan magazynowy bezpieczny.</p>
                ) : (
                  data?.inventory.top_low_stock.map((item: any) => (
                    <div key={item.id} className="flex items-center justify-between p-2 bg-white/5 rounded-lg text-xs">
                      <p className="text-slate-300 truncate max-w-[120px]">{item.name}</p>
                      <p className="font-bold text-amber-400">{item.stock_quantity} {item.unit}</p>
                    </div>
                  ))
                )}
              </div>
              <div className="mt-4 flex justify-end">
                <Button as="link" href="/inventory" size="sm" variant="ghost">
                  Magazyn <ArrowRight className="w-3 h-3 ml-2" />
                </Button>
              </div>
            </Card>

            {/* Quick Actions */}
            <Card title="Szybkie Akcje">
              <div className="grid grid-cols-2 gap-2">
                {[
                  { label: "Magazyn", href: "/inventory", icon: <Package className="w-4 h-4" /> },
                  { label: "Zakupy", href: "/inventory/purchases", icon: <DollarSign className="w-4 h-4" /> },
                  { label: "PÅ‚atnoÅ›ci", href: "/inventory/payments", icon: <TrendingUp className="w-4 h-4" /> },
                  { label: "Stacja CNC", href: "/stations/cnc", icon: <Cpu className="w-4 h-4" /> },
                  { label: "Alarmy", href: "/alarms", icon: <AlertCircle className="w-4 h-4" /> },
                  { label: "Audit Log", href: "/admin/audit-log", icon: <History className="w-4 h-4" /> },
                ].map((act) => (
                  <Link 
                    key={act.label} 
                    href={act.href} 
                    className="flex flex-col items-center gap-2 p-3 bg-white/5 border border-white/10 rounded-xl hover:bg-brand/10 hover:border-brand-ring/30 transition-all text-center"
                  >
                    <span className="text-brand">{act.icon}</span>
                    <span className="text-[10px] font-bold text-slate-300">{act.label}</span>
                  </Link>
                ))}
              </div>
            </Card>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
