"use client";

import AppShell from "@/components/AppShell";
import BusinessHealthStrip from "@/components/BusinessHealthStrip";
import PageHeader from "@/components/PageHeader";
import { Card, Button } from "@/components/ui";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  DollarSign,
  Filter,
  Flag,
  UnfoldVertical,
  ChevronRight,
  TrendingUp,
  TriangleAlert,
  RefreshCcw,
  Target,
  Search
} from "lucide-react";
import { useEffect, useState, useMemo } from "react";
import { TechModulAPI, type IssueCandidate } from "@/services/api";
import { motion, AnimatePresence } from "framer-motion";
import clsx from "clsx";

export default function CriPage() {
  const [issues, setIssues] = useState<IssueCandidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    loadIssues();
  }, []);

  const loadIssues = async () => {
    setLoading(true);
    try {
      const data = await TechModulAPI.getIssues();
      setIssues(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const filtered = useMemo(() => {
    return issues.filter(i =>
      i.issue.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (i.issue.project_name || "").toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [issues, searchTerm]);

  const totalUnlock = useMemo(() => {
    return filtered.reduce((sum, i) => sum + (i.issue.estimated_revenue_unlock || 0), 0);
  }, [filtered]);

  const topPriority = useMemo(() => {
    if (issues.length === 0) return null;
    return [...issues].sort((a, b) => b.score - a.score)[0];
  }, [issues]);

  return (
    <AppShell>
      <PageHeader
        eyebrow="Business Strategy & Optimization"
        title={<>Panel <span className="text-brand-hover">Optymalizatora</span> Biznesowego</>}
        subtitle="Algorytm priorytetyzacji wskazuje zadania o najwiekszym wpywie na wynik finansowy."
        actions={
          <div className="flex gap-3">
             <div className="px-4 py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center gap-3 shadow-brand-glow">
                <TrendingUp className="w-4 h-4 text-emerald-500" />
                <div className="text-right">
                   <div className="text-[9px] font-black text-emerald-500/60 uppercase tracking-widest">Wartosc do odblokowania</div>
                   <div className="text-sm font-black text-emerald-400">{totalUnlock.toLocaleString()} PLN</div>
                </div>
             </div>
             <Button onClick={loadIssues} className="bg-panel-solid/50 border-white/5 hover:bg-white/5">
                <RefreshCcw className="w-4 h-4 mr-2" /> Przelicz priorytety
             </Button>
          </div>
        }
      />

      <div className="max-w-6xl mx-auto space-y-8 py-6">
        <BusinessHealthStrip
          scope="Problemy i blokady"
          subtitle="Widok ryzyk: co blokuje pieniadz, terminy i przeplyw pracy w firmie."
        />
        {loading ? (
          <div className="py-24 flex flex-col items-center justify-center text-slate-500">
            <Clock className="w-12 h-12 animate-spin mb-4 opacity-20" />
            <p className="text-xs font-bold uppercase tracking-widest">Uruchamianie silnika optymalizacji...</p>
          </div>
        ) : error ? (
           <Card className="border-red-500/20 bg-red-500/5 p-12 text-center">
              <TriangleAlert className="w-12 h-12 text-red-500 mx-auto mb-4" />
              <h3 className="text-lg font-bold text-white mb-2">Bad silnika</h3>
              <p className="text-slate-400 text-sm">{error}</p>
           </Card>
        ) : issues.length === 0 ? (
          <Card className="p-12 text-center border-emerald-500/20 bg-emerald-500/5">
             <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-4" />
             <h3 className="text-lg font-bold text-white mb-2">System zoptymalizowany</h3>
             <p className="text-slate-400 text-sm">Brak krytycznych blokad. Wszystkie faktury moga byc wystawiane.</p>
          </Card>
        ) : (
          <>
            {/* TOP RECOMMENDATION */}
            {topPriority && (
              <motion.div
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                className="relative"
              >
                 <div className="absolute -inset-0.5 bg-gradient-to-r from-brand-hover via-purple-500 to-brand-hover rounded-3xl blur opacity-30 animate-pulse" />
                 <Card className="relative bg-canvas-deep border-brand-hover/40 p-1 px-1">
                    <div className="flex flex-col md:flex-row items-center gap-6 p-6">
                       <div className="p-5 rounded-2xl bg-brand/20 border border-brand/30 text-brand-hover">
                          <Target className="w-10 h-10" />
                       </div>
                       <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                             <span className="px-2.5 py-1 rounded-full bg-brand-hover/10 border border-brand-hover/30 text-brand-hover text-[9px] font-black uppercase tracking-widest">
                                Rekomendacja Systemu #1
                             </span>
                             <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">
                                Najwyzszy priorytet dla wyniku firmy
                             </span>
                          </div>
                          <h2 className="text-2xl font-black text-white italic tracking-tighter uppercase whitespace-normal">
                             Zajmij sie tym: <span className="text-brand-hover">{topPriority.issue.title}</span>
                          </h2>
                          <div className="flex items-center gap-6 mt-4">
                             <div className="flex items-center gap-2">
                                <DollarSign className="w-4 h-4 text-emerald-400" />
                                <span className="text-xs text-slate-400">
                                   Odblokuj <strong className="text-emerald-400">{topPriority.issue.estimated_revenue_unlock.toLocaleString()} PLN</strong>
                                </span>
                             </div>
                             <div className="flex items-center gap-2">
                                <Clock className="w-4 h-4 text-blue-400" />
                                <span className="text-xs text-slate-400">
                                   Szacowany czas: <strong>{topPriority.issue.estimated_time_minutes} min</strong>
                                </span>
                             </div>
                          </div>
                       </div>
                       <button className="px-8 py-4 rounded-xl bg-brand text-white font-black uppercase tracking-widest text-[11px] hover:bg-brand-hover transition-all shadow-brand-glow">
                          Otworz Projekt
                       </button>
                    </div>
                 </Card>
              </motion.div>
            )}

            <div className="space-y-4 pt-6">
              <div className="flex items-center justify-between mb-2">
                 <h3 className="eyebrow-brand px-2">Pozostae blokady (Kolejka Optymalizacji)</h3>
              </div>

              <div className="grid grid-cols-1 gap-4">
                {issues.map((candidate, idx) => (
                  <motion.div
                    key={candidate.issue.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.05 }}
                  >
                    <Card className={clsx(
                      "group relative overflow-hidden transition-all hover:border-brand-hover/50",
                      candidate.issue.priority_manual === 'krytyczny' ? "border-red-500/30 bg-red-500/5" : "bg-panel-solid/30"
                    )}>
                      <div className="flex flex-col md:flex-row md:items-center gap-6">
                        {/* Priority Score Shield */}
                        <div className="flex flex-col items-center justify-center p-4 min-w-[100px] border-r border-white/5">
                           <div className={clsx(
                             "text-2xl font-black italic",
                             candidate.score > 40 ? "text-red-500" : "text-brand-hover"
                           )}>{candidate.score.toFixed(0)}</div>
                           <div className="text-[8px] font-black text-slate-500 uppercase tracking-widest mt-1">Impact Score</div>
                        </div>

                        {/* Main Info */}
                        <div className="flex-1 space-y-1">
                          <div className="flex items-center gap-3">
                            <span className={clsx(
                              "px-2 py-0.5 rounded text-[9px] font-black uppercase tracking-tighter italic",
                              candidate.issue.priority_manual === 'krytyczny' ? "bg-red-500 text-white" : "bg-brand/20 text-brand-hover"
                            )}>
                              {candidate.issue.priority_manual}
                            </span>
                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                              {candidate.issue.project_name || "Projekt nieprzypisany"}
                            </span>
                          </div>
                          <h4 className="text-lg font-black text-white group-hover:text-brand-hover transition-colors">
                            {candidate.issue.title}
                          </h4>
                          <p className="text-sm text-slate-400 max-w-2xl line-clamp-2 leading-relaxed">
                            {candidate.issue.description}
                          </p>
                        </div>

                        {/* Revenue Unlock */}
                        <div className="text-right pr-6 border-l border-white/5 pl-6 hidden md:block">
                           <div className="text-[9px] font-black text-slate-500 uppercase tracking-widest mb-1">Odblokowuje</div>
                           <div className="text-xl font-black text-emerald-500 tabular-nums">
                             {candidate.issue.estimated_revenue_unlock > 0
                               ? `+${candidate.issue.estimated_revenue_unlock.toLocaleString()} PLN`
                               : "--"}
                           </div>
                        </div>

                        <ChevronRight className="w-5 h-5 text-slate-700 group-hover:text-brand-hover transition-all" />
                      </div>
                    </Card>
                  </motion.div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
