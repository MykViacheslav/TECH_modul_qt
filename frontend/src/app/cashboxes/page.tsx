"use client";

import AppShell from "@/components/AppShell";
import BusinessHealthStrip from "@/components/BusinessHealthStrip";
import { Card } from "@/components/ui";
import { TechModulAPI, type OrderRecord } from "@/services/api";
import { useSelectedProjectId } from "@/services/project-context";
import clsx from "clsx";
import { Landmark, RefreshCw } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { useEffect } from "react";

type CashboxKey =
  | "kasa_faktura_vat"
  | "kasa_paragon"
  | "kasa_gotowka"
  | "kasa_bez_dokumentu";

type PaymentPlanRow = {
  id?: string;
  stage?: string;
  amount?: number;
  paid?: boolean;
  date?: string;
  method?: string;
  cashbox?: CashboxKey;
  notes?: string;
};

type CashEntry = {
  orderId: number;
  orderTitle: string;
  clientName: string;
  cashbox: CashboxKey;
  amount: number;
  paid: boolean;
  stage: string;
  date: string;
  method: string;
  notes: string;
};

const METHOD_TO_CASHBOX: Record<string, CashboxKey> = {
  invoice_vat: "kasa_faktura_vat",
  receipt: "kasa_paragon",
  cash: "kasa_gotowka",
  no_document: "kasa_bez_dokumentu",
};

const CASHBOX_TO_METHOD: Record<CashboxKey, string> = {
  kasa_faktura_vat: "invoice_vat",
  kasa_paragon: "receipt",
  kasa_gotowka: "cash",
  kasa_bez_dokumentu: "no_document",
};

const METHOD_LABEL: Record<string, string> = {
  invoice_vat: "Faktura VAT",
  receipt: "Paragon",
  cash: "Gotowka",
  no_document: "Bez dokumentu",
};

const CASHBOX_META: Array<{ key: CashboxKey; label: string; color: string }> = [
  { key: "kasa_faktura_vat", label: "Kasa faktura VAT", color: "text-cyan-300" },
  { key: "kasa_paragon", label: "Kasa paragon", color: "text-fuchsia-300" },
  { key: "kasa_gotowka", label: "Kasa gotowka", color: "text-emerald-300" },
  { key: "kasa_bez_dokumentu", label: "Kasa bez dokumentu", color: "text-amber-300" },
];

function formatMoney(v: number): string {
  return `${(Number.isFinite(v) ? v : 0).toFixed(2)} zl`;
}

function normalizeCashEntry(row: CashEntry): CashEntry {
  const methodRaw = String(row.method || "").trim().toLowerCase();
  const methodFromCashbox = CASHBOX_TO_METHOD[row.cashbox];
  const method = METHOD_TO_CASHBOX[methodRaw] ? methodRaw : methodFromCashbox;
  const cashbox = METHOD_TO_CASHBOX[method] || row.cashbox;
  return {
    ...row,
    method,
    cashbox,
  };
}

function methodLabel(method: string): string {
  const key = String(method || "").trim().toLowerCase();
  return METHOD_LABEL[key] || (method || "-");
}

function cashboxLabel(cashbox: CashboxKey): string {
  return CASHBOX_META.find((x) => x.key === cashbox)?.label || cashbox;
}

function parsePaymentPlan(order: OrderRecord): CashEntry[] {
  try {
    if (!order.spec_json) return [];
    const parsed = JSON.parse(order.spec_json);
    const rows = Array.isArray(parsed?.payment_plan)
      ? (parsed.payment_plan as PaymentPlanRow[])
      : Array.isArray(parsed?.payments)
      ? (parsed.payments as PaymentPlanRow[])
      : [];
    return rows
      .filter((row) => row && typeof row === "object")
      .map((row) => ({
        orderId: Number(order.id),
        orderTitle: String(order.title || `Zamowienie #${order.id}`),
        clientName: String(order.client_name || "-"),
        cashbox: (row.cashbox || "kasa_faktura_vat") as CashboxKey,
        amount: Number(row.amount || 0),
        paid: Boolean(row.paid),
        stage: String(row.stage || "Etap"),
        date: String(row.date || ""),
        method: String(row.method || ""),
        notes: String(row.notes || ""),
      }));
  } catch {
    return [];
  }
}

