"use client";

import { useEffect, useState, useMemo } from "react";
import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Card, Button } from "@/components/ui";
import { TechModulAPI, type ProcurementExecutionItem } from "@/services/api";
import { 
  ShoppingCart, 
  RefreshCw, 
  User, 
  Truck, 
  Calendar, 
  AlertCircle, 
  CheckCircle2, 
  Clock,
  MoreVertical,
  Plus,
  Search,
  Filter,
  ExternalLink
} from "lucide-react";
import clsx from "clsx";
import Link from "next/link";
import { useCurrentUser } from "@/services/user-context";

const STATUS_STYLES: Record<string, string> = {
  missing: "bg-red-500/10 text-red-500 border-red-500/30",
  to_buy: "bg-orange-500/10 text-orange-500 border-orange-500/30",
  ordered: "bg-blue-500/10 text-blue-400 border-blue-500/30",
  partially_received: "bg-purple-500/10 text-purple-400 border-purple-500/30",
  received: "bg-emerald-500/10 text-emerald-500 border-emerald-500/30",
  blocked: "bg-slate-500/10 text-slate-400 border-slate-500/30",
  cancelled: "bg-slate-800 text-slate-500 border-slate-700",
};

const STATUS_LABELS: Record<string, string> = {
  missing: "Brakujace",
  to_buy: "Do kupienia",
  ordered: "Zamowione",
  partially_received: "Czesciowo",
  received: "Przyjete",
  blocked: "Zablokowane",
  cancelled: "Anulowane",
};

const PRIORITY_STYLES: Record<string, string> = {
  krytyczny: "text-red-500",
  wysoki: "text-orange-400",
  normalny: "text-slate-400",
};

