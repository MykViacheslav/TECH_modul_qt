"use client";

import clsx from "clsx";
import { X } from "lucide-react";

type Props = {
  editingPart: any;
  allMaterials: any[];
  onClose: () => void;
  updatePartProperty: (partId: string, properties: any) => void;
};

export default function ConfigurationPartInspector({
  editingPart,
  allMaterials,
  onClose,
  updatePartProperty,
}: Props) {
  if (!editingPart) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-[#1e1e1e] border border-[#333] shadow-2xl rounded-sm w-[420px] overflow-hidden flex flex-col animate-in fade-in zoom-in-95 duration-200">
        <div className="h-10 border-b border-[#333] bg-[#2d2d2d] flex items-center justify-between px-4">
          <span className="font-bold text-slate-200 uppercase tracking-widest text-[10px]">Inspektor Formatek</span>
          <button onClick={onClose} className="text-slate-400 hover:text-white cursor-pointer">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-5">
          <div>
            <h3 className="text-lg font-bold text-white mb-1 uppercase bg-[#111] px-2 py-1 rounded inline-block">{editingPart.name_pl}</h3>
            <p className="text-[10px] text-slate-500 uppercase tracking-widest">Wlasciwosci Detalu</p>
          </div>

          <div className="grid grid-cols-3 gap-2">
            <div className="bg-[#252526] border border-[#333] pt-1 pb-2 rounded-sm text-center font-mono">
              <span className="text-[8px] text-slate-500 block mb-1">SZEROKOSC</span>
              <span className="text-lg font-bold text-white">{(editingPart.dims_mm?.w || 0).toFixed(1)}</span>
            </div>
            <div className="bg-[#252526] border border-[#333] pt-1 pb-2 rounded-sm text-center font-mono">
              <span className="text-[8px] text-slate-500 block mb-1">WYSOKOSC</span>
              <span className="text-lg font-bold text-white">{(editingPart.dims_mm?.h || 0).toFixed(1)}</span>
            </div>
            <div className="bg-[#252526] border border-[#333] pt-1 pb-2 rounded-sm text-center font-mono">
              <span className="text-[8px] text-slate-500 block mb-1">GRUBOSC</span>
              <span className="text-lg font-bold text-white">{(editingPart.dims_mm?.t || 0).toFixed(1)}</span>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-[9px] text-slate-400 uppercase font-black block">Nadpisanie materialu:</label>
            <select
              value={editingPart.material_override_key || ""}
              onChange={(e) => updatePartProperty(editingPart.id, { material_override_key: e.target.value })}
              className="w-full bg-[#2d2d2d] border border-[#444] rounded-sm px-2 py-2 text-white outline-none focus:border-blue-500"
            >
              <option value="">-- Domyslny z modulu --</option>
              {allMaterials.map((m) => (
                <option key={m.id} value={m.name}>
                  {m.name} ({m.thickness}mm)
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-[9px] text-slate-400 uppercase font-black block">Sloje (Uslugienie):</label>
              <select
                value={editingPart.grain_direction || "none"}
                onChange={(e) => updatePartProperty(editingPart.id, { grain_direction: e.target.value })}
                className="w-full bg-[#2d2d2d] border border-[#444] rounded-sm px-2 py-2 text-white outline-none focus:border-blue-500 text-[11px]"
              >
                <option value="none">Brak (Jednolity)</option>
                <option value="vertical">Pionowo (Wzdluz H)</option>
                <option value="horizontal">Poziomo (Wzdluz W)</option>
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-[9px] text-slate-400 uppercase font-black block">Wykonczenie:</label>
              <div className="space-y-1">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={!!editingPart.veneer_active}
                    onChange={(e) => updatePartProperty(editingPart.id, { veneer_active: e.target.checked })}
                    className="w-3 h-3 rounded bg-canvas border-subtle text-brand"
                  />
                  <span className="text-[10px] text-slate-300 uppercase">Fornir</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={!!editingPart.lacquer_active}
                    onChange={(e) => updatePartProperty(editingPart.id, { lacquer_active: e.target.checked })}
                    className="w-3 h-3 rounded bg-canvas border-subtle text-brand"
                  />
                  <span className="text-[10px] text-slate-300 uppercase">Lakier</span>
                </label>
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-[9px] text-slate-400 uppercase font-black block">Oklejanie wg bokow (zaznacz aby obkleic):</label>
            <div className="grid grid-cols-4 gap-2">
              {["Gora", "Dol", "Lewo", "Prawo"].map((side) => {
                const sideMap = { Gora: "top", Dol: "bottom", Lewo: "left", Prawo: "right" } as any;
                const backSide = sideMap[side];
                const hasEdge = !!editingPart.edge_banding?.[backSide];

                return (
                  <label
                    key={side}
                    className={clsx(
                      "p-2 rounded-sm border cursor-pointer flex flex-col items-center gap-2 transition-colors",
                      hasEdge ? "bg-blue-900/40 border-blue-500" : "bg-[#252526] border-[#333] hover:border-[#555]"
                    )}
                  >
                    <span className="text-[9px] font-black uppercase text-slate-300">{side}</span>
                    <input
                      type="checkbox"
                      checked={hasEdge}
                      onChange={(e) => {
                        const newEdges = { ...(editingPart.edge_banding || {}) };
                        if (e.target.checked) newEdges[backSide] = "default_edge";
                        else delete newEdges[backSide];
                        updatePartProperty(editingPart.id, { edge_banding: newEdges });
                      }}
                      className="sr-only"
                    />
                    <div
                      className={clsx(
                        "w-4 h-4 rounded-full flex items-center justify-center transition-colors",
                        hasEdge ? "bg-blue-500" : "bg-[#111] border border-[#444]"
                      )}
                    >
                      {hasEdge && <div className="w-2 h-2 bg-white rounded-full"></div>}
                    </div>
                  </label>
                );
              })}
            </div>
          </div>

          <button
            onClick={onClose}
            className="w-full mt-4 bg-emerald-600 hover:bg-emerald-500 border border-emerald-900 shadow-xl shadow-emerald-900/20 py-3 rounded-sm font-black tracking-widest text-white transition-colors uppercase text-[10px] cursor-pointer"
          >
            Zapisz Wlasciwosci
          </button>
        </div>
      </div>
    </div>
  );
}
