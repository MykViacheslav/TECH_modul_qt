"use client";

import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Button, Card, StatCard } from "@/components/ui";
import {
  Hammer,
  Download,
  Search,
  Layers,
  Maximize2,
  Package,
  CheckCircle2,
  AlertCircle,
  Loader2
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { TechModulAPI, type ProductionSummary, type ProductionPart } from "@/services/api";
import { useSelectedProjectId } from "@/services/project-context";
import clsx from "clsx";

export default function ProductionPage() {
  const [projectId] = useSelectedProjectId(1);
  const [summary, setSummary] = useState<ProductionSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filterMaterial, setFilterMaterial] = useState<string>("all");

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await TechModulAPI.getProjectProductionSummary(projectId);
      setSummary(data);
    } catch (e) {
      console.error(e);
      setSummary(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [projectId]);

  const materials = useMemo(() => {
    if (!summary) return [];
    return Array.from(new Set(summary.parts.map(p => p.material)));
  }, [summary]);

  const filteredParts = useMemo(() => {
    if (!summary) return [];
    return summary.parts.filter(p => {
      const matchesSearch = p.name.toLowerCase().includes(search.toLowerCase()) ||
                           p.module_name.toLowerCase().includes(search.toLowerCase());
      const matchesMaterial = filterMaterial === "all" || p.material === filterMaterial;
      return matchesSearch && matchesMaterial;
    });
  }, [summary, search, filterMaterial]);

  if (loading) {
    return (
      <AppShell>
        <div className="flex flex-col items-center justify-center min-h-[60vh] text-slate-400">
          <Loader2 className="w-10 h-10 animate-spin mb-4" />
          <p className="text-sm font-medium">Analizowanie projektu i generowanie rozrysow...</p>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PageHeader
        eyebrow={`Technologia i Produkcja - ID ${projectId}`}
        title={<>Centrum <span className="text-brand-hover">produkcyjne</span></>}
        subtitle="Automatyczne rozrysy, zestawienia materiaowe i gotowe listy dla stolarni."
        actions={
          <>
            <Button
                variant="secondary"
                onClick={() => window.open(TechModulAPI.getProjectProductionExportUrl(projectId), "_blank")}
                disabled={!summary || summary.parts_count === 0}
            >
              <Download className="w-4 h-4" /> Eksportuj CSV
            </Button>
            <Button>
              <CheckCircle2 className="w-4 h-4" /> Zatwierdz do produkcji
            </Button>
          </>
        }
      />

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
            label="Wszystkie formatki"
            value={String(summary?.parts_count || 0)}
            icon={<Layers className="text-brand" />}
        />
        <StatCard
            label="Powierzchnia pyt"
            value={`${summary?.material_stats.reduce((acc, curr) => acc + curr.total_m2, 0).toFixed(2)} m2`}
            icon={<Maximize2 className="text-blue-400" />}
        />
         <StatCard
            label="Typy materiaow"
            value={String(summary?.material_stats.length || 0)}
            icon={<Package className="text-emerald-400" />}
        />
        <StatCard
            label="Status techniczny"
            value="Gotowy"
            tone="success"
            icon={<CheckCircle2 />}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Left Column: Material Inventory */}
        <div className="lg:col-span-1 space-y-6">
          <h3 className="eyebrow mb-4">Zapotrzebowanie pyt</h3>
          {summary?.material_stats.map((mat, i) => (
            <div key={i} className="bg-panel-raised rounded-2xl p-5 border border-subtle relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-24 h-24 bg-brand/5 rounded-full -mr-12 -mt-12 blur-2xl group-hover:bg-brand/10 transition-colors" />
              <div className="relative">
                <p className="text-xs font-bold text-brand-hover mb-1 uppercase tracking-wider">{mat.name}</p>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-bold tracking-tight">{mat.total_m2}</span>
                  <span className="text-sm text-slate-500">m2</span>
                </div>
                <div className="mt-4 flex items-center justify-between text-[11px] text-slate-400">
                  <span>Formatki: {mat.parts_count} szt.</span>
                  <span className="text-emerald-500 font-medium">Na stanie</span>
                </div>
              </div>
            </div>
          ))}
          {(!summary || summary.material_stats.length === 0) && (
             <div className="p-8 border border-dashed border-subtle rounded-3xl text-center">
                <AlertCircle className="w-8 h-8 text-slate-600 mx-auto mb-3" />
                <p className="text-xs text-slate-500">Brak danych materiaowych. Sprawdz konfiguracje moduow.</p>
             </div>
          )}
        </div>

        {/* Right Column: Detailed Cutting List */}
        <div className="lg:col-span-3">
          <Card className="!p-0 overflow-hidden">
            <div className="p-6 border-b border-subtle bg-panel-raised/30 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <h3 className="eyebrow">Lista czesci (Rozrysy)</h3>
              <div className="flex items-center gap-3">
                 <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <input
                      type="text"
                      placeholder="Szukaj formatki..."
                      className="bg-canvas-deep border border-subtle rounded-xl py-2 pl-9 pr-4 text-xs w-full sm:w-48 focus:outline-none focus:border-brand-ring transition-colors"
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                    />
                 </div>
                 <select
                    className="bg-canvas-deep border border-subtle rounded-xl py-2 px-3 text-xs focus:outline-none focus:border-brand-ring transition-colors"
                    value={filterMaterial}
                    onChange={(e) => setFilterMaterial(e.target.value)}
                 >
                    <option value="all">Wszystkie materiay</option>
                    {materials.map(m => <option key={m} value={m}>{m}</option>)}
                 </select>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="bg-panel-raised/50 text-slate-400 text-[11px] uppercase tracking-wider">
                    <th className="px-6 py-4 font-bold">Modu</th>
                    <th className="px-6 py-4 font-bold">Nazwa czesci</th>
                    <th className="px-6 py-4 font-bold text-center">Wymiary (mm)</th>
                    <th className="px-6 py-4 font-bold">Materia</th>
                    <th className="px-6 py-4 font-bold text-right">Powierzchnia</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-subtle">
                  {filteredParts.map((part, i) => (
                    <tr key={i} className="hover:bg-brand/5 transition-colors group">
                      <td className="px-6 py-4">
                        <span className="text-slate-400 text-xs block">#{part.module_id}</span>
                        <span className="font-medium">{part.module_name}</span>
                      </td>
                      <td className="px-6 py-4 font-medium text-slate-200">
                        {part.name}
                      </td>
                      <td className="px-6 py-4 text-center font-mono text-brand-hover tabular-nums">
                        {part.width}  {part.height}
                      </td>
                      <td className="px-6 py-4">
                         <span className="px-2 py-1 rounded bg-panel-raised text-[10px] border border-subtle text-slate-300">
                           {part.material}
                         </span>
                      </td>
                      <td className="px-6 py-4 text-right text-slate-400 tabular-nums">
                        {part.area_m2.toFixed(3)} m2
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filteredParts.length === 0 && (
                <div className="py-20 text-center text-slate-500">
                   <p>Nie znaleziono czesci speniajacych kryteria.</p>
                </div>
              )}
            </div>

            <div className="p-4 bg-panel-raised/30 border-t border-subtle flex items-center justify-between text-xs text-slate-500">
               <p>Wyswietlono {filteredParts.length} z {summary?.parts_count || 0} formatek</p>
               <div className="flex gap-1">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  <span>Wszystkie wymiary netto (bez naddatkow na oklejanie)</span>
               </div>
            </div>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}
