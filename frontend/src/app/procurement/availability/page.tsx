"use client";

import { useEffect, useState, useMemo } from "react";
import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Card, Button } from "@/components/ui";
import { TechModulAPI, type ProcurementItem } from "@/services/api";
import { 
  Package, 
  Search, 
  RefreshCw, 
  ArrowUpRight, 
  AlertTriangle, 
  CheckCircle2, 
  ShoppingCart,
  Boxes,
  Truck
} from "lucide-react";
import clsx from "clsx";
import Link from "next/link";

export default function ProcurementAvailabilityPage() {
  const [items, setItems] = useState<ProcurementItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await TechModulAPI.getProcurementAvailability();
      setItems(data);
    } catch (e: any) {
      setError(e?.message || "Failed to load procurement data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const categories = useMemo(() => {
    const cats = new Set(items.map(i => i.category).filter(Boolean));
    return ["all", ...Array.from(cats)];
  }, [items]);

  const filtered = useMemo(() => {
    return items.filter(i => {
      const matchesSearch = !search || 
        i.name.toLowerCase().includes(search.toLowerCase()) || 
        i.code?.toLowerCase().includes(search.toLowerCase());
      const matchesCat = categoryFilter === "all" || i.category === categoryFilter;
      return matchesSearch && matchesCat;
    });
  }, [items, search, categoryFilter]);

  const stats = useMemo(() => {
    return {
      total: items.length,
      shortages: items.filter(i => i.status !== "OK").length,
      critical: items.filter(i => i.status === "CRITICAL").length
    };
  }, [items]);

  return (
    <AppShell>
      <PageHeader
        eyebrow="Supply Chain"
        title="Material Availability"
        subtitle="Track stock levels, reservations, and incoming materials across all orders."
        actions={
          <div className="flex gap-2">
            <Link href="/procurement/suggestions">
              <Button variant="primary">
                <ShoppingCart className="w-4 h-4 mr-2" /> Purchase Suggestions
              </Button>
            </Link>
            <Button onClick={loadData} variant="secondary" disabled={loading}>
              <RefreshCw className={clsx("w-4 h-4 mr-1", loading && "animate-spin")} /> Refresh
            </Button>
          </div>
        }
      />

      <div className="max-w-7xl mx-auto space-y-4 pb-20">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white/5 border border-white/10 p-4 rounded-xl">
            <div className="text-slate-500 text-[10px] font-black uppercase mb-1">Total Materials</div>
            <div className="text-2xl font-bold text-white flex items-center gap-2">
              <Boxes className="w-5 h-5 text-blue-400" /> {stats.total}
            </div>
          </div>
          <div className="bg-white/5 border border-white/10 p-4 rounded-xl">
            <div className="text-slate-500 text-[10px] font-black uppercase mb-1">Active Shortages</div>
            <div className="text-2xl font-bold text-orange-400 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5" /> {stats.shortages}
            </div>
          </div>
          <div className="bg-white/5 border border-white/10 p-4 rounded-xl">
            <div className="text-slate-500 text-[10px] font-black uppercase mb-1">Critical (Under-reserved)</div>
            <div className="text-2xl font-bold text-red-500 flex items-center gap-2">
              <Package className="w-5 h-5" /> {stats.critical}
            </div>
          </div>
        </div>

        <Card className="p-4 flex flex-wrap gap-4 items-center">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input 
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search material or code..."
              className="w-full bg-black/40 border border-white/10 rounded-lg pl-10 pr-4 py-2 text-sm text-white outline-none focus:border-brand/50 transition-colors"
            />
          </div>
          <select 
            value={categoryFilter}
            onChange={e => setCategoryFilter(e.target.value)}
            className="bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-sm text-white outline-none focus:border-brand/50"
          >
            {categories.map(c => (
              <option key={c} value={c}>{c === "all" ? "All Categories" : c}</option>
            ))}
          </select>
        </Card>

        <Card padded={false} className="overflow-hidden border-white/5">
          <table className="w-full text-sm">
            <thead className="bg-white/[0.03] border-b border-white/5 text-slate-400">
              <tr>
                <th className="text-left p-4 font-bold uppercase text-[10px] tracking-wider">Material</th>
                <th className="text-right p-4 font-bold uppercase text-[10px] tracking-wider">On Hand</th>
                <th className="text-right p-4 font-bold uppercase text-[10px] tracking-wider">Reserved</th>
                <th className="text-right p-4 font-bold uppercase text-[10px] tracking-wider">Incoming</th>
                <th className="text-right p-4 font-bold uppercase text-[10px] tracking-wider">Available</th>
                <th className="text-right p-4 font-bold uppercase text-[10px] tracking-wider">Status</th>
                <th className="w-10 p-4"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {loading ? (
                <tr>
                  <td colSpan={7} className="p-10 text-center animate-pulse text-slate-500">Loading availability...</td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-10 text-center text-slate-600">No materials found matching filters.</td>
                </tr>
              ) : (
                filtered.map(item => (
                  <tr key={item.material_id} className="hover:bg-white/[0.01] transition-colors group">
                    <td className="p-4">
                      <div className="font-bold text-slate-200 group-hover:text-brand transition-colors">{item.name}</div>
                      <div className="text-[10px] text-slate-500 font-mono">{item.code || `ID: ${item.material_id}`} • {item.category}</div>
                      
                      {item.demand_orders.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {item.demand_orders.map(o => (
                            <Link key={o.order_id} href={`/operations?search=${encodeURIComponent(o.order_title)}`}>
                              <span className="text-[9px] bg-blue-500/10 text-blue-400 border border-blue-500/20 px-1.5 py-0.5 rounded-sm hover:bg-blue-500/20 cursor-pointer transition-colors">
                                {o.order_title}: {o.qty}{item.unit}
                              </span>
                            </Link>
                          ))}
                        </div>
                      )}
                    </td>
                    <td className="p-4 text-right font-mono text-slate-300">{item.qty_on_hand} {item.unit}</td>
                    <td className="p-4 text-right font-mono text-slate-400">{item.qty_reserved} {item.unit}</td>
                    <td className="p-4 text-right font-mono text-blue-400">
                      {item.qty_incoming > 0 ? (
                        <div className="flex items-center justify-end gap-1">
                          <Truck className="w-3 h-3" /> {item.qty_incoming}
                        </div>
                      ) : "-"}
                    </td>
                    <td className="p-4 text-right font-mono">
                      <span className={clsx(
                        item.qty_available < 0 ? "text-red-400 font-bold" : "text-emerald-400"
                      )}>
                        {item.qty_available} {item.unit}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      {item.status === "OK" ? (
                        <div className="inline-flex items-center gap-1 text-[10px] font-black text-emerald-500 uppercase">
                          <CheckCircle2 className="w-3 h-3" /> Ready
                        </div>
                      ) : (
                        <div className={clsx(
                          "inline-flex items-center gap-1 text-[10px] font-black uppercase px-2 py-0.5 rounded border",
                          item.status === "CRITICAL" ? "bg-red-500/10 text-red-500 border-red-500/30" : "bg-orange-500/10 text-orange-500 border-orange-500/30"
                        )}>
                          <AlertTriangle className="w-3 h-3" /> {item.status}
                        </div>
                      )}
                    </td>
                    <td className="p-4 text-right">
                      <Link href={`/inventory?search=${encodeURIComponent(item.name)}`}>
                        <Button variant="ghost" size="sm" className="p-1 h-auto text-slate-500 hover:text-white">
                          <ArrowUpRight className="w-4 h-4" />
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </Card>
      </div>
    </AppShell>
  );
}
