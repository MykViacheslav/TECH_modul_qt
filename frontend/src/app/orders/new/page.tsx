"use client";

import AppShell from "@/components/AppShell";
import BusinessHealthStrip from "@/components/BusinessHealthStrip";
import { Button, Card } from "@/components/ui";
import clsx from "clsx";
import {
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Download,
  FileDown,
  Loader2,
  RotateCcw,
  Save,
  Search,
  Upload,
  X,
} from "lucide-react";
import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  TechModulAPI,
  type ClientRecord,
  type ImportedTechnologySummary,
  type MaterialRecord,
  type OrderRecord,
  type ServicePricingResult,
  type UnifiedSummaryData,
} from "@/services/api";
import { useSelectedProjectId } from "@/services/project-context";
import { usePathname, useRouter } from "next/navigation";

type PositionItem = {
  id: string;
  name: string;
  type: string;
  quantity: number;
  vat: number;
  description: string;
  purchaseType: "invoice" | "cash" | "receipt" | "none";
  serviceMode?: WizardMethod;
  serviceSummary?: string;
  serviceEstimatedNet?: number;
  servicePricing?: ServicePricingResult;
  servicePricingInput?: Record<string, unknown>;
  sourceType?: "manual" | "project_import" | "excel_like";
  baseMaterialName?: string;
  lengthMm?: number;
  widthMm?: number;
  thicknessMm?: number;
  textureOrColor?: string;
  edgeTop?: boolean;
  edgeBottom?: boolean;
  edgeLeft?: boolean;
  edgeRight?: boolean;
  technologySummary?: ImportedTechnologySummary;
};

type AttachmentItem = {
  id: string;
  name: string;
  type: "PDF" | "IMG";
  description: string;
  file?: File;
};

type MaterialChoice = {
  id: string;
  positionId: string;
  positionName: string;
  scope: string;
  material: string;
  color: string;
  code: string;
  status: "Proba" | "Final";
  date: string;
  notes: string;
};

type PaymentRow = {
  id: string;
  stage: string;
  amount: number;
  cash: boolean;
  method: "invoice_vat" | "receipt" | "cash" | "no_document";
  cashbox: "kasa_faktura_vat" | "kasa_paragon" | "kasa_gotowka" | "kasa_bez_dokumentu";
  paid: boolean;
  date: string;
  notes: string;
};

type ServiceRow = {
  id: string;
  name: string;
  enabled: boolean;
  qty: number;
  unit: "szt" | "m2" | "mb" | "kpl";
  unitPrice: number;
  notes: string;
};

type ServiceEstimatorDraft = {
  materialId: string;
  edgeMaterialId: string;
  lengthMm: number;
  widthMm: number;
  thicknessMm: number;
  qty: number;
  edgeTop: boolean;
  edgeBottom: boolean;
  edgeLeft: boolean;
  edgeRight: boolean;
  cncPattern: "line" | "classic" | "premium" | "custom";
  lacquer: boolean;
  lacquerSides: 1 | 2;
  veneerSides: 1 | 2;
  veneerLacquer: boolean;
  bentShape: "arc" | "wave" | "custom";
  bentRadiusMm: number;
  bentComplexity: 1 | 2 | 3;
};

type TechnicalSpecConfig = {
  bodyMaterial: string;
  frontMaterial: string;
  hardwareBrand: string;
  accessories: string[];
};

type WizardMethod =
  | "project"
  | "quick-module"
  | "quick-section"
  | "import3d"
  | "service-cut"
  | "service-cut-edge"
  | "service-front-cnc"
  | "service-front-cnc-lacquer"
  | "service-veneer"
  | "service-bent-elements";

const STEPS = [
  { id: 1, label: "Klient" },
  { id: 2, label: "Pozycje do wyceny" },
  { id: 3, label: "Specyfikacja" },
  { id: 4, label: "Zalaczniki" },
  { id: 5, label: "Materialy" },
  { id: 6, label: "Uslugi" },
  { id: 7, label: "Finanse" },
  { id: 8, label: "Podsumowanie" },
] as const;

const SERVICES_CATALOG = [
  "Ciecie",
  "Oklejanie",
  "Lakierowanie",
  "Frezowanie frontow",
  "Wiercenie CNC",
];

const TECH_SCOPE_DEFAULT = "__default__";
const EXTRA_OPTIONS = [
  "Pantograf",
  "Cargo",
  "LED",
  "Kosze",
  "Prasownica",
  "Szuflady wew.",
  "Podnosniki",
  "Organizer",
];

const POSITION_PURCHASE_OPTIONS: Array<{
  value: "invoice" | "cash" | "receipt" | "none";
  label: string;
}> = [
  { value: "invoice", label: "Faktura" },
  { value: "cash", label: "Gotowka" },
  { value: "receipt", label: "Paragon" },
  { value: "none", label: "Bez dokumentu" },
];

const PAYMENT_METHOD_OPTIONS: Array<{
  value: "invoice_vat" | "receipt" | "cash" | "no_document";
  label: string;
}> = [
  { value: "invoice_vat", label: "Faktura VAT" },
  { value: "receipt", label: "Paragon" },
  { value: "cash", label: "Gotowka" },
  { value: "no_document", label: "Bez dokumentu" },
];

const ORDER_METHOD_OPTIONS: Array<{ key: WizardMethod; label: string }> = [
  { key: "project", label: "Projekt\nModuly / Sciany" },
  { key: "quick-module", label: "Szybka\nZ modulu" },
  { key: "quick-section", label: "Szybka\nZ sekcji" },
  { key: "import3d", label: "Import 3D\nPlik .project" },
];

const SERVICE_METHOD_OPTIONS: Array<{ key: WizardMethod; label: string }> = [
  { key: "service-cut-edge", label: "Rozkroj\n/ rozkroj + oklejanie" },
  { key: "service-front-cnc-lacquer", label: "Frezowanie frontow surowych\n+ lakierowanie" },
  { key: "service-veneer", label: "Fornir" },
  { key: "service-bent-elements", label: "Giete elementy" },
];

const SERVICE_MODE_LABEL: Record<
  "service-cut" | "service-cut-edge" | "service-front-cnc-lacquer" | "service-veneer" | "service-bent-elements",
  string
> = {
  "service-cut": "Rozkroj / oklejanie",
  "service-cut-edge": "Rozkroj / oklejanie",
  "service-front-cnc-lacquer": "Frezowanie frontow + lakierowanie",
  "service-veneer": "Fornir",
  "service-bent-elements": "Giete elementy",
};

const CASHBOX_OPTIONS: Array<{
  value: "kasa_faktura_vat" | "kasa_paragon" | "kasa_gotowka" | "kasa_bez_dokumentu";
  label: string;
}> = [
  { value: "kasa_faktura_vat", label: "Kasa faktura VAT" },
  { value: "kasa_paragon", label: "Kasa paragon" },
  { value: "kasa_gotowka", label: "Kasa gotowka" },
  { value: "kasa_bez_dokumentu", label: "Kasa bez dokumentu" },
];

const METHOD_TO_CASHBOX: Record<
  "invoice_vat" | "receipt" | "cash" | "no_document",
  "kasa_faktura_vat" | "kasa_paragon" | "kasa_gotowka" | "kasa_bez_dokumentu"
> = {
  invoice_vat: "kasa_faktura_vat",
  receipt: "kasa_paragon",
  cash: "kasa_gotowka",
  no_document: "kasa_bez_dokumentu",
};

const baseInput =
  "w-full bg-[#1e1e1e] border border-[#333] rounded-sm px-2 py-1.5 text-white outline-none focus:border-blue-500 text-[11px]";

const createDefaultServiceEstimator = (): ServiceEstimatorDraft => ({
  materialId: "",
  edgeMaterialId: "",
  lengthMm: 2000,
  widthMm: 600,
  thicknessMm: 18,
  qty: 1,
  edgeTop: false,
  edgeBottom: false,
  edgeLeft: false,
  edgeRight: false,
  cncPattern: "line",
  lacquer: true,
  lacquerSides: 1,
  veneerSides: 1,
  veneerLacquer: false,
  bentShape: "arc",
  bentRadiusMm: 300,
  bentComplexity: 1,
});

const serviceModeKeys = new Set<WizardMethod>([
  "service-cut",
  "service-cut-edge",
  "service-front-cnc-lacquer",
  "service-veneer",
  "service-bent-elements",
]);

const UNIFIED_SERVICE_ROW_SCHEMA_VERSION = "unified_service_row_v1";
const PRIMARY_CUTTING_SERVICE_MODE: WizardMethod = "service-cut-edge";

const normalizeServiceMode = (mode: WizardMethod | string | null | undefined): WizardMethod => {
  if (mode === "service-cut") {
    return PRIMARY_CUTTING_SERVICE_MODE;
  }
  if (
    mode === "service-cut-edge" ||
    mode === "service-front-cnc-lacquer" ||
    mode === "service-veneer" ||
    mode === "service-bent-elements" ||
    mode === "project" ||
    mode === "quick-module" ||
    mode === "quick-section" ||
    mode === "import3d"
  ) {
    return mode;
  }
  return PRIMARY_CUTTING_SERVICE_MODE;
};

