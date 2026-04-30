"use client";

import { useEffect, useMemo, useState, type MouseEvent } from "react";
import dynamic from "next/dynamic";
import clsx from "clsx";
import AppShell from "@/components/AppShell";
import { Button, Card } from "@/components/ui";
import {
  TechModulAPI,
  type MvpReadiness,
  type Obstacle,
  type ProjectModule,
  type WallConfig,
  type WallSummary,
  type WorkspaceSummary,
  type WallPoint,
  type OperationAction,
} from "@/services/api";
import { previewOperation, applyOperation } from "@/services/operations";
import { getPrimaryOperationMessage, mapOperationChangesToPreviewRows } from "@/services/operation-contract";
import OperationPreviewList from "@/components/OperationPreviewList";
import { useSelectedProjectId } from "@/services/project-context";
import {
  AlertCircle,
  ArrowRight,
  Bolt,
  Box,
  Check,
  ChevronLeft,
  ChevronRight,
  DoorOpen,
  Droplet,
  Flame,
  Home,
  Layers,
  Database,
  Loader2,
  Menu,
  MousePointerClick,
  MoveRight,
  Ruler,
  Save,
  SquareStack,
  Trash2,
  TriangleAlert,
  Wrench,
  X,
} from "lucide-react";

type Tool = "bolt" | "droplet" | "flame";
type PendingAction = {
  action: OperationAction;
  params: Record<string, unknown>;
  title: string;
};

const TOOLS: { id: Tool; icon: any; label: string; tag: string; color: string }[] = [
  { id: "bolt", icon: Bolt, label: "Prąd", tag: "230V", color: "bg-blue-500" },
  { id: "droplet", icon: Droplet, label: "Woda", tag: "H2O", color: "bg-cyan-500" },
  { id: "flame", icon: Flame, label: "Gaz", tag: "GAZ", color: "bg-orange-500" },
];

const AgentPanel = dynamic(() => import("@/components/AgentPanel"), { ssr: false });
const WorkspaceRoom3D = dynamic(() => import("@/components/workspace/WorkspaceRoom3D"), { ssr: false });

type WorkspaceObstacleType = "window" | "door" | "column" | "pipe" | "shaft" | "utility" | "socket";

type WorkspaceObstacle = Obstacle & {
  id: string;
  type: WorkspaceObstacleType;
};

type RoomGeometryPreset = "flat" | "left_column" | "center_column" | "double_column";

type RoomGeometryBlock = {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  depth: number;
};

type ModuleWarning = {
  outOfWall: boolean;
  overlap: boolean;
  obstacleIntersections: string[];
};

const OBSTACLE_DEFAULTS: Record<WorkspaceObstacleType, { width: number; height: number; y: number }> = {
  window: { width: 1200, height: 1000, y: 900 },
  door: { width: 900, height: 2100, y: 0 },
  column: { width: 300, height: 2400, y: 0 },
  pipe: { width: 160, height: 2400, y: 0 },
  shaft: { width: 220, height: 2400, y: 0 },
  utility: { width: 120, height: 160, y: 300 },
  socket: { width: 80, height: 80, y: 350 },
};

const OBSTACLE_LABELS: Record<WorkspaceObstacleType, string> = {
  window: "Okno",
  door: "Drzwi",
  column: "Slup",
  pipe: "Rura",
  shaft: "Szyb",
  utility: "Utility",
  socket: "Gniazdo",
};

const OBSTACLE_FILL: Record<WorkspaceObstacleType, string> = {
  window: "#8ec5ff",
  door: "#cf4f42",
  column: "#e9b27b",
  pipe: "#fde68a",
  shaft: "#f4c46d",
  utility: "#cbd5e1",
  socket: "#e2e8f0",
};

const ROOM_PRESET_LABELS: Record<RoomGeometryPreset, string> = {
  flat: "Sciana prosta",
  left_column: "Lewa kolumna",
  center_column: "Srodkowa kolumna",
  double_column: "Dwie kolumny",
};

const SCENE = {
  viewWidth: 1280,
  viewHeight: 860,
  wallLeft: 270,
  wallTop: 88,
  wallWidth: 740,
  wallHeight: 430,
  sideInset: 110,
  floorDepth: 220,
};

const TOP_SCENE = {
  left: 230,
  top: 150,
  width: 820,
  depth: 310,
};

