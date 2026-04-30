"use client";

import { useState } from "react";
import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Button, Card } from "@/components/ui";
import { TechModulAPI } from "@/services/api";
import { useCurrentUser } from "@/services/user-context";
import { CheckCircle2, XCircle } from "lucide-react";

type Tab = "reserve" | "issue" | "return" | "scrap" | "correction";

const TABS: { key: Tab; label: string }[] = [
  { key: "reserve", label: "Rezerwacja" },
  { key: "issue", label: "Wydanie" },
  { key: "return", label: "Zwrot" },
  { key: "scrap", label: "Brak/odpad" },
  { key: "correction", label: "Korekta" },
];

function FieldRow({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">{children}</div>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs text-slate-400 mb-1">{label}</label>
      {children}
    </div>
  );
}

const inputCls = "w-full bg-black/20 border border-white/10 rounded px-3 py-2 text-sm text-slate-200 outline-none focus:border-blue-500";

export default function InventoryActionsPage() {
  const [currentUser] = useCurrentUser();
  const [tab, setTab] = useState<Tab>("reserve");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

  const createdBy = currentUser?.name ?? "";

  const [materialId, setMaterialId] = useState("");
  const [orderId, setOrderId] = useState("");
  const [qty, setQty] = useState("");
  const [unit, setUnit] = useState("pcs");
  const [note, setNote] = useState("");
  const [unitCostOverride, setUnitCostOverride] = useState("");
  const [relatedIssueId, setRelatedIssueId] = useState("");
  const [chargeToOrder, setChargeToOrder] = useState(false);
  const [qtyDelta, setQtyDelta] = useState("");

  const resetForm = () => {
    setMaterialId("");
    setOrderId("");
    setQty("");
    setUnit("pcs");
    setNote("");
    setUnitCostOverride("");
    setRelatedIssueId("");
    setChargeToOrder(false);
    setQtyDelta("");
    setResult(null);
  };

  const handleSubmit = async () => {
    setBusy(true);
    setResult(null);
    try {
      const mid = Number(materialId);
      if (!mid || mid <= 0) throw new Error("Material ID jest wymagane");

      switch (tab) {
        case "reserve": {
          const oid = Number(orderId);
          if (!oid) throw new Error("Zamowienie ID jest wymagane");
          const q = Number(qty);
          if (!q || q <= 0) throw new Error("Ilosc musi byc wieksza od 0");
          await TechModulAPI.reserveMaterial({ material_id: mid, order_id: oid, qty: q, unit, note, created_by: createdBy });
          setResult({ ok: true, message: `Zarezerwowano ${q} ${unit} materialu #${mid} dla zamowienia #${oid}` });
          break;
        }
        case "issue": {
          const oid = Number(orderId);
          if (!oid) throw new Error("Zamowienie ID jest wymagane");
          const q = Number(qty);
          if (!q || q <= 0) throw new Error("Ilosc musi byc wieksza od 0");
          const costOverride = unitCostOverride ? Number(unitCostOverride) : undefined;
          await TechModulAPI.issueMaterial({ material_id: mid, order_id: oid, qty: q, unit, unit_cost_override: costOverride, note, created_by: createdBy });
          setResult({ ok: true, message: `Wydano ${q} ${unit} materialu #${mid} do zamowienia #${oid}` });
          break;
        }
        case "return": {
          const oid = Number(orderId);
          if (!oid) throw new Error("Zamowienie ID jest wymagane");
          const q = Number(qty);
          if (!q || q <= 0) throw new Error("Ilosc musi byc wieksza od 0");
          const relId = relatedIssueId ? Number(relatedIssueId) : undefined;
          await TechModulAPI.returnMaterial({ material_id: mid, order_id: oid, qty: q, unit, related_issue_movement_id: relId, note, created_by: createdBy });
          setResult({ ok: true, message: `Zwrocono ${q} ${unit} materialu #${mid} z zamowienia #${oid}` });
          break;
        }
        case "scrap": {
          const q = Number(qty);
          if (!q || q <= 0) throw new Error("Ilosc musi byc wieksza od 0");
          const oid = orderId ? Number(orderId) : undefined;
          await TechModulAPI.scrapMaterial({ material_id: mid, qty: q, unit, order_id: oid, charge_to_order: chargeToOrder, note, created_by: createdBy });
          setResult({ ok: true, message: `Odpisano ${q} ${unit} materialu #${mid} jako brak/odpad` });
          break;
        }
        case "correction": {
          const delta = Number(qtyDelta);
          if (!delta || delta === 0) throw new Error("Korekta (delta) nie moze byc 0");
          await TechModulAPI.correctInventory({ material_id: mid, qty_delta: delta, unit, note, created_by: createdBy });
          setResult({ ok: true, message: `Korekta materialu #${mid}: ${delta > 0 ? "+" : ""}${delta} ${unit}` });
          break;
        }
      }
    } catch (e: any) {
      setResult({ ok: false, message: e?.message ?? "Blad operacji" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <AppShell>
      <PageHeader
        eyebrow="Magazyn"
        title="Akcje magazynowe"
        subtitle="Rezerwacja, wydanie, zwrot, odpis brakow, korekta stanow."
        actions={
          <div className="flex gap-2">
            <Button as="link" href="/inventory" variant="secondary">Stany</Button>
            <Button as="link" href="/inventory/movements" variant="secondary">Ruchy</Button>
          </div>
        }
      />

      <div className="max-w-3xl mx-auto space-y-4 pb-10">
        <Card className="p-0">
          <div className="flex border-b border-white/10 overflow-x-auto">
            {TABS.map((t) => (
              <button
                key={t.key}
                onClick={() => { setTab(t.key); setResult(null); }}
                className={`px-5 py-3 text-sm font-medium whitespace-nowrap transition-colors ${
                  tab === t.key
                    ? "text-blue-400 border-b-2 border-blue-500 bg-blue-500/5"
                    : "text-slate-400 hover:text-white hover:bg-white/5"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          <div className="p-5 space-y-4">
            {/* Material ID - always shown */}
            <Field label="Material ID *">
              <input type="number" value={materialId} onChange={(e) => setMaterialId(e.target.value)} className={inputCls} placeholder="np. 1" />
            </Field>

            {/* Order ID - shown for reserve, issue, return, scrap */}
            {tab !== "correction" && (
              <Field label={`Zamowienie ID ${tab === "scrap" ? "(opcjonalnie)" : "*"}`}>
                <input type="number" value={orderId} onChange={(e) => setOrderId(e.target.value)} className={inputCls} placeholder="np. 10" />
              </Field>
            )}

            {/* Qty or QtyDelta */}
            {tab === "correction" ? (
              <Field label="Korekta ilosci (delta) *">
                <input type="number" step="any" value={qtyDelta} onChange={(e) => setQtyDelta(e.target.value)} className={inputCls} placeholder="np. -2 lub +5" />
              </Field>
            ) : (
              <Field label="Ilosc *">
                <input type="number" step="any" min="0.01" value={qty} onChange={(e) => setQty(e.target.value)} className={inputCls} placeholder="np. 3" />
              </Field>
            )}

            <FieldRow>
              <Field label="Jednostka">
                <select value={unit} onChange={(e) => setUnit(e.target.value)} className={inputCls}>
                  <option value="pcs">szt (pcs)</option>
                  <option value="m2">m2</option>
                  <option value="mb">mb</option>
                  <option value="kg">kg</option>
                  <option value="l">l</option>
                </select>
              </Field>
              <Field label="Notatka">
                <input type="text" value={note} onChange={(e) => setNote(e.target.value)} className={inputCls} placeholder="opcjonalnie" />
              </Field>
            </FieldRow>

            {/* Issue-specific: unit cost override */}
            {tab === "issue" && (
              <Field label="Nadpisanie kosztu jednostkowego (opcjonalnie)">
                <input type="number" step="any" value={unitCostOverride} onChange={(e) => setUnitCostOverride(e.target.value)} className={inputCls} placeholder="Automatycznie: srednia wazona" />
              </Field>
            )}

            {/* Return-specific: related issue movement id */}
            {tab === "return" && (
              <Field label="ID ruchu wydania (opcjonalnie)">
                <input type="number" value={relatedIssueId} onChange={(e) => setRelatedIssueId(e.target.value)} className={inputCls} placeholder="Ruch OUT z ktorego zwracamy" />
              </Field>
            )}

            {/* Scrap-specific: charge to order */}
            {tab === "scrap" && (
              <div className="flex items-center gap-2">
                <input type="checkbox" id="chargeToOrder" checked={chargeToOrder} onChange={(e) => setChargeToOrder(e.target.checked)} className="rounded" />
                <label htmlFor="chargeToOrder" className="text-sm text-slate-300">Obciaz koszt zamowienia</label>
              </div>
            )}

            {result && (
              <div className={`flex items-start gap-2 p-3 rounded border text-sm ${result.ok ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300" : "bg-red-500/10 border-red-500/30 text-red-300"}`}>
                {result.ok ? <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" /> : <XCircle className="w-4 h-4 mt-0.5 shrink-0" />}
                {result.message}
              </div>
            )}

            <div className="flex gap-3 pt-2">
              <Button onClick={handleSubmit} disabled={busy}>
                {busy ? "Wykonywanie..." : "Wykonaj"}
              </Button>
              <Button variant="ghost" onClick={resetForm}>
                Wyczysc
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </AppShell>
  );
}
