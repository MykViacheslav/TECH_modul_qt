"use client";

import { useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Button, Card, StatCard } from "@/components/ui";
import { TechModulAPI, type CashBankMovement } from "@/services/api";
import { ArrowDownRight, ArrowUpRight, Banknote, RefreshCw, Search } from "lucide-react";

const TYPE_STYLES: Record<string, string> = {
  CASH_OUT: "bg-red-500/15 text-red-300 border-red-500/30",
  BANK_OUT: "bg-red-500/15 text-red-300 border-red-500/30",
  CASH_IN: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  BANK_IN: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  PAYABLE: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  SETTLED: "bg-blue-500/15 text-blue-300 border-blue-500/30",
  REFUND: "bg-purple-500/15 text-purple-300 border-purple-500/30",
};

const TYPE_LABELS: Record<string, string> = {
  CASH_OUT: "Gotowka - wyjscie",
  BANK_OUT: "Przelew - wyjscie",
  CASH_IN: "Gotowka - wejscie",
  BANK_IN: "Przelew - wejscie",
  PAYABLE: "Zobowiazanie",
  SETTLED: "Rozliczone",
  REFUND: "Zwrot",
};

const OUTGOING_TYPES = new Set(["CASH_OUT", "BANK_OUT"]);
const PAYABLE_TYPES = new Set(["PAYABLE"]);
const SETTLED_TYPES = new Set(["SETTLED"]);

