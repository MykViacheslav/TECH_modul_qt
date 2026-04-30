"use client";

import AppShell from "@/components/AppShell";
import { Button, Card, StatCard } from "@/components/ui";
import dynamic from "next/dynamic";
import { Box, Save, RotateCcw, ArrowRight, Check, Loader2, AlertCircle, Copy, Zap, Layers, Settings2, Maximize2, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState, useRef } from "react";
import clsx from "clsx";
import { TechModulAPI, type OperationAction, type ProjectModule } from "@/services/api";
import { applyModuleOperation, previewModuleOperation } from "@/services/operations";
import { getPrimaryOperationMessage, mapOperationChangesToPreviewRows } from "@/services/operation-contract";
import { useSelectedProjectId } from "@/services/project-context";

const Module3DViewer = dynamic(() => import("@/components/Module3DViewer"), {
  ssr: false,
});
const ConfigurationValuationTab = dynamic(
  () => import("@/components/configuration/ConfigurationValuationTab"),
  { ssr: false }
);
const ConfigurationProductionTab = dynamic(
  () => import("@/components/configuration/ConfigurationProductionTab"),
  { ssr: false }
);
const ConfigurationPartInspector = dynamic(
  () => import("@/components/configuration/ConfigurationPartInspector"),
  { ssr: false }
);
const MaterialPicker = dynamic(() => import("@/components/MaterialPicker"), {
  ssr: false,
});

type DimensionKey = "width" | "height" | "depth";

type PreviewState = {
  action: OperationAction;
  moduleId: string;
  moduleName: string;
  before: number;
  after: number;
  unit: string;
};

function actionForDimension(key: DimensionKey): OperationAction {
  if (key === "width") return "module.set_width";
  if (key === "height") return "module.set_height";
  return "module.set_depth";
}

function paramsForDimension(key: DimensionKey, value: number): Record<string, unknown> {
  if (key === "width") return { width_mm: value };
  if (key === "height") return { height_mm: value };
  return { depth_mm: value };
}

