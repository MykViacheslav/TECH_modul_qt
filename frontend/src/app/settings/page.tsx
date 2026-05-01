"use client";

import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Button, Card } from "@/components/ui";
import { Sliders, ShieldCheck, Terminal, Bell, Loader2, CircleDollarSign, ChevronRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { TechModulAPI, type SystemSummary } from "@/services/api";

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between items-center py-3 border-b border-subtle last:border-0">
      <span className="text-sm text-slate-400">{label}</span>
      <span className="text-sm font-semibold">{value}</span>
    </div>
  );
}

export default function SettingsPage() {
  const [summary, setSummary] = useState<SystemSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    let active = true;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await TechModulAPI.getSystemSummary();
        if (!active) return;
        setSummary(data);
      } catch (e: any) {
        if (!active) return;
        setError(e?.message ?? "Blad pobierania podsumowania systemu");
        setSummary(null);
      } finally {
        if (active) setLoading(false);
      }
    };
    load();
    return () => {
      active = false;
    };
  }, []);

  const statusLabel = useMemo(() => {
    if (!summary) return "Niedostepny";
    return String(summary.status || "offline").toLowerCase() === "online" ? "Stabilny" : "Offline";
  }, [summary]);

  return (
    <AppShell>
      <PageHeader
        eyebrow="Administracja systemem"
        title={<>Ustawienia <span className="text-brand-hover">globalne</span></>}
        subtitle="Konfiguracja motywu, jednostek, uprawnien i silnika obliczen."
      />

      {loading ? (
        <Card className="mb-4">
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <Loader2 className="w-4 h-4 animate-spin" />
            Ladowanie danych systemu...
          </div>
        </Card>
      ) : null}

      {error ? (
        <Card className="mb-4 border-red-500/20 bg-red-500/5">
          <p className="text-sm text-red-300">{error}</p>
        </Card>
      ) : null}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-6">
          <Card>
            <div className="flex items-center gap-3 mb-4">
              <Sliders className="w-5 h-5 text-brand-hover" />
              <h3 className="text-base font-semibold">Wizualizacja i rysunek</h3>
            </div>
            <Row label="Motyw interfejsu" value="Premium Dark" />
            <Row label="Jednostki miar" value="Milimetry (mm)" />
            <Row label="Siatka edytora" value="24 px" />
          </Card>

          <Card>
            <div className="flex items-center gap-3 mb-4">
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
              <h3 className="text-base font-semibold">Bezpieczenstwo i uprawnienia</h3>
            </div>
            <div className="grid grid-cols-2 gap-3 mt-4">
              <Button variant="secondary">Role uzytkownikow</Button>
              <Button variant="secondary">Dziennik logowan</Button>
            </div>
          </Card>

          <Card>
            <div className="flex items-center gap-3 mb-4">
              <Bell className="w-5 h-5 text-amber-400" />
              <h3 className="text-base font-semibold">Powiadomienia</h3>
            </div>
            <Row label="E-mail raportow" value="biuro@example.pl" />
            <Row label="Telegram alarmy" value="Wlaczone" />
          </Card>
          <Card>
            <div className="flex items-center gap-3 mb-4">
              <CircleDollarSign className="w-5 h-5 text-blue-400" />
              <h3 className="text-base font-semibold">Finanse i Cenniki</h3>
            </div>
            <div className="space-y-2">
              <Button 
                variant="secondary" 
                className="w-full justify-between"
                onClick={() => router.push("/settings/pricing")}
              >
                Cennik obróbki (taryfy)
                <ChevronRight className="w-4 h-4 opacity-50" />
              </Button>
            </div>
          </Card>
        </div>

        <Card className="flex flex-col items-center justify-center text-center min-h-[400px]">
          <div className="w-16 h-16 rounded-2xl bg-brand-soft flex items-center justify-center mb-6">
            <Terminal className="w-7 h-7 text-brand-hover" />
          </div>
          <h4 className="text-xl font-bold mb-1">TECH MODUL Enterprise</h4>
          <p className="eyebrow mb-8">Wersja API - {summary?.api_version || "-"}</p>

          <div className="grid grid-cols-2 gap-4 w-full max-w-[340px] mb-6">
            <Row label="Projekty" value={summary?.db.projects_count ?? 0} />
            <Row label="Moduly" value={summary?.db.modules_count ?? 0} />
            <Row label="Zamowienia" value={summary?.db.orders_count ?? 0} />
            <Row label="Materialy" value={summary?.db.materials_count ?? 0} />
            <Row label="Kontrahenci" value={summary?.db.clients_count ?? 0} />
          </div>

          <div className="flex gap-8 text-center">
            <div>
              <p className="eyebrow mb-1">Status</p>
              <p className="text-base font-bold text-emerald-400">{statusLabel}</p>
            </div>
            <div className="w-px bg-subtle" />
            <div>
              <p className="eyebrow mb-1">Silnik obliczen</p>
              <p className="text-base font-bold text-brand-hover">{summary?.engine || "TECH-V4"}</p>
            </div>
          </div>
        </Card>
      </div>
    </AppShell>
  );
}
