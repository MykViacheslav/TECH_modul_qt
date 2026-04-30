"use client";

import { useEffect, useState, useMemo } from "react";
import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Card, Button, StatCard } from "@/components/ui";
import { TechModulAPI, type FulfillmentQueueItem, type FulfillmentRecord } from "@/services/api";
import { useCurrentUser } from "@/services/user-context";
import { 
  Truck, 
  RefreshCw, 
  Package, 
  CheckCircle2, 
  MapPin, 
  AlertTriangle,
  Lock,
  ArrowRight,
  ShieldAlert,
  Search,
  Filter,
  Activity,
  History,
  Info,
  Clock,
  Box,
  ClipboardCheck,
  HardHat,
  ChevronRight,
  ExternalLink
} from "lucide-react";
import clsx from "clsx";
import { motion, AnimatePresence } from "framer-motion";

const STATUS_LABELS: Record<string, string> = {
  ready_for_shipping: "Gotowe do wysyłki",
  packed: "Zapakowane",
  dispatched: "W drodze",
  delivered: "Dostarczone",
  installation_in_progress: "Montaż w toku",
  installation_blocked: "Montaż wstrzymany",
  installed: "Zamontowane",
  closed: "Zakończone"
};

const STAGES = [
  { id: "production", label: "Produkcja", icon: Activity },
  { id: "packed", label: "Pakowanie", icon: Box },
  { id: "dispatched", label: "Wysyłka", icon: Truck },
  { id: "installation", label: "Montaż", icon: HardHat },
  { id: "closed", label: "Finał", icon: CheckCircle2 }
];

