"use client";

import { useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Button, Card, StatCard } from "@/components/ui";
import {
  TechModulAPI,
  type PurchaseDocument,
  type PurchaseDocumentLine,
  type PurchaseDocumentCreatePayload,
} from "@/services/api";
import { useCurrentUser } from "@/services/user-context";
import {
  ChevronDown,
  ChevronRight,
  FileText,
  Plus,
  RefreshCw,
  Search,
  CheckCircle2,
  XCircle,
  PackageCheck,
} from "lucide-react";

const inputCls =
  "w-full bg-black/20 border border-white/10 rounded px-3 py-2 text-sm text-slate-200 outline-none focus:border-blue-500";

const STATUS_STYLES: Record<string, string> = {
  unpaid: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  paid: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  received: "bg-blue-500/15 text-blue-300 border-blue-500/30",
  partial: "bg-purple-500/15 text-purple-300 border-purple-500/30",
};

const STATUS_LABELS: Record<string, string> = {
  unpaid: "Nieoplacone",
  paid: "Oplacone",
  received: "Przyjete",
  partial: "Czesciowe",
};

type LineInput = {
  material_id: string;
  description_snapshot: string;
  qty: string;
  unit: string;
  unit_price_net: string;
  vat_rate: string;
  is_stock_item: boolean;
  order_id: string;
  note: string;
};

function emptyLine(): LineInput {
  return {
    material_id: "",
    description_snapshot: "",
    qty: "1",
    unit: "pcs",
    unit_price_net: "0",
    vat_rate: "23",
    is_stock_item: true,
    order_id: "",
    note: "",
  };
}

