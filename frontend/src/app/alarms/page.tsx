"use client";

import { useEffect, useState, useRef } from "react";
import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Button, Card } from "@/components/ui";
import { TechModulAPI, type AlarmRecord } from "@/services/api";
import { CheckCircle2, XCircle, RefreshCw, TriangleAlert, Info, Zap } from "lucide-react";
import clsx from "clsx";

type Toast = { kind: "ok" | "err"; msg: string };

const SEVERITY_STYLE: Record<string, string> = {
  krytyczny: "bg-red-500/15 text-red-400 border-red-500/30",
  ostrzezenie: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  info: "bg-blue-500/15 text-blue-400 border-blue-500/30",
};

const SEVERITY_ICON: Record<string, React.ReactNode> = {
  krytyczny: <TriangleAlert className="w-3.5 h-3.5" />,
  ostrzezenie: <Zap className="w-3.5 h-3.5" />,
  info: <Info className="w-3.5 h-3.5" />,
};

export default function AlarmsPage() {
  const [alarms, setAlarms] = useState<AlarmRecord[]>([]);
  const [includeResolved, setIncludeResolved] = useState(false);
  const [loading, setLoading] = useState(true);
  const [pendingIds, setPendingIds] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<Toast | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showToast = (kind: Toast["kind"], msg: string) => {
    setToast({ kind, msg });
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 3500);
  };

  const setPending = (id: string, on: boolean) =>
    setPendingIds((s) => { const n = new Set(s); on ? n.add(id) : n.delete(id); return n; });

  const loadAlarms = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await TechModulAPI.getAlarms(includeResolved);
      setAlarms(res.items ?? []);
    } catch (e: any) {
      setError(e?.message ?? "Bad adowania alarmow");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadAlarms(); }, [includeResolved]);

  const onAck = async (alarm: AlarmRecord) => {
    setPending(alarm.alarm_id, true);
    try {
      await TechModulAPI.acknowledgeAlarm(alarm.alarm_id, true);
      showToast("ok", `Alarm "${alarm.title}" potwierdzony.`);
      await loadAlarms();
    } catch (e: any) {
      setError(e?.message ?? "Bad potwierdzania alarmu");
    } finally {
      setPending(alarm.alarm_id, false);
    }
  };

  const onResolve = async (alarm: AlarmRecord) => {
    setPending(alarm.alarm_id, true);
    try {
      await TechModulAPI.resolveAlarm(alarm.alarm_id);
      showToast("ok", `Alarm "${alarm.title}" zamkniety.`);
      await loadAlarms();
    } catch (e: any) {
      setError(e?.message ?? "Bad zamykania alarmu");
    } finally {
      setPending(alarm.alarm_id, false);
    }
  };

  const critical = alarms.filter((a) => !a.is_resolved && a.severity === "krytyczny").length;
  const warnings = alarms.filter((a) => !a.is_resolved && a.severity === "ostrzezenie").length;
  const active = alarms.filter((a) => !a.is_resolved).length;

  return (
    <AppShell>
      <PageHeader
        eyebrow="System Alertow"
        title="Alarmy operacyjne"
        subtitle="Potwierdzaj i zamykaj alarmy generowane przez backend."
        actions={
          <div className="flex items-center gap-3">
            <label className="text-xs text-slate-300 flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                className="rounded"
                checked={includeResolved}
                onChange={(e) => setIncludeResolved(e.target.checked)}
              />
              Pokaz zamkniete
            </label>
            <Button onClick={loadAlarms} disabled={loading}>
              <RefreshCw className={`w-4 h-4 mr-1 ${loading ? "animate-spin" : ""}`} />
              Odswiez
            </Button>
          </div>
        }
      />

      {/* Toast */}
      {toast && (
        <div className={`fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-lg shadow-xl text-sm font-medium
          ${toast.kind === "ok" ? "bg-emerald-600 text-white" : "bg-red-600 text-white"}`}>
          {toast.kind === "ok" ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
          {toast.msg}
        </div>
      )}

      <div className="max-w-6xl mx-auto pb-10 space-y-4">
        {/* COUNTERS */}
        {!loading && (
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-red-400">{critical}</div>
              <div className="text-xs text-slate-500 mt-0.5">Krytyczne</div>
            </div>
            <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-amber-400">{warnings}</div>
              <div className="text-xs text-slate-500 mt-0.5">Ostrzezenia</div>
            </div>
            <div className="bg-white/5 border border-white/10 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-white">{active}</div>
              <div className="text-xs text-slate-500 mt-0.5">Aktywne</div>
            </div>
          </div>
        )}

        <Card padded={false}>
          {loading ? (
            <div className="p-8 text-center text-sm text-slate-400 animate-pulse">adowanie alarmow...</div>
          ) : alarms.length === 0 ? (
            <div className="p-8 text-center">
              <CheckCircle2 className="w-8 h-8 text-emerald-500/40 mx-auto mb-2" />
              <p className="text-sm text-slate-500">Brak alarmow{includeResolved ? "" : " aktywnych"}.</p>
              {!includeResolved && (
                <p className="text-xs text-slate-600 mt-1">Zaznacz "Pokaz zamkniete" zeby zobaczyc historie.</p>
              )}
            </div>
          ) : (
            <div className="divide-y divide-white/10">
              {alarms.map((alarm) => {
                const acknowledged = Boolean(alarm.extra?.acknowledged);
                const pending = pendingIds.has(alarm.alarm_id);
                const sev = String(alarm.severity || "info").toLowerCase();

                return (
                  <div
                    key={alarm.alarm_id}
                    className={clsx(
                      "p-4 flex items-start justify-between gap-4 transition-colors",
                      alarm.is_resolved ? "opacity-50" : "hover:bg-white/[0.02]"
                    )}
                  >
                    <div className="flex items-start gap-3 min-w-0">
                      <span className={clsx(
                        "mt-0.5 flex items-center gap-1 shrink-0 text-[10px] font-bold uppercase px-2 py-1 rounded border",
                        SEVERITY_STYLE[sev] ?? "bg-white/10 text-slate-400 border-white/10"
                      )}>
                        {SEVERITY_ICON[sev]}
                        {sev}
                      </span>
                      <div className="min-w-0">
                        <p className="text-sm text-white font-medium">{alarm.title || "(bez tytuu)"}</p>
                        <p className="text-xs text-slate-400 mt-0.5">
                          {alarm.category}  {alarm.created_at || "-"}
                        </p>
                        {alarm.description && (
                          <p className="text-xs text-slate-500 mt-1 max-w-lg">{alarm.description}</p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        className="text-xs px-2.5 py-1 rounded border border-white/10 text-slate-300 hover:text-white hover:border-white/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        disabled={acknowledged || alarm.is_resolved || pending}
                        onClick={() => onAck(alarm)}
                      >
                        {pending ? "..." : acknowledged ? "Potwierdzono " : "Potwierdz"}
                      </button>
                      <button
                        className="text-xs px-2.5 py-1 rounded border border-emerald-500/20 text-emerald-400 hover:text-emerald-300 hover:border-emerald-400/40 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        disabled={alarm.is_resolved || pending}
                        onClick={() => onResolve(alarm)}
                      >
                        {pending ? "..." : alarm.is_resolved ? "Zamkniety " : "Zamknij"}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        {error && (
          <p className="text-xs text-red-400 flex items-center gap-1">
            <XCircle className="w-3.5 h-3.5" />{error}
          </p>
        )}
      </div>
    </AppShell>
  );
}