export default function FulfillmentPage() {
  const [user] = useCurrentUser();
  const operatorName = user?.name || "Nieznany Operator";
  
  const [items, setItems] = useState<FulfillmentQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("active");

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await TechModulAPI.getFulfillmentQueue();
      setItems(data || []);
    } catch (e: any) {
      setError(e?.message ?? "Błąd ładowania danych logistycznych");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const updateStatus = async (projectName: string, status: string, extraData: Partial<FulfillmentRecord> = {}) => {
    try {
      await TechModulAPI.updateFulfillmentStatus(projectName, { status, ...extraData });
      loadData();
    } catch (e: any) {
      alert("Błąd: " + e.message);
    }
  };

  const handlePack = (projectName: string) => {
    const count = prompt("Liczba paczek / palet?", "1");
    if (count === null) return;
    updateStatus(projectName, "packed", { package_count: parseInt(count) || 1 });
  };

  const handleDispatch = (projectName: string) => {
    const carrier = prompt("Przewoźnik?", "Własny transport");
    const tracking = prompt("Numer listu / trackingu?");
    updateStatus(projectName, "dispatched", { 
      carrier_name: carrier || "", 
      tracking_number: tracking || "" 
    });
  };

  const handleBlockInstallation = (projectName: string) => {
    const reason = prompt("Dlaczego montaż jest wstrzymany?");
    if (!reason) return;
    updateStatus(projectName, "installation_blocked", { blocked_reason: reason });
  };

  const handleUpdateProgress = (projectName: string, currentProgress: number) => {
    const next = Math.min(100, currentProgress + 25);
    updateStatus(projectName, "installation_in_progress", { installation_progress: next });
  };

  const stats = useMemo(() => {
    return {
      active: items.filter(i => i.fulfillment.status !== "closed").length,
      in_transit: items.filter(i => i.fulfillment.status === "dispatched").length,
      installation: items.filter(i => ["installation_in_progress", "delivered"].includes(i.fulfillment.status)).length,
      blocked: items.filter(i => i.fulfillment.status === "installation_blocked").length,
    };
  }, [items]);

  const filtered = useMemo(() => {
    return items.filter(p => {
      const matchesSearch = !search || 
        p.project_name.toLowerCase().includes(search.toLowerCase()) || 
        p.client_name.toLowerCase().includes(search.toLowerCase());
      
      const st = p.fulfillment.status;
      const matchesFilter = filter === "all" || 
        (filter === "active" && st !== "closed") ||
        (filter === "blocked" && st === "installation_blocked") ||
        (filter === "closed" && st === "closed");
        
      return matchesSearch && matchesFilter;
    });
  }, [items, search, filter]);

  return (
    <AppShell>
      <PageHeader
        eyebrow="Dyspozytornia Operacyjna"
        title="Logistyka & Montaż"
        subtitle="Zarządzanie pakowaniem, transportem i postępem prac u klienta."
        actions={
          <Button onClick={loadData} disabled={loading} variant="secondary" className="border-white/10 hover:bg-white/5">
            <RefreshCw className={clsx("w-4 h-4 mr-2", loading && "animate-spin")} /> Odśwież widok
          </Button>
        }
      />

      <div className="max-w-[1600px] mx-auto space-y-6 pb-20 px-4">
        {/* KPI Strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="W realizacji" value={stats.active} icon={<Activity className="w-4 h-4" />} tone="brand" />
          <StatCard label="W transporcie" value={stats.in_transit} icon={<Truck className="w-4 h-4" />} tone="success" />
          <StatCard label="Montaże" value={stats.installation} icon={<HardHat className="w-4 h-4" />} tone="brand" />
          <StatCard label="Blokady" value={stats.blocked} icon={<AlertTriangle className="w-4 h-4" />} tone="danger" />
        </div>

        <Card className="p-4 bg-[#121214]/50 border-white/5 backdrop-blur-md flex flex-wrap gap-4 items-center">
          <div className="relative flex-1 min-w-[300px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input 
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Filtruj zlecenia (nazwa, klient)..."
              className="w-full bg-black/40 border border-white/10 rounded-lg pl-10 pr-4 py-2.5 text-sm text-white outline-none focus:border-blue-500/50 transition-all"
            />
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-500 font-bold uppercase tracking-widest">Status:</span>
            <div className="flex bg-black/40 p-1 rounded-lg border border-white/5">
              {["active", "blocked", "closed", "all"].map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={clsx(
                    "px-4 py-1.5 rounded-md text-[10px] font-black uppercase tracking-widest transition-all",
                    filter === f ? "bg-blue-600 text-white shadow-lg shadow-blue-600/20" : "text-slate-500 hover:text-slate-300"
                  )}
                >
                  {f === "active" ? "Aktywne" : f === "blocked" ? "Blokady" : f === "closed" ? "Zakończone" : "Wszystkie"}
                </button>
              ))}
            </div>
          </div>
        </Card>

        {loading ? (
          <div className="py-40 text-center space-y-4">
            <RefreshCw className="w-10 h-10 text-blue-500 animate-spin mx-auto opacity-50" />
            <div className="text-slate-500 font-mono text-sm tracking-[0.2em] uppercase">Synchronizacja z magazynem...</div>
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-40 text-center">
            <Box className="w-16 h-16 text-slate-800 mx-auto mb-4" />
            <div className="text-slate-600 font-medium">Brak zleceń pasujących do filtrów.</div>
          </div>
        ) : (
          <div className="space-y-4">
            {filtered.map((item) => {
              const f = item.fulfillment;
              const isBlocked = f.status === "installation_blocked";
              const isClosed = f.status === "closed";
              
              // Calculate stage index for timeline
              let stageIdx = 0;
              if (item.production_status === "Zakończona") stageIdx = 1;
              if (["packed", "dispatched", "delivered", "installation_in_progress", "installation_blocked", "installed", "closed"].includes(f.status)) stageIdx = 2;
              if (["dispatched", "delivered", "installation_in_progress", "installation_blocked", "installed", "closed"].includes(f.status)) stageIdx = 3;
              if (["delivered", "installation_in_progress", "installation_blocked", "installed", "closed"].includes(f.status)) stageIdx = 4;
              if (isClosed) stageIdx = 5;

              return (
                <motion.div
                  key={item.project_name}
                  layout
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  <Card padded={false} className={clsx(
                    "overflow-hidden border-white/5 bg-[#1a1a1c]/80 hover:bg-[#1e1e20] transition-all",
                    isBlocked && "border-red-500/30 shadow-[0_0_20px_rgba(239,68,68,0.05)]",
                    isClosed && "opacity-60 grayscale-[0.5]"
                  )}>
                    <div className="flex flex-col xl:flex-row">
                      {/* Left Side: Info */}
                      <div className="p-6 flex-1 min-w-[350px]">
                        <div className="flex items-start justify-between mb-4">
                          <div>
                            <div className="flex items-center gap-3 mb-1">
                              <h3 className="text-lg font-bold text-white tracking-tight">{item.project_name}</h3>
                              <div className={clsx(
                                "text-[9px] font-black uppercase px-2 py-0.5 rounded-full border tracking-widest",
                                isClosed ? "bg-slate-800 text-slate-500 border-slate-700" :
                                isBlocked ? "bg-red-500/10 text-red-500 border-red-500/20 animate-pulse" :
                                "bg-blue-500/10 text-blue-400 border-blue-500/20"
                              )}>
                                {STATUS_LABELS[f.status] || f.status}
                              </div>
                            </div>
                            <p className="text-xs text-slate-400">Klient: <span className="text-slate-200 font-semibold">{item.client_name}</span></p>
                          </div>
                          
                          {f.installation_progress > 0 && !isClosed && (
                            <div className="text-right">
                              <div className="text-[10px] text-slate-500 font-black uppercase mb-1">Montaż: {f.installation_progress}%</div>
                              <div className="w-24 h-1.5 bg-black/40 rounded-full overflow-hidden border border-white/5">
                                <motion.div 
                                  className="h-full bg-blue-500" 
                                  initial={{ width: 0 }}
                                  animate={{ width: `${f.installation_progress}%` }}
                                />
                              </div>
                            </div>
                          )}
                        </div>

                        {/* Progress Timeline */}
                        <div className="relative pt-6 pb-2 px-2">
                          <div className="absolute top-[2.4rem] left-0 right-0 h-0.5 bg-white/5 mx-6"></div>
                          <div className="relative flex justify-between">
                            {STAGES.map((s, idx) => {
                              const isPast = stageIdx > idx;
                              const isCurrent = stageIdx === idx;
                              const SIcon = s.icon;
                              
                              return (
                                <div key={s.id} className="flex flex-col items-center gap-3 relative z-10 group">
                                  <div className={clsx(
                                    "w-8 h-8 rounded-full flex items-center justify-center transition-all duration-500 border",
                                    isPast ? "bg-emerald-500 border-emerald-400 text-black shadow-[0_0_15px_rgba(16,185,129,0.3)]" :
                                    isCurrent ? "bg-blue-600 border-blue-400 text-white shadow-[0_0_20px_rgba(37,99,235,0.4)] animate-pulse" :
                                    "bg-[#121214] border-white/10 text-slate-600"
                                  )}>
                                    <SIcon size={14} />
                                  </div>
                                  <span className={clsx(
                                    "text-[9px] font-black uppercase tracking-widest transition-colors",
                                    isPast ? "text-emerald-500" : isCurrent ? "text-blue-400" : "text-slate-700"
                                  )}>{s.label}</span>
                                </div>
                              );
                            })}
                          </div>
                        </div>

                        {isBlocked && (
                          <div className="mt-6 p-3 bg-red-500/10 border border-red-500/20 rounded-lg flex items-start gap-3">
                            <ShieldAlert size={18} className="text-red-500 shrink-0 mt-0.5" />
                            <div>
                              <div className="text-[10px] text-red-500/70 font-black uppercase tracking-widest mb-1">Blokada Montażu</div>
                              <div className="text-sm text-red-200 font-medium leading-relaxed">{f.blocked_reason}</div>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Middle: Data Summary */}
                      <div className="p-6 bg-black/10 border-y xl:border-y-0 xl:border-x border-white/5 min-w-[300px]">
                        <div className="space-y-4">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2 text-slate-500">
                              <Box size={14} />
                              <span className="text-[10px] font-black uppercase tracking-widest">Ładunek</span>
                            </div>
                            <div className="text-xs text-slate-200 font-mono">{f.package_count || 0} paczek</div>
                          </div>
                          
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2 text-slate-500">
                              <Truck size={14} />
                              <span className="text-[10px] font-black uppercase tracking-widest">Transport</span>
                            </div>
                            <div className="text-xs text-slate-200">{f.carrier_name || "-"}</div>
                          </div>

                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2 text-slate-500">
                              <MapPin size={14} />
                              <span className="text-[10px] font-black uppercase tracking-widest">Tracking</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-blue-400 font-mono">{f.tracking_number || "Brak danych"}</span>
                              {f.tracking_number && <ExternalLink size={12} className="text-slate-600" />}
                            </div>
                          </div>

                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2 text-slate-500">
                              <HardHat size={14} />
                              <span className="text-[10px] font-black uppercase tracking-widest">Ekipa</span>
                            </div>
                            <div className="text-xs text-slate-200">{f.installation_team || "Nie przypisano"}</div>
                          </div>

                          <div className="pt-2 flex flex-wrap gap-2">
                            {f.packed_at && <div className="px-2 py-1 bg-white/5 rounded text-[9px] text-slate-400 border border-white/5" title={`Przez: ${f.packed_by}`}>📦 SP {f.packed_at.split(' ')[0]}</div>}
                            {f.dispatched_at && <div className="px-2 py-1 bg-white/5 rounded text-[9px] text-slate-400 border border-white/5" title={`Przez: ${f.dispatched_by}`}>🚚 WY {f.dispatched_at.split(' ')[0]}</div>}
                          </div>
                        </div>
                      </div>

                      {/* Right Side: Actions */}
                      <div className="p-6 flex flex-col gap-2 min-w-[240px] justify-center bg-black/5">
                        <div className="text-[9px] text-slate-500 font-black uppercase tracking-[0.2em] mb-2 px-1">Centrum Operacji</div>
                        
                        {f.status === "ready_for_shipping" && (
                          <Button onClick={() => handlePack(item.project_name)} className="w-full justify-start bg-slate-800 hover:bg-slate-700 text-white border-white/10 group">
                            <Package className="w-4 h-4 mr-3 text-blue-400 group-hover:scale-110 transition-transform" /> Zapakowano...
                          </Button>
                        )}
                        
                        {(f.status === "packed" || f.status === "ready_for_shipping") && (
                          <Button onClick={() => handleDispatch(item.project_name)} className="w-full justify-start bg-blue-600/10 text-blue-400 hover:bg-blue-600/20 border border-blue-500/20 group">
                            <Truck className="w-4 h-4 mr-3 group-hover:translate-x-1 transition-transform" /> Nadaj wysyłkę...
                          </Button>
                        )}

                        {f.status === "dispatched" && (
                          <Button onClick={() => updateStatus(item.project_name, "delivered")} className="w-full justify-start bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 border border-emerald-500/20 group">
                            <MapPin className="w-4 h-4 mr-3 group-hover:scale-110 transition-transform" /> Potwierdź dostawę
                          </Button>
                        )}

                        {(f.status === "delivered" || f.status === "installation_blocked" || f.status === "installation_in_progress") && !isClosed && (
                          <>
                            <Button 
                              onClick={() => handleUpdateProgress(item.project_name, f.installation_progress)} 
                              className="w-full justify-start bg-blue-600 text-white shadow-lg shadow-blue-600/20 hover:bg-blue-500"
                            >
                              <Lock className="w-4 h-4 mr-3" /> Raportuj postęp (+25%)
                            </Button>
                            
                            <div className="grid grid-cols-2 gap-2">
                              <Button onClick={() => updateStatus(item.project_name, "installed")} variant="secondary" className="text-[10px] h-8 border-emerald-500/30 text-emerald-500 hover:bg-emerald-500/10">
                                <CheckCircle2 size={12} className="mr-1" /> Zakończ
                              </Button>
                              <Button onClick={() => handleBlockInstallation(item.project_name)} variant="secondary" className="text-[10px] h-8 border-red-500/30 text-red-500 hover:bg-red-500/10">
                                <AlertTriangle size={12} className="mr-1" /> Blokuj
                              </Button>
                            </div>
                          </>
                        )}

                        {(f.status === "installed" || f.status === "delivered") && (
                          <Button onClick={() => updateStatus(item.project_name, "closed")} className="w-full justify-start bg-slate-900 text-slate-300 border border-white/5 hover:bg-black mt-2 group">
                            <ClipboardCheck className="w-4 h-4 mr-3 text-emerald-500 group-hover:scale-110 transition-transform" /> Zamknij proces
                          </Button>
                        )}
                        
                        {isClosed && (
                          <div className="py-4 text-center">
                            <CheckCircle2 className="w-8 h-8 text-slate-700 mx-auto mb-1" />
                            <div className="text-[10px] text-slate-600 font-black uppercase tracking-widest">Zarchiwizowane</div>
                          </div>
                        )}
                      </div>
                    </div>
                  </Card>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </AppShell>
  );
}
