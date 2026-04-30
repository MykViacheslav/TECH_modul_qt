"use client";

import { useEffect, useState, useMemo } from "react";
import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Card, Button } from "@/components/ui";
import { TechModulAPI, type ProjectProductionReadiness } from "@/services/api";
import { 
  Workflow, 
  RefreshCw, 
  AlertCircle, 
  CheckCircle2, 
  Clock, 
  ArrowRight,
  Search,
  Filter,
  AlertTriangle
} from "lucide-react";
import clsx from "clsx";
import Link from "next/link";

const STAGE_ORDER = ["cnc", "oklejanie", "lakiernia", "montaz", "pakowanie"];

const STAGE_LABELS: Record<string, string> = {
  cnc: "CNC",
  oklejanie: "Oklejanie",
  lakiernia: "Lakiernia",
  montaz: "Montaż",
  pakowanie: "Pakowanie",
  production_complete: "Zakończone"
};

export default function ProductionReadinessPage() {
  const [projects, setProjects] = useState<ProjectProductionReadiness[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await TechModulAPI.getProductionWorkflowReadiness();
      setProjects(data || []);
    } catch (e: any) {
      setError(e?.message ?? "Błąd ładowania statusu produkcji");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filtered = useMemo(() => {
    return projects.filter(p => {
      const matchesSearch = !search || 
        p.project_name.toLowerCase().includes(search.toLowerCase()) || 
        p.client_name.toLowerCase().includes(search.toLowerCase());
      
      const matchesFilter = filter === "all" || 
        (filter === "blocked" && p.is_blocked) ||
        (filter === "active" && !p.is_blocked && p.current_stage !== "done") ||
        (filter === "done" && p.current_stage === "done");
        
      return matchesSearch && matchesFilter;
    });
  }, [projects, search, filter]);

  return (
    <AppShell>
      <PageHeader
        eyebrow="Monitoring Produkcji"
        title="Workflow Overview"
        subtitle="Analiza postępów produkcji i identyfikacja wąskich gardeł."
        actions={
          <Button onClick={loadData} disabled={loading}>
            <RefreshCw className={clsx("w-4 h-4 mr-1", loading && "animate-spin")} /> Odśwież
          </Button>
        }
      />

      <div className="max-w-7xl mx-auto space-y-6 pb-20">
        <Card className="p-4 flex flex-wrap gap-4 items-center">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input 
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Szukaj projektu lub klienta..."
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
              <option value="all">Wszystkie projekty</option>
              <option value="active">W produkcji</option>
              <option value="blocked">Zablokowane</option>
              <option value="done">Zakończone</option>
            </select>
          </div>
        </Card>

        {loading ? (
          <div className="py-20 text-center text-slate-500 animate-pulse">Analizowanie workflow...</div>
        ) : filtered.length === 0 ? (
          <div className="py-20 text-center text-slate-600">Brak projektów pasujących do filtrów.</div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {filtered.map((project) => (
              <Card key={project.project_name} padded={false} className={clsx(
                "overflow-hidden border-white/5",
                project.is_blocked && "border-red-500/20 bg-red-500/5"
              )}>
                <div className="p-5 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <h3 className="text-lg font-bold text-white">{project.project_name}</h3>
                      {project.is_blocked && (
                        <span className="flex items-center gap-1 text-[10px] font-black uppercase bg-red-500/10 text-red-500 px-2 py-0.5 rounded border border-red-500/20 animate-pulse">
                          <AlertTriangle size={10} /> Blocked
                        </span>
                      )}
                    {project.is_complete && (
                       <span className="flex items-center gap-1 text-[10px] font-black uppercase bg-emerald-500/10 text-emerald-500 px-2 py-0.5 rounded border border-emerald-500/20">
                         <CheckCircle2 size={10} /> Gotowe do wysyłki
                       </span>
                    )}
                    </div>
                    <p className="text-sm text-slate-400">Klient: {project.client_name}</p>
                    
                    {project.is_blocked && (
                      <div className="mt-3 p-2 bg-red-500/10 border border-red-500/20 rounded text-xs text-red-400 font-bold flex items-center gap-2">
                         <AlertCircle size={14} />
                         {project.blocked_reason}
                      </div>
                    )}
                  </div>

                  {/* Progress Bar / Steps */}
                  <div className="flex-1 max-w-2xl">
                    <div className="flex items-center justify-between px-1 mb-2">
                      <span className="text-[10px] text-slate-500 font-black uppercase tracking-widest">Production Pipeline</span>
                      <span className="text-[10px] text-slate-400 italic">Ostatnia zmiana: {project.last_update?.split(" ")[0]}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      {STAGE_ORDER.map((stage, idx) => {
                        const status = project.stages[stage] || "waiting";
                        return (
                          <div key={stage} className="flex-1 flex flex-col gap-1.5">
                            <div className={clsx(
                              "h-1.5 rounded-full transition-all",
                              (status === "done" || status === "accepted") ? "bg-emerald-500 shadow-glow shadow-emerald-500/50" :
                              (status === "blocked" || status === "rejected") ? "bg-red-500 shadow-glow shadow-red-500/50" :
                              status === "rework" ? "bg-orange-500 shadow-glow shadow-orange-500/50 animate-pulse" :
                              status === "pending_handoff" ? "bg-blue-500 shadow-glow shadow-blue-500/50 animate-pulse" :
                              status === "in_progress" ? "bg-brand animate-pulse" :
                              status === "waiting" ? "bg-slate-800" :
                              "bg-slate-900"
                            )} />
                            <div className={clsx(
                              "text-[9px] font-black text-center uppercase tracking-tighter truncate px-0.5",
                              (status === "done" || status === "accepted") ? "text-emerald-500" :
                              (status === "blocked" || status === "rejected") ? "text-red-500" :
                              status === "rework" ? "text-orange-500" :
                              status === "pending_handoff" ? "text-blue-500" :
                              status === "in_progress" ? "text-brand" :
                              "text-slate-600"
                            )}>
                              {STAGE_LABELS[stage]}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  <div className="shrink-0 flex items-center gap-4">
                     <div className="text-right">
                       <div className="text-[9px] text-slate-500 font-black uppercase">Obecny Etap</div>
                       <div className={clsx(
                         "text-sm font-bold uppercase",
                         project.is_blocked ? "text-red-500" : 
                         project.is_complete ? "text-emerald-500" : "text-white"
                       )}>
                         {project.current_stage ? STAGE_LABELS[project.current_stage] || project.current_stage.replace("_", " ") : "Oczekuje"}
                       </div>
                    </div>
                    {project.current_stage && project.current_stage !== "done" && project.current_stage !== "production_complete" && (
                      <Link href={`/stations/${project.current_stage.toLowerCase()}`}>
                        <Button variant="secondary" size="sm">
                          Go to Station <ArrowRight size={14} className="ml-1" />
                        </Button>
                      </Link>
                    )}
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
