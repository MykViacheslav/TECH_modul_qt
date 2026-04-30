"use client";

import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Card } from "@/components/ui";
import { useEffect, useState } from "react";
import { TechModulAPI, type OrderRecord } from "@/services/api";
import { motion, AnimatePresence } from "framer-motion";
import clsx from "clsx";
import {
  PenTool,
  Package,
  Hammer,
  Wrench,
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  User,
  Clock,
  Printer,
} from "lucide-react";

const WORKFLOW_STAGES = [
  { id: "Rysunek", label: "Rysunek", icon: PenTool, color: "text-blue-400 bg-blue-400/10 border-blue-400/20" },
  { id: "Materiay", label: "Materiay zamow", icon: Package, color: "text-amber-400 bg-amber-400/10 border-amber-400/20" },
  { id: "Produkcja", label: "W Produkcji", icon: Hammer, color: "text-brand-hover bg-brand/10 border-brand/20 shadow-[0_0_15px_rgba(59,130,246,0.3)]" },
  { id: "Montaz", label: "Montaz u Klienta", icon: Wrench, color: "text-purple-400 bg-purple-400/10 border-purple-400/20" },
  { id: "Poprawki", label: "Poprawki", icon: AlertTriangle, color: "text-red-400 bg-red-400/10 border-red-400/20 text-red-500 font-bold" },
  { id: "Zakonczone", label: "Zakonczone", icon: CheckCircle2, color: "text-emerald-400 bg-emerald-400/10 border-emerald-400/20 opacity-70" },
];

