"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles,
  ArrowRight,
  Check,
  X,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui";
import OperationPreviewList, { type OperationPreviewRow } from "@/components/OperationPreviewList";
import { parseAgentCommand } from "@/services/agent";
import { applyBulkModuleOperation, previewBulkModuleOperation } from "@/services/operations";
import type { AgentChange, OperationAction } from "@/services/api";
import {
  mapOperationChangesToPreviewRows,
} from "@/services/operation-contract";
import { useSelectedProjectId } from "@/services/project-context";

type Props = {
  onApplied?: () => void | Promise<void>;
  placeholder?: string;
};

const PARAM_LABEL: Record<string, string> = {
  width: "szerokosc",
  height: "wysokosc",
  depth: "gebokosc",
};

type PreviewItem = AgentChange & {
  action: OperationAction;
  params: Record<string, unknown>;
};

type PreviewGroup = {
  action: OperationAction;
  params: Record<string, unknown>;
  moduleIds: string[];
};

type Status =
  | { kind: "idle" }
  | { kind: "loading" }
  | {
      kind: "preview";
      groups: PreviewGroup[];
      rows: OperationPreviewRow[];
      warnings: string[];
      canApply: boolean;
    }
  | { kind: "error"; message: string }
  | { kind: "applying" }
  | { kind: "applied"; count: number };

function actionForParam(param: string): OperationAction {
  if (param === "depth") return "module.set_depth";
  if (param === "width") return "module.set_width";
  if (param === "height") return "module.set_height";
  throw new Error(`Nieobsugiwany parametr: ${param}`);
}

function paramsForChange(param: string, value: number): Record<string, unknown> {
  if (param === "depth") return { depth_mm: value };
  if (param === "width") return { width_mm: value };
  if (param === "height") return { height_mm: value };
  throw new Error(`Nieobsugiwany parametr: ${param}`);
}

export default function AgentPanel({ onApplied, placeholder }: Props = {}) {
  const [projectId] = useSelectedProjectId(1);
  const [text, setText] = useState("");
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  const buildGroups = (changes: PreviewItem[]): PreviewGroup[] => {
    const groups = new Map<string, PreviewGroup>();
    for (const ch of changes) {
      const moduleId = String(ch.id);
      const groupKey = `${ch.action}|${JSON.stringify(ch.params)}`;
      const current = groups.get(groupKey);
      if (current) {
        current.moduleIds.push(moduleId);
      } else {
        groups.set(groupKey, {
          action: ch.action,
          params: ch.params,
          moduleIds: [moduleId],
        });
      }
    }
    return Array.from(groups.values());
  };

  const ask = async () => {
    if (!text.trim()) return;
    setStatus({ kind: "loading" });

    try {
      const parsed = await parseAgentCommand(text, projectId);
      const nextChanges: PreviewItem[] = parsed.changes.map((ch) => {
        const action = actionForParam(ch.param);
        const params = paramsForChange(ch.param, ch.new);
        return { ...ch, action, params };
      });
      if (nextChanges.length === 0) {
        throw new Error("Brak zmian do podgladu.");
      }

      const groups = buildGroups(nextChanges);
      const warnings: string[] = [];
      const backendChanges: Array<{
        path: string;
        label: string;
        before: unknown;
        after: unknown;
        unit?: string;
        kind?: string;
        target_ref?: { type: string; id: string; name: string };
      }> = [];

      for (const group of groups) {
        const preview = await previewBulkModuleOperation({
          action: group.action,
          moduleIds: group.moduleIds,
          params: group.params,
          source: "agent_panel",
        });
        if (!preview.can_apply) {
          throw new Error(preview.errors[0]?.message ?? "Nie mozna przygotowac podgladu");
        }
        warnings.push(...(preview.warnings ?? []));
        backendChanges.push(...(preview.changes ?? []));
      }

      setStatus({
        kind: "preview",
        groups,
        rows: mapOperationChangesToPreviewRows(backendChanges, { fallbackName: "Modu" }),
        warnings,
        canApply: backendChanges.length > 0,
      });
    } catch (e: any) {
      setStatus({ kind: "error", message: e?.message ?? "Bad" });
    }
  };

  const confirm = async () => {
    if (status.kind !== "preview" || !status.canApply) return;
    setStatus({ kind: "applying" });

    try {
      let applied = 0;
      for (const group of status.groups) {
        const result = await applyBulkModuleOperation({
          action: group.action,
          moduleIds: group.moduleIds,
          params: group.params,
          source: "agent_panel",
        });
        if (result.appliedCount <= 0) {
          throw new Error("Nie udao sie zastosowac operacji");
        }
        applied += result.appliedCount;
      }

      if (onApplied) await onApplied();

      setStatus({ kind: "applied", count: applied });
      setText("");
      setTimeout(() => setStatus({ kind: "idle" }), 2500);
    } catch (e: any) {
      setStatus({ kind: "error", message: e?.message ?? "Bad zapisu" });
    }
  };

  const cancel = () => setStatus({ kind: "idle" });

  return (
    <div className="rounded-panel border border-brand-ring/60 bg-gradient-to-br from-brand-soft to-transparent p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-9 h-9 rounded-lg bg-brand flex items-center justify-center shadow-brand-glow">
          <Sparkles className="w-4 h-4 text-white" />
        </div>
        <div>
          <p className="eyebrow-brand">Tech Assistant</p>
          <p className="text-sm font-semibold">Asystent AI</p>
        </div>
      </div>

      <div className="flex gap-2">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
          placeholder={placeholder ?? 'Np. "zwieksz gebokosc o 50"'}
          disabled={status.kind === "loading" || status.kind === "applying"}
          className="input-base disabled:opacity-50"
        />
        <Button
          onClick={ask}
          disabled={
            !text.trim() ||
            status.kind === "loading" ||
            status.kind === "applying"
          }
          className="disabled:opacity-50"
        >
          {status.kind === "loading" ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <ArrowRight className="w-4 h-4" />
          )}
        </Button>
      </div>

      <AnimatePresence mode="wait">
        {status.kind === "error" && (
          <motion.div
            key="err"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="mt-4 flex items-start gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-300"
          >
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{status.message}</span>
          </motion.div>
        )}

        {status.kind === "preview" && (
          <motion.div
            key="preview"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="mt-4"
          >
            <OperationPreviewList
              title="Podglad zmian"
              warnings={status.warnings}
              rows={status.rows}
            />

            <div className="flex gap-2 mt-4">
              <Button variant="secondary" onClick={cancel} className="flex-1">
                <X className="w-4 h-4" /> Anuluj
              </Button>
              <Button onClick={confirm} className="flex-1" disabled={!status.canApply}>
                <Check className="w-4 h-4" /> Zatwierdz
              </Button>
            </div>
          </motion.div>
        )}

        {status.kind === "applying" && (
          <motion.p
            key="applying"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="mt-4 text-xs text-slate-400 flex items-center gap-2"
          >
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            Zapisywanie zmian...
          </motion.p>
        )}

        {status.kind === "applied" && (
          <motion.div
            key="ok"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="mt-4 flex items-center gap-2 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-300"
          >
            <Check className="w-4 h-4" />
            Zastosowano {status.count} {status.count === 1 ? "zmiane" : "zmiany"}.
          </motion.div>
        )}

        {status.kind === "idle" && (
          <motion.p
            key="idle"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-3 text-xs text-slate-500"
          >
            AI nigdy nie zmienia danych bez Twojego potwierdzenia.
          </motion.p>
        )}
      </AnimatePresence>
    </div>
  );
}
