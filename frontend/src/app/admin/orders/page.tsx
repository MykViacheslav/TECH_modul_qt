"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Card, Button } from "@/components/ui";
import { TechModulAPI } from "@/services/api";
import { 
  FileText, 
  Trash2, 
  RefreshCw, 
  Search,
  Calendar,
  User,
  AlertTriangle,
  History
} from "lucide-react";

export default function OrdersManagementPage() {
  const [orders, setOrders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [includeDeleted, setIncludeDeleted] = useState(false);

  const loadOrders = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await TechModulAPI.getOrders(undefined, includeDeleted);
      setOrders(res || []);
    } catch (e: any) {
      setError(e?.message || "Failed to load orders");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOrders();
  }, [includeDeleted]);

  const handleDelete = async (id: number, title: string) => {
    if (!window.confirm(`Czy na pewno chcesz przenieść zamówienie "${title}" do kosza?`)) {
      return;
    }
    try {
      await TechModulAPI.deleteOrder(id);
      loadOrders();
    } catch (e: any) {
      alert(e?.message || "Błąd podczas usuwania zamówienia");
    }
  };

  const handleRestore = async (id: number, title: string) => {
    if (!window.confirm(`Przywrócić zamówienie "${title}"?`)) {
      return;
    }
    try {
      await TechModulAPI.restoreOrder(id);
      loadOrders();
    } catch (e: any) {
      alert(e?.message || "Błąd podczas przywracania zamówienia");
    }
  };

  const filtered = orders.filter(o => 
    o.title.toLowerCase().includes(search.toLowerCase()) || 
    o.client_name?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <AppShell>
      <PageHeader
        eyebrow="Admin Panel"
        title="Zarządzanie Zamówieniami"
        subtitle="Zestawienie wszystkich zamówień w systemie. Możliwość przywracania usuniętych rekordów."
        actions={
          <Button onClick={loadOrders}>
            <RefreshCw className="w-4 h-4 mr-2" /> Odśwież
          </Button>
        }
      />

      <div className="max-w-6xl mx-auto space-y-6 pb-20">
        <div className="flex gap-4 items-center">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 w-4 h-4" />
            <input
              type="text"
              placeholder="Szukaj zamówienia lub klienta..."
              className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-2 text-sm text-white outline-none focus:border-brand/50 transition-all"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-2 px-4 py-2 bg-white/5 border border-white/10 rounded-xl">
             <input 
               type="checkbox" 
               id="show-deleted-orders" 
               checked={includeDeleted} 
               onChange={(e) => setIncludeDeleted(e.target.checked)}
               className="rounded border-slate-700 bg-slate-900 text-brand focus:ring-brand"
             />
             <label htmlFor="show-deleted-orders" className="text-xs text-slate-400 cursor-pointer select-none">
               Pokaż usunięte
             </label>
          </div>
        </div>

        <Card padded={false}>
          {loading ? (
            <div className="p-20 text-center">
              <RefreshCw className="w-8 h-8 text-brand animate-spin mx-auto mb-4" />
              <p className="text-slate-500 font-mono text-xs uppercase tracking-widest">Loading_Order_Registry...</p>
            </div>
          ) : filtered.length === 0 ? (
            <div className="p-20 text-center text-slate-500">
              <History className="w-12 h-12 mx-auto mb-4 opacity-20" />
              <p>Brak zamówień spełniających kryteria.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="bg-white/5 text-slate-500 uppercase font-bold text-[10px]">
                  <tr>
                    <th className="px-6 py-4">Zamówienie</th>
                    <th className="px-6 py-4">Klient</th>
                    <th className="px-6 py-4">Termin</th>
                    <th className="px-6 py-4">Status</th>
                    <th className="px-6 py-4 text-right">Akcje</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {filtered.map((o) => (
                    <tr key={o.id} className={`hover:bg-white/5 transition-colors group ${o.is_deleted ? 'opacity-60 bg-red-500/5' : ''}`}>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs ${o.is_deleted ? 'bg-red-500/10 text-red-400' : 'bg-brand/10 text-brand'}`}>
                            {o.id}
                          </div>
                          <div>
                            <span className={`font-bold block ${o.is_deleted ? 'text-slate-400 line-through' : 'text-slate-200'}`}>{o.title}</span>
                            <span className="text-[10px] text-slate-500 uppercase">Projekt #{o.project_id}</span>
                          </div>
                          {o.is_deleted && (
                            <span className="text-[8px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 uppercase font-black">DELETED</span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-slate-400 italic">
                        {o.client_name || "---"}
                      </td>
                      <td className="px-6 py-4 text-slate-500 text-xs font-mono">
                        {o.deadline || o.deadline_to || "---"}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-tighter border ${o.is_deleted ? 'bg-slate-900 text-slate-600 border-slate-800' : 'bg-brand/10 text-brand border-brand/20'}`}>
                          {o.status || "DRAFT"}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        {o.is_deleted ? (
                          <Button 
                            size="sm" 
                            variant="ghost" 
                            className="text-green-500 hover:text-green-400 hover:bg-green-500/10"
                            onClick={() => handleRestore(o.id, o.title)}
                          >
                            <RefreshCw className="w-4 h-4 mr-1" /> Przywróć
                          </Button>
                        ) : (
                          <Button 
                            size="sm" 
                            variant="ghost" 
                            className="text-slate-500 hover:text-red-400"
                            onClick={() => handleDelete(o.id, o.title)}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </AppShell>
  );
}