function parseDraftPayments(projectId: number): CashEntry[] {
  if (typeof window === "undefined") return [];
  const keys = [
    `techmodul_order_draft_${projectId}`,
    `techmodul_services_draft_${projectId}`,
  ];
  const out: CashEntry[] = [];

  for (const key of keys) {
    try {
      const raw = window.localStorage.getItem(key);
      if (!raw) continue;
      const parsed = JSON.parse(raw);
      const rows = Array.isArray(parsed?.payments)
        ? (parsed.payments as PaymentPlanRow[])
        : Array.isArray(parsed?.payment_plan)
        ? (parsed.payment_plan as PaymentPlanRow[])
        : [];
      const orderTitle = String(parsed?.form?.orderTitle || "Wersja robocza");
      const clientName = String(parsed?.form?.clientName || parsed?.form?.clientCompanyName || "-");

      for (const row of rows) {
        out.push({
          orderId: 0,
          orderTitle,
          clientName,
          cashbox: (row.cashbox || "kasa_faktura_vat") as CashboxKey,
          amount: Number(row.amount || 0),
          paid: Boolean(row.paid),
          stage: String(row.stage || "Etap"),
          date: String(row.date || ""),
          method: String(row.method || ""),
          notes: String(row.notes || ""),
        });
      }
    } catch {
      // ignore malformed draft
    }
  }
  return out;
}

