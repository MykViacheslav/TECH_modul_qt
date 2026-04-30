"use client";

import { useEffect, useState, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Button, Card } from "@/components/ui";
import {
  TechModulAPI,
  type OperationsSummary,
  type OperationsIssueRecord,
  type RouteRecommendation,
} from "@/services/api";
import { CheckCircle2, XCircle, RefreshCw, ChevronUp, ChevronDown, Minus, Edit3, User, Clock } from "lucide-react";
import IssueActionModal from "@/components/IssueActionModal";
import clsx from "clsx";

type Toast = { kind: "ok" | "err"; msg: string };

const PRIORITY_ORDER = ["krytyczny", "wysoki", "sredni", "niski"] as const;
type Priority = typeof PRIORITY_ORDER[number];

const PRIORITY_STYLE: Record<string, string> = {
  krytyczny: "text-red-400 bg-red-500/10 border-red-500/30",
  wysoki: "text-amber-400 bg-amber-500/10 border-amber-500/30",
  sredni: "text-blue-400 bg-blue-500/10 border-blue-500/30",
  niski: "text-slate-400 bg-white/5 border-white/10",
};

export default function OperationsPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <OperationsContent />
    </Suspense>
  );
}

function OperationsContent() {
  const searchParams = useSearchParams();
  const initialSearch = searchParams.get("search") || "";
  
  const [summary, setSummary] = useState<OperationsSummary | null>(null);
  const [issues, setIssues] = useState<OperationsIssueRecord[]>([]);
  const [search, setSearch] = useState(initialSearch);
  const [recommendations, setRecommendations] = useState<RouteRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [pendingIds, setPendingIds] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<Toast | null>(null);
  const [selectedIssue, setSelectedIssue] = useState<OperationsIssueRecord | null>(null);
  const [isActionModalOpen, setIsActionModalOpen] = useState(false);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showToast = (kind: Toast["kind"], msg: string) => {
    setToast({ kind, msg });
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 3500);
  };

  const setPending = (id: string, on: boolean) =>
    setPendingIds((s) => { const n = new Set(s); on ? n.add(id) : n.delete(id); return n; });

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sum, issueRes, recoRes] = await Promise.all([
        TechModulAPI.getOperationsSummary(),
        TechModulAPI.getOperationsIssues("active"),
        TechModulAPI.recommendOperationRoutes({ limit: 8 }),
      ]);
      setSummary(sum);
      setIssues(issueRes.items ?? []);
      setRecommendations(recoRes.items ?? []);
    } catch (e: any) {
      setError(e?.message ?? "Bad adowania operations");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const closeIssue = async (issue: OperationsIssueRecord) => {
    if (!window.confirm(`Zamknac issue "${issue.title || issue.id}"?`)) return;
    setPending(issue.id, true);
    try {
      await TechModulAPI.patchOperationsIssue(issue.id, { status: "zamkniete" });
      showToast("ok", `Issue "${issue.title || issue.id}" zamkniety.`);
      await loadData();
    } catch (e: any) {
      setError(e?.message ?? "Bad zamykania issue");
    } finally {
      setPending(issue.id, false);
    }
  };

  const changePriority = async (issue: OperationsIssueRecord, direction: "up" | "down") => {
    const cur = PRIORITY_ORDER.indexOf((issue.priority_manual as Priority) ?? "niski");
    const next = direction === "up" ? cur - 1 : cur + 1;
    if (next < 0 || next >= PRIORITY_ORDER.length) return;
    const newPrio = PRIORITY_ORDER[next];
    setPending(issue.id + "_prio", true);
    try {
      await TechModulAPI.patchOperationsIssue(issue.id, { priority_manual: newPrio });
      showToast("ok", `Priorytet zmieniony na "${newPrio}".`);
      setIssues((prev) =>
        prev.map((i) => (i.id === issue.id ? { ...i, priority_manual: newPrio } : i))
      );
    } catch (e: any) {
      setError(e?.message ?? "Bad zmiany priorytetu");
    } finally {
      setPending(issue.id + "_prio", false);
    }
  };

  const filteredIssues = issues.filter(issue => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      (issue.title || "").toLowerCase().includes(q) ||
      (issue.project_name || "").toLowerCase().includes(q) ||
      (issue.description || "").toLowerCase().includes(q)
    );
  });

  return (
    <AppShell>
      <PageHeader
        eyebrow="Operations Hub"
        title="Priorytety i trasy"
        subtitle="Zarzadzaj aktywnymi issue i rekomendacjami tras."
        actions={
          <Button onClick={loadData} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-1 ${loading ? "animate-spin" : ""}`} />
            Odswiez
          </Button>
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

      <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6 pb-10">
        {/* METRICS */}
        <Card className="lg:col-span-3 grid grid-cols-2 md:grid-cols-5 gap-3">
          <Metric label="Issue aktywne" value={summary?.issues_active} />
          <Metric label="Issue krytyczne" value={summary?.issues_critical} accent="red" />
          <Metric label="Po terminie" value={summary?.issues_overdue} accent="amber" />
          <Metric label="Trasy aktywne" value={summary?.routes_active} />
          <Metric
            label="Odblokowanie PLN"
            value={summary ? summary.revenue_unlock_total.toFixed(0) : "-"}
            accent="green"
          />
        </Card>

        {/* ISSUES */}
        <Card className="lg:col-span-2" padded={false}>
          <div className="p-4 border-b border-white/10 flex items-center justify-between">
            <span className="text-sm text-slate-300">Aktywne issue</span>
            <span className="text-xs text-slate-500">{filteredIssues.length} issue</span>
          </div>
          {loading ? (
            <div className="p-8 text-center text-sm text-slate-400 animate-pulse">adowanie...</div>
          ) : filteredIssues.length === 0 ? (
            <div className="p-8 text-center">
              <CheckCircle2 className="w-8 h-8 text-emerald-500/40 mx-auto mb-2" />
              <p className="text-sm text-slate-500">Brak wynikÃ³w dla podanego filtra.</p>
            </div>
          ) : (
            <div className="divide-y divide-white/10">
              {filteredIssues.slice(0, 20).map((issue) => {
                const isPending = pendingIds.has(issue.id);
                const isPrioPending = pendingIds.has(issue.id + "_prio");
                const prio = String(issue.priority_manual || "niski").toLowerCase();
                const curIdx = PRIORITY_ORDER.indexOf(prio as Priority);

                const isOverdue = issue.due_date && new Date(issue.due_date) < new Date() && issue.status !== "zamkniete";
                const isUnassignedUrgent = !issue.owner && (prio === "wysoki" || prio === "krytyczny") && issue.status !== "zamkniete";
                const isEscalated = isOverdue || isUnassignedUrgent;

                return (
                  <div key={issue.id} className={clsx(
                    "p-4 flex items-start justify-between gap-3 hover:bg-white/[0.02] transition-colors relative",
                    isEscalated && "bg-red-500/5"
                  )}>
                    {isEscalated && <div className="absolute left-0 top-0 bottom-0 w-1 bg-red-500" />}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={clsx("text-[10px] font-bold uppercase px-2 py-0.5 rounded border", PRIORITY_STYLE[prio] ?? PRIORITY_STYLE.niski)}>
                          {prio}
                        </span>
                        <span className="text-xs text-slate-500">{issue.status}</span>
                        {isOverdue && <span className="text-[9px] font-black text-red-500 uppercase tracking-tighter">Overdue</span>}
                        {isUnassignedUrgent && <span className="text-[9px] font-black text-orange-500 uppercase tracking-tighter">Escalated: No Owner</span>}
                      </div>
                      <p className="text-sm text-white truncate">{issue.title || issue.id}</p>
                      <div className="flex items-center gap-3 mt-1">
                        <p className="text-[10px] text-slate-500 uppercase font-black tracking-tight">{issue.project_name || "-"}</p>
                        {issue.owner && (
                          <div className="flex items-center gap-1 text-[10px] text-brand/70 font-bold uppercase">
                            <User size={10} /> {issue.owner}
                          </div>
                        )}
                        {issue.due_date && (
                          <div className="flex items-center gap-1 text-[10px] text-orange-500/70 font-bold uppercase">
                            <Clock size={10} /> {issue.due_date}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      {/* Priority up/down */}
                      <div className="flex flex-col">
                        <button
                          className="p-0.5 text-slate-500 hover:text-white disabled:opacity-30 transition-colors"
                          disabled={curIdx <= 0 || isPrioPending}
                          onClick={() => changePriority(issue, "up")}
                          title="Podnies priorytet"
                        >
                          <ChevronUp className="w-3.5 h-3.5" />
                        </button>
                        <button
                          className="p-0.5 text-slate-500 hover:text-white disabled:opacity-30 transition-colors"
                          disabled={curIdx >= PRIORITY_ORDER.length - 1 || isPrioPending}
                          onClick={() => changePriority(issue, "down")}
                          title="Obniz priorytet"
                        >
                          <ChevronDown className="w-3.5 h-3.5" />
                        </button>
                      </div>
                      <button
                        className="text-xs px-2.5 py-1 rounded border border-brand/20 text-brand hover:text-white hover:bg-brand/10 transition-colors ml-1"
                        onClick={() => {
                          setSelectedIssue(issue);
                          setIsActionModalOpen(true);
                        }}
                      >
                        Action
                      </button>
                      <button
                        className="text-xs px-2.5 py-1 rounded border border-emerald-500/20 text-emerald-400 hover:text-emerald-300 hover:border-emerald-400/40 disabled:opacity-40 disabled:cursor-not-allowed transition-colors ml-1"
                        disabled={isPending}
                        onClick={() => closeIssue(issue)}
                      >
                        {isPending ? "..." : "Zamknij"}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        {/* RECOMMENDATIONS */}
        <Card className="lg:col-span-1" padded={false}>
          <div className="p-4 border-b border-white/10 text-sm text-slate-300">Rekomendacje tras</div>
          {loading ? (
            <div className="p-8 text-center text-sm text-slate-400 animate-pulse">adowanie...</div>
          ) : recommendations.length === 0 ? (
            <div className="p-8 text-center">
              <Minus className="w-6 h-6 text-slate-600 mx-auto mb-2" />
              <p className="text-sm text-slate-500">Brak rekomendacji.</p>
            </div>
          ) : (
            <div className="divide-y divide-white/10">
              {recommendations.map((rec) => (
                <div key={rec.issue_id} className="p-4 hover:bg-white/[0.02] transition-colors">
                  <p className="text-sm text-white">{rec.title || rec.issue_id}</p>
                  <p className="text-xs text-slate-400 mt-1">
                    Score: <span className="text-brand-hover font-medium">{rec.score.toFixed(1)}</span>
                    {rec.recommended_planned_date ? `  ${rec.recommended_planned_date}` : ""}
                  </p>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {error && (
        <p className="max-w-6xl mx-auto text-xs text-red-400 pb-8 flex items-center gap-1">
          <XCircle className="w-3.5 h-3.5" />{error}
        </p>
      )}

      {selectedIssue && (
        <IssueActionModal
          isOpen={isActionModalOpen}
          onClose={() => {
            setIsActionModalOpen(false);
            setSelectedIssue(null);
          }}
          issue={selectedIssue}
          onUpdate={loadData}
        />
      )}
    </AppShell>
  );
}

function Metric({ label, value, accent }: { label: string; value: number | string | undefined; accent?: "red" | "amber" | "green" }) {
  const val = value ?? "-";
  const color =
    accent === "red" ? "text-red-400" :
    accent === "amber" ? "text-amber-400" :
    accent === "green" ? "text-emerald-400" :
    "text-white";
  return (
    <div className="border border-white/10 rounded p-3 bg-black/20">
      <div className="text-[11px] text-slate-400">{label}</div>
      <div className={clsx("text-lg font-semibold", color)}>{val}</div>
    </div>
  );
}