export default function NewOrderPage() {
  const pathname = usePathname();
  const router = useRouter();
  const isServicesMode = pathname?.startsWith("/services");
  const [projectId] = useSelectedProjectId(1);
  const [step, setStep] = useState(isServicesMode ? 6 : 1);
  const draftStorageKey = `techmodul_${isServicesMode ? "services" : "order"}_draft_${projectId}`;
  const [draftHydrated, setDraftHydrated] = useState(false);

  const [form, setForm] = useState({
    clientName: "",
    clientFirstName: "",
    clientLastName: "",
    clientCompanyName: "",
    clientType: "person" as "person" | "b2b",
    clientAddress: "",
    clientEmail: "",
    clientPhone: "",
    clientNip: "",
    orderTitle: "",
    city: "",
    street: "",
    building: "",
    apartment: "",
    zipCode: "",
    deadlineFrom: "",
    deadlineTo: "",
    budget: "",
    status: "Nowe",
    description: "",
    notes: "",
    spec: {
      body: { material: "Plyta laminowana", color: "Bialy" },
      front: { material: "Lakier MDF", color: "Premium" },
      hardware: { brand: "Blum", hinges: "Blumotion", drawers: "Legrabox" },
      opening: "Uchwyt",
      accessories: [] as string[],
    },
  });

  const [clients, setClients] = useState<ClientRecord[]>([]);
  const [recentOrders, setRecentOrders] = useState<OrderRecord[]>([]);
  const [loadingClients, setLoadingClients] = useState(false);
  const [savingClient, setSavingClient] = useState(false);
  const [savingOrder, setSavingOrder] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedOrderId, setSavedOrderId] = useState<number | null>(null);
  const [clientSaveInfo, setClientSaveInfo] = useState<string | null>(null);
  const [clientSaveState, setClientSaveState] = useState<"success" | "error" | "info" | null>(null);

  const [clientQuery, setClientQuery] = useState("");
  const [showClientDropdown, setShowClientDropdown] = useState(false);
  const [activeClientIdx, setActiveClientIdx] = useState(-1);

  const [unifiedSummary, setUnifiedSummary] = useState<UnifiedSummaryData | null>(null);
  const [unifiedSummaryLoading, setUnifiedSummaryLoading] = useState(false);

  const [valuationMethod, setValuationMethod] = useState<WizardMethod>(
    isServicesMode ? PRIMARY_CUTTING_SERVICE_MODE : "project"
  );

  const [positions, setPositions] = useState<PositionItem[]>([]);
  const [positionDraft, setPositionDraft] = useState({
    name: "",
    type: isServicesMode ? "Usluga" : "Kuchnia",
    quantity: 1,
    vat: 23,
    description: "",
    textureOrColor: "",
    purchaseType: "invoice" as "invoice" | "cash" | "receipt" | "none",
  });
  const [serviceEstimator, setServiceEstimator] = useState<ServiceEstimatorDraft>(
    createDefaultServiceEstimator()
  );
  const [servicePricingPreview, setServicePricingPreview] = useState<ServicePricingResult | null>(null);
  const [servicePricingLoading, setServicePricingLoading] = useState(false);
  const [projectImportLoading, setProjectImportLoading] = useState(false);
  const [editingPositionId, setEditingPositionId] = useState<string | null>(null);
  const [activePositionId, setActivePositionId] = useState<string>("");

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const projectImportInputRef = useRef<HTMLInputElement | null>(null);
  const [attachments, setAttachments] = useState<AttachmentItem[]>([]);
  const [attachmentDraft, setAttachmentDraft] = useState({
    type: "PDF" as "PDF" | "IMG",
    description: "",
  });
  const [selectedAttachmentId, setSelectedAttachmentId] = useState<string | null>(null);

  const [materialChoices, setMaterialChoices] = useState<MaterialChoice[]>([]);
  const [materialDraft, setMaterialDraft] = useState({
    positionId: "",
    scope: "Korpus",
    material: "",
    color: "",
    code: "",
    status: "Proba" as "Proba" | "Final",
    date: new Date().toISOString().slice(0, 10),
    notes: "",
  });
  const [selectedMaterialId, setSelectedMaterialId] = useState<string | null>(null);
  const [materialsView, setMaterialsView] = useState<"active" | "all" | "summary">("active");
  const [materialsDb, setMaterialsDb] = useState<MaterialRecord[]>([]);
  const [materialsDbLoading, setMaterialsDbLoading] = useState(false);
  const [materialDbCategory, setMaterialDbCategory] = useState<"all" | "boards" | "hardware" | "finishes">("all");
  const [materialDbQuery, setMaterialDbQuery] = useState("");
  const [materialDbSelectedId, setMaterialDbSelectedId] = useState<string>("");

  const [payments, setPayments] = useState<PaymentRow[]>([]);
  const [services, setServices] = useState<ServiceRow[]>(
    SERVICES_CATALOG.map((name) => ({
      id: crypto.randomUUID(),
      name,
      enabled: false,
      qty: 1,
      unit: "szt",
      unitPrice: 0,
      notes: "",
    }))
  );
  const [paymentDraft, setPaymentDraft] = useState({
    stage: "Rezerwacja terminu",
    amount: 0,
    cash: false,
    method: "invoice_vat" as "invoice_vat" | "receipt" | "cash" | "no_document",
    cashbox: "kasa_faktura_vat" as
      | "kasa_faktura_vat"
      | "kasa_paragon"
      | "kasa_gotowka"
      | "kasa_bez_dokumentu",
    paid: false,
    date: new Date().toISOString().slice(0, 10),
    notes: "",
  });
  const [selectedPaymentId, setSelectedPaymentId] = useState<string | null>(null);
  const [specTargetId, setSpecTargetId] = useState<string>(TECH_SCOPE_DEFAULT);
  const [lastSavedSignature, setLastSavedSignature] = useState<string | null>(null);
  const [specByTarget, setSpecByTarget] = useState<Record<string, TechnicalSpecConfig>>({
    [TECH_SCOPE_DEFAULT]: {
      bodyMaterial: "Plyta laminowana",
      frontMaterial: "Lakier MDF",
      hardwareBrand: "Blum",
      accessories: [],
    },
  });

  const set = (key: keyof typeof form, value: string) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const currentSpec = specByTarget[specTargetId] ?? specByTarget[TECH_SCOPE_DEFAULT];
  const activePosition = positions.find((p) => p.id === activePositionId) ?? null;

  const setCurrentSpec = (updater: (prev: TechnicalSpecConfig) => TechnicalSpecConfig) => {
    setSpecByTarget((prev) => {
      const fallback = prev[TECH_SCOPE_DEFAULT] ?? {
        bodyMaterial: "Plyta laminowana",
        frontMaterial: "Lakier MDF",
        hardwareBrand: "Blum",
        accessories: [],
      };
      const current = prev[specTargetId] ?? fallback;
      const next = updater(current);
      return { ...prev, [specTargetId]: next };
    });
  };

  const getScopeLabel = (targetId: string) => {
    if (targetId === TECH_SCOPE_DEFAULT) return "Domyslna dla calego zamowienia";
    const pos = positions.find((p) => p.id === targetId);
    if (!pos) return "Pozycja (usunieta)";
    return `Pozycja: ${pos.name}`;
  };

  const filteredClients = useMemo(() => {
    if (!clientQuery.trim()) return [];
    const q = clientQuery.trim().toLowerCase();
    return clients
      .filter((c) => {
        const name = String(c.name || "").toLowerCase();
        const email = String(c.email || "").toLowerCase();
        const phone = String(c.phone || "").toLowerCase();
        const address = String(c.address || "").toLowerCase();
        const location = String(c.location || "").toLowerCase();
        return (
          name.includes(q) ||
          email.includes(q) ||
          phone.includes(q) ||
          address.includes(q) ||
          location.includes(q)
        );
      })
      .slice(0, 8);
  }, [clients, clientQuery]);

  const filteredDbMaterials = useMemo(() => {
    const byCategory =
      materialDbCategory === "all"
        ? materialsDb
        : materialsDb.filter((m) => String(m.category || "").toLowerCase() === materialDbCategory);
    if (!materialDbQuery.trim()) return byCategory;
    const q = materialDbQuery.trim().toLowerCase();
    return byCategory.filter((m) => {
      const name = String(m.name || "").toLowerCase();
      const code = String(m.material_code || "").toLowerCase();
      const supplier = String(m.supplier || "").toLowerCase();
      return name.includes(q) || code.includes(q) || supplier.includes(q);
    });
  }, [materialsDb, materialDbCategory, materialDbQuery]);

  const totalPlanned = useMemo(
    () => payments.reduce((sum, p) => sum + (Number(p.amount) || 0), 0),
    [payments]
  );
  const totalPaid = useMemo(
    () => payments.filter((p) => p.paid).reduce((sum, p) => sum + (Number(p.amount) || 0), 0),
    [payments]
  );
  const totalRemaining = Math.max(0, totalPlanned - totalPaid);

  const paidByCashbox = useMemo(() => {
    return payments
      .filter((p) => p.paid)
      .reduce<Record<string, number>>((acc, item) => {
        const key = item.cashbox || METHOD_TO_CASHBOX[item.method] || "kasa_faktura_vat";
        acc[key] = (acc[key] || 0) + (Number(item.amount) || 0);
        return acc;
      }, {});
  }, [payments]);

  const servicesActive = useMemo(() => services.filter((s) => s.enabled), [services]);
  const servicesTotal = useMemo(
    () =>
      servicesActive.reduce(
        (sum, row) => sum + (Number(row.qty) || 0) * (Number(row.unitPrice) || 0),
        0
      ),
    [servicesActive]
  );

  const selectedServiceMaterial = useMemo(
    () => materialsDb.find((m) => String(m.id) === String(serviceEstimator.materialId)),
    [materialsDb, serviceEstimator.materialId]
  );
  const selectedEdgeMaterial = useMemo(
    () => materialsDb.find((m) => String(m.id) === String(serviceEstimator.edgeMaterialId)),
    [materialsDb, serviceEstimator.edgeMaterialId]
  );

  const buildServicePricingInput = (options?: {
    mode?: WizardMethod;
    qty?: number;
    technologySummary?: ImportedTechnologySummary | Record<string, unknown> | null;
  }): Record<string, unknown> => {
    const mode = options?.mode ?? valuationMethod;
    const qty = Math.max(1, Number(options?.qty ?? serviceEstimator.qty) || 1);
    return {
      schema_version: UNIFIED_SERVICE_ROW_SCHEMA_VERSION,
      service_mode: mode,
      service_subtype: mode,
      base_material_id: serviceEstimator.materialId || "",
      base_material_name: selectedServiceMaterial?.name || "",
      base_material_price_m2: Number(selectedServiceMaterial?.price || 0),
      base_thickness_mm: Math.max(0, Number(serviceEstimator.thicknessMm) || 0),
      length_mm: Math.max(0, Number(serviceEstimator.lengthMm) || 0),
      width_mm: Math.max(0, Number(serviceEstimator.widthMm) || 0),
      quantity: qty,
      edge_mode: "default",
      edge_default_material_id: serviceEstimator.edgeMaterialId || "",
      edge_top: Boolean(serviceEstimator.edgeTop),
      edge_bottom: Boolean(serviceEstimator.edgeBottom),
      edge_left: Boolean(serviceEstimator.edgeLeft),
      edge_right: Boolean(serviceEstimator.edgeRight),
      cnc_pattern: serviceEstimator.cncPattern,
      front_model_code:
        mode === "service-front-cnc-lacquer"
          ? `pattern_${String(serviceEstimator.cncPattern || "line")}`
          : "",
      lacquer: Boolean(serviceEstimator.lacquer),
      lacquer_sides: Number(serviceEstimator.lacquerSides) === 2 ? 2 : 1,
      veneer_sides: Number(serviceEstimator.veneerSides) === 2 ? 2 : 1,
      veneer_lacquer: Boolean(serviceEstimator.veneerLacquer),
      bent_shape: serviceEstimator.bentShape,
      bent_radius_mm: Math.max(0, Number(serviceEstimator.bentRadiusMm) || 0),
      bent_complexity: Number(serviceEstimator.bentComplexity) || 1,
      extra_layers: [],
      technology_summary: options?.technologySummary ?? undefined,
    };
  };

  const requestServicePricingPreview = async (
    inputOverride?: Record<string, unknown>,
    options?: { silent?: boolean }
  ): Promise<ServicePricingResult | null> => {
    const item = inputOverride ?? buildServicePricingInput();
    const silent = Boolean(options?.silent);
    if (!silent) setServicePricingLoading(true);
    try {
      const response = await TechModulAPI.previewServicePricing({ item });
      setServicePricingPreview(response.result);
      return response.result;
    } catch (e: any) {
      if (!silent) setError(e?.message ?? "Nie udalo sie policzyc podgladu uslugi");
      setServicePricingPreview(null);
      return null;
    } finally {
      if (!silent) setServicePricingLoading(false);
    }
  };

  const getRowPricingInput = (row: PositionItem): Record<string, unknown> => {
    if (row.servicePricingInput && typeof row.servicePricingInput === "object") {
      return row.servicePricingInput;
    }
    return {};
  };

  const getRowNumberField = (row: PositionItem, key: string, fallback = 0): number => {
    const payload = getRowPricingInput(row);
    const raw = payload[key];
    const parsed = Number(raw);
    if (Number.isFinite(parsed)) return parsed;
    if (key === "length_mm" && typeof row.lengthMm === "number") return row.lengthMm;
    if (key === "width_mm" && typeof row.widthMm === "number") return row.widthMm;
    if (key === "base_thickness_mm" && typeof row.thicknessMm === "number") return row.thicknessMm;
    return fallback;
  };

  const getRowStringField = (row: PositionItem, key: string, fallback = "-"): string => {
    const payload = getRowPricingInput(row);
    const raw = payload[key];
    const text = String(raw ?? "").trim();
    if (text) return text;
    if (key === "base_material_name" && row.baseMaterialName) return row.baseMaterialName;
    return fallback;
  };

  const serviceMaterialTables = (() => {
    const resolveMaterialName = (idOrName: string): string => {
      const text = String(idOrName || "").trim();
      if (!text) return "";
      const byId = materialsDb.find((m) => String(m.id) === text);
      if (byId) return byId.name;
      return text;
    };

    type ServiceGroup = {
      key: string;
      materialName: string;
      rows: PositionItem[];
      totalM2: number;
      totalNet: number;
      edgeByMaterial: Record<string, number>;
    };

    const groups = new Map<string, ServiceGroup>();
    let globalM2 = 0;
    let globalNet = 0;
    const globalEdges: Record<string, number> = {};

    for (const row of positions) {
      const payload = getRowPricingInput(row);
      const materialName =
        getRowStringField(row, "base_material_name", "").trim() ||
        resolveMaterialName(String(payload.base_material_id ?? "")) ||
        "Bez materialu";
      const groupKey = materialName.toLowerCase();
      if (!groups.has(groupKey)) {
        groups.set(groupKey, {
          key: groupKey,
          materialName,
          rows: [],
          totalM2: 0,
          totalNet: 0,
          edgeByMaterial: {},
        });
      }
      const group = groups.get(groupKey)!;
      group.rows.push(row);

      const lengthMm = Math.max(0, getRowNumberField(row, "length_mm", 0));
      const widthMm = Math.max(0, getRowNumberField(row, "width_mm", 0));
      const qty = Math.max(1, Number(payload.quantity ?? row.quantity) || 1);
      const areaM2 = (lengthMm * widthMm * qty) / 1_000_000;
      group.totalM2 += areaM2;
      globalM2 += areaM2;

      const rowNet =
        typeof row.servicePricing?.buckets?.net_total === "number"
          ? row.servicePricing.buckets.net_total
          : typeof row.serviceEstimatedNet === "number"
          ? row.serviceEstimatedNet
          : 0;
      group.totalNet += rowNet;
      globalNet += rowNet;

      const edgeMode = String(payload.edge_mode ?? "default");
      const sideDefs: Array<{ key: "top" | "bottom" | "left" | "right"; lengthMb: number }> = [
        { key: "top", lengthMb: (widthMm * qty) / 1000 },
        { key: "bottom", lengthMb: (widthMm * qty) / 1000 },
        { key: "left", lengthMb: (lengthMm * qty) / 1000 },
        { key: "right", lengthMb: (lengthMm * qty) / 1000 },
      ];
      for (const side of sideDefs) {
        const enabled = Boolean(payload[`edge_${side.key}`]);
        if (!enabled) continue;
        const sideMaterialId =
          edgeMode === "default"
            ? String(payload.edge_default_material_id ?? "")
            : String(payload[`edge_${side.key}_material_id`] ?? "");
        const edgeName = resolveMaterialName(sideMaterialId) || "Nie wybrano okleiny";
        group.edgeByMaterial[edgeName] = (group.edgeByMaterial[edgeName] || 0) + side.lengthMb;
        globalEdges[edgeName] = (globalEdges[edgeName] || 0) + side.lengthMb;
      }
    }

    return {
      groups: Array.from(groups.values()),
      global: {
        totalM2: globalM2,
        totalNet: globalNet,
        edgeByMaterial: globalEdges,
      },
    };
  })();

  useEffect(() => {
    if (!serviceModeKeys.has(valuationMethod)) {
      setServicePricingPreview(null);
      return;
    }
    const timer = window.setTimeout(() => {
      void requestServicePricingPreview(undefined, { silent: true });
    }, 250);
    return () => window.clearTimeout(timer);
  }, [valuationMethod, serviceEstimator, selectedServiceMaterial?.price, selectedServiceMaterial?.name]);

  const clientDisplayName = useMemo(() => {
    if (form.clientType === "b2b") {
      return (form.clientCompanyName ?? form.clientName ?? "").trim();
    }
    const merged = `${form.clientFirstName ?? ""} ${form.clientLastName ?? ""}`.trim();
    return (merged || (form.clientName ?? "")).trim();
  }, [
    form.clientCompanyName,
    form.clientFirstName,
    form.clientLastName,
    form.clientName,
    form.clientType,
  ]);

  const formattedClientAddress = useMemo(() => {
    const line1 = [(form.street ?? "").trim(), (form.building ?? "").trim()]
      .filter(Boolean)
      .join(" ")
      .trim();
    const apartment = (form.apartment ?? "").trim();
    const line2 = [apartment ? `lok. ${apartment}` : "", (form.zipCode ?? "").trim(), (form.city ?? "").trim()]
      .filter(Boolean)
      .join(", ")
      .trim();
    const extra = (form.clientAddress ?? "").trim();
    return [line1, line2, extra].filter(Boolean).join(" | ");
  }, [form.street, form.building, form.apartment, form.zipCode, form.city, form.clientAddress]);

  const hasDataToSave = useMemo(() => {
    return Boolean(
      clientDisplayName ||
        form.orderTitle.trim() ||
        positions.length ||
        attachments.length ||
        materialChoices.length ||
        payments.length ||
        services.some((s) => s.enabled || s.unitPrice > 0 || (s.notes || "").trim())
    );
  }, [
    attachments.length,
    clientDisplayName,
    form.orderTitle,
    materialChoices.length,
    payments.length,
    positions.length,
    services,
  ]);

  const currentDraftSignature = useMemo(
    () =>
      JSON.stringify({
        form: {
          ...form,
          clientName: clientDisplayName,
          clientAddress: formattedClientAddress,
        },
        positions,
        attachments: attachments.map((a) => ({
          id: a.id,
          name: a.name,
          type: a.type,
          description: a.description,
        })),
        materialChoices,
        payments,
        services,
        specTargetId,
        specByTarget,
        activePositionId,
        valuationMethod,
      }),
    [
      form,
      clientDisplayName,
      formattedClientAddress,
      positions,
      attachments,
      materialChoices,
      payments,
      services,
      specTargetId,
      specByTarget,
      activePositionId,
      valuationMethod,
    ]
  );

  const hasUnsavedChanges = hasDataToSave && currentDraftSignature !== lastSavedSignature;

  const canSaveOrder = useMemo(
    () => clientDisplayName.length > 0 && form.orderTitle.trim().length > 0,
    [clientDisplayName, form.orderTitle]
  );

  useEffect(() => {
    loadClients();
    loadRecentOrders();
    loadMaterialsDb();

    const fetchActiveProject = async () => {
      try {
        const info = await TechModulAPI.getProjectFinanceSummary(projectId);
        setForm((prev) => ({
          ...prev,
          orderTitle: prev.orderTitle || info.project_title,
          clientName: prev.clientName || info.client_name,
        }));
      } catch {
        // optional autofill only
      }
    };

    fetchActiveProject();
  }, [projectId]);

  useEffect(() => {
    if (isServicesMode) {
      setStep((prev) => (prev < 1 || prev > STEPS.length ? 6 : prev));
    }
  }, [isServicesMode]);

  useEffect(() => {
    if (step !== 8 || !projectId) return;
    let cancelled = false;
    setUnifiedSummaryLoading(true);
    TechModulAPI.getProjectUnifiedSummary(projectId)
      .then((data) => {
        if (!cancelled) setUnifiedSummary(data);
      })
      .catch(() => {
        if (!cancelled) setUnifiedSummary(null);
      })
      .finally(() => {
        if (!cancelled) setUnifiedSummaryLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [step, projectId]);

  useEffect(() => {
    let restored = false;
    try {
      const raw = localStorage.getItem(draftStorageKey);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed?.version === 1) {
          if (parsed.form) {
            setForm((prev) => ({
              ...prev,
              ...parsed.form,
              clientName: String(parsed.form.clientName ?? ""),
              clientFirstName: String(parsed.form.clientFirstName ?? ""),
              clientLastName: String(parsed.form.clientLastName ?? ""),
              clientCompanyName: String(parsed.form.clientCompanyName ?? ""),
              clientAddress: String(parsed.form.clientAddress ?? ""),
              clientEmail: String(parsed.form.clientEmail ?? ""),
              clientPhone: String(parsed.form.clientPhone ?? ""),
              clientNip: String(parsed.form.clientNip ?? ""),
              city: String(parsed.form.city ?? ""),
              street: String(parsed.form.street ?? ""),
              building: String(parsed.form.building ?? ""),
              apartment: String(parsed.form.apartment ?? ""),
              zipCode: String(parsed.form.zipCode ?? ""),
              description: String(parsed.form.description ?? ""),
              notes: String(parsed.form.notes ?? ""),
              spec: {
                ...prev.spec,
                ...(parsed.form.spec ?? {}),
                body: {
                  ...prev.spec.body,
                  ...(parsed.form.spec?.body ?? {}),
                },
                front: {
                  ...prev.spec.front,
                  ...(parsed.form.spec?.front ?? {}),
                },
                hardware: {
                  ...prev.spec.hardware,
                  ...(parsed.form.spec?.hardware ?? {}),
                },
              },
            }));
          }
          if (Array.isArray(parsed.positions)) {
            setPositions(parsed.positions);
          } else if (Array.isArray(parsed.service_rows)) {
            setPositions(parsed.service_rows);
          }
          if (Array.isArray(parsed.attachments)) setAttachments(parsed.attachments);
          if (Array.isArray(parsed.materialChoices)) setMaterialChoices(parsed.materialChoices);
          if (Array.isArray(parsed.payments)) setPayments(parsed.payments);
          if (Array.isArray(parsed.services)) setServices(parsed.services);
          if (parsed.positionDraft) setPositionDraft(parsed.positionDraft);
          if (parsed.serviceEstimator) {
            setServiceEstimator({
              ...createDefaultServiceEstimator(),
              ...parsed.serviceEstimator,
            });
          }
          if (parsed.materialDraft) setMaterialDraft(parsed.materialDraft);
          if (parsed.paymentDraft) setPaymentDraft(parsed.paymentDraft);
          if (parsed.specTargetId) setSpecTargetId(parsed.specTargetId);
          if (parsed.specByTarget) setSpecByTarget(parsed.specByTarget);
          if (parsed.activePositionId !== undefined) setActivePositionId(parsed.activePositionId);
          if (parsed.valuationMethod) {
            setValuationMethod(normalizeServiceMode(parsed.valuationMethod as WizardMethod));
          }
          if (typeof parsed.step === "number") setStep(parsed.step);
          restored = true;
        }
      }
    } catch {
      // ignore broken local draft
    } finally {
      setDraftHydrated(true);
    }
    return () => {
      if (!restored) return;
    };
  }, [draftStorageKey]);

  useEffect(() => {
    if (!draftHydrated) return;
    try {
      const payload = {
        version: 1,
        savedAt: new Date().toISOString(),
        step,
        form,
        positions,
        attachments: attachments.map((a) => ({
          id: a.id,
          name: a.name,
          type: a.type,
          description: a.description,
        })),
        materialChoices,
        payments,
        services,
        positionDraft,
        serviceEstimator,
        materialDraft,
        paymentDraft,
        specTargetId,
        specByTarget,
        activePositionId,
        valuationMethod,
      };
      localStorage.setItem(draftStorageKey, JSON.stringify(payload));
    } catch {
      // storage full or unavailable
    }
  }, [
    draftHydrated,
    draftStorageKey,
    step,
    form,
    positions,
    attachments,
    materialChoices,
    payments,
    services,
    positionDraft,
    serviceEstimator,
    materialDraft,
    paymentDraft,
    specTargetId,
    specByTarget,
    activePositionId,
    valuationMethod,
  ]);

  useEffect(() => {
    const normalized = clientDisplayName.trim().toLowerCase();
    if (!normalized) return;
    const matched = clients.find((client) => client.name.trim().toLowerCase() === normalized);
    if (!matched) return;

    setForm((prev) => ({
      ...prev,
      clientType: (matched.type as "person" | "b2b") ?? prev.clientType,
      clientCompanyName:
        matched.type === "b2b" ? matched.name || prev.clientCompanyName : prev.clientCompanyName,
      clientFirstName:
        matched.type === "person"
          ? (matched.name || "").split(" ").slice(0, 1).join(" ") || prev.clientFirstName
          : prev.clientFirstName,
      clientLastName:
        matched.type === "person"
          ? (matched.name || "").split(" ").slice(1).join(" ") || prev.clientLastName
          : prev.clientLastName,
      clientAddress: matched.address ?? prev.clientAddress,
      clientEmail: matched.email ?? prev.clientEmail,
      clientPhone: matched.phone ?? prev.clientPhone,
      city: matched.location ?? prev.city,
    }));
  }, [clientDisplayName, clients]);

  useEffect(() => {
    if (specTargetId === TECH_SCOPE_DEFAULT) return;
    const exists = positions.some((p) => p.id === specTargetId);
    if (!exists) setSpecTargetId(TECH_SCOPE_DEFAULT);
  }, [positions, specTargetId]);

  useEffect(() => {
    if (positions.length === 0) {
      setActivePositionId("");
      return;
    }
    if (activePositionId && positions.some((p) => p.id === activePositionId)) return;
    setActivePositionId(positions[0].id);
  }, [positions, activePositionId]);

  useEffect(() => {
    if (positions.length === 0) {
      setMaterialDraft((prev) => ({ ...prev, positionId: "" }));
      return;
    }
    setMaterialDraft((prev) => {
      if (prev.positionId && positions.some((p) => p.id === prev.positionId)) return prev;
      return { ...prev, positionId: positions[0].id };
    });
  }, [positions]);

  useEffect(() => {
    if (!activePositionId) return;
    setMaterialDraft((prev) => {
      if (prev.positionId === activePositionId) return prev;
      return { ...prev, positionId: activePositionId };
    });
  }, [activePositionId]);

  useEffect(() => {
    if (!activePositionId) return;
    const active = positions.find((p) => p.id === activePositionId);
    if (!active) return;
    if (active.serviceMode && serviceModeKeys.has(active.serviceMode)) {
      setValuationMethod(normalizeServiceMode(active.serviceMode));
    }
    if (active.servicePricingInput && typeof active.servicePricingInput === "object") {
      const input = active.servicePricingInput as Record<string, unknown>;
      setServiceEstimator((prev) => ({
        ...prev,
        materialId: String(input.base_material_id ?? prev.materialId ?? ""),
        edgeMaterialId: String(input.edge_default_material_id ?? prev.edgeMaterialId ?? ""),
        lengthMm: Math.max(0, Number(input.length_mm ?? prev.lengthMm) || 0),
        widthMm: Math.max(0, Number(input.width_mm ?? prev.widthMm) || 0),
        thicknessMm: Math.max(0, Number(input.base_thickness_mm ?? prev.thicknessMm) || 0),
        qty: Math.max(1, Number(input.quantity ?? prev.qty) || 1),
        edgeTop: Boolean(input.edge_top ?? prev.edgeTop),
        edgeBottom: Boolean(input.edge_bottom ?? prev.edgeBottom),
        edgeLeft: Boolean(input.edge_left ?? prev.edgeLeft),
        edgeRight: Boolean(input.edge_right ?? prev.edgeRight),
        cncPattern: String(input.cnc_pattern || prev.cncPattern || "line") as ServiceEstimatorDraft["cncPattern"],
        lacquer: Boolean(input.lacquer ?? prev.lacquer),
        lacquerSides: Number(input.lacquer_sides) === 2 ? 2 : 1,
        veneerSides: Number(input.veneer_sides) === 2 ? 2 : 1,
        veneerLacquer: Boolean(input.veneer_lacquer ?? prev.veneerLacquer),
        bentShape: String(input.bent_shape || prev.bentShape || "arc") as ServiceEstimatorDraft["bentShape"],
        bentRadiusMm: Math.max(0, Number(input.bent_radius_mm ?? prev.bentRadiusMm) || 0),
        bentComplexity: (Math.max(1, Math.min(3, Number(input.bent_complexity ?? prev.bentComplexity) || 1)) as
          | 1
          | 2
          | 3),
      }));
    }
    if (active.servicePricing) {
      setServicePricingPreview(active.servicePricing);
    } else if (active.servicePricingInput && active.serviceMode && serviceModeKeys.has(active.serviceMode)) {
      void requestServicePricingPreview(active.servicePricingInput, { silent: true });
    }
  }, [activePositionId, positions]);

  useEffect(() => {
    if (!selectedMaterialId) return;
    if (materialChoices.some((item) => item.id === selectedMaterialId)) return;
    setSelectedMaterialId(null);
  }, [materialChoices, selectedMaterialId]);

  useEffect(() => {
    setPaymentDraft((prev) => {
      const nextCashbox = METHOD_TO_CASHBOX[prev.method];
      const nextCash = prev.method === "cash";
      if (prev.cashbox === nextCashbox && prev.cash === nextCash) return prev;
      return { ...prev, cashbox: nextCashbox, cash: nextCash };
    });
  }, [paymentDraft.method]);

  useEffect(() => {
    const scope = materialDraft.scope.toLowerCase();
    if (scope === "korpus" || scope === "front" || scope === "blat") {
      setMaterialDbCategory("boards");
      return;
    }
    if (scope === "okleina" || scope === "farba") {
      setMaterialDbCategory("finishes");
      return;
    }
    if (scope === "uchwyt") {
      setMaterialDbCategory("hardware");
      return;
    }
    setMaterialDbCategory("all");
  }, [materialDraft.scope]);

  const loadClients = async () => {
    setLoadingClients(true);
    try {
      const rows = await TechModulAPI.getClients();
      setClients(rows);
    } catch {
      setClients([]);
    } finally {
      setLoadingClients(false);
    }
  };

  const applyClientToForm = (client: ClientRecord) => {
    const type = (client.type as "person" | "b2b") || "person";
    set("clientType", type);
    if (type === "b2b") {
      set("clientCompanyName", client.name || "");
      set("clientFirstName", "");
      set("clientLastName", "");
    } else {
      const first = (client.name || "").split(" ").slice(0, 1).join(" ");
      const last = (client.name || "").split(" ").slice(1).join(" ");
      set("clientFirstName", first);
      set("clientLastName", last);
      set("clientCompanyName", "");
    }
    set("clientAddress", client.address || "");
    set("clientEmail", client.email || "");
    set("clientPhone", client.phone || "");
    set("city", client.location || "");
  };

  const loadRecentOrders = async () => {
    try {
      const rows = await TechModulAPI.getOrders(projectId);
      setRecentOrders(rows.slice(0, 5));
    } catch {
      setRecentOrders([]);
    }
  };

  const loadMaterialsDb = async () => {
    setMaterialsDbLoading(true);
    try {
      const rows = await TechModulAPI.getMaterials();
      setMaterialsDb(rows);
    } catch {
      setMaterialsDb([]);
    } finally {
      setMaterialsDbLoading(false);
    }
  };

  const saveClientToDatabase = async () => {
    if (savingClient) return;

    const normalizedClientName = clientDisplayName.trim();
    if (!normalizedClientName) {
      setClientSaveInfo("Podaj nazwe klienta przed zapisem.");
      setClientSaveState("error");
      return;
    }

    setSavingClient(true);
    setClientSaveInfo(null);
    setClientSaveState(null);

    try {
      const exists = clients.some(
        (client) => client.name.trim().toLowerCase() === normalizedClientName.toLowerCase()
      );
      if (exists) {
        setClientSaveInfo("Klient juz istnieje w bazie.");
        setClientSaveState("info");
        return;
      }

      await TechModulAPI.createClient({
        name: normalizedClientName,
        location: form.city.trim(),
        address: formattedClientAddress,
        email: form.clientEmail.trim(),
        phone: form.clientPhone.trim(),
        type: form.clientType,
        status: "active",
      });

      await loadClients();
      setClientSaveInfo("Klient poprawnie zapisany w bazie.");
      setClientSaveState("success");
    } catch (e: any) {
      setClientSaveInfo(e?.message ?? "Nie udalo sie zapisac klienta.");
      setClientSaveState("error");
    } finally {
      setSavingClient(false);
    }
  };

  const addPosition = async () => {
    if (!positionDraft.name.trim()) return;
    const normalizedName = positionDraft.name.trim();
    const isServiceMethodSelected = serviceModeKeys.has(valuationMethod);
    let pricingInput: Record<string, unknown> | undefined;
    let pricingResult: ServicePricingResult | null = null;
    if (isServiceMethodSelected) {
      pricingInput = buildServicePricingInput({ mode: valuationMethod, qty: Number(positionDraft.quantity) || 1 });
      pricingResult = await requestServicePricingPreview(pricingInput);
      if (!pricingResult) return;
    }
    const normalizedVat = Number.isFinite(Number(positionDraft.vat))
      ? Number(positionDraft.vat)
      : positionDraft.purchaseType === "cash"
      ? 0
      : 23;
    const nextPayload = {
      name: normalizedName,
      type: positionDraft.type,
      quantity: Number(positionDraft.quantity) || 1,
      vat: normalizedVat,
      description: positionDraft.description.trim(),
      textureOrColor: positionDraft.textureOrColor.trim(),
      purchaseType: positionDraft.purchaseType,
      serviceMode: isServiceMethodSelected ? valuationMethod : undefined,
      serviceSummary: isServiceMethodSelected ? pricingResult?.summary_text : undefined,
      serviceEstimatedNet: isServiceMethodSelected ? pricingResult?.buckets?.net_total : undefined,
      servicePricing: isServiceMethodSelected ? pricingResult ?? undefined : undefined,
      servicePricingInput: isServiceMethodSelected ? pricingInput : undefined,
      sourceType: isServiceMethodSelected ? ("manual" as const) : undefined,
      baseMaterialName: selectedServiceMaterial?.name || "",
      lengthMm: Math.max(0, Number(serviceEstimator.lengthMm) || 0),
      widthMm: Math.max(0, Number(serviceEstimator.widthMm) || 0),
      thicknessMm: Math.max(0, Number(serviceEstimator.thicknessMm) || 0),
      edgeTop: Boolean(serviceEstimator.edgeTop),
      edgeBottom: Boolean(serviceEstimator.edgeBottom),
      edgeLeft: Boolean(serviceEstimator.edgeLeft),
      edgeRight: Boolean(serviceEstimator.edgeRight),
    };

    if (editingPositionId) {
      setPositions((prev) =>
        prev.map((item) => (item.id === editingPositionId ? { ...item, ...nextPayload } : item))
      );
      setMaterialChoices((prev) =>
        prev.map((item) =>
          item.positionId === editingPositionId ? { ...item, positionName: normalizedName } : item
        )
      );
      setActivePositionId(editingPositionId);
      setEditingPositionId(null);
      setPositionDraft({
        name: "",
        type: isServicesMode ? "Usluga" : "Kuchnia",
        quantity: 1,
        vat: 23,
        description: "",
        textureOrColor: "",
        purchaseType: "invoice",
      });
      return;
    }

    const newId = crypto.randomUUID();
    setPositions((prev) => [
      ...prev,
      {
        id: newId,
        ...nextPayload,
      },
    ]);
    setSpecByTarget((prev) => {
      const fallback = prev[TECH_SCOPE_DEFAULT] ?? {
        bodyMaterial: "Plyta laminowana",
        frontMaterial: "Lakier MDF",
        hardwareBrand: "Blum",
        accessories: [],
      };
      return { ...prev, [newId]: { ...fallback, accessories: [...fallback.accessories] } };
    });
    setActivePositionId(newId);
    setPositionDraft({
      name: "",
      type: isServicesMode ? "Usluga" : "Kuchnia",
      quantity: 1,
      vat: 23,
      description: "",
      textureOrColor: "",
      purchaseType: "invoice",
    });
  };

  const importProjectRowsToUnifiedTable = async (file: File) => {
    if (projectImportLoading) return;
    setProjectImportLoading(true);
    setError(null);
    try {
      const parsed = await TechModulAPI.importParse(file);
      const defaultMode: WizardMethod = serviceModeKeys.has(valuationMethod)
        ? normalizeServiceMode(valuationMethod)
        : PRIMARY_CUTTING_SERVICE_MODE;
      const materialByName = new Map(
        materialsDb.map((m) => [String(m.name || "").trim().toLowerCase(), m])
      );

      const importedRows = await Promise.all(
        (parsed.rows || []).map(async (row, idx) => {
          const materialName = String(row.material_original || "").trim();
          const matchedMaterial = materialByName.get(materialName.toLowerCase());
          const qty = Math.max(1, Number(row.qty) || 1);
          const servicePricingInput = {
            schema_version: UNIFIED_SERVICE_ROW_SCHEMA_VERSION,
            service_mode: defaultMode,
            service_subtype: defaultMode,
            base_material_id: matchedMaterial ? String(matchedMaterial.id) : "",
            base_material_name: matchedMaterial?.name || materialName || "",
            base_material_price_m2: Number(matchedMaterial?.price || 0),
            base_thickness_mm: Math.max(0, Number(row.thickness_mm) || 0),
            length_mm: Math.max(0, Number(row.length_mm) || 0),
            width_mm: Math.max(0, Number(row.width_mm) || 0),
            quantity: qty,
            edge_mode: "default",
            edge_default_material_id: "",
            edge_top: false,
            edge_bottom: false,
            edge_left: false,
            edge_right: false,
            cnc_pattern: serviceEstimator.cncPattern,
            front_model_code: "",
            lacquer: false,
            lacquer_sides: 1,
            veneer_sides: 1,
            veneer_lacquer: false,
            bent_shape: "arc",
            bent_radius_mm: 0,
            bent_complexity: 1,
            extra_layers: [],
            technology_summary: row.technology_summary || undefined,
          } as Record<string, unknown>;
          const preview = await requestServicePricingPreview(servicePricingInput, { silent: true });
          const name = String(row.name || "").trim() || `Import ${idx + 1}`;
          return {
            id: crypto.randomUUID(),
            name,
            type: "Formatka",
            quantity: qty,
            vat: 23,
            description: String(row.code || row.section || "").trim(),
            purchaseType: "invoice" as const,
            serviceMode: defaultMode,
            serviceSummary: preview?.summary_text || "",
            serviceEstimatedNet: preview?.buckets?.net_total,
            servicePricing: preview ?? undefined,
            servicePricingInput,
            sourceType: "project_import" as const,
            baseMaterialName: materialName || matchedMaterial?.name || "",
            lengthMm: Math.max(0, Number(row.length_mm) || 0),
            widthMm: Math.max(0, Number(row.width_mm) || 0),
            thicknessMm: Math.max(0, Number(row.thickness_mm) || 0),
            textureOrColor: "",
            edgeTop: false,
            edgeBottom: false,
            edgeLeft: false,
            edgeRight: false,
            technologySummary: row.technology_summary || undefined,
          } as PositionItem;
        })
      );
      setPositions((prev) => [...prev, ...importedRows]);
      if (importedRows.length > 0) {
        setActivePositionId(importedRows[0].id);
      }
    } catch (e: any) {
      setError(e?.message ?? "Nie udalo sie zaimportowac .project do unified tabeli");
    } finally {
      setProjectImportLoading(false);
    }
  };

  const startEditPosition = (positionId: string) => {
    const found = positions.find((p) => p.id === positionId);
    if (!found) return;
    if (found.serviceMode && serviceModeKeys.has(found.serviceMode)) {
      setValuationMethod(normalizeServiceMode(found.serviceMode));
    }
    setActivePositionId(positionId);
    setEditingPositionId(positionId);
    setPositionDraft({
      name: found.name,
      type: found.type,
      quantity: found.quantity,
      vat: found.vat,
      description: found.description,
      textureOrColor: found.textureOrColor || "",
      purchaseType: found.purchaseType ?? "invoice",
    });
    if (found.servicePricingInput && typeof found.servicePricingInput === "object") {
      const input = found.servicePricingInput as Record<string, unknown>;
      setServiceEstimator((prev) => ({
        ...prev,
        materialId: String(input.base_material_id ?? prev.materialId ?? ""),
        edgeMaterialId: String(input.edge_default_material_id ?? prev.edgeMaterialId ?? ""),
        lengthMm: Math.max(0, Number(input.length_mm ?? prev.lengthMm) || 0),
        widthMm: Math.max(0, Number(input.width_mm ?? prev.widthMm) || 0),
        thicknessMm: Math.max(0, Number(input.base_thickness_mm ?? prev.thicknessMm) || 0),
        qty: Math.max(1, Number(input.quantity ?? prev.qty) || 1),
        edgeTop: Boolean(input.edge_top ?? prev.edgeTop),
        edgeBottom: Boolean(input.edge_bottom ?? prev.edgeBottom),
        edgeLeft: Boolean(input.edge_left ?? prev.edgeLeft),
        edgeRight: Boolean(input.edge_right ?? prev.edgeRight),
        cncPattern: String(input.cnc_pattern || prev.cncPattern || "line") as ServiceEstimatorDraft["cncPattern"],
        lacquer: Boolean(input.lacquer ?? prev.lacquer),
        lacquerSides: Number(input.lacquer_sides) === 2 ? 2 : 1,
        veneerSides: Number(input.veneer_sides) === 2 ? 2 : 1,
        veneerLacquer: Boolean(input.veneer_lacquer ?? prev.veneerLacquer),
        bentShape: String(input.bent_shape || prev.bentShape || "arc") as ServiceEstimatorDraft["bentShape"],
        bentRadiusMm: Math.max(0, Number(input.bent_radius_mm ?? prev.bentRadiusMm) || 0),
        bentComplexity: (Math.max(1, Math.min(3, Number(input.bent_complexity ?? prev.bentComplexity) || 1)) as
          | 1
          | 2
          | 3),
      }));
    }
    if (found.servicePricing) {
      setServicePricingPreview(found.servicePricing);
      return;
    }
    if (found.servicePricingInput && found.serviceMode && serviceModeKeys.has(found.serviceMode)) {
      void requestServicePricingPreview(found.servicePricingInput, { silent: true });
    }
  };

  const cancelEditPosition = () => {
    setEditingPositionId(null);
    setPositionDraft({
      name: "",
      type: isServicesMode ? "Usluga" : "Kuchnia",
      quantity: 1,
      vat: 23,
      description: "",
      textureOrColor: "",
      purchaseType: "invoice",
    });
    if (!serviceModeKeys.has(valuationMethod)) {
      setServicePricingPreview(null);
    }
  };

  const applyServiceParamsToActiveRow = async () => {
    if (!activePositionId) return;
    const active = positions.find((p) => p.id === activePositionId);
    if (!active) return;
    const rowMode = normalizeServiceMode(
      active.serviceMode && serviceModeKeys.has(active.serviceMode) ? active.serviceMode : valuationMethod
    );
    if (!serviceModeKeys.has(rowMode)) return;
    const existingInput =
      active.servicePricingInput && typeof active.servicePricingInput === "object"
        ? (active.servicePricingInput as Record<string, unknown>)
        : {};
    const nextInput = {
      ...existingInput,
      ...buildServicePricingInput({
        mode: rowMode,
        qty: active.quantity,
        technologySummary:
          (existingInput.technology_summary as Record<string, unknown> | undefined) ||
          (active.technologySummary as Record<string, unknown> | undefined),
      }),
    };
    const pricingResult = await requestServicePricingPreview(nextInput);
    if (!pricingResult) return;
    setPositions((prev) =>
      prev.map((row) =>
        row.id === activePositionId
          ? {
              ...row,
              serviceMode: rowMode,
              servicePricingInput: nextInput,
              servicePricing: pricingResult,
              serviceEstimatedNet: pricingResult.buckets.net_total,
              serviceSummary: pricingResult.summary_text,
            }
          : row
      )
    );
  };

  const removePosition = (positionId: string) => {
    setPositions((prev) => prev.filter((row) => row.id !== positionId));
    setSpecByTarget((prev) => {
      const next = { ...prev };
      delete next[positionId];
      return next;
    });
    setMaterialChoices((prev) => prev.filter((row) => row.positionId !== positionId));
    if (specTargetId === positionId) setSpecTargetId(TECH_SCOPE_DEFAULT);
    if (activePositionId === positionId) setActivePositionId("");
    if (editingPositionId === positionId) cancelEditPosition();
  };

  const onPickAttachment = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const next: AttachmentItem = {
      id: crypto.randomUUID(),
      name: file.name,
      type: file.type.includes("pdf") ? "PDF" : "IMG",
      description: attachmentDraft.description.trim(),
      file,
    };

    setAttachments((prev) => [...prev, next]);
    setSelectedAttachmentId(next.id);
    setAttachmentDraft((prev) => ({ ...prev, description: "" }));
    event.target.value = "";
  };

  const addMaterialChoice = () => {
    if (!materialDraft.positionId) return;
    if (!materialDraft.material.trim()) return;
    const targetPosition = positions.find((p) => p.id === materialDraft.positionId);
    if (!targetPosition) return;

    setMaterialChoices((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        positionId: targetPosition.id,
        positionName: targetPosition.name,
        scope: materialDraft.scope,
        material: materialDraft.material.trim(),
        color: materialDraft.color.trim(),
        code: materialDraft.code.trim(),
        status: materialDraft.status,
        date: materialDraft.date,
        notes: materialDraft.notes.trim(),
      },
    ]);

    setMaterialDraft((prev) => ({ ...prev, material: "", color: "", code: "", notes: "" }));
  };

  const applyMaterialFromDatabase = () => {
    if (!materialDbSelectedId) return;
    const found = filteredDbMaterials.find((m) => String(m.id) === materialDbSelectedId)
      ?? materialsDb.find((m) => String(m.id) === materialDbSelectedId);
    if (!found) return;

    let parsedColor = "";
    if (found.color_hex) parsedColor = found.color_hex;
    if (!parsedColor && found.parameter_json) {
      try {
        const parsed = JSON.parse(found.parameter_json);
        parsedColor =
          String(parsed?.color || parsed?.decor || parsed?.ncs || parsed?.ncs_code || "").trim();
      } catch {
        parsedColor = "";
      }
    }

    setMaterialDraft((prev) => ({
      ...prev,
      material: found.name || prev.material,
      code: found.material_code || prev.code,
      color: parsedColor || prev.color,
    }));
  };

  const removeSelectedMaterial = () => {
    if (!selectedMaterialId) return;
    setMaterialChoices((prev) => prev.filter((item) => item.id !== selectedMaterialId));
    setSelectedMaterialId(null);
  };

  const addPayment = () => {
    if (!paymentDraft.stage.trim()) return;
    setPayments((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        stage: paymentDraft.stage.trim(),
        amount: Number(paymentDraft.amount) || 0,
        cash: paymentDraft.cash,
        method: paymentDraft.method,
        cashbox: paymentDraft.cashbox,
        paid: paymentDraft.paid,
        date: paymentDraft.date,
        notes: paymentDraft.notes.trim(),
      },
    ]);
    setPaymentDraft((prev) => ({ ...prev, amount: 0, notes: "", paid: false }));
  };

  const addDefaultPayments = () => {
    const defaults: PaymentRow[] = [
      {
        id: crypto.randomUUID(),
        stage: "Rezerwacja terminu",
        amount: 1000,
        cash: false,
        method: "invoice_vat",
        cashbox: "kasa_faktura_vat",
        paid: false,
        date: new Date().toISOString().slice(0, 10),
        notes: "",
      },
      {
        id: crypto.randomUUID(),
        stage: "Start prac",
        amount: 3000,
        cash: false,
        method: "invoice_vat",
        cashbox: "kasa_faktura_vat",
        paid: false,
        date: new Date().toISOString().slice(0, 10),
        notes: "",
      },
      {
        id: crypto.randomUUID(),
        stage: "Przed montazem",
        amount: 3000,
        cash: false,
        method: "invoice_vat",
        cashbox: "kasa_faktura_vat",
        paid: false,
        date: new Date().toISOString().slice(0, 10),
        notes: "",
      },
      {
        id: crypto.randomUUID(),
        stage: "Rozliczenie koncowe",
        amount: 2000,
        cash: false,
        method: "invoice_vat",
        cashbox: "kasa_faktura_vat",
        paid: false,
        date: new Date().toISOString().slice(0, 10),
        notes: "",
      },
    ];
    setPayments(defaults);
    setSelectedPaymentId(null);
  };

  const removeSelectedPayment = () => {
    if (!selectedPaymentId) return;
    setPayments((prev) => prev.filter((item) => item.id !== selectedPaymentId));
    setSelectedPaymentId(null);
  };

  const togglePaymentStatus = () => {
    if (!selectedPaymentId) return;
    setPayments((prev) =>
      prev.map((item) => (item.id === selectedPaymentId ? { ...item, paid: !item.paid } : item))
    );
  };

  const saveOrder = async () => {
    if (!canSaveOrder || savingOrder) return false;

    setSavingOrder(true);
    setError(null);

    try {
      const normalizedClientName = clientDisplayName.trim();
      const clientExists = clients.some(
        (client) => client.name.trim().toLowerCase() === normalizedClientName.toLowerCase()
      );

      if (!clientExists && normalizedClientName) {
        try {
          await TechModulAPI.createClient({
            name: normalizedClientName,
            location: form.city.trim(),
            address: formattedClientAddress,
            email: form.clientEmail.trim(),
            phone: form.clientPhone.trim(),
            type: form.clientType,
            status: "active",
          });
          await loadClients();
        } catch {
          // do not block order save if client sync failed
        }
      }

      const budgetNumber = Number(String(form.budget || "").replace(",", "."));
      const payloadSpec = {
        ...form.spec,
        unified_service_row_schema_version: UNIFIED_SERVICE_ROW_SCHEMA_VERSION,
        client_profile: {
          type: form.clientType,
          first_name: form.clientFirstName,
          last_name: form.clientLastName,
          company_name: form.clientCompanyName,
          nip: form.clientNip,
          email: form.clientEmail,
          phone: form.clientPhone,
          city: form.city,
          street: form.street,
          building: form.building,
          apartment: form.apartment,
          zip_code: form.zipCode,
          address_extra: form.clientAddress,
          full_address: formattedClientAddress,
        },
        technical_scope_target_id: specTargetId,
        technical_spec_default: specByTarget[TECH_SCOPE_DEFAULT] ?? null,
        technical_spec_by_scope: specByTarget,
        valuation_method: valuationMethod,
        positions,
        service_rows: positions,
        attachments: attachments.map((a) => ({
          name: a.name,
          type: a.type,
          description: a.description,
        })),
        material_choices: materialChoices,
        payment_plan: payments,
        services: services.map((row) => ({
          ...row,
          client_name: clientDisplayName,
        })),
        order_description: form.description,
        technical_notes: form.notes,
      };

      const result = await TechModulAPI.createOrder({
        project_id: projectId,
        client_name: normalizedClientName,
        title: form.orderTitle.trim(),
        deadline: form.deadlineTo || form.deadlineFrom || "",
        deadline_from: form.deadlineFrom || "",
        deadline_to: form.deadlineTo || "",
        budget: Number.isFinite(budgetNumber) ? budgetNumber : 0,
        status: form.status,
        spec_json: JSON.stringify(payloadSpec),
      });

      setSavedOrderId(result.id);
      setLastSavedSignature(currentDraftSignature);
      await loadRecentOrders();
      return true;
    } catch (e: any) {
      setError(e?.message ?? "Nie udalo sie zapisac zamowienia");
      return false;
    } finally {
      setSavingOrder(false);
    }
  };

  const goToStep = async (targetStep: number) => {
    const nextStep = Math.max(1, Math.min(STEPS.length, targetStep));
    if (nextStep === step) return;

    if (hasUnsavedChanges) {
      const shouldSaveBeforeMove = window.confirm(
        "Masz niezapisane zmiany. Czy zapisac do bazy przed przejsciem do kolejnego kroku?"
      );

      if (shouldSaveBeforeMove) {
        if (!canSaveOrder) {
          setError("Aby zapisac, uzupelnij wymagane pola (klient i tytul zamowienia).");
          return;
        }
        const saved = await saveOrder();
        if (!saved) return;
      }
    }

    setStep(nextStep);
  };

  const handleValuationMethodSelect = async (method: WizardMethod) => {
    setValuationMethod(method);
    if (isServicesMode) {
      if (serviceModeKeys.has(method)) {
        const label =
          SERVICE_MODE_LABEL[
            method as
              | "service-cut"
              | "service-cut-edge"
              | "service-front-cnc-lacquer"
              | "service-veneer"
              | "service-bent-elements"
          ];
        setPositionDraft((prev) => ({ ...prev, type: label }));
      }
      return;
    }

    const routeByMethod: Partial<Record<WizardMethod, string>> = {
      project: "/configuration",
      "quick-module": "/configuration",
      "quick-section": "/assembly",
      import3d: "/workspace/import",
    };
    const targetRoute = routeByMethod[method];
    if (!targetRoute) return;

    if (hasUnsavedChanges) {
      const shouldSaveBeforeMove = window.confirm(
        "Masz niezapisane zmiany. Czy zapisac do bazy przed otwarciem wybranego trybu wyceny?"
      );
      if (shouldSaveBeforeMove) {
        if (!canSaveOrder) {
          setError("Aby zapisac, uzupelnij wymagane pola (klient i tytul zamowienia).");
          return;
        }
        const saved = await saveOrder();
        if (!saved) return;
      }
    }

    const modeParam = encodeURIComponent(method);
    const backTo = encodeURIComponent(`/orders/new?step=2&method=${modeParam}`);
    router.push(`${targetRoute}?mode=${modeParam}&project_id=${projectId}&from=${backTo}`);
  };

  const clearForm = () => {
    setForm((prev) => ({
      ...prev,
      clientName: "",
      clientFirstName: "",
      clientLastName: "",
      clientCompanyName: "",
      clientAddress: "",
      clientEmail: "",
      clientPhone: "",
      clientNip: "",
      orderTitle: "",
      city: "",
      street: "",
      building: "",
      apartment: "",
      zipCode: "",
      deadlineFrom: "",
      deadlineTo: "",
      description: "",
      notes: "",
      status: "Nowe",
    }));
    setPositions([]);
    setServiceEstimator(createDefaultServiceEstimator());
    setAttachments([]);
    setMaterialChoices([]);
    setPayments([]);
    setServices(
      SERVICES_CATALOG.map((name) => ({
        id: crypto.randomUUID(),
        name,
        enabled: false,
        qty: 1,
        unit: "szt",
        unitPrice: 0,
        notes: "",
      }))
    );
    setSavedOrderId(null);
    setLastSavedSignature(null);
    setError(null);
    try {
      localStorage.removeItem(draftStorageKey);
    } catch {
      // ignore storage errors
    }
  };

  const currentStepLabel = STEPS.find((item) => item.id === step)?.label ?? "Klient";
  const selectedAttachment = attachments.find((item) => item.id === selectedAttachmentId) ?? null;
  const visibleMaterialChoices =
    materialsView === "active" && activePositionId
      ? materialChoices.filter((item) => item.positionId === activePositionId)
      : materialChoices;
  const materialSummaryRows = useMemo(() => {
    const map = new Map<
      string,
      {
        positionName: string;
        scope: string;
        material: string;
        color: string;
        code: string;
        status: "Proba" | "Final";
        date: string;
        notes: string;
        count: number;
      }
    >();

    for (const item of materialChoices) {
      const key = [
        item.positionId,
        item.scope.trim().toLowerCase(),
        item.material.trim().toLowerCase(),
        item.color.trim().toLowerCase(),
        item.code.trim().toLowerCase(),
      ].join("::");
      const existing = map.get(key);
      if (!existing) {
        map.set(key, {
          positionName: item.positionName,
          scope: item.scope,
          material: item.material,
          color: item.color,
          code: item.code,
          status: item.status,
          date: item.date,
          notes: item.notes,
          count: 1,
        });
        continue;
      }
      existing.count += 1;
      if ((item.date || "") >= (existing.date || "")) {
        existing.date = item.date;
        existing.status = item.status;
        existing.notes = item.notes;
      }
    }

    return Array.from(map.values()).sort((a, b) => {
      const byPos = a.positionName.localeCompare(b.positionName);
      if (byPos !== 0) return byPos;
      const byScope = a.scope.localeCompare(b.scope);
      if (byScope !== 0) return byScope;
      return a.material.localeCompare(b.material);
    });
  }, [materialChoices]);
  const specScopeRows = useMemo(() => {
    const allTargets = [TECH_SCOPE_DEFAULT, ...positions.map((p) => p.id)];
    return allTargets.map((targetId) => {
      const cfg = specByTarget[targetId] ?? specByTarget[TECH_SCOPE_DEFAULT] ?? {
        bodyMaterial: "Plyta laminowana",
        frontMaterial: "Lakier MDF",
        hardwareBrand: "Blum",
        accessories: [],
      };
      return { targetId, cfg };
    });
  }, [positions, specByTarget]);

  return (
    <AppShell>
      <div className="flex h-full w-full flex-col overflow-hidden bg-transparent text-[11px] text-slate-200 select-none">
        <div className="h-10 shrink-0 border-b border-[#111] bg-[#2d2d2d] px-4 shadow-md">
          <div className="flex h-full items-center justify-between gap-4">
            <div className="flex items-center gap-3 overflow-x-auto">
              <span className="whitespace-nowrap font-bold tracking-wider text-slate-300">
                {isServicesMode
                  ? `KREATOR USLUG / PROJEKT #${projectId}`
                  : `KREATOR ZAMOWIENIA / PROJEKT #${projectId}`}
              </span>
              <div className="h-4 w-px bg-[#444]" />
              {STEPS.filter((item) => item.id !== 6).map((item) => (
                <button
                  key={item.id}
                  onClick={() => {
                    void goToStep(item.id);
                  }}
                  className={clsx(
                    "whitespace-nowrap rounded-sm px-2 py-1 transition-colors",
                    step === item.id
                      ? "bg-blue-600 font-bold text-white"
                      : "text-slate-400 hover:bg-[#3e3e42]"
                  )}
                >
                  {item.id}. {item.label}
                </button>
              ))}
            </div>
            <button
              onClick={saveOrder}
              disabled={!canSaveOrder || savingOrder}
              className={clsx(
                "flex items-center gap-1.5 rounded-sm px-3 py-1 font-bold transition-colors",
                canSaveOrder
                  ? "bg-emerald-600 text-white hover:bg-emerald-500"
                  : "border border-[#333] bg-[#1e1e1e] text-slate-500"
              )}
            >
              {savingOrder ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Save className="h-3.5 w-3.5" />
              )}
              Zapisz zamowienie
            </button>
          </div>
        </div>

        <div className="h-10 shrink-0 border-b border-[#1a1a1a] bg-[#252526] px-3">
          <div className="flex h-full items-center justify-between gap-2">
            <div className="font-black text-slate-300">
              Krok {step}/{STEPS.length} - {currentStepLabel}
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                className="h-8"
                onClick={() => {
                  void goToStep(step - 1);
                }}
              >
                <ChevronLeft className="h-4 w-4" /> Wstecz
              </Button>
              <Button
                variant="ghost"
                className="h-8"
                onClick={() => {
                  void goToStep(step + 1);
                }}
              >
                Dalej <ChevronRight className="h-4 w-4" />
              </Button>
              <Button className="h-8" onClick={saveOrder} disabled={!canSaveOrder || savingOrder}>
                {savingOrder ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Save className="h-4 w-4" />
                )}{" "}
                Zapisz
              </Button>
              <Button
                className="h-8"
                variant="secondary"
                onClick={saveClientToDatabase}
                disabled={savingClient || !clientDisplayName.trim()}
              >
                Dodaj bazy
              </Button>
              <Button className="h-8" variant="secondary" onClick={clearForm}>
                <RotateCcw className="h-4 w-4" /> Wyczysc
              </Button>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-auto custom-scrollbar px-3 py-2">
          <div className="mb-2">
            <BusinessHealthStrip
              scope={isServicesMode ? "Uslugi i wyceny" : "Zamowienia i wyceny"}
              subtitle={
                isServicesMode
                  ? "Widok dla uslug: ile kosztuje godzina pracy i czy firma ma zdrowy bufor na realizacje."
                  : "Widok dla zamowien: pieniadze, ryzyko i koszt realizacji widoczne bez wychodzenia z kreatora."
              }
            />
          </div>
          {error ? (
            <div className="mb-3 flex items-center gap-2 rounded border border-red-500/30 bg-red-500/10 px-3 py-2 text-red-300">
              <AlertCircle className="h-4 w-4" />
              {error}
            </div>
          ) : null}

          {clientSaveInfo ? (
            <div
              className={clsx(
                "mb-3 rounded border px-3 py-2",
                clientSaveState === "success" &&
                  "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
                clientSaveState === "error" &&
                  "border-rose-500/30 bg-rose-500/10 text-rose-300",
                clientSaveState === "info" &&
                  "border-slate-500/30 bg-slate-500/10 text-slate-300"
              )}
            >
              {clientSaveInfo}
            </div>
          ) : null}

          {step === 1 ? (
            <div className="space-y-2">
              <Card padded={false} className="rounded-md border-[#1f1f1f] bg-[#202020] px-3 py-2 shadow-none backdrop-blur-none">
                <div className="flex items-center gap-2">
                  <div className="relative flex-1">
                    <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                    <input
                      type="text"
                      value={clientQuery}
                      onChange={(e) => {
                        setClientQuery(e.target.value);
                        setShowClientDropdown(true);
                        setActiveClientIdx(-1);
                      }}
                      onFocus={() => setShowClientDropdown(true)}
                      onBlur={() => setTimeout(() => setShowClientDropdown(false), 150)}
                      onKeyDown={(e) => {
                        if (e.key === "ArrowDown") {
                          e.preventDefault();
                          setShowClientDropdown(true);
                          setActiveClientIdx((idx) =>
                            Math.min(idx + 1, filteredClients.length - 1)
                          );
                        } else if (e.key === "ArrowUp") {
                          e.preventDefault();
                          setActiveClientIdx((idx) => Math.max(idx - 1, 0));
                        } else if (e.key === "Enter") {
                          if (filteredClients.length === 0) return;
                          e.preventDefault();
                          const pickIdx = activeClientIdx >= 0 ? activeClientIdx : 0;
                          const pick = filteredClients[pickIdx];
                          if (pick) {
                            applyClientToForm(pick);
                            setClientQuery(pick.name);
                            setShowClientDropdown(false);
                            setActiveClientIdx(-1);
                          }
                        } else if (e.key === "Escape") {
                          setShowClientDropdown(false);
                          setActiveClientIdx(-1);
                        }
                      }}
                      placeholder="Wybierz z bazy: zacznij pisac nazwisko, telefon lub adres..."
                      className="w-full rounded-md border border-[#444] bg-[#2d2d2d] py-1.5 pl-9 pr-3 text-[12px] outline-none focus:border-blue-500"
                    />
                    {showClientDropdown && clientQuery.trim() && filteredClients.length > 0 ? (
                      <div className="absolute z-30 mt-1 w-full overflow-hidden rounded-xl border border-[#444] bg-[#1e1e1e] shadow-lg">
                        {filteredClients.map((client, idx) => (
                          <button
                            key={client.id}
                            type="button"
                            onMouseDown={(e) => e.preventDefault()}
                            onMouseEnter={() => setActiveClientIdx(idx)}
                            onClick={() => {
                              applyClientToForm(client);
                              setClientQuery(client.name);
                              setShowClientDropdown(false);
                              setActiveClientIdx(-1);
                            }}
                            className={clsx(
                              "flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-[12px] hover:bg-blue-600/10",
                              idx === activeClientIdx ? "bg-blue-600/15" : ""
                            )}
                          >
                            <div className="min-w-0 flex-1">
                              <div className="truncate font-bold text-white">{client.name}</div>
                              <div className="truncate text-[10px] text-slate-500">
                                {client.address || "Brak adresu"}
                                {client.phone ? ` · ${client.phone}` : ""}
                                {client.email ? ` · ${client.email}` : ""}
                              </div>
                            </div>
                            <span className="rounded-full border border-blue-500/30 bg-blue-500/10 px-2 py-0.5 text-[9px] font-black uppercase text-blue-300">
                              {client.type === "b2b" ? "Firma" : "Osoba"}
                            </span>
                          </button>
                        ))}
                      </div>
                    ) : null}
                    {showClientDropdown &&
                    clientQuery.trim() &&
                    filteredClients.length === 0 &&
                    !loadingClients ? (
                      <div className="absolute z-30 mt-1 w-full rounded-xl border border-[#444] bg-[#1e1e1e] px-3 py-2 text-[11px] text-slate-500 shadow-lg">
                        Brak wynikow w bazie
                      </div>
                    ) : null}
                  </div>
                  <button
                    type="button"
                    onClick={() => router.push("/database/clients")}
                    className="whitespace-nowrap text-[11px] font-semibold text-blue-400 hover:text-blue-300"
                  >
                    Otworz pelna baze →
                  </button>
                </div>
              </Card>
              <Card padded={false} className="rounded-md border-[#1f1f1f] bg-[#252526] px-3 py-2.5 shadow-none backdrop-blur-none">
                <div className="mb-2 text-[10px] font-black uppercase tracking-widest text-slate-400">
                  Dane kontrahenta
                </div>
                <div className="grid grid-cols-1 gap-x-3 gap-y-2 xl:grid-cols-6">
                  <div className="xl:col-span-2">
                    <label className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">
                      Typ
                    </label>
                    <select
                      className={baseInput}
                      value={form.clientType}
                      onChange={(e) => set("clientType", e.target.value as "person" | "b2b")}
                    >
                      <option value="person">Indywidualny</option>
                      <option value="b2b">Firma</option>
                    </select>
                  </div>
                  {form.clientType === "person" ? (
                    <>
                      <div className="xl:col-span-2">
                        <label className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">
                          Imie
                        </label>
                        <input
                          className={baseInput}
                          value={form.clientFirstName}
                          onChange={(e) => set("clientFirstName", e.target.value)}
                          placeholder="Imie klienta"
                        />
                      </div>
                      <div className="xl:col-span-2">
                        <label className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">
                          Nazwisko
                        </label>
                        <input
                          className={baseInput}
                          value={form.clientLastName}
                          onChange={(e) => set("clientLastName", e.target.value)}
                          placeholder="Nazwisko klienta"
                        />
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="xl:col-span-4">
                        <label className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">
                          Nazwa firmy
                        </label>
                        <input
                          className={baseInput}
                          value={form.clientCompanyName}
                          onChange={(e) => set("clientCompanyName", e.target.value)}
                          placeholder="Pelna nazwa firmy"
                        />
                      </div>
                    </>
                  )}
                  <div className="xl:col-span-2">
                    <label className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">
                      NIP
                    </label>
                    <input
                      className={baseInput}
                      value={form.clientNip}
                      onChange={(e) => set("clientNip", e.target.value)}
                      placeholder="NIP (opcjonalnie)"
                    />
                  </div>
                  <div className="xl:col-span-2">
                    <label className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">
                      Miasto
                    </label>
                    <input
                      className={baseInput}
                      value={form.city}
                      onChange={(e) => set("city", e.target.value)}
                      placeholder="Miasto"
                    />
                  </div>
                  <div className="xl:col-span-2">
                    <label className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">
                      Kod pocztowy
                    </label>
                    <input
                      className={baseInput}
                      value={form.zipCode}
                      onChange={(e) => set("zipCode", e.target.value)}
                      placeholder="00-000"
                    />
                  </div>
                  <div className="xl:col-span-2">
                    <label className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">
                      Ulica
                    </label>
                    <input
                      className={baseInput}
                      value={form.street}
                      onChange={(e) => set("street", e.target.value)}
                      placeholder="Ulica"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">
                      Budynek
                    </label>
                    <input
                      className={baseInput}
                      value={form.building}
                      onChange={(e) => set("building", e.target.value)}
                      placeholder="Nr"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">
                      Mieszkanie
                    </label>
                    <input
                      className={baseInput}
                      value={form.apartment}
                      onChange={(e) => set("apartment", e.target.value)}
                      placeholder="Nr"
                    />
                  </div>
                  <div className="xl:col-span-4">
                    <label className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">
                      Adres dodatkowy / lokalizacja
                    </label>
                    <input
                      className={baseInput}
                      value={form.clientAddress}
                      onChange={(e) => set("clientAddress", e.target.value)}
                      placeholder="Klatka, pietro, kod domofonu itd."
                    />
                  </div>
                  <div className="xl:col-span-3">
                    <label className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">
                      Email
                    </label>
                    <input
                      className={baseInput}
                      value={form.clientEmail}
                      onChange={(e) => set("clientEmail", e.target.value)}
                    />
                  </div>
                  <div className="xl:col-span-3">
                    <label className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">
                      Telefon
                    </label>
                    <input
                      className={baseInput}
                      value={form.clientPhone}
                      onChange={(e) => set("clientPhone", e.target.value)}
                    />
                  </div>
                  <div className="xl:col-span-3">
                    <label className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">
                      Opis projektu / lokalizacja
                    </label>
                    <textarea
                      className={clsx(baseInput, "h-20 resize-none")}
                      value={form.description}
                      onChange={(e) => set("description", e.target.value)}
                      placeholder="np. Apartament 12, III pietro"
                    />
                  </div>
                  <div className="xl:col-span-3">
                    <label className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">
                      Notatka techniczna
                    </label>
                    <textarea
                      className={clsx(baseInput, "h-20 resize-none")}
                      value={form.notes}
                      onChange={(e) => set("notes", e.target.value)}
                      placeholder="Uwagi do klienta / montazu"
                    />
                  </div>
                  <Button
                    className="h-9 xl:col-span-6"
                    onClick={saveClientToDatabase}
                    disabled={savingClient || !clientDisplayName.trim()}
                  >
                    {savingClient ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Save className="h-4 w-4" />
                    )}{" "}
                    Zapisz klienta do bazy ({clientDisplayName || "brak nazwy"})
                  </Button>
                </div>
              </Card>
            </div>
          ) : null}

          {step === 3 ? (
            <div className="space-y-4">
              <Card className="border-[#333] bg-[#1e1e1e] p-4">
                <div className="mb-2 text-xl font-bold">Karta techniczna</div>
                <div className="mb-4 text-sm text-slate-400">
                  Doprecyzuj detale konstrukcyjne i terminy.
                </div>
                <div className="mb-4 rounded-lg border border-blue-500/20 bg-blue-500/5 px-3 py-2 text-[11px] text-blue-200">
                  Konfigurujesz dla:{" "}
                  <span className="font-black">{getScopeLabel(specTargetId)}</span>
                  {positions.length === 0 ? (
                    <span className="ml-2 text-slate-300">
                      (dodaj najpierw pozycje w kroku 2, wtedy przypniesz konfiguracje do konkretnej szafki/sekcji)
                    </span>
                  ) : null}
                </div>

                {positions.length > 0 ? (
                  <div className="mb-4 rounded-lg border border-[#2b3952] bg-[#121b2b] p-2">
                    <div className="mb-1 text-[10px] uppercase tracking-widest text-slate-400">
                      Pozycja robocza
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {positions.map((p, idx) => (
                        <button
                          key={p.id}
                          className={clsx(
                            "rounded-md px-3 py-1.5 text-[10px] font-black uppercase tracking-widest",
                            activePositionId === p.id
                              ? "bg-blue-600 text-white"
                              : "bg-[#1d2636] text-slate-300"
                          )}
                          onClick={() => {
                            setActivePositionId(p.id);
                            setSpecTargetId(p.id);
                          }}
                        >
                          {idx + 1}. {p.name}
                        </button>
                      ))}
                      <button
                        className={clsx(
                          "rounded-md px-3 py-1.5 text-[10px] font-black uppercase tracking-widest",
                          specTargetId === TECH_SCOPE_DEFAULT
                            ? "bg-emerald-600 text-white"
                            : "bg-[#1d2636] text-slate-300"
                        )}
                        onClick={() => setSpecTargetId(TECH_SCOPE_DEFAULT)}
                      >
                        Domyslna (caly projekt)
                      </button>
                    </div>
                  </div>
                ) : null}

                <div className="mb-4 overflow-hidden rounded-lg border border-[#33445f]">
                  <div className="bg-[#bcc8da] px-3 py-2 text-[10px] font-black uppercase tracking-widest text-[#0b1c39]">
                    Matryca konfiguracji (pozycja do parametrow)
                  </div>
                  <div className="max-h-44 overflow-auto custom-scrollbar">
                    <table className="w-full border-collapse text-left">
                      <thead className="sticky top-0 bg-[#27344a] text-[10px] uppercase tracking-widest text-slate-300">
                        <tr>
                          <th className="px-2 py-2">Zakres</th>
                          <th className="px-2 py-2">Korpus</th>
                          <th className="px-2 py-2">Front</th>
                          <th className="px-2 py-2">Okucia</th>
                          <th className="px-2 py-2">Extra</th>
                        </tr>
                      </thead>
                      <tbody>
                        {specScopeRows.map(({ targetId, cfg }) => (
                          <tr
                            key={targetId}
                            className={clsx(
                              "cursor-pointer border-t border-white/5",
                              targetId === specTargetId ? "bg-blue-600/10" : "hover:bg-white/[0.03]"
                            )}
                            onClick={() => {
                              setSpecTargetId(targetId);
                              if (targetId !== TECH_SCOPE_DEFAULT) setActivePositionId(targetId);
                            }}
                          >
                            <td className="px-2 py-2 font-semibold">{getScopeLabel(targetId)}</td>
                            <td className="px-2 py-2">{cfg.bodyMaterial}</td>
                            <td className="px-2 py-2">{cfg.frontMaterial}</td>
                            <td className="px-2 py-2">{cfg.hardwareBrand}</td>
                            <td className="px-2 py-2 text-slate-300">
                              {cfg.accessories.length ? cfg.accessories.join(", ") : "-"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="mb-4 grid grid-cols-1 gap-2 md:grid-cols-[280px_1fr]">
                  <div>
                    <label className="mb-1 block text-[10px] uppercase tracking-widest text-slate-500">
                      Zakres konfiguracji
                    </label>
                    <select
                      className={baseInput}
                      value={specTargetId}
                      onChange={(e) => {
                        const next = e.target.value;
                        setSpecTargetId(next);
                        if (next !== TECH_SCOPE_DEFAULT) setActivePositionId(next);
                      }}
                    >
                      <option value={TECH_SCOPE_DEFAULT}>Domyslna dla calego zamowienia</option>
                      {positions.map((p, idx) => (
                        <option key={p.id} value={p.id}>
                          {idx + 1}. {p.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="flex flex-wrap gap-2 rounded-lg border border-[#2b3952] bg-[#121b2b] p-2">
                    <button
                      className={clsx(
                        "rounded-md px-3 py-1.5 text-[10px] font-black uppercase tracking-widest",
                        specTargetId === TECH_SCOPE_DEFAULT
                          ? "bg-blue-600 text-white"
                          : "bg-[#1d2636] text-slate-300"
                      )}
                      onClick={() => setSpecTargetId(TECH_SCOPE_DEFAULT)}
                    >
                      Domyslna
                    </button>
                    {positions.map((p, idx) => (
                      <button
                        key={p.id}
                        className={clsx(
                          "rounded-md px-3 py-1.5 text-[10px] font-black uppercase tracking-widest",
                          specTargetId === p.id ? "bg-blue-600 text-white" : "bg-[#1d2636] text-slate-300"
                        )}
                        onClick={() => {
                          setActivePositionId(p.id);
                          setSpecTargetId(p.id);
                        }}
                      >
                        {idx + 1}. {p.name}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="mb-4 grid grid-cols-1 gap-3 lg:grid-cols-3">
                  <div className="lg:col-span-1">
                    <label className="mb-1 block text-[10px] uppercase tracking-widest text-slate-500">
                      Tytul projektu
                    </label>
                    <input
                      className={baseInput}
                      value={form.orderTitle}
                      onChange={(e) => set("orderTitle", e.target.value)}
                      placeholder="Np. Szafa wnekowa - salon"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-[10px] uppercase tracking-widest text-slate-500">
                      Start (termin)
                    </label>
                    <input
                      type="date"
                      className={baseInput}
                      value={form.deadlineFrom}
                      onChange={(e) => set("deadlineFrom", e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-[10px] uppercase tracking-widest text-slate-500">
                      Koniec (termin)
                    </label>
                    <input
                      type="date"
                      className={baseInput}
                      value={form.deadlineTo}
                      onChange={(e) => set("deadlineTo", e.target.value)}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                  <div className="rounded-2xl border border-[#23314a] bg-[#101522] p-4">
                    <div className="mb-3 text-[12px] font-black uppercase tracking-widest text-slate-300">
                      Konstrukcja
                    </div>
                    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                      <div>
                        <label className="mb-1 block text-[10px] uppercase tracking-widest text-slate-500">
                          Korpus
                        </label>
                        <select
                          className={baseInput}
                          value={currentSpec.bodyMaterial}
                          onChange={(e) =>
                            setCurrentSpec((prev) => ({ ...prev, bodyMaterial: e.target.value }))
                          }
                        >
                          <option>Plyta laminowana</option>
                          <option>Plyta fornirowana</option>
                          <option>Sklejka</option>
                        </select>
                      </div>
                      <div>
                        <label className="mb-1 block text-[10px] uppercase tracking-widest text-slate-500">
                          Front
                        </label>
                        <select
                          className={baseInput}
                          value={currentSpec.frontMaterial}
                          onChange={(e) =>
                            setCurrentSpec((prev) => ({ ...prev, frontMaterial: e.target.value }))
                          }
                        >
                          <option>Lakier MDF</option>
                          <option>Fornir</option>
                          <option>Szklo</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-[#23314a] bg-[#101522] p-4">
                    <div className="mb-3 text-[12px] font-black uppercase tracking-widest text-slate-300">
                      Okucia
                    </div>
                    <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
                      {["Blum", "GTV", "Hettich", "Sevroll"].map((brand) => (
                        <button
                          key={brand}
                          onClick={() =>
                            setCurrentSpec((prev) => ({ ...prev, hardwareBrand: brand }))
                          }
                          className={clsx(
                            "rounded-lg border px-3 py-2 text-[10px] font-black uppercase tracking-widest",
                            currentSpec.hardwareBrand === brand
                              ? "border-blue-500 bg-blue-600/20 text-white"
                              : "border-[#2a2f3a] bg-[#0f1320] text-slate-400 hover:text-white"
                          )}
                        >
                          {brand}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-[#23314a] bg-[#101522] p-4 xl:col-span-2">
                    <div className="mb-3 text-[12px] font-black uppercase tracking-widest text-slate-300">
                      Wyposazenie extra
                    </div>
                    <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
                      {EXTRA_OPTIONS.map((extra) => {
                        const active = currentSpec.accessories.includes(extra);
                        return (
                          <button
                            key={extra}
                            onClick={() => {
                              setCurrentSpec((prev) => {
                                const exists = prev.accessories.includes(extra);
                                return {
                                  ...prev,
                                  accessories: exists
                                    ? prev.accessories.filter((item) => item !== extra)
                                    : [...prev.accessories, extra],
                                };
                              });
                            }}
                            className={clsx(
                              "rounded-lg border px-3 py-2 text-[10px] font-black uppercase tracking-widest",
                              active
                                ? "border-emerald-500/50 bg-emerald-500/15 text-emerald-300"
                                : "border-[#2a2f3a] bg-[#0f1320] text-slate-400"
                            )}
                          >
                            {extra}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>

              </Card>
            </div>
          ) : null}

          {step === 2 ? (
            <div className="space-y-3">
              <Card padded={false} className="rounded-md border-[#333] bg-[#1e1e1e] px-3 py-2 shadow-none backdrop-blur-none">
                <div className="flex items-center gap-3">
                  <div className="w-24 shrink-0 text-[11px] font-black uppercase tracking-widest text-slate-300">
                    {isServicesMode ? "Typ uslugi" : "Metoda wyceny"}
                  </div>
                  <div
                    className={clsx(
                      "grid min-w-0 flex-1 grid-cols-1 gap-1.5",
                      isServicesMode ? "md:grid-cols-2 xl:grid-cols-4" : "md:grid-cols-4"
                    )}
                  >
                    {(isServicesMode ? SERVICE_METHOD_OPTIONS : ORDER_METHOD_OPTIONS).map((method) => (
                      <button
                        key={method.key}
                        onClick={() => {
                          void handleValuationMethodSelect(method.key);
                        }}
                        className={clsx(
                          "h-11 rounded border px-2 text-center text-[10px] font-black uppercase tracking-widest whitespace-pre-line",
                          valuationMethod === method.key
                            ? "border-blue-500 bg-blue-600/20 text-white"
                            : "border-[#39465a] bg-[#242a34] text-slate-300"
                        )}
                      >
                        {method.label}
                      </button>
                    ))}
                  </div>
                  {isServicesMode ? (
                    <div className="shrink-0">
                      <Button
                        className="h-8"
                        variant="secondary"
                        onClick={() => projectImportInputRef.current?.click()}
                        disabled={projectImportLoading}
                      >
                        {projectImportLoading ? (
                          <>
                            <Loader2 className="h-3.5 w-3.5 animate-spin" /> Import .project...
                          </>
                        ) : (
                          <>
                            <Upload className="h-3.5 w-3.5" /> Importuj .project
                          </>
                        )}
                      </Button>
                      <input
                        ref={projectImportInputRef}
                        type="file"
                        className="hidden"
                        accept=".project"
                        onChange={(e) => {
                          const f = e.target.files?.[0];
                          if (f) {
                            void importProjectRowsToUnifiedTable(f);
                          }
                          e.target.value = "";
                        }}
                      />
                    </div>
                  ) : null}
                </div>
              </Card>

              {isServicesMode && (
                <Card padded={false} className="rounded-md border-[#333] bg-[#1e1e1e] px-3 py-2.5 shadow-none backdrop-blur-none">
                  <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <div className="text-[12px] font-black uppercase tracking-widest text-slate-300">
                        Nowa pozycja / parametry uslugi
                      </div>
                      <div className="mt-0.5 text-[10px] text-slate-500">
                        Jedna pozycja: nazwa, material, okleina, wymiary i kalkulacja w jednym miejscu.
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 text-[11px]">
                      <span className="rounded border border-[#33445f] bg-[#121b2b] px-2 py-1 text-slate-300">
                        Aktywny: {activePosition?.name || "-"}
                      </span>
                      <Button
                        className="h-8"
                        variant="secondary"
                        onClick={() => {
                          void applyServiceParamsToActiveRow();
                        }}
                        disabled={!activePositionId || !serviceModeKeys.has(valuationMethod)}
                      >
                        Zastosuj do aktywnego
                      </Button>
                    </div>
                  </div>

                  <div className="mb-2 grid grid-cols-1 gap-2 xl:grid-cols-[1fr_72px_80px_120px_150px_170px_120px_100px]">
                    <input
                      className={baseInput}
                      placeholder="Nazwa pozycji, np. Kuchnia"
                      value={positionDraft.name}
                      onChange={(e) =>
                        setPositionDraft((prev) => ({ ...prev, name: e.target.value }))
                      }
                    />
                    <input
                      type="number"
                      className={baseInput}
                      title="Ilosc"
                      value={positionDraft.quantity}
                      onChange={(e) =>
                        setPositionDraft((prev) => ({
                          ...prev,
                          quantity: Number(e.target.value) || 1,
                        }))
                      }
                    />
                    <input
                      type="number"
                      className={baseInput}
                      title="VAT %"
                      value={positionDraft.vat}
                      onChange={(e) =>
                        setPositionDraft((prev) => {
                          const parsed = Number(e.target.value);
                          return { ...prev, vat: Number.isFinite(parsed) ? parsed : 0 };
                        })
                      }
                    />
                    <input
                      className={baseInput}
                      placeholder="Typ"
                      value={positionDraft.type}
                      onChange={(e) =>
                        setPositionDraft((prev) => ({ ...prev, type: e.target.value }))
                      }
                    />
                    <select
                      className={baseInput}
                      value={positionDraft.purchaseType}
                      onChange={(e) =>
                        setPositionDraft((prev) => {
                          const nextType = e.target.value as "invoice" | "cash" | "receipt" | "none";
                          const shouldDefaultToZeroVat = nextType === "cash" && prev.vat === 23;
                          return {
                            ...prev,
                            purchaseType: nextType,
                            vat: shouldDefaultToZeroVat ? 0 : prev.vat,
                          };
                        })
                      }
                    >
                      {POSITION_PURCHASE_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                    <input
                      className={baseInput}
                      placeholder="Kolor / tekstura"
                      value={positionDraft.textureOrColor}
                      onChange={(e) =>
                        setPositionDraft((prev) => ({
                          ...prev,
                          textureOrColor: e.target.value,
                        }))
                      }
                    />
                    <Button
                      className="h-8"
                      onClick={() => {
                        void addPosition();
                      }}
                    >
                      {editingPositionId ? "Zapisz" : "+ Dodaj"}
                    </Button>
                    <Button
                      className="h-8"
                      variant="secondary"
                      onClick={cancelEditPosition}
                      disabled={!editingPositionId}
                    >
                      Anuluj
                    </Button>
                  </div>
                  <input
                    className={clsx(baseInput, "mb-2")}
                    placeholder="Opis / uwagi do wyceny"
                    value={positionDraft.description}
                    onChange={(e) =>
                      setPositionDraft((prev) => ({
                        ...prev,
                        description: e.target.value,
                      }))
                    }
                  />

                <div className="rounded border border-[#33445f] bg-[#101722] overflow-x-auto">
                  <table className="w-full min-w-[1360px] text-[11px]">
                    <thead className="bg-[#d4dde9] text-[#0f172a]">
                      <tr className="uppercase tracking-wide font-black">
                        <th className="px-2 py-1.5 text-left">Material bazowy</th>
                        <th className="px-2 py-1.5 text-left">Dl (mm)</th>
                        <th className="px-2 py-1.5 text-left">Sz (mm)</th>
                        <th className="px-2 py-1.5 text-left">Gr (mm)</th>
                        <th className="px-2 py-1.5 text-left">Ilosc</th>
                        <th className="px-2 py-1.5 text-left">Okleina</th>
                        <th className="px-2 py-1.5 text-center">Gora</th>
                        <th className="px-2 py-1.5 text-center">Dol</th>
                        <th className="px-2 py-1.5 text-center">Lewa</th>
                        <th className="px-2 py-1.5 text-center">Prawa</th>
                        <th className="px-2 py-1.5 text-left">Wybrana okleina</th>
                        <th className="px-2 py-1.5 text-left">Status materialu</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-t border-[#33445f] bg-[#111827]">
                        <td className="px-2 py-1.5">
                          <select
                            className={baseInput}
                            value={serviceEstimator.materialId}
                            onChange={(e) => setServiceEstimator((prev) => ({ ...prev, materialId: e.target.value }))}
                          >
                            <option value="">Material z bazy (opcjonalnie)</option>
                            {materialsDb.map((m) => (
                              <option key={`service-material-${m.id}`} value={String(m.id)}>
                                {m.name}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="px-2 py-1.5">
                          <input
                            type="number"
                            className={baseInput}
                            value={serviceEstimator.lengthMm}
                            onChange={(e) =>
                              setServiceEstimator((prev) => ({ ...prev, lengthMm: Math.max(0, Number(e.target.value) || 0) }))
                            }
                          />
                        </td>
                        <td className="px-2 py-1.5">
                          <input
                            type="number"
                            className={baseInput}
                            value={serviceEstimator.widthMm}
                            onChange={(e) =>
                              setServiceEstimator((prev) => ({ ...prev, widthMm: Math.max(0, Number(e.target.value) || 0) }))
                            }
                          />
                        </td>
                        <td className="px-2 py-1.5">
                          <input
                            type="number"
                            className={baseInput}
                            value={serviceEstimator.thicknessMm}
                            onChange={(e) =>
                              setServiceEstimator((prev) => ({ ...prev, thicknessMm: Math.max(0, Number(e.target.value) || 0) }))
                            }
                          />
                        </td>
                        <td className="px-2 py-1.5">
                          <input
                            type="number"
                            className={baseInput}
                            value={serviceEstimator.qty}
                            onChange={(e) =>
                              setServiceEstimator((prev) => ({ ...prev, qty: Math.max(1, Number(e.target.value) || 1) }))
                            }
                          />
                        </td>
                        <td className="px-2 py-1.5">
                          <select
                            className={baseInput}
                            value={serviceEstimator.edgeMaterialId}
                            onChange={(e) => setServiceEstimator((prev) => ({ ...prev, edgeMaterialId: e.target.value }))}
                          >
                            <option value="">Okleina z bazy (opcjonalnie)</option>
                            {materialsDb.map((m) => (
                              <option key={`service-edge-${m.id}`} value={String(m.id)}>
                                {m.name}
                              </option>
                            ))}
                          </select>
                        </td>
                        {[
                          ["edgeTop", "Gora"],
                          ["edgeBottom", "Dol"],
                          ["edgeLeft", "Lewa"],
                          ["edgeRight", "Prawa"],
                        ].map(([key, label]) => (
                          <td key={key} className="px-2 py-1.5 text-center">
                            {(valuationMethod === "service-cut-edge" || valuationMethod === "service-veneer") ? (
                              <label className="inline-flex items-center gap-1.5 text-slate-200">
                                <input
                                  type="checkbox"
                                  checked={Boolean(serviceEstimator[key as keyof ServiceEstimatorDraft])}
                                  onChange={(e) =>
                                    setServiceEstimator((prev) => ({
                                      ...prev,
                                      [key]: e.target.checked,
                                    }))
                                  }
                                  className="accent-emerald-500"
                                  aria-label={label}
                                />
                              </label>
                            ) : (
                              <span className="text-slate-500">-</span>
                            )}
                          </td>
                        ))}
                        <td className="px-2 py-1.5 text-slate-300">
                          {(valuationMethod === "service-cut-edge" || valuationMethod === "service-veneer")
                            ? (selectedEdgeMaterial ? selectedEdgeMaterial.name : "nie wybrano")
                            : "-"}
                        </td>
                        <td className="px-2 py-1.5 text-slate-300">
                          {materialsDbLoading
                            ? "Ladowanie bazy materialow..."
                            : selectedServiceMaterial
                            ? `Material: ${selectedServiceMaterial.name}`
                            : "Material nie wybrany"}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                  {valuationMethod === "service-front-cnc-lacquer" && (
                    <div className="mt-2 grid grid-cols-1 gap-2 md:grid-cols-4">
                      <select
                        className={baseInput}
                        value={serviceEstimator.cncPattern}
                        onChange={(e) =>
                          setServiceEstimator((prev) => ({
                            ...prev,
                            cncPattern: e.target.value as ServiceEstimatorDraft["cncPattern"],
                          }))
                        }
                      >
                        <option value="line">Frez liniowy</option>
                        <option value="classic">Frez klasyczny</option>
                        <option value="premium">Frez premium</option>
                        <option value="custom">Frez custom</option>
                      </select>
                      <label className="flex items-center gap-2 rounded border border-[#333] bg-[#10151f] px-3 py-2 text-[11px]">
                        <input
                          type="checkbox"
                          checked={serviceEstimator.lacquer}
                          onChange={(e) =>
                            setServiceEstimator((prev) => ({ ...prev, lacquer: e.target.checked }))
                          }
                          className="accent-emerald-500"
                        />
                        Lakierowanie
                      </label>
                      <select
                        className={baseInput}
                        value={serviceEstimator.lacquerSides}
                        onChange={(e) =>
                          setServiceEstimator((prev) => ({
                            ...prev,
                            lacquerSides: Number(e.target.value) === 2 ? 2 : 1,
                          }))
                        }
                        disabled={!serviceEstimator.lacquer}
                      >
                        <option value={1}>1 strona</option>
                        <option value={2}>2 strony</option>
                      </select>
                    </div>
                  )}

                  {valuationMethod === "service-veneer" && (
                    <div className="mt-2 grid grid-cols-1 gap-2 md:grid-cols-3">
                      <select
                        className={baseInput}
                        value={serviceEstimator.veneerSides}
                        onChange={(e) =>
                          setServiceEstimator((prev) => ({
                            ...prev,
                            veneerSides: Number(e.target.value) === 2 ? 2 : 1,
                          }))
                        }
                      >
                        <option value={1}>Fornir 1 strona</option>
                        <option value={2}>Fornir 2 strony</option>
                      </select>
                      <label className="flex items-center gap-2 rounded border border-[#333] bg-[#10151f] px-3 py-2 text-[11px]">
                        <input
                          type="checkbox"
                          checked={serviceEstimator.veneerLacquer}
                          onChange={(e) =>
                            setServiceEstimator((prev) => ({ ...prev, veneerLacquer: e.target.checked }))
                          }
                          className="accent-emerald-500"
                        />
                        Lakier po fornirze
                      </label>
                    </div>
                  )}

                  {valuationMethod === "service-bent-elements" && (
                    <div className="mt-2 grid grid-cols-1 gap-2 md:grid-cols-4">
                      <select
                        className={baseInput}
                        value={serviceEstimator.bentShape}
                        onChange={(e) =>
                          setServiceEstimator((prev) => ({
                            ...prev,
                            bentShape: e.target.value as ServiceEstimatorDraft["bentShape"],
                          }))
                        }
                      >
                        <option value="arc">Luk</option>
                        <option value="wave">Fala</option>
                        <option value="custom">Ksztalt custom</option>
                      </select>
                      <input
                        type="number"
                        className={baseInput}
                        placeholder="Promien mm"
                        value={serviceEstimator.bentRadiusMm}
                        onChange={(e) =>
                          setServiceEstimator((prev) => ({
                            ...prev,
                            bentRadiusMm: Math.max(0, Number(e.target.value) || 0),
                          }))
                        }
                      />
                      <select
                        className={baseInput}
                        value={serviceEstimator.bentComplexity}
                        onChange={(e) =>
                          setServiceEstimator((prev) => ({
                            ...prev,
                            bentComplexity: (Number(e.target.value) || 1) as ServiceEstimatorDraft["bentComplexity"],
                          }))
                        }
                      >
                        <option value={1}>Prosty</option>
                        <option value={2}>Sredni</option>
                        <option value={3}>Trudny</option>
                      </select>
                    </div>
                  )}

                  <div className="mt-3 rounded border border-blue-500/25 bg-blue-500/5 p-3 text-[11px]">
                    <div className="font-black uppercase tracking-widest text-blue-200">Podglad kalkulacji</div>
                    {servicePricingLoading ? (
                      <div className="mt-2 flex items-center gap-2 text-slate-300">
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        Liczenie backend pricing...
                      </div>
                    ) : servicePricingPreview ? (
                      <>
                        <div className="mt-2 flex flex-wrap items-center gap-2">
                          <span
                            className={clsx(
                              "rounded-full border px-2 py-0.5 text-[10px] font-black uppercase tracking-wider",
                              servicePricingPreview.pricing_status === "ready"
                                ? "border-emerald-400/40 bg-emerald-500/15 text-emerald-300"
                                : "border-amber-400/40 bg-amber-500/15 text-amber-300"
                            )}
                          >
                            {servicePricingPreview.pricing_status === "ready" ? "ready" : "manual_review"}
                          </span>
                          <span className="text-slate-400">
                            schema: {servicePricingPreview.schema_version}
                            {servicePricingPreview.tariff_schema_version
                              ? ` | taryfa: ${servicePricingPreview.tariff_schema_version}`
                              : ""}
                          </span>
                        </div>
                        <div className="mt-2 grid grid-cols-1 gap-1 text-slate-200 md:grid-cols-2 xl:grid-cols-5">
                          <div>material: {servicePricingPreview.buckets.material_cost.toFixed(2)} zl</div>
                          <div>cnc: {servicePricingPreview.buckets.cnc_service_cost.toFixed(2)} zl</div>
                          <div>finishing: {servicePricingPreview.buckets.finishing_cost.toFixed(2)} zl</div>
                          <div>extra: {servicePricingPreview.buckets.extra_cost.toFixed(2)} zl</div>
                          <div className="font-black text-emerald-300">
                            netto: {servicePricingPreview.buckets.net_total.toFixed(2)} zl
                          </div>
                        </div>
                        <div className="mt-2 text-slate-300">{servicePricingPreview.summary_text}</div>
                        {servicePricingPreview.validation_flags.length > 0 && (
                          <div className="mt-2 rounded border border-amber-500/30 bg-amber-500/10 px-2 py-1.5 text-[10px] text-amber-200">
                            Flagi walidacji:{" "}
                            {servicePricingPreview.validation_flags
                              .map((flag) => `${flag.code}: ${flag.message}`)
                              .join(" | ")}
                          </div>
                        )}
                        {servicePricingPreview.manual_review_reasons.length > 0 && (
                          <div className="mt-1 text-[10px] text-rose-300">
                            Powody manual review: {servicePricingPreview.manual_review_reasons.join(", ")}
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="mt-2 text-slate-400">
                        Brak podgladu. Uzupelnij pola uslugi lub kliknij Dodaj pozycje (backend wykona kalkulacje).
                      </div>
                    )}
                  </div>
                </Card>
              )}

              {!isServicesMode ? (
              <Card className="border-[#333] bg-[#1e1e1e] p-4">
                <div className="mb-2 text-lg font-bold">
                  {editingPositionId ? "Edycja pozycji" : "Nowa pozycja"}
                </div>
                <div className="mb-3 text-[11px] text-slate-400">
                  {editingPositionId
                    ? "Zmien dane pozycji i zapisz."
                    : "Wprowadz dane dla nowego tematu handlowego."}
                </div>
                <div className="grid grid-cols-1 gap-2 lg:grid-cols-[1fr_90px_110px_90px_150px_180px]">
                  <input
                    className={baseInput}
                    placeholder="Nazwa, np. Kuchnia"
                    value={positionDraft.name}
                    onChange={(e) =>
                      setPositionDraft((prev) => ({ ...prev, name: e.target.value }))
                    }
                  />
                  <input
                    type="number"
                    className={baseInput}
                    value={positionDraft.quantity}
                    onChange={(e) =>
                      setPositionDraft((prev) => ({
                        ...prev,
                        quantity: Number(e.target.value) || 1,
                      }))
                    }
                  />
                  <input
                    type="number"
                    className={baseInput}
                    value={positionDraft.vat}
                    onChange={(e) =>
                      setPositionDraft((prev) => {
                        const parsed = Number(e.target.value);
                        return { ...prev, vat: Number.isFinite(parsed) ? parsed : 0 };
                      })
                    }
                  />
                  <input className={baseInput} value={`${positionDraft.vat}%`} readOnly />
                  <input
                    className={baseInput}
                    value={positionDraft.type}
                    onChange={(e) =>
                      setPositionDraft((prev) => ({ ...prev, type: e.target.value }))
                    }
                  />
                  <select
                    className={baseInput}
                    value={positionDraft.purchaseType}
                    onChange={(e) =>
                      setPositionDraft((prev) => {
                        const nextType = e.target.value as "invoice" | "cash" | "receipt" | "none";
                        const shouldDefaultToZeroVat = nextType === "cash" && prev.vat === 23;
                        return {
                          ...prev,
                          purchaseType: nextType,
                          vat: shouldDefaultToZeroVat ? 0 : prev.vat,
                        };
                      })
                    }
                  >
                    {POSITION_PURCHASE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="mt-2 text-[10px] text-slate-400">
                  Dla opcji <span className="font-black text-slate-200">Gotowka</span> VAT domyslnie
                  ustawia sie na <span className="font-black text-slate-200">0%</span>, ale mozesz
                  wpisac VAT recznie.
                </div>
                <div className="mt-2 grid grid-cols-1 gap-2 lg:grid-cols-[1fr_260px_180px_140px]">
                  <input
                    className={baseInput}
                    placeholder="Opis / uwagi do wyceny"
                    value={positionDraft.description}
                    onChange={(e) =>
                      setPositionDraft((prev) => ({
                        ...prev,
                        description: e.target.value,
                      }))
                    }
                  />
                  <input
                    className={baseInput}
                    placeholder="Kolor / tekstura (opcjonalnie)"
                    value={positionDraft.textureOrColor}
                    onChange={(e) =>
                      setPositionDraft((prev) => ({
                        ...prev,
                        textureOrColor: e.target.value,
                      }))
                    }
                  />
                  <Button
                    className="h-10"
                    onClick={() => {
                      void addPosition();
                    }}
                  >
                    {editingPositionId ? "Zapisz zmiany" : "+ Dodaj pozycje"}
                  </Button>
                  <Button
                    className="h-10"
                    variant="secondary"
                    onClick={cancelEditPosition}
                    disabled={!editingPositionId}
                  >
                    Anuluj
                  </Button>
                </div>
              </Card>
              ) : null}

              <Card className="border-[#333] bg-[#1e1e1e] p-4">
                <div className="mb-2 text-lg font-bold">Lista pozycji</div>
                {isServicesMode ? (
                  <div className="space-y-3">
                    <div className="flex flex-wrap items-center gap-2 text-[11px]">
                      <Button
                        className="h-8"
                        variant="secondary"
                        disabled={!activePositionId}
                        onClick={() => activePositionId && startEditPosition(activePositionId)}
                      >
                        Edytuj aktywny wiersz
                      </Button>
                      <Button
                        className="h-8"
                        variant="secondary"
                        disabled={!activePositionId}
                        onClick={() => {
                          if (!activePositionId) return;
                          setSpecTargetId(activePositionId);
                          void goToStep(3);
                        }}
                      >
                        Specyfikacja aktywnego
                      </Button>
                      <Button
                        className="h-8"
                        variant="secondary"
                        disabled={!activePositionId}
                        onClick={() => {
                          if (!activePositionId) return;
                          setMaterialDraft((prev) => ({ ...prev, positionId: activePositionId }));
                          void goToStep(5);
                        }}
                      >
                        Materialy aktywnego
                      </Button>
                      <Button
                        className="h-8"
                        variant="secondary"
                        disabled={!activePositionId}
                        onClick={() => activePositionId && removePosition(activePositionId)}
                      >
                        Usun aktywny wiersz
                      </Button>
                    </div>

                    {serviceMaterialTables.groups.length === 0 ? (
                      <div className="rounded border border-[#33445f] px-3 py-8 text-center text-slate-500">
                        Brak pozycji
                      </div>
                    ) : (
                      serviceMaterialTables.groups.map((group) => (
                        <div key={group.key} className="overflow-hidden rounded border border-[#33445f]">
                          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#33445f] bg-[#1a2233] px-3 py-2 text-[11px]">
                            <div>
                              <span className="font-black uppercase tracking-wider text-blue-200">Material: </span>
                              <span className="font-semibold text-slate-100">{group.materialName}</span>
                            </div>
                            <div className="text-slate-300">m2: {group.totalM2.toFixed(3)}</div>
                          </div>
                          <table className="w-full border-collapse">
                            <thead className="bg-[#bcc8da] text-[#0b1c39]">
                              <tr>
                                <th className="px-2 py-2 text-left">Nr</th>
                                <th className="px-2 py-2 text-left">Pozycja</th>
                                <th className="px-2 py-2 text-left">Material</th>
                                <th className="px-2 py-2 text-left">Dl</th>
                                <th className="px-2 py-2 text-left">Sz</th>
                                <th className="px-2 py-2 text-left">Gr</th>
                                <th className="px-2 py-2 text-left">Ilosc</th>
                                <th className="px-2 py-2 text-left">Tekstura/Kolor</th>
                                <th className="px-2 py-2 text-left">Nazwa</th>
                                <th className="px-2 py-2 text-center">OG</th>
                                <th className="px-2 py-2 text-center">OD</th>
                                <th className="px-2 py-2 text-center">OL</th>
                                <th className="px-2 py-2 text-center">OP</th>
                                <th className="px-2 py-2 text-left">Okleina</th>
                                <th className="px-2 py-2 text-left">Kod</th>
                                <th className="px-2 py-2 text-left">Opis</th>
                              </tr>
                            </thead>
                            <tbody>
                              {group.rows.map((item, idx) => {
                                const input = getRowPricingInput(item);
                                const edgeMode = String(input.edge_mode ?? "default");
                                const edgeRaw =
                                  edgeMode === "default"
                                    ? String(input.edge_default_material_id ?? "").trim()
                                    : "Wiele stron";
                                const edgeName =
                                  edgeRaw && edgeRaw !== "Wiele stron"
                                    ? materialsDb.find((m) => String(m.id) === edgeRaw)?.name || edgeRaw
                                    : edgeRaw;
                                return (
                                  <tr
                                    key={item.id}
                                    className={clsx(
                                      "cursor-pointer border-t border-white/5",
                                      activePositionId === item.id ? "bg-blue-600/10" : "hover:bg-white/[0.03]"
                                    )}
                                    onClick={() => setActivePositionId(item.id)}
                                  >
                                    <td className="px-2 py-2">{idx + 1}</td>
                                    <td className="px-2 py-2">{item.id}</td>
                                    <td className="px-2 py-2">{getRowStringField(item, "base_material_name", "-")}</td>
                                    <td className="px-2 py-2">{getRowNumberField(item, "length_mm", 0)}</td>
                                    <td className="px-2 py-2">{getRowNumberField(item, "width_mm", 0)}</td>
                                    <td className="px-2 py-2">{getRowNumberField(item, "base_thickness_mm", 0)}</td>
                                    <td className="px-2 py-2">{item.quantity}</td>
                                    <td className="px-2 py-2">{item.textureOrColor || "-"}</td>
                                    <td className="px-2 py-2 font-semibold">{item.name}</td>
                                    <td className="px-2 py-2 text-center">{Boolean(input.edge_top) ? "✓" : ""}</td>
                                    <td className="px-2 py-2 text-center">{Boolean(input.edge_bottom) ? "✓" : ""}</td>
                                    <td className="px-2 py-2 text-center">{Boolean(input.edge_left) ? "✓" : ""}</td>
                                    <td className="px-2 py-2 text-center">{Boolean(input.edge_right) ? "✓" : ""}</td>
                                    <td className="px-2 py-2">{edgeName || "-"}</td>
                                    <td className="px-2 py-2">{String(input.part_code ?? input.code ?? "-")}</td>
                                    <td className="px-2 py-2">{item.description || "-"}</td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                          <div className="border-t border-[#33445f] bg-[#101925] px-3 py-2 text-[11px] text-slate-300">
                            <span className="font-black uppercase tracking-wider text-blue-200">Okleiny: </span>
                            {Object.keys(group.edgeByMaterial).length === 0
                              ? "brak"
                              : Object.entries(group.edgeByMaterial)
                                  .map(([name, mb]) => `${name}: ${mb.toFixed(2)} mb`)
                                  .join(" | ")}
                          </div>
                        </div>
                      ))
                    )}

                    <div className="rounded border border-blue-500/25 bg-blue-500/5 p-3 text-[11px]">
                      <div className="font-black uppercase tracking-widest text-blue-200">Podsumowanie operacji</div>
                      <div className="mt-2 grid grid-cols-1 gap-2 md:grid-cols-3">
                        <div className="rounded border border-[#33445f] bg-[#101925] px-3 py-2">
                          Suma m2: <span className="font-black">{serviceMaterialTables.global.totalM2.toFixed(3)}</span>
                        </div>
                        <div className="rounded border border-[#33445f] bg-[#101925] px-3 py-2">
                          Cena koncowa netto:{" "}
                          <span className="font-black">{serviceMaterialTables.global.totalNet.toFixed(2)} zl</span>
                        </div>
                        <div className="rounded border border-[#33445f] bg-[#101925] px-3 py-2">
                          Oklejanie razem:{" "}
                          <span className="font-black">
                            {Object.values(serviceMaterialTables.global.edgeByMaterial)
                              .reduce((sum, value) => sum + value, 0)
                              .toFixed(2)}{" "}
                            mb
                          </span>
                        </div>
                      </div>
                      <div className="mt-2 text-slate-300">
                        <span className="font-black uppercase tracking-wider text-blue-200">Rozbicie oklein: </span>
                        {Object.keys(serviceMaterialTables.global.edgeByMaterial).length === 0
                          ? "brak"
                          : Object.entries(serviceMaterialTables.global.edgeByMaterial)
                              .map(([name, mb]) => `${name}: ${mb.toFixed(2)} mb`)
                              .join(" | ")}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="overflow-hidden rounded border border-[#33445f]">
                    <table className="w-full border-collapse">
                      <thead className="bg-[#bcc8da] text-[#0b1c39]">
                        <tr>
                          <th className="px-2 py-2 text-left">Nr</th>
                          <th className="px-2 py-2 text-left">Nazwa</th>
                          <th className="px-2 py-2 text-left">Material</th>
                          <th className="px-2 py-2 text-left">Kolor/tekstura</th>
                          <th className="px-2 py-2 text-left">L</th>
                          <th className="px-2 py-2 text-left">W</th>
                          <th className="px-2 py-2 text-left">T</th>
                          <th className="px-2 py-2 text-left">Ilosc</th>
                          <th className="px-2 py-2 text-left">Krawedzie (G/D/L/P)</th>
                          <th className="px-2 py-2 text-left">Tryb</th>
                          <th className="px-2 py-2 text-left">Zrodlo</th>
                        </tr>
                      </thead>
                      <tbody>
                        {positions.length === 0 ? (
                          <tr>
                            <td colSpan={11} className="px-3 py-8 text-center text-slate-500">
                              Brak pozycji
                            </td>
                          </tr>
                        ) : (
                          positions.map((item, idx) => (
                            <tr
                              key={item.id}
                              className={clsx(
                                "cursor-pointer border-t border-white/5",
                                activePositionId === item.id ? "bg-blue-600/10" : "hover:bg-white/[0.03]"
                              )}
                              onClick={() => setActivePositionId(item.id)}
                            >
                              <td className="px-2 py-2">{idx + 1}</td>
                              <td className="px-2 py-2 font-semibold">{item.name}</td>
                              <td className="px-2 py-2">{getRowStringField(item, "base_material_name", "-")}</td>
                              <td className="px-2 py-2">{item.textureOrColor || "-"}</td>
                              <td className="px-2 py-2">{getRowNumberField(item, "length_mm", 0)}</td>
                              <td className="px-2 py-2">{getRowNumberField(item, "width_mm", 0)}</td>
                              <td className="px-2 py-2">{getRowNumberField(item, "base_thickness_mm", 0)}</td>
                              <td className="px-2 py-2">{item.quantity}</td>
                              <td className="px-2 py-2 text-[11px]">
                                {Boolean(getRowPricingInput(item).edge_top) ? "1" : "0"}/
                                {Boolean(getRowPricingInput(item).edge_bottom) ? "1" : "0"}/
                                {Boolean(getRowPricingInput(item).edge_left) ? "1" : "0"}/
                                {Boolean(getRowPricingInput(item).edge_right) ? "1" : "0"}
                              </td>
                              <td className="px-2 py-2 text-[11px] text-slate-300">
                                {item.serviceMode && serviceModeKeys.has(item.serviceMode)
                                  ? SERVICE_MODE_LABEL[
                                      item.serviceMode as
                                        | "service-cut"
                                        | "service-cut-edge"
                                        | "service-front-cnc-lacquer"
                                        | "service-veneer"
                                        | "service-bent-elements"
                                    ]
                                  : "-"}
                              </td>
                              <td className="px-2 py-2 text-[11px] uppercase text-slate-400">
                                {item.sourceType || "manual"}
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                )}
              </Card>
            </div>
          ) : null}

          {step === 4 ? (
            <div className="space-y-4">
              <Card className="border-[#333] bg-[#1e1e1e] p-4">
                <div className="mb-3 text-lg font-bold">Zalaczniki</div>
                <div className="mb-3 text-[11px] text-slate-400">
                  PDF-y, zrzuty i referencje od architekta lub pomiarow z ImageMeter Pro.
                </div>

                <div className="grid grid-cols-1 gap-2 lg:grid-cols-[1fr_180px_180px]">
                  <input
                    className={baseInput}
                    placeholder="Sciezka do PDF albo obrazu"
                    readOnly
                    value={selectedAttachment?.name || ""}
                  />
                  <Button className="h-10" onClick={() => fileInputRef.current?.click()}>
                    <Upload className="h-4 w-4" /> Wybierz plik
                  </Button>
                  <Button className="h-10" variant="secondary">
                    Import z ImageMeter
                  </Button>
                </div>

                <div className="mt-2 grid grid-cols-1 gap-2 lg:grid-cols-[90px_1fr]">
                  <select
                    className={baseInput}
                    value={attachmentDraft.type}
                    onChange={(e) =>
                      setAttachmentDraft((prev) => ({
                        ...prev,
                        type: e.target.value as "PDF" | "IMG",
                      }))
                    }
                  >
                    <option value="PDF">PDF</option>
                    <option value="IMG">IMG</option>
                  </select>
                  <input
                    className={baseInput}
                    placeholder="Opis zalacznika"
                    value={attachmentDraft.description}
                    onChange={(e) =>
                      setAttachmentDraft((prev) => ({
                        ...prev,
                        description: e.target.value,
                      }))
                    }
                  />
                </div>

                <input
                  ref={fileInputRef}
                  type="file"
                  className="hidden"
                  accept=".pdf,image/*"
                  onChange={onPickAttachment}
                />

                <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-[280px_1fr]">
                  <div className="rounded border border-[#33445f]">
                    <table className="w-full border-collapse">
                      <thead className="bg-[#bcc8da] text-[#0b1c39]">
                        <tr>
                          <th className="px-2 py-2 text-left">Plik</th>
                          <th className="px-2 py-2 text-left">Typ</th>
                          <th className="px-2 py-2 text-left">Opis</th>
                        </tr>
                      </thead>
                      <tbody>
                        {attachments.length === 0 ? (
                          <tr>
                            <td colSpan={3} className="px-2 py-8 text-center text-slate-500">
                              Brak zalacznikow
                            </td>
                          </tr>
                        ) : (
                          attachments.map((item) => (
                            <tr
                              key={item.id}
                              className={clsx(
                                "cursor-pointer border-t border-white/5",
                                selectedAttachmentId === item.id
                                  ? "bg-blue-600/10"
                                  : "hover:bg-white/[0.03]"
                              )}
                              onClick={() => setSelectedAttachmentId(item.id)}
                            >
                              <td className="px-2 py-2">{item.name}</td>
                              <td className="px-2 py-2">{item.type}</td>
                              <td className="px-2 py-2 text-slate-400">
                                {item.description || "-"}
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>

                  <div className="rounded border border-[#33445f] p-3">
                    <div className="mb-2 text-[12px] font-bold">Podglad i wycinanie</div>
                    {selectedAttachment ? (
                      <div className="space-y-2">
                        <div className="rounded border border-[#2f3a4d] bg-[#131a27] p-3 text-sm">
                          Wybrano: {selectedAttachment.name}
                        </div>
                        <div className="h-64 rounded border border-dashed border-[#2f3a4d] bg-[#111827] p-4 text-center text-slate-500">
                          Podglad pliku i wycinki zostana podlaczone tutaj.
                        </div>
                      </div>
                    ) : (
                      <div className="h-72 rounded border border-dashed border-[#2f3a4d] bg-[#111827] p-4 text-center text-slate-500">
                        Wybierz zalacznik, aby zobaczyc podglad.
                      </div>
                    )}
                  </div>
                </div>
              </Card>
            </div>
          ) : null}

          {step === 5 ? (
            <div className="space-y-4">
              <Card className="border-[#333] bg-[#1e1e1e] p-4">
                <div className="mb-2 text-lg font-bold">Nowy wybor klienta</div>
                {positions.length === 0 ? (
                  <div className="mb-3 rounded border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-[11px] text-amber-200">
                    Brak pozycji. Najpierw dodaj pozycje w kroku 2, zeby przypisac material do
                    konkretnej szafki/sekcji.
                  </div>
                ) : null}
                {positions.length > 0 ? (
                  <div className="mb-3 rounded border border-[#2b3952] bg-[#121b2b] px-3 py-2">
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <div className="text-[11px] text-slate-300">
                        Aktywna pozycja:{" "}
                        <span className="font-black text-white">
                          {activePosition ? activePosition.name : "Brak"}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          className={clsx(
                            "rounded px-2 py-1 text-[10px] font-black uppercase tracking-widest",
                            materialsView === "active"
                              ? "bg-blue-600 text-white"
                              : "bg-[#1d2636] text-slate-300"
                          )}
                          onClick={() => setMaterialsView("active")}
                        >
                          Tylko aktywna pozycja
                        </button>
                        <button
                          className={clsx(
                            "rounded px-2 py-1 text-[10px] font-black uppercase tracking-widest",
                            materialsView === "all"
                              ? "bg-blue-600 text-white"
                              : "bg-[#1d2636] text-slate-300"
                          )}
                          onClick={() => setMaterialsView("all")}
                        >
                          Wszystkie pozycje
                        </button>
                        <button
                          className={clsx(
                            "rounded px-2 py-1 text-[10px] font-black uppercase tracking-widest",
                            materialsView === "summary"
                              ? "bg-blue-600 text-white"
                              : "bg-[#1d2636] text-slate-300"
                          )}
                          onClick={() => setMaterialsView("summary")}
                        >
                          Podsumowanie zamowienia
                        </button>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {positions.map((p, idx) => (
                        <button
                          key={p.id}
                          className={clsx(
                            "rounded-md px-3 py-1.5 text-[10px] font-black uppercase tracking-widest",
                            activePositionId === p.id
                              ? "bg-blue-600 text-white"
                              : "bg-[#1d2636] text-slate-300"
                          )}
                          onClick={() => {
                            setActivePositionId(p.id);
                            setMaterialDraft((prev) => ({ ...prev, positionId: p.id }));
                          }}
                        >
                          {idx + 1}. {p.name}
                        </button>
                      ))}
                    </div>
                  </div>
                ) : null}

                <div className="mb-3 rounded border border-[#2b3952] bg-[#121b2b] p-3">
                  <div className="mb-2 text-[10px] font-black uppercase tracking-widest text-slate-400">
                    Material z bazy
                  </div>
                  <div className="grid grid-cols-1 gap-2 md:grid-cols-[150px_1fr_220px_160px]">
                    <select
                      className={baseInput}
                      value={materialDbCategory}
                      onChange={(e) =>
                        setMaterialDbCategory(
                          e.target.value as "all" | "boards" | "hardware" | "finishes"
                        )
                      }
                    >
                      <option value="all">Wszystkie</option>
                      <option value="boards">Plyty</option>
                      <option value="finishes">Wykonczenia / okleina</option>
                      <option value="hardware">Okucia / uchwyty</option>
                    </select>
                    <input
                      className={baseInput}
                      placeholder="Filtruj baze: nazwa / kod / dostawca"
                      value={materialDbQuery}
                      onChange={(e) => setMaterialDbQuery(e.target.value)}
                    />
                    <select
                      className={baseInput}
                      value={materialDbSelectedId}
                      onChange={(e) => setMaterialDbSelectedId(e.target.value)}
                      disabled={materialsDbLoading}
                    >
                      <option value="">
                        {materialsDbLoading
                          ? "Ladowanie bazy..."
                          : `Wybierz material (${filteredDbMaterials.length})`}
                      </option>
                      {filteredDbMaterials.slice(0, 500).map((m) => (
                        <option key={m.id} value={String(m.id)}>
                          {m.name} {m.material_code ? `| ${m.material_code}` : ""}
                        </option>
                      ))}
                    </select>
                    <Button
                      className="h-10"
                      variant="secondary"
                      onClick={applyMaterialFromDatabase}
                      disabled={!materialDbSelectedId}
                    >
                      Wstaw z bazy
                    </Button>
                  </div>
                </div>

                <div className="mb-3 grid grid-cols-1 gap-2 md:grid-cols-2 lg:grid-cols-4">
                  <select
                    className={baseInput}
                    value={materialDraft.positionId}
                    onChange={(e) => {
                      const nextId = e.target.value;
                      setActivePositionId(nextId);
                      setMaterialDraft((prev) => ({ ...prev, positionId: nextId }));
                    }}
                  >
                    {positions.map((p, idx) => (
                      <option key={p.id} value={p.id}>
                        {idx + 1}. {p.name}
                      </option>
                    ))}
                  </select>
                  <select
                    className={baseInput}
                    value={materialDraft.scope}
                    onChange={(e) =>
                      setMaterialDraft((prev) => ({ ...prev, scope: e.target.value }))
                    }
                  >
                    <option>Korpus</option>
                    <option>Front</option>
                    <option>Okleina</option>
                    <option>Blat</option>
                    <option>Farba</option>
                    <option>Uchwyt</option>
                    <option>Inne</option>
                  </select>
                  <select
                    className={baseInput}
                    value={materialDraft.status}
                    onChange={(e) =>
                      setMaterialDraft((prev) => ({
                        ...prev,
                        status: e.target.value as "Proba" | "Final",
                      }))
                    }
                  >
                    <option value="Proba">Proba pokazana</option>
                    <option value="Final">Finalny wybor</option>
                  </select>
                  <input
                    className={baseInput}
                    placeholder="Material / producent"
                    value={materialDraft.material}
                    onChange={(e) =>
                      setMaterialDraft((prev) => ({
                        ...prev,
                        material: e.target.value,
                      }))
                    }
                  />
                  <input
                    className={baseInput}
                    placeholder="Kolor / dekor"
                    value={materialDraft.color}
                    onChange={(e) =>
                      setMaterialDraft((prev) => ({ ...prev, color: e.target.value }))
                    }
                  />
                </div>

                <div className="mb-3 grid grid-cols-1 gap-2 md:grid-cols-3 lg:grid-cols-4">
                  <input
                    className={baseInput}
                    placeholder="Kod"
                    value={materialDraft.code}
                    onChange={(e) =>
                      setMaterialDraft((prev) => ({ ...prev, code: e.target.value }))
                    }
                  />
                  <input
                    type="date"
                    className={baseInput}
                    value={materialDraft.date}
                    onChange={(e) =>
                      setMaterialDraft((prev) => ({ ...prev, date: e.target.value }))
                    }
                  />
                  <input
                    className={clsx(baseInput, "md:col-span-2 lg:col-span-2")}
                    placeholder="Uwagi"
                    value={materialDraft.notes}
                    onChange={(e) =>
                      setMaterialDraft((prev) => ({ ...prev, notes: e.target.value }))
                    }
                  />
                </div>

                <div className="flex items-center gap-2">
                  <Button className="h-10" onClick={addMaterialChoice} disabled={positions.length === 0}>
                    Dodaj wpis
                  </Button>
                  <Button
                    className="h-10"
                    variant="secondary"
                    onClick={removeSelectedMaterial}
                    disabled={!selectedMaterialId}
                  >
                    Usun zaznaczony
                  </Button>
                </div>
              </Card>

              <Card className="border-[#333] bg-[#1e1e1e] p-4">
                <div className="mb-2 text-lg font-bold">Historia probek i finalnych wyborow</div>
                <div className="overflow-hidden rounded border border-[#33445f]">
                  <table className="w-full border-collapse">
                    <thead className="bg-[#bcc8da] text-[#0b1c39]">
                      <tr>
                        <th className="px-2 py-2 text-left">Pozycja</th>
                        <th className="px-2 py-2 text-left">Zakres</th>
                        <th className="px-2 py-2 text-left">Material</th>
                        <th className="px-2 py-2 text-left">Kolor</th>
                        <th className="px-2 py-2 text-left">Kod</th>
                        {materialsView === "summary" ? (
                          <th className="px-2 py-2 text-left">Liczba wpisow</th>
                        ) : null}
                        <th className="px-2 py-2 text-left">Status</th>
                        <th className="px-2 py-2 text-left">Data</th>
                        <th className="px-2 py-2 text-left">Uwagi</th>
                      </tr>
                    </thead>
                    <tbody>
                      {materialsView === "summary" ? (
                        materialSummaryRows.length === 0 ? (
                          <tr>
                            <td colSpan={9} className="px-2 py-8 text-center text-slate-500">
                              Brak wpisow
                            </td>
                          </tr>
                        ) : (
                          materialSummaryRows.map((item, index) => (
                            <tr key={`${item.positionName}-${item.scope}-${item.material}-${index}`} className="border-t border-white/5">
                              <td className="px-2 py-2">{item.positionName}</td>
                              <td className="px-2 py-2">{item.scope}</td>
                              <td className="px-2 py-2 font-semibold">{item.material}</td>
                              <td className="px-2 py-2">{item.color || "-"}</td>
                              <td className="px-2 py-2">{item.code || "-"}</td>
                              <td className="px-2 py-2">{item.count}</td>
                              <td className="px-2 py-2">{item.status}</td>
                              <td className="px-2 py-2">{item.date || "-"}</td>
                              <td className="px-2 py-2 text-slate-400">{item.notes || "-"}</td>
                            </tr>
                          ))
                        )
                      ) : visibleMaterialChoices.length === 0 ? (
                        <tr>
                          <td colSpan={8} className="px-2 py-8 text-center text-slate-500">
                            Brak wpisow
                          </td>
                        </tr>
                      ) : (
                        visibleMaterialChoices.map((item) => (
                          <tr
                            key={item.id}
                            onClick={() => {
                              setSelectedMaterialId(item.id);
                              setActivePositionId(item.positionId);
                            }}
                            className={clsx(
                              "cursor-pointer border-t border-white/5",
                              selectedMaterialId === item.id
                                ? "bg-blue-600/10"
                                : "hover:bg-white/[0.03]"
                            )}
                          >
                            <td className="px-2 py-2">{item.positionName}</td>
                            <td className="px-2 py-2">{item.scope}</td>
                            <td className="px-2 py-2 font-semibold">{item.material}</td>
                            <td className="px-2 py-2">{item.color || "-"}</td>
                            <td className="px-2 py-2">{item.code || "-"}</td>
                            <td className="px-2 py-2">{item.status}</td>
                            <td className="px-2 py-2">{item.date}</td>
                            <td className="px-2 py-2 text-slate-400">{item.notes || "-"}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>
          ) : null}

          {step === 6 ? (
            <div className="space-y-4">
              <Card className="border-[#333] bg-[#1e1e1e] p-4">
                <div className="mb-2 text-lg font-bold">Uslugi dla klienta</div>
                <div className="mb-2 rounded border border-blue-500/20 bg-blue-500/5 px-3 py-2 text-[11px] text-blue-200">
                  Klient przypisany do uslug:{" "}
                  <span className="font-black">{clientDisplayName || "-"}</span>
                </div>
                <div className="mb-3 text-slate-400">
                  Zaznacz uslugi wykonywane przy zamowieniu i dopisz ilosc, cene oraz uwagi.
                </div>
                <div className="overflow-hidden rounded border border-[#33445f]">
                  <table className="w-full border-collapse">
                    <thead className="bg-[#bcc8da] text-[#0b1c39]">
                      <tr>
                        <th className="px-2 py-2 text-left">Aktywna</th>
                        <th className="px-2 py-2 text-left">Usluga</th>
                        <th className="px-2 py-2 text-left">Ilosc</th>
                        <th className="px-2 py-2 text-left">Jedn.</th>
                        <th className="px-2 py-2 text-left">Cena jedn.</th>
                        <th className="px-2 py-2 text-left">Uwagi</th>
                        <th className="px-2 py-2 text-left">Wartosc</th>
                      </tr>
                    </thead>
                    <tbody>
                      {services.map((srv) => (
                        <tr key={srv.id} className="border-t border-white/5">
                          <td className="px-2 py-2">
                            <input
                              type="checkbox"
                              checked={srv.enabled}
                              onChange={(e) =>
                                setServices((prev) =>
                                  prev.map((item) =>
                                    item.id === srv.id ? { ...item, enabled: e.target.checked } : item
                                  )
                                )
                              }
                            />
                          </td>
                          <td className="px-2 py-2 font-semibold">{srv.name}</td>
                          <td className="px-2 py-2">
                            <input
                              type="number"
                              min={0}
                              step={1}
                              className={clsx(baseInput, "w-24")}
                              value={srv.qty}
                              onChange={(e) =>
                                setServices((prev) =>
                                  prev.map((item) =>
                                    item.id === srv.id
                                      ? { ...item, qty: Number(e.target.value) || 0 }
                                      : item
                                  )
                                )
                              }
                            />
                          </td>
                          <td className="px-2 py-2">
                            <select
                              className={clsx(baseInput, "w-24")}
                              value={srv.unit}
                              onChange={(e) =>
                                setServices((prev) =>
                                  prev.map((item) =>
                                    item.id === srv.id
                                      ? { ...item, unit: e.target.value as "szt" | "m2" | "mb" | "kpl" }
                                      : item
                                  )
                                )
                              }
                            >
                              <option value="szt">szt</option>
                              <option value="m2">m2</option>
                              <option value="mb">mb</option>
                              <option value="kpl">kpl</option>
                            </select>
                          </td>
                          <td className="px-2 py-2">
                            <input
                              type="number"
                              min={0}
                              step={0.01}
                              className={clsx(baseInput, "w-28")}
                              value={srv.unitPrice}
                              onChange={(e) =>
                                setServices((prev) =>
                                  prev.map((item) =>
                                    item.id === srv.id
                                      ? { ...item, unitPrice: Number(e.target.value) || 0 }
                                      : item
                                  )
                                )
                              }
                            />
                          </td>
                          <td className="px-2 py-2">
                            <input
                              className={clsx(baseInput, "w-full min-w-[180px]")}
                              value={srv.notes}
                              onChange={(e) =>
                                setServices((prev) =>
                                  prev.map((item) =>
                                    item.id === srv.id ? { ...item, notes: e.target.value } : item
                                  )
                                )
                              }
                              placeholder="Uwagi"
                            />
                          </td>
                          <td className="px-2 py-2 font-semibold">
                            {((Number(srv.qty) || 0) * (Number(srv.unitPrice) || 0)).toFixed(2)} zl
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>

              <Card className="border-[#333] bg-[#1e1e1e] p-4 text-sm leading-7">
                <div>Aktywne uslugi: {servicesActive.length}</div>
                <div>Wartosc uslug: {servicesTotal.toFixed(2)} zl</div>
              </Card>
            </div>
          ) : null}

          {step === 7 ? (
            <div className="space-y-4">
              <Card className="border-[#333] bg-[#1e1e1e] p-4">
                <div className="mb-2 text-lg font-bold">Nowa wplata klienta</div>
                <div className="mb-3 grid grid-cols-1 gap-2 lg:grid-cols-[1fr_140px_170px_180px_120px_140px]">
                  <input
                    className={baseInput}
                    value={paymentDraft.stage}
                    onChange={(e) =>
                      setPaymentDraft((prev) => ({ ...prev, stage: e.target.value }))
                    }
                    placeholder="Etap"
                  />
                  <input
                    type="number"
                    className={baseInput}
                    value={paymentDraft.amount}
                    onChange={(e) =>
                      setPaymentDraft((prev) => ({
                        ...prev,
                        amount: Number(e.target.value) || 0,
                      }))
                    }
                  />
                  <select
                    className={baseInput}
                    value={paymentDraft.method}
                    onChange={(e) =>
                      setPaymentDraft((prev) => ({
                        ...prev,
                        method: e.target.value as "invoice_vat" | "receipt" | "cash" | "no_document",
                      }))
                    }
                  >
                    {PAYMENT_METHOD_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                  <select
                    className={baseInput}
                    value={paymentDraft.cashbox}
                    onChange={(e) =>
                      setPaymentDraft((prev) => ({
                        ...prev,
                        cashbox: e.target.value as
                          | "kasa_faktura_vat"
                          | "kasa_paragon"
                          | "kasa_gotowka"
                          | "kasa_bez_dokumentu",
                      }))
                    }
                  >
                    {CASHBOX_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                  <label className="flex items-center gap-2 rounded-sm border border-[#333] bg-[#1e1e1e] px-2 py-1.5">
                    <input
                      type="checkbox"
                      checked={paymentDraft.paid}
                      onChange={(e) =>
                        setPaymentDraft((prev) => ({ ...prev, paid: e.target.checked }))
                      }
                    />
                    Oplacone
                  </label>
                  <input
                    type="date"
                    className={baseInput}
                    value={paymentDraft.date}
                    onChange={(e) =>
                      setPaymentDraft((prev) => ({ ...prev, date: e.target.value }))
                    }
                  />
                  <input
                    className={baseInput}
                    placeholder="ID platnosci"
                    value={paymentDraft.notes}
                    onChange={(e) =>
                      setPaymentDraft((prev) => ({ ...prev, notes: e.target.value }))
                    }
                  />
                </div>

                <div className="flex items-center gap-2">
                  <Button className="h-10" variant="secondary" onClick={addDefaultPayments}>
                    Wstaw etapy
                  </Button>
                  <Button className="h-10" onClick={addPayment}>
                    Dodaj / zapisz
                  </Button>
                  <Button
                    className="h-10"
                    variant="secondary"
                    onClick={togglePaymentStatus}
                    disabled={!selectedPaymentId}
                  >
                    Zmien status (oplacone/do zaplaty)
                  </Button>
                  <Button
                    className="h-10"
                    variant="secondary"
                    onClick={removeSelectedPayment}
                    disabled={!selectedPaymentId}
                  >
                    Usun zaznaczony
                  </Button>
                </div>
              </Card>

              <Card className="border-[#333] bg-[#1e1e1e] p-4">
                <div className="mb-2 text-lg font-bold">Historia wplat klienta</div>
                <div className="overflow-hidden rounded border border-[#33445f]">
                  <table className="w-full border-collapse">
                    <thead className="bg-[#bcc8da] text-[#0b1c39]">
                      <tr>
                        <th className="px-2 py-2 text-left">Etap</th>
                        <th className="px-2 py-2 text-left">Kwota</th>
                        <th className="px-2 py-2 text-left">Forma</th>
                        <th className="px-2 py-2 text-left">Kasa</th>
                        <th className="px-2 py-2 text-left">Status</th>
                        <th className="px-2 py-2 text-left">Data</th>
                        <th className="px-2 py-2 text-left">Uwagi</th>
                        <th className="px-2 py-2 text-right">Akcja</th>
                      </tr>
                    </thead>
                    <tbody>
                      {payments.length === 0 ? (
                        <tr>
                          <td colSpan={8} className="px-2 py-8 text-center text-slate-500">
                            Brak wplat
                          </td>
                        </tr>
                      ) : (
                        payments.map((item) => (
                          <tr
                            key={item.id}
                            onClick={() => setSelectedPaymentId(item.id)}
                            className={clsx(
                              "cursor-pointer border-t border-white/5",
                              selectedPaymentId === item.id
                                ? "bg-blue-600/10"
                                : "hover:bg-white/[0.03]"
                            )}
                          >
                            <td className="px-2 py-2">{item.stage}</td>
                            <td className="px-2 py-2">{item.amount.toFixed(2)} zl</td>
                            <td className="px-2 py-2">
                              {PAYMENT_METHOD_OPTIONS.find((opt) => opt.value === item.method)?.label || "-"}
                            </td>
                            <td className="px-2 py-2">
                              {CASHBOX_OPTIONS.find((opt) => opt.value === item.cashbox)?.label || "-"}
                            </td>
                            <td className="px-2 py-2">{item.paid ? "Oplacone" : "Do zaplaty"}</td>
                            <td className="px-2 py-2">{item.date}</td>
                            <td className="px-2 py-2 text-slate-400">{item.notes || "-"}</td>
                            <td className="px-2 py-2 text-right">
                              <Button
                                className="h-7"
                                variant="secondary"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setPayments((prev) =>
                                    prev.map((row) =>
                                      row.id === item.id ? { ...row, paid: !row.paid } : row
                                    )
                                  );
                                }}
                              >
                                {item.paid ? "Cofnij" : "Oplacono"}
                              </Button>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </Card>

              <Card className="border-[#333] bg-[#1e1e1e] p-4 text-sm leading-7">
                <div>Harmonogram wplat: {payments.length}</div>
                <div>Planowana kwota: {totalPlanned.toFixed(2)} zl</div>
                <div>Oplacone: {totalPaid.toFixed(2)} zl</div>
                <div>Pozostalo: {totalRemaining.toFixed(2)} zl</div>
                <div className="mt-3 border-t border-white/10 pt-3 text-[12px]">
                  <div className="mb-1 font-black uppercase tracking-wider text-slate-300">
                    Oplacone wg kas
                  </div>
                  {CASHBOX_OPTIONS.map((opt) => (
                    <div key={opt.value}>
                      {opt.label}: {(paidByCashbox[opt.value] || 0).toFixed(2)} zl
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          ) : null}

          {step === 8 ? (
            <div className="space-y-4">
              <Card className="border-[#333] bg-[#1e1e1e] p-4">
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <Button variant="secondary" className="h-10">
                    Dalej: Sciana
                  </Button>
                  <Button variant="secondary" className="h-10">
                    <Download className="h-4 w-4" /> Export oferty
                  </Button>
                  <Button variant="secondary" className="h-10">
                    <FileDown className="h-4 w-4" /> Export PDF
                  </Button>
                </div>

                <div className="mb-4 grid grid-cols-2 gap-2 md:grid-cols-4">
                  <div className="rounded border border-[#39465a] bg-[#202734] p-3">
                    <div className="text-slate-400">Material</div>
                    <div className="text-2xl font-black">
                      {unifiedSummary
                        ? unifiedSummary.pricing.material_value.toFixed(2)
                        : totalPlanned.toFixed(2)} zl
                    </div>
                  </div>
                  <div className="rounded border border-[#39465a] bg-[#202734] p-3">
                    <div className="text-slate-400">Uslugi</div>
                    <div className="text-2xl font-black">
                      {unifiedSummary
                        ? unifiedSummary.pricing.services_total.toFixed(2)
                        : servicesTotal.toFixed(2)} zl
                    </div>
                  </div>
                  <div className="rounded border border-[#39465a] bg-[#202734] p-3">
                    <div className="text-slate-400">Razem netto</div>
                    <div className="text-2xl font-black">
                      {unifiedSummary
                        ? unifiedSummary.pricing.sale_total.toFixed(2)
                        : (totalPlanned + servicesTotal).toFixed(2)} zl
                    </div>
                  </div>
                  <div className="rounded border border-[#39465a] bg-[#202734] p-3">
                    <div className="text-slate-400">Brutto</div>
                    <div className="text-2xl font-black">
                      {unifiedSummary
                        ? unifiedSummary.pricing.brutto_total.toFixed(2)
                        : (totalPlanned + servicesTotal).toFixed(2)} zl
                    </div>
                  </div>
                </div>

                {unifiedSummary ? (
                  <div className="mb-3 rounded border border-emerald-900/40 bg-emerald-950/20 p-2 text-xs leading-5 text-emerald-300/90">
                    <div>
                      Zysk: {unifiedSummary.pricing.profit_total.toFixed(2)} zl |
                      Marza: {unifiedSummary.pricing.margin_percent}% |
                      VAT: {unifiedSummary.pricing.vat.toFixed(2)} zl
                    </div>
                    <div className="text-emerald-200/60">
                      Zrodla: {unifiedSummary.audit.built_from.length > 0
                        ? unifiedSummary.audit.built_from.join(" + ")
                        : "brak"} |
                      Adapter: {unifiedSummary.audit.adapter_name} |
                      {unifiedSummary.audit.built_at}
                    </div>
                  </div>
                ) : unifiedSummaryLoading ? (
                  <div className="mb-3 text-xs text-slate-500">Pobieram ujednolicone podsumowanie...</div>
                ) : null}

                <div className="rounded border border-[#39465a] bg-[#202734] p-3 text-sm leading-7">
                  <div>Klient: {clientDisplayName || "-"}</div>
                  <div>Zamowienie: {form.orderTitle || "-"}</div>
                  <div>Status: {form.status}</div>
                  <div>Zaawansowanie: {Math.round((step / STEPS.length) * 100)}%</div>
                  <div>Zalaczniki od architekta: {attachments.length}</div>
                  <div>Pozycje do wyceny: {positions.length}</div>
                  <div>Probki / materialy: {materialChoices.length}</div>
                  <div>Uslugi: {servicesActive.length} (wartosc {servicesTotal.toFixed(2)} zl)</div>
                  <div>
                    Wplaty klienta: {payments.length} | Oplacone: {totalPaid.toFixed(2)} zl |
                    Pozostalo: {totalRemaining.toFixed(2)} zl
                  </div>
                  {savedOrderId ? <div className="text-emerald-300">Zapisane ID: {savedOrderId}</div> : null}
                </div>
              </Card>

              <Card className="border-[#333] bg-[#1e1e1e] p-4">
                <div className="mb-2 text-lg font-bold">Oferta klienta</div>
                <div className="mb-3 text-slate-400">Referencje obrazu do oferty: {attachments.length}</div>
                <div className="overflow-hidden rounded border border-[#33445f]">
                  <table className="w-full border-collapse">
                    <thead className="bg-[#bcc8da] text-[#0b1c39]">
                      <tr>
                        <th className="px-2 py-2 text-left">Plik</th>
                        <th className="px-2 py-2 text-left">Cel</th>
                        <th className="px-2 py-2 text-left">Opis</th>
                      </tr>
                    </thead>
                    <tbody>
                      {attachments.length === 0 ? (
                        <tr>
                          <td colSpan={3} className="px-2 py-8 text-center text-slate-500">
                            Brak obrazow przypietych do oferty.
                          </td>
                        </tr>
                      ) : (
                        attachments.map((item) => (
                          <tr key={item.id} className="border-t border-white/5">
                            <td className="px-2 py-2">{item.name}</td>
                            <td className="px-2 py-2">Zamowienie</td>
                            <td className="px-2 py-2">{item.description || "-"}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </Card>

              <Card className="border-[#333] bg-[#1e1e1e] p-4">
                <div className="text-[12px] font-bold uppercase tracking-widest text-slate-400">
                  Ostatnie zamowienia
                </div>
                <div className="mt-2 space-y-1">
                  {recentOrders.length === 0 ? (
                    <div className="text-slate-500">Brak zapisanych zamowien.</div>
                  ) : (
                    recentOrders.map((row) => (
                      <div
                        key={row.id}
                        className="flex items-center justify-between border-b border-white/5 py-1.5 text-sm"
                      >
                        <span>
                          #{row.id} - {row.client_name}
                        </span>
                        <span className="text-slate-500">{row.status}</span>
                      </div>
                    ))
                  )}
                </div>
              </Card>
            </div>
          ) : null}
        </div>

        <div className="shrink-0 border-t border-[#1a1a1a] bg-[#1c1d20] px-4 py-3">
          <div className="flex items-center justify-between">
            <Button
              variant="ghost"
              className="h-9"
              onClick={() => {
                void goToStep(step - 1);
              }}
              disabled={step === 1}
            >
              <ChevronLeft className="h-4 w-4" /> Cofnij
            </Button>
            <Button
              className="h-9"
              onClick={() => {
                void goToStep(step + 1);
              }}
              disabled={step === STEPS.length}
            >
              Kontynuuj <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
