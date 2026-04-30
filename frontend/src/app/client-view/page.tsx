"use client";

import { motion } from "framer-motion";
import { Eye, Maximize2, Printer, ArrowRight, Loader2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import clsx from "clsx";
import { TechModulAPI, type FinanceSummary, type MaterialRecord } from "@/services/api";
import { useSelectedProjectId } from "@/services/project-context";

type Color = "material_0" | "material_1" | "material_2";

type ColorOption = {
  id: Color;
  label: string;
  bg: string;
  border: string;
  pricePerM2: number;
};

const FALLBACK_COLORS: ColorOption[] = [
  { id: "material_0", label: "Bialy", bg: "bg-slate-50", border: "border-slate-300", pricePerM2: 22.5 },
  { id: "material_1", label: "Dab", bg: "bg-[#8B5E3C]", border: "border-[#6d4830]", pricePerM2: 45.0 },
  { id: "material_2", label: "Antracyt", bg: "bg-slate-800", border: "border-slate-900", pricePerM2: 39.9 },
];

function mapMaterialsToColors(materials: MaterialRecord[]): ColorOption[] {
  const top = (materials ?? []).slice(0, 3);
  if (top.length < 3) return FALLBACK_COLORS;
  return top.map((m, idx) => ({
    id: (`material_${idx}` as Color),
    label: m.name,
    bg: idx === 0 ? "bg-slate-50" : idx === 1 ? "bg-[#8B5E3C]" : "bg-slate-800",
    border: idx === 0 ? "border-slate-300" : idx === 1 ? "border-[#6d4830]" : "border-slate-900",
    pricePerM2: Number(m.price || 0),
  }));
}

export default function ClientView() {
  const [projectId] = useSelectedProjectId(1);
  const [summary, setSummary] = useState<FinanceSummary | null>(null);
  const [colors, setColors] = useState<ColorOption[]>(FALLBACK_COLORS);
  const [color, setColor] = useState<Color>("material_1");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [finance, materials] = await Promise.all([
          TechModulAPI.getProjectFinanceSummary(projectId),
          TechModulAPI.getMaterials(),
        ]);
        if (!active) return;
        setSummary(finance);
        const mapped = mapMaterialsToColors(materials);
        setColors(mapped);
        if (!mapped.some((c) => c.id === color)) {
          setColor(mapped[0].id);
        }
      } catch (e: any) {
        if (!active) return;
        setError(e?.message ?? "Blad pobierania podgladu klienta");
        setSummary(null);
        setColors(FALLBACK_COLORS);
      } finally {
        if (active) setLoading(false);
      }
    };
    load();
    return () => {
      active = false;
    };
  }, [projectId]);

  const current = useMemo(() => colors.find((c) => c.id === color) ?? colors[0], [colors, color]);
  const baseGross = Number(summary?.total_gross || 0);
  const variantDelta = Number(current?.pricePerM2 || 0) * 3;
  const price = Math.max(0, baseGross + variantDelta);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <header className="bg-white border-b border-slate-200 shadow-sm">
        <div className="mx-auto max-w-7xl px-8 py-5 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold text-lg shadow-md">T</div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-400">Twoj projekt - Premium</p>
              <h1 className="text-lg font-bold text-slate-900">Prezentacja oferty #{projectId}</h1>
            </div>
          </div>
          <button className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-200 text-sm font-medium text-slate-600 hover:text-blue-600 hover:border-blue-400 transition-colors">
            <Printer className="w-4 h-4" /> Drukuj oferte
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-8 py-10">
        {loading ? (
          <div className="mb-6 text-sm text-slate-500 flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" /> Ladowanie danych oferty...
          </div>
        ) : null}

        {error ? (
          <div className="mb-6 text-sm text-red-600">{error}</div>
        ) : null}

        <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-8">
          <div className="bg-white rounded-3xl shadow-xl border border-slate-200 relative overflow-hidden min-h-[520px]">
            <div className="absolute top-5 left-5 flex gap-2 z-10">
              <span className="px-3 py-1 rounded-full bg-slate-900 text-white text-xs font-semibold shadow">Widok 2D</span>
              <span className="px-3 py-1 rounded-full bg-blue-600 text-white text-xs font-semibold shadow">Skala 1:1</span>
            </div>

            <div className="h-full min-h-[520px] flex items-center justify-center p-12">
              <motion.div
                key={color}
                initial={{ opacity: 0, scale: 0.96 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.4 }}
                className={clsx(
                  "w-full max-w-lg aspect-[4/3] rounded-2xl shadow-2xl border-b-8 flex items-center justify-center relative",
                  current.bg,
                  current.border
                )}
              >
                <p className={clsx("text-lg font-semibold uppercase tracking-[0.2em]", current.bg === "bg-slate-50" ? "text-slate-400" : "text-white/70")}>Front: {current.label}</p>
              </motion.div>
            </div>

            <div className="absolute bottom-5 right-5 flex gap-2">
              <button className="w-10 h-10 rounded-full bg-white shadow-lg border border-slate-200 flex items-center justify-center hover:scale-105 transition-transform">
                <Maximize2 className="w-4 h-4 text-slate-600" />
              </button>
              <button className="w-10 h-10 rounded-full bg-blue-600 text-white shadow-lg flex items-center justify-center hover:scale-105 transition-transform">
                <Eye className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-white rounded-3xl shadow-xl border border-slate-100 p-7">
              <h3 className="text-[11px] font-semibold text-slate-400 uppercase tracking-[0.2em] mb-4">Wybierz wariant wykonczenia</h3>
              <div className="grid grid-cols-3 gap-3">
                {colors.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => setColor(c.id)}
                    className={clsx(
                      "aspect-square rounded-xl border-2 transition-all",
                      c.bg,
                      color === c.id ? "border-blue-500 scale-105 shadow-lg" : "border-slate-200 hover:border-slate-400"
                    )}
                    title={c.label}
                  />
                ))}
              </div>
              <p className="mt-3 text-xs text-center text-slate-500">{current.label}</p>
            </div>

            <div className="bg-white rounded-3xl shadow-xl border border-slate-100 p-7">
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-400 mb-3">Calkowita wartosc inwestycji</p>
              <p className="text-4xl font-bold tracking-tight text-slate-900">
                {price.toLocaleString("pl-PL", { maximumFractionDigits: 0 })}
                <span className="text-lg font-normal text-slate-500 ml-2">PLN</span>
              </p>
              <p className="mt-2 text-xs font-semibold text-emerald-600">Gwarancja ceny do wygasniecia oferty</p>
              <button className="mt-6 w-full py-3.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-semibold text-sm shadow-lg flex items-center justify-center gap-2 transition-colors">
                Zloz zamowienie <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
