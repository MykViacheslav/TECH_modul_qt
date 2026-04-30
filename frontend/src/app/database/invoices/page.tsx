"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import AppShell from "@/components/AppShell";
import { Card, Button, Section } from "@/components/ui";
import { ArrowLeft, Upload, Loader2, CheckCircle2, XCircle, RefreshCw, Link2, History } from "lucide-react";
import { TechModulAPI, type InvoiceLineItemRecord, type InvoiceScanned, type MaterialRecord, type ArrivalRecord } from "@/services/api";

type InvoiceTabKey = "import" | "review" | "linked" | "price";

const INVOICE_TABS: Array<{ key: InvoiceTabKey; label: string }> = [
  { key: "import", label: "Import" },
  { key: "review", label: "Review" },
  { key: "linked", label: "Linked deliveries" },
  { key: "price", label: "Price history" },
];

function pickInvoiceId(row: any): number {
  return Number(row?.id || row?.invoice_id || 0);
}

function pickInvoiceLabel(row: any): string {
  return String(row?.invoice_nr || row?.nr || row?.source_filename || `#${pickInvoiceId(row)}`);
}

function badgeClass(statusRaw: string): string {
  const status = statusRaw.toLowerCase();
  if (status === "confirmed") return "border-emerald-500/60 bg-emerald-500/15 text-emerald-300";
  if (status === "partial") return "border-amber-500/60 bg-amber-500/15 text-amber-300";
  return "border-slate-500/60 bg-white/5 text-slate-300";
}

function normalizeInvoiceStatus(statusRaw?: string): "IMPORTED" | "PARTIAL" | "CONFIRMED" {
  const status = String(statusRaw || "").toLowerCase();
  if (status === "confirmed") return "CONFIRMED";
  if (status === "partial") return "PARTIAL";
  return "IMPORTED";
}

function canConfirmLine(row: InvoiceLineItemRecord): { ok: boolean; reason: string } {
  const confidence = Number(row.confidence || 0);
  const hasUnit = String(row.unit || "").trim().length > 0;
  if (!hasUnit) return { ok: false, reason: "Brak jednostki - zostaje w review." };
  if (confidence < 0.75) return { ok: false, reason: "Niska pewnosc OCR/parsowania - zostaje w review." };
  return { ok: true, reason: "" };
}

