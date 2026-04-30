"use client";

import clsx from "clsx";
import { Box, Layers, Loader2, Zap } from "lucide-react";

type Props = {
  productionSummary: any;
  projectId: number;
  selectedId: string;
  onSelectModule: (id: string) => void;
};

export default function ConfigurationValuationTab({
  productionSummary,
  projectId,
  selectedId,
  onSelectModule,
}: Props) {
  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div className="flex flex-col gap-1 border-b border-[#333] pb-4 mb-2">
        <div className="text-[13px] font-black text-white tracking-tight flex items-center gap-2">
          <Layers className="w-4 h-4 text-blue-500" /> PODSUMOWANIE PROJEKTU
        </div>
        <div className="text-[10px] text-slate-500 font-mono tracking-widest uppercase">SYGNATURA: PRJ-{projectId}</div>
      </div>

      {productionSummary ? (
        <div className="space-y-6">
          <div className="bg-gradient-to-br from-[#1e1e20] to-[#111] p-6 border border-[#333] rounded-xl shadow-2xl relative overflow-hidden group border-l-4 border-l-emerald-500">
            <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 blur-3xl group-hover:bg-emerald-500/10 transition-all"></div>
            <div className="text-[10px] text-slate-400 font-black uppercase mb-2 tracking-widest">Calkowita wycena sugerowana (brutto)</div>
            <div className="text-4xl font-black text-white flex items-baseline gap-2 tabular-nums">
              {productionSummary.pricing.final_price} <span className="text-sm text-slate-500 font-bold">PLN</span>
            </div>

            <div className="mt-6 pt-4 border-t border-[#333] grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1">
                <span className="text-[10px] text-slate-500 font-black uppercase tracking-wider">Koszt materialow</span>
                <span className="text-lg font-bold text-red-500/90 font-mono">-{productionSummary.pricing.material_cost} <span className="text-[10px]">PLN</span></span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[10px] text-slate-500 font-black uppercase tracking-wider">Est. robocizna</span>
                <span className="text-lg font-bold text-blue-400 font-mono">+{productionSummary.pricing.labor_cost} <span className="text-[10px]">PLN</span></span>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between px-1">
              <span className="text-[11px] text-slate-300 font-black uppercase tracking-wider">Moduly w scenie</span>
              <span className="bg-[#333] text-white text-[10px] px-2 py-0.5 rounded-full font-bold">{Object.keys(productionSummary.modules || {}).length}</span>
            </div>
            <div className="space-y-2">
              {Object.entries(productionSummary.modules || {}).map(([id, mod]: [string, any]) => (
                <div
                  key={id}
                  className={clsx(
                    "bg-[#252526] hover:bg-[#2d2d30] p-3 border rounded-lg transition-all flex justify-between items-center group cursor-pointer shadow-sm",
                    selectedId === id ? "border-blue-500 ring-1 ring-blue-500/50 bg-[#2d323a]" : "border-[#333]"
                  )}
                  onClick={() => onSelectModule(id)}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-[#1a1a1c] rounded-md flex items-center justify-center border border-[#444] text-slate-500 group-hover:text-blue-400 transition-colors">
                      <Box className="w-4 h-4" />
                    </div>
                    <div className="flex flex-col">
                      <span className="text-slate-200 font-bold text-[12px] group-hover:text-white transition-colors">{mod.name}</span>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[9px] text-slate-500 font-bold uppercase tracking-tighter">{mod.parts_count} CZESCI</span>
                        <span className="w-1 h-1 bg-[#444] rounded-full"></span>
                        <span className="text-[9px] text-slate-500 font-bold font-mono tracking-tighter">{mod.area_m2.toFixed(2)} M2</span>
                      </div>
                    </div>
                  </div>
                  <div className="text-emerald-400 font-mono font-black text-[13px] bg-emerald-400/5 px-2 py-1 rounded-md border border-emerald-400/10">
                    {mod.cost.toFixed(0)} <span className="text-[10px] font-bold">PLN</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="p-5 bg-[#1a1a1c] border border-[#333] rounded-xl shadow-inner shadow-black/40">
            <div className="flex items-center gap-2 text-[10px] text-slate-400 font-black uppercase mb-4 pb-2 border-b border-[#222]">
              <Zap className="w-3 h-3 text-amber-500" /> Baza materialowa (agregacja)
            </div>
            <div className="space-y-4">
              {Object.entries(productionSummary.material_usage || {}).map(([key, mat]: [string, any]) => (
                <div key={key} className="space-y-1.5 group">
                  <div className="flex justify-between text-[11px] items-center">
                    <span className="text-slate-300 font-bold group-hover:text-blue-400 transition-colors">{mat.name}</span>
                    <div className="flex items-baseline gap-1">
                      <span className="text-white font-mono font-bold">{mat.total_m2.toFixed(3)}</span>
                      <span className="text-[9px] text-slate-500 font-black uppercase">m2</span>
                    </div>
                  </div>
                  <div className="h-1.5 bg-[#111] rounded-full overflow-hidden border border-[#222]">
                    <div
                      className="h-full bg-gradient-to-r from-blue-600 to-blue-400 rounded-full transition-all duration-700 shadow-[0_0_8px_rgba(37,99,235,0.4)]"
                      style={{ width: `${Math.min(100, (mat.total_m2 / (productionSummary.bom.total_area_m2 || 1)) * 100)}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4 pt-3 border-t border-[#222] flex justify-between text-[10px] font-black text-slate-500">
              <span>SUMA POWIERZCHNI</span>
              <span className="text-slate-300">{productionSummary.bom.total_area_m2.toFixed(2)} m2</span>
            </div>
          </div>

          <div className="pt-4">
            <button
              onClick={() => window.open(`http://localhost:8000/projects/${projectId}/export-pdf`)}
              className="w-full bg-blue-600/10 hover:bg-blue-600 text-blue-500 hover:text-white border border-blue-500/20 hover:border-blue-500 font-black py-3 rounded-xl transition-all uppercase tracking-widest text-xs flex items-center justify-center gap-2 shadow-lg shadow-blue-900/10 active:scale-[0.98]"
            >
              POBIERZ ARKUSZ WYCENY (PDF)
            </button>
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center h-80 gap-4 border-2 border-dashed border-[#333] rounded-2xl bg-[#111]/30">
          <div className="relative">
            <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
            <div className="absolute inset-0 bg-blue-500/10 blur-xl animate-pulse"></div>
          </div>
          <div className="flex flex-col items-center gap-1">
            <span className="text-slate-300 text-[12px] font-black uppercase tracking-widest">Analizowanie produkcji</span>
            <span className="text-[10px] text-slate-600 font-bold uppercase animate-pulse italic">Czekam na silnik wyceny...</span>
          </div>
        </div>
      )}
    </div>
  );
}