function asNumber(value: unknown, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function rectIntersects(
  a: { x: number; y: number; width: number; height: number },
  b: { x: number; y: number; width: number; height: number }
): boolean {
  return a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y;
}

function moduleName(module: ProjectModule): string {
  const fallback = `Modul ${module.id}`;
  const raw = String((module as any).name || (module as any).module_name || "").trim();
  return raw || fallback;
}

function resolveModuleMountType(module: ProjectModule): "floor" | "wall" {
  const cabinetType = String((module as any).cabinet_type || "").trim().toLowerCase();
  if (cabinetType === "wall" || cabinetType === "corner_wall") return "wall";
  if (cabinetType === "base" || cabinetType === "tall" || cabinetType === "corner_base") return "floor";

  const family = String((module as any).module_family || "").trim().toLowerCase();
  if (family.includes("wall") || family.includes("upper") || family.includes("hanging") || family.includes("overhead")) {
    return "wall";
  }
  return "floor";
}

function obstacleLabel(obstacle: WorkspaceObstacle): string {
  return `${OBSTACLE_LABELS[obstacle.type] ?? obstacle.type} (${obstacle.id})`;
}

function normalizeObstacle(raw: any, index: number): WorkspaceObstacle {
  const typeRaw = String(raw?.type || raw?.kind || "utility").trim().toLowerCase() as WorkspaceObstacleType;
  const type = (
    ["window", "door", "column", "pipe", "shaft", "utility", "socket"].includes(typeRaw) ? typeRaw : "utility"
  ) as WorkspaceObstacleType;

  return {
    id: String(raw?.id || `${type}_${index + 1}`),
    type,
    x: asNumber(raw?.x, 0),
    y: asNumber(raw?.y, 0),
    width: Math.max(1, asNumber(raw?.width, OBSTACLE_DEFAULTS[type].width)),
    height: Math.max(1, asNumber(raw?.height, OBSTACLE_DEFAULTS[type].height)),
    depth: Math.max(0, asNumber(raw?.depth, 0)),
  };
}

function buildRoomGeometryBlocks(
  preset: RoomGeometryPreset,
  wallWidth: number,
  wallHeight: number
): RoomGeometryBlock[] {
  const fullHeight = Math.max(1000, wallHeight);
  const standardDepth = 260;

  if (preset === "left_column") {
    const width = Math.round(wallWidth * 0.14);
    return [
      {
        id: "room_left_column",
        x: Math.round(wallWidth * 0.08),
        y: 0,
        width,
        height: fullHeight,
        depth: standardDepth,
      },
    ];
  }

  if (preset === "center_column") {
    const width = Math.round(wallWidth * 0.16);
    return [
      {
        id: "room_center_column",
        x: Math.round((wallWidth - width) * 0.5),
        y: 0,
        width,
        height: fullHeight,
        depth: standardDepth,
      },
    ];
  }

  if (preset === "double_column") {
    const width = Math.round(wallWidth * 0.12);
    return [
      {
        id: "room_left_column",
        x: Math.round(wallWidth * 0.16),
        y: 0,
        width,
        height: fullHeight,
        depth: standardDepth,
      },
      {
        id: "room_right_column",
        x: Math.round(wallWidth * 0.72),
        y: 0,
        width,
        height: fullHeight,
        depth: standardDepth,
      },
    ];
  }

  return [];
}

function isPointInFrontWall(sceneX: number, sceneY: number) {
  return (
    sceneX >= SCENE.wallLeft &&
    sceneX <= SCENE.wallLeft + SCENE.wallWidth &&
    sceneY >= SCENE.wallTop &&
    sceneY <= SCENE.wallTop + SCENE.wallHeight
  );
}

export default function WorkspacePage() {
  const [projectId] = useSelectedProjectId(1);
  const [summary, setSummary] = useState<WorkspaceSummary | null>(null);
  const [wallSummary, setWallSummary] = useState<WallSummary | null>(null);
  const [mvpReadiness, setMvpReadiness] = useState<MvpReadiness | null>(null);
  const [wallConfig, setWallConfig] = useState<WallConfig | null>(null);
  const [modules, setModules] = useState<ProjectModule[]>([]);
  const [obstacles, setObstacles] = useState<WorkspaceObstacle[]>([]);
  const [selectedModuleId, setSelectedModuleId] = useState("");
  const [selectedObstacleId, setSelectedObstacleId] = useState("");
  const [moduleToPlaceId, setModuleToPlaceId] = useState("");
  const [newObstacleType, setNewObstacleType] = useState<WorkspaceObstacleType>("window");
  const [modulePosX, setModulePosX] = useState(0);
  const [modulePosY, setModulePosY] = useState(0);
  const [roomWidthInput, setRoomWidthInput] = useState(3250);
  const [roomHeightInput, setRoomHeightInput] = useState(2500);
  const [roomDepthInput, setRoomDepthInput] = useState(3200);
  const [roomGeometryPreset, setRoomGeometryPreset] = useState<RoomGeometryPreset>("flat");
  const [leftPanelMode, setLeftPanelMode] = useState<"room" | "obstacles" | "modules" | "connections" | "warnings" | "komplet" | "struktura">("room");
  const [sceneView, setSceneView] = useState<"3d" | "front" | "top">("3d");
  const [leftPanelOpen, setLeftPanelOpen] = useState(true);
  const [rightPanelOpen, setRightPanelOpen] = useState(true);
  const [loading, setLoading] = useState(true);
  const [savingObstacles, setSavingObstacles] = useState(false);
  const [savingRoomConfig, setSavingRoomConfig] = useState(false);
  const [updatingModule, setUpdatingModule] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Read ?mode= from URL to support deep-links and redirects
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const mode = params.get("mode");
    const validModes = ["room", "obstacles", "modules", "connections", "warnings", "komplet", "struktura"] as const;
    if (mode && (validModes as readonly string[]).includes(mode)) {
      setLeftPanelMode(mode as typeof leftPanelMode);
    }
  }, []);

  // Connections state
  const [points, setPoints] = useState<WallPoint[]>([]);
  const [activeTool, setActiveTool] = useState<Tool>("bolt");
  const [busy, setBusy] = useState<"preview" | "apply" | null>(null);
  const [previewRows, setPreviewRows] = useState<
    Array<{ key: string; name?: string; label: string; before: string; after: string; unit?: string }>
  >([]);
  const [previewWarnings, setPreviewWarnings] = useState<string[]>([]);
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);

  const activeToolData = useMemo(() => TOOLS.find((t) => t.id === activeTool)!, [activeTool]);
  const wallName = useMemo(() => wallConfig?.wall_name ?? `WEB_PROJECT_${projectId}`, [projectId, wallConfig?.wall_name]);

  const wallWidth = Math.max(
    1000,
    Math.round(roomWidthInput > 0 ? roomWidthInput : asNumber(wallConfig?.width, 3250))
  );
  const wallHeight = Math.max(
    1000,
    Math.round(roomHeightInput > 0 ? roomHeightInput : asNumber(wallConfig?.height, 2500))
  );
  const roomDepth = Math.max(
    1200,
    Math.round(
      roomDepthInput > 0
        ? roomDepthInput
        : asNumber(wallConfig?.room_depth, Math.max(1800, Math.round(wallWidth * 0.78)))
    )
  );
  const wallScaleX = SCENE.wallWidth / wallWidth;
  const wallScaleY = SCENE.wallHeight / wallHeight;
  const roomGeometryBlocks = useMemo(
    () => buildRoomGeometryBlocks(roomGeometryPreset, wallWidth, wallHeight),
    [roomGeometryPreset, wallWidth, wallHeight]
  );

  const moduleRows = useMemo(
    () =>
      modules.map((module) => {
        const mountType = resolveModuleMountType(module);
        const rawY = asNumber((module as any).y, 0);
        return {
          module,
          id: String(module.id),
          name: moduleName(module),
          mountType,
          x: asNumber((module as any).x, 0),
          y: mountType === "floor" ? 0 : rawY,
          width: Math.max(1, asNumber(module.width, 600)),
          height: Math.max(1, asNumber(module.height, 720)),
        };
      }),
    [modules]
  );

  const moduleWarnings = useMemo(() => {
    const warnings = new Map<string, ModuleWarning>();
    for (const row of moduleRows) {
      warnings.set(row.id, { outOfWall: false, overlap: false, obstacleIntersections: [] });
    }

    for (const row of moduleRows) {
      const rect = { x: row.x, y: row.y, width: row.width, height: row.height };
      const warning = warnings.get(row.id);
      if (!warning) continue;

      if (row.x < 0 || row.y < 0 || row.x + row.width > wallWidth || row.y + row.height > wallHeight) {
        warning.outOfWall = true;
      }

      for (const obstacle of obstacles) {
        const obstacleRect = { x: obstacle.x, y: obstacle.y, width: obstacle.width, height: obstacle.height };
        if (rectIntersects(rect, obstacleRect)) {
          warning.obstacleIntersections.push(obstacle.id);
        }
      }

      for (const block of roomGeometryBlocks) {
        const obstacleRect = { x: block.x, y: block.y, width: block.width, height: block.height };
        if (rectIntersects(rect, obstacleRect)) {
          warning.obstacleIntersections.push(block.id);
        }
      }
    }

    for (let i = 0; i < moduleRows.length; i += 1) {
      for (let j = i + 1; j < moduleRows.length; j += 1) {
        const left = moduleRows[i];
        const right = moduleRows[j];
        if (
          rectIntersects(
            { x: left.x, y: left.y, width: left.width, height: left.height },
            { x: right.x, y: right.y, width: right.width, height: right.height }
          )
        ) {
          const leftWarning = warnings.get(left.id);
          const rightWarning = warnings.get(right.id);
          if (leftWarning) leftWarning.overlap = true;
          if (rightWarning) rightWarning.overlap = true;
        }
      }
    }

    return warnings;
  }, [moduleRows, obstacles, roomGeometryBlocks, wallWidth, wallHeight]);

  const obstacleWarnings = useMemo(() => {
    const out = new Map<string, { outOfWall: boolean }>();
    for (const obstacle of obstacles) {
      out.set(obstacle.id, {
        outOfWall:
          obstacle.x < 0 ||
          obstacle.y < 0 ||
          obstacle.x + obstacle.width > wallWidth ||
          obstacle.y + obstacle.height > wallHeight,
      });
    }
    return out;
  }, [obstacles, wallWidth, wallHeight]);

  const selectedModule = useMemo(
    () => moduleRows.find((row) => row.id === selectedModuleId) ?? null,
    [moduleRows, selectedModuleId]
  );

  const selectedObstacle = useMemo(
    () => obstacles.find((obstacle) => obstacle.id === selectedObstacleId) ?? null,
    [obstacles, selectedObstacleId]
  );

  const selectedModuleWarning = selectedModule ? moduleWarnings.get(selectedModule.id) ?? null : null;

  const obstacleIntersections = useMemo(() => {
    const out = new Map<string, string[]>();
    for (const obstacle of obstacles) out.set(obstacle.id, []);

    for (const row of moduleRows) {
      const warning = moduleWarnings.get(row.id);
      if (!warning) continue;
      for (const obstacleId of warning.obstacleIntersections) {
        const existing = out.get(obstacleId) ?? [];
        if (!existing.includes(row.id)) existing.push(row.id);
        out.set(obstacleId, existing);
      }
    }

    return out;
  }, [moduleRows, moduleWarnings, obstacles]);

  const selectedObstacleIntersectingModules = useMemo(
    () =>
      selectedObstacle
        ? (obstacleIntersections.get(selectedObstacle.id) ?? [])
            .map((moduleId) => moduleRows.find((row) => row.id === moduleId))
            .filter((row): row is NonNullable<typeof row> => !!row)
        : [],
    [selectedObstacle, obstacleIntersections, moduleRows]
  );

  const warningSummary = useMemo(() => {
    let modulesOutOfWall = 0;
    let modulesOverlap = 0;
    let modulesObstacleIntersection = 0;
    let modulesWithAnyWarning = 0;
    let obstaclesOutOfWall = 0;

    for (const warning of Array.from(moduleWarnings.values())) {
      const hasObstacle = warning.obstacleIntersections.length > 0;
      if (warning.outOfWall) modulesOutOfWall += 1;
      if (warning.overlap) modulesOverlap += 1;
      if (hasObstacle) modulesObstacleIntersection += 1;
      if (warning.outOfWall || warning.overlap || hasObstacle) modulesWithAnyWarning += 1;
    }

    for (const warning of Array.from(obstacleWarnings.values())) {
      if (warning.outOfWall) obstaclesOutOfWall += 1;
    }

    return {
      modulesOutOfWall,
      modulesOverlap,
      modulesObstacleIntersection,
      modulesWithAnyWarning,
      obstaclesOutOfWall,
    };
  }, [moduleWarnings, obstacleWarnings]);

  const plannerSteps = useMemo(
    () => [
      { label: "Ustaw kontekst ściany", done: !!wallConfig },
      { label: "Dodaj przeszkody", done: obstacles.length > 0 },
      { label: "Dodaj moduły", done: moduleRows.length > 0 },
      {
        label: "Rozwiąż ostrzeżenia",
        done: warningSummary.modulesWithAnyWarning === 0 && warningSummary.obstaclesOutOfWall === 0,
      },
    ],
    [wallConfig, obstacles.length, moduleRows.length, warningSummary]
  );

  const workspaceGridClass = useMemo(() => {
    if (leftPanelOpen && rightPanelOpen) return "xl:grid-cols-[280px_minmax(0,1fr)_300px]";
    if (leftPanelOpen && !rightPanelOpen) return "xl:grid-cols-[280px_minmax(0,1fr)_54px]";
    if (!leftPanelOpen && rightPanelOpen) return "xl:grid-cols-[54px_minmax(0,1fr)_300px]";
    return "xl:grid-cols-[54px_minmax(0,1fr)_54px]";
  }, [leftPanelOpen, rightPanelOpen]);

  const sceneHint = useMemo(() => {
    if (sceneView === "top") return "Top: szybki uklad i odczyt pozycji wzgledem sciany.";
    if (sceneView === "front") return "Front: czysty widok elewacji sciany i wysokosci.";
    return "3D: glowny widok roboczy, najblizszy pracy jak w Proboard.";
  }, [sceneView]);

  const getAnchoredModuleY = (row: (typeof moduleRows)[number], requestedY: number): number => {
    if (row.mountType === "floor") return 0;
    return Math.round(clamp(requestedY, 0, Math.max(0, wallHeight - row.height)));
  };

  useEffect(() => {
    if (!selectedModule) return;
    setModulePosX(selectedModule.x);
    setModulePosY(getAnchoredModuleY(selectedModule, selectedModule.y));
  }, [selectedModule?.id, selectedModule?.x, selectedModule?.y, selectedModule?.mountType, wallHeight]);

  useEffect(() => {
    let active = true;

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [workspaceData, wallData, readinessData, modulesData, obstaclesData, configData] = await Promise.all([
          TechModulAPI.getProjectWorkspaceSummary(projectId),
          TechModulAPI.getProjectWallSummary(projectId),
          TechModulAPI.getProjectMvpReadiness(projectId),
          TechModulAPI.getProjectModules(projectId),
          TechModulAPI.getProjectObstacles(projectId),
          TechModulAPI.getWallConfig(projectId),
        ]);

        if (!active) return;

        const nextModules = Array.isArray(modulesData) ? modulesData : [];
        const nextObstacles = Array.isArray(obstaclesData)
          ? obstaclesData.map((item, index) => normalizeObstacle(item, index))
          : [];

        setSummary(workspaceData);
        setWallSummary(wallData);
        setMvpReadiness(readinessData);
        setWallConfig(configData);
        setRoomWidthInput(Math.max(1000, Math.round(asNumber(configData?.width, 3250))));
        setRoomHeightInput(Math.max(1000, Math.round(asNumber(configData?.height, 2500))));
        setRoomDepthInput(
          Math.max(1200, Math.round(asNumber(configData?.room_depth, Math.max(1800, Math.round(asNumber(configData?.width, 3250) * 0.78)))))
        );
        setModules(nextModules);
        setObstacles(nextObstacles);

        if (nextModules.length > 0) {
          setSelectedModuleId((prev) => prev || String(nextModules[0].id));
          setModuleToPlaceId((prev) => prev || String(nextModules[0].id));
        } else {
          setSelectedModuleId("");
          setModuleToPlaceId("");
        }
      } catch (e: any) {
        if (!active) return;
        setError(e?.message ?? "Blad pobierania danych workspace");
      } finally {
        if (active) setLoading(false);
      }
    };

    load();
    return () => {
      active = false;
    };
  }, [projectId]);

  const loadPoints = async () => {
    try {
      const wall = await TechModulAPI.getWallPoints(wallName);
      setPoints(wall.points ?? []);
    } catch (e: any) {
      setPoints([]);
    }
  };

  useEffect(() => {
    loadPoints();
  }, [wallName]);

  const buildAddPreview = async (x: number, y: number) => {
    setBusy("preview");
    setError(null);
    try {
      const params = { point_type: activeTool, x_mm: x, y_mm: y };
      const preview = await previewOperation({
        action: "wall.add_point",
        target: { name: wallName },
        params,
        source: "wall_page",
      });
      if (preview.status !== "ok" || !preview.can_apply) {
        throw new Error(getPrimaryOperationMessage(preview, "Podglad operacji jest niedostepny"));
      }

      setPreviewWarnings(preview.warnings ?? []);
      setPreviewRows(mapOperationChangesToPreviewRows(preview.changes ?? [], { fallbackName: "Sciana" }));
      setPendingAction({ action: "wall.add_point", params, title: "Podglad dodania punktu" });
    } catch (e: any) {
      setError(e?.message ?? "Blad podgladu");
      setPendingAction(null);
      setPreviewRows([]);
      setPreviewWarnings([]);
    } finally {
      setBusy(null);
    }
  };

  const buildRemovePreview = async (pointId: string) => {
    setBusy("preview");
    setError(null);
    try {
      const params = { point_id: pointId };
      const preview = await previewOperation({
        action: "wall.remove_point",
        target: { name: wallName },
        params,
        source: "wall_page",
      });
      if (preview.status !== "ok" || !preview.can_apply) {
        throw new Error(getPrimaryOperationMessage(preview, "Podglad operacji jest niedostepny"));
      }

      setPreviewWarnings(preview.warnings ?? []);
      setPreviewRows(mapOperationChangesToPreviewRows(preview.changes ?? [], { fallbackName: "Sciana" }));
      setPendingAction({ action: "wall.remove_point", params, title: "Podglad usuniecia punktu" });
    } catch (e: any) {
      setError(e?.message ?? "Blad podgladu");
      setPendingAction(null);
      setPreviewRows([]);
      setPreviewWarnings([]);
    } finally {
      setBusy(null);
    }
  };

  const applyPending = async () => {
    if (!pendingAction) return;
    setBusy("apply");
    setError(null);
    try {
      const applied = await applyOperation({
        action: pendingAction.action,
        target: { name: wallName },
        params: pendingAction.params,
        source: "wall_page",
      });
      if (applied.status !== "ok") {
        throw new Error(getPrimaryOperationMessage(applied, "Nie udalo sie zastosowac operacji"));
      }
      setPendingAction(null);
      setPreviewRows([]);
      setPreviewWarnings([]);
      await loadPoints();
    } catch (e: any) {
      setError(e?.message ?? "Blad zapisu");
    } finally {
      setBusy(null);
    }
  };

  const cancelPending = () => {
    setPendingAction(null);
    setPreviewRows([]);
    setPreviewWarnings([]);
  };

  const saveObstacles = async () => {
    setSavingObstacles(true);
    setError(null);
    try {
      await TechModulAPI.updateProjectObstacles(projectId, obstacles);
    } catch (e: any) {
      setError(e?.message ?? "Nie udalo sie zapisac przeszkod");
    } finally {
      setSavingObstacles(false);
    }
  };

  const saveRoomConfig = async () => {
    setSavingRoomConfig(true);
    setError(null);
    try {
      const response = await TechModulAPI.updateWallConfig(projectId, {
        width: wallWidth,
        height: wallHeight,
        room_depth: roomDepth,
      });
      setWallConfig(response);
      setRoomWidthInput(Math.max(1000, Math.round(asNumber(response?.width, wallWidth))));
      setRoomHeightInput(Math.max(1000, Math.round(asNumber(response?.height, wallHeight))));
      setRoomDepthInput(Math.max(1200, Math.round(asNumber(response?.room_depth, roomDepth))));
    } catch (e: any) {
      setError(e?.message ?? "Nie udalo sie zapisac wymiarow pokoju");
    } finally {
      setSavingRoomConfig(false);
    }
  };

  const addObstacle = () => {
    const defaults = OBSTACLE_DEFAULTS[newObstacleType];
    const next: WorkspaceObstacle = {
      id: `obs_${Date.now().toString(36)}`,
      type: newObstacleType,
      x: Math.max(0, Math.round((wallWidth - defaults.width) * 0.5)),
      y: defaults.y,
      width: defaults.width,
      height: defaults.height,
      depth: 0,
    };
    setObstacles((prev) => [...prev, next]);
    setSelectedObstacleId(next.id);
    setSelectedModuleId("");
    setLeftPanelMode("obstacles");
  };

  const updateSelectedObstacle = (field: keyof WorkspaceObstacle, value: number | string) => {
    if (!selectedObstacleId) return;
    setObstacles((prev) =>
      prev.map((item) =>
        item.id === selectedObstacleId
          ? {
              ...item,
              [field]:
                field === "type" || field === "id"
                  ? String(value)
                  : Math.max(0, Number(value)),
            }
          : item
      )
    );
  };

  const removeSelectedObstacle = () => {
    if (!selectedObstacleId) return;
    setObstacles((prev) => prev.filter((item) => item.id !== selectedObstacleId));
    setSelectedObstacleId("");
  };

  const clampSelectedObstacleToWall = () => {
    if (!selectedObstacle) return;
    updateSelectedObstacle("x", Math.round(clamp(selectedObstacle.x, 0, Math.max(0, wallWidth - selectedObstacle.width))));
    updateSelectedObstacle("y", Math.round(clamp(selectedObstacle.y, 0, Math.max(0, wallHeight - selectedObstacle.height))));
  };

  const applySelectedModulePlacement = async () => {
    if (!selectedModule) return;
    const nextX = Math.round(clamp(modulePosX, 0, Math.max(0, wallWidth - selectedModule.width)));
    const nextY = getAnchoredModuleY(selectedModule, modulePosY);
    setUpdatingModule(true);
    setError(null);
    try {
      await TechModulAPI.updateProjectModulePlacement(projectId, selectedModule.id, {
        x_mm: nextX,
        y_mm: nextY,
      });
      setModules((prev) =>
        prev.map((item) =>
          String(item.id) === selectedModule.id ? { ...item, x: nextX, y: nextY } : item
        )
      );
      setModulePosX(nextX);
      setModulePosY(nextY);
    } catch (e: any) {
      setError(e?.message ?? "Nie udalo sie ustawic polozenia modulu");
    } finally {
      setUpdatingModule(false);
    }
  };

  const clampSelectedModuleToWall = () => {
    if (!selectedModule) return;
    setModulePosX(Math.round(clamp(modulePosX, 0, Math.max(0, wallWidth - selectedModule.width))));
    setModulePosY(getAnchoredModuleY(selectedModule, modulePosY));
  };

  const spreadSelectedModuleFromOverlap = () => {
    if (!selectedModule) return;
    const maxX = Math.max(0, wallWidth - selectedModule.width);
    let nextX = clamp(modulePosX, 0, maxX);
    const nextY = getAnchoredModuleY(selectedModule, modulePosY);
    const currentRect = () => ({ x: nextX, y: nextY, width: selectedModule.width, height: selectedModule.height });

    for (let guard = 0; guard < moduleRows.length + 2; guard += 1) {
      const overlapping = moduleRows.filter((row) => {
        if (row.id === selectedModule.id) return false;
        return rectIntersects(currentRect(), { x: row.x, y: row.y, width: row.width, height: row.height });
      });
      if (overlapping.length === 0) break;
      const rightEdge = Math.max(...overlapping.map((row) => row.x + row.width));
      const candidate = clamp(rightEdge + 40, 0, maxX);
      if (candidate <= nextX + 0.5) break;
      nextX = candidate;
    }

    setModulePosX(Math.round(nextX));
    setModulePosY(getAnchoredModuleY(selectedModule, nextY));
  };

  const nudgeSelectedModuleX = (delta: number) => {
    if (!selectedModule) return;
    setModulePosX(Math.round(clamp(modulePosX + delta, 0, Math.max(0, wallWidth - selectedModule.width))));
  };

  const alignSelectedModuleX = (side: "start" | "end") => {
    if (!selectedModule) return;
    setModulePosX(side === "start" ? 0 : Math.max(0, wallWidth - selectedModule.width));
  };

  const addExistingModuleToWall = async () => {
    if (!moduleToPlaceId) return;
    const candidate = moduleRows.find((item) => item.id === moduleToPlaceId);
    if (!candidate) return;
    const maxRight = moduleRows.reduce((acc, row) => Math.max(acc, row.x + row.width), 0);
    const nextX = Math.max(0, Math.min(wallWidth - candidate.width, maxRight + 40));
    const nextY = candidate.mountType === "floor"
      ? 0
      : Math.round(clamp(wallHeight * 0.58, 0, Math.max(0, wallHeight - candidate.height)));
    setUpdatingModule(true);
    setError(null);
    try {
      await TechModulAPI.updateProjectModulePlacement(projectId, candidate.id, { x_mm: nextX, y_mm: nextY });
      setModules((prev) =>
        prev.map((item) => (String(item.id) === candidate.id ? { ...item, x: nextX, y: nextY } : item))
      );
      setSelectedModuleId(candidate.id);
      setModulePosX(nextX);
      setModulePosY(nextY);
      setSelectedObstacleId("");
      setLeftPanelMode("modules");
    } catch (e: any) {
      setError(e?.message ?? "Nie udalo sie dodac modulu do sciany");
    } finally {
      setUpdatingModule(false);
    }
  };

  const applyWallPlacementFromScene = (xFromLeft: number, yFromBottom: number) => {
    if (leftPanelMode === "connections") {
      buildAddPreview(Math.round(xFromLeft), Math.round(yFromBottom));
      return;
    }

    if (selectedModule) {
      setModulePosX(
        Math.round(clamp(xFromLeft - selectedModule.width * 0.5, 0, Math.max(0, wallWidth - selectedModule.width)))
      );
      const requestedY = yFromBottom - selectedModule.height * 0.5;
      setModulePosY(getAnchoredModuleY(selectedModule, requestedY));
      return;
    }

    if (selectedObstacle) {
      updateSelectedObstacle(
        "x",
        Math.round(clamp(xFromLeft - selectedObstacle.width * 0.5, 0, Math.max(0, wallWidth - selectedObstacle.width)))
      );
      updateSelectedObstacle(
        "y",
        Math.round(
          clamp(yFromBottom - selectedObstacle.height * 0.5, 0, Math.max(0, wallHeight - selectedObstacle.height))
        )
      );
    }
  };

  const onSceneClick = (event: MouseEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return;

    if (sceneView === "top") {
      const sceneX = ((event.clientX - rect.left) / rect.width) * SCENE.viewWidth;
      const sceneY = ((event.clientY - rect.top) / rect.height) * SCENE.viewHeight;

      if (
        sceneX < TOP_SCENE.left ||
        sceneX > TOP_SCENE.left + TOP_SCENE.width ||
        sceneY < TOP_SCENE.top ||
        sceneY > TOP_SCENE.top + TOP_SCENE.depth
      ) {
        setSelectedModuleId("");
        setSelectedObstacleId("");
        return;
      }

      const xFromLeft = ((sceneX - TOP_SCENE.left) / TOP_SCENE.width) * wallWidth;
      applyWallPlacementFromScene(xFromLeft, selectedModule ? modulePosY + selectedModule.height * 0.5 : selectedObstacle ? selectedObstacle.y + selectedObstacle.height * 0.5 : 0);
      return;
    }

    const sceneX = ((event.clientX - rect.left) / rect.width) * SCENE.viewWidth;
    const sceneY = ((event.clientY - rect.top) / rect.height) * SCENE.viewHeight;

    if (!isPointInFrontWall(sceneX, sceneY)) {
      setSelectedModuleId("");
      setSelectedObstacleId("");
      return;
    }

    const xFromLeft = ((sceneX - SCENE.wallLeft) / SCENE.wallWidth) * wallWidth;
    const yFromTop = ((sceneY - SCENE.wallTop) / SCENE.wallHeight) * wallHeight;
    const yFromBottom = wallHeight - yFromTop;
    applyWallPlacementFromScene(xFromLeft, yFromBottom);
  };

  return (
    <AppShell>
      {error ? (
        <Card className="mb-4 border-red-500/30 bg-red-500/10">
          <div className="flex items-center gap-2 text-sm text-red-200">
            <AlertCircle className="h-4 w-4" />
            <span>{error}</span>
          </div>
        </Card>
      ) : null}

      <div className="mb-4 flex items-center justify-between gap-4 rounded-[22px] border border-white/10 bg-[#11161d]/90 px-5 py-4 shadow-2xl">
        <div>
          <div className="mb-2 flex items-center gap-2">
            <button
              onClick={() => setLeftPanelOpen((prev) => !prev)}
              className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-white/20 bg-white/5 text-white transition hover:bg-white/10"
              aria-label={leftPanelOpen ? "Schowaj lewy panel" : "Pokaz lewy panel"}
              title={leftPanelOpen ? "Schowaj lewy panel" : "Pokaz lewy panel"}
            >
              <Menu className="h-4 w-4" />
            </button>
            <button
              onClick={() => setRightPanelOpen((prev) => !prev)}
              className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-white/20 bg-white/5 text-white transition hover:bg-white/10"
              aria-label={rightPanelOpen ? "Schowaj prawy panel" : "Pokaz prawy panel"}
              title={rightPanelOpen ? "Schowaj prawy panel" : "Pokaz prawy panel"}
            >
              <SquareStack className="h-4 w-4" />
            </button>
          </div>
          <div className="text-[11px] uppercase tracking-[0.24em] text-sky-200/60">Planowanie ściany</div>
          <h1 className="mt-1 text-2xl font-semibold text-white">
            {summary?.project_title || `Projekt ${projectId}`} / {wallConfig?.wall_name ?? `WEB_PROJECT_${projectId}`}
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Widoczny planner MVP: boczne panele, room-stage, przeszkody i moduly na tej samej scenie.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3 text-right">
            <div className="text-[11px] uppercase tracking-[0.2em] text-cyan-100/70">Rozmiar ściany</div>
            <div className="mt-1 text-lg font-semibold text-white">
              {wallWidth} x {wallHeight} mm
            </div>
          </div>
          <Button
            as="link"
            href={selectedModuleId ? `/configuration?module_id=${encodeURIComponent(selectedModuleId)}` : "/configuration"}
            variant="secondary"
          >
            Otwórz aktywny moduł <ArrowRight className="h-4 w-4" />
          </Button>
          <Button onClick={saveObstacles} disabled={savingObstacles}>
            {savingObstacles ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            Zapisz układ ściany
          </Button>
        </div>
      </div>

      <div className={clsx("grid min-h-[760px] grid-cols-1 gap-4", workspaceGridClass)}>
        {leftPanelOpen ? (
        <aside className="overflow-hidden rounded-[26px] border border-[#467cad]/30 bg-[linear-gradient(180deg,#3177a8_0%,#204f73_35%,#163f60_100%)] text-white shadow-2xl">
          <div className="border-b border-white/10 px-5 py-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-[11px] uppercase tracking-[0.22em] text-white/55">Narzędzia</div>
                <h2 className="mt-2 text-2xl font-semibold">POKÓJ</h2>
              </div>
              <button
                onClick={() => setLeftPanelOpen(false)}
                className="rounded-xl border border-white/15 bg-black/10 p-2 text-white/80 transition hover:bg-white/10 hover:text-white"
                aria-label="Schowaj lewy panel"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
            </div>
          </div>

          <div className="border-b border-white/10 px-3 py-3">
            <div className="grid grid-cols-7 gap-2">
              {[
                { key: "room", label: "Pokój", icon: Home },
                { key: "obstacles", label: "Obiekty", icon: DoorOpen },
                { key: "modules", label: "Moduły", icon: Box },
                { key: "connections", label: "Przyłącza", icon: Bolt },
                { key: "komplet", label: "Komplet", icon: Layers },
                { key: "struktura", label: "Struktura", icon: Database },
                { key: "warnings", label: "Ostrzeżenia", icon: TriangleAlert },
              ].map((item) => {
                const Icon = item.icon;
                const active = leftPanelMode === item.key;
                return (
                  <button
                    key={item.key}
                    onClick={() => setLeftPanelMode(item.key as typeof leftPanelMode)}
                    className={clsx(
                      "rounded-2xl border px-2 py-3 text-center transition-all",
                      active
                        ? "border-white/30 bg-white/18 text-white shadow-lg"
                        : "border-white/10 bg-black/10 text-white/72 hover:bg-white/10"
                    )}
                  >
                    <Icon className="mx-auto mb-2 h-4 w-4" />
                    <div className="text-[11px] font-medium">{item.label}</div>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="max-h-[620px] space-y-4 overflow-auto px-5 py-5 text-sm">
            {leftPanelMode === "room" ? (
              <>
                <div className="space-y-2">
                  <div className="text-xs uppercase tracking-[0.18em] text-white/55">Pomieszczenie</div>
                  <div className="overflow-hidden rounded-2xl border border-white/15 bg-white/10">
                    <button
                      className="flex w-full items-center justify-between border-b border-white/10 px-4 py-3 text-left text-sm hover:bg-white/10"
                      onClick={() => setLeftPanelMode("room")}
                    >
                      <span>Rozmiar pokoju</span>
                      <ChevronRight className="h-4 w-4 text-white/70" />
                    </button>
                    <button
                      className="flex w-full items-center justify-between border-b border-white/10 px-4 py-3 text-left text-sm hover:bg-white/10"
                      onClick={() => setLeftPanelMode("room")}
                    >
                      <span>Ściany i kolumny</span>
                      <ChevronRight className="h-4 w-4 text-white/70" />
                    </button>
                    <button
                      className="flex w-full items-center justify-between border-b border-white/10 px-4 py-3 text-left text-sm hover:bg-white/10"
                      onClick={() => {
                        setNewObstacleType("window");
                        setLeftPanelMode("obstacles");
                      }}
                    >
                      <span>Drzwi i okna</span>
                      <ChevronRight className="h-4 w-4 text-white/70" />
                    </button>
                    <button
                      className="flex w-full items-center justify-between px-4 py-3 text-left text-sm hover:bg-white/10"
                      onClick={() => {
                        setNewObstacleType("utility");
                        setLeftPanelMode("obstacles");
                      }}
                    >
                      <span>Instalacje</span>
                      <ChevronRight className="h-4 w-4 text-white/70" />
                    </button>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="text-xs uppercase tracking-[0.18em] text-white/55">Wymiary pokoju</div>
                  <div className="grid grid-cols-1 gap-2 rounded-2xl bg-white/10 p-3">
                    <label className="text-[11px] uppercase tracking-[0.14em] text-white/60">Szerokość (X) mm</label>
                    <input
                      className="input-base bg-white/95 text-slate-900"
                      type="number"
                      min={1000}
                      step={10}
                      value={Math.round(roomWidthInput)}
                      onChange={(event) => setRoomWidthInput(Math.max(0, Number(event.target.value) || 0))}
                    />
                    <label className="text-[11px] uppercase tracking-[0.14em] text-white/60">Wysokość (Y) mm</label>
                    <input
                      className="input-base bg-white/95 text-slate-900"
                      type="number"
                      min={1000}
                      step={10}
                      value={Math.round(roomHeightInput)}
                      onChange={(event) => setRoomHeightInput(Math.max(0, Number(event.target.value) || 0))}
                    />
                    <label className="text-[11px] uppercase tracking-[0.14em] text-white/60">Głębokość pokoju (Z) mm</label>
                    <input
                      className="input-base bg-white/95 text-slate-900"
                      type="number"
                      min={1200}
                      step={10}
                      value={Math.round(roomDepthInput)}
                      onChange={(event) => setRoomDepthInput(Math.max(0, Number(event.target.value) || 0))}
                    />
                    <label className="text-[11px] uppercase tracking-[0.14em] text-white/60">Geometria tylnej sciany</label>
                    <select
                      className="input-base bg-white/95 text-slate-900"
                      value={roomGeometryPreset}
                      onChange={(event) => setRoomGeometryPreset(event.target.value as RoomGeometryPreset)}
                    >
                      {Object.entries(ROOM_PRESET_LABELS).map(([key, label]) => (
                        <option key={key} value={key}>
                          {label}
                        </option>
                      ))}
                    </select>
                    <Button onClick={saveRoomConfig} disabled={savingRoomConfig}>
                      {savingRoomConfig ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                      Zapisz rozmiar pokoju
                    </Button>
                  </div>
                  <div className="rounded-2xl bg-white/10 px-4 py-3">Punkty na ścianie: {wallSummary?.points_count ?? 0}</div>
                </div>
                <div className="space-y-2">
                  <div className="text-xs uppercase tracking-[0.18em] text-white/55">Podsumowanie planera</div>
                  <div className="rounded-2xl bg-black/15 px-4 py-3">Moduly na scenie: {moduleRows.length}</div>
                  <div className="rounded-2xl bg-black/15 px-4 py-3">Przeszkody na scenie: {obstacles.length}</div>
                  <div className="rounded-2xl bg-black/15 px-4 py-3">
                    Gotowość: {mvpReadiness ? `${mvpReadiness.ready ? "gotowe" : "w toku"} (${mvpReadiness.score.percent}%)` : "-"}
                  </div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/15 p-4 text-[12px] leading-5 text-white/78">
                  To jest teraz plannerowy shell: po lewej narzedzia, w srodku scena z podloga i tylna sciana, po prawej inspektor.
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/15 p-4 text-[12px] leading-5 text-white/78">
                  Aktywny preset geometrii: <span className="font-semibold">{ROOM_PRESET_LABELS[roomGeometryPreset]}</span>.
                </div>
              </>
            ) : null}

            {leftPanelMode === "obstacles" ? (
              <>
                <div className="flex gap-2">
                  <select
                    value={newObstacleType}
                    onChange={(event) => setNewObstacleType(event.target.value as WorkspaceObstacleType)}
                    className="input-base flex-1 bg-white/95 text-slate-900"
                  >
                    {Object.entries(OBSTACLE_LABELS).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                  <Button variant="secondary" onClick={addObstacle}>Dodaj</Button>
                </div>

                <div className="space-y-2">
                  {obstacles.length === 0 ? <p className="text-xs text-white/65">Brak przeszkod. Dodaj pierwsza przeszkode.</p> : null}
                  {obstacles.map((item) => {
                    const warn = obstacleWarnings.get(item.id);
                    return (
                      <button
                        key={item.id}
                        onClick={() => {
                          setSelectedObstacleId(item.id);
                          setSelectedModuleId("");
                        }}
                        className={clsx(
                          "w-full rounded-2xl border px-3 py-3 text-left transition-all",
                          item.id === selectedObstacleId ? "border-white/30 bg-white/18" : "border-white/10 bg-black/10 hover:bg-white/10"
                        )}
                      >
                        <div className="flex items-center justify-between gap-3">
                          <span className="font-semibold">{obstacleLabel(item)}</span>
                          {warn?.outOfWall ? <span className="rounded-full bg-red-500/80 px-2 py-0.5 text-[10px] uppercase">out</span> : null}
                        </div>
                        <div className="mt-1 text-[11px] text-white/70">
                          x:{Math.round(item.x)} y:{Math.round(item.y)} w:{Math.round(item.width)} h:{Math.round(item.height)}
                        </div>
                      </button>
                    );
                  })}
                </div>

                {selectedObstacle ? (
                  <div className="space-y-2 rounded-2xl border border-white/10 bg-black/15 p-4">
                    <div className="text-xs uppercase tracking-[0.18em] text-white/55">Selected obstacle</div>
                    <select
                      value={selectedObstacle.type}
                      onChange={(event) => updateSelectedObstacle("type", event.target.value)}
                      className="input-base bg-white/95 text-slate-900"
                    >
                      {Object.entries(OBSTACLE_LABELS).map(([key, label]) => (
                        <option key={key} value={key}>
                          {label}
                        </option>
                      ))}
                    </select>
                    <div className="grid grid-cols-2 gap-2">
                      <input className="input-base bg-white/95 text-slate-900" type="number" value={Math.round(selectedObstacle.x)} onChange={(event) => updateSelectedObstacle("x", Number(event.target.value))} />
                      <input className="input-base bg-white/95 text-slate-900" type="number" value={Math.round(selectedObstacle.y)} onChange={(event) => updateSelectedObstacle("y", Number(event.target.value))} />
                      <input className="input-base bg-white/95 text-slate-900" type="number" value={Math.round(selectedObstacle.width)} onChange={(event) => updateSelectedObstacle("width", Number(event.target.value))} />
                      <input className="input-base bg-white/95 text-slate-900" type="number" value={Math.round(selectedObstacle.height)} onChange={(event) => updateSelectedObstacle("height", Number(event.target.value))} />
                    </div>
                    <div className="text-[11px] text-white/70">
                      Moduly kolidujace: {selectedObstacleIntersectingModules.length}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {selectedObstacleIntersectingModules.map((row) => (
                        <button
                          key={row.id}
                          className="rounded-full border border-white/15 bg-white/10 px-2 py-1 text-[11px]"
                          onClick={() => {
                            setSelectedModuleId(row.id);
                            setSelectedObstacleId("");
                            setLeftPanelMode("modules");
                          }}
                        >
                          {row.name}
                        </button>
                      ))}
                    </div>
                    <Button variant="secondary" onClick={clampSelectedObstacleToWall}>Napraw pozycje w scianie</Button>
                    <Button variant="danger" onClick={removeSelectedObstacle}>Usun zaznaczona przeszkode</Button>
                  </div>
                ) : (
                  <div className="rounded-2xl border border-dashed border-white/15 px-4 py-4 text-xs text-white/70">
                    Kliknij przeszkode na scenie lub z listy, zeby edytowac i zapisac.
                  </div>
                )}
              </>
            ) : null}

            {leftPanelMode === "modules" ? (
              <>
                <div className="flex gap-2">
                  <select value={moduleToPlaceId} onChange={(event) => setModuleToPlaceId(event.target.value)} className="input-base flex-1 bg-white/95 text-slate-900">
                    {moduleRows.map((row) => (
                      <option key={row.id} value={row.id}>
                        {row.name}
                      </option>
                    ))}
                  </select>
                  <Button variant="secondary" disabled={!moduleToPlaceId || updatingModule} onClick={addExistingModuleToWall}>
                    {updatingModule ? <Loader2 className="h-4 w-4 animate-spin" /> : <MoveRight className="h-4 w-4" />}
                    Dodaj
                  </Button>
                </div>

                <div className="space-y-2">
                  {moduleRows.map((row) => {
                    const warning = moduleWarnings.get(row.id);
                    const hasWarning = !!warning && (warning.outOfWall || warning.overlap || warning.obstacleIntersections.length > 0);
                    return (
                      <button
                        key={row.id}
                        onClick={() => {
                          setSelectedModuleId(row.id);
                          setSelectedObstacleId("");
                        }}
                        className={clsx(
                          "w-full rounded-2xl border px-3 py-3 text-left transition-all",
                          row.id === selectedModuleId ? "border-white/30 bg-white/18" : "border-white/10 bg-black/10 hover:bg-white/10"
                        )}
                      >
                        <div className="flex items-center justify-between gap-3">
                          <span className="font-semibold">{row.name}</span>
                          {hasWarning ? <span className="rounded-full bg-amber-400/90 px-2 py-0.5 text-[10px] uppercase text-slate-900">warn</span> : null}
                        </div>
                        <div className="mt-1 text-[11px] text-white/70">
                          x:{Math.round(row.x)} y:{Math.round(row.y)} w:{Math.round(row.width)} h:{Math.round(row.height)}
                        </div>
                      </button>
                    );
                  })}
                </div>

                {selectedModule ? (
                  <div className="space-y-2 rounded-2xl border border-white/10 bg-black/15 p-4">
                    <div className="text-xs uppercase tracking-[0.18em] text-white/55">Wybrany moduł</div>
                    <div className="grid grid-cols-2 gap-2">
                      <input className="input-base bg-white/95 text-slate-900" type="number" value={Math.round(modulePosX)} onChange={(event) => setModulePosX(Number(event.target.value) || 0)} />
                      <input
                        className="input-base bg-white/95 text-slate-900 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500"
                        type="number"
                        value={Math.round(modulePosY)}
                        disabled={selectedModule.mountType === "floor"}
                        onChange={(event) => setModulePosY(Number(event.target.value) || 0)}
                      />
                    </div>
                    {selectedModule.mountType === "floor" ? (
                      <div className="text-[11px] text-white/70">
                        Modul stojacy: Y jest stale = 0 (przy podlodze), przesuwasz go tylko po osi X.
                      </div>
                    ) : (
                      <div className="text-[11px] text-white/70">
                        Modul wiszacy: mozna ustawic X i Y, z automatycznym clampem do granic sciany.
                      </div>
                    )}
                    <div className="grid grid-cols-4 gap-2">
                      <Button variant="secondary" onClick={() => nudgeSelectedModuleX(-50)}>-50</Button>
                      <Button variant="secondary" onClick={() => nudgeSelectedModuleX(50)}>+50</Button>
                      <Button variant="secondary" onClick={() => alignSelectedModuleX("start")}>Start</Button>
                      <Button variant="secondary" onClick={() => alignSelectedModuleX("end")}>Koniec</Button>
                    </div>
                    <Button variant="secondary" onClick={spreadSelectedModuleFromOverlap}>Rozsun od kolizji</Button>
                    <Button disabled={updatingModule} onClick={applySelectedModulePlacement}>
                      {updatingModule ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                      Zastosuj polozenie
                    </Button>
                    <Button variant="secondary" onClick={clampSelectedModuleToWall}>Napraw pozycje w scianie</Button>
                    <Button as="link" href={`/configuration?module_id=${encodeURIComponent(selectedModule.id)}`} variant="secondary">
                      Otworz aktywny modul <ArrowRight className="h-4 w-4" />
                    </Button>
                  </div>
                ) : null}
              </>
            ) : null}

            {leftPanelMode === "connections" ? (
              <>
                <div className="space-y-3">
                  <div className="text-xs uppercase tracking-[0.18em] text-white/55">Narzędzia</div>
                  <div className="flex justify-center gap-3">
                    {TOOLS.map((t) => {
                      const Icon = t.icon;
                      const active = activeTool === t.id;
                      return (
                        <button
                          key={t.id}
                          onClick={() => setActiveTool(t.id)}
                          className={clsx(
                            "w-16 h-16 rounded-xl flex flex-col items-center justify-center gap-1 transition-all",
                            active
                              ? `${t.color} text-white shadow-lg scale-105`
                              : "bg-white/10 border border-white/10 text-white/60 hover:text-white"
                          )}
                          title={t.label}
                        >
                          <Icon className="w-5 h-5" />
                          <span className="text-[10px] font-bold">{t.label}</span>
                        </button>
                      );
                    })}
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-black/15 p-4 text-[12px] leading-5 text-white/78">
                    Kliknij w ścianę w widoku <span className="font-semibold text-white">Front</span> lub na <span className="font-semibold text-white">Scenie 3D</span>, aby nanieść punkt przyłącza.
                  </div>
                </div>

                <div className="space-y-2 mt-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-white/55">Zestawienie ({points.length})</div>
                  {pendingAction && (
                    <div className="rounded-2xl bg-white/10 p-4 border border-white/20">
                      <OperationPreviewList
                        title={pendingAction.title}
                        rows={previewRows}
                        warnings={previewWarnings}
                        maxHeightClassName="max-h-[140px]"
                      />
                      <div className="flex gap-2 mt-3">
                        <Button variant="secondary" className="flex-1" onClick={cancelPending}>
                          <X className="w-4 h-4 mr-1" /> Anuluj
                        </Button>
                        <Button className="flex-1" onClick={applyPending} disabled={busy !== null}>
                          {busy === "apply" ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <Check className="w-4 h-4 mr-1" />} Zatwierdź
                        </Button>
                      </div>
                    </div>
                  )}

                  <div className="space-y-2 max-h-[300px] overflow-y-auto">
                    {points.map((p) => {
                      const tool = TOOLS.find((t) => t.id === p.type) ?? TOOLS[0];
                      return (
                        <div
                          key={p.id}
                          className="bg-white/5 border border-white/10 rounded-xl p-3 flex items-center justify-between group hover:bg-white/10 transition-colors"
                        >
                          <div className="flex items-center gap-3">
                            <div className={clsx("w-8 h-8 rounded-lg flex items-center justify-center", tool.color)}>
                              <tool.icon className="w-4 h-4 text-white" />
                            </div>
                            <div>
                              <p className="text-sm font-semibold">{tool.label}</p>
                              <p className="text-xs text-white/60">X: {p.x} Y: {p.y}</p>
                            </div>
                          </div>
                          <button
                            onClick={() => buildRemovePreview(p.id)}
                            className="p-2 rounded-lg text-white/50 hover:text-red-400 hover:bg-red-500/20 transition-colors"
                            disabled={busy !== null}
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      );
                    })}
                    {points.length === 0 && !pendingAction && (
                      <div className="text-sm text-white/50 text-center py-4">Brak punktów na ścianie</div>
                    )}
                  </div>
                </div>
              </>
            ) : null}

            {leftPanelMode === "warnings" ? (
              <div className="space-y-3">
                <div className="rounded-2xl border border-red-400/20 bg-red-400/10 px-4 py-3">
                  Moduly out_of_wall: <span className="font-semibold">{warningSummary.modulesOutOfWall}</span>
                </div>
                <div className="rounded-2xl border border-amber-300/20 bg-amber-300/10 px-4 py-3">
                  Module overlap: <span className="font-semibold">{warningSummary.modulesOverlap}</span>
                </div>
                <div className="rounded-2xl border border-yellow-200/20 bg-yellow-200/10 px-4 py-3">
                  Obstacle intersection: <span className="font-semibold">{warningSummary.modulesObstacleIntersection}</span>
                </div>
                <div className="rounded-2xl border border-rose-300/20 bg-rose-300/10 px-4 py-3">
                  Obstacles out_of_wall: <span className="font-semibold">{warningSummary.obstaclesOutOfWall}</span>
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/15 px-4 py-3 text-xs text-white/72">
                  Kliknij modul lub przeszkode na scenie i popraw polozenie w lewym panelu.
                </div>
              </div>
            ) : null}

            {leftPanelMode === "komplet" ? (
              <div className="space-y-4 rounded-2xl border border-white/10 bg-black/15 p-5 text-center">
                <Layers className="mx-auto h-8 w-8 text-white/50" />
                <div>
                  <h3 className="font-semibold text-white">Kompletacja i Montaż</h3>
                  <p className="mt-2 text-xs text-white/70">
                    Zarządzanie kompletem zostało przeniesione do dedykowanego modułu, aby zoptymalizować przestrzeń roboczą dla całych zleceń.
                  </p>
                </div>
                <Button as="link" href="/assembly" className="w-full">
                  Przejdź do edytora kompletu <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            ) : null}

            {leftPanelMode === "struktura" ? (
              <div className="space-y-4 rounded-2xl border border-white/10 bg-black/15 p-5 text-center">
                <Database className="mx-auto h-8 w-8 text-white/50" />
                <div>
                  <h3 className="font-semibold text-white">Struktura i Konfiguracja</h3>
                  <p className="mt-2 text-xs text-white/70">
                    Konfiguracja okuć, właściwości fizycznych oraz materiałów odbywa się w dedykowanym edytorze strukturalnym.
                  </p>
                </div>
                <Button as="link" href="/configuration" className="w-full">
                  Przejdź do edytora struktury <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            ) : null}
          </div>
        </aside>
        ) : (
          <aside className="hidden xl:flex overflow-hidden rounded-[26px] border border-[#467cad]/30 bg-[linear-gradient(180deg,#235a84_0%,#163f60_100%)] text-white shadow-2xl">
            <div className="flex w-full flex-col items-center justify-between py-5">
              <button
                onClick={() => setLeftPanelOpen(true)}
                className="rounded-2xl border border-white/15 bg-white/10 p-3 text-white transition hover:bg-white/20"
                aria-label="Pokaz lewy panel"
              >
                <ChevronRight className="h-5 w-5" />
              </button>
              <div className="flex -rotate-180 flex-col items-center gap-3 [writing-mode:vertical-rl]">
                <span className="text-[11px] uppercase tracking-[0.28em] text-white/55">tools</span>
                <span className="text-sm font-semibold">{leftPanelMode}</span>
              </div>
              <div className="flex flex-col gap-3 text-white/65">
                <Home className="h-4 w-4" />
                <DoorOpen className="h-4 w-4" />
                <Box className="h-4 w-4" />
                <TriangleAlert className="h-4 w-4" />
              </div>
            </div>
          </aside>
        )}

        <main className="overflow-hidden rounded-[30px] border border-white/20 bg-[linear-gradient(180deg,#f2f5f8_0%,#edf2f7_35%,#dfe6ee_100%)] shadow-[0_30px_90px_rgba(0,0,0,0.35)]">
          <div className="flex h-full flex-col">
            <div className="flex items-center justify-between border-b border-slate-300/50 px-6 py-4">
              <div>
                <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500">Obszar roboczy</div>
                <h3 className="mt-1 text-xl font-semibold text-slate-900">Widok roboczy ściany</h3>
              </div>
              <div className="flex flex-wrap items-center gap-3 text-xs text-slate-600">
                <div className="inline-flex rounded-full border border-slate-300 bg-white/90 p-1 shadow-sm">
                  {[
                    { key: "3d", label: "3D" },
                    { key: "front", label: "Front" },
                    { key: "top", label: "Top" },
                  ].map((item) => (
                    <button
                      key={item.key}
                      onClick={() => setSceneView(item.key as typeof sceneView)}
                      className={clsx(
                        "rounded-full px-3 py-1.5 text-[11px] font-semibold transition",
                        sceneView === item.key ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-200"
                      )}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
                <span className="rounded-full border border-slate-300 bg-white/80 px-3 py-1">{sceneHint}</span>
                <span className="rounded-full border border-slate-300 bg-white/80 px-3 py-1">Edytor modułów pozostaje aktywny</span>
              </div>
            </div>

            <div className="relative flex-1 overflow-hidden px-5 py-5">
              {loading ? (
                <div className="flex h-full min-h-[560px] items-center justify-center text-sm text-slate-500">
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Ladowanie sceny workspace...
                </div>
              ) : (
                <div className="relative h-full min-h-[620px] overflow-hidden rounded-[28px] border border-slate-300/70 bg-[radial-gradient(circle_at_top,#ffffff_0%,#eef3f8_48%,#dce4ed_100%)]">
                  <div className="pointer-events-none absolute left-1/2 top-5 z-10 -translate-x-1/2 rounded-2xl border border-sky-300/50 bg-sky-300/35 px-5 py-3 text-center shadow-lg backdrop-blur">
                    <div className="text-[10px] uppercase tracking-[0.22em] text-slate-600">Aktywna ściana</div>
                    <div className="mt-1 text-lg font-semibold text-slate-900">{wallConfig?.wall_name ?? `WEB_PROJECT_${projectId}`}</div>
                    <div className="text-xs text-slate-600">{wallWidth} mm x {wallHeight} mm</div>
                  </div>

                  {sceneView === "3d" ? (
                    <WorkspaceRoom3D
                      wallWidth={wallWidth}
                      wallHeight={wallHeight}
                      roomDepth={roomDepth}
                      roomGeometryPreset={roomGeometryPreset}
                      roomGeometryBlocks={roomGeometryBlocks}
                      modules={moduleRows.map((row) => ({
                        id: row.id,
                        name: row.name,
                        x: row.id === selectedModuleId ? modulePosX : row.x,
                        y: row.id === selectedModuleId ? modulePosY : row.y,
                        width: row.width,
                        height: row.height,
                        depth: asNumber((row.module as any).depth, 560),
                        selected: row.id === selectedModuleId,
                        warning: moduleWarnings.get(row.id) ?? { outOfWall: false, overlap: false, obstacleIntersections: [] },
                      }))}
                      obstacles={obstacles.map((obstacle) => ({
                        ...obstacle,
                        depth: Math.max(0, asNumber(obstacle.depth, 0)),
                        selected: obstacle.id === selectedObstacleId,
                        warning: obstacleWarnings.get(obstacle.id) ?? { outOfWall: false },
                      }))}
                      onSelectModule={(moduleId) => {
                        setSelectedModuleId(moduleId);
                        setSelectedObstacleId("");
                        setLeftPanelMode("modules");
                      }}
                      onSelectObstacle={(obstacleId) => {
                        setSelectedObstacleId(obstacleId);
                        setSelectedModuleId("");
                        setLeftPanelMode("obstacles");
                      }}
                      onWallPlace={applyWallPlacementFromScene}
                    />
                  ) : null}

                  {sceneView === "front" ? (
                    <svg viewBox={`0 0 ${SCENE.viewWidth} ${SCENE.viewHeight}`} className="h-full w-full" onClick={onSceneClick}>
                      <defs>
                        <linearGradient id="front-wall-fill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#fffdf9" />
                          <stop offset="100%" stopColor="#f2eee7" />
                        </linearGradient>
                      </defs>
                      <rect x="0" y="0" width={SCENE.viewWidth} height={SCENE.viewHeight} fill="#edf2f7" />
                      <rect x={SCENE.wallLeft} y={SCENE.wallTop} width={SCENE.wallWidth} height={SCENE.wallHeight} rx="8" fill="url(#front-wall-fill)" stroke="#d7dde5" strokeWidth="2" />
                      <rect x={SCENE.wallLeft} y={SCENE.wallTop + SCENE.wallHeight} width={SCENE.wallWidth} height={120} fill="#e5ebf1" />
                      {roomGeometryBlocks.map((block) => {
                        const x = SCENE.wallLeft + block.x * wallScaleX;
                        const y = SCENE.wallTop + SCENE.wallHeight - (block.y + block.height) * wallScaleY;
                        const widthPx = block.width * wallScaleX;
                        const heightPx = block.height * wallScaleY;
                        return (
                          <g key={block.id}>
                            <rect
                              x={x}
                              y={y}
                              width={widthPx}
                              height={heightPx}
                              fill="#e7ebef"
                              stroke="#b7c0c9"
                              strokeWidth="1.6"
                            />
                            <text x={x + widthPx * 0.5} y={y + 20} textAnchor="middle" fill="#526070" fontSize="11" fontWeight="700">
                              kolumna
                            </text>
                          </g>
                        );
                      })}

                      <line x1={SCENE.wallLeft} y1={SCENE.wallTop - 24} x2={SCENE.wallLeft + SCENE.wallWidth} y2={SCENE.wallTop - 24} stroke="#444" strokeWidth="1.4" />
                      <line x1={SCENE.wallLeft} y1={SCENE.wallTop - 30} x2={SCENE.wallLeft} y2={SCENE.wallTop - 18} stroke="#444" strokeWidth="1.4" />
                      <line x1={SCENE.wallLeft + SCENE.wallWidth} y1={SCENE.wallTop - 30} x2={SCENE.wallLeft + SCENE.wallWidth} y2={SCENE.wallTop - 18} stroke="#444" strokeWidth="1.4" />
                      <text x={SCENE.wallLeft + SCENE.wallWidth / 2} y={SCENE.wallTop - 34} textAnchor="middle" fill="#1f2937" fontSize="20" fontWeight="700">
                        {wallWidth} mm
                      </text>

                      {obstacles.map((obstacle) => {
                        const warning = obstacleWarnings.get(obstacle.id);
                        const selected = obstacle.id === selectedObstacleId;
                        const x = SCENE.wallLeft + obstacle.x * wallScaleX;
                        const y = SCENE.wallTop + SCENE.wallHeight - (obstacle.y + obstacle.height) * wallScaleY;
                        const widthPx = obstacle.width * wallScaleX;
                        const heightPx = obstacle.height * wallScaleY;
                        const stroke = warning?.outOfWall ? "#dc2626" : selected ? "#0ea5e9" : "#475569";

                        return (
                          <g
                            key={obstacle.id}
                            onClick={(evt) => {
                              evt.stopPropagation();
                              setSelectedObstacleId(obstacle.id);
                              setSelectedModuleId("");
                              setLeftPanelMode("obstacles");
                            }}
                          >
                            <rect x={x} y={y} width={widthPx} height={heightPx} fill={OBSTACLE_FILL[obstacle.type]} fillOpacity={obstacle.type === "window" ? 0.4 : 0.85} stroke={stroke} strokeWidth={selected ? 4 : 2} rx="4" />
                            <text x={x + widthPx / 2} y={y - 8} textAnchor="middle" fill="#334155" fontSize="14" fontWeight="700">
                              {OBSTACLE_LABELS[obstacle.type]}
                            </text>
                          </g>
                        );
                      })}

                      {moduleRows.map((row) => {
                        const warning = moduleWarnings.get(row.id);
                        const selected = row.id === selectedModuleId;
                        const x = SCENE.wallLeft + row.x * wallScaleX;
                        const y = SCENE.wallTop + SCENE.wallHeight - (row.y + row.height) * wallScaleY;
                        const widthPx = Math.max(24, row.width * wallScaleX);
                        const heightPx = Math.max(24, row.height * wallScaleY);
                        const hasWarning = !!warning && (warning.outOfWall || warning.overlap || warning.obstacleIntersections.length > 0);
                        const frontFill = selected ? "#f5d6a6" : hasWarning ? "#f7d9bf" : "#f5efe5";
                        const stroke = warning?.outOfWall ? "#dc2626" : selected ? "#fb923c" : hasWarning ? "#f59e0b" : "#9ca3af";

                        return (
                          <g
                            key={row.id}
                            onClick={(evt) => {
                              evt.stopPropagation();
                              setSelectedModuleId(row.id);
                              setSelectedObstacleId("");
                              setLeftPanelMode("modules");
                            }}
                          >
                            <rect x={x} y={y} width={widthPx} height={heightPx} rx="5" fill={frontFill} stroke={stroke} strokeWidth={selected ? 4 : 2.2} />
                            <line x1={x + widthPx * 0.68} y1={y + heightPx * 0.26} x2={x + widthPx * 0.68} y2={y + heightPx * 0.76} stroke="#8b5e3c" strokeWidth="2.4" />
                            <text x={x + widthPx / 2} y={y + heightPx + 22} textAnchor="middle" fill="#1f2937" fontSize="13" fontWeight="700">
                              {row.name.length > 24 ? `${row.name.slice(0, 24)}...` : row.name}
                            </text>
                          </g>
                        );
                      })}

                      {points.map((p) => {
                        const tool = TOOLS.find((t) => t.id === p.type) ?? TOOLS[0];
                        const x = SCENE.wallLeft + p.x * wallScaleX;
                        const y = SCENE.wallTop + SCENE.wallHeight - p.y * wallScaleY;
                        return (
                          <g key={p.id}>
                            <circle cx={x} cy={y} r="12" fill={tool.color.includes("blue") ? "#3b82f6" : tool.color.includes("cyan") ? "#06b6d4" : "#f97316"} />
                            <circle cx={x} cy={y} r="6" fill="#ffffff" />
                            <text x={x} y={y + 24} textAnchor="middle" fill="#334155" fontSize="10" fontWeight="700">
                              {tool.tag}
                            </text>
                          </g>
                        );
                      })}
                    </svg>
                  ) : null}

                  {sceneView === "top" ? (
                    <svg viewBox={`0 0 ${SCENE.viewWidth} ${SCENE.viewHeight}`} className="h-full w-full" onClick={onSceneClick}>
                      <defs>
                        <pattern id="top-grid" width="42" height="42" patternUnits="userSpaceOnUse">
                          <rect width="42" height="42" fill="#eef3f7" />
                          <path d="M 42 0 L 0 0 0 42" fill="none" stroke="#d9e2ea" strokeWidth="1.4" />
                        </pattern>
                      </defs>
                      <rect x="0" y="0" width={SCENE.viewWidth} height={SCENE.viewHeight} fill="#edf2f7" />
                      <rect x={TOP_SCENE.left} y={TOP_SCENE.top} width={TOP_SCENE.width} height={TOP_SCENE.depth} rx="10" fill="url(#top-grid)" stroke="#cfd8e3" strokeWidth="2" />
                      <rect x={TOP_SCENE.left} y={TOP_SCENE.top} width={TOP_SCENE.width} height="24" fill="#f4efe7" stroke="#d7dde5" strokeWidth="1" />
                      <text x={TOP_SCENE.left + TOP_SCENE.width / 2} y={TOP_SCENE.top - 14} textAnchor="middle" fill="#1f2937" fontSize="20" fontWeight="700">
                        TOP VIEW / {wallWidth} mm
                      </text>
                      <text x={TOP_SCENE.left + 14} y={TOP_SCENE.top + 17} fill="#475569" fontSize="12" fontWeight="700">
                        tylna sciana
                      </text>
                      {roomGeometryBlocks.map((block) => {
                        const x = TOP_SCENE.left + (block.x / wallWidth) * TOP_SCENE.width;
                        const widthPx = Math.max(10, (block.width / wallWidth) * TOP_SCENE.width);
                        return (
                          <rect
                            key={block.id}
                            x={x}
                            y={TOP_SCENE.top + 2}
                            width={widthPx}
                            height={TOP_SCENE.depth - 4}
                            rx="4"
                            fill="#dee5eb"
                            stroke="#98a3b1"
                            strokeWidth="1.2"
                            opacity="0.86"
                          />
                        );
                      })}

                      {obstacles.map((obstacle) => {
                        const selected = obstacle.id === selectedObstacleId;
                        const warning = obstacleWarnings.get(obstacle.id);
                        const centerX = TOP_SCENE.left + (obstacle.x / wallWidth) * TOP_SCENE.width;
                        const markerWidth = Math.max(12, (obstacle.width / wallWidth) * TOP_SCENE.width);
                        const stroke = warning?.outOfWall ? "#dc2626" : selected ? "#0ea5e9" : "#475569";
                        return (
                          <g
                            key={obstacle.id}
                            onClick={(evt) => {
                              evt.stopPropagation();
                              setSelectedObstacleId(obstacle.id);
                              setSelectedModuleId("");
                              setLeftPanelMode("obstacles");
                            }}
                          >
                            <rect
                              x={centerX}
                              y={TOP_SCENE.top + 3}
                              width={markerWidth}
                              height="18"
                              rx="4"
                              fill={OBSTACLE_FILL[obstacle.type]}
                              stroke={stroke}
                              strokeWidth={selected ? 3 : 1.6}
                            />
                          </g>
                        );
                      })}

                      {moduleRows.map((row) => {
                        const warning = moduleWarnings.get(row.id);
                        const selected = row.id === selectedModuleId;
                        const x = TOP_SCENE.left + (row.x / wallWidth) * TOP_SCENE.width;
                        const widthPx = Math.max(24, (row.width / wallWidth) * TOP_SCENE.width);
                        const depthPx = 84;
                        const y = TOP_SCENE.top + 28 + Math.min(180, Math.max(0, row.y * 0.06));
                        const hasWarning = !!warning && (warning.outOfWall || warning.overlap || warning.obstacleIntersections.length > 0);
                        const fill = selected ? "#f5d6a6" : hasWarning ? "#f7d9bf" : "#f5efe5";
                        const stroke = warning?.outOfWall ? "#dc2626" : selected ? "#fb923c" : hasWarning ? "#f59e0b" : "#9ca3af";

                        return (
                          <g
                            key={row.id}
                            onClick={(evt) => {
                              evt.stopPropagation();
                              setSelectedModuleId(row.id);
                              setSelectedObstacleId("");
                              setLeftPanelMode("modules");
                            }}
                          >
                            <rect x={x} y={y} width={widthPx} height={depthPx} rx="6" fill={fill} stroke={stroke} strokeWidth={selected ? 4 : 2.2} />
                            <text x={x + widthPx / 2} y={y + depthPx + 18} textAnchor="middle" fill="#1f2937" fontSize="12" fontWeight="700">
                              {row.name.length > 18 ? `${row.name.slice(0, 18)}...` : row.name}
                            </text>
                          </g>
                        );
                      })}

                      {points.map((p) => {
                        const tool = TOOLS.find((t) => t.id === p.type) ?? TOOLS[0];
                        const x = TOP_SCENE.left + (p.x / wallWidth) * TOP_SCENE.width;
                        const y = TOP_SCENE.top + 12; // place on the rear wall line
                        return (
                          <g key={p.id}>
                            <circle cx={x} cy={y} r="6" fill={tool.color.includes("blue") ? "#3b82f6" : tool.color.includes("cyan") ? "#06b6d4" : "#f97316"} />
                          </g>
                        );
                      })}
                    </svg>
                  ) : null}

                  <div className="absolute bottom-4 left-4 right-4 grid grid-cols-1 gap-3 lg:grid-cols-4">
                    <div className="rounded-2xl border border-white/70 bg-white/75 px-4 py-3 backdrop-blur">
                      <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Selection</div>
                      <div className="mt-1 text-sm font-semibold text-slate-900">
                        {selectedModule ? `Modul: ${selectedModule.name}` : selectedObstacle ? `Przeszkoda: ${obstacleLabel(selectedObstacle)}` : "Brak zaznaczenia"}
                      </div>
                    </div>
                    <div className="rounded-2xl border border-white/70 bg-white/75 px-4 py-3 backdrop-blur">
                      <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Modules</div>
                      <div className="mt-1 text-sm font-semibold text-slate-900">{moduleRows.length} na scenie</div>
                    </div>
                    <div className="rounded-2xl border border-white/70 bg-white/75 px-4 py-3 backdrop-blur">
                      <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Przeszkody</div>
                      <div className="mt-1 text-sm font-semibold text-slate-900">{obstacles.length} na scianie</div>
                    </div>
                    <div className="rounded-2xl border border-white/70 bg-white/75 px-4 py-3 backdrop-blur">
                      <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Ostrzeżenia</div>
                      <div className="mt-1 text-sm font-semibold text-slate-900">{warningSummary.modulesWithAnyWarning + warningSummary.obstaclesOutOfWall}</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </main>

        {rightPanelOpen ? (
        <aside className="overflow-hidden rounded-[26px] border border-white/10 bg-[#2f3133]/95 text-white shadow-2xl">
          <div className="border-b border-white/10 px-5 py-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-[11px] uppercase tracking-[0.22em] text-white/45">Asystent</div>
                <div className="mt-2 text-xl font-semibold">Inspektor ściany</div>
              </div>
              <button
                onClick={() => setRightPanelOpen(false)}
                className="rounded-xl border border-white/15 bg-white/5 p-2 text-white/80 transition hover:bg-white/10 hover:text-white"
                aria-label="Schowaj prawy panel"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>

          <div className="space-y-5 px-5 py-5 text-sm">
            <div>
              <div className="mb-3 text-[11px] uppercase tracking-[0.18em] text-white/45">Postęp</div>
              <div className="space-y-3">
                {plannerSteps.map((step, index) => (
                  <div key={step.label}>
                    <div className="mb-1 flex items-center justify-between text-white/80">
                      <span>Krok {index + 1}. {step.label}</span>
                      <span className={clsx("text-[11px] uppercase", step.done ? "text-emerald-300" : "text-white/35")}>
                        {step.done ? "gotowe" : "do zrobienia"}
                      </span>
                    </div>
                    <div className="h-1.5 rounded-full bg-white/10">
                      <div className={clsx("h-1.5 rounded-full", step.done ? "w-full bg-white" : "w-1/3 bg-white/30")} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <div className="mb-3 text-[11px] uppercase tracking-[0.18em] text-white/45">Projekcja widoku</div>
              <div className="space-y-2 text-xs">
                {[
                  { key: "3d", label: "Perspektywa / 3D", tone: "Główny widok roboczy, najbliższy pracy jak w Proboard" },
                  { key: "front", label: "Elewacja frontowa", tone: "Czysty odczyt ściany i wysokości" },
                  { key: "top", label: "Rzut z góry", tone: "Szybki układ X i relacja z podłogą" },
                ].map((item) => (
                  <button
                    key={item.key}
                    onClick={() => setSceneView(item.key as typeof sceneView)}
                    className={clsx(
                      "w-full rounded-xl border px-3 py-2 text-left transition",
                      sceneView === item.key ? "border-sky-400/60 bg-sky-400/20 text-white" : "border-white/10 bg-white/5 text-white/72 hover:bg-white/10"
                    )}
                  >
                    <div className="font-semibold">{item.label}</div>
                    <div className="mt-1 text-[11px] text-white/55">{item.tone}</div>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <div className="mb-3 text-[11px] uppercase tracking-[0.18em] text-white/45">Wskazówki interfejsu</div>
              <div className="space-y-2">
                <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                  <div className="mb-1 flex items-center gap-2 font-semibold"><Ruler className="h-4 w-4" /> Wymiary ściany</div>
                  <div className="text-xs text-white/65">Widoczne nad scena i po lewej osi tylnej sciany.</div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                  <div className="mb-1 flex items-center gap-2 font-semibold"><MousePointerClick className="h-4 w-4" /> Kliknij aby wstawić</div>
                  <div className="text-xs text-white/65">
                    {sceneView === "3d"
                      ? "W 3D: dwuklik na tylnej scianie ustawia wybrany modul lub przeszkode (drag zostaje dla kamery)."
                      : sceneView === "top"
                      ? "W top view klik ustawia glownie pozycje X wzgledem sciany."
                      : "Klikaj w tylna sciane pokoju, zeby ustawic modul lub przeszkode."}
                  </div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                  <div className="mb-1 flex items-center gap-2 font-semibold"><Wrench className="h-4 w-4" /> Zarządzanie modułem</div>
                  <div className="text-xs text-white/65">Edytor `/configuration` nadal otwiera prawdziwy domenowy modul.</div>
                </div>
              </div>
            </div>

            <div>
              <div className="mb-3 text-[11px] uppercase tracking-[0.18em] text-white/45">Ostrzeżenia</div>
              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between rounded-xl bg-red-500/12 px-3 py-2">
                  <span className="inline-flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-red-400" /> out_of_wall</span>
                  <span>{warningSummary.modulesOutOfWall + warningSummary.obstaclesOutOfWall}</span>
                </div>
                <div className="flex items-center justify-between rounded-xl bg-amber-400/12 px-3 py-2">
                  <span className="inline-flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-amber-300" /> overlap</span>
                  <span>{warningSummary.modulesOverlap}</span>
                </div>
                <div className="flex items-center justify-between rounded-xl bg-yellow-200/12 px-3 py-2">
                  <span className="inline-flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-yellow-200" /> obstacle</span>
                  <span>{warningSummary.modulesObstacleIntersection}</span>
                </div>
              </div>
            </div>

            <div>
              <div className="mb-3 text-[11px] uppercase tracking-[0.18em] text-white/45">Warstwy</div>
              <div className="space-y-2 text-xs text-white/72">
                <div className="flex items-center justify-between rounded-xl border border-white/10 px-3 py-2">
                  <span className="inline-flex items-center gap-2"><Home className="h-3.5 w-3.5" /> budynek</span>
                  <span>on</span>
                </div>
                <div className="flex items-center justify-between rounded-xl border border-white/10 px-3 py-2">
                  <span className="inline-flex items-center gap-2"><Box className="h-3.5 w-3.5" /> szafki</span>
                  <span>on</span>
                </div>
                <div className="flex items-center justify-between rounded-xl border border-white/10 px-3 py-2">
                  <span className="inline-flex items-center gap-2"><DoorOpen className="h-3.5 w-3.5" /> przeszkody</span>
                  <span>on</span>
                </div>
                <div className="flex items-center justify-between rounded-xl border border-white/10 px-3 py-2">
                  <span className="inline-flex items-center gap-2"><SquareStack className="h-3.5 w-3.5" /> dane planera</span>
                  <span>sync</span>
                </div>
              </div>
            </div>

            {selectedModuleWarning ? (
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-xs text-white/75">
                <div className="mb-2 font-semibold text-white">Active module warnings</div>
                <div>{selectedModuleWarning.outOfWall ? "out_of_wall" : "out_of_wall: brak"}</div>
                <div>{selectedModuleWarning.overlap ? "module_overlap" : "module_overlap: brak"}</div>
                <div>
                  {selectedModuleWarning.obstacleIntersections.length > 0
                    ? `obstacle_intersection: ${selectedModuleWarning.obstacleIntersections.join(", ")}`
                    : "obstacle_intersection: brak"}
                </div>
              </div>
            ) : null}

            <AgentPanel />
          </div>
        </aside>
        ) : (
          <aside className="hidden xl:flex overflow-hidden rounded-[26px] border border-white/10 bg-[#2f3133]/95 text-white shadow-2xl">
            <div className="flex w-full flex-col items-center justify-between py-5">
              <button
                onClick={() => setRightPanelOpen(true)}
                className="rounded-2xl border border-white/15 bg-white/10 p-3 text-white transition hover:bg-white/20"
                aria-label="Pokaz prawy panel"
              >
                <ChevronLeft className="h-5 w-5" />
              </button>
              <div className="flex -rotate-180 flex-col items-center gap-3 [writing-mode:vertical-rl]">
                <span className="text-[11px] uppercase tracking-[0.28em] text-white/45">view</span>
                <span className="text-sm font-semibold">{sceneView}</span>
              </div>
              <div className="flex flex-col gap-3 text-white/65">
                <Ruler className="h-4 w-4" />
                <MousePointerClick className="h-4 w-4" />
                <SquareStack className="h-4 w-4" />
              </div>
            </div>
          </aside>
        )}
      </div>
    </AppShell>
  );
}
