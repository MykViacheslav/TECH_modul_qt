"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { Button, Card, Section } from "@/components/ui";
import { ArrowDownLeft, Search, AlertTriangle, Loader2, ArrowLeft, ChevronDown, ChevronRight, Pencil, Save, X } from "lucide-react";
import { TechModulAPI, type MaterialRecord, type LowStockItem, type ArrivalRecord } from "@/services/api";
import Link from "next/link";

function parseParamJson(raw?: string): Record<string, any> {
  const text = String(raw || "").trim();
  if (!text) return {};
  try {
    const parsed = JSON.parse(text);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function readParam(row: MaterialRecord, params: Record<string, any>, keys: string[]): string {
  for (const key of keys) {
    const fromParam = params?.[key];
    if (fromParam !== undefined && fromParam !== null && String(fromParam).trim() !== "") {
      return String(fromParam).trim();
    }
    const fromRow = (row as any)?.[key];
    if (fromRow !== undefined && fromRow !== null && String(fromRow).trim() !== "") {
      return String(fromRow).trim();
    }
  }
  return "";
}

function groupKey(row: MaterialRecord): string {
  const params = parseParamJson(row.parameter_json);
  const explicit = String(row.material_kind || row.category || "").trim().toLowerCase();
  if (explicit && !["other", "inne", "material", "misc"].includes(explicit)) return explicit;

  const name = String(row.name || "").toLowerCase();
  const unit = String(row.unit || "").toLowerCase();
  const ptext = JSON.stringify(params).toLowerCase();
  const text = `${name} ${ptext}`;

  if (text.includes("abs") || text.includes("pcv") || text.includes("oklein")) return "okleina";
  if (text.includes("hdf")) return "hdf";
  if (text.includes("mdf")) return "mdf";
  if (text.includes("fornir")) return "fornir";
  if (text.includes("lakier") || text.includes("farb") || text.includes("bejca") || text.includes("olej")) return "lakier";
  if (text.includes("zawias") || text.includes("prowadnic") || text.includes("uchwyt") || text.includes("wkret") || text.includes("okuc")) return "okucie";
  if (text.includes("blat") || text.includes("plyt") || text.includes("egger") || text.includes("krono") || text.includes("laminat")) return "plyta";
  if (unit === "mb") return "okleina";
  if (unit === "m2") return "plyta";
  if (unit === "szt") return "okucie";
  return "inne";
}

function groupLabel(key: string): string {
  const k = String(key || "").trim().toLowerCase();
  if (!k) return "Inne";
  return k.charAt(0).toUpperCase() + k.slice(1);
}

const DESKTOP_COLUMNS = [
  { key: "id", label: "ID" },
  { key: "typ", label: "TYP" },
  { key: "nazwa", label: "Nazwa" },
  { key: "kod", label: "Kod" },
  { key: "producent", label: "Producent" },
  { key: "ilosc", label: "Ilosc" },
  { key: "spisano", label: "Spisano na zamowienie" },
  { key: "pracownik", label: "Pracownik" },
  { key: "data_wpisu", label: "Data wpisu" },
  { key: "szerokosc", label: "Szerokosc" },
  { key: "dlugosc", label: "Dlugosc" },
  { key: "grubosc", label: "Grubosc" },
  { key: "parametry", label: "Parametry" },
  { key: "cena", label: "Cena [zl]" },
  { key: "magazyn", label: "Ilosc na magazynie" },
  { key: "min_stan", label: "Min. stan" },
  { key: "zakup", label: "Zakup" },
  { key: "faktura", label: "Numer faktury" },
  { key: "data_zakupu", label: "Data zakupu" },
  { key: "suma_zam_kw", label: "Suma zam. kw [zl]" },
  { key: "suma_za_szt", label: "Suma za szt [zl]" },
  { key: "magazyn_id", label: "Magazyn ID" },
  { key: "magazyn_nazwa", label: "Magazyn" },
  { key: "netto", label: "Netto / j." },
  { key: "brutto", label: "Brutto / j." },
  { key: "hurtownia", label: "Hurtownia" },
  { key: "status", label: "Status" },
] as const;

type DesktopColumnKey = (typeof DESKTOP_COLUMNS)[number]["key"];
type WarehouseTypeTabKey = "all" | "boards" | "hardware" | "paint" | "other";

const MATERIAL_TYPE_TABS: Array<{ key: WarehouseTypeTabKey; label: string }> = [
  { key: "all", label: "All" },
  { key: "boards", label: "Boards" },
  { key: "hardware", label: "Hardware" },
  { key: "paint", label: "Paint" },
  { key: "other", label: "Other" },
];

type TabColumnPrefs = {
  order: DesktopColumnKey[];
  visible: Record<DesktopColumnKey, boolean>;
  widths: Record<DesktopColumnKey, number>;
};
type FormFieldKey =
  | "material_id"
  | "quantity"
  | "unit"
  | "date"
  | "purchase_type"
  | "document_nr"
  | "unit_price_net"
  | "unit_price_gross"
  | "supplier"
  | "wholesaler";

const FORM_FIELDS: Array<{ key: FormFieldKey; label: string }> = [
  { key: "material_id", label: "Material" },
  { key: "quantity", label: "Ilosc" },
  { key: "unit", label: "Jednostka" },
  { key: "date", label: "Data wpisu" },
  { key: "purchase_type", label: "Typ zakupu" },
  { key: "document_nr", label: "Dokument / opis" },
  { key: "unit_price_net", label: "Cena netto / j." },
  { key: "unit_price_gross", label: "Cena brutto / j." },
  { key: "supplier", label: "Dostawca" },
  { key: "wholesaler", label: "Hurtownia" },
];

const COLUMN_TO_FORM_FIELD_MAP: Partial<Record<DesktopColumnKey, FormFieldKey[]>> = {
  nazwa: ["material_id"],
  ilosc: ["quantity"],
  data_wpisu: ["date"],
  data_zakupu: ["date"],
  zakup: ["purchase_type"],
  faktura: ["document_nr"],
  netto: ["unit_price_net"],
  brutto: ["unit_price_gross"],
  cena: ["unit_price_gross"],
  producent: ["supplier"],
  hurtownia: ["wholesaler"],
};

type ExtraFieldByTab = Record<string, DesktopColumnKey[]>;

function defaultFormVisibilityForTab(tab: string): Record<FormFieldKey, boolean> {
  const base = {
    material_id: true,
    quantity: true,
    unit: true,
    date: true,
    purchase_type: true,
    document_nr: true,
    unit_price_net: true,
    unit_price_gross: true,
    supplier: true,
    wholesaler: true,
  } as Record<FormFieldKey, boolean>;

  const t = String(tab || "").toLowerCase();
  if (t === "lakier" || t === "chemia") {
    base.unit = false;
  }
  return base;
}

function sanitizeFormVisibility(raw: any, tab: string): Record<FormFieldKey, boolean> {
  const defaults = defaultFormVisibilityForTab(tab);
  if (!raw || typeof raw !== "object") return defaults;
  const out = { ...defaults };
  for (const field of FORM_FIELDS) {
    const value = (raw as any)[field.key];
    if (typeof value === "boolean") out[field.key] = value;
  }
  if (!Object.values(out).some(Boolean)) out.material_id = true;
  return out;
}

function mapMaterialToTypeTab(row: MaterialRecord): WarehouseTypeTabKey {
  const category = String(row.category || "").trim().toLowerCase();
  const kind = String(row.material_kind || "").trim().toLowerCase();
  const key = groupKey(row);
  const text = `${category} ${kind} ${key}`.toLowerCase();

  if (
    text.includes("board") ||
    text.includes("plyta") ||
    text.includes("mdf") ||
    text.includes("hdf") ||
    text.includes("fornir") ||
    text.includes("okleina")
  ) {
    return "boards";
  }
  if (
    text.includes("hardware") ||
    text.includes("okucie") ||
    text.includes("zawias") ||
    text.includes("prowadnic") ||
    text.includes("uchwyt")
  ) {
    return "hardware";
  }
  if (
    text.includes("finish") ||
    text.includes("paint") ||
    text.includes("lakier") ||
    text.includes("farb") ||
    text.includes("bejca") ||
    text.includes("olej") ||
    text.includes("chemia")
  ) {
    return "paint";
  }
  return "other";
}

type PositionEditForm = {
  material_id: number;
  arrival_id: number | null;
  name: string;
  material_code: string;
  category: string;
  material_kind: string;
  unit: string;
  thickness: number;
  min_stock: number;
  purchase_type: string;
  supplier: string;
  wholesaler: string;
  quantity: number;
  date: string;
  document_nr: string;
  unit_price_net: number;
  unit_price_gross: number;
  price_total: number;
};

function buildDefaultTabPrefs(): TabColumnPrefs {
  const order = DESKTOP_COLUMNS.map((c) => c.key) as DesktopColumnKey[];
  const visible = {} as Record<DesktopColumnKey, boolean>;
  const widths = {} as Record<DesktopColumnKey, number>;
  for (const key of order) {
    visible[key] = true;
    widths[key] = 110;
  }
  return { order, visible, widths };
}

function sanitizeTabPrefs(raw: any): TabColumnPrefs {
  const defaults = buildDefaultTabPrefs();
  const allowed = new Set<DesktopColumnKey>(defaults.order);

  const orderInput = Array.isArray(raw?.order) ? raw.order : [];
  const safeOrder = orderInput.filter((key: unknown): key is DesktopColumnKey => typeof key === "string" && allowed.has(key as DesktopColumnKey));
  const order = [...safeOrder, ...defaults.order.filter((k) => !safeOrder.includes(k))];

  const visible = { ...defaults.visible };
  if (raw?.visible && typeof raw.visible === "object") {
    for (const key of defaults.order) {
      const value = (raw.visible as any)[key];
      if (typeof value === "boolean") visible[key] = value;
    }
  }
  if (!Object.values(visible).some(Boolean)) {
    visible[defaults.order[0]] = true;
  }

  const widths = { ...defaults.widths };
  if (raw?.widths && typeof raw.widths === "object") {
    for (const key of defaults.order) {
      const value = Number((raw.widths as any)[key] || 0);
      if (Number.isFinite(value) && value >= 70 && value <= 1200) widths[key] = value;
    }
  }

  return { order, visible, widths };
}

export default function WarehousePage() {
  const [materials, setMaterials] = useState<MaterialRecord[]>([]);
  const [lowStock, setLowStock] = useState<LowStockItem[]>([]);
  const [arrivals, setArrivals] = useState<ArrivalRecord[]>([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({});
  const [columnFilters, setColumnFilters] = useState<Record<string, string>>({});
  const [collapsedDesktopGroups, setCollapsedDesktopGroups] = useState<Record<string, boolean>>({});
  const [activeTypeTab, setActiveTypeTab] = useState<WarehouseTypeTabKey>("all");
  const [showColumnPanel, setShowColumnPanel] = useState(false);
  const [draggingCol, setDraggingCol] = useState<DesktopColumnKey | null>(null);
  const [draggingPanelColumn, setDraggingPanelColumn] = useState<DesktopColumnKey | null>(null);
  const [formDropActive, setFormDropActive] = useState(false);
  const [panelInfo, setPanelInfo] = useState<string | null>(null);
  const [columnPrefsByTab, setColumnPrefsByTab] = useState<Record<string, TabColumnPrefs>>({});
  const [formVisibilityByTab, setFormVisibilityByTab] = useState<Record<string, Record<FormFieldKey, boolean>>>({});
  const [extraFieldsByTab, setExtraFieldsByTab] = useState<ExtraFieldByTab>({});
  const [extraFieldValues, setExtraFieldValues] = useState<Record<string, string>>({});
  const [editingPosition, setEditingPosition] = useState<PositionEditForm | null>(null);
  const [editingSaving, setEditingSaving] = useState(false);
  const [selectedMaterialId, setSelectedMaterialId] = useState<number>(0);
  const [tableActionMsg, setTableActionMsg] = useState<string | null>(null);
  const viewMode: "quick" | "desktop" = "desktop";
  const resizeRef = useRef<{ key: string; startX: number; startW: number } | null>(null);
  const arrivalsFormRef = useRef<HTMLDivElement | null>(null);

  const [form, setForm] = useState({
    material_id: "",
    quantity: "",
    unit: "m2",
    date: new Date().toISOString().split("T")[0],
    purchase_type: "nothing",
    document_nr: "STAN_START",
    supplier: "",
    wholesaler: "",
    unit_price_net: "",
    unit_price_gross: "",
    price_total: "",
  });

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [matData, lowData] = await Promise.all([
        TechModulAPI.getMaterials(),
        TechModulAPI.getLowStockMaterials(),
      ]);
      const arrivalsData = await TechModulAPI.getArrivals();
      setMaterials(matData || []);
      setLowStock(lowData.items || []);
      setArrivals(arrivalsData || []);
    } catch (e: any) {
      setError(e?.message || "Blad ladowania magazynu");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem("warehouse_active_type_tab_v1");
      const key = String(saved || "").trim().toLowerCase();
      if (MATERIAL_TYPE_TABS.some((tab) => tab.key === key)) {
        setActiveTypeTab(key as WarehouseTypeTabKey);
      }
    } catch {}
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem("warehouse_active_type_tab_v1", activeTypeTab);
    } catch {}
  }, [activeTypeTab]);

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    const query = q.trim().toLowerCase();
    if (!query) return materials;
    return materials.filter((m) =>
      [
        m.name,
        m.material_code || "",
        m.material_kind || "",
        m.category || "",
        m.supplier || "",
        m.wholesaler || "",
        m.purchase_type || "",
        m.parameter_json || "",
      ].some((v) => String(v || "").toLowerCase().includes(query))
    );
  }, [materials, q]);

  const grouped = useMemo(() => {
    const map: Record<string, MaterialRecord[]> = {};
    for (const row of filtered) {
      const key = groupKey(row);
      if (!map[key]) map[key] = [];
      map[key].push(row);
    }
    const keys = Object.keys(map).sort((a, b) => a.localeCompare(b));
    return keys.map((key) => ({
      key,
      label: groupLabel(key),
      rows: map[key].sort((a, b) => String(a.name || "").localeCompare(String(b.name || ""))),
    }));
  }, [filtered]);

  const latestArrivalByMaterial = useMemo(() => {
    const out: Record<number, ArrivalRecord> = {};
    for (const row of arrivals) {
      const matId = Number(row.material_id || 0);
      if (!matId) continue;
      const current = out[matId];
      const currentDate = current?.date ? Date.parse(current.date) : 0;
      const nextDate = row?.date ? Date.parse(row.date) : 0;
      if (!current || nextDate >= currentDate) out[matId] = row;
    }
    return out;
  }, [arrivals]);

  const desktopColumns = DESKTOP_COLUMNS;

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem("warehouse_desktop_columns_v3");
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object") {
        const next: Record<string, TabColumnPrefs> = {};
        for (const [tabKey, prefs] of Object.entries(parsed)) {
          next[tabKey] = sanitizeTabPrefs(prefs);
        }
        setColumnPrefsByTab(next);
      }
    } catch {}
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem(
        "warehouse_desktop_columns_v3",
        JSON.stringify(columnPrefsByTab)
      );
    } catch {}
  }, [columnPrefsByTab]);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem("warehouse_form_fields_v1");
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== "object") return;
      const next: Record<string, Record<FormFieldKey, boolean>> = {};
      for (const [tabKey, value] of Object.entries(parsed)) {
        next[tabKey] = sanitizeFormVisibility(value, tabKey);
      }
      setFormVisibilityByTab(next);
    } catch {}
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem("warehouse_form_fields_v1", JSON.stringify(formVisibilityByTab));
    } catch {}
  }, [formVisibilityByTab]);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem("warehouse_extra_fields_v1");
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== "object") return;
      const next: ExtraFieldByTab = {};
      const allowed = new Set<DesktopColumnKey>(DESKTOP_COLUMNS.map((c) => c.key));
      for (const [tab, arr] of Object.entries(parsed)) {
        if (!Array.isArray(arr)) continue;
        const safe = arr.filter((k): k is DesktopColumnKey => typeof k === "string" && allowed.has(k as DesktopColumnKey));
        next[tab] = Array.from(new Set(safe));
      }
      setExtraFieldsByTab(next);
    } catch {}
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem("warehouse_extra_fields_v1", JSON.stringify(extraFieldsByTab));
    } catch {}
  }, [extraFieldsByTab]);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem("warehouse_extra_field_values_v1");
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object") {
        setExtraFieldValues(parsed as Record<string, string>);
      }
    } catch {}
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem("warehouse_extra_field_values_v1", JSON.stringify(extraFieldValues));
    } catch {}
  }, [extraFieldValues]);

  const activeTabPrefs = useMemo(() => {
    const current = columnPrefsByTab[activeTypeTab];
    if (current) return sanitizeTabPrefs(current);
    const shared = columnPrefsByTab["all"];
    if (shared) return sanitizeTabPrefs(shared);
    return buildDefaultTabPrefs();
  }, [columnPrefsByTab, activeTypeTab]);

  const orderedColumns = useMemo(() => {
    const ordered = activeTabPrefs.order
      .map((key) => desktopColumns.find((c) => c.key === key))
      .filter((c): c is (typeof DESKTOP_COLUMNS)[number] => !!c);
    return ordered.filter((c) => activeTabPrefs.visible[c.key]);
  }, [desktopColumns, activeTabPrefs]);

  const setActiveTabPrefs = (updater: (prev: TabColumnPrefs) => TabColumnPrefs) => {
    setColumnPrefsByTab((prev) => {
      const base = prev[activeTypeTab] ?? prev["all"] ?? buildDefaultTabPrefs();
      const next = sanitizeTabPrefs(updater(sanitizeTabPrefs(base)));
      return { ...prev, [activeTypeTab]: next };
    });
  };

  const activeFormVisibility = useMemo(() => {
    return sanitizeFormVisibility(
      formVisibilityByTab[activeTypeTab] ?? formVisibilityByTab["all"],
      activeTypeTab
    );
  }, [formVisibilityByTab, activeTypeTab]);

  const setActiveFormVisibility = (
    updater: (prev: Record<FormFieldKey, boolean>) => Record<FormFieldKey, boolean>
  ) => {
    setFormVisibilityByTab((prev) => {
      const current = sanitizeFormVisibility(prev[activeTypeTab] ?? prev["all"], activeTypeTab);
      const next = sanitizeFormVisibility(updater(current), activeTypeTab);
      return { ...prev, [activeTypeTab]: next };
    });
  };

  const toggleFormField = (key: FormFieldKey) => {
    setActiveFormVisibility((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      if (!Object.values(next).some(Boolean)) next[key] = true;
      return next;
    });
  };

  const resetDesktopColumns = () => {
    setColumnPrefsByTab((prev) => {
      const next = { ...prev };
      delete next[activeTypeTab];
      return next;
    });
  };

  const resetAllDesktopColumns = () => {
    setColumnPrefsByTab({});
    try {
      window.localStorage.removeItem("warehouse_desktop_columns_v1");
      window.localStorage.removeItem("warehouse_desktop_columns_v2");
      window.localStorage.removeItem("warehouse_desktop_columns_v3");
    } catch {}
  };

  const moveColumn = (fromKey: DesktopColumnKey, toKey: DesktopColumnKey) => {
    if (!fromKey || !toKey || fromKey === toKey) return;
    setActiveTabPrefs((prev) => {
      const list = [...prev.order];
      const from = list.indexOf(fromKey);
      const to = list.indexOf(toKey);
      if (from < 0 || to < 0) return prev;
      const [item] = list.splice(from, 1);
      list.splice(to, 0, item);
      return { ...prev, order: list };
    });
  };

  const toggleColumnVisible = (key: DesktopColumnKey) => {
    setActiveTabPrefs((prev) => {
      const nextVisible = { ...prev.visible, [key]: !prev.visible[key] };
      if (!Object.values(nextVisible).some(Boolean)) {
        nextVisible[key] = true;
      }
      return { ...prev, visible: nextVisible };
    });
  };

  const showAllColumns = () => {
    setActiveTabPrefs((prev) => {
      const nextVisible = { ...prev.visible };
      for (const c of desktopColumns) nextVisible[c.key] = true;
      return { ...prev, visible: nextVisible };
    });
  };

  const showAllFormFields = () => {
    setActiveFormVisibility((prev) => {
      const next = { ...prev };
      for (const field of FORM_FIELDS) next[field.key] = true;
      return next;
    });
  };

  const columnLabelByKey = useMemo(() => {
    const out = {} as Record<DesktopColumnKey, string>;
    for (const col of desktopColumns) out[col.key] = col.label;
    return out;
  }, [desktopColumns]);

  const applyColumnToForm = (columnKey: DesktopColumnKey) => {
    const mapped = COLUMN_TO_FORM_FIELD_MAP[columnKey] || [];
    if (!mapped.length) {
      setExtraFieldsByTab((prev) => {
        const current = prev[activeTypeTab] || [];
        if (current.includes(columnKey)) return prev;
        return { ...prev, [activeTypeTab]: [...current, columnKey] };
      });
      const valueKey = `${activeTypeTab}:${columnKey}`;
      setExtraFieldValues((prev) => (valueKey in prev ? prev : { ...prev, [valueKey]: "" }));
      setPanelInfo(`Dodano "${columnLabelByKey[columnKey]}" jako pole dodatkowe po lewej stronie.`);
      return;
    }
    setActiveFormVisibility((prev) => {
      const next = { ...prev };
      for (const field of mapped) next[field] = true;
      return next;
    });
    setPanelInfo(`Dodano kolumne "${columnLabelByKey[columnKey]}" do pol panelu po lewej.`);
  };

  const activeExtraFields = useMemo(() => {
    const allFields = extraFieldsByTab["all"] || [];
    const tabFields = extraFieldsByTab[activeTypeTab] || [];
    return Array.from(new Set([...allFields, ...tabFields]));
  }, [extraFieldsByTab, activeTypeTab]);

  const removeExtraField = (columnKey: DesktopColumnKey) => {
    setExtraFieldsByTab((prev) => {
      const inActive = (prev[activeTypeTab] || []).includes(columnKey);
      if (inActive) {
        return {
          ...prev,
          [activeTypeTab]: (prev[activeTypeTab] || []).filter((k) => k !== columnKey),
        };
      }
      return {
        ...prev,
        all: (prev.all || []).filter((k) => k !== columnKey),
      };
    });
  };

  const onFormDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setFormDropActive(false);
    if (!draggingPanelColumn) return;
    applyColumnToForm(draggingPanelColumn);
    setDraggingPanelColumn(null);
  };

  const onResizeMouseDown = (key: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const startW = Number(activeTabPrefs.widths[key as DesktopColumnKey] || 110);
    resizeRef.current = { key, startX: e.clientX, startW };
    const onMove = (ev: MouseEvent) => {
      const ref = resizeRef.current;
      if (!ref) return;
      const next = Math.max(70, Math.min(1200, ref.startW + (ev.clientX - ref.startX)));
      setActiveTabPrefs((prev) => ({
        ...prev,
        widths: { ...prev.widths, [ref.key as DesktopColumnKey]: next },
      }));
    };
    const onUp = () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
      resizeRef.current = null;
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  };

  const desktopRows = useMemo(() => {
    return filtered.map((row) => {
      const latest = latestArrivalByMaterial[row.id];
      const params = parseParamJson(row.parameter_json);
      const width = readParam(row, params, ["format_width_mm", "width_mm", "width"]);
      const length = readParam(row, params, ["format_length_mm", "length_mm", "length"]);
      const thickness = readParam(row, params, ["thickness", "thickness_mm", "grubosc_mm"]);
      const status = row.is_low_stock ? "NISKI_STAN" : "OK";
      return {
        id: String(row.id),
        typ: groupKey(row),
        nazwa: String(row.name || ""),
        kod: String(row.material_code || "NO-CODE"),
        producent: String(latest?.supplier || row.supplier || ""),
        ilosc: Number(latest?.quantity || 0).toFixed(2),
        spisano: "-",
        pracownik: "-",
        data_wpisu: String(latest?.date || ""),
        szerokosc: width ? `${width}` : "",
        dlugosc: length ? `${length}` : "",
        grubosc: thickness ? `${thickness}` : String(row.thickness || ""),
        parametry: String(row.parameter_json || ""),
        cena: Number(row.price || 0).toFixed(2),
        magazyn: `${Number(row.stock_quantity || 0).toFixed(1)} ${row.unit || ""}`.trim(),
        min_stan: `${Number(row.min_stock || 0).toFixed(1)} ${row.unit || ""}`.trim(),
        zakup: String(latest?.purchase_type || row.purchase_type || "nothing"),
        faktura: String(latest?.document_nr || ""),
        data_zakupu: String(latest?.date || ""),
        suma_zam_kw: Number((latest?.quantity || 0) * (latest?.unit_price_net || 0)).toFixed(2),
        suma_za_szt: Number((latest?.quantity || 0) * (latest?.unit_price_gross || 0)).toFixed(2),
        magazyn_id: "1",
        magazyn_nazwa: "MAGAZYN GLOWNY",
        netto: Number(latest?.unit_price_net || 0).toFixed(2),
        brutto: Number(latest?.unit_price_gross || 0).toFixed(2),
        hurtownia: String(latest?.wholesaler || row.wholesaler || ""),
        status,
        _material_id: Number(row.id),
        _arrival_id: latest?.id ? Number(latest.id) : null,
        _category: String(row.category || ""),
        _material_kind: String(row.material_kind || ""),
        _unit: String(row.unit || "m2"),
        _thickness: Number(row.thickness || 0),
        _min_stock: Number(row.min_stock || 0),
        _purchase_type: String(latest?.purchase_type || row.purchase_type || "nothing"),
        _quantity: Number(latest?.quantity || 0),
        _document_nr: String(latest?.document_nr || ""),
        _date: String(latest?.date || ""),
        _supplier: String(latest?.supplier || row.supplier || ""),
        _wholesaler: String(latest?.wholesaler || row.wholesaler || ""),
        _unit_price_net: Number(latest?.unit_price_net || 0),
        _unit_price_gross: Number(latest?.unit_price_gross || 0),
        _price_total: Number(latest?.price_total || 0),
        _price_per_m2: Number(row.price || 0),
      };
    });
  }, [filtered, latestArrivalByMaterial]);

  const desktopFilteredRows = useMemo(() => {
    return desktopRows.filter((row) =>
      desktopColumns.every((col) => {
        const needle = String(columnFilters[col.key] || "").trim().toLowerCase();
        if (!needle) return true;
        return String((row as any)[col.key] || "").toLowerCase().includes(needle);
      })
    );
  }, [desktopRows, desktopColumns, columnFilters]);

  const desktopGroupedRows = useMemo(() => {
    const map: Record<string, typeof desktopFilteredRows> = {};
    for (const row of desktopFilteredRows) {
      const key = String(row.typ || "inne").toLowerCase();
      if (!map[key]) map[key] = [];
      map[key].push(row);
    }
    return Object.keys(map)
      .sort((a, b) => a.localeCompare(b))
      .map((key) => ({
        key,
        label: groupLabel(key),
        rows: map[key].sort((a, b) => String(a.nazwa || "").localeCompare(String(b.nazwa || ""))),
      }));
  }, [desktopFilteredRows]);

  const desktopTabs = useMemo(() => {
    const counters: Record<WarehouseTypeTabKey, number> = {
      all: desktopFilteredRows.length,
      boards: 0,
      hardware: 0,
      paint: 0,
      other: 0,
    };
    for (const row of desktopFilteredRows) {
      const material = materials.find((m) => Number(m.id) === Number(row._material_id));
      if (!material) continue;
      const bucket = mapMaterialToTypeTab(material);
      counters[bucket] += 1;
    }
    return MATERIAL_TYPE_TABS.map((tab) => ({ ...tab, count: counters[tab.key] }));
  }, [desktopFilteredRows, materials]);

  const activeDesktopRows = useMemo(() => {
    if (activeTypeTab === "all") return desktopFilteredRows;
    return desktopFilteredRows.filter((row) => {
      const material = materials.find((m) => Number(m.id) === Number(row._material_id));
      return !!material && mapMaterialToTypeTab(material) === activeTypeTab;
    });
  }, [desktopFilteredRows, activeTypeTab, materials]);

  const selectedDesktopRow = useMemo(() => {
    if (!selectedMaterialId) return null;
    return desktopRows.find((row) => Number(row._material_id || 0) === Number(selectedMaterialId)) || null;
  }, [desktopRows, selectedMaterialId]);

  const focusArrivalForm = () => {
    arrivalsFormRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    setTableActionMsg("Uzupelnij pola po lewej i kliknij \"Zapisz Przyjecie\".");
  };

  const startEditSelected = () => {
    if (!selectedDesktopRow) {
      setTableActionMsg("Najpierw wybierz wiersz w tabeli.");
      return;
    }
    beginEditPosition(selectedDesktopRow);
    setTableActionMsg(`Wlaczono edycje pozycji #${selectedDesktopRow._material_id}.`);
  };

  const moveTypeSelected = async () => {
    if (!selectedDesktopRow) {
      setTableActionMsg("Najpierw wybierz wiersz, aby przeniesc typ.");
      return;
    }
    const next = window.prompt(
      "Podaj nowy typ: boards / hardware / paint / other",
      String(selectedDesktopRow.typ || "other")
    );
    if (!next) return;
    const normalized = String(next || "").trim().toLowerCase();
    const allowed = new Set(["boards", "hardware", "paint", "other"]);
    if (!allowed.has(normalized)) {
      setTableActionMsg("Niepoprawny typ. Uzyj: boards / hardware / paint / other.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await TechModulAPI.updateMaterial(Number(selectedDesktopRow._material_id || 0), {
        material_kind: normalized,
        category: normalized,
      });
      setTableActionMsg(`Przeniesiono pozycje #${selectedDesktopRow._material_id} do typu ${normalized}.`);
      await load();
    } catch (e: any) {
      setError(e?.message || "Blad zmiany typu");
    } finally {
      setSaving(false);
    }
  };

  const exportVisibleRowsCsv = () => {
    const rows = activeDesktopRows;
    const cols = orderedColumns;
    const escape = (value: unknown) => {
      const text = String(value ?? "");
      const safe = text.replace(/"/g, "\"\"");
      return `"${safe}"`;
    };
    const header = cols.map((c) => escape(c.label)).join(";");
    const body = rows.map((row) => cols.map((c) => escape((row as any)[c.key])).join(";")).join("\n");
    const csv = `${header}\n${body}`;
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `warehouse_${activeTypeTab}_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    setTableActionMsg(`Wyeksportowano ${rows.length} wierszy do CSV.`);
  };

  const toggleGroup = (key: string) => {
    setCollapsedGroups((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleReceive = async () => {
    if (!form.material_id) return;
    setSaving(true);
    setError(null);
    try {
      await TechModulAPI.createArrival({
        material_id: parseInt(form.material_id, 10),
        quantity: parseFloat((form.quantity || "0").replace(",", ".")) || 0,
        unit: form.unit,
        purchase_type: form.purchase_type,
        document_nr: (form.document_nr || "").trim() || "STAN_START",
        price_total:
          parseFloat((form.price_total || "0").replace(",", ".")) ||
          (parseFloat((form.quantity || "0").replace(",", ".")) || 0) *
            (parseFloat((form.unit_price_gross || "0").replace(",", ".")) || 0),
        date: form.date || new Date().toISOString().split("T")[0],
        order_id: null,
        supplier: (form.supplier || "").trim(),
        wholesaler: (form.wholesaler || "").trim(),
        unit_price_net: parseFloat((form.unit_price_net || "0").replace(",", ".")) || 0,
        unit_price_gross: parseFloat((form.unit_price_gross || "0").replace(",", ".")) || 0,
      });
      setForm((prev) => ({
        ...prev,
        material_id: "",
        quantity: "",
        unit_price_net: "",
        unit_price_gross: "",
        price_total: "",
      }));
      await load();
    } catch (e: any) {
      setError(e?.message || "Blad zapisu przyjecia");
    } finally {
      setSaving(false);
    }
  };

  const beginEditPosition = (row: any) => {
    setError(null);
    setEditingPosition({
      material_id: Number(row._material_id || 0),
      arrival_id: row._arrival_id ? Number(row._arrival_id) : null,
      name: String(row.nazwa || ""),
      material_code: String(row.kod || "").replace(/^NO-CODE$/i, ""),
      category: String(row._category || "boards"),
      material_kind: String(row._material_kind || row.typ || "inne"),
      unit: String(row._unit || "m2"),
      thickness: Number(row._thickness || 0),
      min_stock: Number(row._min_stock || 0),
      purchase_type: String(row._purchase_type || "nothing"),
      supplier: String(row._supplier || ""),
      wholesaler: String(row._wholesaler || ""),
      quantity: Number(row._quantity || 0),
      date: String(row._date || new Date().toISOString().split("T")[0]),
      document_nr: String(row._document_nr || "STAN_START"),
      unit_price_net: Number(row._unit_price_net || 0),
      unit_price_gross: Number(row._unit_price_gross || 0),
      price_total: Number(row._price_total || 0),
    });
  };

  const saveEditedPosition = async () => {
    if (!editingPosition) return;
    setEditingSaving(true);
    setError(null);
    try {
      await TechModulAPI.updateMaterial(editingPosition.material_id, {
        name: editingPosition.name.trim(),
        material_code: editingPosition.material_code.trim(),
        category: editingPosition.category.trim() || "boards",
        material_kind: editingPosition.material_kind.trim() || "inne",
        unit: editingPosition.unit,
        thickness: Number(editingPosition.thickness || 0),
        min_stock: Number(editingPosition.min_stock || 0),
        purchase_type: editingPosition.purchase_type,
        supplier: editingPosition.supplier.trim(),
        wholesaler: editingPosition.wholesaler.trim(),
        price_per_m2: Number(editingPosition.unit_price_gross || 0),
      });

      if (editingPosition.arrival_id) {
        await TechModulAPI.updateArrival(editingPosition.arrival_id, {
          quantity: Number(editingPosition.quantity || 0),
          unit: editingPosition.unit,
          purchase_type: editingPosition.purchase_type,
          document_nr: editingPosition.document_nr.trim() || "STAN_START",
          supplier: editingPosition.supplier.trim(),
          wholesaler: editingPosition.wholesaler.trim(),
          unit_price_net: Number(editingPosition.unit_price_net || 0),
          unit_price_gross: Number(editingPosition.unit_price_gross || 0),
          price_total: Number(
            editingPosition.price_total ||
            Number(editingPosition.quantity || 0) * Number(editingPosition.unit_price_gross || 0)
          ),
          date: editingPosition.date,
        });
      } else if (Number(editingPosition.quantity || 0) > 0) {
        await TechModulAPI.createArrival({
          material_id: editingPosition.material_id,
          order_id: null,
          quantity: Number(editingPosition.quantity || 0),
          unit: editingPosition.unit,
          purchase_type: editingPosition.purchase_type,
          document_nr: editingPosition.document_nr.trim() || "STAN_START",
          supplier: editingPosition.supplier.trim(),
          wholesaler: editingPosition.wholesaler.trim(),
          unit_price_net: Number(editingPosition.unit_price_net || 0),
          unit_price_gross: Number(editingPosition.unit_price_gross || 0),
          price_total: Number(
            editingPosition.price_total ||
            Number(editingPosition.quantity || 0) * Number(editingPosition.unit_price_gross || 0)
          ),
          date: editingPosition.date || new Date().toISOString().split("T")[0],
        });
      }

      await load();
      setEditingPosition(null);
    } catch (e: any) {
      setError(e?.message || "Blad edycji pozycji");
    } finally {
      setEditingSaving(false);
    }
  };

  const isEditingRow = (row: any) => {
    if (!editingPosition) return false;
    return Number(row?._material_id || 0) === Number(editingPosition.material_id || 0);
  };

  const renderRowCell = (row: any, col: (typeof DESKTOP_COLUMNS)[number]) => {
    const plainValue = String((row as any)[col.key] || "-");
    if (!isEditingRow(row) || !editingPosition) return plainValue;

    const inputClass =
      "w-full bg-canvas-deep border border-subtle rounded-lg px-2 py-1 text-[11px] text-white";

    switch (col.key) {
      case "id":
        return String(editingPosition.material_id);
      case "typ":
        return (
          <input
            className={inputClass}
            value={editingPosition.material_kind}
            onChange={(e) =>
              setEditingPosition((p) => (p ? { ...p, material_kind: e.target.value } : p))
            }
          />
        );
      case "nazwa":
        return (
          <input
            className={inputClass}
            value={editingPosition.name}
            onChange={(e) => setEditingPosition((p) => (p ? { ...p, name: e.target.value } : p))}
          />
        );
      case "kod":
        return (
          <input
            className={inputClass}
            value={editingPosition.material_code}
            onChange={(e) =>
              setEditingPosition((p) => (p ? { ...p, material_code: e.target.value } : p))
            }
          />
        );
      case "producent":
        return (
          <input
            className={inputClass}
            value={editingPosition.supplier}
            onChange={(e) =>
              setEditingPosition((p) => (p ? { ...p, supplier: e.target.value } : p))
            }
          />
        );
      case "ilosc":
        return (
          <input
            type="number"
            step="0.01"
            className={inputClass}
            value={editingPosition.quantity}
            onChange={(e) =>
              setEditingPosition((p) => (p ? { ...p, quantity: Number(e.target.value || 0) } : p))
            }
          />
        );
      case "data_wpisu":
      case "data_zakupu":
        return (
          <input
            type="date"
            className={inputClass}
            value={editingPosition.date}
            onChange={(e) => setEditingPosition((p) => (p ? { ...p, date: e.target.value } : p))}
          />
        );
      case "zakup":
        return (
          <select
            className={inputClass}
            value={editingPosition.purchase_type}
            onChange={(e) =>
              setEditingPosition((p) => (p ? { ...p, purchase_type: e.target.value } : p))
            }
          >
            <option value="invoice">Faktura</option>
            <option value="cash">Gotowka</option>
            <option value="nothing">Bez dokumentu</option>
          </select>
        );
      case "faktura":
        return (
          <input
            className={inputClass}
            value={editingPosition.document_nr}
            onChange={(e) =>
              setEditingPosition((p) => (p ? { ...p, document_nr: e.target.value } : p))
            }
          />
        );
      case "netto":
        return (
          <input
            type="number"
            step="0.01"
            className={inputClass}
            value={editingPosition.unit_price_net}
            onChange={(e) =>
              setEditingPosition((p) =>
                p ? { ...p, unit_price_net: Number(e.target.value || 0) } : p
              )
            }
          />
        );
      case "brutto":
      case "cena":
        return (
          <input
            type="number"
            step="0.01"
            className={inputClass}
            value={editingPosition.unit_price_gross}
            onChange={(e) =>
              setEditingPosition((p) =>
                p ? { ...p, unit_price_gross: Number(e.target.value || 0) } : p
              )
            }
          />
        );
      case "hurtownia":
        return (
          <input
            className={inputClass}
            value={editingPosition.wholesaler}
            onChange={(e) =>
              setEditingPosition((p) => (p ? { ...p, wholesaler: e.target.value } : p))
            }
          />
        );
      case "grubosc":
        return (
          <input
            type="number"
            step="0.01"
            className={inputClass}
            value={editingPosition.thickness}
            onChange={(e) =>
              setEditingPosition((p) => (p ? { ...p, thickness: Number(e.target.value || 0) } : p))
            }
          />
        );
      case "min_stan":
        return (
          <input
            type="number"
            step="0.01"
            className={inputClass}
            value={editingPosition.min_stock}
            onChange={(e) =>
              setEditingPosition((p) => (p ? { ...p, min_stock: Number(e.target.value || 0) } : p))
            }
          />
        );
      default:
        return plainValue;
    }
  };

  const renderDesktopRow = (row: any) => {
    const rowEditing = isEditingRow(row);
    const rowSelected = Number(row._material_id || 0) === Number(selectedMaterialId || 0);
    return (
      <tr
        key={row.id}
        onClick={() => {
          setSelectedMaterialId(Number(row._material_id || 0));
          setTableActionMsg(null);
        }}
        className={`border-b border-subtle transition-colors align-top cursor-pointer ${
          rowSelected ? "bg-emerald-500/10" : "hover:bg-emerald-500/5"
        }`}
      >
        {orderedColumns.map((col) => (
          <td
            key={`${row.id}-${col.key}`}
            className="p-2 text-[11px] text-slate-200 whitespace-nowrap"
            style={{ width: activeTabPrefs.widths[col.key] || 110, minWidth: 70 }}
          >
            {renderRowCell(row, col)}
          </td>
        ))}
        <td className="p-2 text-right">
          {rowEditing ? (
            <div className="inline-flex items-center gap-1">
              <button
                type="button"
                onClick={saveEditedPosition}
                disabled={editingSaving}
                className="inline-flex items-center gap-1 px-2 py-1 rounded-md border border-emerald-500/50 bg-emerald-500/15 hover:bg-emerald-500/25 text-[10px] uppercase tracking-wider font-black disabled:opacity-60"
              >
                {editingSaving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
                Zapisz
              </button>
              <button
                type="button"
                onClick={() => setEditingPosition(null)}
                disabled={editingSaving}
                className="inline-flex items-center gap-1 px-2 py-1 rounded-md border border-subtle bg-white/5 hover:bg-white/10 text-[10px] uppercase tracking-wider font-black disabled:opacity-60"
              >
                <X size={12} />
                Anuluj
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => beginEditPosition(row)}
              className="inline-flex items-center gap-1 px-2 py-1 rounded-md border border-subtle bg-white/5 hover:bg-white/10 text-[10px] uppercase tracking-wider font-black"
            >
              <Pencil size={12} />
              Edytuj
            </button>
          )}
        </td>
      </tr>
    );
  };

  return (
    <div className="flex h-[calc(100vh-140px)] gap-6 overflow-hidden">
      <aside className="w-80 flex flex-col gap-6">
        <div className="px-1">
          <Link
            href="/database"
            className="inline-flex items-center gap-2 text-[10px] text-slate-500 hover:text-brand font-black uppercase tracking-widest group transition-colors"
          >
            <ArrowLeft size={10} className="group-hover:-translate-x-1 transition-transform" />
            Powrot do Centrum Baz
          </Link>
        </div>
        <Section title="Przyjecia Towaru">
          <div ref={arrivalsFormRef}>
          <Card className="space-y-4">
            {activeFormVisibility.material_id && (
            <div className="space-y-1.5">
              <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Material</label>
              <select
                className="w-full bg-canvas-deep border border-subtle rounded-xl px-3 py-2 text-sm text-white"
                value={form.material_id}
                onChange={(e) => setForm((f) => ({ ...f, material_id: e.target.value }))}
              >
                <option value="">Wybierz z katalogu...</option>
                {materials.map((m) => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
              </select>
            </div>
            )}

            {(activeFormVisibility.quantity || activeFormVisibility.unit) && (
            <div className="grid grid-cols-2 gap-4">
              {activeFormVisibility.quantity && (
              <div className="space-y-1.5">
                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Ilosc</label>
                <input
                  type="number"
                  placeholder="0.00"
                  className="w-full bg-canvas-deep border border-subtle rounded-xl px-3 py-2 text-sm text-white"
                  value={form.quantity}
                  onChange={(e) => setForm((f) => ({ ...f, quantity: e.target.value }))}
                />
              </div>
              )}
              {activeFormVisibility.unit && (
              <div className="space-y-1.5">
                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Jednostka</label>
                <select
                  className="w-full bg-canvas-deep border border-subtle rounded-xl px-3 py-2 text-sm text-white"
                  value={form.unit}
                  onChange={(e) => setForm((f) => ({ ...f, unit: e.target.value }))}
                >
                  <option value="m2">m2</option>
                  <option value="szt">szt</option>
                  <option value="mb">mb</option>
                </select>
              </div>
              )}
            </div>
            )}

            {(activeFormVisibility.date || activeFormVisibility.purchase_type) && (
            <div className="grid grid-cols-2 gap-4">
              {activeFormVisibility.date && (
              <div className="space-y-1.5">
                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Data wpisu</label>
                <input
                  type="date"
                  className="w-full bg-canvas-deep border border-subtle rounded-xl px-3 py-2 text-sm text-white"
                  value={form.date}
                  onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))}
                />
              </div>
              )}
              {activeFormVisibility.purchase_type && (
              <div className="space-y-1.5">
                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Typ zakupu</label>
                <select
                  className="w-full bg-canvas-deep border border-subtle rounded-xl px-3 py-2 text-sm text-white"
                  value={form.purchase_type}
                  onChange={(e) => setForm((f) => ({ ...f, purchase_type: e.target.value }))}
                >
                  <option value="invoice">Faktura</option>
                  <option value="cash">Gotowka</option>
                  <option value="nothing">Bez dokumentu</option>
                </select>
              </div>
              )}
            </div>
            )}

            {activeFormVisibility.document_nr && (
            <div className="space-y-1.5">
              <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Dokument / Opis</label>
              <input
                type="text"
                placeholder="FV/2026/... lub STAN_START"
                className="w-full bg-canvas-deep border border-subtle rounded-xl px-3 py-2 text-sm text-white"
                value={form.document_nr}
                onChange={(e) => setForm((f) => ({ ...f, document_nr: e.target.value }))}
              />
            </div>
            )}

            {(activeFormVisibility.unit_price_net || activeFormVisibility.unit_price_gross) && (
            <div className="grid grid-cols-2 gap-4">
              {activeFormVisibility.unit_price_net && (
              <div className="space-y-1.5">
                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Cena netto / j.</label>
                <input
                  type="number"
                  placeholder="0.00"
                  className="w-full bg-canvas-deep border border-subtle rounded-xl px-3 py-2 text-sm text-white"
                  value={form.unit_price_net}
                  onChange={(e) => setForm((f) => ({ ...f, unit_price_net: e.target.value }))}
                />
              </div>
              )}
              {activeFormVisibility.unit_price_gross && (
              <div className="space-y-1.5">
                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Cena brutto / j.</label>
                <input
                  type="number"
                  placeholder="0.00"
                  className="w-full bg-canvas-deep border border-subtle rounded-xl px-3 py-2 text-sm text-white"
                  value={form.unit_price_gross}
                  onChange={(e) => setForm((f) => ({ ...f, unit_price_gross: e.target.value }))}
                />
              </div>
              )}
            </div>
            )}

            {(activeFormVisibility.supplier || activeFormVisibility.wholesaler) && (
            <div className="grid grid-cols-2 gap-4">
              {activeFormVisibility.supplier && (
              <div className="space-y-1.5">
                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Faktura czyja (dostawca)</label>
                <input
                  type="text"
                  placeholder="np. EGGER"
                  className="w-full bg-canvas-deep border border-subtle rounded-xl px-3 py-2 text-sm text-white"
                  value={form.supplier}
                  onChange={(e) => setForm((f) => ({ ...f, supplier: e.target.value }))}
                />
              </div>
              )}
              {activeFormVisibility.wholesaler && (
              <div className="space-y-1.5">
                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Hurtownia</label>
                <input
                  type="text"
                  placeholder="np. Kronospan"
                  className="w-full bg-canvas-deep border border-subtle rounded-xl px-3 py-2 text-sm text-white"
                  value={form.wholesaler}
                  onChange={(e) => setForm((f) => ({ ...f, wholesaler: e.target.value }))}
                />
              </div>
              )}
            </div>
            )}

            {activeExtraFields.length > 0 && (
              <div className="space-y-2 border-t border-subtle pt-3">
                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Dodatkowe pola (z kolumn)</p>
                <div className="space-y-2">
                  {activeExtraFields.map((colKey) => {
                    const tabStorageKey = `${activeTypeTab}:${colKey}`;
                    const allStorageKey = `all:${colKey}`;
                    const resolvedValue =
                      extraFieldValues[tabStorageKey] ??
                      extraFieldValues[allStorageKey] ??
                      "";
                    return (
                      <div key={`extra-left-${colKey}`} className="space-y-1.5">
                        <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">
                          {columnLabelByKey[colKey]}
                        </label>
                        <input
                          type="text"
                          placeholder="Wpisz wartosc..."
                          className="w-full bg-canvas-deep border border-subtle rounded-xl px-3 py-2 text-sm text-white"
                          value={resolvedValue}
                          onChange={(e) =>
                            setExtraFieldValues((prev) => ({ ...prev, [tabStorageKey]: e.target.value }))
                          }
                        />
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-2">
              <Button variant="primary" className="w-full !bg-emerald-600 hover:!bg-emerald-500" onClick={handleReceive} disabled={saving || !form.material_id}>
                {saving ? <Loader2 size={16} className="animate-spin" /> : <ArrowDownLeft size={16} />}
                Zapisz Przyjecie
              </Button>
              <Button
                variant="ghost"
                className="w-full !px-3 !py-2 text-xs"
                onClick={() =>
                  setForm((prev) => ({
                    ...prev,
                    material_id: "",
                    quantity: "",
                    unit_price_net: "",
                    unit_price_gross: "",
                    price_total: "",
                    supplier: "",
                    wholesaler: "",
                  }))
                }
              >
                Clear form
              </Button>
            </div>
          </Card>
          </div>
        </Section>

        <Section title="Alerty Magazynu">
          <Card className="space-y-2">
            <div className="flex items-center gap-2 text-rose-300">
              <AlertTriangle size={14} />
              <span className="text-[11px] font-black uppercase tracking-widest">Niski stan: {lowStock.length}</span>
            </div>
            <p className="text-[10px] text-slate-500 uppercase tracking-wider">
              System automatycznie pokazuje pozycje ponizej minimum.
            </p>
          </Card>
        </Section>
      </aside>

      <main className="flex-1 flex flex-col gap-4 overflow-hidden">
        <header className="flex items-center justify-between gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
            <input
              type="text"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Szukaj w magazynie..."
              className="w-full bg-panel-solid/60 border border-subtle rounded-xl pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500/50 transition-colors"
            />
          </div>
          <button
            type="button"
            onClick={() => setShowColumnPanel((v) => !v)}
            className="px-3 py-2 text-[10px] uppercase tracking-wider font-black rounded-lg border border-subtle bg-white/5 hover:bg-white/10 text-slate-300"
          >
            Kolumny
          </button>
          <button
            type="button"
            onClick={resetDesktopColumns}
            className="px-3 py-2 text-[10px] uppercase tracking-wider font-black rounded-lg border border-subtle bg-white/5 hover:bg-white/10 text-slate-300"
          >
            Reset zakladki
          </button>
          <button
            type="button"
            onClick={resetAllDesktopColumns}
            className="px-3 py-2 text-[10px] uppercase tracking-wider font-black rounded-lg border border-subtle bg-white/5 hover:bg-white/10 text-slate-300"
          >
            Reset wszystkich
          </button>
          <div className="text-[11px] text-slate-400 font-bold">Widok desktop (pelne kolumny)  Typy: 5</div>
        </header>

        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          {desktopTabs.map((tab) => {
            const isActive = activeTypeTab === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTypeTab(tab.key)}
                className={`shrink-0 px-3 py-1.5 rounded-lg text-[11px] uppercase tracking-wider font-black border transition-colors ${
                  isActive
                    ? "bg-emerald-600/20 border-emerald-500/60 text-emerald-300"
                    : "bg-white/5 border-subtle text-slate-300 hover:bg-white/10"
                }`}
              >
                {tab.label} ({tab.count})
              </button>
            );
          })}
        </div>

        {error && (
          <Card className="border-rose-500/30 bg-rose-500/5">
            <p className="text-sm text-rose-300">{error}</p>
          </Card>
        )}

        {lowStock.length > 0 && (
          <Card className="border-rose-500/30 bg-rose-500/5">
            <p className="text-[11px] font-black uppercase tracking-widest text-rose-300 mb-2">
              Materialy do pilnego dokupienia
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {lowStock.slice(0, 8).map((item) => (
                <div key={item.id} className="rounded-lg border border-rose-500/20 bg-black/20 px-3 py-2">
                  <p className="text-[11px] font-bold text-white">{item.name}</p>
                  <p className="text-[10px] text-slate-300 uppercase">
                    stan {item.stock_quantity} {item.unit} - min {item.min_stock} - brakuje {item.missing_qty}
                  </p>
                </div>
              ))}
            </div>
          </Card>
        )}

        {showColumnPanel && (
          <Card className="space-y-3 border-subtle">
            <div className="flex items-center justify-between gap-3">
              <p className="text-[11px] font-black uppercase tracking-widest text-slate-300">
                Widoczne kolumny dla: {activeTypeTab === "all" ? "Wszystkie" : groupLabel(activeTypeTab)}
              </p>
              <div className="flex items-center gap-2">
                <Button variant="ghost" className="!px-3 !py-1.5 text-[10px]" onClick={showAllColumns}>
                  Pokaz wszystkie kolumny
                </Button>
                <Button variant="ghost" className="!px-3 !py-1.5 text-[10px]" onClick={showAllFormFields}>
                  Pokaz wszystkie pola
                </Button>
              </div>
            </div>
            <div className="rounded-xl border border-subtle bg-black/20 p-3">
              <p className="text-[11px] font-black uppercase tracking-widest text-slate-300 mb-2">
                Widoczne kolumny (przeciagnij na dol)
              </p>
              <div className="flex flex-wrap gap-2">
                {desktopColumns
                  .filter((col) => !!activeTabPrefs.visible[col.key])
                  .map((col) => (
                    <button
                      key={`drag-col-${col.key}`}
                      type="button"
                      draggable
                      onDragStart={() => setDraggingPanelColumn(col.key)}
                      onDragEnd={() => {
                        setDraggingPanelColumn(null);
                        setFormDropActive(false);
                      }}
                      className="px-2 py-1 text-[10px] uppercase tracking-wider font-black rounded-md border border-subtle bg-white/5 text-slate-300 cursor-grab active:cursor-grabbing hover:bg-white/10"
                    >
                      {col.label}
                    </button>
                  ))}
              </div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {desktopColumns.map((col) => (
                <label key={`col-toggle-${col.key}`} className="flex items-center gap-2 text-[11px] text-slate-200">
                  <input
                    type="checkbox"
                    checked={!!activeTabPrefs.visible[col.key]}
                    onChange={() => toggleColumnVisible(col.key)}
                    className="accent-emerald-500"
                  />
                  <span>{col.label}</span>
                </label>
              ))}
            </div>
            <p className="text-[10px] text-slate-500">
              Przeciagnij naglowek kolumny, aby zmienic kolejnosc. Ustawienia zapisuja sie osobno dla kazdej zakladki typu.
            </p>
            <div
              className={`border-t border-subtle pt-3 rounded-lg ${formDropActive ? "ring-1 ring-emerald-500/70 bg-emerald-500/5" : ""}`}
              onDragOver={(e) => {
                if (!draggingPanelColumn) return;
                e.preventDefault();
                setFormDropActive(true);
              }}
              onDragLeave={() => setFormDropActive(false)}
              onDrop={onFormDrop}
            >
              <p className="text-[11px] font-black uppercase tracking-widest text-slate-300 mb-2">
                Pola panelu po lewej dla: {activeTypeTab === "all" ? "Wszystkie" : groupLabel(activeTypeTab)}
              </p>
              <p className="text-[10px] text-slate-500 mb-2">
                Przeciagnij tutaj chip kolumny z sekcji wyzej, aby automatycznie wlaczyc pasujace pola po lewej.
              </p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {FORM_FIELDS.map((field) => (
                  <label key={`field-toggle-${field.key}`} className="flex items-center gap-2 text-[11px] text-slate-200">
                    <input
                      type="checkbox"
                      checked={!!activeFormVisibility[field.key]}
                      onChange={() => toggleFormField(field.key)}
                      className="accent-emerald-500"
                    />
                    <span>{field.label}</span>
                  </label>
                ))}
              </div>
              {activeExtraFields.length > 0 && (
                <div className="mt-3 border-t border-subtle pt-2">
                  <p className="text-[10px] uppercase tracking-wider font-black text-slate-400 mb-2">
                    Dodatkowe pola dla tej zakladki
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {activeExtraFields.map((colKey) => (
                      <span
                        key={`extra-chip-${colKey}`}
                        className="inline-flex items-center gap-2 px-2 py-1 rounded-md border border-subtle bg-white/5 text-[10px] uppercase tracking-wider font-black text-slate-300"
                      >
                        {columnLabelByKey[colKey]}
                        <button
                          type="button"
                          onClick={() => removeExtraField(colKey)}
                          className="text-slate-400 hover:text-white"
                          title="Usun pole dodatkowe"
                        >
                          <X size={12} />
                        </button>
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {panelInfo ? <p className="text-[10px] text-emerald-300 mt-2">{panelInfo}</p> : null}
            </div>
          </Card>
        )}

        <Card className="p-3 border-subtle shrink-0">
          <div className="flex flex-wrap items-center gap-2">
            <Button onClick={focusArrivalForm} className="!px-3 !py-2 text-xs">
              Add
            </Button>
            <Button variant="secondary" onClick={startEditSelected} className="!px-3 !py-2 text-xs">
              Edit
            </Button>
            <Button variant="secondary" onClick={moveTypeSelected} disabled={saving} className="!px-3 !py-2 text-xs">
              Move type
            </Button>
            <Button variant="ghost" onClick={() => setShowColumnPanel((v) => !v)} className="!px-3 !py-2 text-xs">
              Hide/Show columns
            </Button>
            <Button variant="ghost" onClick={exportVisibleRowsCsv} className="!px-3 !py-2 text-xs">
              Export
            </Button>
            <span className="text-[10px] text-slate-500 ml-auto">
              {selectedDesktopRow ? `Wybrano material #${selectedDesktopRow._material_id}` : "Brak zaznaczonego wiersza"}
            </span>
          </div>
          {tableActionMsg ? <p className="text-[10px] text-emerald-300 mt-2">{tableActionMsg}</p> : null}
        </Card>

        <section className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
          {false ? (
            <Card className="p-0 border-subtle overflow-hidden">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-white/5 border-b border-subtle">
                  <th className="p-4 eyebrow">Zasob</th>
                  <th className="p-4 eyebrow">Parametry</th>
                  <th className="p-4 eyebrow">Zakup / Dostawca</th>
                  <th className="p-4 eyebrow text-right">Dostepne</th>
                  <th className="p-4 eyebrow text-right">Min. stan</th>
                  <th className="p-4 eyebrow text-right">Cena</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={6} className="p-8 text-center text-slate-500 text-sm">Ladowanie...</td>
                  </tr>
                ) : filtered.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="p-8 text-center text-slate-500 text-sm">Brak pozycji</td>
                  </tr>
                ) : grouped.map((group) => (
                  <React.Fragment key={group.key}>
                    <tr className="bg-white/5 border-b border-subtle">
                      <td colSpan={6} className="p-0">
                        <button
                          type="button"
                          onClick={() => toggleGroup(group.key)}
                          className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-white/5"
                        >
                          <div className="flex items-center gap-2">
                            {collapsedGroups[group.key] ? <ChevronRight size={14} /> : <ChevronDown size={14} />}
                            <span className="text-xs font-black uppercase tracking-widest text-slate-300">{group.label}</span>
                            <span className="text-[10px] text-slate-500">({group.rows.length})</span>
                          </div>
                        </button>
                      </td>
                    </tr>
                    {!collapsedGroups[group.key] && group.rows.map((row) => {
                      const params = parseParamJson(row.parameter_json);
                      const latest = latestArrivalByMaterial[row.id];
                      const formatL = readParam(row, params, ["format_length_mm", "length_mm", "length"]);
                      const formatW = readParam(row, params, ["format_width_mm", "width_mm", "width"]);
                      const thickness = readParam(row, params, ["thickness", "thickness_mm", "grubosc_mm"]);
                      const qtyPack = readParam(row, params, ["pack_size", "qty_per_pack", "paczka"]);
                      const dims = formatL && formatW ? `${formatL}x${formatW} mm` : "";
                      const meta: string[] = [];
                      if (dims) meta.push(dims);
                      if (thickness) meta.push(`t=${thickness} mm`);
                      if (qtyPack) meta.push(`paczka ${qtyPack}`);
                      const keys = Object.keys(params).slice(0, 4);

                      return (
                        <tr key={row.id} className="border-b border-subtle hover:bg-emerald-500/5 transition-colors group align-top">
                          <td className="p-4">
                            <p className="font-bold text-slate-200">{row.name}</p>
                            <p className="text-[10px] text-slate-500 uppercase font-bold">
                              {(row.material_kind || "other").toUpperCase()} - {(row.material_code || "NO-CODE")}
                            </p>
                            {meta.length > 0 ? (
                              <p className="text-[10px] text-slate-400 mt-1">{meta.join("  ")}</p>
                            ) : null}
                          </td>
                          <td className="p-4">
                            {keys.length === 0 ? (
                              <span className="text-[11px] text-slate-500">Brak dodatkowych parametrow</span>
                            ) : (
                              <div className="space-y-1">
                                {keys.map((k) => (
                                  <p key={k} className="text-[10px] text-slate-300">
                                    <span className="text-slate-500">{k}:</span> {String(params[k])}
                                  </p>
                                ))}
                              </div>
                            )}
                          </td>
                          <td className="p-4">
                            <p className="text-[11px] text-slate-300 uppercase">
                              {latest?.purchase_type || row.purchase_type || "nothing"} - {row.category || "other"}
                            </p>
                            <p className="text-[10px] text-slate-500 mt-1">
                              {latest?.supplier || latest?.wholesaler
                                ? `${latest?.supplier || "-"} / ${latest?.wholesaler || "-"}`
                                : (row.supplier || row.wholesaler ? `${row.supplier || "-"} / ${row.wholesaler || "-"}` : "Brak dostawcy")}
                            </p>
                            <p className="text-[10px] text-slate-500 mt-1">
                              Netto/Brutto: {(latest?.unit_price_net ?? 0).toFixed(2)} / {(latest?.unit_price_gross ?? 0).toFixed(2)}
                            </p>
                            <p className="text-[10px] text-slate-500 mt-1">
                              Dokument: {latest?.document_nr || "-"}
                            </p>
                          </td>
                          <td className="p-4 text-right">
                            <span className={`text-sm font-black font-mono ${(row.is_low_stock ? "text-red-400" : "text-emerald-400")}`}>
                              {row.stock_quantity.toFixed(1)} <span className="text-[10px] text-slate-500 font-normal">{row.unit}</span>
                            </span>
                          </td>
                          <td className="p-4 text-right">
                            <span className="text-sm font-mono text-amber-500">
                              {(row.min_stock || 0).toFixed(1)} <span className="text-[10px] text-slate-500 font-normal">{row.unit}</span>
                            </span>
                          </td>
                          <td className="p-4 text-right text-sm font-mono text-slate-400">
                            {row.price.toFixed(2)} PLN/j.
                          </td>
                        </tr>
                      );
                    })}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
            </Card>
          ) : (
            <Card className="p-0 border-subtle overflow-hidden">
              <div className="overflow-auto">
                <table className="w-full text-left border-collapse table-fixed" style={{ minWidth: `${Math.max(1200, orderedColumns.length * 110)}px` }}>
                  <thead>
                    <tr className="sticky top-0 z-20 bg-slate-950 border-b border-subtle">
                      {orderedColumns.map((col) => (
                        <th
                          key={col.key}
                          draggable
                          onDragStart={() => setDraggingCol(col.key)}
                          onDragOver={(e) => e.preventDefault()}
                          onDrop={() => {
                            if (!draggingCol) return;
                            moveColumn(draggingCol, col.key);
                            setDraggingCol(null);
                          }}
                          onDragEnd={() => setDraggingCol(null)}
                          className="p-2 pr-6 eyebrow whitespace-nowrap relative select-none cursor-move"
                          style={{ width: activeTabPrefs.widths[col.key] || 110, minWidth: 70 }}
                        >
                          {col.label}
                          <span
                            onMouseDown={(e) => onResizeMouseDown(col.key, e)}
                            className="absolute top-0 right-0 h-full w-2 cursor-col-resize bg-transparent hover:bg-brand/30"
                            title="Zmien szerokosc kolumny"
                          />
                        </th>
                      ))}
                      <th className="p-2 pr-2 eyebrow whitespace-nowrap text-right" style={{ width: 120, minWidth: 120 }}>Edycja</th>
                    </tr>
                    <tr className="sticky top-[33px] z-20 bg-slate-950 border-b border-subtle">
                      {orderedColumns.map((col) => (
                        <th
                          key={`${col.key}-f`}
                          className="p-2"
                          style={{ width: activeTabPrefs.widths[col.key] || 110, minWidth: 70 }}
                        >
                          <input
                            type="text"
                            value={columnFilters[col.key] || ""}
                            onChange={(e) => setColumnFilters((prev) => ({ ...prev, [col.key]: e.target.value }))}
                            placeholder="filtr"
                            className="w-full bg-canvas-deep border border-subtle rounded-lg px-2 py-1 text-[11px] text-white"
                          />
                        </th>
                      ))}
                      <th className="p-2" />
                    </tr>
                  </thead>
                  <tbody>
                    {loading ? (
                      <tr>
                        <td colSpan={orderedColumns.length + 1} className="p-8 text-center text-slate-500 text-sm">Ladowanie...</td>
                      </tr>
                    ) : activeDesktopRows.length === 0 ? (
                      <tr>
                        <td colSpan={orderedColumns.length + 1} className="p-8 text-center text-slate-500 text-sm">Brak pozycji</td>
                      </tr>
                    ) : activeTypeTab === "all" ? desktopGroupedRows.map((group) => (
                      <React.Fragment key={group.key}>
                        <tr className="bg-white/5 border-b border-subtle">
                          <td colSpan={orderedColumns.length + 1} className="p-0">
                            <button
                              type="button"
                              onClick={() => setCollapsedDesktopGroups((prev) => ({ ...prev, [group.key]: !prev[group.key] }))}
                              className="w-full px-3 py-2 flex items-center gap-2 text-left hover:bg-white/5"
                            >
                              {collapsedDesktopGroups[group.key] ? <ChevronRight size={14} /> : <ChevronDown size={14} />}
                              <span className="text-[11px] font-black uppercase tracking-wider text-slate-300">{group.label}</span>
                              <span className="text-[10px] text-slate-500">({group.rows.length})</span>
                            </button>
                          </td>
                        </tr>
                        {!collapsedDesktopGroups[group.key] && group.rows.map((row) => renderDesktopRow(row))}
                      </React.Fragment>
                    )) : activeDesktopRows.map((row) => renderDesktopRow(row))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </section>
      </main>
    </div>
  );
}
