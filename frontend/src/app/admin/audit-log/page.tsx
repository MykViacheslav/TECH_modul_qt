"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Card, Button } from "@/components/ui";
import { TechModulAPI, type AuditEntry } from "@/services/api";
import { 
  History, 
  RefreshCw, 
  User, 
  Shield, 
  Package, 
  DollarSign, 
  AlertCircle,
  Clock,
  ExternalLink
} from "lucide-react";
import clsx from "clsx";

export default function AuditLogPage() {
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await TechModulAPI.getAuditLog(1000);
      setLogs(data ?? []);
    } catch (e: any) {
      setError(e?.message ?? "Blad ladowania logow audytu");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const getActionConfig = (action: string) => {
    if (action.startsWith("INV_")) {
      return { 
        icon: <Package className="w-4 h-4" />, 
        color: "text-blue-400", 
        bg: "bg-blue-500/10",
        label: action.replace("INV_", "") 
      };
    }
    if (action.startsWith("PURCHASE_")) {
      return { 
        icon: <DollarSign className="w-4 h-4" />, 
        color: "text-emerald-400", 
        bg: "bg-emerald-500/10",
        label: action.replace("PURCHASE_DOC_", "")
      };
    }
    if (action === "COST_ENTRY_CREATE") {
      return { 
        icon: <DollarSign className="w-4 h-4" />, 
        color: "text-amber-400", 
        bg: "bg-amber-500/10",
        label: "COST" 
      };
    }
    return { 
      icon: <History className="w-4 h-4" />, 
      color: "text-slate-400", 
      bg: "bg-slate-500/10",
      label: action 
    };
  };

  return (
    <AppShell>
      <PageHeader
        eyebrow="Administracja"
        title="Audit Log"
        subtitle="Historia wszystkich krytycznych operacji w systemie. Kto, kiedy i co zrobiÅ‚."
        actions={
          <Button onClick={loadData} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-1 ${loading ? "animate-spin" : ""}`} />
            Odswiez
          </Button>
        }
      />

      <div className="max-w-7xl mx-auto space-y-6 pb-20">
        <Card padded={false}>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-200/90 text-slate-900 font-bold">
                <tr>
                  <th className="text-left px-4 py-3">Czas zdarzenia</th>
                  <th className="text-left px-4 py-3">Uzytkownik</th>
                  <th className="text-left px-4 py-3">Akcja</th>
                  <th className="text-left px-4 py-3">Obiekt</th>
                  <th className="text-left px-4 py-3">Szczegoly</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10">
                {loading ? (
                  <tr><td colSpan={5} className="p-20 text-center animate-pulse text-slate-500">Ladowanie historii...</td></tr>
                ) : logs.length === 0 ? (
                  <tr><td colSpan={5} className="p-20 text-center text-slate-500">Brak zarejestrowanych zdarzen.</td></tr>
                ) : (
                  logs.map((log) => {
                    const config = getActionConfig(log.action);
                    return (
                      <tr key={log.id} className="hover:bg-white/5 transition-colors group">
                        <td className="px-4 py-3 whitespace-nowrap">
                          <div className="flex items-center gap-2 text-slate-400">
                            <Clock className="w-3 h-3" />
                            {log.timestamp}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2 text-white font-medium">
                            <div className="w-6 h-6 rounded-full bg-slate-700 flex items-center justify-center">
                              <User className="w-3 h-3" />
                            </div>
                            {log.user_name || 'System'}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <span className={clsx(
                            "inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold uppercase border",
                            config.color, config.bg, "border-current/10"
                          )}>
                            {config.icon}
                            {config.label}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-col">
                            <span className="text-slate-300 font-mono text-xs uppercase tracking-tight">
                              {log.target_type}
                            </span>
                            <span className="text-[10px] text-slate-500 font-mono">
                              ID: {log.target_id}
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="text-slate-300 max-w-md truncate group-hover:whitespace-normal group-hover:overflow-visible transition-all">
                            {log.details}
                          </div>
                          {log.metadata_json && log.metadata_json !== '{}' && (
                            <div className="text-[10px] text-slate-500 font-mono mt-1 opacity-60">
                              {log.metadata_json}
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </AppShell>
  );
}
