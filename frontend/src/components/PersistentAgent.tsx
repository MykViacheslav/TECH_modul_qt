"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles,
  X,
  Target,
  DollarSign,
  Clock,
  TriangleAlert,
  Info,
  TrendingUp,
  ChevronRight,
  MessageSquare,
  ShoppingCart,
  Send
} from "lucide-react";
import { TechModulAPI, type AiTip } from "@/services/api";
import clsx from "clsx";

export default function PersistentAgent() {
  const [tips, setTips] = useState<AiTip[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [tipIdx, setTipIdx] = useState(0);
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [chatMsg, setChatMsg] = useState("");
  const [isChatting, setIsChatting] = useState(false);

  const fetchTips = async () => {
    try {
      const res = await TechModulAPI.getAiAdvice();
      setTips(res.tips);
      setLastUpdate(new Date());
    } catch (e) {}
  };

  useEffect(() => {
    fetchTips();
    const interval = setInterval(fetchTips, 30000); // 30s
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (tips.length <= 1) return;
    const interval = setInterval(() => {
       if (!isOpen) {
         setTipIdx(prev => (prev + 1) % tips.length);
       }
    }, 10000);
    return () => clearInterval(interval);
  }, [tips, isOpen]);

  const currentTip = tips[tipIdx];

  return (
    <div className="fixed bottom-10 right-10 z-[100] flex flex-col items-end gap-3 pointer-events-none">
      {/* Expanded Advice Panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            className="w-80 rounded-3xl bg-panel-solid/80 border border-brand/20 backdrop-blur-3xl shadow-2xl p-6 mb-2 pointer-events-auto overflow-hidden relative"
          >
             <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-brand to-purple-500" />
             <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                   <Target className="w-4 h-4 text-brand-hover" />
                   <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Strateg AI Professional</span>
                </div>
                <div className="flex items-center gap-2">
                   <button
                      onClick={() => window.location.href = '/database/shopping'}
                      className="p-1.5 hover:bg-emerald-500/10 rounded-lg transition-colors group"
                      title="Lista Zakupow"
                   >
                      <ShoppingCart className="w-3.5 h-3.5 text-emerald-500 group-hover:scale-110 transition-transform" />
                   </button>
                   <button onClick={() => setIsOpen(false)} className="p-1 hover:bg-white/5 rounded-lg transition-colors">
                      <X className="w-4 h-4 text-slate-500" />
                   </button>
                </div>
             </div>

             <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
                {tips.map((tip, i) => (
                   <div
                     key={i}
                     className={clsx(
                       "p-4 rounded-2xl border transition-all cursor-pointer group relative overflow-hidden",
                       i === tipIdx ? "bg-brand/10 border-brand/30 ring-1 ring-brand/20" : "bg-white/5 border-white/5 hover:border-white/10"
                     )}
                     onClick={() => setTipIdx(i)}
                   >
                      <div className="flex items-center gap-3 mb-2">
                         <TipIcon type={tip.type} />
                         <span className="text-[9px] font-black uppercase tracking-widest text-white">{tip.title}</span>
                      </div>
                      <p className="text-[11px] text-slate-400 leading-relaxed group-hover:text-slate-300 transition-colors">
                         {tip.content}
                      </p>
                      <div className="mt-2 text-[9px] font-bold text-brand-hover uppercase italic">Wpyw: {tip.impact}</div>
                   </div>
                ))}
             </div>

             {/* AI CHAT INPUT */}
             <div className="mt-6 pt-4 border-t border-white/5">
                <div className="relative">
                   <input
                     value={chatMsg}
                     onChange={(e) => setChatMsg(e.target.value)}
                     onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                           // Placeholder for chat logic
                           setChatMsg("");
                           alert("Agent analizuje: " + chatMsg + "... (Wdrazam logike AI)");
                        }
                     }}
                     placeholder="Zapyaj o produkcje, zakupy..."
                     className="w-full bg-canvas-deep border border-brand/20 rounded-xl py-2.5 pl-4 pr-10 text-[11px] placeholder:text-slate-600 focus:border-brand-hover outline-none transition-all"
                   />
                   <button className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-brand-hover hover:scale-110 transition-all">
                      <Send className="w-3.5 h-3.5" />
                   </button>
                </div>
             </div>

             <div className="mt-4 flex items-center justify-between">
                <div className="text-[8px] text-slate-600 font-bold uppercase tracking-widest">Synch: {lastUpdate.toLocaleTimeString()}</div>
                <div className="flex gap-2 text-[9px] font-black text-white/40 uppercase tracking-widest italic animate-pulse">
                   System Ready
                </div>
             </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Persistent Bubble (Visible always) */}
      <AnimatePresence>
        {!isOpen && currentTip && (
           <motion.div
             initial={{ opacity: 0, x: 50 }}
             animate={{ opacity: 1, x: 0 }}
             exit={{ opacity: 0, x: 50 }}
             onClick={() => setIsOpen(true)}
             className="flex items-center gap-4 bg-panel-solid/40 border border-brand/10 backdrop-blur-xl px-4 py-3 rounded-2xl shadow-xl pointer-events-auto cursor-pointer hover:border-brand/40 group transition-all"
           >
              <div className="flex flex-col items-end">
                 <div className="text-[8px] font-black text-brand-hover uppercase tracking-widest mb-0.5">Strateg AI radzi:</div>
                 <div className="text-[11px] text-slate-300 font-bold italic line-clamp-1 max-w-[180px] group-hover:text-white transition-colors">
                    {currentTip.title}
                 </div>
              </div>
              <div className="relative">
                 <div className="absolute -inset-2 bg-brand/20 rounded-full blur animate-pulse" />
                 <div className="w-10 h-10 rounded-xl bg-brand/10 border border-brand/20 flex items-center justify-center text-brand-hover relative">
                    <Sparkles className="w-5 h-5" />
                 </div>
              </div>
           </motion.div>
        )}
      </AnimatePresence>

      {/* Floating Action Button (Alternative trigger) */}
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => setIsOpen(!isOpen)}
        className={clsx(
           "w-14 h-14 rounded-2xl flex items-center justify-center shadow-brand-glow pointer-events-auto transition-all",
           isOpen ? "bg-slate-800 border border-white/10 text-white rotate-45" : "bg-brand text-white"
        )}
      >
        <Sparkles className="w-6 h-6" />
      </motion.button>
    </div>
  );
}

function TipIcon({ type }: { type: string }) {
   if (type === 'warning') return <TriangleAlert className="w-3.5 h-3.5 text-red-400" />;
   if (type === 'opportunity') return <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />;
   return <Info className="w-3.5 h-3.5 text-blue-400" />;
}
