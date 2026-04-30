"use client";

import { useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Button, Card } from "@/components/ui";
import { TechModulAPI, type InventoryMovement } from "@/services/api";
import { ArrowLeftRight, RefreshCw } from "lucide-react";

const TYPE_COLORS: Record<string, string> = {
  IN: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  OUT: "bg-red-500/15 text-red-300 border-red-500/30",
  RESERVED: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  RETURN: "bg-blue-500/15 text-blue-300 border-blue-500/30",
  SCRAP: "bg-rose-500/15 text-rose-300 border-rose-500/30",
  CORRECTION: "bg-purple-500/15 text-purple-300 border-purple-500/30",
};

const TYPE_LABELS: Record<string, string> = {
  IN: "Przyjecie",
  OUT: "Wydanie",
  RESERVED: "Rezerwacja",
  RETURN: "Zwrot",
  SCRAP: "Brak/odpad",
  CORRECTION: "Korekta",
};

export default function InventoryMovementsPage() {
  const [movements, setMovements] = useState<InventoryMovement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState("all");
  const [materialFilter, setMaterialFilter] = useState("");
  const [orderFilter, setOrderFilter] = useState("");

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const opts: { material_id?: number; order_id?: number; limit?: number } = { limit: 1000 };
      if (materialFilter) opts.material_id = Number(materialFilter);
      if (orderFilter) opts.order_id = Number(orderFilter);
      const data = await TechModulAPI.getInventoryMovements(opts);
      setMovements(data ?? []);
    } catch (e: any) {
      setError(e?.message ?? "Blad ladowania ruchow magazynowych");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filtered = useMemo(() => {
    if (typeFilter === "all") return movements;
    return movements.filter((m) => m.movement_type === typeFilter);
  }, [movements, typeFilter]);

  return (
    <AppShell>
      <PageHeader
        eyebrow="Magazyn"
        title="Historia ruchow"
        subtitle="Wszystkie ruchy magazynowe: przyjecia, wydania, rezerwacje, zwroty, braki, korekty."
        actions={
          <div className="flex gap-2">
            <Button as="link" href="/inventory" variant="secondary">Stany</Button>
            <Button as="link" href="/inventory/actions" variant="secondary">Akcje</Button>
            <Button onClick={loadData} disabled={loading}>
              <RefreshCw className={`w-4 h-4 mr-1 ${loading ? "animate-spin" : ""}`} />
              Odswiez
            </Button>
          </div>
        }
      />

      <div className="max-w-7xl mx-auto space-y-4 pb-10">
        <Card className="p-4">
          <div className="flex flex-wrap gap-3 items-end">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Material ID</label>
              <input
                type="number"
                placeholder="Wszystkie"
                value={materialFilter}
                onChange={(e) => setMaterialFilter(e.target.value)}
                className="bg-black/20 border border-white/10 rounded px-3 py-2 text-sm w-28 outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Zamowienie ID</label>
              <input
                type="number"
                placeholder="Wszystkie"
                value={orderFilter}
                onChange={(e) => setOrderFilter(e.target.value)}
                className="bg-black/20 border border-white/10 rounded px-3 py-2 text-sm w-28 outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Typ ruchu</label>
              <select
                className="bg-black/20 border border-white/10 rounded px-3 py-2 text-sm"
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
              >
                <option value="all">Wszystkie</option>
                <option value="IN">Przyjecie (IN)</option>
                <option value="OUT">Wydanie (OUT)</option>
                <option value="RESERVED">Rezerwacja</option>
                <option value="RETURN">Zwrot</option>
                <option value="SCRAP">Brak/odpad</option>
                <option value="CORRECTION">Korekta</option>
              </select>
            </div>
            <Button onClick={loadData} variant="secondary" disabled={loading}>
              Filtruj
            </Button>
          </div>
        </Card>

        <Card padded={false}>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-200/90 text-slate-900">
                <tr>
                  <th className="text-left px-3 py-2">ID</th>
                  <th className="text-left px-3 py-2">Typ</th>
                  <th className="text-left px-3 py-2">Material</th>
                  <th className="text-right px-3 py-2">Ilosc</th>
                  <th className="text-left px-3 py-2">Jedn.</th>
                  <th className="text-right px-3 py-2">Koszt jedn.</th>
                  <th className="text-right px-3 py-2">Koszt calkowity</th>
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
                      Ladowanie ruchow...
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
                      Brak ruchow do wyswietlenia.
                    </td>
                  </tr>
                ) : (
                  filtered.map((m) => {
                    const style = TYPE_COLORS[m.movement_type] ?? "bg-slate-500/15 text-slate-300 border-slate-500/30";
                    return (
                      <tr key={m.id} className="hover:bg-white/5">
                        <td className="px-3 py-2 font-mono text-slate-400">{m.id}</td>
                        <td className="px-3 py-2">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs font-semibold ${style}`}>
                            <ArrowLeftRight className="w-3 h-3" />
                            {TYPE_LABELS[m.movement_type] ?? m.movement_type}
                          </span>
                        </td>
                        <td className="px-3 py-2">
                          <div className="flex flex-col">
                            <span className="text-slate-200">{m.material_name || `#${m.material_id ?? m.catalog_item_id ?? "-"}`}</span>
                            <div className="flex items-center gap-2 mt-0.5">
                              {m.material_name && <span className="text-[10px] text-slate-500 font-mono">ID: {m.material_id}</span>}
                              {m.purchase_document_id && (
                                <span className="text-[9px] bg-blue-500/10 text-blue-400 border border-blue-500/20 px-1 rounded">
                                  Doc: #{m.purchase_document_id}
                                </span>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="px-3 py-2 text-right text-white font-semibold">{m.qty}</td>
                        <td className="px-3 py-2 text-slate-300">{m.unit}</td>
                        <td className="px-3 py-2 text-right text-slate-300">{m.unit_cost_net != null ? m.unit_cost_net.toFixed(2) : "-"}</td>
                        <td className="px-3 py-2 text-right text-slate-300">{m.total_cost_net != null ? m.total_cost_net.toFixed(2) : "-"}</td>
                        <td className="px-3 py-2">
                          {m.order_title ? (
                            <div>
                              <div className="text-slate-200 text-xs font-semibold">{m.order_title}</div>
                              <div className="text-[10px] text-slate-500 uppercase tracking-tighter">{m.order_client_name || "Brak klienta"}</div>
                              <div className="text-[9px] text-slate-600 font-mono">#{m.order_id}</div>
                            </div>
                          ) : (
                            <span className="text-slate-500">-</span>
                          )}
                        </td>
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
