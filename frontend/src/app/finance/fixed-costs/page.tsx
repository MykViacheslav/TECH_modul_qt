"use client";

import { useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import BusinessHealthStrip from "@/components/BusinessHealthStrip";
import PageHeader from "@/components/PageHeader";
import { Button, Card } from "@/components/ui";
import { TechModulAPI, type CompanyExpenseItem, type FixedCompanyExpensesResponse } from "@/services/api";
import { Landmark, Loader2, Plus, Save, Trash2 } from "lucide-react";

function formatMoney(value: number): string {
  return `${(Number.isFinite(value) ? value : 0).toFixed(2)} zl`;
}

const DEFAULT_ITEMS = ["Wynajem", "Leasingi", "OC / AC", "BHP", "Badania", "Internet", "Inne"];

export default function FixedCostsPage() {
  const [items, setItems] = useState<CompanyExpenseItem[]>([]);
  const [workersCount, setWorkersCount] = useState(1);
  const [hoursPerWorker, setHoursPerWorker] = useState(160);
  const [summary, setSummary] = useState<FixedCompanyExpensesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await TechModulAPI.getFixedCompanyExpenses();
      setSummary(data);
      setItems(data.fixed?.length ? data.fixed : DEFAULT_ITEMS.map((name) => ({ name, amount: 0 })));
      setWorkersCount(Math.max(1, Number(data.workers_count || 1)));
      setHoursPerWorker(Math.max(1, Number(data.hours_per_worker || 160)));
    } catch (e: any) {
      setError(String(e?.message || "Nie udalo sie pobrac wydatkow stalych"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const fixedTotal = useMemo(
    () => items.reduce((sum, item) => sum + Number(item.amount || 0), 0),
    [items]
  );
  const plannedHours = Math.max(1, workersCount) * Math.max(1, hoursPerWorker);
  const fixedHourRate = fixedTotal / plannedHours;
  const variableTotal = Number(summary?.variable_total || 0);

  const updateItem = (index: number, patch: Partial<CompanyExpenseItem>) => {
    setItems((prev) => prev.map((item, i) => (i === index ? { ...item, ...patch } : item)));
  };

  const removeItem = (index: number) => {
    setItems((prev) => prev.filter((_, i) => i !== index));
  };

  const addItem = () => {
    setItems((prev) => [...prev, { name: "Nowy koszt", amount: 0 }]);
  };

  const save = async () => {
    setSaving(true);
    setSaved("");
    setError("");
    try {
      const payload = await TechModulAPI.updateFixedCompanyExpenses({
        fixed: items.map((item) => ({
          expense_id: item.expense_id,
          name: String(item.name || "").trim(),
          amount: Number(item.amount || 0),
          account_type: item.account_type || "bank",
          source_type: item.source_type || "bank_faktura",
        })),
        workers_count: workersCount,
        hours_per_worker: hoursPerWorker,
      });
      setSummary(payload);
      setItems(payload.fixed);
      setSaved("Zapisano wydatki stale i przeliczono koszt godziny.");
      window.setTimeout(() => setSaved(""), 3500);
    } catch (e: any) {
      setError(String(e?.message || "Nie udalo sie zapisac wydatkow"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppShell>
      <PageHeader
        eyebrow="Finanse firmy"
        title={<>Wydatki <span className="text-brand-hover">stale</span></>}
        subtitle="Koszty miesieczne, ktore trzeba doliczyc do prawdziwego kosztu godziny pracy i produkcji."
        actions={
          <div className="flex gap-2">
            <Button as="link" href="/finance/global" variant="secondary">Podsumowanie firmy</Button>
            <Button onClick={save} disabled={saving}>
              {saving ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <Save className="mr-1 h-4 w-4" />}
              Zapisz
            </Button>
          </div>
        }
      />

      <div className="mx-auto max-w-7xl space-y-4 pb-10">
        <BusinessHealthStrip
          scope="Wydatki stale i prawdziwy koszt godziny"
          subtitle="Tutaj ustawiasz koszty firmy, bez ktorych roboczogodzina bylaby zanizona."
        />

        {error ? (
          <Card className="border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">{error}</Card>
        ) : null}
        {saved ? (
          <Card className="border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-200">{saved}</Card>
        ) : null}

        <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
          <Card className="xl:col-span-2 p-4">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <div className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-500">Lista kosztow miesiecznych</div>
                <div className="text-sm text-slate-400">Wpisz realne stale wydatki firmy.</div>
              </div>
              <Button variant="secondary" onClick={addItem}>
                <Plus className="mr-1 h-4 w-4" /> Dodaj pozycje
              </Button>
            </div>

            <div className="space-y-3">
              {loading ? (
                <div className="rounded-xl border border-white/10 bg-black/10 px-4 py-8 text-sm text-slate-400">
                  <Loader2 className="mr-2 inline h-4 w-4 animate-spin" /> Ladowanie wydatkow...
                </div>
              ) : null}

              {!loading &&
                items.map((item, index) => (
                  <div key={item.expense_id || `${item.name}-${index}`} className="grid grid-cols-1 gap-3 rounded-2xl border border-white/10 bg-black/10 p-3 md:grid-cols-[1.7fr_0.8fr_0.7fr_0.7fr_auto]">
                    <input
                      value={item.name}
                      onChange={(e) => updateItem(index, { name: e.target.value })}
                      className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white outline-none focus:border-cyan-400"
                      placeholder="Nazwa kosztu"
                    />
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={Number(item.amount || 0)}
                      onChange={(e) => updateItem(index, { amount: Number(e.target.value || 0) })}
                      className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white outline-none focus:border-cyan-400"
                      placeholder="Kwota"
                    />
                    <select
                      value={item.account_type || "bank"}
                      onChange={(e) => updateItem(index, { account_type: e.target.value })}
                      className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white outline-none focus:border-cyan-400"
                    >
                      <option value="bank">Bank</option>
                      <option value="cash">Gotowka</option>
                    </select>
                    <select
                      value={item.source_type || "bank_faktura"}
                      onChange={(e) => updateItem(index, { source_type: e.target.value })}
                      className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white outline-none focus:border-cyan-400"
                    >
                      <option value="bank_faktura">Faktura</option>
                      <option value="leasing">Leasing</option>
                      <option value="skladka">Skladka</option>
                      <option value="abonament">Abonament</option>
                      <option value="inne">Inne</option>
                    </select>
                    <button
                      onClick={() => removeItem(index)}
                      className="inline-flex items-center justify-center rounded-xl border border-red-500/20 bg-red-500/10 px-3 py-2 text-red-200 hover:bg-red-500/20"
                      title="Usun pozycje"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
            </div>
          </Card>

          <div className="space-y-4">
            <Card className="p-4">
              <div className="mb-3 flex items-center gap-2">
                <Landmark className="h-4 w-4 text-cyan-300" />
                <div className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-500">Model godzin firmy</div>
              </div>
              <div className="space-y-3">
                <label className="block">
                  <div className="mb-1 text-xs text-slate-400">Liczba pracownikow</div>
                  <input
                    type="number"
                    min="1"
                    value={workersCount}
                    onChange={(e) => setWorkersCount(Math.max(1, Number(e.target.value || 1)))}
                    className="w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white outline-none focus:border-cyan-400"
                  />
                </label>
                <label className="block">
                  <div className="mb-1 text-xs text-slate-400">Godzin miesiecznie / pracownika</div>
                  <input
                    type="number"
                    min="1"
                    step="1"
                    value={hoursPerWorker}
                    onChange={(e) => setHoursPerWorker(Math.max(1, Number(e.target.value || 160)))}
                    className="w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white outline-none focus:border-cyan-400"
                  />
                </label>
              </div>
            </Card>

            <Card className="p-4">
              <div className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-500">Podsumowanie</div>
              <div className="mt-3 space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Wydatki stale</span>
                  <span className="font-black text-white">{formatMoney(fixedTotal)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Wydatki zmienne (zapisane)</span>
                  <span className="font-black text-white">{formatMoney(variableTotal)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Godziny miesieczne firmy</span>
                  <span className="font-black text-white">{plannedHours.toFixed(0)} h</span>
                </div>
                <div className="rounded-2xl border border-cyan-500/20 bg-cyan-500/10 p-3">
                  <div className="text-xs text-cyan-100">Sam narzut kosztow stalych na 1h</div>
                  <div className="mt-1 text-2xl font-black text-cyan-200">{formatMoney(fixedHourRate)}</div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/15 p-3 text-xs text-slate-400">
                  Ten ekran zasila prawdziwy koszt godziny w dashboardzie, produkcji, uslugach i innych zakladkach.
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