export default function ConfigurationPage() {
  const [projectId] = useSelectedProjectId(1);
  const [modules, setModules] = useState<ProjectModule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sceneMode, setSceneMode] = useState(false);
  const [obstacles, setObstacles] = useState<any[]>([]);

  const [selectedId, setSelectedId] = useState<string>("");
  const hasAppliedRouteSelection = useRef(false);
  const [requestedModuleId, setRequestedModuleId] = useState<string>("");
  const [valuation, setValuation] = useState<any>(null);

  const lastOpTime = useRef(0);
  const [activeTab, setActiveTab] = useState<"main" | "options" | "fittings" | "settings" | "cam">("main");
  const [w, setW] = useState(600);
  const [h, setH] = useState(720);
  const [d, setD] = useState(560);

  const [pendingPreview, setPendingPreview] = useState<PreviewState | null>(null);
  const [busy, setBusy] = useState<"preview" | "apply" | null>(null);
  const [allMaterials, setAllMaterials] = useState<any[]>([]);
  const [highlightedPartId, setHighlightedPartId] = useState<string | null>(null);
  const [productionSummary, setProductionSummary] = useState<any>(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickerGroup, setPickerGroup] = useState<string>("");

  const selectedModule = useMemo(
    () => modules.find((m) => String(m.id) === selectedId) ?? null,
    [modules, selectedId]
  );

  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    setRequestedModuleId(String(params.get("module_id") || "").trim());
  }, []);

  const loadProductionSummary = useCallback(async () => {
    try {
      const res = await fetch(`http://localhost:8000/api/production/project/${projectId}/summary`);
      if (res.ok) {
        setProductionSummary(await res.json());
      }
    } catch (e) {
      console.error(e);
    }
  }, [projectId]);

  // Fetch valuation when module changes or is modified
  useEffect(() => {
    if (selectedModule?.id) {
       TechModulAPI.getModuleValuation(selectedModule.id)
         .then(setValuation)
         .catch(console.error);
    } else {
       setValuation(null);
    }
  }, [selectedModule?.id]);

  useEffect(() => {
     if (selectedModule?.id && !busy && lastOpTime.current > 0) {
        TechModulAPI.getModuleValuation(selectedModule.id)
          .then(setValuation);
     }
  }, [busy]);

  useEffect(() => {
    loadProductionSummary();
  }, [activeTab, loadProductionSummary]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [data, mats, obs] = await Promise.all([
        TechModulAPI.getProjectModules(projectId),
        TechModulAPI.getMaterials(),
        TechModulAPI.getProjectObstacles(projectId)
      ]);
      setModules(data);
      setAllMaterials(mats);
      setObstacles(obs || []);
      if (!hasAppliedRouteSelection.current && requestedModuleId) {
        const exists = data.some((module) => String(module.id) === requestedModuleId);
        if (exists) {
          setSelectedId(requestedModuleId);
          hasAppliedRouteSelection.current = true;
        }
      }
      if (!selectedId && data.length > 0) {
        const requestedExists = requestedModuleId
          ? data.some((module) => String(module.id) === requestedModuleId)
          : false;
        if (!requestedExists) {
          setSelectedId(String(data[0].id));
        }
      }
    } catch (e: any) {
      setError(e?.message ?? "BL,A...d poL,A...czenia z API");
      setModules([]);
    } finally {
      setLoading(false);
    }
  }, [projectId, requestedModuleId, selectedId]);

  useEffect(() => {
    load();
  }, [load]);


  useEffect(() => {
    if (!selectedModule) return;
    setW(selectedModule.width);
    setH(selectedModule.height);
    setD(selectedModule.depth);
    setPendingPreview(null);
  }, [selectedModule?.id, selectedModule?.width, selectedModule?.height, selectedModule?.depth]);

  const reset = () => {
    if (!selectedModule) return;
    setW(selectedModule.width);
    setH(selectedModule.height);
    setD(selectedModule.depth);
    setPendingPreview(null);
  };

  const carcassMaterial = useMemo(() => {
    if (!selectedModule || !allMaterials) return null;
    const matKey = selectedModule.materials?.carcass;
    return allMaterials.find(m => m.name === matKey || m.id === selectedModule.material_id) || null;
  }, [selectedModule, allMaterials]);

  const hardwareMaterials = useMemo(() => {
    return allMaterials.filter(m => m.category === "hardware");
  }, [allMaterials]);

  const setPartMaterial = async (group: string, materialId: number) => {
    if (!selectedModule) return;
    setBusy("apply");
    setError(null);
    try {
      const result = await TechModulAPI.applyModuleOperation({
        action: "module.change_material",
        target: { id: String(selectedModule.id) },
        params: {
          material_key: String(materialId),
          part_group: group
        },
        source: "configuration_page"
      });
      if (result.status !== "ok") throw new Error(`BL,A...d zmiany materiaL,u dla: ${group}`);
      await load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  };

  const setPartEdgeband = async (group: string, edgebandId: number) => {
    if (!selectedModule) return;
    setBusy("apply");
    setError(null);
    try {
      const result = await TechModulAPI.applyModuleOperation({
        action: "module.change_edgeband",
        target: { id: String(selectedModule.id) },
        params: {
          edgeband_key: String(edgebandId),
          part_group: group
        },
        source: "configuration_page"
      });
      if (result.status !== "ok") throw new Error(`BL,A...d zmiany okleiny dla: ${group}`);
      await load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  };

  const [editingPart, setEditingPart] = useState<any | null>(null);


  const applyScheme = async (schemeKey: string) => {
    if (!selectedModule) return;
    setBusy("apply");
    setError(null);
    try {
      const result = await TechModulAPI.applyModuleOperation({
        action: "module.apply_scheme",
        target: { id: String(selectedModule.id) },
        params: { scheme_key: schemeKey },
        source: "configuration_page"
      });
      if (result.status !== "ok") throw new Error(`BL,A...d nakL,adania schematu: ${schemeKey}`);
      await load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  };

  const applyMaterialToAll = async (group: string, materialId: number) => {
    if (!selectedModule || !modules.length) return;
    setBusy("apply");
    setError(null);
    try {
       const moduleIds = modules.map(m => String(m.id));
       const result = await TechModulAPI.applyBulkModuleOperation({
          action: "module.change_material",
          module_ids: moduleIds,
          params: { material_key: String(materialId), part_group: group },
          source: "configuration_page_bulk"
       });
       if (result.status !== "ok") throw new Error("BL,A...d podczas operacji hurtowej");
       await load();
    } catch (e: any) {
        setError(e.message);
    } finally {
        setBusy(null);
    }
  };

  const updatePartProperty = async (partId: string, properties: any) => {
    if (!selectedModule) return;
    setBusy("apply");
    setError(null);
    try {
      const result = await TechModulAPI.applyModuleOperation({
        action: "module.update_part" as any,
        target: { id: String(selectedModule.id) },
        params: { part_id: partId, properties },
        source: "configuration_page"
      });
      if (result.status !== "ok") throw new Error(`BL,A...d aktualizacji czATMLci: ${partId}`);
      await load();
      if (editingPart && editingPart.id === partId) {
         setEditingPart(null); // Zamykamy inspektor LLeby pobraA LwieLLe dane przy ponownym klikniATMciu
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  };

  const updateProperty = async (key: string, value: any) => {
    if (!selectedModule) return;
    setBusy("apply");
    setError(null);
    try {
      const result = await TechModulAPI.applyModuleOperation({
        action: "module.update_properties",
        target: { id: String(selectedModule.id) },
        params: { [key]: value },
        source: "configuration_page"
      });
      if (result.status !== "ok") throw new Error(`BL,A...d aktualizacji: ${key}`);
      await load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  };

  const buildPreview = async (key: DimensionKey) => {
    if (!selectedModule) return;

    const before = key === "width" ? selectedModule.width : key === "height" ? selectedModule.height : selectedModule.depth;
    const after = key === "width" ? w : key === "height" ? h : d;

    if (before === after) {
      setError("Brak zmian do podglA...du.");
      return;
    }

    setBusy("preview");
    setError(null);
    try {
      const action = actionForDimension(key);
      const result = await previewModuleOperation({
        action,
        target: { id: String(selectedModule.id) },
        params: paramsForDimension(key, after),
        source: "configuration_page",
      });

      if (result.status !== "ok" || !result.can_apply) {
        throw new Error(getPrimaryOperationMessage(result, "PodglA...d operacji jest niedostATMpny"));
      }

      setPendingPreview({
        action,
        moduleId: String(selectedModule.id),
        moduleName: selectedModule.name,
        before,
        after,
        unit: "mm",
      });
    } catch (e: any) {
      setError(e?.message ?? "BL,A...d podglA...du");
      setPendingPreview(null);
    } finally {
      setBusy(null);
    }
  };

  const applyPreview = async () => {
    if (!pendingPreview || !selectedModule) return;
    setBusy("apply");
    setError(null);
    try {
      const key: DimensionKey = pendingPreview.action.includes("width")
        ? "width"
        : pendingPreview.action.includes("height")
        ? "height"
        : "depth";

      const result = await applyModuleOperation({
        action: pendingPreview.action,
        target: { id: pendingPreview.moduleId },
        params: paramsForDimension(key, pendingPreview.after),
        source: "configuration_page",
      });

      if (result.status !== "ok") {
        throw new Error(getPrimaryOperationMessage(result, "Zastosowanie operacji nie powiodL,o siATM"));
      }

      await load();
      setPendingPreview(null);
    } catch (e: any) {
      setError(e?.message ?? "BL,A...d zapisu");
    } finally {
      setBusy(null);
    }
  };

  const DimensionInput = ({
    label,
    value,
    setValue,
    onPreview,
  }: {
    label: string;
    value: number;
    setValue: (v: number) => void;
    onPreview: () => void;
  }) => (
    <div className="flex flex-col gap-1.5">
      <label className="text-[10px] text-slate-500 uppercase font-black tracking-widest">{label}</label>
      <div className="relative group">
        <input
          type="number"
          value={value}
          onChange={(e) => setValue(parseInt(e.target.value, 10) || 0)}
          className="w-full bg-canvas-deep border border-subtle rounded-lg px-3 py-2 text-sm font-bold tabular-nums focus:border-brand-hover focus:ring-1 focus:ring-brand-hover/30 outline-none transition-all"
        />
        <div className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-slate-600 font-bold group-focus-within:text-brand-hover">mm</div>
      </div>
      <Button
        variant="ghost"
        className="h-7 text-[10px] opacity-40 hover:opacity-100"
        onClick={onPreview}
        disabled={busy !== null || !selectedModule}
      >
        {busy === "preview" ? <Loader2 className="w-3 h-3 animate-spin" /> : "PodglA...d"}
      </Button>
    </div>
  );

  const MaterialSelector = ({
    label,
    group,
    currentMat,
    currentEdg
  }: {
    label: string,
    group: string,
    currentMat?: string,
    currentEdg?: string
  }) => {
    const selectedMatId = selectedModule?.materials?.[group];
    const selectedEdgId = selectedModule?.edgebands?.[group];

    // Znajdujemy peL,ne obiekty materiaL,Aw dla podglA...du
    const matObj = allMaterials.find(m => String(m.id) === String(selectedMatId) || m.name === selectedMatId);
    const edgObj = allMaterials.find(m => String(m.id) === String(selectedEdgId) || m.name === selectedEdgId);

    return (
      <div className="bg-panel-raised/30 border border-subtle rounded-xl p-3 flex flex-col gap-3 shadow-sm hover:shadow-md transition-shadow group/card">
        <div className="flex items-center justify-between">
          <label className="text-[10px] text-slate-400 uppercase font-black tracking-widest flex items-center gap-2">
            <Layers className="w-3 h-3 text-brand" />
            {label}
          </label>
        </div>

        <div className="grid grid-cols-1 gap-3">
          {/* PL,yta / Material */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-end">
              <label className="text-[9px] text-slate-500 uppercase font-bold">GL,Awna PL,yta</label>
              <div className="text-[9px] text-slate-400 font-mono">{matObj?.thickness ? `${matObj.thickness}mm` : ''}</div>
            </div>

            <div className="flex gap-2">
              {/* Material Preview & Trigger Button */}
              <button
                onClick={() => { setPickerGroup(group); setPickerOpen(true); }}
                className="flex-1 flex gap-3 p-2 bg-canvas-deep border border-subtle rounded-lg text-left hover:border-brand/40 transition-colors group/trigger"
              >
                <div
                  className="w-10 h-10 rounded-md border border-white/5 bg-panel-solid flex-shrink-0 flex items-center justify-center overflow-hidden shadow-inner"
                  style={matObj?.color_hex ? { backgroundColor: matObj.color_hex } : {}}
                >
                  {matObj?.texture_url ? (
                    <img src={matObj.texture_url} alt="" className="w-full h-full object-cover" />
                  ) : !matObj?.color_hex && (
                    <Box className="w-5 h-5 text-slate-700" />
                  )}
                </div>
                <div className="flex flex-col min-w-0">
                   <span className="text-[11px] font-bold text-slate-200 truncate group-hover/trigger:text-brand transition-colors">
                     {matObj?.name || 'Wybierz materia...'}
                   </span>
                   <span className="text-[9px] text-slate-500 font-mono uppercase truncate">
                     {matObj?.material_code || 'Brak wyboru'}
                   </span>
                </div>
              </button>

              <button
                 className="p-1 w-10 h-14 rounded-lg bg-canvas-deep border border-subtle text-slate-500 hover:text-brand-hover hover:border-brand-hover transition-all flex items-center justify-center group/btn"
                 title="Ustaw dla wszystkich moduL,Aw"
                 onClick={() => {
                    if (selectedMatId) {
                       const mat = allMaterials.find(m => String(m.id) === String(selectedMatId) || m.name === selectedMatId);
                       if (mat) applyMaterialToAll(group, mat.id);
                    }
                 }}
              >
                 <Copy className="w-4 h-4 group-hover/btn:scale-110 transition-transform" />
              </button>
            </div>
          </div>

          {/* Okleina / Edgeband */}
          <div className="space-y-1.5">
            <label className="text-[9px] text-slate-500 uppercase font-bold block">ObrzeLLe (Okleina)</label>
            <div className="flex gap-2">
              <div
                className="w-8 h-10 rounded-sm border-l-4 border-subtle bg-canvas-deep flex-shrink-0 flex items-center justify-center overflow-hidden"
                style={edgObj?.color_hex ? { borderLeftColor: edgObj.color_hex } : {}}
              >
                 <div className="w-1 h-6 bg-slate-800/30 rounded-full" />
              </div>
              <select
                value={selectedEdgId || ""}
                onChange={(e) => setPartEdgeband(group, parseInt(e.target.value, 10))}
                className="input-base text-[11px] h-10 flex-1 bg-[#1a1a1c] border-[#333]"
                disabled={loading || busy !== null}
              >
                <option value="">Auto (Dopasowana)</option>
                {allMaterials.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Finishing controls */}
        <div className="flex items-center justify-between mt-1 pt-2 border-t border-subtle/30">
          <div className="flex gap-3">
             <label className="flex items-center gap-1.5 cursor-pointer group">
                <input
                  type="checkbox"
                  checked={!!selectedModule?.materials_finish?.[`${group}_lacquer`]}
                  onChange={(e) => updateProperty(`finish_${group}_lacquer`, e.target.checked)}
                  className="w-3.5 h-3.5 rounded border-subtle bg-canvas text-brand-hover focus:ring-brand-hover/30"
                />
                <span className="text-[9px] text-slate-400 uppercase font-black group-hover:text-slate-200 transition-colors">Lakier</span>
             </label>
             <label className="flex items-center gap-1.5 cursor-pointer group">
                <input
                  type="checkbox"
                  checked={!!selectedModule?.materials_finish?.[`${group}_veneer`]}
                  onChange={(e) => updateProperty(`finish_${group}_veneer`, e.target.checked)}
                  className="w-3.5 h-3.5 rounded border-subtle bg-canvas text-brand-hover focus:ring-brand-hover/30"
                />
                <span className="text-[9px] text-slate-400 uppercase font-black group-hover:text-slate-200 transition-colors">Fornir</span>
             </label>
          </div>
        </div>
      </div>
    );
  };


  return (
    <AppShell>
      <div className="flex flex-col h-full w-full bg-transparent text-slate-200 overflow-hidden text-[11px] select-none">
        {/* CAD TOP TOOLBAR */}
        <div className="h-10 shrink-0 bg-[#2d2d2d] border-b border-[#111] flex items-center justify-between px-4 shadow-md z-10 relative">
           <div className="flex items-center gap-4">
              <span className="font-bold text-slate-300 tracking-wider">MODUL / SCENA</span>
              <div className="h-4 w-px bg-[#444] mx-1"></div>

              <button onClick={reset} disabled={!selectedModule || busy !== null} className="flex items-center gap-1.5 hover:bg-[#3e3e42] px-2 py-1 rounded-sm transition-colors text-slate-300 disabled:opacity-30 cursor-pointer">
                 <RotateCcw className="w-3.5 h-3.5" /> OdLwieLL
              </button>

              <button
                 onClick={applyPreview}
                 disabled={!pendingPreview || busy !== null}
                 className={clsx(
                    "flex items-center gap-1.5 px-3 py-1 rounded-sm font-bold transition-colors cursor-pointer",
                    pendingPreview ? "bg-blue-600 text-white hover:bg-blue-500 shadow-md shadow-blue-900/50" : "text-slate-500 bg-[#1e1e1e] border border-[#333]"
                 )}
              >
                 {busy === "apply" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />} Zastosuj
              </button>

              {error && <span className="text-red-400 text-[10px] ml-4 font-bold flex items-center gap-1"><AlertCircle className="w-3 h-3"/> {error}</span>}
           </div>

           <div className="flex items-center gap-3">
              <div className="flex bg-[#1e1e1e] rounded-sm p-0.5 border border-[#111]">
                  <button onClick={() => setSceneMode(false)} className={clsx("px-3 py-1 rounded-sm font-black transition-colors cursor-pointer", !sceneMode ? "bg-[#3e3e42] text-white" : "text-slate-500 hover:text-slate-300")}><Box className="w-3.5 h-3.5 inline mr-1" /> ModuL,</button>
                  <button onClick={() => setSceneMode(true)} className={clsx("px-3 py-1 rounded-sm font-black transition-colors cursor-pointer", sceneMode ? "bg-[#3e3e42] text-white" : "text-slate-500 hover:text-slate-300")}><Layers className="w-3.5 h-3.5 inline mr-1" /> Scena</button>
              </div>
           </div>
        </div>

        {/* CAD WORKSPACE */}
        <div className="flex flex-1 overflow-hidden">

           {/* LEFT PANEL: PROPERTIES TREE */}
           <div className="w-[340px] shrink-0 border-r border-[#111] bg-[#252526] flex flex-col z-10 shadow-lg relative">
              <div className="p-3 border-b border-[#111] bg-[#2d2d2d] flex flex-col gap-2">
                 <label className="text-[9px] text-slate-500 font-bold uppercase tracking-widest">Aktywny ModuL,</label>
                 <select
                   value={selectedId}
                   onChange={(e) => setSelectedId(e.target.value)}
                   className="bg-[#1e1e1e] border border-[#111] rounded-sm px-2 py-1.5 text-slate-200 outline-none focus:border-blue-500 text-[11px] w-full"
                   disabled={loading || modules.length === 0}
                 >
                   {modules.map((m) => (
                     <option key={m.id} value={String(m.id)}>
                       [{m.id}] {m.name}
                     </option>
                   ))}
                 </select>
              </div>

              {/* TABS */}
              <div className="flex overflow-x-auto border-b border-[#111] bg-[#2d2d2d] custom-scrollbar hide-scrollbar-arrows text-[9px] font-black uppercase tracking-widest px-2 pt-2">
                 {[
                   { id: "main", label: "Gowne" },
                   { id: "options", label: "Opcje" },
                   { id: "fittings", label: "Okucia" },
                   { id: "settings", label: "Ustawienia" },
                   { id: "cam", label: "CAM" },
                 ].map(t => (
                   <button
                     key={t.id}
                     onClick={() => setActiveTab(t.id as any)}
                     className={clsx(
                       "px-3 pb-2 pt-1 border-b-2 transition-colors whitespace-nowrap cursor-pointer",
                       activeTab === t.id ? "border-blue-500 text-white" : "border-transparent text-slate-500 hover:text-slate-300 hover:bg-[#3e3e42]"
                     )}
                   >
                     {t.label}
                   </button>
                 ))}
              </div>

              {/* PROPERTIES CONTENT */}
              <div className="flex-1 overflow-auto custom-scrollbar p-3 space-y-4">
                 {activeTab === "main" && (
                    <div className="space-y-4">
                       {/* Cabinet type */}
                       <div className="space-y-2 pb-4 border-b border-[#333]">
                         <div className="text-[10px] font-black text-slate-400 mb-1">TYP SZAFKI</div>
                         <select
                           value={selectedModule?.cabinet_type || "base"}
                           onChange={(e) => {
                             const type = e.target.value as NonNullable<ProjectModule["cabinet_type"]>;
                             const presets: Record<string, { w: number; h: number; d: number }> = {
                               base:        { w: 600, h: 720, d: 560 },
                               wall:        { w: 600, h: 720, d: 300 },
                               tall:        { w: 600, h: 2000, d: 560 },
                               corner_base: { w: 900, h: 820, d: 560 },
                               corner_wall: { w: 600, h: 720, d: 320 },
                             };
                             const p = presets[type];
                             setW(p.w); setH(p.h); setD(p.d);
                             updateProperty("cabinet_type", type);
                           }}
                           className="bg-[#1e1e1e] text-white border border-[#333] p-1 rounded-sm w-full outline-none focus:border-blue-500"
                         >
                           <option value="base">Szafka dolna (720A-600A-560)</option>
                           <option value="wall">Szafka wiszA...ca (720A-600A-300)</option>
                           <option value="tall">Szafka wysoka (2000A-600A-560)</option>
                           <option value="corner_base">NaroLLna dolna (820A-900A-560)</option>
                           <option value="corner_wall">NaroLLna wiszA...ca (720A-600A-320)</option>
                         </select>
                       </div>

                       {/* Dimensions */}
                       <div className="space-y-2 pb-4 border-b border-[#333]">
                         <div className="text-[10px] font-black text-slate-400 mb-1">WYMIARY BAZOWE</div>
                         {[
                           { key: 'width', label: 'SzerokoLA X', val: w, setter: setW },
                           { key: 'height', label: 'WysokoLA Y', val: h, setter: setH },
                           { key: 'depth', label: 'GL,ATMbokoLA Z', val: d, setter: setD }
                         ].map(dim => (
                           <div key={dim.key} className="flex items-center justify-between">
                              <span className="text-slate-400 w-24 text-[10px]">{dim.label}</span>
                              <div className="flex flex-1 items-center gap-1">
                                 <input
                                   type="number"
                                   value={dim.val}
                                   onChange={(e) => dim.setter(parseInt(e.target.value) || 0)}
                                   className="flex-1 bg-[#1e1e1e] border border-[#333] px-2 py-1 text-white font-mono text-right rounded-sm focus:border-blue-500 outline-none h-6"
                                 />
                                 <button
                                   onClick={() => buildPreview(dim.key as any)}
                                   className="bg-[#3e3e42] hover:bg-blue-600 px-2 py-1 rounded-sm text-white font-bold h-6 cursor-pointer"
                                 >
                                    OK
                                 </button>
                              </div>
                           </div>
                         ))}
                       </div>
                                                {/* Ilosc (Quantity) */}
                        <div className="space-y-2 pb-4 border-b border-[#333]">
                           <div className="flex items-center justify-between">
                              <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Ilosc (Sztuk)</span>
                              <input
                                 type="number"
                                 value={selectedModule?.quantity || 1}
                                 onChange={(e) => updateProperty("quantity", parseInt(e.target.value) || 1)}
                                 className="w-20 bg-[#1e1e1e] border border-[#333] px-2 py-1 text-white font-mono text-right rounded-sm focus:border-blue-500 outline-none h-6"
                              />
                           </div>
                        </div>

                        {/* Materials (Quick Preview style) */}
                        <div className="space-y-2">
                          <div className="text-[10px] font-black text-slate-400 mb-1">MATERIAY BAZOWE</div>
                          {[
                            { key: 'carcass', label: 'Korpus' },
                            { key: 'front', label: 'Fronty' },
                            { key: 'back', label: 'Plecy' }
                          ].map(grp => (
                             <div key={grp.key} className="flex flex-col gap-1 p-2 border border-[#333] rounded-sm bg-[#1e1e1e]/50">
                                <div className="text-[9px] text-slate-500 font-bold uppercase">{grp.label}</div>
                                <select
                                   className="bg-[#2d2d2d] border border-[#333] text-white px-2 py-1 rounded-sm outline-none text-[11px]"
                                   value={selectedModule?.materials?.[grp.key] || ""}
                                   onChange={(e) => setPartMaterial(grp.key, parseInt(e.target.value))}
                                >
                                   <option value="">-- Pyta --</option>
                                   {allMaterials.map(m => (
                                      <option key={m.id} value={m.name}>{m.name} ({m.thickness}mm)</option>
                                   ))}
                                </select>
                             </div>
                          ))}
                        </div>
                     </div>
                  )}

                  {activeTab === "options" && (
                     <div className="space-y-4 animate-in fade-in slide-in-from-left-2 duration-200">
                        {/* Construction - Joints */}
                        <div className="space-y-3 pb-4 border-b border-[#333]">
                          <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest">KONSTRUKCJA</div>
                          <div className="flex flex-col gap-1">
                            <label className="text-slate-500 text-[10px]">Zacza Korpusu</label>
                            <select value={selectedModule?.carcass_joint_type || "type2"} onChange={(e) => updateProperty("carcass_joint_type", e.target.value)} className="bg-[#1e1e1e] text-white border border-[#333] p-1 rounded-sm text-[11px] outline-none focus:border-blue-500">
                               <option value="type2">Wieniec miedzy boki</option>
                               <option value="minifix">Mimosrody (Minifix)</option>
                               <option value="confirmat">Konfirmanty</option>
                               <option value="clamex">Lamello Clamex</option>
                            </select>
                          </div>
                          <div className="flex flex-col gap-1">
                            <label className="text-slate-500 text-[10px]">Montaz Plecow</label>
                            <select value={selectedModule?.back_mounting_mode || "insert"} onChange={(e) => updateProperty("back_mounting_mode", e.target.value)} className="bg-[#1e1e1e] text-white border border-[#333] p-1 rounded-sm text-[11px] outline-none focus:border-blue-500">
                               <option value="overlay">Nakadane (Overlay)</option>
                               <option value="insert">Wpuszczane (Insert)</option>
                               <option value="recess">W nucie (Recess 20mm)</option>
                               <option value="recess_service">Serwisowe (50mm)</option>
                            </select>
                          </div>
                        </div>

                        {/* Components */}
                        <div className="space-y-3 pb-4 border-b border-[#333]">
                           <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest">WNETRZE</div>
                           <div className="grid grid-cols-2 gap-3">
                              <div>
                                 <label className="text-slate-500 text-[10px] block mb-1">Poki (szt)</label>
                                 <input type="number" value={selectedModule?.shelf_count || 0} onChange={(e) => updateProperty("shelf_count", parseInt(e.target.value) || 0)} className="bg-[#1e1e1e] text-white border border-[#333] p-1 rounded-sm w-full font-mono text-right focus:border-blue-500 outline-none h-7"/>
                              </div>
                              <div>
                                 <label className="text-slate-500 text-[10px] block mb-1">Przegrody (szt)</label>
                                 <input type="number" value={selectedModule?.divider_count || 0} onChange={(e) => updateProperty("divider_count", parseInt(e.target.value) || 0)} className="bg-[#1e1e1e] text-white border border-[#333] p-1 rounded-sm w-full font-mono text-right focus:border-blue-500 outline-none h-7"/>
                              </div>
                           </div>
                        </div>

                        {/* Legs & Plinth */}
                        <div className="space-y-3">
                           <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest">NOZKI I COKO</div>

                           <div className="flex items-center justify-between mb-2">
                             <label className="text-slate-500 text-[10px]">Coko (Plinth)</label>
                             <input
                                type="checkbox"
                                checked={!!selectedModule?.has_plinth}
                                onChange={(e) => updateProperty("has_plinth", e.target.checked)}
                                className="w-4 h-4 rounded border-[#333] bg-[#1e1e1e] text-blue-600 focus:ring-blue-500"
                             />
                           </div>

                           <div className="grid grid-cols-2 gap-2">
                              <div>
                                 <div className="text-[9px] text-slate-500 mb-0.5">Wysokosc Nozki</div>
                                 <input type="number" value={selectedModule?.legs_height_mm ?? 100} onChange={(e) => updateProperty("legs_height_mm", parseFloat(e.target.value) || 0)} className="bg-[#1e1e1e] text-white border border-[#333] w-full p-1 text-right font-mono rounded-sm outline-none focus:border-blue-500 h-7"/>
                              </div>
                              <div>
                                 <div className="text-[9px] text-slate-500 mb-0.5">Cofniecie Cokou</div>
                                 <input type="number" value={selectedModule?.plinth_inset_mm ?? 20} onChange={(e) => updateProperty("plinth_inset_mm", parseFloat(e.target.value) || 0)} className="bg-[#1e1e1e] text-white border border-[#333] w-full p-1 text-right font-mono rounded-sm outline-none focus:border-blue-500 h-7" disabled={!selectedModule?.has_plinth}/>
                              </div>
                           </div>

                           <div className="pt-2">
                              <div className="text-[9px] text-slate-500 mb-1 uppercase font-bold">Odsuniecia Nozek (L/P, P/T)</div>
                              <div className="grid grid-cols-3 gap-1">
                                 <div>
                                    <div className="text-[8px] text-slate-600 mb-0.5">Przod</div>
                                    <input type="number" value={selectedModule?.leg_offset_front ?? 50} onChange={(e) => updateProperty("leg_offset_front", parseFloat(e.target.value) || 0)} className="bg-[#1a1a1c] text-white border border-[#333] w-full p-1 text-center font-mono rounded-sm text-[10px] outline-none focus:border-blue-500 h-6"/>
                                 </div>
                                 <div>
                                    <div className="text-[8px] text-slate-600 mb-0.5">Ty</div>
                                    <input type="number" value={selectedModule?.leg_offset_back ?? 50} onChange={(e) => updateProperty("leg_offset_back", parseFloat(e.target.value) || 0)} className="bg-[#1a1a1c] text-white border border-[#333] w-full p-1 text-center font-mono rounded-sm text-[10px] outline-none focus:border-blue-500 h-6"/>
                                 </div>
                                 <div>
                                    <div className="text-[8px] text-slate-600 mb-0.5">Boki</div>
                                    <input type="number" value={selectedModule?.leg_offset_side ?? 50} onChange={(e) => updateProperty("leg_offset_side", parseFloat(e.target.value) || 0)} className="bg-[#1a1a1c] text-white border border-[#333] w-full p-1 text-center font-mono rounded-sm text-[10px] outline-none focus:border-blue-500 h-6"/>
                                 </div>
                              </div>
                           </div>
                        </div>
                     </div>
                  )}

                  {activeTab === "fittings" && (
                     <div className="space-y-4 animate-in fade-in slide-in-from-left-2 duration-200">
                        {/* Front Layout */}
                        <div className="space-y-3 pb-4 border-b border-[#333]">
                          <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest">FRONT I UKAD</div>
                          <div className="flex flex-col gap-1">
                            <label className="text-slate-500 text-[10px]">Typ Elewacji</label>
                            <select value={selectedModule?.facade_mode || "doors"} onChange={(e) => updateProperty("facade_mode", e.target.value)} className="bg-[#1e1e1e] text-white border border-[#333] p-1 rounded-sm text-[11px] outline-none focus:border-blue-500">
                               <option value="doors">Drzwi</option>
                               <option value="drawers">Szuflady</option>
                               <option value="open">Otwarta</option>
                               <option value="sliding">Przesuwne</option>
                            </select>
                          </div>
                        </div>

                        {/* Gaps Grid */}
                        <div className="space-y-3 pb-4 border-b border-[#333]">
                           <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest">LUZY (FUGI)</div>
                           <div className="flex items-center justify-center p-4 bg-[#111] rounded-sm border border-[#333] relative">
                              <div className="w-24 h-32 border-2 border-slate-600 rounded-sm relative flex items-center justify-center">
                                 <span className="text-[8px] text-slate-700 font-black">FRONT</span>
                                 {/* Top Gap */}
                                 <input
                                    type="number" value={selectedModule?.front_gap_top ?? 2}
                                    onChange={(e) => updateProperty("front_gap_top", parseFloat(e.target.value) || 0)}
                                    className="absolute -top-3 left-1/2 -translate-x-1/2 w-8 h-5 bg-[#252526] border border-[#444] text-white text-[9px] text-center rounded-xs outline-none"
                                    title="Gora"
                                 />
                                 {/* Bottom Gap */}
                                 <input
                                    type="number" value={selectedModule?.front_gap_bottom ?? 2}
                                    onChange={(e) => updateProperty("front_gap_bottom", parseFloat(e.target.value) || 0)}
                                    className="absolute -bottom-3 left-1/2 -translate-x-1/2 w-8 h-5 bg-[#252526] border border-[#444] text-white text-[9px] text-center rounded-xs outline-none"
                                    title="Do"
                                 />
                                 {/* Left Gap */}
                                 <input
                                    type="number" value={selectedModule?.front_gap_left ?? 2}
                                    onChange={(e) => updateProperty("front_gap_left", parseFloat(e.target.value) || 0)}
                                    className="absolute top-1/2 -left-4 -translate-y-1/2 w-8 h-5 bg-[#252526] border border-[#444] text-white text-[9px] text-center rounded-xs outline-none"
                                    title="Lewo"
                                 />
                                 {/* Right Gap */}
                                 <input
                                    type="number" value={selectedModule?.front_gap_right ?? 2}
                                    onChange={(e) => updateProperty("front_gap_right", parseFloat(e.target.value) || 0)}
                                    className="absolute top-1/2 -right-4 -translate-y-1/2 w-8 h-5 bg-[#252526] border border-[#444] text-white text-[9px] text-center rounded-xs outline-none"
                                    title="Prawo"
                                 />
                              </div>
                           </div>
                        </div>

                        {/* Systems */}
                        <div className="space-y-3">
                           <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest">SYSTEMY OKUC</div>
                           <div className="space-y-2">
                              <div className="flex flex-col gap-1">
                                <label className="text-slate-500 text-[10px]">Prowadnice Szuflad</label>
                                <select value={selectedModule?.drawer_vendor || "generic"} onChange={(e) => updateProperty("drawer_vendor", e.target.value)} className="bg-[#1e1e1e] text-white border border-[#333] p-1 rounded-sm text-[11px] outline-none">
                                   <option value="generic">Ekonomiczne</option>
                                   <option value="blum_tandembox">Blum TANDEMBOX</option>
                                   <option value="blum_legrabox">Blum LEGRABOX</option>
                                   <option value="gtv_modernbox">GTV ModernBox</option>
                                </select>
                              </div>
                              <div className="flex flex-col gap-1">
                                <label className="text-slate-500 text-[10px]">Zawiasy</label>
                                <select value={selectedModule?.hinge_vendor || "blum"} onChange={(e) => updateProperty("hinge_vendor", e.target.value)} className="bg-[#1e1e1e] text-white border border-[#333] p-1 rounded-sm text-[11px] outline-none">
                                   <option value="blum">Blum Clip-Top</option>
                                   <option value="gtv">GTV Prestige</option>
                                   <option value="hafele">Hafele Metalla</option>
                                </select>
                              </div>
                           </div>
                        </div>
                     </div>
                  )}

                  {activeTab === "settings" && (
                     <div className="space-y-4 animate-in fade-in slide-in-from-left-2 duration-200">
                        <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest">METADANE I SCENA</div>

                        <div className="space-y-3">
                           <div className="flex flex-col gap-1">
                              <label className="text-[9px] text-slate-500 font-bold uppercase">Kod Moduu</label>
                              <input
                                 type="text"
                                 value={selectedModule?.code || ""}
                                 onChange={(e) => updateProperty("code", e.target.value)}
                                 className="bg-[#1e1e1e] border border-[#333] rounded-sm px-2 py-1.5 text-white outline-none focus:border-blue-500 text-[11px]"
                                 placeholder="NP. SD-60"
                              />
                           </div>

                           <div className="flex flex-col gap-1">
                              <label className="text-[9px] text-slate-500 font-bold uppercase">Opis</label>
                              <textarea
                                 value={selectedModule?.description || ""}
                                 onChange={(e) => updateProperty("description", e.target.value)}
                                 className="bg-[#1e1e1e] border border-[#333] rounded-sm p-2 text-white h-24 outline-none focus:border-blue-500 resize-none text-[11px]"
                                 placeholder="Opis handlowy..."
                              />
                           </div>

                           <div className="flex flex-col gap-1 border-t border-[#333] pt-3">
                              <label className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mb-2">USTAWIENIA PREZENTACJI</label>
                              <label className="flex items-center justify-between cursor-pointer group py-1">
                                 <span className="text-[10px] text-slate-300 group-hover:text-white transition-colors">Widoczny w rzutach</span>
                                 <input
                                    type="checkbox"
                                    checked={selectedModule?.visible_in_projection !== false}
                                    onChange={(e) => updateProperty("visible_in_projection", e.target.checked)}
                                    className="w-4 h-4 rounded border-[#333] bg-[#1e1e1e] text-blue-600"
                                 />
                              </label>
                              <label className="flex items-center justify-between cursor-pointer group py-1">
                                 <span className="text-[10px] text-slate-300 group-hover:text-white transition-colors">Zablokuj wymiary</span>
                                 <input
                                    type="checkbox"
                                    checked={!!selectedModule?.lock_dimensions}
                                    onChange={(e) => updateProperty("lock_dimensions", e.target.checked)}
                                    className="w-4 h-4 rounded border-[#333] bg-[#1e1e1e] text-blue-600"
                                 />
                              </label>
                           </div>
                        </div>
                     </div>
                  )}

                  {activeTab === "cam" && (
                    <div className="space-y-4 animate-in fade-in slide-in-from-left-2 duration-200">
                        <div className="flex bg-[#1e1e1e] p-1 rounded-sm border border-[#111] mb-2">
                           <button onClick={() => setActiveTab("cam")} className="flex-1 py-1 text-[9px] font-bold uppercase bg-[#3e3e42] text-white rounded-xs">Produkcja</button>
                           {/* Add sub-navigation if needed later */}
                        </div>

                        <ConfigurationProductionTab
                          productionSummary={productionSummary}
                          projectId={projectId}
                          selectedId={selectedId}
                        />

                        <div className="pt-4 border-t border-[#333]">
                           <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">DRZEWO FORMATEK</div>
                           <div className="space-y-1">
                              {selectedModule?.parts && Object.values(selectedModule.parts).map((part: any) => (
                                 <div
                                    key={part.id}
                                    className="p-1.5 border border-[#111] bg-[#1a1a1c] rounded-xs flex items-center justify-between group hover:border-[#444] transition-colors"
                                    onMouseEnter={() => setHighlightedPartId(part.id)}
                                    onMouseLeave={() => setHighlightedPartId(null)}
                                    onClick={() => { setEditingPart(part); setActiveTab("cam"); }}
                                 >
                                    <span className="text-[10px] text-slate-300">{part.name_pl}</span>
                                    <span className="text-[9px] text-slate-600 font-mono">{part.id}</span>
                                 </div>
                              ))}
                           </div>
                        </div>
                     </div>
                  )}
              </div>
           </div>

           {/* CENTER PANEL: CANVAS 3D/2D */}
           <div className="flex-1 relative bg-[#18191c] border-r border-[#111] overflow-hidden flex min-h-[300px]">
              {/* Scene Mode Button Overlay */}
              {sceneMode && <div className="absolute top-4 left-4 bg-[#111]/80 backdrop-blur border border-[#333] px-3 py-1 rounded-sm text-slate-300 font-bold uppercase z-10"><Layers className="w-3 h-3 inline mr-1 text-blue-400" /> Scena Multi-Moduowa</div>}

              <div className="w-full h-full p-0">
                <Module3DViewer
                  width={w}
                  height={h}
                  depth={d}
                  name={selectedModule?.name}
                  legHeight={selectedModule?.legs_height_mm || 100}
                  legOffsetSide={selectedModule?.leg_offset_side || 50}
                  legOffsetFront={selectedModule?.leg_offset_front || 50}
                  legOffsetBack={selectedModule?.leg_offset_back || 50}
                  shelfCount={selectedModule?.shelf_count || 0}
                  showInterior={selectedModule?.show_interior !== false}
                  modules={sceneMode ? modules : undefined}
                  obstacles={obstacles}
                  handleType={selectedModule?.handle_type as any || 'none'}
                  handleLength={selectedModule?.handle_length || 128}
                  handleOrientation={selectedModule?.handle_orientation || 'horizontal'}
                  handlePosX={selectedModule?.handle_pos_x || 'center'}
                  handlePosY={selectedModule?.handle_pos_y || 'top'}
                  color={carcassMaterial?.color_hex || '#ffffff'}
                  textureUrl={carcassMaterial?.texture_url}
                  highlightedPartId={highlightedPartId || undefined}
                  onPartClick={(pid) => {setHighlightedPartId(pid); setEditingPart(selectedModule?.parts?.[pid]); setActiveTab("cam")}}
                />
              </div>
           </div>

           {/* RIGHT PANEL: BOM / PARTS LIST (Fixed Width CAD Table) */}
           <div className="w-[450px] shrink-0 bg-[#1e1e1e] flex flex-col z-10 shadow-lg relative h-full">
              <div className="h-10 bg-[#252526] border-b border-[#111] flex items-center px-4 font-bold text-[#aaa] tracking-widest text-[10px]">
                 ZESTAWIENIE FORMATEK (BOM)
              </div>
              <div className="flex-1 overflow-auto custom-scrollbar">
                 <table className="w-full text-left border-collapse text-[10px] tabular-nums">
                    <thead className="sticky top-0 bg-[#2d2d2d] z-10 shadow-sm border-b border-[#111]">
                       <tr className="text-slate-400">
                          <th className="px-3 py-1.5 font-normal border-r border-[#333]">Nazwa</th>
                          <th className="px-3 py-1.5 font-normal border-r border-[#333]">Wymiary (mm)</th>
                          <th className="px-3 py-1.5 font-normal">Materia</th>
                       </tr>
                    </thead>
                    <tbody className="divide-y divide-[#111]">
                       {selectedModule?.parts && Object.values(selectedModule.parts).length > 0 ? Object.values(selectedModule.parts).map((part: any, i: number) => (
                          <tr
                            key={part.id}
                            className={clsx(
                               "hover:bg-[#2a2d2e] cursor-pointer transition-colors group",
                               highlightedPartId === part.id ? "bg-[#252526] text-blue-300" : "text-slate-300",
                               editingPart?.id === part.id ? "bg-[#3e3e42] border-l-2 border-l-blue-500" : ""
                            )}
                            onMouseEnter={() => setHighlightedPartId(part.id)}
                            onMouseLeave={() => setHighlightedPartId(null)}
                            onClick={() => { setEditingPart(part); }}
                          >
                             <td className="px-3 py-2 border-r border-[#222]">
                                <div className="font-bold text-white group-hover:text-blue-400">{part.name_pl}</div>
                                <div className="text-[8px] text-slate-600 mt-0.5">{(i+1).toString().padStart(2, '0')} - {part.id}</div>
                             </td>
                             <td className="px-3 py-2 border-r border-[#222]">
                                {(part.dims_mm?.w || 0).toFixed(1)} <span className="text-slate-600">x</span> {(part.dims_mm?.h || 0).toFixed(1)} <span className="text-slate-600">x</span> {(part.dims_mm?.t || 0).toFixed(0)}
                             </td>
                             <td className="px-3 py-2 text-slate-400 truncate max-w-[150px]">
                                {part.material_override_key || part.material_key || "-"}
                             </td>
                          </tr>
                       )) : (
                          <tr><td colSpan={3} className="px-3 py-10 text-center text-slate-600 italic border-b border-[#111]">
                             Wybierz wymiary aby wygenerowac BOM.
                          </td></tr>
                       )}
                    </tbody>
                 </table>
              </div>

              <div className="p-4 bg-[#252526] border-t border-[#111] space-y-2">
                 <div className="flex justify-between text-[10px] text-slate-500 font-bold uppercase tracking-widest">
                    <span>Razem Powierzchnia:</span>
                    <span className="text-white">{(valuation?.m2_total || 0).toFixed(2)} m2</span>
                 </div>
                 <div className="flex justify-between text-[10px] text-slate-500 font-bold uppercase tracking-widest">
                    <span>Razem Okleina:</span>
                    <span className="text-white">{(valuation?.lm_total || 0).toFixed(1)} mb</span>
                 </div>
              </div>
           </div>
        </div>

        {/* EDITING PART MODAL (INSPEKTOR) */}
        {editingPart && (
           <ConfigurationPartInspector
             editingPart={editingPart}
             allMaterials={allMaterials}
             onClose={() => setEditingPart(null)}
             updatePartProperty={updatePartProperty}
           />
        )}

      </div>

      <MaterialPicker
        isOpen={pickerOpen}
        onClose={() => setPickerOpen(false)}
        title={`Wybierz materia: ${pickerGroup === 'carcass' ? 'Korpus' : pickerGroup === 'front' ? 'Fronty' : 'Plecy'}`}
        categoryHint={pickerGroup === 'front' ? 'Front' : pickerGroup === 'back' ? 'HDF' : 'Pyta'}
        onSelect={(mat) => {
          setPartMaterial(pickerGroup, mat.id);
          setPickerOpen(false);
        }}
      />
    </AppShell>
  );
}
