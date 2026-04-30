"use client";

import { useEffect, useState, useMemo } from "react";
import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Card, Button } from "@/components/ui";
import { TechModulAPI, type OrderReadiness } from "@/services/api";
import { 
  Package, 
  RefreshCw, 
  AlertTriangle, 
  CheckCircle2, 
  Search,
  Filter,
  ArrowRight,
  ChevronDown,
  ChevronUp
} from "lucide-react";
import clsx from "clsx";
import Link from "next/link";

const READINESS_STYLES: Record<string, string> = {
  READY: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
  PARTIAL: "text-blue-400 bg-blue-500/10 border-blue-500/30",
  BLOCKED: "text-red-400 bg-red-500/10 border-red-500/30",
};

const READINESS_LABELS: Record<string, string> = {
  READY: "Ready for Production",
  PARTIAL: "Partially Covered",
  BLOCKED: "Material Blocked",
};

export default function OrderReadinessPage() {
  const [orders, setOrders] = useState<OrderReadiness[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await TechModulAPI.getOrderReadiness();
      setOrders(data);
    } catch (e: any) {
      setError(e?.message || "Blad ladowania gotowosci");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filtered = useMemo(() => {
    return orders.filter(o => {
      const matchesSearch = !search || 
        o.order_title.toLowerCase().includes(search.toLowerCase()) || 
        o.client_name.toLowerCase().includes(search.toLowerCase());
      const matchesFilter = filter === "all" || o.readiness === filter;
      return matchesSearch && matchesFilter;
    });
  }, [orders, search, filter]);

  return (
    <AppShell>
      <PageHeader
        eyebrow="Production Planning"
        title="Order Material Readiness"
        subtitle="Track whether active orders have all materials reserved or ordered."
        actions={
          <Button onClick={loadData} variant="secondary" disabled={loading}>
            <RefreshCw className={clsx("w-4 h-4 mr-1", loading && "animate-spin")} /> Refresh
          </Button>
        }
      />

      <div className="max-w-7xl mx-auto space-y-4 pb-20">
        <Card className="p-4 flex flex-wrap gap-4 items-center">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input 
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search order or client..."
              className="w-full bg-black/40 border border-white/10 rounded-lg pl-10 pr-4 py-2 text-sm text-white outline-none focus:border-brand/50"
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-500" />
            <select 
              value={filter}
              onChange={e => setFilter(e.target.value)}
              className="bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-brand/50"
            >
              <option value="all">Wszystkie statusy</option>
              <option value="READY">Ready</option>
              <option value="PARTIAL">Partial</option>
              <option value="BLOCKED">Blocked</option>
            </select>
          </div>
        </Card>

        {loading ? (
          <div className="py-20 text-center text-slate-500 animate-pulse">Analizowanie zamowien...</div>
        ) : filtered.length === 0 ? (
          <div className="py-20 text-center text-slate-600">Brak zamowien pasujacych do filtrow.</div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {filtered.map(order => (
              <Card key={order.order_id} padded={false} className="overflow-hidden border-white/5">
                <div 
                  className="p-4 flex items-center justify-between cursor-pointer hover:bg-white/[0.02]"
                  onClick={() => setExpandedId(expandedId === order.order_id ? null : order.order_id)}
                >
                  <div className="flex items-center gap-4">
                    <div className={clsx(
                      "w-10 h-10 rounded-lg flex items-center justify-center border",
                      order.readiness === "READY" ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" :
                      order.readiness === "PARTIAL" ? "bg-blue-500/10 border-blue-500/20 text-blue-400" :
                      "bg-red-500/10 border-red-500/20 text-red-400"
                    )}>
                      {order.readiness === "READY" ? <CheckCircle2 size={20} /> : <Package size={20} />}
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-white">{order.order_title}</h3>
                      <p className="text-xs text-slate-500">{order.client_name}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-8">
                    <div className="hidden md:flex items-center gap-4">
                      <div className="text-center">
                        <div className="text-[9px] text-slate-600 font-black uppercase">Ready</div>
                        <div className="text-sm font-bold text-slate-300">{order.ready_count}</div>
                      </div>
                      <div className="text-center">
                        <div className="text-[9px] text-slate-600 font-black uppercase">Partial</div>
                        <div className="text-sm font-bold text-blue-400">{order.partial_count}</div>
                      </div>
                      <div className="text-center">
                        <div className="text-[9px] text-slate-600 font-black uppercase">Blocked</div>
                        <div className="text-sm font-bold text-red-500">{order.blocked_count}</div>
                      </div>
                    </div>

                    <div className={clsx(
                      "px-3 py-1 rounded-full text-[10px] font-black uppercase border tracking-widest",
                      READINESS_STYLES[order.readiness]
                    )}>
                      {READINESS_LABELS[order.readiness]}
                    </div>

                    <div className="text-slate-500">
                      {expandedId === order.order_id ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                    </div>
                  </div>
                </div>

                {expandedId === order.order_id && (
                  <div className="px-4 pb-4 pt-0 animate-in fade-in slide-in-from-top-2">
                    <div className="border-t border-white/5 mt-2 pt-4">
                      <h4 className="text-[10px] font-black uppercase text-slate-600 mb-3 tracking-widest">Material Breakdown</h4>
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                        {order.materials.map((mat, idx) => (
                          <div key={idx} className="bg-black/20 border border-white/5 p-3 rounded-lg flex items-center justify-between group">
                            <div>
                              <div className="text-xs font-bold text-slate-200 group-hover:text-brand transition-colors">{mat.name}</div>
                              <div className="text-[10px] text-slate-500">{mat.reserved_qty} {mat.unit} reserved</div>
                            </div>
                            <div className="flex items-center gap-3">
                              <div className={clsx(
                                "w-2 h-2 rounded-full shadow-glow",
                                mat.status === "READY" ? "bg-emerald-500 shadow-emerald-500/50" :
                                mat.status === "PARTIAL" ? "bg-blue-500 shadow-blue-500/50" :
                                "bg-red-500 shadow-red-500/50"
                              )} />
                              {mat.status !== "READY" && (
                                <Link href={`/procurement/execution?search=${encodeURIComponent(mat.name)}`}>
                                  <ArrowRight size={14} className="text-slate-600 hover:text-white transition-colors cursor-pointer" />
                                </Link>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </Card>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
