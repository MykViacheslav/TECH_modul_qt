"use client";

import React from "react";
import { 
  Package, 
  ArrowRight, 
  ArrowDown, 
  ArrowUp, 
  CheckCircle2, 
  AlertTriangle,
  History,
  ShoppingCart,
  FileOutput,
  RefreshCw
} from "lucide-react";
import { type InventoryMovement } from "@/services/api";
import clsx from "clsx";

interface TraceabilityTimelineProps {
  movements: InventoryMovement[];
  isLoading?: boolean;
}

export default function TraceabilityTimeline({ movements, isLoading }: TraceabilityTimelineProps) {
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center p-12 space-y-4 animate-pulse">
        <RefreshCw className="w-8 h-8 text-brand animate-spin" />
        <p className="text-slate-500 text-sm">Analizowanie Å›ladu kosztowego...</p>
      </div>
    );
  }

  if (!movements || movements.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center">
        <History className="w-12 h-12 text-slate-700 mb-4" />
        <p className="text-slate-400 font-medium">Brak historii ruchÃ³w dla tej pozycji.</p>
        <p className="text-slate-600 text-sm mt-1">Upewnij siÄ™, Å¼e materiaÅ‚ zostaÅ‚ juÅ¼ przyjÄ™ty lub wydany.</p>
      </div>
    );
  }

  const getStepConfig = (m: InventoryMovement) => {
    switch (m.movement_type) {
      case "IN":
        return {
          icon: <ShoppingCart className="w-4 h-4" />,
          title: "Zakup / PrzyjÄ™cie",
          color: "text-emerald-400",
          bg: "bg-emerald-500/10",
          border: "border-emerald-500/20",
          desc: `PrzyjÄ™to ${m.qty} ${m.unit} z dokumentu #${m.purchase_document_id || '?'}`
        };
      case "RESERVED":
        return {
          icon: <Package className="w-4 h-4" />,
          title: "Rezerwacja",
          color: "text-amber-400",
          bg: "bg-amber-500/10",
          border: "border-amber-500/20",
          desc: `Zarezerwowano ${m.qty} ${m.unit} dla zamÃ³wienia #${m.order_id || '?'}`
        };
      case "OUT":
        return {
          icon: <FileOutput className="w-4 h-4" />,
          title: "Wydanie na produkcjÄ™",
          color: "text-blue-400",
          bg: "bg-blue-500/10",
          border: "border-blue-500/20",
          desc: `Wydano ${m.qty} ${m.unit} do zamÃ³wienia #${m.order_id || '?'}`
        };
      case "RETURN":
        return {
          icon: <ArrowUp className="w-4 h-4" />,
          title: "Zwrot z produkcji",
          color: "text-indigo-400",
          bg: "bg-indigo-500/10",
          border: "border-indigo-500/20",
          desc: `ZwrÃ³cono ${m.qty} ${m.unit} na magazyn.`
        };
      case "SCRAP":
        return {
          icon: <AlertTriangle className="w-4 h-4" />,
          title: "Odpis / Brak",
          color: "text-red-400",
          bg: "bg-red-500/10",
          border: "border-red-500/20",
          desc: `Zeskrapowano ${m.qty} ${m.unit}. PowÃ³d: ${m.note || 'Brak danych'}`
        };
      default:
        return {
          icon: <RefreshCw className="w-4 h-4" />,
          title: m.movement_type,
          color: "text-slate-400",
          bg: "bg-slate-500/10",
          border: "border-slate-500/20",
          desc: `${m.qty} ${m.unit} - ${m.note || ''}`
        };
    }
  };

  return (
    <div className="relative space-y-8 before:absolute before:inset-0 before:ml-5 before:-translate-x-px before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-700 before:to-transparent">
      {movements.map((m, idx) => {
        const config = getStepConfig(m);
        return (
          <div key={m.id || idx} className="relative flex items-start group">
            {/* Dot / Icon */}
            <div className={clsx(
              "absolute left-0 flex items-center justify-center w-10 h-10 rounded-full border shadow-lg transition-transform group-hover:scale-110",
              config.bg, config.border, config.color
            )}>
              {config.icon}
            </div>

            {/* Content */}
            <div className="ml-14 flex-1 bg-panel-solid/40 border border-subtle rounded-xl p-4 transition-colors group-hover:border-subtle-strong">
              <div className="flex justify-between items-start mb-1">
                <h4 className={clsx("text-sm font-bold", config.color)}>
                  {config.title}
                </h4>
                <span className="text-[10px] font-mono text-slate-500 uppercase">
                  {m.created_at?.split(' ')[0]}
                </span>
              </div>
              
              <p className="text-slate-300 text-sm mb-3">
                {config.desc}
              </p>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-[10px]">
                <div className="flex flex-col">
                  <span className="text-slate-500 uppercase tracking-widest mb-1">IloÅ›Ä‡</span>
                  <span className="text-white font-medium">{m.qty} {m.unit}</span>
                </div>
                {m.unit_cost_net != null && (
                  <div className="flex flex-col">
                    <span className="text-slate-500 uppercase tracking-widest mb-1">Koszt jedn.</span>
                    <span className="text-white font-medium">{m.unit_cost_net.toFixed(2)} PLN</span>
                  </div>
                )}
                {m.total_cost_net != null && (
                  <div className="flex flex-col">
                    <span className="text-slate-500 uppercase tracking-widest mb-1">WartoÅ›Ä‡</span>
                    <span className="text-white font-medium">{m.total_cost_net.toFixed(2)} PLN</span>
                  </div>
                )}
                <div className="flex flex-col">
                  <span className="text-slate-500 uppercase tracking-widest mb-1">UÅ¼ytkownik</span>
                  <span className="text-white font-medium">{m.created_by || 'system'}</span>
                </div>
              </div>

              {m.note && (
                <div className="mt-3 pt-3 border-t border-white/5 italic text-xs text-slate-500">
                  "{m.note}"
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