export default function HandoffKiosk() {
  const [orders, setOrders] = useState<OrderRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeWorkerId, setActiveWorkerId] = useState("");
  const [showScanner, setShowScanner] = useState(false);
  const [scanResult, setScanResult] = useState<string | null>(null);

  const fetchOrders = async () => {
    try {
      const res = await TechModulAPI.getOrders();
      setOrders(res);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
    const interval = setInterval(fetchOrders, 10000);
    return () => clearInterval(interval);
  }, []);

  const moveOrder = async (orderId: number, currentStatus: string, direction: 1 | -1) => {
    const currentIndex = WORKFLOW_STAGES.findIndex((s) => s.id === currentStatus);
    const newIndex = currentIndex + direction;
    if (newIndex < 0 || newIndex >= WORKFLOW_STAGES.length) return;
    if (!activeWorkerId.trim()) throw new Error("Podaj ID operatora przed zmiana statusu.");

    const newStatus = WORKFLOW_STAGES[newIndex].id;
    const res = await TechModulAPI.updateOrderStatus(orderId, {
      status: newStatus,
      worker: activeWorkerId.trim(),
    });
    if (String(res.status || "").toLowerCase() !== "success") {
      throw new Error(res.message || "Nie udao sie zmienic statusu.");
    }
    await fetchOrders();
  };

  const handleScan = async (value: string) => {
    const match = value.match(/PRJ-(\d+)/i);
    const orderId = match ? parseInt(match[1], 10) : parseInt(value, 10);

    const order = orders.find((o) => o.id === orderId);
    if (!order) {
      setScanResult("Zlecenie nie istnieje w systemie.");
      setTimeout(() => setScanResult(null), 3000);
      return;
    }
    const currentStatus = order.status || "Rysunek";
    if (currentStatus === "Zakonczone") {
      setScanResult(`Zlecenie PRJ-${orderId} jest juz zakonczone.`);
      setTimeout(() => setScanResult(null), 3000);
      return;
    }

    try {
      await moveOrder(orderId, currentStatus, 1);
      setScanResult(`Awansowano PRJ-${orderId} do nastepnego etapu.`);
      setTimeout(() => {
        setScanResult(null);
        setShowScanner(false);
      }, 2000);
    } catch (e: any) {
      setScanResult(e?.message || "Bad aktualizacji statusu.");
      setTimeout(() => setScanResult(null), 3000);
    }
  };

  return (
    <AppShell>
      <PageHeader
        eyebrow="Handoff Kiosk Terminal"
        title={<>Zarzadzanie <span className="text-brand-hover">Przepywem Zlecen</span></>}
        subtitle="Panel warsztatowy - cykl zycia zamowienia na hali produkcyjnej."
        actions={
          <div className="flex items-center gap-4">
            <input
              value={activeWorkerId}
              onChange={(e) => setActiveWorkerId(e.target.value)}
              placeholder="ID operatora"
              className="px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-xs font-black uppercase tracking-widest text-white w-44"
            />
            <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-brand/10 border border-brand/20">
              <User className="w-4 h-4 text-brand-hover" />
              <span className="text-xs font-black uppercase tracking-widest text-brand-hover">{activeWorkerId || "Brak ID"}</span>
            </div>
            <button
              onClick={() => setShowScanner(true)}
              className="px-4 py-2 border border-brand/40 bg-brand/5 rounded-xl uppercase tracking-widest text-[10px] font-black hover:bg-brand/20 transition flex items-center gap-2"
            >
              <Printer className="w-4 h-4 text-slate-400" /> Skanuj QR
            </button>
          </div>
        }
      />

      <AnimatePresence>
        {showScanner && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-canvas-deep/90 backdrop-blur-md"
            onClick={() => setShowScanner(false)}
          >
            <div
              className="bg-panel-solid border border-subtle rounded-3xl p-8 max-w-sm w-full shadow-2xl flex flex-col items-center text-center"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="w-20 h-20 rounded-full border-4 border-dashed border-brand/50 flex items-center justify-center mb-6 animate-pulse">
                <Printer className="w-8 h-8 text-brand-hover" />
              </div>
              <h3 className="text-lg font-black uppercase tracking-widest text-white mb-2">Skanuj etykiete QR</h3>
              <p className="text-xs text-slate-400 mb-6">Uzyj skanera lub wpisz kod recznie.</p>

              {scanResult ? (
                <div className={clsx("p-3 rounded-xl w-full text-xs font-bold", scanResult.toLowerCase().includes("bad") || scanResult.toLowerCase().includes("nie ") ? "bg-red-500/20 text-red-400" : "bg-emerald-500/20 text-emerald-400")}>
                  {scanResult}
                </div>
              ) : (
                <input
                  autoFocus
                  className="w-full bg-canvas-deep border border-brand/30 rounded-xl px-4 py-3 text-center text-xl font-mono text-white focus:border-brand-hover focus:ring-2 focus:ring-brand/20 outline-none"
                  placeholder="PRJ-..."
                  onKeyDown={async (e) => {
                    if (e.key === "Enter") {
                      await handleScan(e.currentTarget.value);
                      e.currentTarget.value = "";
                    }
                  }}
                />
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex gap-4 overflow-x-auto pb-8 custom-scrollbar h-[calc(100vh-200px)]">
        {WORKFLOW_STAGES.map((stage, stageIdx) => {
          const stageOrders = orders.filter(
            (o) =>
              o.status === stage.id ||
              (stage.id === "Rysunek" && (o.status === "DRAFT" || o.status === "Wycena" || o.status === "Nowe"))
          );

          return (
            <div key={stage.id} className="flex-shrink-0 w-[350px] flex flex-col h-full">
              <div className={clsx("p-4 rounded-t-2xl border-x border-t flex items-center gap-3 backdrop-blur-md", stage.color.split(" ").slice(1).join(" "))}>
                <div className="p-2 rounded-xl bg-white/10 shrink-0">
                  <stage.icon className={clsx("w-5 h-5", stage.color.split(" ")[0])} />
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-black uppercase tracking-widest text-white italic">{stage.label}</h3>
                  <div className="text-[10px] font-bold opacity-80 uppercase">{stageOrders.length} kart</div>
                </div>
              </div>

              <div className={clsx("flex-1 p-2 border-x border-b rounded-b-2xl overflow-y-auto custom-scrollbar flex flex-col gap-3", stage.color.split(" ")[2].replace("border-", "border-").replace("/20", "/10"), "bg-canvas-deep/40")}>
                {loading ? (
                  <Card className="p-3 bg-panel-solid/60 border-subtle text-xs text-slate-400">adowanie...</Card>
                ) : null}
                <AnimatePresence>
                  {stageOrders.map((order) => (
                    <motion.div key={order.id} layoutId={`order-${order.id}`} initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }}>
                      <Card className="p-4 bg-panel-solid/80 border-subtle shadow-xl hover:border-brand-hover/50 hover:shadow-brand/5 transition-all">
                        <div className="flex justify-between items-start mb-3">
                          <div>
                            <div className="text-[9px] text-slate-500 font-black uppercase tracking-widest mb-1">
                              #{order.id} | {new Date(order.created_at || "").toLocaleDateString()}
                            </div>
                            <h4 className="text-sm font-bold text-white truncate max-w-[220px]" title={order.title || order.order_name}>{order.title || order.order_name}</h4>
                          </div>
                          <div className="w-8 h-8 rounded bg-white/5 flex items-center justify-center">
                            <Clock className="w-4 h-4 text-slate-400" />
                          </div>
                        </div>
                        <p className="text-[11px] text-slate-400 mb-4 line-clamp-2">{order.client_name}</p>

                        <div className="flex items-center justify-between pt-3 border-t border-white/5">
                          <button
                            disabled={stageIdx === 0}
                            onClick={async () => {
                              try {
                                await moveOrder(order.id, stage.id, -1);
                              } catch (e: any) {
                                setScanResult(e?.message || "Bad aktualizacji statusu.");
                                setTimeout(() => setScanResult(null), 3000);
                              }
                            }}
                            className="p-2 rounded-lg bg-panel-raised hover:bg-red-500/20 hover:text-red-400 transition-colors disabled:opacity-30"
                            title="Cofnij etap"
                          >
                            <ChevronRight className="w-4 h-4 rotate-180" />
                          </button>
                          <button className="text-[9px] font-black uppercase tracking-widest text-brand-hover border border-brand/20 bg-brand/5 px-3 py-1.5 rounded">
                            Otworz Karte
                          </button>
                          <button
                            disabled={stageIdx === WORKFLOW_STAGES.length - 1}
                            onClick={async () => {
                              try {
                                await moveOrder(order.id, stage.id, 1);
                              } catch (e: any) {
                                setScanResult(e?.message || "Bad aktualizacji statusu.");
                                setTimeout(() => setScanResult(null), 3000);
                              }
                            }}
                            className="p-2 rounded-lg bg-panel-raised hover:bg-emerald-500/20 hover:text-emerald-400 transition-colors disabled:opacity-30"
                            title="Przekaz dalej"
                          >
                            <ChevronRight className="w-4 h-4" />
                          </button>
                        </div>
                      </Card>
                    </motion.div>
                  ))}
                </AnimatePresence>

                {stageOrders.length === 0 ? (
                  <div className="flex-1 flex flex-col items-center justify-center opacity-30 pointer-events-none p-6 text-center">
                    <stage.icon className="w-8 h-8 mb-3" />
                    <span className="text-[10px] uppercase tracking-widest font-black leading-tight">Brak kart na tym stanowisku</span>
                  </div>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>
    </AppShell>
  );
}
