"use client";

import AppShell from "@/components/AppShell";
import { Button, Card, StatCard } from "@/components/ui";
import { TechModulAPI } from "@/services/api";
import { useParams, useRouter } from "next/navigation";
import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  Calendar,
  CheckCircle2,
  Clock,
  Coins,
  FileText,
  Info,
  LayoutList,
  Loader2,
  Package,
  TrendingUp,
  History,
  ChevronLeft,
  Search,
} from "lucide-react";
import clsx from "clsx";

export default function OrderOperationalReviewPage() {
  const params = useParams();
  const orderId = Number(params.id);
  const router = useRouter();

  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [reserving, setReserving] = useState(false);
  const [issuing, setIssuing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (orderId) {
      loadReview();
    }
  }, [orderId]);

  const loadReview = async () => {
    setLoading(true);
    try {
      const res = await TechModulAPI.getOrderOperationalReview(orderId);
      setData(res);
    } catch (err: any) {
      setError(err.message || "Błąd ładowania przeglądu operacyjnego");
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateTasks = async () => {
    setGenerating(true);
    try {
      const res = await TechModulAPI.generateProductionTasks(orderId);
      alert(res.message);
      await loadReview();
    } catch (err: any) {
      alert("Błąd generowania zadań: " + err.message);
    } finally {
      setGenerating(false);
    }
  };

  const handleReserveMaterials = async () => {
    setReserving(true);
    try {
      const res = await TechModulAPI.reserveOrderMaterials(orderId);
      alert(res.message);
      await loadReview();
    } catch (err: any) {
      alert("Błąd rezerwacji: " + err.message);
    } finally {
      setReserving(false);
    }
  };

  const handleIssueMaterials = async () => {
    setIssuing(true);
    try {
      const res = await TechModulAPI.issueOrderMaterials(orderId);
      alert(res.message);
      await loadReview();
    } catch (err: any) {
      alert("Błąd wydania: " + err.message);
    } finally {
      setIssuing(false);
    }
  };

  if (loading) {
    return (
      <AppShell>
        <div className="flex h-[80vh] items-center justify-center">
          <div className="text-center">
            <Loader2 className="h-8 w-8 animate-spin text-blue-500 mx-auto mb-4" />
            <p className="text-[10px] uppercase tracking-widest text-slate-500 font-orbitron">Inicjalizacja przeglądu...</p>
          </div>
        </div>
      </AppShell>
    );
  }

  if (error || !data) {
    return (
      <AppShell>
        <div className="p-8 text-center text-red-400">
          <AlertTriangle className="mx-auto mb-4 h-12 w-12" />
          <h1 className="text-xl font-bold font-orbitron">Wystąpił błąd</h1>
          <p className="mt-2 text-sm">{error || "Nie znaleziono danych"}</p>
          <Button onClick={() => router.back()} className="mt-6" variant="secondary">
            <ChevronLeft className="h-4 w-4" /> Powrót
          </Button>
        </div>
      </AppShell>
    );
  }

  const { order, positions, derived_demand, material_readiness, calendar_events, finance, audit, readiness, production_tasks = [] } = data;

  const getPriorityTone = (p: string) => {
    switch (p) {
      case "Krytyczny": return "danger";
      case "Pilny": return "warn";
      default: return "brand";
    }
  };

  return (
    <AppShell>
      <div className="max-w-[1600px] mx-auto space-y-8 p-8 font-sans text-slate-200">
        
        {/* Navigation & Actions */}
        <div className="flex items-center justify-between">
          <Button variant="ghost" onClick={() => router.back()} size="sm" className="text-slate-500">
            <ChevronLeft className="h-4 w-4" /> Lista zleceń
          </Button>
          <div className="flex gap-2">
             <Button variant="secondary" size="sm" onClick={() => window.print()}>
               Drukuj raport
             </Button>
          </div>
        </div>

        {/* 1. Header */}
        <div className="flex flex-wrap items-end justify-between gap-6 border-b border-white/5 pb-8">
          <div>
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.3em] text-blue-400 font-bold mb-2">
              <span className="h-px w-8 bg-blue-500/50" />
              Przegląd Operacyjny Zlecenia
            </div>
            <h1 className="font-orbitron text-4xl font-black tracking-tighter text-white uppercase leading-none">
              {order.title} <span className="text-slate-700 ml-2">ID {order.id}</span>
            </h1>
            <div className="mt-4 flex items-center gap-6 text-xs text-slate-400">
              <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-full bg-slate-800 flex items-center justify-center text-slate-300 font-bold">
                  {order.client_name?.slice(0, 1)}
                </div>
                <div>
                   <div className="text-[10px] uppercase text-slate-600 font-black tracking-widest">Kontrahent</div>
                   <div className="font-bold text-slate-200">{order.client_name}</div>
                </div>
              </div>
              <div className="h-8 w-px bg-white/5" />
              <div>
                 <div className="text-[10px] uppercase text-slate-600 font-black tracking-widest">Projekt</div>
                 <div className="font-bold text-slate-200">#{order.project_id}</div>
              </div>
            </div>
          </div>
          
          <div className="flex gap-4">
            <div className={clsx(
              "flex flex-col items-center justify-center rounded-xl border px-6 py-3",
              order.priority === "Krytyczny" ? "border-red-500/30 bg-red-500/5" : 
              order.priority === "Pilny" ? "border-amber-500/30 bg-amber-500/5" : "border-blue-500/30 bg-blue-500/5"
            )}>
              <span className="text-[9px] uppercase tracking-widest font-black text-slate-500 mb-1">Priorytet</span>
              <span className={clsx("font-orbitron text-sm font-black uppercase", 
                order.priority === "Krytyczny" ? "text-red-400" : 
                order.priority === "Pilny" ? "text-amber-400" : "text-blue-400"
              )}>{order.priority}</span>
            </div>
            
            <div className="flex flex-col items-center justify-center rounded-xl border border-emerald-500/30 bg-emerald-500/5 px-6 py-3">
              <span className="text-[9px] uppercase tracking-widest font-black text-slate-500 mb-1">Status</span>
              <span className="font-orbitron text-sm font-black uppercase text-emerald-400">{order.status}</span>
            </div>
          </div>
        </div>

        {/* 2. Key Metrics Grid */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatCard 
            label="Data przyjęcia" 
            value={order.received_date || "—"} 
            icon={<Clock className="h-4 w-4" />} 
          />
          <StatCard 
            label="Termin oddania" 
            value={order.deadline_to || order.deadline || "—"} 
            icon={<Calendar className="h-4 w-4" />} 
            tone="brand"
          />
          <StatCard 
            label="Termin montażu" 
            value={order.installation_date || "—"} 
            icon={<Calendar className="h-4 w-4" />} 
            tone="brand"
          />
          <StatCard 
            label="Budżet zlecenia" 
            value={`${(order.budget || 0).toLocaleString()} PLN`} 
            icon={<Coins className="h-4 w-4" />} 
            tone="success"
          />
        </div>

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
          
          {/* Main Column */}
          <div className="lg:col-span-8 space-y-8">
            
            {/* 2. Positions Table */}
            <Card title="Wykaz Pozycji i Specyfikacja" icon={<LayoutList className="h-4 w-4" />} padded={false}>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-[12px]">
                  <thead>
                    <tr className="border-b border-white/5 bg-white/[0.02] text-left uppercase tracking-wider text-slate-500">
                      <th className="px-6 py-4 font-black">Nr</th>
                      <th className="px-6 py-4 font-black">Pozycja / Detal</th>
                      <th className="px-6 py-4 font-black">Materiał Bazowy</th>
                      <th className="px-6 py-4 font-black">Obrzeże</th>
                      <th className="px-6 py-4 font-black text-right">Pow. (m²)</th>
                      <th className="px-6 py-4 font-black text-right">Okl. (mb)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {positions.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-6 py-12 text-center text-slate-600 italic">Brak zdefiniowanych pozycji</td>
                      </tr>
                    ) : (
                      positions.map((p: any) => {
                        const input = p.servicePricingInput || {};
                        const isNoEdge = !input.edge_default_material_id || input.edge_mode === "none";
                        
                        // Derived measurements
                        const qty = Number(p.quantity || 1);
                        const area = ((p.lengthMm || 0) * (p.widthMm || 0) * qty) / 1000000;
                        
                        let edgeLen = 0;
                        if (!isNoEdge) {
                           const l = (p.lengthMm || 0) / 1000;
                           const w = (p.widthMm || 0) / 1000;
                           if (input.edge_top) edgeLen += l;
                           if (input.edge_bottom) edgeLen += l;
                           if (input.edge_left) edgeLen += w;
                           if (input.edge_right) edgeLen += w;
                           edgeLen *= qty;
                        }

                        return (
                          <tr key={p.id} className="hover:bg-white/[0.01] transition-colors">
                            <td className="px-6 py-4 font-mono text-slate-600 font-bold">{p.position_number || "—"}</td>
                            <td className="px-6 py-4">
                              <div className="font-black text-slate-200 uppercase tracking-tight">{p.name}</div>
                              <div className="text-[10px] text-slate-600 font-mono mt-0.5">{p.id?.slice(0, 8)}</div>
                            </td>
                            <td className="px-6 py-4">
                              <div className="font-semibold text-slate-400">{input.base_material_name || "—"}</div>
                              <div className="text-[10px] text-slate-600 uppercase tracking-widest">{input.base_thickness_mm}mm • {p.textureOrColor || "Standard"}</div>
                            </td>
                            <td className="px-6 py-4">
                              {isNoEdge ? (
                                <span className="text-[10px] font-black uppercase tracking-widest text-slate-700">Brak</span>
                              ) : (
                                <div className="flex flex-col">
                                   <span className="text-blue-400/80 font-bold">{input.edge_default_material_id}</span>
                                   <div className="flex gap-1 mt-1">
                                      {['top','bottom','left','right'].map(d => input[`edge_${d}`] && (
                                        <span key={d} className="h-1.5 w-1.5 rounded-full bg-blue-500/40" title={d} />
                                      ))}
                                   </div>
                                </div>
                              )}
                            </td>
                            <td className="px-6 py-4 text-right font-mono font-bold text-slate-400">
                               {area > 0 ? area.toFixed(3) : "—"}
                            </td>
                            <td className="px-6 py-4 text-right font-mono font-bold text-blue-400/60">
                               {edgeLen > 0 ? edgeLen.toFixed(2) : "—"}
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </Card>

            {/* 3. Material Demand Panel */}
            <Card title="Zapotrzebowanie i Dostępność Materiałów" icon={<Package className="h-4 w-4" />}>
               <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                 {derived_demand.length === 0 ? (
                   <div className="col-span-2 py-8 text-center bg-black/20 rounded-xl border border-white/5">
                      <Search className="h-8 w-8 text-slate-700 mx-auto mb-2" />
                      <p className="text-[11px] text-slate-500 uppercase tracking-widest">Brak danych o materiałach</p>
                   </div>
                 ) : (
                   derived_demand.map((d: any, idx: number) => (
                     <div key={idx} className="group flex items-center justify-between rounded-xl border border-white/5 bg-white/[0.02] p-4 hover:border-white/10 transition-all">
                       <div>
                         <div className="text-xs font-black text-slate-200 uppercase tracking-tight">{d.name}</div>
                         <div className="mt-2 flex items-center gap-4">
                            <div className="flex flex-col">
                               <span className="text-[9px] text-slate-600 uppercase font-black tracking-widest">Wymagane</span>
                               <span className="text-sm font-orbitron font-bold text-white">{d.needed} <span className="text-[10px] text-slate-500">{d.unit}</span></span>
                            </div>
                            <div className="h-6 w-px bg-white/5" />
                            <div className="flex flex-col">
                               <span className="text-[9px] text-slate-600 uppercase font-black tracking-widest">Dostępne</span>
                               <span className={clsx("text-sm font-orbitron font-bold", d.available < d.needed ? "text-red-400" : "text-emerald-400")}>
                                 {d.available} <span className="text-[10px] text-slate-500">{d.unit}</span>
                               </span>
                            </div>
                         </div>
                       </div>
                       <div className={clsx(
                         "flex h-12 w-12 items-center justify-center rounded-full border text-[10px] font-black uppercase tracking-tighter",
                         d.status === "OK" ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-400" : "border-red-500/20 bg-red-500/5 text-red-400"
                       )}>
                         {d.status}
                       </div>
                     </div>
                   ))
                 )}
               </div>
            </Card>

          </div>

          {/* Sidebar */}
          <div className="lg:col-span-4 space-y-8">
            
            {/* 5. Production Readiness */}
            <Card title="Material Readiness & Route" icon={<Package className="h-4 w-4" />}>
               <div className="space-y-6">
                 <div className={clsx(
                   "rounded-2xl border p-5 flex items-center gap-5 transition-all duration-300",
                   readiness.is_ready ? "bg-emerald-500/10 border-emerald-500/20 shadow-[0_0_20px_rgba(16,185,129,0.05)]" : "bg-amber-500/10 border-amber-500/20 shadow-[0_0_20px_rgba(245,158,11,0.05)]"
                 )}>
                   <div className={clsx(
                     "h-14 w-14 rounded-2xl flex items-center justify-center shadow-lg",
                     readiness.is_ready ? "bg-emerald-500 text-white" : "bg-amber-500 text-white"
                   )}>
                     {readiness.is_ready ? <CheckCircle2 className="h-8 w-8" /> : <AlertTriangle className="h-8 w-8" />}
                   </div>
                   <div>
                      <div className="text-lg font-black text-white uppercase tracking-tight leading-tight">
                        {readiness.status_text || (readiness.is_ready ? "READY" : "BLOCKED")}
                      </div>
                      <div className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                        {readiness.is_ready 
                          ? "Pełna dostępność lub wydanie materiałów. Można rozpoczynać produkcję." 
                          : `Braki materiałowe: ${readiness.missing_materials.join(", ") || "Niewystarczająca ilość na stanie"}`}
                      </div>
                   </div>
                 </div>

                 {/* Per Position Material Detail */}
                 {material_readiness && material_readiness.positions && (
                   <div className="space-y-3">
                     <div className="text-[10px] font-black uppercase tracking-widest text-slate-600 px-1">Gotowość wg pozycji</div>
                     {material_readiness.positions.map((p: any) => (
                       <div key={p.position_id} className="rounded-xl bg-white/[0.02] border border-white/5 p-3 flex flex-col gap-2">
                         <div className="flex items-center justify-between">
                            <span className="text-[10px] font-bold text-slate-300">P{p.position_number}: {p.name}</span>
                            <div className="flex gap-1">
                               <span className={clsx(
                                 "text-[8px] font-black uppercase px-1.5 py-0.5 rounded",
                                 p.status === "Wydano" ? "bg-emerald-500/20 text-emerald-400" :
                                 p.status === "Zarezerwowano" ? "bg-blue-500/20 text-blue-400" :
                                 p.status === "Dostępny" ? "bg-slate-500/20 text-slate-400" : "bg-red-500/20 text-red-400"
                               )}>
                                 Płyta: {p.status}
                               </span>
                               {p.edge.needed > 0 && (
                                 <span className={clsx(
                                   "text-[8px] font-black uppercase px-1.5 py-0.5 rounded",
                                   p.edge_status === "Wydano" ? "bg-emerald-500/20 text-emerald-400" :
                                   p.edge_status === "Zarezerwowano" ? "bg-blue-500/20 text-blue-400" :
                                   p.edge_status === "Dostępny" ? "bg-slate-500/20 text-slate-400" : "bg-red-500/20 text-red-400"
                                 )}>
                                   Okleina: {p.edge_status}
                                 </span>
                               )}
                            </div>
                         </div>
                       </div>
                     ))}
                   </div>
                 )}

                 <div>
                    <div className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-600 mb-4 flex items-center gap-2">
                       <span className="h-px flex-1 bg-white/5" />
                       Akcje Operacyjne
                       <span className="h-px flex-1 bg-white/5" />
                    </div>
                    
                    <div className="grid grid-cols-2 gap-3 mb-4">
                       <Button 
                         onClick={handleReserveMaterials} 
                         disabled={reserving || issuing || material_readiness?.is_all_issued}
                         variant={material_readiness?.is_all_ready ? "primary" : "secondary"}
                         size="sm"
                         className="text-[10px] uppercase font-bold"
                       >
                         {reserving ? <Loader2 className="h-3 w-3 animate-spin mr-2" /> : <Package className="h-3 w-3 mr-2" />}
                         Rezerwuj wszystko
                       </Button>
                       <Button 
                         onClick={handleIssueMaterials} 
                         disabled={issuing || material_readiness?.is_all_issued}
                         variant="primary"
                         size="sm"
                         className="text-[10px] uppercase font-bold"
                       >
                         {issuing ? <Loader2 className="h-3 w-3 animate-spin mr-2" /> : <TrendingUp className="h-3 w-3 mr-2" />}
                         Wydaj na produkcję
                       </Button>
                    </div>

                    <Button 
                      onClick={handleGenerateTasks} 
                      disabled={generating}
                      className="w-full"
                      variant="secondary"
                    >
                      {generating ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Generowanie...
                        </>
                      ) : (
                        "Utwórz zadania produkcyjne"
                      )}
                    </Button>
                 </div>
               </div>
            </Card>

            {/* Production Tasks Listing */}
            {production_tasks.length > 0 && (
              <Card title="Wygenerowane Zadania Produkcyjne" icon={<LayoutList className="h-4 w-4" />}>
                <div className="space-y-6">
                  {["cnc", "oklejanie", "lakiernia", "montaz"].map(station => {
                    const tasks = production_tasks.filter((t: any) => t.task_type === station);
                    if (tasks.length === 0) return null;
                    return (
                      <div key={station}>
                        <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2">{station}</div>
                        <div className="space-y-2">
                          {tasks.map((t: any) => (
                            <div key={t.id} className="flex items-center justify-between rounded-lg border border-white/5 bg-white/[0.02] p-3 text-xs">
                              <div className="flex-1 min-w-0">
                                <div className="font-bold text-slate-200 truncate">{t.notes}</div>
                                <div className="text-[9px] text-slate-500 font-mono mt-0.5">{t.id}</div>
                              </div>
                              <div className={clsx(
                                "ml-3 text-[9px] font-black uppercase px-1.5 py-0.5 rounded",
                                t.status === "wykonane" ? "bg-emerald-500/10 text-emerald-500" : "bg-blue-500/10 text-blue-400"
                              )}>
                                {t.status}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </Card>
            )}

            {/* 4. Calendar Panel */}
            <Card title="Terminy i Harmonogram" icon={<Calendar className="h-4 w-4" />}>
               <div className="space-y-4">
                  {/* Validation alerts */}
                  {(!calendar_events.some((e: any) => e.event_type === "zlecenie" || e.title.toLowerCase().includes("oddanie"))) && (
                     <div className="flex items-start gap-3 rounded-xl border border-red-500/20 bg-red-500/5 p-3 text-red-400 text-[11px]">
                        <AlertTriangle className="h-4 w-4 shrink-0" />
                        <div>
                           <div className="font-bold uppercase tracking-widest">Brak w kalendarzu</div>
                           <p className="mt-1 opacity-80">Termin oddania ({order.deadline_to || order.deadline}) nie został naniesiony na główny harmonogram.</p>
                        </div>
                     </div>
                  )}

                  {(!calendar_events.some((e: any) => e.event_type === "montaż" || e.installation_date)) && order.installation_date && (
                     <div className="flex items-start gap-3 rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 text-amber-400 text-[11px]">
                        <AlertTriangle className="h-4 w-4 shrink-0" />
                        <div>
                           <div className="font-bold uppercase tracking-widest">Brak terminu montażu</div>
                           <p className="mt-1 opacity-80">Planowana data montażu ({order.installation_date}) nie jest widoczna w kalendarzu ekip.</p>
                        </div>
                     </div>
                  )}

                  <div className="space-y-2">
                     {calendar_events.length === 0 ? (
                        <p className="text-[11px] text-slate-600 italic text-center py-4">Brak powiązanych wpisów</p>
                     ) : (
                        calendar_events.map((e: any) => (
                           <div key={e.id} className="group rounded-xl border border-white/5 bg-white/[0.02] p-4 hover:bg-white/[0.04] transition-colors">
                              <div className="flex items-center justify-between mb-1">
                                 <span className="text-[9px] font-black uppercase tracking-widest text-blue-500">{e.event_type}</span>
                                 <span className="text-[9px] text-slate-600">{e.date_from}</span>
                              </div>
                              <div className="text-xs font-bold text-white uppercase tracking-tight">{e.title}</div>
                           </div>
                        ))
                     )}
                  </div>
               </div>
            </Card>

            {/* 6. Finance Summary Panel */}
            <Card title="Status Finansowy" icon={<Coins className="h-4 w-4" />}>
               {finance.by_type?.length === 0 && (finance.budget || 0) === 0 ? (
                 <div className="py-8 text-center text-[11px] text-slate-600 italic">Brak danych finansowych</div>
               ) : (
                 <div className="space-y-6">
                    <div className="flex flex-col gap-1">
                       <span className="text-[10px] font-black uppercase text-slate-600 tracking-widest">Budżet całkowity (Netto)</span>
                       <div className="text-2xl font-orbitron font-black text-white">
                         {(order.budget || 0).toLocaleString()} <span className="text-xs text-slate-500">PLN</span>
                       </div>
                    </div>

                    <div className="h-px bg-white/5" />

                    <div className="space-y-3">
                       <div className="flex justify-between text-[11px]">
                          <span className="text-slate-500 font-bold uppercase tracking-widest">Koszty zaksięgowane</span>
                          <span className="font-black text-red-400">{(finance.total_net || 0).toLocaleString()} PLN</span>
                       </div>
                       <div className="flex justify-between text-[11px]">
                          <span className="text-slate-500 font-bold uppercase tracking-widest">Przewidywana Marża</span>
                          <span className="font-black text-emerald-400">
                             {((order.budget || 0) - (finance.total_net || 0)).toLocaleString()} PLN
                          </span>
                       </div>
                    </div>

                    {finance.by_type?.length > 0 && (
                       <div className="pt-4 border-t border-white/5 space-y-2">
                          <div className="text-[9px] font-black uppercase text-slate-700 tracking-widest mb-2">Rozbicie kosztów</div>
                          {finance.by_type.map((t: any, i: number) => (
                             <div key={i} className="flex justify-between text-[10px]">
                                <span className="text-slate-500">{t.cost_type}</span>
                                <span className="font-bold text-slate-300">{(t.total_net || 0).toLocaleString()} PLN</span>
                             </div>
                          ))}
                       </div>
                    )}
                 </div>
               )}
            </Card>

            {/* 7. Audit Log / History */}
            <Card title="Dziennik Zdarzeń" icon={<History className="h-4 w-4" />}>
               <div className="space-y-6 relative before:absolute before:left-2 before:top-2 before:bottom-2 before:w-px before:bg-white/5">
                  {audit.length === 0 ? (
                    <div className="py-4 text-center text-[11px] text-slate-700 italic">Brak wpisów</div>
                  ) : (
                    audit.map((log: any) => (
                      <div key={log.id} className="relative pl-6">
                        <div className="absolute left-[5.5px] top-1.5 h-2 w-2 rounded-full border-2 border-slate-900 bg-slate-700" />
                        <div className="text-[10px] font-black text-slate-300 uppercase tracking-tight">{log.action}</div>
                        <div className="text-[10px] text-slate-500 mt-1 leading-relaxed">{log.details}</div>
                        <div className="mt-1.5 flex items-center gap-2 text-[8px] text-slate-700 uppercase font-black tracking-widest">
                           <span>{log.timestamp}</span>
                           <span>•</span>
                           <span className="text-blue-500/50">{log.user_name}</span>
                        </div>
                      </div>
                    ))
                  )}
               </div>
            </Card>

          </div>
        </div>
      </div>
    </AppShell>
  );
}
