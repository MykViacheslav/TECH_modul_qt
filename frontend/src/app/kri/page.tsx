"use client";

import { useEffect, useState, useMemo } from "react";
import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Card, Button } from "@/components/ui";
import { 
  TechModulAPI, 
  type KriResponse 
} from "@/services/api";
import { 
  ShieldAlert, 
  RefreshCw, 
  AlertOctagon,
  Clock,
  Package,
  DollarSign,
  Cpu,
  History,
  Activity,
  ChevronRight,
  ExternalLink
} from "lucide-react";
import clsx from "clsx";
import Link from "next/link";
import IssueActionModal from "@/components/IssueActionModal";

export default function KriPage() {
  const [data, setData] = useState<KriResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedRisk, setSelectedRisk] = useState<any | null>(null);
  const [isActionModalOpen, setIsActionModalOpen] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await TechModulAPI.getKriV1();
      setData(res);
    } catch (e: any) {
      setError(e?.message || "Failed to load KRI data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const riskGroups = useMemo(() => {
    if (!data) return {};
    return data.risks.reduce((acc, risk) => {
      if (!acc[risk.category]) acc[risk.category] = [];
      acc[risk.category].push(risk);
      return acc;
    }, {} as Record<string, any[]>);
  }, [data]);

  const severityColor = (sev: string) => {
    switch (sev) {
      case "CRITICAL": return "text-red-500 bg-red-500/10 border-red-500/20";
      case "HIGH": return "text-orange-500 bg-orange-500/10 border-orange-500/20";
      case "MEDIUM": return "text-amber-500 bg-amber-500/10 border-amber-500/20";
      default: return "text-blue-500 bg-blue-500/10 border-blue-500/20";
    }
  };

  const getSourceLink = (risk: any) => {
    switch (risk.source_type) {
      case "issue": return `/operations?search=${encodeURIComponent(risk.title.replace('Overdue Issue: ', ''))}`;
      case "route_task": return "/stations/cnc";
      case "material": return `/inventory?search=${encodeURIComponent(risk.title.replace('Low Stock: ', ''))}`;
      case "material_shortage": return "/procurement/suggestions";
      case "order_cost": return `/orders/${risk.source_id}/costs`;
      case "audit_log": return "/admin/audit-log";
      default: return null;
    }
  };

  if (loading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center min-h-[60vh]">
          <RefreshCw className="w-8 h-8 text-brand animate-spin" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PageHeader
        eyebrow="Risk Management"
        title="Key Risk Indicators (KRI)"
        subtitle="Analiza krytycznych ryzyk operacyjnych, terminowych i kosztowych."
        actions={
          <Button onClick={loadData}>
            <RefreshCw className="w-4 h-4 mr-1" /> Odswiez
          </Button>
        }
      />

      <div className="max-w-7xl mx-auto space-y-8 pb-20">
        {Object.keys(riskGroups).length === 0 ? (
          <Card className="p-20 text-center flex flex-col items-center gap-4">
            <AlertOctagon className="w-12 h-12 text-emerald-500/50" />
            <p className="text-slate-400 font-medium">Brak zidentyfikowanych ryzyk krytycznych. System jest w normie.</p>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Deadline / Flow */}
            {(riskGroups.DEADLINE || riskGroups.FLOW) && (
              <Card title="Deadline & Flow Risks" icon={<Clock className="text-blue-400" />}>
                <div className="space-y-4">
                  {[...(riskGroups.DEADLINE || []), ...(riskGroups.FLOW || [])].map((risk, idx) => (
                    <RiskItem 
                      key={idx} 
                      risk={risk} 
                      color={severityColor(risk.severity)} 
                      href={getSourceLink(risk)} 
                      onAction={() => {
                        setSelectedRisk(risk);
                        setIsActionModalOpen(true);
                      }}
                    />
                  ))}
                </div>
              </Card>
            )}

            {/* Material */}
            {riskGroups.MATERIAL && (
              <Card title="Material Risks" icon={<Package className="text-amber-400" />}>
                <div className="space-y-4">
                  {riskGroups.MATERIAL.map((risk, idx) => (
                    <RiskItem 
                      key={idx} 
                      risk={risk} 
                      color={severityColor(risk.severity)} 
                      href={getSourceLink(risk)} 
                      onAction={() => {
                        setSelectedRisk(risk);
                        setIsActionModalOpen(true);
                      }}
                    />
                  ))}
                </div>
              </Card>
            )}

            {/* Cost */}
            {riskGroups.COST && (
              <Card title="Financial / Cost Risks" icon={<DollarSign className="text-emerald-400" />}>
                <div className="space-y-4">
                  {riskGroups.COST.map((risk, idx) => (
                    <RiskItem 
                      key={idx} 
                      risk={risk} 
                      color={severityColor(risk.severity)} 
                      href={getSourceLink(risk)} 
                      onAction={() => {
                        setSelectedRisk(risk);
                        setIsActionModalOpen(true);
                      }}
                    />
                  ))}
                </div>
              </Card>
            )}

            {/* Process */}
            {riskGroups.PROCESS && (
              <Card title="Process & Quality Risks" icon={<Activity className="text-purple-400" />}>
                <div className="space-y-4">
                  {riskGroups.PROCESS.map((risk, idx) => (
                    <RiskItem 
                      key={idx} 
                      risk={risk} 
                      color={severityColor(risk.severity)} 
                      href={getSourceLink(risk)} 
                      onAction={() => {
                        setSelectedRisk(risk);
                        setIsActionModalOpen(true);
                      }}
                    />
                  ))}
                </div>
              </Card>
            )}
          </div>
        )}
      </div>

      {selectedRisk && (
        <IssueActionModal
          isOpen={isActionModalOpen}
          onClose={() => {
            setIsActionModalOpen(false);
            setSelectedRisk(null);
          }}
          issue={selectedRisk.source_type === "issue" ? {
            id: selectedRisk.source_id,
            title: selectedRisk.title,
            status: selectedRisk.status || "nowe",
            owner: selectedRisk.owner || "",
            priority_manual: selectedRisk.priority || "normalny",
            due_date: selectedRisk.due_date || "",
            // Mock other required fields if necessary
          } as any : null}
          onUpdate={loadData}
        />
      )}
    </AppShell>
  );
}

