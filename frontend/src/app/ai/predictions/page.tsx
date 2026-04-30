"use client";

import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Card, Button } from "@/components/ui";
import {
  Telescope,
  BrainCircuit,
  TriangleAlert,
  TrendingDown,
  TrendingUp,
  Clock,
  ChevronRight,
  Zap,
  ShieldCheck,
  BarChart3
} from "lucide-react";
import { useEffect, useState } from "react";
import { TechModulAPI, type AiPrediction } from "@/services/api";
import { motion } from "framer-motion";
import clsx from "clsx";

export default function AiPredictionsPage() {
  const [predictions, setPredictions] = useState<AiPrediction[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPredictions();
  }, []);

  const loadPredictions = async () => {
    setLoading(true);
    try {
      const data = await TechModulAPI.getAiPredictions();
      setPredictions(data.predictions);
    } catch (e) {}
    setLoading(false);
  };

  return (
    <AppShell>
      <PageHeader
        eyebrow="AI Predictive Analysis"
        title={<>Cyfrowy <span className="text-brand-hover">Jasnowidz AI</span></>}
        subtitle="Analiza predykcyjna przewiduje opoznienia i waskie garda zanim wystapia."
        actions={
          <Button onClick={loadPredictions} className="bg-brand/20 border-brand/30 text-brand-hover">
            <Zap className="w-4 h-4 mr-2" /> Przelicz prognozy
          </Button>
        }
      />

      <div className="max-w-6xl mx-auto py-8">
         <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
            {/* MAIN FORECASTS */}
            <div className="lg:col-span-3 space-y-6">
               <h3 className="eyebrow-brand px-2 text-slate-500">Kluczowe Prognozy Operacyjne</h3>

               {loading ? (
                 <div className="py-20 text-center animate-pulse">
                    <BrainCircuit size={48} className="mx-auto mb-4 text-brand-hover opacity-20" />
                    <p className="text-xs font-black uppercase tracking-widest text-slate-600">Analizowanie trendow hali...</p>
                 </div>
               ) : (
                 <div className="grid grid-cols-1 gap-4">
                    {predictions.map((p, i) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.1 }}
                      >
                         <Card className={clsx(
                           "relative overflow-hidden group transition-all hover:bg-white/[0.02]",
                           p.severity === 'high' ? "border-red-500/30 bg-red-500/5 shadow-2xl shadow-red-500/5" : "border-white/5 bg-panel-solid/30"
                         )}>
                            <div className="flex items-stretch min-h-[140px]">
                               <div className={clsx(
                                 "w-2 shrink-0",
                                 p.severity === 'high' ? "bg-red-500" : p.severity === 'medium' ? "bg-amber-500" : "bg-blue-500"
                               )} />
                               <div className="flex-1 p-8 flex flex-col md:flex-row md:items-center gap-8">
                                  <div className="flex-1">
                                     <div className="flex items-center gap-3 mb-2">
                                        <PredictionIcon type={p.type} />
                                        <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Typ: {p.type}</span>
                                        <div className="px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-[9px] font-bold text-slate-400">
                                           Prawdopodobienstwo: {(p.confidence * 100).toFixed(0)}%
                                        </div>
                                     </div>
                                     <h4 className="text-2xl font-black text-white italic uppercase tracking-tighter mb-2">
                                        {p.title}
                                     </h4>
                                     <p className="text-sm text-slate-400 max-w-2xl leading-relaxed">
                                        {p.content}
                                     </p>
                                  </div>
                                  <div className="shrink-0 flex flex-col items-end gap-4">
                                     <div className={clsx(
                                       "px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest flex items-center gap-2",
                                       p.severity === 'high' ? "bg-red-500 text-white" : "bg-white/5 text-slate-400 border border-white/5"
                                     )}>
                                        {p.severity === 'high' ? <TriangleAlert size={14} /> : <ShieldCheck size={14} />}
                                        Poziom Ryzyka: {p.severity}
                                     </div>
                                     <button className="text-[9px] font-black text-brand-hover uppercase tracking-widest border-b border-brand-hover/0 hover:border-brand-hover transition-all">
                                        Zastosuj sugerowana akcje
                                     </button>
                                  </div>
                               </div>
                            </div>
                         </Card>
                      </motion.div>
                    ))}
                 </div>
               )}
            </div>

            {/* AI STATS & INSIGHTS */}
            <div className="space-y-6">
               <h3 className="eyebrow-brand px-2">Analityka AI</h3>
               <Card className="p-6 bg-canvas-deep border-white/5 space-y-8">
                  <div className="flex flex-col">
                     <div className="flex items-center justify-between mb-2">
                        <span className="text-[9px] font-black text-slate-600 uppercase">Ogolna Droznosc Hali</span>
                        <TrendingUp size={14} className="text-emerald-500" />
                     </div>
                     <span className="text-3xl font-black italic text-emerald-500">82%</span>
                     <p className="text-[10px] text-slate-500 font-bold mt-1">+4.5% wzgledem zeszego tygodnia</p>
                  </div>

                  <div className="flex flex-col">
                     <div className="flex items-center justify-between mb-2">
                        <span className="text-[9px] font-black text-slate-600 uppercase">Przewidywane Finanse</span>
                        <BarChart3 size={14} className="text-brand-hover" />
                     </div>
                     <span className="text-2xl font-black italic">Stabilne</span>
                     <p className="text-[10px] text-slate-500 font-bold mt-1">Cashflow bezpieczny na min. 45 dni</p>
                  </div>

                  <div className="pt-4 border-t border-white/5">
                     <h5 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-4">Waskie garda (7 dni)</h5>
                     <div className="space-y-4">
                        <LoadIndicator label="CNC" progress={35} />
                        <LoadIndicator label="LAKIER" progress={85} warning />
                        <LoadIndicator label="MONTAZ" progress={60} />
                     </div>
                  </div>
               </Card>
            </div>
         </div>
      </div>
    </AppShell>
  );
}

function PredictionIcon({ type }: { type: string }) {
  if (type === 'delay') return <Clock className="w-4 h-4 text-red-400" />;
  if (type === 'bottleneck') return <Zap className="w-4 h-4 text-amber-400" />;
  return <BarChart3 className="w-4 h-4 text-blue-400" />;
}

function LoadIndicator({ label, progress, warning }: { label: string, progress: number, warning?: boolean }) {
  return (
    <div className="space-y-1.5">
       <div className="flex items-center justify-between text-[8px] font-black uppercase text-slate-500">
          <span>{label}</span>
          <span>{progress}%</span>
       </div>
       <div className="w-full h-1 bg-white/5 rounded-full overflow-hidden">
          <div
            className={clsx("h-full transition-all duration-1000", warning ? "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]" : "bg-brand")}
            style={{ width: `${progress}%` }}
          />
       </div>
    </div>
  )
}
