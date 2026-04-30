"use client";

import { useEffect, useMemo, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import AppShell from "@/components/AppShell";
import BusinessHealthStrip from "@/components/BusinessHealthStrip";
import PageHeader from "@/components/PageHeader";
import { Button, Card, StatCard, Section } from "@/components/ui";
import { TechModulAPI, type InventoryBalance, type InventoryMovement } from "@/services/api";
import { Package, RefreshCw, Search, History } from "lucide-react";
import TraceabilityTimeline from "@/components/TraceabilityTimeline";

export default function InventoryBalancesPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <InventoryBalancesContent />
    </Suspense>
  );
}

function InventoryBalancesContent() {
  const searchParams = useSearchParams();
  const initialSearch = searchParams.get("search") || "";
  
  const [balances, setBalances] = useState<InventoryBalance[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState(initialSearch);
  const [locationFilter, setLocationFilter] = useState("all");

  // State for side panel
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [selectedMaterialId, setSelectedMaterialId] = useState<number | null>(null);
  const [selectedMaterialName, setSelectedMaterialName] = useState("");
  const [selectedMaterialMovements, setSelectedMaterialMovements] = useState<InventoryMovement[]>([]);
  const [loadingMovements, setLoadingMovements] = useState(false);

  // Fetch movements when material is selected
  useEffect(() => {
    if (selectedMaterialId && isPanelOpen) {
      const fetchMovements = async () => {
        setLoadingMovements(true);
        try {
          const data = await TechModulAPI.getInventoryMovements({ material_id: selectedMaterialId });
          setSelectedMaterialMovements(data);
        } catch (e) {
          console.error("Failed to fetch movements", e);
        } finally {
          setLoadingMovements(false);
        }
      };
      fetchMovements();
    }
  }, [selectedMaterialId, isPanelOpen]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await TechModulAPI.getInventoryBalances(1000);
      setBalances(data ?? []);
    } catch (e: any) {
      setError(e?.message ?? "Blad ladowania stanow magazynowych");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const locations = useMemo(() => {
    const set = new Set(balances.map((b) => b.location || "brak"));
    return Array.from(set).sort();
  }, [balances]);

  const filtered = useMemo(() => {
    return balances.filter((b) => {
      if (locationFilter !== "all" && (b.location || "brak") !== locationFilter) return false;
      if (search) {
        const q = search.toLowerCase();
        const id = String(b.material_id);
        const name = (b.material_name || "").toLowerCase();
        if (!id.includes(q) && !name.includes(q) && !(b.location || "").toLowerCase().includes(q)) return false;
      }
      return true;
    });
  }, [balances, search, locationFilter]);

  const totalOnHand = filtered.reduce((s, b) => s + (b.qty_on_hand ?? 0), 0);
  const totalReserved = filtered.reduce((s, b) => s + (b.qty_reserved ?? 0), 0);
  const totalAvailable = filtered.reduce((s, b) => s + (b.qty_available ?? 0), 0);

  return (
    <AppShell>
      <PageHeader
        eyebrow="Magazyn"
        title="Stany magazynowe"
        subtitle="Biezace stany, rezerwacje i dostepnosc materialow."
        actions={
          <div className="flex gap-2">
            <Button as="link" href="/inventory/purchases" variant="secondary">Zakupy</Button>
            <Button as="link" href="/inventory/payments" variant="secondary">Platnosci</Button>
            <Button as="link" href="/inventory/movements" variant="secondary">Ruchy</Button>
            <Button as="link" href="/inventory/actions" variant="secondary">Akcje</Button>
            <Button as="link" href="/inventory/costs" variant="secondary">Koszty</Button>
            <Button onClick={loadData} disabled={loading}>
              <RefreshCw className={`w-4 h-4 mr-1 ${loading ? "animate-spin" : ""}`} />
              Odswiez
            </Button>
          </div>
        }
      />

      <div className="max-w-7xl mx-auto space-y-4 pb-10">
        <BusinessHealthStrip
          scope="Magazyn i materialy"
          subtitle="Wartosc zapasu, niskie stany i to, jak magazyn wspiera realna produkcje."
        />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <StatCard label="Pozycji" value={filtered.length} icon={<Package className="w-5 h-5" />} />
          <StatCard label="Na stanie (suma)" value={totalOnHand.toFixed(2)} />
          <StatCard label="Zarezerwowane" value={totalReserved.toFixed(2)} tone="warn" />
          <StatCard label="Dostepne" value={totalAvailable.toFixed(2)} tone="success" />
        </div>

        <Card className="p-4">
          <div className="flex flex-wrap gap-3 items-center">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                placeholder="Szukaj po nazwie, ID materialu lub lokalizacji..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-black/20 border border-white/10 rounded px-3 py-2 pl-9 text-sm text-slate-200 outline-none focus:border-blue-500"
              />
            </div>
            <select
              className="bg-black/20 border border-white/10 rounded px-3 py-2 text-sm"
              value={locationFilter}
              onChange={(e) => setLocationFilter(e.target.value)}
            >
              <option value="all">Wszystkie lokalizacje</option>
              {locations.map((loc) => (
                <option key={loc} value={loc}>{loc}</option>
              ))}
            </select>
          </div>
        </Card>

        <Card padded={false}>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-200/90 text-slate-900">
                <tr>
                  <th className="text-left px-3 py-2">Material</th>
                  <th className="text-left px-3 py-2">Jedn.</th>
                  <th className="text-left px-3 py-2">Lokalizacja</th>
                  <th className="text-right px-3 py-2">Na stanie</th>
                  <th className="text-right px-3 py-2">Zarezerwowane</th>
                  <th className="text-right px-3 py-2">Dostepne</th>
                  <th className="text-left px-3 py-2">Aktualizacja</th>
                  <th className="text-right px-3 py-2">Akcje</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="px-3 py-8 text-center text-slate-400">
                      Ladowanie stanow magazynowych...
                    </td>
                  </tr>
                ) : error ? (
                  <tr>
                    <td colSpan={7} className="px-3 py-8 text-center text-red-300">
                      {error}
                    </td>
                  </tr>
                ) : filtered.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-3 py-8 text-center text-slate-500">
                      Brak pozycji magazynowych.
                    </td>
                  </tr>
                ) : (
                  filtered.map((b, idx) => (
                    <tr key={`${b.material_id}-${b.location}-${idx}`} className="hover:bg-white/5">
                      <td className="px-3 py-2">
                        <div className="text-white font-medium">{b.material_name || `Material #${b.material_id}`}</div>
                        <div className="text-xs text-slate-500 font-mono">ID: {b.material_id}</div>
                      </td>
                      <td className="px-3 py-2 text-slate-300">{b.material_unit || "-"}</td>
                      <td className="px-3 py-2 text-slate-300">{b.location || "-"}</td>
                      <td className="px-3 py-2 text-right text-white font-semibold">{b.qty_on_hand}</td>
                      <td className="px-3 py-2 text-right text-amber-300">{b.qty_reserved}</td>
                      <td className={`px-3 py-2 text-right font-semibold ${b.qty_available > 0 ? "text-emerald-300" : "text-red-300"}`}>
                        {b.qty_available}
                      </td>
                      <td className="px-3 py-2 text-slate-400 text-xs">{b.last_updated_at || "-"}</td>
                      <td className="px-3 py-2 text-right">
                        <Button 
                          size="sm" 
                          variant="ghost" 
                          onClick={() => {
                            setSelectedMaterialId(b.material_id);
                            setSelectedMaterialName(b.material_name || `Material #${b.material_id}`);
                            setIsPanelOpen(true);
                          }}
                        >
                          Szczegoly
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {/* Material Details Side Panel */}
      {isPanelOpen && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setIsPanelOpen(false)} />
          <div className="relative w-full max-w-xl bg-panel-solid border-l border-white/10 shadow-2xl flex flex-col h-full animate-in slide-in-from-right duration-300">
            <div className="p-6 border-b border-white/10 flex justify-between items-center">
              <div>
                <h3 className="text-lg font-bold text-white">{selectedMaterialName}</h3>
                <p className="text-xs text-slate-500 font-mono">Material ID: {selectedMaterialId}</p>
              </div>
              <Button variant="ghost" onClick={() => setIsPanelOpen(false)}>Zamknij</Button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-6">
              <Section title="Historia ruchu (Traceability)">
                <TraceabilityTimeline 
                  movements={selectedMaterialMovements} 
                  isLoading={loadingMovements} 
                />
              </Section>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