export default function DatabaseInvoicesPage() {
  const [invoices, setInvoices] = useState<InvoiceScanned[]>([]);
  const [materials, setMaterials] = useState<MaterialRecord[]>([]);
  const [arrivals, setArrivals] = useState<ArrivalRecord[]>([]);
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<number>(0);
  const [lineItems, setLineItems] = useState<InvoiceLineItemRecord[]>([]);
  const [selectedLineId, setSelectedLineId] = useState<number>(0);
  const [activeTab, setActiveTab] = useState<InvoiceTabKey>("review");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [scanningSources, setScanningSources] = useState(false);
  const [savingLineId, setSavingLineId] = useState<number>(0);
  const [confirming, setConfirming] = useState(false);
  const [msg, setMsg] = useState<string>("");
  const [pickedMaterial, setPickedMaterial] = useState<Record<number, number>>({});
  const [sinceDate, setSinceDate] = useState<string>("");
  const [scanLocal, setScanLocal] = useState(true);
  const [scanEmail, setScanEmail] = useState(true);

  const selectedInvoice = useMemo(
    () => invoices.find((x) => pickInvoiceId(x) === selectedInvoiceId),
    [invoices, selectedInvoiceId]
  );

  const selectedLine = useMemo(
    () => lineItems.find((x) => Number(x.id) === Number(selectedLineId)),
    [lineItems, selectedLineId]
  );

  const selectedInvoiceStatus = normalizeInvoiceStatus((selectedInvoice as any)?.status);

  const linkedArrivals = useMemo(() => {
    if (!selectedInvoiceId) return [];
    return arrivals
      .filter((x) => Number(x.invoice_id || 0) === Number(selectedInvoiceId))
      .sort((a, b) => String(b.date || "").localeCompare(String(a.date || "")));
  }, [arrivals, selectedInvoiceId]);

  const selectedMaterialIdForPrice = useMemo(() => {
    if (!selectedLine) return 0;
    return Number(
      pickedMaterial[selectedLine.id] || selectedLine.selected_material_id || 0
    );
  }, [pickedMaterial, selectedLine]);

  const selectedMaterial = useMemo(
    () => materials.find((m) => Number(m.id) === selectedMaterialIdForPrice),
    [materials, selectedMaterialIdForPrice]
  );

  const priceHistoryRows = useMemo(() => {
    if (!selectedMaterialIdForPrice) return [];
    return arrivals
      .filter((x) => Number(x.material_id || 0) === Number(selectedMaterialIdForPrice))
      .sort((a, b) => String(b.date || "").localeCompare(String(a.date || "")))
      .slice(0, 20);
  }, [arrivals, selectedMaterialIdForPrice]);

  const loadInvoices = async () => {
    const list = await TechModulAPI.getInvoices();
    setInvoices(list || []);
    if ((list || []).length > 0 && !selectedInvoiceId) {
      setSelectedInvoiceId(pickInvoiceId(list[0]));
    }
  };

  const loadLineItems = async (invoiceId: number) => {
    if (!invoiceId) {
      setLineItems([]);
      setSelectedLineId(0);
      return;
    }
    const res = await TechModulAPI.getInvoiceLineItems(invoiceId);
    const items = res.items || [];
    setLineItems(items);
    const first = items[0];
    setSelectedLineId((prev) => (prev && items.some((x) => Number(x.id) === Number(prev)) ? prev : Number(first?.id || 0)));
  };

  const loadAll = async () => {
    setLoading(true);
    setMsg("");
    try {
      const [mats, arr] = await Promise.all([TechModulAPI.getMaterials(), TechModulAPI.getArrivals()]);
      setMaterials(mats || []);
      setArrivals(arr || []);
      await loadInvoices();
    } catch (e: any) {
      setMsg(e?.message || "Blad ladowania danych faktur");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  useEffect(() => {
    try {
      const rawTab = window.localStorage.getItem("invoices_active_local_tab_v1");
      if (rawTab === "import" || rawTab === "review" || rawTab === "linked" || rawTab === "price") {
        setActiveTab(rawTab);
      }
      const fromStorage = window.localStorage.getItem("invoice_sources_since_date");
      if (fromStorage && /^\d{4}-\d{2}-\d{2}$/.test(fromStorage)) {
        setSinceDate(fromStorage);
        return;
      }
    } catch {}
    const now = new Date();
    now.setDate(now.getDate() - 14);
    setSinceDate(now.toISOString().slice(0, 10));
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem("invoices_active_local_tab_v1", activeTab);
    } catch {}
  }, [activeTab]);

  useEffect(() => {
    if (sinceDate) {
      try {
        window.localStorage.setItem("invoice_sources_since_date", sinceDate);
      } catch {}
    }
  }, [sinceDate]);

  useEffect(() => {
    if (!selectedInvoiceId) return;
    loadLineItems(selectedInvoiceId).catch((e: any) => {
      setMsg(e?.message || "Blad ladowania pozycji faktury");
    });
  }, [selectedInvoiceId]);

  const onUpload = async (file: File | null) => {
    if (!file) return;
    setUploading(true);
    setMsg("");
    try {
      const res = await TechModulAPI.importInvoicePdf(file);
      if (res.is_duplicate) {
        setMsg(`Duplikat faktury (${res.duplicate_reason}). Uzyto istniejacego wpisu #${res.invoice_id}.`);
      } else {
        setMsg(`Zaimportowano fakture #${res.invoice_id}, pozycje: ${res.line_items_total}.`);
      }
      await loadAll();
      setSelectedInvoiceId(res.invoice_id);
      await loadLineItems(res.invoice_id);
      setActiveTab("review");
    } catch (e: any) {
      setMsg(e?.message || "Blad importu PDF");
    } finally {
      setUploading(false);
    }
  };

  const checkSources = async () => {
    setScanningSources(true);
    setMsg("");
    try {
      const res = await TechModulAPI.checkInvoiceSources({
        since_date: sinceDate || "",
        scan_local: scanLocal,
        scan_email: scanEmail,
        scan_telegram: false,
        scan_whatsapp: false,
      });
      const summary = res.summary || { checked: 0, imported: 0, duplicates: 0, errors: 0 };
      const warningText = (res.warnings || []).join(" | ");
      setMsg(
        `Sprawdzono: ${summary.checked}, import: ${summary.imported}, duplikaty: ${summary.duplicates}, bledy: ${summary.errors}` +
          (warningText ? ` | ${warningText}` : "")
      );
      await loadAll();
      if (selectedInvoiceId) {
        await loadLineItems(selectedInvoiceId);
      }
    } catch (e: any) {
      setMsg(e?.message || "Blad sprawdzania zrodel faktur");
    } finally {
      setScanningSources(false);
    }
  };

  const markLine = async (row: InvoiceLineItemRecord, status: "confirmed" | "skipped") => {
    setSavingLineId(row.id);
    setMsg("");
    try {
      const selectedMatId = pickedMaterial[row.id] || row.selected_material_id || 0;
      const payload: any = { review_status: status };
      if (status === "confirmed") {
        const safe = canConfirmLine(row);
        if (!safe.ok) {
          setMsg(safe.reason);
          return;
        }
        if (!selectedMatId) {
          setMsg("Wybierz material dla pozycji przed potwierdzeniem.");
          return;
        }
        const mat = materials.find((m) => Number(m.id) === Number(selectedMatId));
        payload.selected_material_id = selectedMatId;
        payload.selected_material_name = String(mat?.name || "");
      }
      await TechModulAPI.updateInvoiceLineItem(selectedInvoiceId, row.id, payload);
      await loadLineItems(selectedInvoiceId);
      await loadAll();
    } catch (e: any) {
      setMsg(e?.message || "Blad aktualizacji pozycji");
    } finally {
      setSavingLineId(0);
    }
  };

  const confirmExport = async () => {
    if (!selectedInvoiceId) return;
    setConfirming(true);
    setMsg("");
    try {
      const res = await TechModulAPI.confirmInvoice(selectedInvoiceId);
      setMsg(
        `Zakonczono confirm/export. Dostawy: ${res.arrivals_created}, price_history: ${res.price_history_written}, pominiete: ${res.skipped_lines}.`
      );
      await loadAll();
      await loadLineItems(selectedInvoiceId);
    } catch (e: any) {
      setMsg(e?.message || "Blad confirm/export");
    } finally {
      setConfirming(false);
    }
  };

  const refreshData = async () => {
    setMsg("");
    await loadAll();
    if (selectedInvoiceId) await loadLineItems(selectedInvoiceId);
  };

  return (
    <AppShell>
      <div className="h-[calc(100vh-130px)] overflow-hidden flex flex-col">
        <div className="pb-3 mb-3 border-b border-subtle flex items-end justify-between gap-3">
          <div>
            <p className="eyebrow-brand mb-2">
              <Link href="/database" className="inline-flex items-center gap-1 hover:text-brand transition-colors group">
                <ArrowLeft size={12} className="group-hover:-translate-x-0.5 transition-transform" />
                Powrot do Centrum Baz
              </Link>
            </p>
            <h1 className="text-2xl font-bold tracking-tight text-white">Faktury: Import + Review</h1>
            <p className="text-xs text-slate-400 mt-1">Jeden ekran roboczy: import, review, linked deliveries i obserwacje cen.</p>
          </div>
          <span className={`px-3 py-1 rounded-lg border text-[10px] font-black tracking-wider ${badgeClass(selectedInvoiceStatus)}`}>
            {selectedInvoiceStatus}
          </span>
        </div>

        <div className="flex-1 min-h-0 flex gap-4 overflow-hidden">
          <aside className="w-80 shrink-0 overflow-y-auto pr-1 custom-scrollbar">
            <Section title="Panel kontekstowy">
              <Card className="space-y-3">
                {activeTab === "import" && (
                  <>
                    <p className="text-[10px] uppercase tracking-wider font-black text-slate-400">Zrodla importu</p>
                    <div className="space-y-1.5">
                      <label className="text-[10px] font-black uppercase tracking-widest text-slate-500">Od daty</label>
                      <input
                        type="date"
                        value={sinceDate}
                        onChange={(e) => setSinceDate(e.target.value)}
                        className="w-full bg-canvas-deep border border-subtle rounded-lg px-2 py-1.5 text-xs"
                      />
                    </div>
                    <label className="flex items-center gap-2 text-xs text-slate-200">
                      <input type="checkbox" checked={scanLocal} onChange={(e) => setScanLocal(e.target.checked)} />
                      Foldery (Faktury, Downloads)
                    </label>
                    <label className="flex items-center gap-2 text-xs text-slate-200">
                      <input type="checkbox" checked={scanEmail} onChange={(e) => setScanEmail(e.target.checked)} />
                      Email (zalaczniki)
                    </label>
                    <p className="text-[10px] text-slate-500">
                      Limity i dodatkowe zrodla (Telegram/WhatsApp) poza zakresem tego kroku.
                    </p>
                  </>
                )}

                {activeTab === "review" && (
                  <>
                    <p className="text-[10px] uppercase tracking-wider font-black text-slate-400">Szczegoly zaznaczonej pozycji</p>
                    {!selectedLine ? (
                      <p className="text-xs text-slate-400">Wybierz pozycje z tabeli review.</p>
                    ) : (
                      <div className="space-y-2 text-xs">
                        <p><span className="text-slate-500">Line:</span> {selectedLine.line_no}</p>
                        <p><span className="text-slate-500">Nazwa:</span> {selectedLine.name_raw}</p>
                        <p><span className="text-slate-500">Ilosc:</span> {Number(selectedLine.quantity || 0).toFixed(3)} {selectedLine.unit || "-"}</p>
                        <p><span className="text-slate-500">Cena:</span> {Number(selectedLine.unit_price_gross || 0).toFixed(2)}</p>
                        <p><span className="text-slate-500">Confidence:</span> {Number(selectedLine.confidence || 0).toFixed(2)}</p>
                        <div className="pt-2 flex items-center gap-2">
                          <button
                            type="button"
                            disabled={savingLineId === selectedLine.id}
                            onClick={() => markLine(selectedLine, "confirmed")}
                            className="px-2 py-1 rounded border border-emerald-500/40 bg-emerald-500/10 hover:bg-emerald-500/20 text-xs"
                          >
                            {savingLineId === selectedLine.id ? <Loader2 size={12} className="animate-spin" /> : "Confirm"}
                          </button>
                          <button
                            type="button"
                            disabled={savingLineId === selectedLine.id}
                            onClick={() => markLine(selectedLine, "skipped")}
                            className="px-2 py-1 rounded border border-subtle bg-white/5 hover:bg-white/10 text-xs"
                          >
                            Skip
                          </button>
                        </div>
                      </div>
                    )}
                  </>
                )}

                {activeTab === "linked" && (
                  <>
                    <p className="text-[10px] uppercase tracking-wider font-black text-slate-400">Linked deliveries</p>
                    <p className="text-xs text-slate-300">Powiazane dostawy dla faktury #{selectedInvoiceId || "-"}</p>
                    <p className="text-xs text-slate-500">Wiersze: {linkedArrivals.length}</p>
                  </>
                )}

                {activeTab === "price" && (
                  <>
                    <p className="text-[10px] uppercase tracking-wider font-black text-slate-400">Obserwacje cenowe</p>
                    <p className="text-xs text-slate-300">
                      Material: {selectedMaterial ? `${selectedMaterial.name} (#${selectedMaterial.id})` : "Wybierz pozycje i material w Review"}
                    </p>
                    <p className="text-xs text-slate-500">Ostatnie wpisy: {priceHistoryRows.length}</p>
                  </>
                )}
              </Card>
            </Section>
          </aside>

          <main className="flex-1 min-h-0 flex flex-col gap-3 overflow-hidden">
            <Card className="p-3 space-y-3 shrink-0">
              <div className="flex items-center gap-2 overflow-x-auto pb-1">
                {INVOICE_TABS.map((tab) => {
                  const active = tab.key === activeTab;
                  return (
                    <button
                      key={tab.key}
                      type="button"
                      onClick={() => setActiveTab(tab.key)}
                      className={`shrink-0 px-3 py-1.5 rounded-lg text-[11px] uppercase tracking-wider font-black border transition-colors ${
                        active
                          ? "bg-emerald-600/20 border-emerald-500/60 text-emerald-300"
                          : "bg-white/5 border-subtle text-slate-300 hover:bg-white/10"
                      }`}
                    >
                      {tab.label}
                    </button>
                  );
                })}
              </div>

              <div className="flex flex-wrap items-center gap-2 border-t border-subtle pt-3">
                <label className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-subtle bg-white/5 hover:bg-white/10 cursor-pointer text-xs font-bold uppercase tracking-wider">
                  <input
                    type="file"
                    accept=".pdf,application/pdf"
                    className="hidden"
                    onChange={(e) => onUpload(e.target.files?.[0] || null)}
                    disabled={uploading}
                  />
                  {uploading ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
                  Upload PDF
                </label>

                <Button
                  onClick={checkSources}
                  disabled={scanningSources || (!scanLocal && !scanEmail)}
                  className="!px-3 !py-2 text-xs"
                >
                  {scanningSources ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
                  Check sources
                </Button>

                <Button onClick={confirmExport} disabled={!selectedInvoiceId || confirming} className="!px-3 !py-2 text-xs">
                  {confirming ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                  Confirm / Export
                </Button>

                <Button variant="ghost" onClick={refreshData} className="!px-3 !py-2 text-xs">
                  <RefreshCw size={14} />
                  Refresh
                </Button>
              </div>
            </Card>

            {msg ? (
              <Card className="p-3 shrink-0 border-emerald-500/20 bg-emerald-500/5">
                <p className="text-xs text-emerald-300">{msg}</p>
              </Card>
            ) : null}

            <Card className="p-0 border-subtle overflow-hidden flex-1 min-h-0">
              <div className="overflow-auto h-full">
                {activeTab === "import" && (
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="sticky top-0 z-20 bg-slate-950 text-slate-500 uppercase border-b border-subtle">
                        <th className="p-2">ID</th>
                        <th className="p-2">Numer</th>
                        <th className="p-2">Data</th>
                        <th className="p-2">Status</th>
                        <th className="p-2">Pozycje</th>
                      </tr>
                    </thead>
                    <tbody>
                      {loading ? (
                        <tr><td className="p-4 text-slate-400" colSpan={5}>Ladowanie...</td></tr>
                      ) : invoices.length === 0 ? (
                        <tr><td className="p-4 text-slate-400" colSpan={5}>Brak faktur.</td></tr>
                      ) : invoices.map((row) => {
                        const id = pickInvoiceId(row);
                        const active = id === selectedInvoiceId;
                        const status = normalizeInvoiceStatus(String((row as any).status || ""));
                        return (
                          <tr
                            key={`inv-${id}`}
                            onClick={() => {
                              setSelectedInvoiceId(id);
                              setActiveTab("review");
                            }}
                            className={`cursor-pointer border-t border-subtle ${active ? "bg-emerald-500/10" : "hover:bg-white/5"}`}
                          >
                            <td className="p-2">{id}</td>
                            <td className="p-2">{pickInvoiceLabel(row)}</td>
                            <td className="p-2">{String((row as any).date || "-")}</td>
                            <td className="p-2">
                              <span className={`px-2 py-1 rounded-md border text-[10px] font-black tracking-wider ${badgeClass(status)}`}>{status}</span>
                            </td>
                            <td className="p-2">{Number((row as any).line_items_total || 0)}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                )}

                {activeTab === "review" && (
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="sticky top-0 z-20 bg-slate-950 text-slate-500 uppercase border-b border-subtle">
                        <th className="p-2">Name</th>
                        <th className="p-2">Quantity</th>
                        <th className="p-2">Unit</th>
                        <th className="p-2">Price</th>
                        <th className="p-2">Confidence</th>
                        <th className="p-2">Material</th>
                        <th className="p-2">Status</th>
                        <th className="p-2">Akcja</th>
                      </tr>
                    </thead>
                    <tbody>
                      {lineItems.length === 0 ? (
                        <tr><td className="p-4 text-slate-400" colSpan={8}>Brak pozycji do review.</td></tr>
                      ) : lineItems.map((row) => {
                        const safe = canConfirmLine(row);
                        const rowActive = Number(row.id) === Number(selectedLineId);
                        return (
                          <tr
                            key={`line-${row.id}`}
                            onClick={() => setSelectedLineId(row.id)}
                            className={`border-t border-subtle ${rowActive ? "bg-emerald-500/10" : "hover:bg-white/5"} cursor-pointer`}
                          >
                            <td className="p-2">{row.name_raw}</td>
                            <td className="p-2">{Number(row.quantity || 0).toFixed(3)}</td>
                            <td className="p-2">{row.unit || "-"}</td>
                            <td className="p-2">{Number(row.unit_price_gross || 0).toFixed(2)}</td>
                            <td className="p-2">{Number(row.confidence || 0).toFixed(2)}</td>
                            <td className="p-2">
                              <select
                                className="bg-canvas-deep border border-subtle rounded px-2 py-1 text-xs"
                                value={String(pickedMaterial[row.id] || row.selected_material_id || "")}
                                onChange={(e) =>
                                  setPickedMaterial((prev) => ({ ...prev, [row.id]: Number(e.target.value || 0) }))
                                }
                              >
                                <option value="">Wybierz material...</option>
                                {materials.map((m) => (
                                  <option key={`mat-${m.id}`} value={m.id}>{m.name}</option>
                                ))}
                              </select>
                            </td>
                            <td className="p-2">
                              <span className={`px-2 py-1 rounded border text-[10px] ${
                                row.review_status === "confirmed"
                                  ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-300"
                                  : row.review_status === "skipped"
                                  ? "border-slate-500/50 bg-white/5 text-slate-300"
                                  : "border-amber-500/50 bg-amber-500/10 text-amber-300"
                              }`}>
                                {safe.ok ? row.review_status : "review_required"}
                              </span>
                            </td>
                            <td className="p-2">
                              <div className="flex items-center gap-1">
                                <button
                                  type="button"
                                  disabled={savingLineId === row.id || !safe.ok}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    markLine(row, "confirmed");
                                  }}
                                  className="px-2 py-1 rounded border border-emerald-500/40 bg-emerald-500/10 hover:bg-emerald-500/20 disabled:opacity-40"
                                  title={safe.ok ? "Potwierdz" : safe.reason}
                                >
                                  {savingLineId === row.id ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle2 size={12} />}
                                </button>
                                <button
                                  type="button"
                                  disabled={savingLineId === row.id}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    markLine(row, "skipped");
                                  }}
                                  className="px-2 py-1 rounded border border-slate-500/40 bg-white/5 hover:bg-white/10"
                                  title="Pomin"
                                >
                                  <XCircle size={12} />
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                )}

                {activeTab === "linked" && (
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="sticky top-0 z-20 bg-slate-950 text-slate-500 uppercase border-b border-subtle">
                        <th className="p-2">Data</th>
                        <th className="p-2">Material</th>
                        <th className="p-2">Ilosc</th>
                        <th className="p-2">Jednostka</th>
                        <th className="p-2">Cena brutto</th>
                        <th className="p-2">Dokument</th>
                        <th className="p-2">Link</th>
                      </tr>
                    </thead>
                    <tbody>
                      {linkedArrivals.length === 0 ? (
                        <tr><td className="p-4 text-slate-400" colSpan={7}>Brak powiazanych dostaw.</td></tr>
                      ) : linkedArrivals.map((row) => (
                        <tr key={`arr-${row.id}`} className="border-t border-subtle">
                          <td className="p-2">{row.date || "-"}</td>
                          <td className="p-2">{row.material_name || row.material_id}</td>
                          <td className="p-2">{Number(row.quantity || 0).toFixed(3)}</td>
                          <td className="p-2">{row.unit || "-"}</td>
                          <td className="p-2">{Number(row.unit_price_gross || 0).toFixed(2)}</td>
                          <td className="p-2">{row.document_nr || "-"}</td>
                          <td className="p-2 text-slate-400"><Link2 size={12} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}

                {activeTab === "price" && (
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="sticky top-0 z-20 bg-slate-950 text-slate-500 uppercase border-b border-subtle">
                        <th className="p-2">Data</th>
                        <th className="p-2">Material</th>
                        <th className="p-2">Supplier</th>
                        <th className="p-2">Unit net</th>
                        <th className="p-2">Unit gross</th>
                        <th className="p-2">Invoice</th>
                        <th className="p-2">History</th>
                      </tr>
                    </thead>
                    <tbody>
                      {priceHistoryRows.length === 0 ? (
                        <tr><td className="p-4 text-slate-400" colSpan={7}>Brak obserwacji cen dla wybranego materialu.</td></tr>
                      ) : priceHistoryRows.map((row) => (
                        <tr key={`price-${row.id}`} className="border-t border-subtle">
                          <td className="p-2">{row.date || "-"}</td>
                          <td className="p-2">{row.material_name || row.material_id}</td>
                          <td className="p-2">{row.supplier || row.wholesaler || "-"}</td>
                          <td className="p-2">{Number(row.unit_price_net || 0).toFixed(2)}</td>
                          <td className="p-2">{Number(row.unit_price_gross || 0).toFixed(2)}</td>
                          <td className="p-2">#{row.invoice_id || "-"}</td>
                          <td className="p-2 text-slate-400"><History size={12} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </Card>
          </main>
        </div>
      </div>
    </AppShell>
  );
}
