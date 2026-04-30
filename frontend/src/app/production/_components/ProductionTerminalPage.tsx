"use client";

import { useEffect, useMemo, useState } from "react";
import clsx from "clsx";
import { AlertTriangle, CheckCircle2, Clock, Cpu, Lightbulb, Play, Timer } from "lucide-react";
import BusinessHealthStrip from "@/components/BusinessHealthStrip";
import { Button, Card } from "@/components/ui";
import { TechModulAPI, type MaterialRecord, type ProductionTask } from "@/services/api";

type StationId = "cnc" | "oklejanie" | "lakiernia" | "montaz" | "biuro";

const STATIONS: Array<{ id: StationId; label: string }> = [
  { id: "cnc", label: "CNC" },
  { id: "oklejanie", label: "Oklejanie" },
  { id: "lakiernia", label: "Lakiernia" },
  { id: "montaz", label: "Montaz" },
  { id: "biuro", label: "Biuro" },
];

function statusLabel(value: string): string {
  const token = String(value || "").toLowerCase();
  if (token === "w_trakcie") return "W TRAKCIE";
  if (token === "planowane") return "PLANOWANE";
  if (token === "zakonczone" || token === "zakonczone" || token === "wykonane") return "ZAKONCZONE";
  return token.toUpperCase() || "NIEZNANE";
}

