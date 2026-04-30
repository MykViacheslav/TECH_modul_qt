"use client";

import React, { useMemo } from "react";
import { X, ExternalLink, Download, FileCode, AlertCircle, Maximize2 } from "lucide-react";
import clsx from "clsx";
import { Button } from "./ui";

interface PartTechnicalViewerProps {
  name: string;
  width: number;
  height: number;
  thickness: number;
  cncData?: string;
  edges?: Record<string, string | null>;
  onClose: () => void;
}

interface Hole {
  x: number;
  y: number;
  diameter: number;
  depth: number | string;
  side: "front" | "back";
}

export default function PartTechnicalViewer({ name, width, height, thickness, cncData, edges, onClose }: PartTechnicalViewerProps) {
  const data = useMemo(() => {
    if (!cncData) return { holes: [] as Hole[], dx: width, dy: height };

    try {
      const parser = new DOMParser();
      const xmlDoc = parser.parseFromString(cncData, "text/xml");
      const program = xmlDoc.getElementsByTagName("program")[0];
      if (!program) return { holes: [] as Hole[], dx: width, dy: height };

      const dx = parseFloat(program.getAttribute("dx") || String(width));
      const dy = parseFloat(program.getAttribute("dy") || String(height));
      const result: Hole[] = [];

      const evaluate = (expr: string | null): number => {
        if (!expr) return 0;
        try {
          if (expr.includes("-")) {
            const [a, b] = expr.split("-").map(parseFloat);
            return a - b;
          }
          return parseFloat(expr);
        } catch { return 0; }
      };

      const tools: Record<string, number> = {};
      const toolElems = xmlDoc.getElementsByTagName("tool");
      for (let i = 0; i < toolElems.length; i++) {
        const t = toolElems[i];
        tools[t.getAttribute("name") || ""] = parseFloat(t.getAttribute("d") || "0");
      }

      // Bore Front (bf)
      const bfs = xmlDoc.getElementsByTagName("bf");
      for (let i = 0; i < bfs.length; i++) {
        const bf = bfs[i];
        result.push({
          x: evaluate(bf.getAttribute("x")),
          y: evaluate(bf.getAttribute("y")),
          diameter: tools[bf.getAttribute("name") || ""] || 5,
          depth: bf.getAttribute("dp") || 0,
          side: "front"
        });
      }

      // Bore Rear (br)
      const brs = xmlDoc.getElementsByTagName("br");
      for (let i = 0; i < brs.length; i++) {
        const br = brs[i];
        result.push({
          x: evaluate(br.getAttribute("x")),
          y: evaluate(br.getAttribute("y")),
          diameter: tools[br.getAttribute("name") || ""] || 5,
          depth: br.getAttribute("dp") || 0,
          side: "back"
        });
      }

      return { holes: result, dx, dy };
    } catch (e) {
      console.error("Error parsing CNC data:", e);
      return { holes: [], dx: width, dy: height };
    }
  }, [cncData, width, height]);

  const { holes, dx, dy } = data;
  const currentWidth = dx;
  const currentHeight = dy;

  const scale = Math.min(600 / currentWidth, 500 / currentHeight) * 0.9;
  const canvasWidth = currentWidth * scale;
  const canvasHeight = currentHeight * scale;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-md p-8 animate-in fade-in duration-300">
      <div className="bg-canvas-deep border border-white/10 rounded-[2.5rem] w-full max-w-5xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
        <div className="p-8 border-b border-white/5 flex items-center justify-between">
          <div className="flex items-center gap-4">
             <div className="w-12 h-12 rounded-2xl bg-brand/10 border border-brand/20 flex items-center justify-center">
                <FileCode className="w-6 h-6 text-brand" />
             </div>
             <div>
                <h3 className="text-xl font-bold text-white tracking-tight">{name}</h3>
                <p className="text-xs text-slate-500 uppercase font-black tracking-widest mt-1">Podglad Techniczny CNC - {currentWidth} x {currentHeight} x {thickness} mm</p>
             </div>
          </div>
          <button
            onClick={onClose}
            className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center text-slate-400 hover:bg-red-500/20 hover:text-red-400 transition-all"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="flex-1 overflow-auto p-12 flex items-center justify-center bg-[#080808]">
           <div className="relative" style={{ width: canvasWidth, height: canvasHeight }}>
              {/* Board Body */}
              <div
                className="absolute inset-0 border-2 border-brand-hover/20 bg-brand-soft shadow-[0_0_40px_rgba(59,130,246,0.05)] rounded-sm"
              />

              {/* Edgebanding Indicators */}
              {edges?.top && <div className="absolute top-0 left-0 right-0 h-1 bg-brand shadow-[0_0_10px_rgba(59,130,246,0.5)] z-10" title={`Okleina Gora: ${edges.top}`} />}
              {edges?.bottom && <div className="absolute bottom-0 left-0 right-0 h-1 bg-brand shadow-[0_0_10px_rgba(59,130,246,0.5)] z-10" title={`Okleina Do: ${edges.bottom}`} />}
              {edges?.left && <div className="absolute top-0 bottom-0 left-0 w-1 bg-brand shadow-[10px_0_10px_rgba(59,130,246,0.5)] z-10" title={`Okleina Lewa: ${edges.left}`} />}
              {edges?.right && <div className="absolute top-0 bottom-0 right-0 w-1 bg-brand shadow-[-10px_0_10px_rgba(59,130,246,0.5)] z-10" title={`Okleina Prawa: ${edges.right}`} />}

              {/* Grid */}
              <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'radial-gradient(#fff 0.5px, transparent 0.5px)', backgroundSize: '20px 20px' }} />

              {/* Axis Labels */}
              <div className="absolute -bottom-8 left-0 right-0 flex justify-between text-[10px] text-slate-500 font-mono"><span>0</span><span>X: {currentWidth} mm</span></div>
              <div className="absolute top-0 bottom-0 -left-14 flex flex-col justify-between text-[10px] text-slate-500 font-mono"><span>Y: {currentHeight}</span><span>0</span></div>

              {/* Holes */}
              {holes.map((h, i) => {
                const isFront = h.side === "front";
                return (
                  <div
                    key={i}
                    className={clsx(
                        "absolute rounded-full border flex items-center justify-center group cursor-help transition-all hover:scale-125 z-20",
                        isFront ? "border-orange-500/80 bg-orange-500/30" : "border-blue-500/80 bg-blue-500/30 border-dashed"
                    )}
                    style={{
                      left: h.x * scale,
                      bottom: h.y * scale,
                      width: h.diameter * scale,
                      height: h.diameter * scale,
                      transform: 'translate(-50%, 50%)' // Center on X,Y
                    }}
                  >
                     <div className={clsx("w-0.5 h-0.5 rounded-full", isFront ? "bg-orange-400" : "bg-blue-400")} />
                     <div className="absolute bottom-full mb-3 bg-black/95 text-[10px] text-white p-2.5 rounded-xl whitespace-nowrap opacity-0 group-hover:opacity-100 transition-all z-[100] border border-white/10 shadow-2xl scale-90 group-hover:scale-100">
                        <div className="font-black uppercase tracking-widest text-[8px] mb-1 text-slate-400">{isFront ? "Front Face" : "Rear Face"}</div>
                        <div className="flex items-center gap-3">
                           <span className="font-bold"> {h.diameter}mm</span>
                           <span className="text-slate-500">|</span>
                           <span className="font-bold">DP: {h.depth}mm</span>
                        </div>
                     </div>
                  </div>
                );
              })}
           </div>
        </div>

        <div className="p-8 bg-black/30 border-t border-white/5 flex items-center justify-between">
           <div className="flex items-center gap-8">
              <div className="flex flex-col gap-2">
                 <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-orange-500/40 border-2 border-orange-500" />
                    <span className="text-[10px] text-slate-300 uppercase font-black tracking-widest">Nawierty GORA (Front)</span>
                 </div>
                 <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-blue-500/40 border-2 border-blue-500 border-dashed" />
                    <span className="text-[10px] text-slate-300 uppercase font-black tracking-widest">Nawierty DO (Rear)</span>
                 </div>
              </div>
              <div className="w-px h-10 bg-white/10" />
              <div className="flex flex-col gap-2">
                 <div className="flex items-center gap-2">
                    <div className="w-4 h-1 bg-brand shadow-[0_0_8px_rgba(59,130,246,1)]" />
                    <span className="text-[10px] text-slate-300 uppercase font-black tracking-widest">Okleina (Edgeband)</span>
                 </div>
                 <div className="text-[9px] text-slate-500 uppercase font-bold">Wykryta oklejarka: 1-stronna</div>
              </div>

              {holes.some(h => h.side === 'back') && (
                 <div className="px-4 py-2 bg-red-500/10 border border-red-500/30 rounded-xl flex items-center gap-3 animate-pulse">
                    <AlertCircle className="w-4 h-4 text-red-400" />
                    <span className="text-[10px] text-red-200 uppercase font-black tracking-widest leading-none">Wymagany obrot formatki</span>
                 </div>
              )}
           </div>

           <div className="flex gap-4">
              <Button variant="ghost" size="sm" className="text-xs uppercase font-black tracking-widest gap-2">
                 <Download className="w-4 h-4" /> Nesting CSV
              </Button>
              <Button variant="primary" size="sm" className="text-xs uppercase font-black tracking-widest gap-3 shadow-brand-glow/20">
                 <Maximize2 className="w-4 h-4" /> Panel Sterowania CNC
              </Button>
           </div>
        </div>
      </div>
    </div>
  );
}
