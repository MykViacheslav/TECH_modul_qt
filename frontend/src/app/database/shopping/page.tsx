"use client";

import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Card, Button } from "@/components/ui";
import {
  ShoppingCart,
  Package,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Search,
  ChevronRight,
  Truck,
  DollarSign,
  ArrowLeft,
} from "lucide-react";
import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { TechModulAPI, type IssueCandidate } from "@/services/api";
import { motion, AnimatePresence } from "framer-motion";
import clsx from "clsx";

export default function ShoppingPage() {
  const [issues, setIssues] = useState<IssueCandidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    loadShoppingList();
  }, []);

  const loadShoppingList = async () => {
    setLoading(true);
    try {
      const data = await TechModulAPI.getIssues();
      // Filter for material issues only
      const materialIssues = data.filter(i => i.issue.issue_type === 'brak_materialu');
      setIssues(materialIssues);
    } catch (e) {}
    setLoading(false);
  };

  const filtered = useMemo(() => {
    return issues.filter(i =>
      i.issue.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      i.issue.project_name.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [issues, searchTerm]);

  const toggleBought = async (issueId: string) => {
    // In a real app, this would call TechModulAPI.updateIssueStatus
    // For now, we simulate by removing it from the list (marking as resolved)
    setIssues(prev => prev.filter(i => i.issue.id !== issueId));
    alert("Materia odhaczony jako kupiony/dostarczony!");
  };

  return (
    <AppShell>
      <PageHeader
        eyebrow={
          <Link
            href="/database"
            className="flex items-center gap-1 hover:text-brand transition-colors group"
          >
            <ArrowLeft size={12} className="group-hover:-translate-x-0.5 transition-transform" />
            Powrot do Centrum Baz
          </Link>
        }
        title={<>Lista <span className="text-brand-hover">Zakupow i Brakow</span></>}
        subtitle="Zestawienie materiaow i okuc, ktorych brakuje do realizacji zlecen."
        actions={
          <div className="flex gap-2">
            <div className="relative">
               <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
               <input
                 value={searchTerm}
                 onChange={(e) => setSearchTerm(e.target.value)}
                 placeholder="Szukaj materiau..."
                 className="input-base pl-10 w-64"
               />
            </div>
            <Button onClick={loadShoppingList}>Odswiez</Button>
          </div>
        }
      />

      <div className="max-w-5xl mx-auto py-6 space-y-6">
        {loading ? (
          <div className="py-24 text-center text-slate-500 uppercase tracking-widest text-[10px] font-black italic">
             Generowanie listy potrzeb materiaowych...
          </div>
        ) : filtered.length === 0 ? (
          <Card className="p-20 text-center border-emerald-500/20 bg-emerald-500/5">
             <CheckCircle2 className="w-16 h-16 text-emerald-500 mx-auto mb-6" />
             <h3 className="text-2xl font-black text-white italic tracking-tighter uppercase mb-2">Magazyn Peny</h3>
             <p className="text-slate-400">Wszystkie niezbedne materiay sa na stanie.</p>
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-4">
             {filtered.map((item, idx) => (
               <motion.div
                 key={item.issue.id}
                 initial={{ opacity: 0, x: -20 }}
                 animate={{ opacity: 1, x: 0 }}
                 transition={{ delay: idx * 0.05 }}
               >
                 <Card className="group relative overflow-hidden p-0 border-white/5 bg-panel-solid/30 hover:border-brand-hover/40 transition-all">
                    <div className="flex items-stretch">
                       {/* Priority Indicator */}
                       <div className={clsx(
                         "w-1.5 shrink-0",
                         item.score > 40 ? "bg-red-500" : "bg-brand"
                       )} />

                       <div className="flex-1 p-4 md:p-6 flex flex-col gap-4">
                          <div className="flex flex-col md:flex-row md:items-start gap-4 md:gap-8">
                             <div className="hidden md:flex p-4 rounded-2xl bg-white/5 border border-white/5 text-slate-400">
                                <Package className="w-6 h-6" />
                             </div>

                             <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1.5 overflow-hidden">
                                   <span className="px-2 py-0.5 rounded bg-brand/10 text-brand-hover text-[8px] font-black uppercase tracking-widest whitespace-nowrap">
                                      {item.issue.project_name}
                                   </span>
                                   <span className="text-[9px] text-slate-500 font-bold uppercase shrink-0">
                                      #{item.issue.id.split('-').pop()}
                                   </span>
                                </div>
                                <h4 className="text-base md:text-lg font-black text-white group-hover:text-brand-hover transition-colors truncate">
                                   {item.issue.title}
                                </h4>
                                <p className="text-[11px] md:text-xs text-slate-500 mt-1 line-clamp-2 leading-relaxed">
                                   {item.issue.description}
                                </p>
                             </div>

                             <div className="text-right hidden md:block border-l border-white/5 pl-6 shrink-0">
                                <div className="text-[8px] text-slate-600 font-bold uppercase tracking-widest mb-0.5">Szacowany koszt</div>
                                <div className="text-lg font-black text-emerald-500 tabular-nums">
                                   {item.issue.estimated_cost?.toLocaleString()} PLN
                                </div>
                             </div>
                          </div>

                          {/* Purchase Form (Partial/Full) */}
                          <div className="mt-2 p-4 rounded-2xl bg-white/[0.02] border border-white/5 grid grid-cols-2 md:grid-cols-4 gap-3">
                             <div className="flex flex-col gap-1">
                                <label className="text-[8px] font-black text-slate-500 uppercase">Ilosc Kupiona</label>
                                <div className="flex items-center gap-2">
                                   <input
                                     type="number"
                                     defaultValue={item.issue.quantity_required}
                                     className="w-full bg-canvas-deep border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:border-brand-hover outline-none"
                                   />
                                   <span className="text-[10px] text-slate-600 font-bold uppercase">/ {item.issue.quantity_required}</span>
                                </div>
                             </div>
                             <div className="flex flex-col gap-1">
                                <label className="text-[8px] font-black text-slate-500 uppercase">Dostawca</label>
                                <input
                                  placeholder="Miejsce zakupu..."
                                  className="bg-canvas-deep border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:border-brand-hover outline-none"
                                />
                             </div>
                             <div className="flex flex-col gap-1">
                                <label className="text-[8px] font-black text-slate-500 uppercase">Cena Faktyczna</label>
                                <div className="relative">
                                   <input
                                     placeholder="0.00"
                                     className="w-full bg-canvas-deep border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:border-brand-hover outline-none pl-7"
                                   />
                                   <DollarSign className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-600" />
                                </div>
                             </div>
                             <div className="flex items-end">
                                <button
                                  onClick={() => toggleBought(item.issue.id)}
                                  className="w-full bg-emerald-500 hover:bg-emerald-400 text-white py-2 rounded-lg font-black uppercase tracking-widest text-[9px] shadow-lg shadow-emerald-500/10 transition-all active:scale-95 flex items-center justify-center gap-2"
                                >
                                   ZATWIERDZ <ChevronRight className="w-3 h-3" />
                                </button>
                             </div>
                          </div>
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
