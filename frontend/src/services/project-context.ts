"use client";

import { useCallback, useEffect, useState } from "react";

const SELECTED_PROJECT_KEY = "tech_modul.selected_project_id";
const SELECTED_PROJECT_EVENT = "tech_modul:selected_project_changed";

function normalizeProjectId(value: unknown, fallback: number): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) return fallback;
  return Math.floor(parsed);
}

export function getStoredProjectId(fallback = 1): number {
  if (typeof window === "undefined") return fallback;
  return normalizeProjectId(window.localStorage.getItem(SELECTED_PROJECT_KEY), fallback);
}

export function setStoredProjectId(projectId: number): void {
  if (typeof window === "undefined") return;
  const normalized = normalizeProjectId(projectId, 1);
  window.localStorage.setItem(SELECTED_PROJECT_KEY, String(normalized));
  window.dispatchEvent(
    new CustomEvent(SELECTED_PROJECT_EVENT, {
      detail: { projectId: normalized },
    })
  );
}

export function useSelectedProjectId(fallback = 1): [number, (projectId: number) => void] {
  const [projectId, setProjectId] = useState<number>(fallback);

  useEffect(() => {
    setProjectId(getStoredProjectId(fallback));

    const onStorage = (event: StorageEvent) => {
      if (event.key !== SELECTED_PROJECT_KEY) return;
      setProjectId(getStoredProjectId(fallback));
    };
    const onCustom = (event: Event) => {
      const custom = event as CustomEvent<{ projectId?: number }>;
      setProjectId(normalizeProjectId(custom.detail?.projectId, fallback));
    };

    window.addEventListener("storage", onStorage);
    window.addEventListener(SELECTED_PROJECT_EVENT, onCustom as EventListener);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener(SELECTED_PROJECT_EVENT, onCustom as EventListener);
    };
  }, [fallback]);

  const updateProjectId = useCallback((nextProjectId: number) => {
    const normalized = normalizeProjectId(nextProjectId, fallback);
    setProjectId(normalized);
    setStoredProjectId(normalized);
  }, [fallback]);

  return [projectId, updateProjectId];
}
