// Phase 1 Safe Work Mode: visible labels showing which modules are safe for real
// work and which are still in development. Edit only the MODULE_STATUS map below
// when a module changes phase. The plan classification is in
// docs/WEB_SAFE_WORK_MODE_PHASE1_IMPLEMENTATION_PLAN.md section 3.6.

export type ModuleStatus = "READY_FOR_WORK" | "TESTING" | "IN_DEVELOPMENT";

export const MODULE_STATUS: Record<string, ModuleStatus> = {
  "/calendar": "READY_FOR_WORK",
  "/inventory": "READY_FOR_WORK",
  "/database": "READY_FOR_WORK",
  "/finance": "READY_FOR_WORK",
  "/finance/fixed-costs": "READY_FOR_WORK",
  "/cashboxes": "READY_FOR_WORK",
  "/alarms": "READY_FOR_WORK",
  "/orders/new": "READY_FOR_WORK",
  "/dashboard": "READY_FOR_WORK",
  "/settings": "READY_FOR_WORK",

  "/services": "TESTING",
  "/workspace/production": "TESTING",
  "/wall": "TESTING",
  "/operations": "TESTING",
  "/production/handoff": "TESTING",

  "/configuration": "IN_DEVELOPMENT",
  "/assembly": "IN_DEVELOPMENT",
  "/workspace": "IN_DEVELOPMENT",
  "/cri": "IN_DEVELOPMENT",
  "/overview": "IN_DEVELOPMENT",
};

export function getModuleStatus(href: string): ModuleStatus | null {
  if (Object.prototype.hasOwnProperty.call(MODULE_STATUS, href)) {
    return MODULE_STATUS[href];
  }
  return null;
}

export const STATUS_LABEL: Record<ModuleStatus, string> = {
  READY_FOR_WORK: "Gotowe do pracy",
  TESTING: "Testowanie",
  IN_DEVELOPMENT: "W rozwoju",
};

export const STATUS_DOT_CLASS: Record<ModuleStatus, string> = {
  READY_FOR_WORK: "bg-emerald-400",
  TESTING: "bg-amber-400",
  IN_DEVELOPMENT: "bg-red-400",
};

export const STATUS_BORDER_CLASS: Record<ModuleStatus, string> = {
  READY_FOR_WORK: "border-emerald-500/40 text-emerald-300",
  TESTING: "border-amber-500/40 text-amber-300",
  IN_DEVELOPMENT: "border-red-500/40 text-red-300",
};