function RiskItem({ risk, color, href, onAction }: { risk: any, color: string, href: string | null, onAction?: () => void }) {
  const statusLabels: Record<string, string> = {
    nowe: "Open",
    w_toku: "In Progress",
    zablokowane: "Blocked",
    zamkniete: "Resolved",
  };

  const isOverdue = risk.due_date && new Date(risk.due_date) < new Date() && risk.status !== "zamkniete";
  const isEscalated = risk.severity === "CRITICAL" || isOverdue;

  return (
    <div className={clsx(
      "group relative p-4 bg-white/5 border rounded-xl hover:bg-white/10 transition-all overflow-hidden",
      isEscalated ? "border-red-500/30 bg-red-500/5" : "border-white/10"
    )}>
      {isEscalated && <div className="absolute left-0 top-0 bottom-0 w-1 bg-red-500" />}
      <div className="flex justify-between items-start mb-2">
        <div className="flex items-center gap-2">
          <span className={clsx("px-2 py-0.5 rounded text-[10px] font-black uppercase border", color)}>
            {risk.severity}
          </span>
          {risk.status && (
            <span className="text-[9px] font-bold text-slate-500 uppercase bg-white/5 px-2 py-0.5 rounded">
              {statusLabels[risk.status] || risk.status}
            </span>
          )}
          {isEscalated && (
            <span className="text-[9px] font-black text-red-500 uppercase tracking-tighter bg-red-500/10 px-1 rounded">Escalated</span>
          )}
        </div>
        <span className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">
          {risk.category}
        </span>
      </div>
      <h3 className="text-sm font-bold text-white mb-1 group-hover:text-brand transition-colors">{risk.title}</h3>
      <p className="text-xs text-slate-400 leading-relaxed mb-3">
        {risk.details}
      </p>
      
      <div className="flex items-center justify-between border-t border-white/5 pt-3 mt-2">
        <div className="flex flex-col gap-0.5">
          <div className="flex items-center gap-1.5 text-[9px] text-slate-500 font-bold uppercase">
            <Activity size={10} /> {risk.actor || risk.owner || "System"}
          </div>
          {risk.due_date && (
            <div className="flex items-center gap-1.5 text-[9px] text-orange-500/70 font-bold uppercase">
              <Clock size={10} /> Due: {risk.due_date}
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          {risk.source_type === "issue" && (
            <button 
              onClick={onAction}
              className="px-2 py-1 bg-brand/10 border border-brand/20 rounded text-[10px] font-bold text-brand uppercase hover:bg-brand/20 transition-all"
            >
              Action
            </button>
          )}
          {href && (
            <Link 
              href={href} 
              className="p-1 hover:bg-white/10 rounded transition-colors text-slate-500 hover:text-white"
              title="Go to source"
            >
              <ExternalLink size={14} />
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
function getSourceLink(risk: any) {
  switch (risk.source_type) {
    case "issue": return `/operations?search=${encodeURIComponent(risk.title.replace('Overdue Issue: ', ''))}`;
    case "route_task": return "/stations/cnc";
    case "material": return `/inventory?search=${encodeURIComponent(risk.title.replace('Low Stock: ', ''))}`;
    case "order_cost": return `/orders/${risk.source_id}/costs`;
    case "audit_log": return "/admin/audit-log";
    default: return null;
  }
}
