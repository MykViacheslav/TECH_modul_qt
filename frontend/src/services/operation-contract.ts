import type { OperationChange, OperationError, OperationResult } from "@/services/api";

const ERROR_CODE_PL: Record<string, string> = {
  OUT_OF_RANGE: "Wartosc jest poza dozwolonym zakresem.",
  NOT_FOUND: "Nie znaleziono docelowego elementu.",
  POINT_NOT_FOUND: "Nie znaleziono wskazanego punktu.",
  UNKNOWN_MATERIAL: "Podany materia nie istnieje w katalogu.",
  MISSING_FIELD: "Brakuje wymaganego pola wejsciowego.",
  UNSUPPORTED_ACTION: "Nieobsugiwana akcja operacji.",
  UNSUPPORTED_POINT_TYPE: "Nieobsugiwany typ punktu.",
  VALIDATION_ERROR: "Dane wejsciowe nie przeszy walidacji.",
  INTERNAL_ERROR: "Wystapi bad wewnetrzny operacji.",
};

export type UnifiedPreviewRow = {
  key: string;
  name?: string;
  label: string;
  before: string;
  after: string;
  unit?: string;
};

function stringifyValue(value: unknown): string {
  if (value === null || value === undefined) return "-";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

export function mapOperationChangesToPreviewRows(
  changes: OperationChange[],
  opts?: { fallbackName?: string }
): UnifiedPreviewRow[] {
  const fallbackName = opts?.fallbackName ?? "Element";
  return (changes ?? []).map((ch, idx) => ({
    key: `${ch.path}-${idx}`,
    name: ch.target_ref?.name || fallbackName,
    label: ch.label || ch.path || "Zmiana",
    before: stringifyValue(ch.before),
    after: stringifyValue(ch.after),
    unit: ch.unit,
  }));
}

export function getOperationErrorMessage(error: OperationError | undefined, fallback: string): string {
  if (!error) return fallback;
  const code = String(error.code || "").trim().toUpperCase();
  const mapped = ERROR_CODE_PL[code];
  if (mapped) return `${mapped}${error.message ? ` (${error.message})` : ""}`;
  return error.message || fallback;
}

export function getPrimaryOperationMessage(result: OperationResult, fallback: string): string {
  if (!result) return fallback;
  if (result.status === "ok") return "";
  return getOperationErrorMessage(result.errors?.[0], fallback);
}

