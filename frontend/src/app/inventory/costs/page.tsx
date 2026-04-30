"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Button, Card, StatCard } from "@/components/ui";
import { TechModulAPI, type OrderCostEntry, type OrderCostSummary } from "@/services/api";
import { DollarSign, RefreshCw, Search } from "lucide-react";

const COST_TYPE_LABELS: Record<string, string> = {
  MATERIAL: "Material",
  LABOR: "Robocizna",
  SERVICE: "Usluga",
  TRANSPORT: "Transport",
  INSTALLATION: "Montaz",
  OTHER_DIRECT: "Inny bezposredni",
};

const COST_TYPE_COLORS: Record<string, string> = {
  MATERIAL: "bg-blue-500/15 text-blue-300 border-blue-500/30",
  LABOR: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  SERVICE: "bg-purple-500/15 text-purple-300 border-purple-500/30",
  TRANSPORT: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  INSTALLATION: "bg-cyan-500/15 text-cyan-300 border-cyan-500/30",
  OTHER_DIRECT: "bg-slate-500/15 text-slate-300 border-slate-500/30",
};

export default function InventoryCostsPage() {
  const [orderId, setOrderId] = useState("");
  const [entries, setEntries] = useState<OrderCostEntry[]>([]);
  const [summary, setSummary] = useState<OrderCostSummary>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const loadData = async () => {
    const oid = Number(orderId);
    if (!oid || oid <= 0) {
      setError("Podaj prawidlowe ID zamowienia");
      return;
    }
    setLoading(true);
    setError(null);
    setSearched(true);
    try {
      const data = await TechModulAPI.getOrderCosts(oid);
      setEntries(data.entries ?? []);
      setSummary(data.summary ?? {});
    } catch (e: any) {
      setError(e?.message ?? "Blad ladowania kosztow zamowienia");
      setEntries([]);
      setSummary({});
    } finally {
      setLoading(false);
    }
  };

  const totalNet = entries.reduce((s, e) => s + (e.amount_net ?? 0), 0);
  const totalGross = entries.reduce((s, e) => s + (e.amount_gross ?? 0), 0);

  return (
    <AppShell>
      <PageHeader
        eyebrow="Magazyn"
        title="Koszty zamowien"
        subtitle="Realne koszty materialowe i bezposrednie przypisane do zamowien."
        actions={
          <div className="flex gap-2">
            <Button as="link" href="/inventory" variant="secondary">Stany</Button>
            <Button as="link" href="/inventory/movements" variant="secondary">Ruchy</Button>
            <Button as="link" href="/inventory/actions" variant="secondary">Akcje</Button>
          </div>
        }
      />

      <div className="max-w-6xl mx-auto space-y-4 pb-10">
        <Card className="p-4">
          <div className="flex flex-wrap gap-3 items-end">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Zamowienie ID *</label>
              <input
                type="number"
                placeholder="np. 1"
                value={orderId}
                onChange={(e) => setOrderId(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && loadData()}
                className="bg-black/20 border border-white/10 rounded px-3 py-2 text-sm w-32 outline-none focus:border-blue-500"
              />
            </div>
            <Button onClick={loadData} disabled={loading}>
              <Search className="w-4 h-4 mr-1" />
              Pokaz koszty
            </Button>
            {searched && (
              <Button onClick={loadData} variant="ghost" disabled={loading}>
                <RefreshCw className={`w-4 h-4 mr-1 ${loading ? "animate-spin" : ""}`} />
                Odswiez
              </Button>
            )}
          </div>
        </Card>

        {searched && !loading && !error && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <StatCard label="Pozycji kosztowych" value={entries.length} icon={<DollarSign className="w-5 h-5" />} />
              <StatCard label="Suma netto" value={`${totalNet.toFixed(2)} PLN`} tone="brand" />
              <StatCard label="Suma brutto" value={`${totalGross.toFixed(2)} PLN`} />
            </div>

            {Object.keys(summary).length > 0 && (
              <Card className="p-4">
                <p className="text-xs uppercase tracking-wide text-slate-400 mb-3">Podsumowanie wg typu</p>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
                  {Object.entries(summary).map(([key, val]) => (
                    <div key={key} className="bg-white/5 rounded p-3 text-center">
                      <p className="text-xs text-slate-400">{COST_TYPE_LABELS[key] ?? key}</p>
                      <p className="text-lg font-semibold text-white mt-1">{Number(val).toFixed(2)}</p>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </>
        )}

        {error && (
          <Card className="p-4">
            <p className="text-red-300 text-sm">{error}</p>
          </Card>
        )}

        {searched && (
          <Card padded={false}>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-200/90 text-slate-900">
                  <tr>
                    <th className="text-left px-3 py-2">ID</th>
                    <th className="text-left px-3 py-2">Typ kosztu</th>
                    <th className="text-left px-3 py-2">Zrodlo</th>
                    <th className="text-right px-3 py-2">Netto</th>
                    <th className="text-right px-3 py-2">VAT %</th>
                    <th className="text-right px-3 py-2">Brutto</th>
                    <th className="text-right px-3 py-2">Ilosc</th>
                    <th className="text-left px-3 py-2">Opis</th>
                    <th className="text-left px-3 py-2">Data</th>
                    <th className="text-left px-3 py-2">Kto</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/10">
                  {loading ? (
                    <tr>
                      <td colSpan={10} className="px-3 py-8 text-center text-slate-400">
                        Ladowanie kosztow...
                      </td>
                    </tr>
                  ) : entries.length === 0 ? (
                    <tr>
                      <td colSpan={10} className="px-3 py-8 text-center text-slate-500">
                        Brak pozycji kosztowych dla tego zamowienia.
                      </td>
                    </tr>
                  ) : (
                    entries.map((e) => {
                      const style = COST_TYPE_COLORS[e.cost_type] ?? COST_TYPE_COLORS.OTHER_DIRECT;
                      return (
                        <tr key={e.id} className={`hover:bg-white/5 ${e.amount_net < 0 ? "bg-red-500/5" : ""}`}>
                          <td className="px-3 py-2 font-mono text-slate-400">{e.id}</td>
                          <td className="px-3 py-2">
                            <span className={`inline-flex px-2 py-0.5 rounded border text-xs font-semibold ${style}`}>
                              {COST_TYPE_LABELS[e.cost_type] ?? e.cost_type}
                            </span>
                          </td>
                          <td className="px-3 py-2 text-slate-300 text-xs">{e.source_type || "-"}</td>
                          <td className={`px-3 py-2 text-right font-semibold ${e.amount_net < 0 ? "text-red-300" : "text-white"}`}>
                            {e.amount_net.toFixed(2)}
                          </td>
                          <td className="px-3 py-2 text-right text-slate-400">{e.vat_rate}%</td>
                          <td className="px-3 py-2 text-right text-slate-300">{e.amount_gross.toFixed(2)}</td>
                          <td className="px-3 py-2 text-right text-slate-300">{e.qty != null ? e.qty : "-"}</td>
                          <td className="px-3 py-2 text-slate-400 text-xs max-w-[200px] truncate">{e.description || "-"}</td>
                          <td className="px-3 py-2 text-slate-400 text-xs whitespace-nowrap">{e.created_at || "-"}</td>
                          <td className="px-3 py-2 text-slate-400 text-xs">{e.created_by || "-"}</td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </div>
    </AppShell>
  );
}