export default function ProcurementExecutionPage() {
  const [currentUser] = useCurrentUser();
  const [items, setItems] = useState<ProcurementExecutionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const [editingItem, setEditingItem] = useState<ProcurementExecutionItem | null>(null);
  const [updating, setUpdating] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await TechModulAPI.getProcurementExecution();
      setItems(data);
    } catch (e: any) {
      setError(e?.message || "Blad ladowania danych");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filtered = useMemo(() => {
    return items.filter(i => {
      const matchesSearch = !search || 
        i.material_name.toLowerCase().includes(search.toLowerCase()) || 
        (i.owner_name || "").toLowerCase().includes(search.toLowerCase()) ||
        (i.supplier_name || "").toLowerCase().includes(search.toLowerCase());
      const matchesStatus = statusFilter === "all" || i.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [items, search, statusFilter]);

  const handleUpdate = async (id: number, updates: Partial<ProcurementExecutionItem>) => {
    setUpdating(true);
    try {
      await TechModulAPI.updateProcurementExecution(id, updates);
      await loadData();
      setEditingItem(null);
    } catch (e: any) {
      alert(e?.message || "Blad aktualizacji");
    } finally {
      setUpdating(false);
    }
  };

  const isManager = currentUser?.role === "admin" || currentUser?.role === "manager";

  return (
    <AppShell>
      <PageHeader
        eyebrow="Supply Chain"
        title="Procurement Execution"
        subtitle="Manage purchasing tasks, assign owners, and track supplier order status."
        actions={
          <div className="flex gap-2">
            <Link href="/procurement/suggestions">
              <Button variant="secondary">
                <Plus className="w-4 h-4 mr-2" /> From Suggestions
              </Button>
            </Link>
            <Button onClick={loadData} variant="secondary" disabled={loading}>
              <RefreshCw className={clsx("w-4 h-4 mr-1", loading && "animate-spin")} /> Refresh
            </Button>
          </div>
        }
      />

      <div className="max-w-7xl mx-auto space-y-4 pb-20">
        <Card className="p-4 flex flex-wrap gap-4 items-center">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input 
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search material, owner, or supplier..."
              className="w-full bg-black/40 border border-white/10 rounded-lg pl-10 pr-4 py-2 text-sm text-white outline-none focus:border-brand/50"
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-500" />
            <select 
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              className="bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-brand/50"
            >
              <option value="all">Wszystkie statusy</option>
              {Object.entries(STATUS_LABELS).map(([val, lab]) => (
                <option key={val} value={val}>{lab}</option>
              ))}
            </select>
          </div>
        </Card>

        {loading ? (
          <div className="py-20 text-center text-slate-500 animate-pulse">Ladowanie zadan...</div>
        ) : filtered.length === 0 ? (
          <div className="py-20 text-center text-slate-600">Brak zadan zakupowych pasujacych do filtrow.</div>
        ) : (
          <div className="grid grid-cols-1 gap-3">
            {filtered.map(item => (
              <Card key={item.id} padded={false} className="group overflow-hidden border-white/5 hover:border-white/10 transition-colors">
                <div className="flex flex-col md:flex-row">
                  <div className={clsx("w-1 md:w-2 shrink-0", item.priority === "krytyczny" ? "bg-red-500" : item.priority === "wysoki" ? "bg-orange-500" : "bg-slate-700")} />
                  
                  <div className="p-4 flex-1 flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className={clsx("text-[9px] font-black uppercase px-1.5 py-0.5 rounded border", STATUS_STYLES[item.status])}>
                          {STATUS_LABELS[item.status]}
                        </span>
                        <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">{item.material_category}</span>
                      </div>
                      <h3 className="text-base font-bold text-white group-hover:text-brand transition-colors">{item.material_name}</h3>
                      <div className="flex items-center gap-3 text-xs text-slate-400">
                        <span className="flex items-center gap-1"><ShoppingCart size={12} /> {item.qty_target} {item.material_unit}</span>
                        {item.order_title && (
                          <Link href={`/operations?search=${encodeURIComponent(item.order_title)}`} className="flex items-center gap-1 hover:text-white transition-colors">
                            <ExternalLink size={12} /> {item.order_title}
                          </Link>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-xs">
                      <div>
                        <div className="text-[10px] text-slate-600 font-black uppercase mb-1">Owner</div>
                        <div className="flex items-center gap-1.5 text-slate-300 font-medium">
                          <User size={12} className="text-slate-500" /> {item.owner_name || "Unassigned"}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] text-slate-600 font-black uppercase mb-1">Supplier</div>
                        <div className="flex items-center gap-1.5 text-slate-300">
                          <Truck size={12} className="text-slate-500" /> {item.supplier_name || "Not set"}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] text-slate-600 font-black uppercase mb-1">Due Date</div>
                        <div className={clsx("flex items-center gap-1.5 font-medium", 
                          item.due_date && new Date(item.due_date) < new Date() ? "text-red-400" : "text-slate-300"
                        )}>
                          <Calendar size={12} className="text-slate-500" /> {item.due_date || "No date"}
                        </div>
                      </div>
                      <div className="flex items-center justify-end">
                        {isManager ? (
                          <Button variant="secondary" size="sm" onClick={() => setEditingItem(item)}>
                            Manage
                          </Button>
                        ) : (
                          <Link href={`/inventory/purchases?search=${encodeURIComponent(item.material_name)}`}>
                            <Button variant="ghost" size="sm">Purchases</Button>
                          </Link>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Edit Modal */}
      {editingItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <Card className="w-full max-w-lg shadow-2xl border-white/10" title="Manage Procurement Task">
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] font-black uppercase text-slate-500 mb-1">Status</label>
                  <select 
                    value={editingItem.status}
                    onChange={e => setEditingItem({...editingItem, status: e.target.value})}
                    className="w-full bg-black/40 border border-white/10 rounded px-3 py-2 text-sm text-white outline-none focus:border-brand"
                  >
                    {Object.entries(STATUS_LABELS).map(([val, lab]) => (
                      <option key={val} value={val}>{lab}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] font-black uppercase text-slate-500 mb-1">Priority</label>
                  <select 
                    value={editingItem.priority}
                    onChange={e => setEditingItem({...editingItem, priority: e.target.value})}
                    className="w-full bg-black/40 border border-white/10 rounded px-3 py-2 text-sm text-white outline-none focus:border-brand"
                  >
                    <option value="normalny">Normal</option>
                    <option value="wysoki">High</option>
                    <option value="krytyczny">Critical</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] font-black uppercase text-slate-500 mb-1">Owner</label>
                  <input 
                    value={editingItem.owner_name || ""}
                    onChange={e => setEditingItem({...editingItem, owner_name: e.target.value})}
                    className="w-full bg-black/40 border border-white/10 rounded px-3 py-2 text-sm text-white outline-none focus:border-brand"
                    placeholder="Technician name"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-black uppercase text-slate-500 mb-1">Due Date</label>
                  <input 
                    type="date"
                    value={editingItem.due_date || ""}
                    onChange={e => setEditingItem({...editingItem, due_date: e.target.value})}
                    className="w-full bg-black/40 border border-white/10 rounded px-3 py-2 text-sm text-white outline-none focus:border-brand"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[10px] font-black uppercase text-slate-500 mb-1">Supplier</label>
                <input 
                  value={editingItem.supplier_name || ""}
                  onChange={e => setEditingItem({...editingItem, supplier_name: e.target.value})}
                  className="w-full bg-black/40 border border-white/10 rounded px-3 py-2 text-sm text-white outline-none focus:border-brand"
                  placeholder="NP. Kronospan"
                />
              </div>

              <div>
                <label className="block text-[10px] font-black uppercase text-slate-500 mb-1">Note</label>
                <textarea 
                  value={editingItem.note || ""}
                  onChange={e => setEditingItem({...editingItem, note: e.target.value})}
                  className="w-full bg-black/40 border border-white/10 rounded px-3 py-2 text-sm text-white outline-none focus:border-brand h-20 resize-none"
                  placeholder="Purchasing notes..."
                />
              </div>

              <div className="flex gap-3 pt-2">
                <Button 
                  className="flex-1" 
                  disabled={updating}
                  onClick={() => handleUpdate(editingItem.id, {
                    status: editingItem.status,
                    priority: editingItem.priority,
                    owner_name: editingItem.owner_name,
                    due_date: editingItem.due_date,
                    supplier_name: editingItem.supplier_name,
                    note: editingItem.note
                  })}
                >
                  {updating ? "Saving..." : "Save Changes"}
                </Button>
                <Button variant="ghost" onClick={() => setEditingItem(null)}>Cancel</Button>
              </div>
            </div>
          </Card>
        </div>
      )}
    </AppShell>
  );
}