export default function PurchasesPage() {
  const [currentUser] = useCurrentUser();
  const [docs, setDocs] = useState<PurchaseDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [expandedLines, setExpandedLines] = useState<PurchaseDocumentLine[]>([]);
  const [linesLoading, setLinesLoading] = useState(false);

  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createResult, setCreateResult] = useState<{ ok: boolean; message: string } | null>(null);

  const [supplierName, setSupplierName] = useState("");
  const [docNumber, setDocNumber] = useState("");
  const [docDate, setDocDate] = useState(new Date().toISOString().slice(0, 10));
  const [docType, setDocType] = useState("invoice");
  const [paymentMethod, setPaymentMethod] = useState("");
  const [paymentStatus, setPaymentStatus] = useState("unpaid");
  const [docNote, setDocNote] = useState("");
  const [lines, setLines] = useState<LineInput[]>([emptyLine()]);

  const [receiveLoading, setReceiveLoading] = useState<number | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await TechModulAPI.getPurchaseDocuments(500);
      setDocs(data ?? []);
    } catch (e: any) {
      setError(e?.message ?? "Blad ladowania dokumentow zakupu");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filtered = useMemo(() => {
    return docs.filter((d) => {
      if (statusFilter !== "all" && d.payment_status !== statusFilter) return false;
      if (search) {
        const q = search.toLowerCase();
        if (
          !d.document_number.toLowerCase().includes(q) &&
          !d.supplier_name.toLowerCase().includes(q)
        )
          return false;
      }
      return true;
    });
  }, [docs, search, statusFilter]);

  const totalNet = docs.reduce((s, d) => s + (d.total_net ?? 0), 0);
  const totalGross = docs.reduce((s, d) => s + (d.total_gross ?? 0), 0);
  const receivedCount = docs.filter((d) => d.payment_status === "received").length;

  const toggleExpand = async (docId: number) => {
    if (expandedId === docId) {
      setExpandedId(null);
      setExpandedLines([]);
      return;
    }
    setExpandedId(docId);
    setExpandedLines([]);
    setLinesLoading(true);
    try {
      const detail = await TechModulAPI.getPurchaseDocument(docId);
      setExpandedLines(detail.lines ?? []);
    } catch {
      setExpandedLines([]);
    } finally {
      setLinesLoading(false);
    }
  };

  const handleReceive = async (docId: number) => {
    if (!window.confirm(`Przyjac dokument #${docId} na magazyn?`)) return;
    setReceiveLoading(docId);
    try {
      await TechModulAPI.receivePurchaseDocument(docId, "", currentUser?.name ?? "");
      await loadData();
      if (expandedId === docId) {
        setExpandedId(null);
        setExpandedLines([]);
      }
    } catch (e: any) {
      alert(e?.message ?? "Blad przyjecia");
    } finally {
      setReceiveLoading(null);
    }
  };

  const updateLine = (idx: number, field: keyof LineInput, value: any) => {
    setLines((prev) => prev.map((l, i) => (i === idx ? { ...l, [field]: value } : l)));
  };

  const removeLine = (idx: number) => {
    setLines((prev) => (prev.length <= 1 ? prev : prev.filter((_, i) => i !== idx)));
  };

  const resetCreateForm = () => {
    setSupplierName("");
    setDocNumber("");
    setDocDate(new Date().toISOString().slice(0, 10));
    setDocType("invoice");
    setPaymentMethod("");
    setPaymentStatus("unpaid");
    setDocNote("");
    setLines([emptyLine()]);
    setCreateResult(null);
  };

  const handleCreate = async () => {
    setCreating(true);
    setCreateResult(null);
    try {
      if (!supplierName.trim()) throw new Error("Dostawca jest wymagany");
      if (!docNumber.trim()) throw new Error("Numer dokumentu jest wymagany");
      if (!docDate.trim()) throw new Error("Data dokumentu jest wymagana");

      const payload: PurchaseDocumentCreatePayload = {
        supplier_name: supplierName.trim(),
        document_number: docNumber.trim(),
        document_date: docDate.trim(),
        document_type: docType,
        payment_method: paymentMethod,
        payment_status: paymentStatus,
        note: docNote,
        lines: lines
          .filter((l) => Number(l.qty) > 0)
          .map((l) => ({
            material_id: l.material_id ? Number(l.material_id) : null,
            description_snapshot: l.description_snapshot,
            qty: Number(l.qty),
            unit: l.unit,
            unit_price_net: Number(l.unit_price_net),
            vat_rate: Number(l.vat_rate),
            is_stock_item: l.is_stock_item,
            order_id: l.order_id ? Number(l.order_id) : null,
            note: l.note,
          })),
      };

      const result = await TechModulAPI.createPurchaseDocument(payload);
      setCreateResult({
        ok: true,
        message: `Dokument #${result.id} utworzony (${result.line_ids?.length ?? 0} pozycji)`,
      });
      await loadData();
      resetCreateForm();
      setShowCreate(false);
    } catch (e: any) {
      setCreateResult({ ok: false, message: e?.message ?? "Blad tworzenia dokumentu" });
    } finally {
      setCreating(false);
    }
  };

  return (
    <AppShell>
      <PageHeader
        eyebrow="Magazyn"
        title="Dokumenty zakupu"
        subtitle="Tworzenie i przeglad dokumentow zakupu, przyjecia na magazyn."
        actions={
          <div className="flex gap-2">
            <Button as="link" href="/inventory" variant="secondary">Stany</Button>
            <Button as="link" href="/inventory/payments" variant="secondary">Platnosci</Button>
            <Button onClick={() => { setShowCreate((v) => !v); setCreateResult(null); }}>
              <Plus className="w-4 h-4 mr-1" />
              Nowy dokument
            </Button>
            <Button onClick={loadData} variant="secondary" disabled={loading}>
              <RefreshCw className={`w-4 h-4 mr-1 ${loading ? "animate-spin" : ""}`} />
              Odswiez
            </Button>
          </div>
        }
      />

      <div className="max-w-7xl mx-auto space-y-4 pb-10">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <StatCard label="Dokumentow" value={docs.length} icon={<FileText className="w-5 h-5" />} />
          <StatCard label="Suma netto" value={`${totalNet.toFixed(2)} PLN`} />
          <StatCard label="Suma brutto" value={`${totalGross.toFixed(2)} PLN`} tone="warn" />
          <StatCard label="Przyjete" value={receivedCount} tone="success" />
        </div>

        {/* Create result (persists outside form) */}
        {createResult && !showCreate && (
          <div className={`flex items-start gap-2 p-3 rounded border text-sm ${createResult.ok ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300" : "bg-red-500/10 border-red-500/30 text-red-300"}`}>
            {createResult.ok ? <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" /> : <XCircle className="w-4 h-4 mt-0.5 shrink-0" />}
            {createResult.message}
          </div>
        )}

        {/* Create form */}
        {showCreate && (
          <Card className="p-5 space-y-4">
            <h3 className="text-sm font-semibold text-white">Nowy dokument zakupu</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Dostawca *</label>
                <input value={supplierName} onChange={(e) => setSupplierName(e.target.value)} className={inputCls} placeholder="np. Kronospan" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Numer dokumentu *</label>
                <input value={docNumber} onChange={(e) => setDocNumber(e.target.value)} className={inputCls} placeholder="np. FV/2026/04/001" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Data dokumentu *</label>
                <input type="date" value={docDate} onChange={(e) => setDocDate(e.target.value)} className={inputCls} />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Typ dokumentu</label>
                <select value={docType} onChange={(e) => setDocType(e.target.value)} className={inputCls}>
                  <option value="invoice">Faktura</option>
                  <option value="receipt">Paragon</option>
                  <option value="proforma">Proforma</option>
                  <option value="other">Inny</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Metoda platnosci</label>
                <select value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)} className={inputCls}>
                  <option value="">Nie wybrano</option>
                  <option value="bank">Przelew</option>
                  <option value="cash">Gotowka</option>
                  <option value="card">Karta</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Status platnosci</label>
                <select value={paymentStatus} onChange={(e) => setPaymentStatus(e.target.value)} className={inputCls}>
                  <option value="unpaid">Nieoplacone</option>
                  <option value="paid">Oplacone</option>
                  <option value="partial">Czesciowe</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Notatka</label>
              <input value={docNote} onChange={(e) => setDocNote(e.target.value)} className={inputCls} placeholder="opcjonalnie" />
            </div>

            {/* Lines */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wide">Pozycje dokumentu</h4>
                <button onClick={() => setLines((p) => [...p, emptyLine()])} className="text-xs text-blue-400 hover:text-blue-300">
                  + Dodaj pozycje
                </button>
              </div>
              {lines.map((line, idx) => (
                <div key={idx} className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-8 gap-2 bg-white/5 rounded p-2 items-end text-xs">
                  <div className="col-span-1">
                    <label className="block text-slate-500 mb-0.5">Material ID</label>
                    <input value={line.material_id} onChange={(e) => updateLine(idx, "material_id", e.target.value)} className={inputCls} placeholder="-" />
                  </div>
                  <div className="col-span-2">
                    <label className="block text-slate-500 mb-0.5">Opis</label>
                    <input value={line.description_snapshot} onChange={(e) => updateLine(idx, "description_snapshot", e.target.value)} className={inputCls} placeholder="opis pozycji" />
                  </div>
                  <div>
                    <label className="block text-slate-500 mb-0.5">Ilosc</label>
                    <input type="number" step="any" min="0" value={line.qty} onChange={(e) => updateLine(idx, "qty", e.target.value)} className={inputCls} />
                  </div>
                  <div>
                    <label className="block text-slate-500 mb-0.5">Jedn.</label>
                    <select value={line.unit} onChange={(e) => updateLine(idx, "unit", e.target.value)} className={inputCls}>
                      <option value="pcs">szt</option>
                      <option value="m2">m2</option>
                      <option value="mb">mb</option>
                      <option value="kg">kg</option>
                      <option value="l">l</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-slate-500 mb-0.5">Cena netto</label>
                    <input type="number" step="any" min="0" value={line.unit_price_net} onChange={(e) => updateLine(idx, "unit_price_net", e.target.value)} className={inputCls} />
                  </div>
                  <div>
                    <label className="block text-slate-500 mb-0.5">VAT %</label>
                    <input type="number" step="any" value={line.vat_rate} onChange={(e) => updateLine(idx, "vat_rate", e.target.value)} className={inputCls} />
                  </div>
                  <div className="flex items-end gap-2">
                    <label className="flex items-center gap-1 text-slate-400 cursor-pointer">
                      <input type="checkbox" checked={line.is_stock_item} onChange={(e) => updateLine(idx, "is_stock_item", e.target.checked)} className="rounded" />
                      Magazyn
                    </label>
                    {lines.length > 1 && (
                      <button onClick={() => removeLine(idx)} className="text-red-400 hover:text-red-300 text-xs px-1">X</button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {createResult && (
              <div className={`flex items-start gap-2 p-3 rounded border text-sm ${createResult.ok ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300" : "bg-red-500/10 border-red-500/30 text-red-300"}`}>
                {createResult.ok ? <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" /> : <XCircle className="w-4 h-4 mt-0.5 shrink-0" />}
                {createResult.message}
              </div>
            )}

            <div className="flex gap-3">
              <Button onClick={handleCreate} disabled={creating}>
                {creating ? "Tworzenie..." : "Utworz dokument"}
              </Button>
              <Button variant="ghost" onClick={() => { resetCreateForm(); setShowCreate(false); }}>
                Anuluj
              </Button>
            </div>
          </Card>
        )}

        {/* Filters */}
        <Card className="p-4">
          <div className="flex flex-wrap gap-3 items-center">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                placeholder="Szukaj po numerze dokumentu lub dostawcy..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-black/20 border border-white/10 rounded px-3 py-2 pl-9 text-sm text-slate-200 outline-none focus:border-blue-500"
              />
            </div>
            <select
              className="bg-black/20 border border-white/10 rounded px-3 py-2 text-sm"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">Wszystkie statusy</option>
              <option value="unpaid">Nieoplacone</option>
              <option value="paid">Oplacone</option>
              <option value="received">Przyjete</option>
              <option value="partial">Czesciowe</option>
            </select>
          </div>
        </Card>

        {/* Table */}
        <Card padded={false}>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-200/90 text-slate-900">
                <tr>
                  <th className="w-8 px-2 py-2"></th>
                  <th className="text-left px-3 py-2">Nr dokumentu</th>
                  <th className="text-left px-3 py-2">Dostawca</th>
                  <th className="text-left px-3 py-2">Data</th>
                  <th className="text-left px-3 py-2">Status</th>
                  <th className="text-left px-3 py-2">Platnosc</th>
                  <th className="text-right px-3 py-2">Netto</th>
                  <th className="text-right px-3 py-2">Brutto</th>
                  <th className="text-left px-3 py-2">Akcja</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10">
                {loading ? (
                  <tr>
                    <td colSpan={9} className="px-3 py-8 text-center text-slate-400">
                      Ladowanie dokumentow...
                    </td>
                  </tr>
                ) : error ? (
                  <tr>
                    <td colSpan={9} className="px-3 py-8 text-center text-red-300">
                      {error}
                    </td>
                  </tr>
                ) : filtered.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="px-3 py-8 text-center text-slate-500">
                      Brak dokumentow zakupu.
                    </td>
                  </tr>
                ) : (
                  filtered.map((d) => {
                    const isExpanded = expandedId === d.id;
                    const sty = STATUS_STYLES[d.payment_status] ?? STATUS_STYLES.unpaid;
                    const canReceive = d.payment_status !== "received";
                    return (
                      <>
                        <tr key={d.id} className={`hover:bg-white/5 cursor-pointer ${isExpanded ? "bg-white/5" : ""}`} onClick={() => toggleExpand(d.id)}>
                          <td className="px-2 py-2 text-slate-500">
                            {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                          </td>
                          <td className="px-3 py-2 text-white font-medium">{d.document_number}</td>
                          <td className="px-3 py-2 text-slate-200">{d.supplier_name}</td>
                          <td className="px-3 py-2 text-slate-300 whitespace-nowrap">{d.document_date}</td>
                          <td className="px-3 py-2">
                            <span className={`inline-flex px-2 py-0.5 rounded border text-xs font-semibold ${sty}`}>
                              {STATUS_LABELS[d.payment_status] ?? d.payment_status}
                            </span>
                          </td>
                          <td className="px-3 py-2 text-slate-300">{d.payment_method || "-"}</td>
                          <td className="px-3 py-2 text-right text-white">{d.total_net.toFixed(2)}</td>
                          <td className="px-3 py-2 text-right text-slate-300">{d.total_gross.toFixed(2)}</td>
                          <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                            {canReceive && (
                              <button
                                onClick={() => handleReceive(d.id)}
                                disabled={receiveLoading === d.id}
                                className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded border border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/10 disabled:opacity-50"
                              >
                                <PackageCheck className="w-3 h-3" />
                                {receiveLoading === d.id ? "..." : "Przyjmij"}
                              </button>
                            )}
                          </td>
                        </tr>
                        {isExpanded && (
                          <tr key={`${d.id}-detail`}>
                            <td colSpan={9} className="px-6 py-3 bg-white/[0.02]">
                              {linesLoading ? (
                                <p className="text-slate-400 text-xs">Ladowanie pozycji...</p>
                              ) : expandedLines.length === 0 ? (
                                <p className="text-slate-500 text-xs">Brak pozycji w tym dokumencie.</p>
                              ) : (
                                <table className="w-full text-xs">
                                  <thead className="text-slate-400">
                                    <tr>
                                      <th className="text-left px-2 py-1">Material</th>
                                      <th className="text-left px-2 py-1">Opis</th>
                                      <th className="text-right px-2 py-1">Ilosc</th>
                                      <th className="text-left px-2 py-1">Jedn.</th>
                                      <th className="text-right px-2 py-1">Cena netto</th>
                                      <th className="text-right px-2 py-1">Wartosc netto</th>
                                      <th className="text-right px-2 py-1">Wartosc brutto</th>
                                      <th className="text-center px-2 py-1">Magazyn</th>
                                      <th className="text-left px-2 py-1">Zamowienie</th>
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-white/5">
                                    {expandedLines.map((ln) => (
                                      <tr key={ln.id} className="hover:bg-white/5">
                                        <td className="px-2 py-1 text-slate-200 font-mono">
                                          {ln.material_name ? `${ln.material_name} (#${ln.material_id})` : (ln.material_id ?? "-")}
                                        </td>
                                        <td className="px-2 py-1 text-slate-300">{ln.description_snapshot || "-"}</td>
                                        <td className="px-2 py-1 text-right text-white">{ln.qty}</td>
                                        <td className="px-2 py-1 text-slate-300">{ln.unit}</td>
                                        <td className="px-2 py-1 text-right text-slate-300">{ln.unit_price_net.toFixed(2)}</td>
                                        <td className="px-2 py-1 text-right text-white">{ln.line_total_net.toFixed(2)}</td>
                                        <td className="px-2 py-1 text-right text-slate-300">{ln.line_total_gross.toFixed(2)}</td>
                                        <td className="px-2 py-1 text-center">{Number(ln.is_stock_item) ? "✓" : "-"}</td>
                                        <td className="px-2 py-1 text-slate-400">{ln.order_id ?? "-"}</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              )}
                            </td>
                          </tr>
                        )}
                      </>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </Card>

        <div className="text-xs text-slate-500 text-right">
          Wyswietlono {filtered.length} z {docs.length} dokumentow
        </div>
      </div>
    </AppShell>
  );
}
