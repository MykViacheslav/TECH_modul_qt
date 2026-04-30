"use client";

import { useEffect, useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Card, Button } from "@/components/ui";
import { TechModulAPI, type ProcurementItem } from "@/services/api";
import { 
  ShoppingCart, 
  RefreshCw, 
  AlertTriangle, 
  Package,
  Plus,
  Truck,
  History,
  FileSearch,
  ExternalLink
} from "lucide-react";
import clsx from "clsx";
import Link from "next/link";

export default function ProcurementSuggestionsPage() {
  const [items, setItems] = useState<ProcurementItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [executing, setExecuting] = useState<number | null>(null);
  const router = useRouter();

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await TechModulAPI.getPurchaseSuggestions();
      setItems(data);
    } catch (e: any) {
      setError(e?.message || "Failed to load suggestions");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const startExecution = async (item: ProcurementItem) => {
    setExecuting(item.material_id);
    try {
      await TechModulAPI.createProcurementExecution({
        material_id: item.material_id,
        qty_target: item.shortage,
        status: "missing",
        priority: item.status === "CRITICAL" ? "krytyczny" : "normalny",
        order_id: item.demand_orders.length > 0 ? item.demand_orders[0].order_id : null
      });
      router.push(`/procurement/execution?search=${encodeURIComponent(item.name)}`);
    } catch (e: any) {
      alert(e?.message || "Failed to start execution");
    } finally {
      setExecuting(null);
    }
  };

  return (
    <AppShell>
      <PageHeader
        eyebrow="Purchasing"
        title="Purchase Suggestions"
        subtitle="Automatic detection of material shortages for active production orders."
        actions={
          <div className="flex gap-2">
            <Link href="/inventory/purchases">
              <Button variant="secondary">
                <History className="w-4 h-4 mr-2" /> Recent Purchases
              </Button>
            </Link>
            <Button onClick={loadData} disabled={loading}>
              <RefreshCw className={clsx("w-4 h-4 mr-1", loading && "animate-spin")} /> Refresh
            </Button>
          </div>
        }
      />

      <div className="max-w-6xl mx-auto space-y-6 pb-20">
        {loading ? (
          <div className="py-20 text-center animate-pulse text-slate-500">Calculating shortages...</div>
        ) : error ? (
          <Card className="p-10 text-center border-red-500/20">
            <AlertTriangle className="w-12 h-12 text-red-500/50 mx-auto mb-4" />
            <p className="text-red-400 font-bold">{error}</p>
          </Card>
        ) : items.length === 0 ? (
          <div className="py-20 text-center space-y-4">
            <div className="w-16 h-16 bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto">
              <Package className="w-8 h-8 text-emerald-500/40" />
            </div>
            <h3 className="text-lg font-medium text-slate-300">No shortages detected</h3>
            <p className="text-sm text-slate-500 max-w-sm mx-auto">All active reservations and safety stocks are currently covered by on-hand inventory or incoming purchases.</p>
            <Link href="/procurement/availability">
              <Button variant="ghost" className="text-brand">View Availability Dashboard</Button>
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {items.map(item => (
              <Card key={item.material_id} padded={false} className="overflow-hidden group hover:border-brand/30 transition-all">
                <div className="flex flex-col md:flex-row">
                  <div className={clsx(
                    "w-1 md:w-2 shrink-0",
                    item.status === "CRITICAL" ? "bg-red-500" : "bg-orange-500"
                  )} />
                  
                  <div className="p-5 flex-1 bg-white/[0.02]">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className={clsx(
                            "text-[10px] font-black uppercase px-2 py-0.5 rounded border",
                            item.status === "CRITICAL" ? "bg-red-500/10 text-red-500 border-red-500/30" : "bg-orange-500/10 text-orange-500 border-orange-500/30"
                          )}>
                            {item.status}
                          </span>
                          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">{item.category}</span>
                        </div>
                        <h3 className="text-lg font-bold text-white group-hover:text-brand transition-colors">{item.name}</h3>
                        <p className="text-xs text-slate-400 mt-1">Shortage: <span className="text-red-400 font-bold">{item.shortage} {item.unit}</span></p>
                      </div>

                      <div className="flex items-center gap-6">
                        <div className="text-right">
                          <div className="text-[10px] text-slate-500 font-black uppercase">On Hand</div>
                          <div className="text-sm font-mono text-slate-300">{item.qty_on_hand} {item.unit}</div>
                        </div>
                        <div className="text-right">
                          <div className="text-[10px] text-slate-500 font-black uppercase">Incoming</div>
                          <div className="text-sm font-mono text-blue-400">{item.qty_incoming} {item.unit}</div>
                        </div>
                        <div className="text-right">
                          <div className="text-[10px] text-slate-500 font-black uppercase">Need</div>
                          <div className="text-sm font-mono text-white">{item.qty_reserved + item.min_stock} {item.unit}</div>
                        </div>
                      </div>
                    </div>

                    <div className="mt-4 pt-4 border-t border-white/5 flex flex-col md:flex-row md:items-center justify-between gap-4">
                      <div className="flex flex-wrap gap-2 items-center">
                        <span className="text-[10px] text-slate-500 font-black uppercase mr-2">Required by:</span>
                        {item.demand_orders.map(o => (
                          <div key={o.order_id} className="group/order flex items-center gap-1.5 px-2 py-1 bg-white/5 border border-white/10 rounded-sm text-[10px] text-slate-400">
                            <span className="font-bold text-slate-300">{o.order_title}</span>
                            <span>({o.qty}{item.unit})</span>
                            <Link href={`/operations?search=${encodeURIComponent(o.order_title)}`}>
                              <ExternalLink size={10} className="hover:text-brand cursor-pointer transition-colors" />
                            </Link>
                          </div>
                        ))}
                        {item.min_stock > 0 && (
                          <div className="px-2 py-1 bg-white/5 border border-white/10 rounded-sm text-[10px] text-slate-500 italic">
                            + {item.min_stock}{item.unit} Safety Stock
                          </div>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        <Link href={`/inventory/purchases?search=${encodeURIComponent(item.name)}`}>
                          <Button variant="secondary" size="sm">
                            <FileSearch className="w-3.5 h-3.5 mr-2" /> Check Existing
                          </Button>
                        </Link>
                        <Button 
                          variant="primary" 
                          size="sm" 
                          onClick={() => startExecution(item)}
                          disabled={executing === item.material_id}
                        >
                          <Plus className={clsx("w-3.5 h-3.5 mr-2", executing === item.material_id && "animate-spin")} /> Start Execution
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
