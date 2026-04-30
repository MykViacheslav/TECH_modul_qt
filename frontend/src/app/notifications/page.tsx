"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Card, Button } from "@/components/ui";
import { 
  TechModulAPI, 
  type NotificationItem 
} from "@/services/api";
import { 
  AlertCircle, 
  Clock, 
  UserPlus, 
  ShieldAlert, 
  RefreshCw, 
  ChevronRight,
  User,
  Activity,
  History,
  ShoppingCart
} from "lucide-react";
import clsx from "clsx";
import Link from "next/link";
import IssueActionModal from "@/components/IssueActionModal";

export default function NotificationsPage() {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedItem, setSelectedItem] = useState<NotificationItem | null>(null);
  const [isActionModalOpen, setIsActionModalOpen] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await TechModulAPI.getNotificationItems();
      setItems(res);
    } catch (e: any) {
      setError(e?.message || "Failed to load notifications");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case "OVERDUE": return <Clock className="w-4 h-4 text-orange-400" />;
      case "UNASSIGNED": return <UserPlus className="w-4 h-4 text-red-400" />;
      case "BLOCKED_LONG": return <ShieldAlert className="w-4 h-4 text-amber-400" />;
      case "ALARM": return <AlertCircle className="w-4 h-4 text-red-500" />;
      case "MATERIAL": return <ShoppingCart className="w-4 h-4 text-blue-400" />;
      default: return <Activity className="w-4 h-4 text-slate-400" />;
    }
  };

  const getSourceLink = (item: NotificationItem) => {
    switch (item.source_type) {
      case "issue": return `/operations?search=${encodeURIComponent(item.title.replace(/Overdue: |Unassigned Urgent: |Blocked >48h: /, ""))}`;
      case "alarm": return "/alarms";
      case "material_shortage": return "/procurement/suggestions";
      case "procurement_item": return "/procurement/execution";
      case "production_task": return "/production/workflow/readiness";
      default: return null;
    }
  };

  return (
    <AppShell>
      <PageHeader
        eyebrow="Attention Management"
        title="Escalations & Alerts"
        subtitle="Operational items requiring immediate manager or admin attention."
        actions={
          <Button onClick={loadData} disabled={loading}>
            <RefreshCw className={clsx("w-4 h-4 mr-1", loading && "animate-spin")} /> Refresh
          </Button>
        }
      />

      <div className="max-w-5xl mx-auto space-y-6 pb-20">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <RefreshCw className="w-8 h-8 text-brand animate-spin" />
          </div>
        ) : error ? (
          <Card className="p-10 text-center border-red-500/20">
            <ShieldAlert className="w-12 h-12 text-red-500/50 mx-auto mb-4" />
            <p className="text-red-400 font-bold">{error}</p>
          </Card>
        ) : items.length === 0 ? (
          <Card className="p-20 text-center flex flex-col items-center gap-4 border-emerald-500/10">
            <Activity className="w-12 h-12 text-emerald-500/30" />
            <p className="text-slate-400 font-medium">No urgent items found. All clear.</p>
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {items.map((item) => (
              <Card key={item.id} padded={false} className="group hover:border-white/20 transition-all overflow-hidden border-white/5">
                <div className="flex flex-col md:flex-row">
                  {/* Category Indicator */}
                  <div className={clsx(
                    "w-1 md:w-2 shrink-0",
                    item.severity === "CRITICAL" ? "bg-red-500" : 
                    item.severity === "HIGH" ? "bg-orange-500" : "bg-amber-500"
                  )} />
                  
                  <div className="p-5 flex-1 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 bg-panel-solid/40">
                    <div className="flex items-start gap-4">
                      <div className="p-2 rounded-lg bg-white/5 border border-white/10 mt-1">
                        {getCategoryIcon(item.category)}
                      </div>
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className={clsx(
                            "text-[10px] font-black uppercase px-2 py-0.5 rounded border",
                            item.severity === "CRITICAL" ? "text-red-400 border-red-500/30 bg-red-500/10" :
                            item.severity === "HIGH" ? "text-orange-400 border-orange-500/30 bg-orange-500/10" :
                            "text-amber-400 border-amber-500/30 bg-amber-500/10"
                          )}>
                            {item.severity}
                          </span>
                          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">{item.category}</span>
                        </div>
                        <h3 className="text-base font-bold text-white group-hover:text-brand transition-colors">{item.title}</h3>
                        <p className="text-xs text-slate-400 mt-1">{item.details}</p>
                        
                        <div className="flex items-center gap-4 mt-3">
                          <div className="flex items-center gap-1.5 text-[10px] text-slate-500 font-bold uppercase">
                            <User size={10} /> {item.owner || "Unassigned"}
                          </div>
                          {item.escalation_reason && (
                            <div className="flex items-center gap-1.5 text-[10px] text-red-400/80 font-bold uppercase italic">
                              <ShieldAlert size={10} /> {item.escalation_reason}
                            </div>
                          )}
                          <div className="flex items-center gap-1.5 text-[10px] text-slate-600 font-mono">
                            <History size={10} /> {new Date(item.timestamp).toLocaleString()}
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 self-end md:self-center">
                      {item.source_type === "issue" && (
                        <Button 
                          variant="primary" 
                          size="sm"
                          onClick={() => {
                            setSelectedItem(item);
                            setIsActionModalOpen(true);
                          }}
                        >
                          Action
                        </Button>
                      )}
                      {getSourceLink(item) && (
                        <Link href={getSourceLink(item)!}>
                          <Button variant="secondary" size="sm">
                            Details <ChevronRight className="w-3.5 h-3.5 ml-1" />
                          </Button>
                        </Link>
                      )}
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {selectedItem && (
        <IssueActionModal
          isOpen={isActionModalOpen}
          onClose={() => {
            setIsActionModalOpen(false);
            setSelectedItem(null);
          }}
          issue={selectedItem.source_type === "issue" ? {
            id: selectedItem.source_id.toString(),
            title: selectedItem.title.replace(/Overdue: |Unassigned Urgent: |Blocked >48h: /, ""),
            status: selectedItem.status || "nowe",
            owner: selectedItem.owner === "Unassigned" ? "" : (selectedItem.owner || ""),
            priority_manual: selectedItem.priority || "normalny",
            due_date: selectedItem.timestamp.split(" ")[0] || "",
          } as any : null}
          onUpdate={loadData}
        />
      )}
    </AppShell>
  );
}
