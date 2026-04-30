"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Card, StatCard, Button } from "@/components/ui";
import { TechModulAPI, type OrderCostEntry, type OrderRecord } from "@/services/api";
import { 
  BarChart3, 
  TrendingDown, 
  TrendingUp, 
  RefreshCw, 
  ArrowLeft,
  Package,
  Wrench,
  Truck,
  HelpCircle
} from "lucide-react";

export default function OrderCostAnalysisPage() {
  const params = useParams();
  const orderId = Number(params.id);
  
  const [order, setOrder] = useState<OrderRecord | null>(null);
  const [entries, setEntries] = useState<OrderCostEntry[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      // We don't have getOrder, but we can search in orders list or add getOrder to API
      // For now, let's assume we fetch all and find this one, or just the costs
      const [costsData, allOrders] = await Promise.all([
        TechModulAPI.getOrderCosts(orderId),
        TechModulAPI.getOrders()
      ]);
      
      setEntries(costsData.entries);
      setSummary(costsData.summary);
      
      const foundOrder = allOrders.find(o => o.id === orderId);
      if (foundOrder) setOrder(foundOrder);
      
    } catch (e: any) {
      setError(e?.message ?? "Blad ladowania kosztow zamowienia");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (orderId) loadData();
  }, [orderId]);

  if (!orderId) return <div className="p-20 text-center">Niepoprawne ID zamowienia</div>;

  const budget = order?.budget || 0;
  const totalNet = summary?.total_net || 0;
  const variance = budget - totalNet;
  const isOverBudget = variance < 0;
  const variancePercent = budget > 0 ? (Math.abs(variance) / budget) * 100 : 0;

  const getIconForType = (type: string) => {
    switch (type.toUpperCase()) {
      case "MATERIAL": return <Package className="w-4 h-4" />;
      case "LABOR": return <Wrench className="w-4 h-4" />;
      case "TRANSPORT": return <Truck className="w-4 h-4" />;
      default: return <HelpCircle className="w-4 h-4" />;
    }
  };

  return (
    <AppShell>
      <PageHeader
        eyebrow={`Zamowienie #${orderId}`}
        title={order?.title || "Analiza kosztow"}
        subtitle="Porownanie budzetu z realnymi kosztami materialowymi i robocizna."
        actions={
          <div className="flex gap-2">
            <Button as="link" href="/orders" variant="secondary">
              <ArrowLeft className="w-4 h-4 mr-1" /> Powrot
            </Button>
            <Button onClick={loadData} disabled={loading}>
              <RefreshCw className={`w-4 h-4 mr-1 ${loading ? "animate-spin" : ""}`} />
              Odswiez
            </Button>
          </div>
        }
      />

      <div className="max-w-7xl mx-auto space-y-6 pb-20">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <StatCard label="Zalozony budzet" value={`${budget.toFixed(2)} PLN`} icon={<BarChart3 className="w-5 h-5" />} />
          <StatCard label="Koszty rzeczywiste (Net)" value={`${totalNet.toFixed(2)} PLN`} tone={isOverBudget ? "danger" : "default"} />
          <StatCard 
            label="Odchylenie (PLN)" 
            value={`${variance.toFixed(2)} PLN`} 
            tone={isOverBudget ? "danger" : "success"}
            icon={isOverBudget ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
          />
          <StatCard 
            label="Odchylenie (%)" 
            value={`${variancePercent.toFixed(1)}%`} 
            tone={isOverBudget ? "danger" : "success"}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Summary by type */}
          <Card title="Podzial kosztow">
            <div className="space-y-4">
              {(summary?.by_type || []).map((t: any) => {
                const pct = totalNet > 0 ? (t.total_net / totalNet) * 100 : 0;
                return (
                  <div key={t.cost_type}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="flex items-center gap-2 text-slate-300">
                        {getIconForType(t.cost_type)}
                        {t.cost_type}
                      </span>
                      <span className="text-white font-medium">{t.total_net.toFixed(2)} PLN</span>
                    </div>
                    <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                      <div className="h-full bg-blue-500 rounded-full" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
              {(!summary?.by_type || summary.by_type.length === 0) && (
                <p className="text-slate-500 text-sm text-center py-4">Brak zarejestrowanych kosztow.</p>
              )}
            </div>
          </Card>

          {/* History of costs */}
          <Card className="lg:col-span-2" padded={false}>
            <div className="p-4 border-b border-white/10 flex justify-between items-center">
              <span className="text-sm font-semibold">Historia kosztow</span>
              <span className="text-xs text-slate-500">{entries.length} wpisow</span>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-200/90 text-slate-900">
                  <tr>
                    <th className="text-left px-3 py-2">Data</th>
                    <th className="text-left px-3 py-2">Typ</th>
                    <th className="text-left px-3 py-2">Opis</th>
                    <th className="text-right px-3 py-2">Netto</th>
                    <th className="text-left px-3 py-2">Kto</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/10">
                  {loading ? (
                    <tr><td colSpan={5} className="p-8 text-center animate-pulse">Ladowanie...</td></tr>
                  ) : entries.length === 0 ? (
                    <tr><td colSpan={5} className="p-8 text-center text-slate-500">Brak kosztow.</td></tr>
                  ) : (
                    entries.map((e) => (
                      <tr key={e.id} className="hover:bg-white/5">
                        <td className="px-3 py-2 text-slate-400 text-xs">{e.created_at?.split(' ')[0]}</td>
                        <td className="px-3 py-2">
                          <span className="text-[10px] bg-white/5 border border-white/10 rounded px-1.5 py-0.5 text-slate-300">
                            {e.cost_type}
                          </span>
                        </td>
                        <td className="px-3 py-2">
                          <div className="text-white">{e.description}</div>
                          {e.note && <div className="text-xs text-slate-500">{e.note}</div>}
                        </td>
                        <td className="px-3 py-2 text-right font-medium text-white">{e.amount_net.toFixed(2)}</td>
                        <td className="px-3 py-2 text-slate-400 text-xs">{e.created_by}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}
