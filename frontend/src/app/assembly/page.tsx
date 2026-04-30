"use client";

import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import AgentPanel from "@/components/AgentPanel";
import OperationPreviewList from "@/components/OperationPreviewList";
import { Button, Card, StatCard } from "@/components/ui";
import {
  Plus,
  Trash2,
  Copy,
  GripVertical,
  Loader2,
  AlertCircle,
  RefreshCw,
  Database,
  Check,
  ArrowRight,
} from "lucide-react";
import { useEffect, useState, useCallback, useMemo } from "react";
import { TechModulAPI, type AssemblySummary, type OperationAction, type ProjectModule } from "@/services/api";
import { applyBulkModuleOperation, previewBulkModuleOperation } from "@/services/operations";
import { mapOperationChangesToPreviewRows } from "@/services/operation-contract";
import { useSelectedProjectId } from "@/services/project-context";

type BulkAction = OperationAction;

type BulkPreviewState = {
  action: BulkAction;
  params: Record<string, unknown>;
  moduleIds: string[];
  warnings: string[];
  changes: Array<{
    path: string;
    before: unknown;
    after: unknown;
    label: string;
    moduleName?: string;
  }>;
};

export default function AssemblyPage() {
  const [projectId] = useSelectedProjectId(1);
  const [modules, setModules] = useState<ProjectModule[] | null>(null);
  const [summary, setSummary] = useState<AssemblySummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [bulkAction, setBulkAction] = useState<BulkAction>("module.set_depth");
  const [valueMm, setValueMm] = useState<string>("560");
  const [shelfDelta, setShelfDelta] = useState<string>("1");
  const [materialKey, setMaterialKey] = useState<string>("PB18");
  const [materialGroup, setMaterialGroup] = useState<string>("carcass");

  const [bulkPreview, setBulkPreview] = useState<BulkPreviewState | null>(null);
  const [bulkBusy, setBulkBusy] = useState<"preview" | "apply" | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [data, summaryData] = await Promise.all([
        TechModulAPI.getProjectModules(projectId),
        TechModulAPI.getProjectAssemblySummary(projectId),
      ]);
      setModules(data);
      setSummary(summaryData);
      setSelectedIds((prev) => prev.filter((id) => data.some((m) => String(m.id) === id)));
    } catch (e: any) {
      setError(e?.message ?? "Bad poaczenia z API");
      setModules(null);
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    load();
  }, [load]);

  const list: ProjectModule[] = modules ?? [];
  const selectedCount = selectedIds.length;

  const toggleSelected = (id: string) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const selectAll = () => setSelectedIds(list.map((m) => String(m.id)));
  const clearSelection = () => setSelectedIds([]);

  const bulkParams = useMemo<Record<string, unknown>>(() => {
    if (bulkAction === "module.set_depth") return { depth_mm: Number(valueMm || 0) };
    if (bulkAction === "module.set_width") return { width_mm: Number(valueMm || 0) };
    if (bulkAction === "module.set_height") return { height_mm: Number(valueMm || 0) };
    if (bulkAction === "module.add_shelves") return { delta_count: Number(shelfDelta || 0) };
    return { material_key: materialKey, part_group: materialGroup };
  }, [bulkAction, valueMm, shelfDelta, materialKey, materialGroup]);

  const buildBulkPreview = async () => {
    if (selectedIds.length === 0) {
      setError("Wybierz co najmniej jeden modu.");
      return;
    }
    setBulkBusy("preview");
    setError(null);

    try {
      const result = await previewBulkModuleOperation({
        action: bulkAction,
        moduleIds: selectedIds,
        params: bulkParams,
        source: "assembly_page",
      });

      if (!result.can_apply) {
        const msg = result.errors[0]?.message ?? "Podglad operacji zwroci bedy";
        throw new Error(msg);
      }

      setBulkPreview({
        action: bulkAction,
        params: bulkParams,
        moduleIds: selectedIds,
        warnings: result.warnings,
        changes: result.changes.map((ch) => ({
          path: ch.path,
          label: ch.label,
          before: ch.before,
          after: ch.after,
          moduleName: ch.target_ref?.name,
        })),
      });
    } catch (e: any) {
      setError(e?.message ?? "Bad podgladu operacji");
      setBulkPreview(null);
    } finally {
      setBulkBusy(null);
    }
  };

  const applyBulk = async () => {
    if (!bulkPreview) return;
    setBulkBusy("apply");
    setError(null);

    try {
      const result = await applyBulkModuleOperation({
        action: bulkPreview.action,
        moduleIds: bulkPreview.moduleIds,
        params: bulkPreview.params,
        source: "assembly_page",
      });

      if (result.appliedCount <= 0) {
        throw new Error("Brak zastosowanych zmian");
      }

      await load();
      setBulkPreview(null);
    } catch (e: any) {
      setError(e?.message ?? "Bad zapisu operacji");
    } finally {
      setBulkBusy(null);
    }
  };

  return (
    <AppShell>
      <PageHeader
        eyebrow={`Projekt #${projectId} - Montaz i kompletacja`}
        title={
          <>
            Zarzadzanie <span className="text-brand-hover">kompletem</span>
          </>
        }
        subtitle="Operacje hurtowe dziaaja przez backend: podglad -> potwierdzenie -> apply -> odswiezenie."
        actions={
          <>
            <Button variant="ghost" onClick={load} disabled={loading || bulkBusy !== null}>
              <RefreshCw className={loading ? "w-4 h-4 animate-spin" : "w-4 h-4"} />
              Odswiez
            </Button>
            <Button>
              <Plus className="w-4 h-4" /> Dodaj modu
            </Button>
          </>
        }
      />

      {error ? (
        <div className="mb-4 flex items-start gap-3 p-4 rounded-card border border-red-500/30 bg-red-500/10 text-sm text-red-200">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Wystapi problem</p>
            <p className="mt-1 text-red-300/80">{error}</p>
          </div>
        </div>
      ) : null}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          {loading && !modules ? (
            <Card className="flex items-center justify-center py-16 text-slate-500">
              <Loader2 className="w-5 h-5 animate-spin mr-2" />
              adowanie moduow z bazy...
            </Card>
          ) : null}

          {!loading && modules && modules.length === 0 ? (
            <Card className="py-16 text-center">
              <Database className="w-8 h-8 text-slate-600 mx-auto mb-3" />
              <p className="text-sm text-slate-400">Brak moduow w tym projekcie.</p>
            </Card>
          ) : null}

          <div className="flex gap-2 mb-3">
            <Button variant="secondary" onClick={selectAll} disabled={list.length === 0}>Zaznacz wszystko</Button>
            <Button variant="secondary" onClick={clearSelection} disabled={selectedCount === 0}>Wyczysc zaznaczenie</Button>
          </div>

          <div className="space-y-3">
            {list.map((m) => {
              const isSelected = selectedIds.includes(String(m.id));
              return (
                <Card
                  key={m.id}
                  className={`flex items-center justify-between group transition-colors ${isSelected ? "border-brand-ring" : "hover:border-brand-ring"}`}
                >
                  <div className="flex items-center gap-4 min-w-0">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleSelected(String(m.id))}
                      className="accent-brand w-4 h-4"
                    />
                    <button className="text-slate-600 hover:text-slate-300 cursor-grab shrink-0">
                      <GripVertical className="w-5 h-5" />
                    </button>
                    <div className="w-12 h-12 rounded-lg bg-panel-raised border border-subtle flex items-center justify-center font-bold text-xs text-brand-hover shrink-0">
                      #{m.id}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold truncate">{m.name}</p>
                      <p className="text-xs text-slate-500 mt-0.5 font-mono">
                        {m.width}  {m.height}  {m.depth} mm
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button className="p-2 rounded-lg hover:bg-white/5 text-slate-400 hover:text-white">
                      <Copy className="w-4 h-4" />
                    </button>
                    <button className="p-2 rounded-lg hover:bg-red-500/10 text-slate-400 hover:text-red-400">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </Card>
              );
            })}
          </div>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <StatCard label="Moduow" value={summary ? summary.modules_count : modules ? modules.length : "-"} tone="brand" />
            <StatCard label="Wybrane" value={selectedCount} tone="success" />
            <StatCard
              label="Objetosc aczna"
              value={summary ? `${summary.total_volume_l} L` : "-"}
            />
            <StatCard
              label="Sr. gebokosc"
              value={summary ? `${Math.round(summary.avg_depth_mm)} mm` : "-"}
            />
          </div>

          <Card>
            <h3 className="eyebrow mb-3">Operacja hurtowa</h3>
            <label className="text-xs text-slate-500">Akcja</label>
            <select
              value={bulkAction}
              onChange={(e) => setBulkAction(e.target.value as BulkAction)}
              className="input-base mt-1 mb-3"
            >
              <option value="module.set_depth">Ustaw gebokosc</option>
              <option value="module.set_width">Ustaw szerokosc</option>
              <option value="module.set_height">Ustaw wysokosc</option>
              <option value="module.add_shelves">Dodaj poki (delta)</option>
              <option value="module.change_material">Zmien materia</option>
            </select>

            {(bulkAction === "module.set_depth" || bulkAction === "module.set_width" || bulkAction === "module.set_height") && (
              <>
                <label className="text-xs text-slate-500">Wartosc (mm)</label>
                <input
                  className="input-base mt-1"
                  type="number"
                  value={valueMm}
                  onChange={(e) => setValueMm(e.target.value)}
                />
              </>
            )}

            {bulkAction === "module.add_shelves" && (
              <>
                <label className="text-xs text-slate-500">Delta poek</label>
                <input
                  className="input-base mt-1"
                  type="number"
                  value={shelfDelta}
                  onChange={(e) => setShelfDelta(e.target.value)}
                />
              </>
            )}

            {bulkAction === "module.change_material" && (
              <>
                <label className="text-xs text-slate-500">Material key</label>
                <input
                  className="input-base mt-1 mb-2"
                  value={materialKey}
                  onChange={(e) => setMaterialKey(e.target.value)}
                />
                <label className="text-xs text-slate-500">Part group</label>
                <input
                  className="input-base mt-1"
                  value={materialGroup}
                  onChange={(e) => setMaterialGroup(e.target.value)}
                />
              </>
            )}

            <div className="flex gap-2 mt-3">
              <Button className="flex-1" onClick={buildBulkPreview} disabled={bulkBusy !== null || selectedCount === 0}>
                {bulkBusy === "preview" ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />} Podglad
              </Button>
              <Button className="flex-1" onClick={applyBulk} disabled={!bulkPreview || bulkBusy !== null}>
                {bulkBusy === "apply" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />} Zastosuj
              </Button>
            </div>
          </Card>

          {bulkPreview && (
            <Card>
              <OperationPreviewList
                title="Podglad zmian"
                warnings={bulkPreview.warnings}
                maxHeightClassName="max-h-[180px]"
                rows={mapOperationChangesToPreviewRows(
                  bulkPreview.changes.map((ch) => ({
                    path: ch.path,
                    label: ch.label,
                    before: ch.before,
                    after: ch.after,
                    target_ref: {
                      type: "module",
                      id: "",
                      name: ch.moduleName ?? "Modul",
                    },
                  })),
                  { fallbackName: "Modul" }
                )}
              />
            </Card>
          )}

          <AgentPanel
            onApplied={load}
            placeholder='Np. "zwieksz gebokosc o 50"'
          />
        </div>
      </div>
    </AppShell>
  );
}
