"use client";

import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Button, Card, StatCard } from "@/components/ui";
import { TrendingUp, Printer, Info, Send, Loader2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { TechModulAPI, type FinanceSummary } from "@/services/api";
import { useSelectedProjectId } from "@/services/project-context";

export default function FinancePage() {
  const [projectId] = useSelectedProjectId(1);
  const [summary, setSummary] = useState<FinanceSummary | null>(null);
  const [margin, setMargin] = useState(30);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);

  const loadSummary = async () => {
    setLoading(true);
    setSavedMsg(null);
    try {
      const data = await TechModulAPI.getProjectFinanceSummary(projectId);
      setSummary(data);
      setMargin(Number(data.margin || 30));
    } catch (e: any) {
      setSavedMsg(e?.message ?? "Blad pobierania danych finansowych");
      setSummary(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSummary();
  }, [projectId]);

  const baseCost = useMemo(() => summary?.base_cost ?? 0, [summary]);
  const totalNet = useMemo(() => baseCost * (1 + margin / 100), [baseCost, margin]);
  const profit = useMemo(() => totalNet - baseCost, [totalNet, baseCost]);
  const vat = useMemo(() => totalNet * 0.23, [totalNet]);
  const totalGross = useMemo(() => totalNet + vat, [totalNet, vat]);

  const saveMargin = async () => {
    setSaving(true);
    setSavedMsg(null);
    try {
      await TechModulAPI.updateMargin(projectId, margin);
      await loadSummary();
      setSavedMsg("Zapisano");
    } catch (e: any) {
      setSavedMsg(e?.message ?? "Blad zapisu (API offline?)");
    } finally {
      setSaving(false);
      setTimeout(() => setSavedMsg(null), 3000);
    }
  };

  return (
    <AppShell>
      <PageHeader
        eyebrow={`Analiza finansowa projektu - ID ${projectId}`}
        title={<>Wycena <span className="text-brand-hover">precyzyjna</span></>}
        subtitle="Zarzadzaj marza w czasie rzeczywistym. Podglad zysku, VAT i kwoty dla klienta."
        actions={
          <>
            <Button as="link" href="/finance/fixed-costs" variant="secondary">
              Koszty stale
            </Button>
            <Button variant="secondary">
              <Info className="w-4 h-4" /> Szczegoly kosztow
            </Button>
            <Button onClick={() => window.open(TechModulAPI.getProjectPdfUrl(projectId), "_blank")}>
              <Printer className="w-4 h-4" /> Generuj PDF
            </Button>
          </>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <div className="flex items-center justify-between mb-8">
            <h3 className="eyebrow">Zarzadzanie marza handlowa</h3>
            <button onClick={saveMargin} disabled={saving} className="btn-ghost text-xs disabled:opacity-50">
              {saving ? "Zapisywanie..." : "Zapisz marze"}
            </button>
          </div>

          {loading ? (
            <div className="mb-6 flex items-center gap-2 text-sm text-slate-400">
              <Loader2 className="w-4 h-4 animate-spin" />
              Ladowanie podsumowania finansowego...
            </div>
          ) : null}

          <div className="mb-10">
            <div className="flex items-baseline justify-between mb-4">
              <span className="text-sm text-slate-400">Twoja marza</span>
              <span className="text-5xl font-bold text-brand-hover tabular-nums">{margin}%</span>
            </div>
            <input
              type="range"
              min={5}
              max={100}
              value={margin}
              onChange={(e) => setMargin(parseInt(e.target.value, 10))}
              className="w-full h-2 bg-canvas-deep rounded-lg appearance-none cursor-pointer accent-brand"
            />
            <div className="flex justify-between mt-2 text-xs text-slate-600">
              <span>5%</span>
              <span className="text-emerald-500">Zalecane 25-45%</span>
              <span>100%</span>
            </div>
            {savedMsg ? <p className="mt-3 text-xs text-brand-hover">{savedMsg}</p> : null}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <StatCard label="Koszt bazowy (netto)" value={`${baseCost.toFixed(2)} PLN`} />
            <StatCard label="Twoj zysk" value={`${profit.toFixed(2)} PLN`} tone="success" />
            <StatCard label="Zamowienia" value={String(summary?.orders_count ?? 0)} />
            <StatCard label="Projekt" value={summary?.project_title || "-"} />
          </div>
        </Card>

        <div className="rounded-hero bg-brand p-8 text-white shadow-brand-glow relative overflow-hidden">
          <div className="absolute -top-16 -right-16 w-48 h-48 bg-white/10 rounded-full blur-3xl" />
          <TrendingUp className="w-10 h-10 text-blue-200 mb-6 relative" />
          <p className="eyebrow-brand !text-blue-200 relative">Dla klienta (brutto)</p>
          <p className="relative mt-3 text-5xl font-bold tracking-tight tabular-nums">
            {totalGross.toLocaleString("pl-PL", { maximumFractionDigits: 0 })}
            <span className="text-xl font-normal text-blue-200 ml-2">PLN</span>
          </p>

          <div className="relative mt-8 pt-6 border-t border-white/20 space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-blue-200">Netto</span>
              <span className="font-mono">{totalNet.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-blue-200">VAT 23%</span>
              <span className="font-mono">{vat.toFixed(2)}</span>
            </div>
            <div className="flex justify-between opacity-70">
              <span>Zadatek 30%</span>
              <span className="font-mono">{(totalGross * 0.3).toFixed(2)}</span>
            </div>
          </div>

          <button className="relative mt-8 w-full py-3.5 rounded-xl bg-white text-brand font-semibold text-sm hover:bg-slate-100 transition-colors flex items-center justify-center gap-2">
            <Send className="w-4 h-4" /> Wyslij oferte
          </button>
        </div>
      </div>
    </AppShell>
  );
}
