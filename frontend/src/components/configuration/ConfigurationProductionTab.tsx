"use client";

import { Box } from "lucide-react";

type Props = {
  productionSummary: any;
  projectId: number;
  selectedId: string;
};

export default function ConfigurationProductionTab({
  productionSummary,
  projectId,
  selectedId,
}: Props) {
  return (
    <div className="space-y-4">
      <div className="text-[10px] font-black text-slate-400 mb-1">PRODUKCJA (CAM)</div>
      <div className="flex flex-col gap-2">
        <button
          onClick={() => {
            window.open(`http://localhost:8000/api/production/project/${projectId}/export/project`);
          }}
          className="bg-blue-600 hover:bg-blue-500 text-white font-black py-3 rounded-lg w-full cursor-pointer transition-all shadow-lg shadow-blue-900/40 uppercase tracking-tight text-xs flex items-center justify-center gap-2"
        >
          <Box className="w-4 h-4" /> EKSPORT PROJEKTU DO GibLab
        </button>
        <button
          onClick={() => {
            if (!selectedId) {
              alert("Wybierz modul do eksportu.");
              return;
            }
            window.open(`http://localhost:8000/api/config/modules/${selectedId}/export/project`);
          }}
          className="bg-[#2d2d30] hover:bg-[#3e3e42] text-slate-300 font-bold py-2 rounded-sm w-full cursor-pointer transition-colors border border-[#444] text-[10px]"
        >
          Eksport Modulu (.project)
        </button>
        <button
          onClick={() => window.open(`http://localhost:8000/projects/${projectId}/export-pdf`)}
          className="bg-emerald-700 hover:bg-emerald-600 text-white font-bold py-2 rounded-sm w-full border border-emerald-900 cursor-pointer shadow-lg shadow-emerald-900/20"
        >
          Generuj Oferte PDF (Wycena)
        </button>
        <button
          onClick={() => window.open(`http://localhost:8000/api/production/project/${projectId}/export/csv`)}
          className="bg-[#3e3e42] hover:bg-[#555] text-slate-400 font-bold py-1 rounded-sm w-full cursor-pointer transition-colors text-[9px]"
        >
          Lista Ciecia CSV (Ardis/Optimik)
        </button>
      </div>

      {productionSummary && (
        <div className="mt-4 p-3 border border-[#333] bg-[#1a1a1c] rounded-sm shadow-inner text-[10px]">
          <div className="text-slate-400 mb-2 font-black">PODSUMOWANIE SZYBKIE:</div>
          <div className="flex justify-between py-1 border-b border-[#222]">
            <span className="text-slate-500">Ilosc Formatek</span>
            <span className="text-white font-mono">{productionSummary.bom.total_parts}</span>
          </div>
          <div className="flex justify-between py-1 border-b border-[#222]">
            <span className="text-slate-500">M2 Plyty</span>
            <span className="text-white font-mono">{productionSummary.bom.total_area_m2.toFixed(2)}</span>
          </div>
          <div className="flex justify-between py-1 border-[#222]">
            <span className="text-slate-500">Obrzeze (mb)</span>
            <span className="text-white font-mono">{productionSummary.bom.total_edge_m.toFixed(2)}</span>
          </div>

          <div className="mt-4 text-slate-400 mb-2 font-black">WYCENA RYNKOWA:</div>
          <div className="flex justify-between py-1 border-b border-[#222]">
            <span className="text-slate-500">Koszty Materialowe</span>
            <span className="text-red-400 font-mono">{productionSummary.pricing.material_cost} PLN</span>
          </div>
          <div className="flex justify-between py-1 border-[#222]">
            <span className="text-slate-500">Sugerowana Wycena</span>
            <span className="text-emerald-400 font-black text-sm">{productionSummary.pricing.final_price} PLN</span>
          </div>
        </div>
      )}
    </div>
  );
}