export default function CashboxesPage() {
  const [projectId] = useSelectedProjectId(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [entries, setEntries] = useState<CashEntry[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const orders = await TechModulAPI.getOrders(projectId);
      const fromOrders = (orders || []).flatMap((order) => parsePaymentPlan(order));
      const fromDraft = parseDraftPayments(projectId);
      const dedup = new Map<string, CashEntry>();
      for (const rowRaw of [...fromOrders, ...fromDraft]) {
        const row = normalizeCashEntry(rowRaw);
        if (!(row.amount > 0)) continue;
        const key = [
          row.orderId,
          row.orderTitle.trim().toLowerCase(),
          row.clientName.trim().toLowerCase(),
          row.cashbox,
          row.stage.trim().toLowerCase(),
          Number(row.amount || 0).toFixed(2),
          row.date,
          row.method.trim().toLowerCase(),
          row.paid ? "1" : "0",
        ].join("::");
        dedup.set(key, row);
      }
      const next = Array.from(dedup.values());
      setEntries(next);
    } catch (e: any) {
      setError(e?.message || "Nie udalo sie pobrac danych kas");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    load();
  }, [load]);

  const byCashbox = useMemo(() => {
    const initial: Record<CashboxKey, { total: number; paid: number; pending: number; rows: number }> = {
      kasa_faktura_vat: { total: 0, paid: 0, pending: 0, rows: 0 },
      kasa_paragon: { total: 0, paid: 0, pending: 0, rows: 0 },
      kasa_gotowka: { total: 0, paid: 0, pending: 0, rows: 0 },
      kasa_bez_dokumentu: { total: 0, paid: 0, pending: 0, rows: 0 },
    };
    for (const row of entries) {
      const bucket = initial[row.cashbox] ?? initial.kasa_faktura_vat;
      bucket.rows += 1;
      bucket.total += row.amount;
      if (row.paid) bucket.paid += row.amount;
      else bucket.pending += row.amount;
    }
    return initial;
  }, [entries]);

  const totals = useMemo(() => {
    return entries.reduce(
      (acc, row) => {
        acc.total += row.amount;
        if (row.paid) acc.paid += row.amount;
        else acc.pending += row.amount;
        return acc;
      },
      { total: 0, paid: 0, pending: 0 }
    );
  }, [entries]);

  return (
    <AppShell>
      <div className="flex h-full flex-col gap-4 overflow-auto text-slate-100">
        <BusinessHealthStrip
          scope="Kasa i platnosci"
          subtitle="Szybka ocena gotowki, marzy i tego, czy firma dowozi pieniadz w terminie."
        />
        <Card className="border-[#333] bg-[#1e1e1e] p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-[20px] font-black uppercase tracking-wide">Kasy</div>
              <div className="text-[12px] text-slate-400">
                Projekt #{projectId} - podglad 4 kas z planu platnosci w zamowieniach.
              </div>
            </div>
            <button
              onClick={load}
              className="inline-flex items-center gap-2 rounded border border-[#38507a] bg-[#1f2a3f] px-3 py-2 text-[11px] font-bold uppercase tracking-wider hover:bg-[#223152]"
            >
              <RefreshCw className={clsx("h-4 w-4", loading && "animate-spin")} />
              Odswiez
            </button>
          </div>
          {error ? <div className="mt-3 text-[12px] text-red-300">{error}</div> : null}
        </Card>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          {CASHBOX_META.map((box) => {
            const stats = byCashbox[box.key];
            return (
              <Card key={box.key} className="border-[#2b3d5c] bg-[#111827] p-4">
                <div className="mb-3 flex items-center gap-2">
                  <Landmark className="h-4 w-4 text-blue-300" />
                  <div className={clsx("text-[12px] font-black uppercase tracking-wider", box.color)}>
                    {box.label}
                  </div>
                </div>
                <div className="space-y-1 text-[12px]">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Pozycji</span>
                    <span className="font-bold text-slate-200">{stats.rows}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Suma</span>
                    <span className="font-bold text-white">{formatMoney(stats.total)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Oplacone</span>
                    <span className="font-bold text-emerald-300">{formatMoney(stats.paid)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Do zaplaty</span>
                    <span className="font-bold text-amber-300">{formatMoney(stats.pending)}</span>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>

        <Card className="border-[#333] bg-[#1e1e1e] p-4">
          <div className="mb-3 text-[13px] font-black uppercase tracking-wider">Wszystkie ruchy kasowe</div>
          <div className="mb-2 grid grid-cols-1 gap-2 text-[12px] md:grid-cols-3">
            <div className="rounded border border-[#33445f] bg-[#111827] px-3 py-2">
              <span className="text-slate-400">Suma calkowita: </span>
              <span className="font-bold text-white">{formatMoney(totals.total)}</span>
            </div>
            <div className="rounded border border-[#33445f] bg-[#111827] px-3 py-2">
              <span className="text-slate-400">Suma oplacona: </span>
              <span className="font-bold text-emerald-300">{formatMoney(totals.paid)}</span>
            </div>
            <div className="rounded border border-[#33445f] bg-[#111827] px-3 py-2">
              <span className="text-slate-400">Suma oczekuje: </span>
              <span className="font-bold text-amber-300">{formatMoney(totals.pending)}</span>
            </div>
          </div>
          <div className="overflow-x-auto rounded border border-[#33445f]">
            <table className="w-full min-w-[980px] border-collapse text-[12px]">
              <thead className="bg-[#bcc8da] text-[#0b1c39]">
                <tr>
                  <th className="px-2 py-2 text-left">Kasa</th>
                  <th className="px-2 py-2 text-left">Zamowienie</th>
                  <th className="px-2 py-2 text-left">Klient</th>
                  <th className="px-2 py-2 text-left">Etap</th>
                  <th className="px-2 py-2 text-left">Kwota</th>
                  <th className="px-2 py-2 text-left">Status</th>
                  <th className="px-2 py-2 text-left">Data</th>
                  <th className="px-2 py-2 text-left">Metoda</th>
                  <th className="px-2 py-2 text-left">Uwagi</th>
                </tr>
              </thead>
              <tbody>
                {entries.length === 0 ? (
                  <tr>
                    <td className="px-2 py-5 text-center text-slate-400" colSpan={9}>
                      {loading ? "Ladowanie..." : "Brak danych platnosci w zamowieniach."}
                    </td>
                  </tr>
                ) : (
                  entries.map((row, idx) => (
                    <tr key={`${row.orderId}-${row.stage}-${idx}`} className="border-t border-[#243248]">
                      <td className="px-2 py-2">{cashboxLabel(row.cashbox)}</td>
                      <td className="px-2 py-2">
                        {row.orderId > 0 ? `#${row.orderId} - ${row.orderTitle}` : `${row.orderTitle} (draft)`}
                      </td>
                      <td className="px-2 py-2">{row.clientName}</td>
                      <td className="px-2 py-2">{row.stage}</td>
                      <td className="px-2 py-2">{formatMoney(row.amount)}</td>
                      <td className="px-2 py-2">
                        <span className={row.paid ? "text-emerald-300" : "text-amber-300"}>
                          {row.paid ? "Oplacone" : "Do zaplaty"}
                        </span>
                      </td>
                      <td className="px-2 py-2">{row.date || "-"}</td>
                      <td className="px-2 py-2">{methodLabel(row.method)}</td>
                      <td className="px-2 py-2">{row.notes || "-"}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </AppShell>
  );
}
