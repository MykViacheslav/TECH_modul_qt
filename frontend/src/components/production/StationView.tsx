"use client";

import { useEffect, useState, useMemo } from "react";
import { Card, Button, StatCard } from "@/components/ui";
import { TechModulAPI, type StationJob } from "@/services/api";
import { 
  Cpu, 
  RefreshCw, 
  Play, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  User, 
  MessageSquare,
  Lock,
  ChevronRight
} from "lucide-react";
import clsx from "clsx";
import Link from "next/link";

interface StationViewProps {
  stationType: string;
  stationName: string;
  stationDescription: string;
  icon?: any;
}

export default function StationView({ stationType, stationName, stationDescription, icon: Icon = Cpu }: StationViewProps) {
  const [tasks, setTasks] = useState<StationJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [operatorName, setOperatorName] = useState(`Operator ${stationName}`);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await TechModulAPI.getStationJobs(stationType);
      setTasks(data || []);
    } catch (e: any) {
      setError(e?.message ?? "Blad ladowania zlecen");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [stationType]);

  const updateStatus = async (taskId: string, newStatus: string, blockedReason?: string) => {
    try {
      await TechModulAPI.updateStationJob(taskId, { 
        status: newStatus, 
        worker: operatorName,
        blocked_reason: blockedReason
      });
      loadData();
    } catch (e: any) {
      alert("Blad aktualizacji statusu: " + e.message);
    }
  };

  const reportProblem = async (taskId: string) => {
    const reason = prompt("Dlaczego praca jest zablokowana? (np. brak materialu, awaria)");
    if (!reason) return;
    updateStatus(taskId, "problem", reason);
  };

  const handoff = async (taskId: string) => {
    try {
      await TechModulAPI.handoffStationJob(taskId, operatorName);
      loadData();
    } catch (e: any) {
      alert("Błąd: " + e.message);
    }
  };

  const accept = async (taskId: string) => {
    try {
      await TechModulAPI.acceptStationJob(taskId, operatorName);
      loadData();
    } catch (e: any) {
      alert("Błąd: " + e.message);
    }
  };

  const reject = async (taskId: string) => {
    const reason = prompt("Dlaczego odrzucasz tę partię? (np. błędne wymiary)");
    if (!reason) return;
    try {
      await TechModulAPI.rejectStationJob(taskId, reason, operatorName);
      loadData();
    } catch (e: any) {
      alert("Błąd: " + e.message);
    }
  };

  const stats = useMemo(() => {
    return {
      waiting: tasks.filter(t => t.status === "planowane" && !t.is_ready).length,
      ready: tasks.filter(t => t.status === "planowane" && t.is_ready).length,
      active: tasks.filter(t => t.status === "w_trasie" || t.status === "w toku").length,
      done: tasks.filter(t => t.status === "wykonane").length,
      problem: tasks.filter(t => t.status === "problem").length,
    };
  }, [tasks]);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <StatCard label="Oczekuje" value={stats.waiting} tone="default" />
        <StatCard label="Gotowe do startu" value={stats.ready} tone="brand" />
        <StatCard label="W trakcie" value={stats.active} tone="brand" />
        <StatCard label="Wykonane dziś" value={stats.done} tone="success" />
        <StatCard label="Problemy" value={stats.problem} tone="danger" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between px-1">
            <h2 className="text-sm font-bold text-slate-500 uppercase tracking-widest">Kolejka zleceń</h2>
            <Button variant="ghost" size="sm" onClick={loadData} disabled={loading}>
              <RefreshCw className={clsx("w-3.5 h-3.5 mr-1", loading && "animate-spin")} /> Odśwież
            </Button>
          </div>

          {loading ? (
            <div className="py-20 text-center text-slate-500 animate-pulse">Ładowanie zadań...</div>
          ) : tasks.length === 0 ? (
            <Card className="flex flex-col items-center justify-center p-20 text-center">
              <Icon className="w-16 h-16 text-slate-800 mb-4" />
              <p className="text-slate-400 font-medium">Brak zleceń dla {stationName}.</p>
            </Card>
          ) : (
            <div className="space-y-3">
              {tasks.map((task) => (
                <Card key={task.id} padded={false} className={clsx(
                  "overflow-hidden border-l-4 transition-all",
                  task.status === "wykonane" ? "border-l-emerald-500 opacity-60" :
                  task.status === "problem" ? "border-l-red-500" :
                  (task.status === "w_trasie" || task.status === "w toku") ? "border-l-brand bg-brand-soft/20 ring-1 ring-brand-ring/30" :
                  !task.is_ready ? "border-l-slate-800 grayscale-[0.5]" : "border-l-slate-600"
                )}>
                  <div className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono text-slate-500 uppercase tracking-tighter">#{task.id}</span>
                        <span className={clsx(
                          "px-1.5 py-0.5 rounded text-[9px] font-black uppercase border tracking-widest",
                          task.status === "wykonane" ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" :
                          task.status === "problem" ? "bg-red-500/10 border-red-500/20 text-red-400" :
                          task.status === "planowane" && !task.is_ready ? "bg-slate-800 border-white/5 text-slate-500" :
                          "bg-white/5 border-white/10 text-slate-300"
                        )}>
                          {task.status === "planowane" && !task.is_ready ? "WAITING" : task.status}
                        </span>
                        {task.prerequisite_blocked && task.prev_handoff_status !== "ready_for_next" && (
                          <span className="flex items-center gap-1 text-[9px] font-bold text-amber-500 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20">
                            <Lock size={10} /> BLOCKED BY {task.prerequisite_name.toUpperCase()}
                          </span>
                        )}
                        {task.prev_handoff_status === "ready_for_next" && task.status === "planowane" && (
                          <span className="flex items-center gap-1 text-[9px] font-bold text-brand bg-brand/10 px-1.5 py-0.5 rounded border border-brand/20 animate-pulse">
                            OCZEKUJE NA AKCEPTACJĘ Z {task.prerequisite_name.toUpperCase()}
                          </span>
                        )}
                      </div>
                      <h3 className="text-base font-bold text-white">{task.project_name}</h3>
                      <p className="text-slate-400 text-xs font-medium">Klient: {task.client_name}</p>
                      
                      {task.quality_result === "needs_rework" && (
                        <div className="mt-2 p-2 bg-red-500/10 border border-red-500/20 rounded text-xs text-red-400 font-bold flex items-center gap-2">
                           <AlertCircle size={14} />
                           ODRZUCONE DO POPRAWY: {task.rework_reason || "Brak powodu"}
                        </div>
                      )}
                      <div className="flex items-center gap-4 mt-2">
                        <div className="flex items-center gap-1.5 text-[10px] text-slate-500 font-bold uppercase tracking-widest">
                          <Clock className="w-3 h-3" />
                          Est. {task.estimated_time_minutes} min
                        </div>
                        {task.status === "problem" && (
                          <div className="flex items-center gap-1.5 text-[10px] text-red-400 font-bold uppercase tracking-widest">
                            <AlertCircle className="w-3 h-3" />
                            {task.blocked_reason || "Problem zgłoszony"}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      {task.prev_handoff_status === "ready_for_next" && task.status === "planowane" && (
                        <>
                          <Button onClick={() => accept(task.id)} size="sm" variant="primary" className="bg-brand hover:bg-brand-hover">
                            <CheckCircle2 className="w-4 h-4 mr-1" /> Akceptuj
                          </Button>
                          <Button onClick={() => reject(task.id)} size="sm" variant="ghost" className="text-red-400 hover:bg-red-500/10">
                            Odrzuć
                          </Button>
                        </>
                      )}
                      {task.status === "planowane" && task.is_ready && task.prev_handoff_status !== "ready_for_next" && (
                        <Button onClick={() => updateStatus(task.id, "w_trasie")} size="sm" variant="primary">
                          <Play className="w-4 h-4 mr-1" /> START
                        </Button>
                      )}
                      {(task.status === "w_trasie" || task.status === "w toku") && (
                        <Button onClick={() => updateStatus(task.id, "wykonane")} size="sm" variant="primary" className="bg-emerald-600 hover:bg-emerald-500">
                          <CheckCircle2 className="w-4 h-4 mr-1" /> GOTOWE
                        </Button>
                      )}
                      {task.status === "wykonane" && task.handoff_status !== "ready_for_next" && task.handoff_status !== "accepted" && (
                        <Button onClick={() => handoff(task.id)} size="sm" variant="primary" className="bg-blue-600 hover:bg-blue-500">
                          <ChevronRight className="w-4 h-4 mr-1" /> Przekaż dalej
                        </Button>
                      )}
                      {task.status === "wykonane" && task.handoff_status === "ready_for_next" && (
                        <span className="text-xs font-bold text-slate-500 flex items-center">
                          Oczekuje na odbiór
                        </span>
                      )}
                      {task.status !== "wykonane" && task.status !== "problem" && task.prev_handoff_status !== "ready_for_next" && (
                        <Button onClick={() => reportProblem(task.id)} size="sm" variant="ghost" className="text-red-400 hover:bg-red-500/10">
                          <AlertCircle className="w-4 h-4 mr-1" /> BLOKADA
                        </Button>
                      )}
                      {task.status === "problem" && (
                        <Button onClick={() => updateStatus(task.id, "planowane")} size="sm" variant="secondary">
                          Ponów
                        </Button>
                      )}
                    </div>
                  </div>
                  {(task.notes || task.blocked_reason) && (
                    <div className="px-4 py-2 bg-black/20 border-t border-white/5 text-[11px] text-slate-400 flex items-start gap-2">
                      <MessageSquare size={12} className="mt-0.5 text-slate-600" />
                      <div className="flex-1">
                         {task.blocked_reason && <span className="text-red-500/80 font-bold block mb-1 uppercase tracking-tighter">Powód blokady: {task.blocked_reason}</span>}
                         {task.notes && <span className="italic">&quot;{task.notes}&quot;</span>}
                      </div>
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-6">
          <Card title="Operator">
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center text-brand border border-white/5">
                  <User className="w-5 h-5" />
                </div>
                <div>
                  <input 
                    type="text" 
                    value={operatorName}
                    onChange={(e) => setOperatorName(e.target.value)}
                    className="bg-transparent border-none text-white font-bold focus:ring-0 p-0 text-sm outline-none"
                  />
                  <p className="text-[10px] text-slate-500 uppercase font-black tracking-widest">Zalogowany jako</p>
                </div>
              </div>
            </div>
          </Card>

          <Card title="Instrukcja Stanowiska">
            <ul className="text-xs text-slate-400 space-y-3 list-disc pl-4">
              <li>{stationDescription}</li>
              <li>Kliknij <strong>START</strong> aby rozpocząć zadanie.</li>
              <li>Jeśli brakuje materiału lub wystąpił błąd, użyj <strong>BLOKADA</strong>.</li>
              <li>Po zakończeniu oznacz jako <strong>GOTOWE</strong>.</li>
              <li>Zadanie automatycznie stanie się gotowe dla kolejnego etapu.</li>
            </ul>
          </Card>

          <Card padded={false} className="overflow-hidden bg-brand/5 border-brand/20">
            <Link href="/production/workflow/readiness" className="p-4 flex items-center justify-between hover:bg-brand/10 transition-colors group">
               <div>
                  <h4 className="text-xs font-bold text-brand group-hover:text-white transition-colors">Overview Produkcji</h4>
                  <p className="text-[10px] text-slate-500 uppercase tracking-widest font-black">Sprawdź status wszystkich projektów</p>
               </div>
               <ChevronRight className="w-5 h-5 text-brand group-hover:translate-x-1 transition-transform" />
            </Link>
          </Card>
        </div>
      </div>
    </div>
  );
}
