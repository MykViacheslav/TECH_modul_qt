"use client";

import { useEffect, useState, useMemo } from "react";
import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Card, Button, StatCard } from "@/components/ui";
import { TechModulAPI } from "@/services/api";
import { 
  FileText, 
  Search, 
  Plus, 
  RefreshCw, 
  Filter,
  Calendar,
  Clock,
  User,
  Activity,
  ArrowRight,
  ExternalLink,
  ClipboardList
} from "lucide-react";
import Link from "next/link";
import clsx from "clsx";
import { motion } from "framer-motion";

export default function OrdersListPage() {
  const [orders, setOrders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      // TechModulAPI.getOrders is usually available as it maps to GET /orders
      const data = await TechModulAPI.getOrders();
      setOrders(data || []);
    } catch (e: any) {
      setError(e?.message ?? "Błąd ładowania listy zleceń");
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
        o.title?.toLowerCase().includes(search.toLowerCase()) || 
        o.client_name?.toLowerCase().includes(search.toLowerCase());
      
      const matchesFilter = filter === "all" || o.status === filter;
      return matchesSearch && matchesFilter;
    });
  }, [orders, search, filter]);

  const stats = useMemo(() => {
    return {
      total: orders.length,
      active: orders.filter(o => o.status !== 'ZAKOŃCZONE' && o.status !== 'ANULOWANE').length,
      new: orders.filter(o => o.status === 'NOWE').length,
      urgent: orders.filter(o => o.priority === 'HIGH' || o.priority === 'CRITICAL').length
    };
  }, [orders]);

  return (
    <AppShell>
      <PageHeader
        eyebrow="System Zarządzania"
        title="Książka Zleceń"
        subtitle="Pełny rejestr zamówień, statusów operacyjnych i terminów realizacji."
        actions={
          <div className="flex gap-2">
            <Button as="link" href="/orders/new" variant="primary">
              <Plus className="w-4 h-4 mr-2" /> Nowe Zlecenie
            </Button>
            <Button onClick={loadData} variant="secondary" className="border-white/10">
              <RefreshCw className={clsx("w-4 h-4", loading && "animate-spin")} />
            </Button>
          </div>
        }
      />

      <div className="max-w-[1600px] mx-auto space-y-6 pb-20 px-4">
        {/* Stats Strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Wszystkie" value={stats.total} icon={<FileText className="w-4 h-4" />} tone="default" />
          <StatCard label="W realizacji" value={stats.active} icon={<Activity className="w-4 h-4" />} tone="brand" />
          <StatCard label="Nowe" value={stats.new} icon={<Plus className="w-4 h-4" />} tone="success" />
          <StatCard label="Priorytetowe" value={stats.urgent} icon={<ClipboardList className="w-4 h-4" />} tone="danger" />
        </div>

        {/* Search & Filter */}
        <Card className="p-4 bg-[#121214]/50 border-white/5 backdrop-blur-md flex flex-wrap gap-4 items-center">
          <div className="relative flex-1 min-w-[300px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input 
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Szukaj zlecenia, klienta..."
              className="w-full bg-black/40 border border-white/10 rounded-lg pl-10 pr-4 py-2.5 text-sm text-white outline-none focus:border-blue-500/50 transition-all"
            />
          </div>
          <div className="flex items-center gap-3">
             <Filter size={14} className="text-slate-500" />
             <select 
               value={filter}
               onChange={e => setFilter(e.target.value)}
               className="bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-xs text-white outline-none"
             >
               <option value="all">Wszystkie statusy</option>
               <option value="NOWE">Nowe</option>
               <option value="POTWIERDZONE">Potwierdzone</option>
               <option value="W PRODUKCJI">W produkcji</option>
               <option value="ZAKOŃCZONE">Zakończone</option>
             </select>
          </div>
        </Card>

        {loading ? (
          <div className="py-40 text-center">
            <RefreshCw className="w-10 h-10 text-blue-500 animate-spin mx-auto opacity-50 mb-4" />
            <div className="text-slate-500 font-mono text-sm tracking-widest uppercase">Ładowanie rejestru...</div>
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-40 text-center">
            <FileText className="w-16 h-16 text-slate-800 mx-auto mb-4 opacity-20" />
            <p className="text-slate-600">Brak zleceń do wyświetlenia.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map((order) => (
              <motion.div
                key={order.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <Card className="group overflow-hidden border-white/5 bg-[#1a1a1c]/80 hover:bg-[#1e1e20] transition-all hover:border-blue-500/30">
                  <div className="p-5">
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-[10px] font-black text-blue-500 font-mono">#{order.id}</span>
                          <h3 className="text-sm font-bold text-white truncate max-w-[180px]">{order.title}</h3>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-slate-500">
                          <User size={12} />
                          <span className="truncate max-w-[150px]">{order.client_name || 'Brak klienta'}</span>
                        </div>
                      </div>
                      <div className={clsx(
                        "text-[9px] font-black uppercase px-2 py-0.5 rounded-full border tracking-widest",
                        order.status === 'ZAKOŃCZONE' ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" :
                        order.status === 'NOWE' ? "bg-blue-500/10 text-blue-400 border-blue-500/20" :
                        "bg-amber-500/10 text-amber-500 border-amber-500/20"
                      )}>
                        {order.status}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4 mb-5">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2 text-[10px] text-slate-500 uppercase font-black tracking-widest">
                          <Calendar size={10} /> Otrzymano
                        </div>
                        <div className="text-xs text-slate-200">{order.received_date || order.created_at?.split(' ')[0] || '-'}</div>
                      </div>
                      <div className="space-y-1">
                        <div className="flex items-center gap-2 text-[10px] text-slate-500 uppercase font-black tracking-widest">
                          <Clock size={10} /> Termin
                        </div>
                        <div className={clsx(
                          "text-xs font-bold",
                          order.due_date ? "text-blue-400" : "text-slate-500"
                        )}>
                          {order.due_date || order.deadline || 'Brak'}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between pt-4 border-t border-white/5">
                      <div className="flex items-center gap-2">
                        {order.priority === 'HIGH' && <span className="w-2 h-2 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]" />}
                        <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">
                          Priorytet: {order.priority || 'NORMAL'}
                        </span>
                      </div>
                      <Link 
                        href={`/orders/${order.id}`}
                        className="flex items-center gap-2 text-xs font-bold text-blue-400 hover:text-white transition-colors"
                      >
                        Przegląd <ArrowRight size={14} />
                      </Link>
                    </div>
                  </div>
                </Card>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