export default function PaymentsPage() {
  const [movements, setMovements] = useState<CashBankMovement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [docFilter, setDocFilter] = useState("");

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await TechModulAPI.getCashBankMovements(1000);
      setMovements(data ?? []);
    } catch (e: any) {
      setError(e?.message ?? "Blad ladowania ruchow finansowych");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filtered = useMemo(() => {
    return movements.filter((m) => {
      if (typeFilter !== "all" && m.movement_type !== typeFilter) return false;
      if (docFilter && m.purchase_document_id !== Number(docFilter)) return false;
      if (search) {
        const q = search.toLowerCase();
        if (
          !(m.supplier_name || "").toLowerCase().includes(q) &&
          !(m.note || "").toLowerCase().includes(q) &&
          !String(m.id).includes(q)
        )
          return false;
      }
      return true;
    });
  }, [movements, typeFilter, search, docFilter]);

  const totalOutgoing = filtered
    .filter((m) => OUTGOING_TYPES.has(m.movement_type))
    .reduce((s, m) => s + m.amount, 0);
  const totalPayable = filtered
    .filter((m) => PAYABLE_TYPES.has(m.movement_type))
    .reduce((s, m) => s + m.amount, 0);
  const totalSettled = filtered
    .filter((m) => SETTLED_TYPES.has(m.movement_type))
    .reduce((s, m) => s + m.amount, 0);

  return (
    <AppShell>
      <PageHeader
        eyebrow="Magazyn"
        title="Platnosci dostawcow"
        subtitle="Ruchy kasowe i bankowe zwiazane z zakupami materialow."
        actions={
          <div className="flex gap-2">
            <Button as="link" href="/inventory" variant="secondary">Stany</Button>
            <Button as="link" href="/inventory/purchases" variant="secondary">Zakupy</Button>
            <Button onClick={loadData} variant="secondary" disabled={loading}>
              <RefreshCw className={`w-4 h-4 mr-1 ${loading ? "animate-spin" : ""}`} />
              Odswiez
            </Button>
          </div>
        }
      />

      <div className="max-w-7xl mx-auto space-y-4 pb-10">
        {/* Summary stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <StatCard label="Ruchow" value={filtered.length} icon={<Banknote className="w-5 h-5" />} />
          <StatCard
            label="Wydatki (gotowka + bank)"
            value={`${totalOutgoing.toFixed(2)} PLN`}
            tone="warn"
            icon={<ArrowDownRight className="w-5 h-5" />}
          />
          <StatCard
            label="Zobowiazania (payable)"
            value={`${totalPayable.toFixed(2)} PLN`}
            tone="warn"
          />
          <StatCard
            label="Rozliczone"
            value={`${totalSettled.toFixed(2)} PLN`}
            tone="success"
            icon={<ArrowUpRight className="w-5 h-5" />}
          />
        </div>

        {/* Filters */}
        <Card className="p-4">
          <div className="flex flex-wrap gap-3 items-end">
            <div className="flex-1 min-w-[200px] relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                placeholder="Szukaj po dostawcy, notatce..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-black/20 border border-white/10 rounded px-3 py-2 pl-9 text-sm text-slate-200 outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Typ ruchu</label>
              <select
                className="bg-black/20 border border-white/10 rounded px-3 py-2 text-sm"
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
              >
                <option value="all">Wszystkie typy</option>
                <option value="CASH_OUT">Gotowka - wyjscie</option>
                <option value="BANK_OUT">Przelew - wyjscie</option>
                <option value="CASH_IN">Gotowka - wejscie</option>
                <option value="BANK_IN">Przelew - wejscie</option>
                <option value="PAYABLE">Zobowiazanie</option>
                <option value="SETTLED">Rozliczone</option>
                <option value="REFUND">Zwrot</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Dokument zakupu ID</label>
              <input
                type="number"
                placeholder="Wszystkie"
                value={docFilter}
                onChange={(e) => setDocFilter(e.target.value)}
                className="bg-black/20 border border-white/10 rounded px-3 py-2 text-sm w-28 outline-none focus:border-blue-500"
              />
            </div>
          </div>
        </Card>

        {/* Table */}
        <Card padded={false}>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-200/90 text-slate-900">
                <tr>
                  <th className="text-left px-3 py-2">ID</th>
                  <th className="text-left px-3 py-2">Typ</th>
                  <th className="text-right px-3 py-2">Kwota</th>
                  <th className="text-left px-3 py-2">Waluta</th>
                  <th className="text-left px-3 py-2">Metoda</th>
                  <th className="text-left px-3 py-2">Dostawca</th>
                  <th className="text-left px-3 py-2">Dok. zakupu</th>
                  <th className="text-left px-3 py-2">Zamowienie</th>
                  <th className="text-left px-3 py-2">Notatka</th>
                  <th className="text-left px-3 py-2">Data</th>
                  <th className="text-left px-3 py-2">Kto</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10">
                {loading ? (
                  <tr>
                    <td colSpan={11} className="px-3 py-8 text-center text-slate-400">
                      Ladowanie ruchow finansowych...
                    </td>
                  </tr>
                ) : error ? (
                  <tr>
                    <td colSpan={11} className="px-3 py-8 text-center text-red-300">
                      {error}
                    </td>
                  </tr>
                ) : filtered.length === 0 ? (
                  <tr>
                    <td colSpan={11} className="px-3 py-8 text-center text-slate-500">
                      Brak ruchow finansowych do wyswietlenia.
                    </td>
                  </tr>
                ) : (
                  filtered.map((m) => {
                    const style = TYPE_STYLES[m.movement_type] ?? "bg-slate-500/15 text-slate-300 border-slate-500/30";
                    const isOutgoing = OUTGOING_TYPES.has(m.movement_type);
                    return (
                      <tr key={m.id} className="hover:bg-white/5">
                        <td className="px-3 py-2 font-mono text-slate-400">{m.id}</td>
                        <td className="px-3 py-2">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs font-semibold ${style}`}>
                            {isOutgoing ? <ArrowDownRight className="w-3 h-3" /> : <ArrowUpRight className="w-3 h-3" />}
                            {TYPE_LABELS[m.movement_type] ?? m.movement_type}
                          </span>
                        </td>
                        <td className={`px-3 py-2 text-right font-semibold ${isOutgoing ? "text-red-300" : "text-white"}`}>
                          {m.amount.toFixed(2)}
                        </td>
                        <td className="px-3 py-2 text-slate-300">{m.currency}</td>
                        <td className="px-3 py-2 text-slate-300">{m.payment_method || "-"}</td>
                        <td className="px-3 py-2 text-slate-200">{m.supplier_name || "-"}</td>
                        <td className="px-3 py-2 text-slate-300 font-mono">{m.purchase_document_id ?? "-"}</td>
                        <td className="px-3 py-2 text-slate-300">{m.order_id ?? "-"}</td>
                        <td className="px-3 py-2 text-slate-400 text-xs max-w-[200px] truncate">{m.note || "-"}</td>
                        <td className="px-3 py-2 text-slate-400 text-xs whitespace-nowrap">{m.created_at || "-"}</td>
                        <td className="px-3 py-2 text-slate-400 text-xs">{m.created_by || "-"}</td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </Card>

        <div className="text-xs text-slate-500 text-right">
          Wyswietlono {filtered.length} z {movements.length} ruchow
        </div>
      </div>
    </AppShell>
  );
}