function formatDuration(seconds: number): string {
  const safe = Math.max(0, Math.floor(seconds || 0));
  const h = Math.floor(safe / 3600);
  const m = Math.floor((safe % 3600) / 60);
  const s = safe % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function normalizeToken(value: string): string {
  return String(value || "")
    .toLowerCase()
    .replaceAll("a", "a")
    .replaceAll("c", "c")
    .replaceAll("e", "e")
    .replaceAll("", "l")
    .replaceAll("n", "n")
    .replaceAll("o", "o")
    .replaceAll("s", "s")
    .replaceAll("z", "z")
    .replaceAll("z", "z");
}

function compactToken(value: string): string {
  return normalizeToken(value).replace(/\s+/g, "");
}

function taskSearchText(task: ProductionTask): string {
  return normalizeToken(`${task.project_name || ""} ${task.client_name || ""} ${task.notes || ""} ${task.task_type || ""}`);
}

function detectSheetFormat(text: string): string {
  const compact = compactToken(text);
  const match = compact.match(/(\d{3,4})\s*[x*\/-]\s*(\d{3,4})/i);
  if (!match) return "";
  const a = Number(match[1] || 0);
  const b = Number(match[2] || 0);
  if (a <= 0 || b <= 0) return "";
  const longSide = Math.max(a, b);
  const shortSide = Math.min(a, b);
  return `${longSide}x${shortSide}`;
}

function detectGlueType(text: string): "BIALY" | "BEZBARWNY" {
  const t = normalizeToken(text);
  const whiteHints = ["bialy", "biala", "white", "alpin", "snow", "jasny bialy"];
  for (const hint of whiteHints) {
    if (t.includes(hint)) return "BIALY";
  }
  return "BEZBARWNY";
}

function formatFromMaterial(material?: MaterialRecord | null): string {
  if (!material) return "";
  const l = Number(material.format_length_mm || 0);
  const w = Number(material.format_width_mm || 0);
  if (l > 0 && w > 0) {
    const longSide = Math.max(l, w);
    const shortSide = Math.min(l, w);
    return `${longSide}x${shortSide}`;
  }
  return "";
}

function findMaterialForTask(task: ProductionTask, materials: MaterialRecord[]): MaterialRecord | null {
  if (!materials.length) return null;
  const hay = compactToken(taskSearchText(task));
  let best: MaterialRecord | null = null;
  let bestScore = -1;
  for (const mat of materials) {
    const name = compactToken(mat.name || "");
    const code = compactToken(mat.material_code || "");
    let score = 0;
    if (code && hay.includes(code)) score += 4;
    if (name && hay.includes(name)) score += 3;
    const chunks = name.split(/[^a-z0-9]+/i).filter((x) => x.length >= 4);
    for (const c of chunks) {
      if (hay.includes(c)) score += 1;
    }
    if (score > bestScore) {
      bestScore = score;
      best = mat;
    }
  }
  return bestScore > 0 ? best : null;
}

function detectBatchTag(task: ProductionTask): string {
  const source = normalizeToken(
    `${task.project_name || ""} ${task.client_name || ""} ${task.notes || ""} ${task.task_type || ""}`
  );
  if (source.includes("bial")) return "BIALY";
  if (source.includes("czarn")) return "CZARNY";
  if (source.includes("szar")) return "SZARY";
  if (source.includes("dab")) return "DAB";
  if (source.includes("orzech")) return "ORZECH";
  if (source.includes("mat")) return "MAT";
  if (source.includes("polysk")) return "POLYSK";
  if (source.includes("hpl")) return "HPL";
  if (source.includes("mdf")) return "MDF";
  if (source.includes("hdf")) return "HDF";
  return "MIX";
}

function toDateWeight(dateValue?: string): number {
  if (!dateValue) return 10_000_000;
  const t = Date.parse(dateValue);
  return Number.isFinite(t) ? t : 10_000_000;
}

function elapsedFromUpdatedAt(task: ProductionTask | null): number {
  if (!task?.updated_at) return 0;
  const t = Date.parse(task.updated_at);
  if (!Number.isFinite(t)) return 0;
  return Math.floor((Date.now() - t) / 1000);
}

export default function ProductionTerminalPage({ initialStation = "cnc" }: { initialStation?: StationId }) {
  const [station, setStation] = useState<StationId>(initialStation);
  const [statusFilter, setStatusFilter] = useState<"active" | "all" | "done">("active");
  const [showAllStations, setShowAllStations] = useState(false);
  const [multiStart, setMultiStart] = useState(initialStation === "lakiernia");
  const [tasks, setTasks] = useState<ProductionTask[]>([]);
  const [materials, setMaterials] = useState<MaterialRecord[]>([]);
  const [workers, setWorkers] = useState<Array<{ worker_id: string; name: string; role?: string }>>([]);
  const [selectedTaskIds, setSelectedTaskIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [workerId, setWorkerId] = useState("");
  const [workerName, setWorkerName] = useState("");
  const [note, setNote] = useState("");
  const [correctionNote, setCorrectionNote] = useState("");
  const [error, setError] = useState("");
  const [tick, setTick] = useState(0);
  const [lastSync, setLastSync] = useState("");

  useEffect(() => {
    const cachedId = window.localStorage.getItem(`production_worker_id_${initialStation}`);
    const cached = window.localStorage.getItem(`production_worker_name_${initialStation}`);
    if (cachedId) setWorkerId(cachedId);
    if (cached) setWorkerName(cached);
  }, [initialStation]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const rows = await TechModulAPI.getKioskWorkers();
        if (!mounted) return;
        const normalized = (rows || [])
          .map((w: any) => ({
            worker_id: String(w.worker_id || w.id || "").trim(),
            name: String(w.name || "").trim(),
            role: w.role || "",
          }))
          .filter((w) => w.worker_id && w.name)
          .sort((a, b) => a.name.localeCompare(b.name, "pl"));
        setWorkers(normalized);
      } catch {
        if (mounted) setWorkers([]);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    window.localStorage.setItem(`production_worker_id_${initialStation}`, workerId);
    window.localStorage.setItem(`production_worker_name_${initialStation}`, workerName);
  }, [workerId, workerName, initialStation]);

  useEffect(() => {
    let mounted = true;
    const loadMaterials = async () => {
      try {
        const rows = await TechModulAPI.getMaterials();
        if (mounted) setMaterials(rows || []);
      } catch {
        if (mounted) setMaterials([]);
      }
    };
    if (station === "cnc" || station === "lakiernia") {
      void loadMaterials();
    }
    return () => {
      mounted = false;
    };
  }, [station]);

  const loadTasks = async () => {
    setError("");
    try {
      const apiStation = showAllStations ? "" : station;
      const res = await TechModulAPI.getProductionTasks(apiStation, statusFilter, 500);
      setTasks(res.items || []);
      setLastSync(new Date().toLocaleTimeString());
    } catch (e: any) {
      setError(e?.message || "Nie udalo sie pobrac zadan.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    setSelectedTaskIds(new Set());
    void loadTasks();
    const poll = setInterval(() => {
      void loadTasks();
      setTick((x) => x + 1);
    }, 10000);
    return () => clearInterval(poll);
  }, [station, statusFilter, showAllStations]);

  useEffect(() => {
    setMultiStart(station === "lakiernia");
  }, [station]);

  const activeTasks = useMemo(
    () => tasks.filter((t) => String(t.status || "").toLowerCase() === "w_trakcie"),
    [tasks, tick]
  );
  const activeTask = useMemo(
    () => activeTasks[0] || null,
    [tasks, tick]
  );
  const queueTasks = useMemo(
    () =>
      tasks.filter((t) => {
        const token = String(t.status || "").toLowerCase();
        return token !== "w_trakcie" && token !== "zakonczone" && token !== "zakonczone" && token !== "wykonane";
      }),
    [tasks]
  );
  const doneTasksCount = useMemo(
    () =>
      tasks.filter((t) => {
        const token = String(t.status || "").toLowerCase();
        return token === "zakonczone" || token === "zakonczone" || token === "wykonane";
      }).length,
    [tasks]
  );
  const recommendedQueue = useMemo(() => {
    const buckets = new Map<string, ProductionTask[]>();
    for (const task of queueTasks) {
      const tag = detectBatchTag(task);
      if (!buckets.has(tag)) buckets.set(tag, []);
      buckets.get(tag)!.push(task);
    }
    let dominantTag = "MIX";
    let dominantSize = 0;
    for (const [tag, items] of Array.from(buckets.entries())) {
      if (items.length > dominantSize) {
        dominantTag = tag;
        dominantSize = items.length;
      }
    }
    const sorted = [...queueTasks].sort((a, b) => {
      const aTag = detectBatchTag(a);
      const bTag = detectBatchTag(b);
      const aDominant = aTag === dominantTag ? 0 : 1;
      const bDominant = bTag === dominantTag ? 0 : 1;
      if (aDominant !== bDominant) return aDominant - bDominant;
      const dateDiff = toDateWeight(a.planned_date) - toDateWeight(b.planned_date);
      if (dateDiff !== 0) return dateDiff;
      return (a.estimated_time_minutes || 0) - (b.estimated_time_minutes || 0);
    });
    let advice = "Wybierz kolejnosc recznie wedug realnego ukadu materiau na stanowisku.";
    if (station === "cnc") {
      advice = `Propozycja CNC: zacznij od grupy '${dominantTag}' (mniej przezbrojen / mniej zmian arkuszy).`;
    } else if (station === "lakiernia") {
      advice = "Propozycja Lakiernia: uruchom partie podobnych wykonczen razem i zamykaj po caej serii.";
    }
    return { items: sorted, advice, dominantTag };
  }, [queueTasks, station]);
  const sheetPlan = useMemo(() => {
    type PlanGroup = {
      key: string;
      label: string;
      format: string;
      materialName: string;
      items: ProductionTask[];
      lowStock: boolean;
    };
    const groups = new Map<string, PlanGroup>();
    for (const task of queueTasks) {
      const matched = findMaterialForTask(task, materials);
      const fromTask = detectSheetFormat(taskSearchText(task));
      const fromMaterial = formatFromMaterial(matched);
      const format = fromTask || fromMaterial || "";
      const materialName = matched?.name || detectBatchTag(task);
      const key = `${compactToken(materialName)}|${format || "NA"}`;
      if (!groups.has(key)) {
        groups.set(key, {
          key,
          label: format ? `${materialName} (${format})` : materialName,
          format,
          materialName,
          items: [],
          lowStock: Boolean((matched?.is_low_stock ?? false) || ((matched?.stock_quantity || 0) <= (matched?.min_stock || 0) && (matched?.min_stock || 0) > 0)),
        });
      }
      groups.get(key)!.items.push(task);
    }
    const ordered = Array.from(groups.values()).sort((a, b) => {
      if (a.lowStock !== b.lowStock) return a.lowStock ? -1 : 1;
      if (b.items.length !== a.items.length) return b.items.length - a.items.length;
      const aDate = toDateWeight(a.items[0]?.planned_date);
      const bDate = toDateWeight(b.items[0]?.planned_date);
      return aDate - bDate;
    });
    const firstGroup = ordered[0] || null;
    const recommendedTaskIds = new Set((firstGroup?.items || []).map((t) => String(t.id)));
    let headline = "";
    if (firstGroup) {
      headline = `Najpierw: ${firstGroup.label}. Potem kolejne grupy wg tej samej logiki, by ograniczyc zmiany arkuszy/ustawien.`;
    } else {
      headline = "Brak danych do planu materiaowego.";
    }
    return { groups: ordered, recommendedTaskIds, headline };
  }, [queueTasks, materials]);
  const oklejaniePlan = useMemo(() => {
    const groups: Record<"BIALY" | "BEZBARWNY", ProductionTask[]> = {
      BIALY: [],
      BEZBARWNY: [],
    };
    for (const task of queueTasks) {
      const matched = findMaterialForTask(task, materials);
      const hintText = `${taskSearchText(task)} ${matched?.name || ""} ${matched?.material_code || ""}`;
      const glue = detectGlueType(hintText);
      groups[glue].push(task);
    }
    const activeGlue = activeTasks.length > 0
      ? detectGlueType(taskSearchText(activeTasks[0]))
      : null;
    const priorityOrder: Array<"BIALY" | "BEZBARWNY"> = activeGlue
      ? [activeGlue, activeGlue === "BIALY" ? "BEZBARWNY" : "BIALY"]
      : (groups.BIALY.length >= groups.BEZBARWNY.length ? ["BIALY", "BEZBARWNY"] : ["BEZBARWNY", "BIALY"]);
    const recommendedGlue = priorityOrder[0];
    const recommendedTaskIds = new Set(groups[recommendedGlue].map((t) => String(t.id)));
    const headline = activeGlue
      ? `Kontynuuj na kleju ${activeGlue}. Najpierw dokoncz te grupe, potem przeacz na ${priorityOrder[1]}.`
      : `Start od kleju ${recommendedGlue}, bo ta grupa ma wiecej zadan i da mniej przezbrojen.`;
    return {
      groups,
      headline,
      recommendedGlue,
      recommendedTaskIds,
      nextGlue: priorityOrder[1],
    };
  }, [queueTasks, materials, activeTasks]);
  const elapsed = elapsedFromUpdatedAt(activeTask);
  const canStartNew = multiStart || activeTasks.length === 0;

  const handleStart = async (task: ProductionTask) => {
    if (!workerId.trim()) {
      setError("Wybierz pracownika z listy.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await TechModulAPI.toggleProductionTask(task.id, workerId.trim(), workerName.trim(), "start", {
        note: note.trim(),
      });
      setNote("");
      await loadTasks();
    } catch (e: any) {
      setError(e?.message || "Nie udalo sie uruchomic zadania.");
    } finally {
      setBusy(false);
    }
  };

  const handleStartSelected = async () => {
    if (!workerId.trim()) {
      setError("Wybierz pracownika z listy.");
      return;
    }
    if (selectedTaskIds.size === 0) {
      setError("Zaznacz przynajmniej jedno zadanie.");
      return;
    }
    if (!multiStart && activeTasks.length > 0) {
      setError("Wyaczone multi-start: najpierw zakoncz aktywne zadanie.");
      return;
    }
    const selected = queueTasks.filter((t) => selectedTaskIds.has(String(t.id)));
    if (selected.length === 0) return;
    setBusy(true);
    setError("");
    try {
      for (const task of selected) {
        await TechModulAPI.toggleProductionTask(task.id, workerId.trim(), workerName.trim(), "start", {
          note: note.trim(),
        });
      }
      setSelectedTaskIds(new Set());
      setNote("");
      await loadTasks();
    } catch (e: any) {
      setError(e?.message || "Nie udalo sie uruchomic wybranych zadan.");
    } finally {
      setBusy(false);
    }
  };

  const handleFinish = async (task: ProductionTask) => {
    if (!workerId.trim()) {
      setError("Wybierz pracownika z listy.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await TechModulAPI.toggleProductionTask(task.id, workerId.trim(), workerName.trim(), "finish", {
        note: note.trim(),
        correction_note: correctionNote.trim(),
      });
      setNote("");
      setCorrectionNote("");
      await loadTasks();
    } catch (e: any) {
      setError(e?.message || "Nie udalo sie zakonczyc zadania.");
    } finally {
      setBusy(false);
    }
  };

  const toggleTaskSelection = (taskId: string) => {
    setSelectedTaskIds((prev) => {
      const next = new Set(prev);
      if (next.has(taskId)) next.delete(taskId);
      else next.add(taskId);
      return next;
    });
  };

  return (
    <div className="min-h-screen bg-[#050810] text-white p-6">
      <div className="mb-6 flex flex-wrap items-center justify-between border-b border-white/10 pb-4 gap-4">
        <div className="flex items-center gap-4">
          <div className="p-3 rounded-2xl bg-brand/20 border border-brand/30 text-brand-hover">
            <Cpu size={30} />
          </div>
          <div>
            <h1 className="text-3xl font-black italic uppercase tracking-tighter">
              Terminal <span className="text-brand-hover">{STATIONS.find((s) => s.id === station)?.label}</span>
            </h1>
            <p className="text-xs text-slate-500 font-bold uppercase tracking-widest mt-1">
              Stanowiska z desktopu: CNC / Oklejanie / Lakiernia / Montaz / Biuro
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={workerId}
            onChange={(e) => {
              const id = e.target.value;
              setWorkerId(id);
              const match = workers.find((w) => w.worker_id === id);
              setWorkerName(match?.name || "");
            }}
            className="w-72 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-brand/50"
          >
            <option value="">-- Wybierz pracownika --</option>
            {workers.map((w) => (
              <option key={w.worker_id} value={w.worker_id}>
                {w.name} ({w.worker_id}){w.role ? ` - ${w.role}` : ""}
              </option>
            ))}
          </select>
          <span className="text-[10px] text-slate-500 font-black uppercase">Sync: {lastSync || "--:--:--"}</span>
        </div>
      </div>

      <div className="mb-6 flex flex-wrap gap-2">
        {STATIONS.map((s) => (
          <button
            key={s.id}
            onClick={() => setStation(s.id)}
            className={clsx(
              "px-4 py-2 rounded-xl text-xs font-black uppercase tracking-widest border transition",
              station === s.id
                ? "bg-brand text-white border-brand/70 shadow-brand-glow"
                : "bg-white/5 text-slate-400 border-white/10 hover:text-white hover:border-brand/30"
            )}
          >
            {s.label}
          </button>
        ))}
        <button
          onClick={() => setShowAllStations((v) => !v)}
          className={clsx(
            "px-4 py-2 rounded-xl text-xs font-black uppercase tracking-widest border transition",
            showAllStations
              ? "bg-amber-500/20 text-amber-200 border-amber-500/40"
              : "bg-white/5 text-slate-400 border-white/10 hover:text-white hover:border-amber-500/30"
          )}
        >
          {showAllStations ? "Wszystkie stacje: ON" : "Wszystkie stacje: OFF"}
        </button>
        <button
          onClick={() => setMultiStart((v) => !v)}
          className={clsx(
            "px-4 py-2 rounded-xl text-xs font-black uppercase tracking-widest border transition",
            multiStart
              ? "bg-emerald-500/20 text-emerald-200 border-emerald-500/40"
              : "bg-white/5 text-slate-400 border-white/10 hover:text-white hover:border-emerald-500/30"
          )}
        >
          Multi-start: {multiStart ? "ON" : "OFF"}
        </button>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as "active" | "all" | "done")}
          className="px-3 py-2 rounded-xl text-xs font-black uppercase tracking-widest border bg-white/5 text-slate-300 border-white/10"
        >
          <option value="active">Aktywne + Planowane</option>
          <option value="all">Wszystkie statusy</option>
          <option value="done">Tylko zakonczone</option>
        </select>
      </div>

      {error ? (
        <Card className="mb-5 p-3 border-red-500/30 bg-red-500/10 text-red-300 text-sm">{error}</Card>
      ) : null}

      <div className="mb-6">
        <BusinessHealthStrip
          scope={`Produkcja / ${STATIONS.find((s) => s.id === station)?.label || station}`}
          subtitle="Stan firmy z perspektywy hali: ryzyko, materialy oraz koszt godziny pracy i produkcji."
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-4">
          <Card className="p-4 border-amber-400/20 bg-amber-500/5">
            <div className="flex items-start gap-3">
              <Lightbulb className="text-amber-300 mt-0.5" size={18} />
              <div>
                <p className="text-[11px] font-black uppercase tracking-widest text-amber-200 mb-1">
                  Sugestia kolejki ({station.toUpperCase()})
                </p>
                <p className="text-sm text-amber-100/90">{recommendedQueue.advice}</p>
                <p className="text-xs text-amber-300/80 mt-1">
                  Dominujaca grupa: {recommendedQueue.dominantTag}. Operator moze zmienic kolejnosc wg realnego ukadu arkuszy.
                </p>
              </div>
            </div>
          </Card>
          {(station === "cnc" || station === "lakiernia") && (
            <Card className="p-4 border-sky-400/20 bg-sky-500/5">
              <div className="flex items-start gap-3">
                <Lightbulb className="text-sky-300 mt-0.5" size={18} />
                <div className="w-full">
                  <p className="text-[11px] font-black uppercase tracking-widest text-sky-200 mb-1">
                    Plan ciecia / partii (materia + format)
                  </p>
                  <p className="text-sm text-sky-100/90">{sheetPlan.headline}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button
                      disabled={busy || sheetPlan.recommendedTaskIds.size === 0}
                      onClick={() => setSelectedTaskIds(new Set(sheetPlan.recommendedTaskIds))}
                      className="px-4 py-2 rounded-xl bg-sky-500/20 text-sky-100 border border-sky-400/40 hover:bg-sky-500/30 font-black uppercase text-xs"
                    >
                      Zaznacz rekomendowana grupe
                    </Button>
                  </div>
                  <div className="mt-3 space-y-2">
                    {sheetPlan.groups.slice(0, 5).map((group, idx) => (
                      <div key={group.key} className="text-xs rounded-lg border border-white/10 bg-white/5 px-3 py-2 flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <span className="font-black text-white">#{idx + 1} {group.label}</span>
                          {group.lowStock ? <span className="ml-2 text-[10px] uppercase text-amber-300">Niski stan</span> : null}
                        </div>
                        <span className="text-slate-300 font-bold">{group.items.length} zadan</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </Card>
          )}
          {station === "oklejanie" && (
            <Card className="p-4 border-violet-400/20 bg-violet-500/5">
              <div className="flex items-start gap-3">
                <Lightbulb className="text-violet-300 mt-0.5" size={18} />
                <div className="w-full">
                  <p className="text-[11px] font-black uppercase tracking-widest text-violet-200 mb-1">
                    Plan kleju (oklejanie)
                  </p>
                  <p className="text-sm text-violet-100/90">{oklejaniePlan.headline}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button
                      disabled={busy || oklejaniePlan.recommendedTaskIds.size === 0}
                      onClick={() => setSelectedTaskIds(new Set(oklejaniePlan.recommendedTaskIds))}
                      className="px-4 py-2 rounded-xl bg-violet-500/20 text-violet-100 border border-violet-400/40 hover:bg-violet-500/30 font-black uppercase text-xs"
                    >
                      Zaznacz partie: {oklejaniePlan.recommendedGlue}
                    </Button>
                  </div>
                  <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2">
                    <div className="text-xs rounded-lg border border-white/10 bg-white/5 px-3 py-2 flex items-center justify-between gap-3">
                      <span className="font-black text-white">KLEJ BIAY</span>
                      <span className="text-slate-300 font-bold">{oklejaniePlan.groups.BIALY.length} zadan</span>
                    </div>
                    <div className="text-xs rounded-lg border border-white/10 bg-white/5 px-3 py-2 flex items-center justify-between gap-3">
                      <span className="font-black text-white">KLEJ BEZBARWNY</span>
                      <span className="text-slate-300 font-bold">{oklejaniePlan.groups.BEZBARWNY.length} zadan</span>
                    </div>
                  </div>
                  <p className="mt-2 text-[11px] text-violet-200/80">
                    Po zakonczeniu partii {oklejaniePlan.recommendedGlue} przejdz na {oklejaniePlan.nextGlue}.
                  </p>
                </div>
              </div>
            </Card>
          )}

          <div className="flex items-center justify-between">
            <h3 className="text-lg font-black uppercase text-slate-400 italic">Kolejka Zadan</h3>
            <span className="px-3 py-1 rounded-full bg-white/5 text-[10px] font-black text-slate-500">
              Planowane: {queueTasks.length}
            </span>
          </div>

          {loading ? (
            <Card className="p-6 border-white/10 bg-panel-solid/30 text-slate-400 text-sm">Ladowanie zadan...</Card>
          ) : null}

          {!loading && queueTasks.length === 0 ? (
            <Card className="p-6 border-white/10 bg-panel-solid/30 text-slate-400 text-sm">Brak zadan dla tej stacji.</Card>
          ) : null}

          <div className="flex gap-2">
            <Button
              disabled={busy || selectedTaskIds.size === 0 || (!multiStart && activeTasks.length > 0)}
              onClick={handleStartSelected}
              className="px-5 py-3 rounded-xl bg-brand text-white font-black uppercase hover:bg-brand-hover disabled:opacity-50"
            >
              START zaznaczone ({selectedTaskIds.size})
            </Button>
            <Button
              disabled={busy || queueTasks.length === 0}
              onClick={() => {
                if (selectedTaskIds.size === queueTasks.length) {
                  setSelectedTaskIds(new Set());
                } else {
                  setSelectedTaskIds(new Set(queueTasks.map((t) => String(t.id))));
                }
              }}
              className="px-5 py-3 rounded-xl bg-white/10 text-slate-100 font-black uppercase hover:bg-white/20 disabled:opacity-50"
            >
              {selectedTaskIds.size === queueTasks.length ? "Odznacz wszystko" : "Zaznacz wszystko"}
            </Button>
          </div>

          <div className="grid grid-cols-1 gap-3">
            {recommendedQueue.items.map((task) => (
              <Card key={task.id} className="bg-panel-solid/40 border-white/10 p-5 hover:border-brand-hover/40 transition-all">
                <div className="flex items-center gap-5">
                  <input
                    type="checkbox"
                    checked={selectedTaskIds.has(String(task.id))}
                    onChange={() => toggleTaskSelection(String(task.id))}
                    className="h-4 w-4 accent-blue-500"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      <span className="px-2 py-0.5 rounded bg-brand/20 text-brand-hover text-[9px] font-black uppercase">
                        {task.task_type || station}
                      </span>
                      <span className="text-[10px] text-slate-500 font-bold uppercase">ID: {task.id}</span>
                      <span className="text-[10px] text-slate-500 font-bold uppercase">{statusLabel(task.status)}</span>
                      <span className="text-[10px] text-amber-300 font-bold uppercase bg-amber-500/10 px-2 py-0.5 rounded">
                        {detectBatchTag(task)}
                      </span>
                    </div>
                    <h4 className="text-lg font-black text-white truncate">
                      {task.project_name || "Bez projektu"} - {task.client_name || "Bez klienta"}
                    </h4>
                    <div className="flex items-center gap-4 mt-2 text-xs text-slate-400">
                      <div className="flex items-center gap-1">
                        <Clock size={13} className="text-slate-600" />
                        {task.planned_date || "brak daty"}
                      </div>
                      <div className="flex items-center gap-1">
                        <Timer size={13} className="text-slate-600" />
                        {task.estimated_time_minutes || 0} min
                      </div>
                    </div>
                  </div>
                  <Button
                    disabled={busy || !canStartNew}
                    onClick={() => handleStart(task)}
                    className="px-7 py-5 rounded-2xl bg-brand text-white font-black uppercase hover:bg-brand-hover disabled:opacity-50"
                  >
                    START <Play fill="currentColor" size={14} className="ml-2" />
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </div>

        <div className="space-y-6">
          <Card
            className={clsx(
              "p-6 border-2 transition-all",
              activeTasks.length > 0 ? "border-brand-hover bg-brand/5" : "border-white/10 bg-panel-solid/20"
            )}
          >
            {activeTasks.length > 0 ? (
              <>
                <h3 className="text-[10px] font-black text-brand-hover uppercase tracking-[0.2em] mb-3">
                  Aktywne zadania ({activeTasks.length})
                </h3>
                <div className="space-y-2 mb-5">
                  {activeTasks.map((task) => (
                    <div key={task.id} className="rounded-xl border border-white/10 bg-white/5 p-3">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <h2 className="text-sm font-black text-white uppercase tracking-tight">
                            {task.project_name || "Bez projektu"}
                          </h2>
                          <div className="text-xs text-slate-400">
                            Klient: {task.client_name || "brak"} | Typ: {task.task_type || station} | ID: {task.id}
                          </div>
                        </div>
                        <Button
                          disabled={busy}
                          onClick={() => handleFinish(task)}
                          className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-white font-black uppercase text-xs disabled:opacity-50"
                        >
                          ZAKONCZ
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="mb-5 p-4 rounded-2xl bg-canvas-deep border border-brand/20 text-center">
                  <div className="text-[10px] font-black text-slate-600 uppercase mb-1">Czas pracy (najstarsze aktywne)</div>
                  <div className="text-4xl font-black text-white tabular-nums tracking-tighter">{formatDuration(elapsed)}</div>
                </div>

                <div className="space-y-3">
                  <textarea
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="Notatka operatora (opcjonalnie)"
                    rows={3}
                    className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-brand/50"
                  />
                  <textarea
                    value={correctionNote}
                    onChange={(e) => setCorrectionNote(e.target.value)}
                    placeholder="Poprawka / blad (opcjonalnie, utworzy issue)"
                    rows={3}
                    className="w-full rounded-xl border border-red-500/30 bg-red-500/5 px-3 py-2 text-sm text-white outline-none focus:border-red-500/60"
                  />
                  <p className="text-[11px] text-slate-500">
                    Notatki i korekty zostana dopiete do zadania, ktore zakonczysz przyciskiem "ZAKONCZ".
                  </p>
                </div>
              </>
            ) : (
              <div className="py-14 flex flex-col items-center justify-center text-center">
                <Timer size={44} className="text-slate-700 mb-4" />
                <p className="text-slate-500 text-xs font-bold uppercase tracking-widest">Brak aktywnego zadania</p>
              </div>
            )}
          </Card>

          <Card className="p-5 border-white/10 bg-panel-solid/30">
            <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-3">Szybki podglad</h3>
            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between text-slate-300">
                <span className="flex items-center gap-2"><Clock size={13} /> Planowane</span>
                <strong>{queueTasks.length}</strong>
              </div>
              <div className="flex items-center justify-between text-slate-300">
                <span className="flex items-center gap-2"><Play size={13} /> W trakcie</span>
                <strong>{activeTasks.length}</strong>
              </div>
              <div className="flex items-center justify-between text-slate-300">
                <span className="flex items-center gap-2"><CheckCircle2 size={13} /> Gotowe</span>
                <strong>{doneTasksCount}</strong>
              </div>
              <div className="flex items-center justify-between text-amber-300">
                <span className="flex items-center gap-2"><AlertTriangle size={13} /> Korekty</span>
                <strong>{correctionNote.trim() ? "wpisana" : "brak"}</strong>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
