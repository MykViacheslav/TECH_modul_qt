import {
  TechModulAPI,
  type BulkOperationResult,
  type OperationAction,
  type OperationRequest,
  type OperationResult,
} from "@/services/api";

export type BulkModuleOperationRequest = {
  action: OperationAction;
  moduleIds: Array<number | string>;
  params?: Record<string, unknown>;
  source?: string;
};

export type BulkOperationPreviewResult = {
  status: "ok" | "validation_error" | "error";
  can_apply: boolean;
  action: OperationAction;
  warnings: string[];
  errors: Array<{ moduleId: string; message: string }>;
  changes: OperationResult["changes"];
};

function normalizeModuleId(id: string | number): string {
  return String(id ?? "").trim();
}

export async function previewOperation(request: OperationRequest): Promise<OperationResult> {
  if (request.action.startsWith("wall.")) {
    return TechModulAPI.previewWallOperation(request);
  }
  return TechModulAPI.previewModuleOperation(request);
}

export async function applyOperation(request: OperationRequest): Promise<OperationResult> {
  if (request.action.startsWith("wall.")) {
    return TechModulAPI.applyWallOperation(request);
  }
  return TechModulAPI.applyModuleOperation(request);
}

export async function previewModuleOperationSvc(request: OperationRequest): Promise<OperationResult> {
  return previewOperation(request);
}

export async function applyModuleOperationSvc(request: OperationRequest): Promise<OperationResult> {
  return applyOperation(request);
}

// Aliases for compatibility
export const applyModuleOperation = applyOperation;
export const previewModuleOperation = previewOperation;

export async function previewBulkModuleOperation(
  req: BulkModuleOperationRequest
): Promise<BulkOperationPreviewResult> {
  const moduleIds = req.moduleIds.map(normalizeModuleId).filter(Boolean);
  const result: BulkOperationResult = await TechModulAPI.previewBulkModuleOperation({
    action: req.action,
    module_ids: moduleIds,
    params: req.params ?? {},
    source: req.source ?? "frontend",
  });

  const errors = (result.errors ?? []).map((e) => ({
    moduleId: String(e.module_id),
    message: String(e.message || "Bad podgladu"),
  }));
  const changes = (result.changes ?? []) as OperationResult["changes"];
  const can_apply = Boolean(result.can_apply) && errors.length === 0 && changes.length > 0;

  return {
    status: can_apply ? "ok" : "validation_error",
    can_apply,
    action: req.action,
    warnings: (result.warnings ?? []).map((w) => String(w)),
    errors,
    changes,
  };
}

export async function applyBulkModuleOperation(req: BulkModuleOperationRequest): Promise<{ appliedCount: number }> {
  const moduleIds = req.moduleIds.map(normalizeModuleId).filter(Boolean);
  const result: BulkOperationResult = await TechModulAPI.applyBulkModuleOperation({
    action: req.action,
    module_ids: moduleIds,
    params: req.params ?? {},
    source: req.source ?? "frontend",
  });
  return { appliedCount: Number(result.applied_count ?? 0) };
}
