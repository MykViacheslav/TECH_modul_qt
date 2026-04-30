"use client";

import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Card } from "@/components/ui";
import {
  Monitor,
  Activity,
  Clock,
  CheckCircle2,
  AlertCircle,
  RefreshCcw,
  User,
  Package,
  Hammer,
  Palette,
  Truck
} from "lucide-react";
import { useEffect, useState } from "react";
import { TechModulAPI, type ProductionStatus } from "@/services/api";
import { motion, AnimatePresence } from "framer-motion";
import clsx from "clsx";

export default function ProductionDashboard() {
  const [data, setData] = useState<ProductionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  const fetchStatus = async () => {
    try {
      const res = await TechModulAPI.getProductionStatus();
      setData(res);
      setLastUpdate(new Date());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000); // 10s refresh
    return () => clearInterval(interval);
  }, []);

  return (
    <AppShell>
      <PageHeader
        eyebrow="Real-Time Operation Monitoring"
        title={<>Hala <span className="text-brand-hover">Produkcyjna</span> Live</>}
        subtitle="Podglad obciazenia stanowisk, statusu zlecen i aktywnosci personelu."
        actions={
          <div className="flex items-center gap-4">
             <div className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">
                Ostatnia synch: {lastUpdate.toLocaleTimeString()}
             </div>
             <button
                onClick={fetchStatus}
                className="p-2 rounded-xl bg-white/5 border border-white/10 text-slate-400 hover:text-white transition-all"
             >
                <RefreshCcw className={clsx("w-4 h-4", loading && "animate-spin")} />
             </button>
          </div>
        }
      />

      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-6 mb-8">
         <SummaryTile
           label="Aktywne Zlecenia"
           value={data?.stats.active_orders ?? 0}
           icon={Activity}
           color="text-emerald-400"
         />
         <SummaryTile
           label="Pracownicy Online"
           value={data?.stats.online_workers ?? 0}
           icon={User}
           color="text-blue-400"
         />
         <SummaryTile
           label="Oczekujace"
           value={data?.stats.pending_tasks ?? 0}
           icon={Clock}
           color="text-orange-400"
         />
         <SummaryTile
           label="Zakonczone Dzisiaj"
           value={data?.stats.finished_today ?? 0}
           icon={CheckCircle2}
           color="text-emerald-500"
         />
         <SummaryTile
           label="Krytyczne / Blokady"
           value={data?.stats.critical_issues ?? 0}
           icon={AlertCircle}
           color="text-red-500"
         />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
         {/* Live Stations */}
         <div className="lg:col-span-3 grid grid-cols-1 md:grid-cols-2 gap-6">
            {data?.workstations.map((ws, idx) => (
               <StationCard key={ws.id} station={ws} index={idx} />
            ))}
         </div>

         {/* Sidebar: Activity Feed */}
         <div className="space-y-6">
            <Card className="p-6 bg-panel-solid/40 border-brand-ring/10">
               <h3 className="eyebrow-brand mb-6 flex items-center gap-2">
                  <Activity className="w-4 h-4" /> Live Log
               </h3>
               <div className="space-y-6">
                  {data?.activity_log.map((log, i) => (
                     <div key={i} className="relative pl-6 border-l border-white/5 pb-2">
                        <div className="absolute left-[-5px] top-1.5 w-2 h-2 rounded-full bg-brand shadow-brand-glow" />
                        <div className="text-[10px] text-slate-500 font-bold uppercase tracking-tighter mb-1">
                           {log.time}
                        </div>
                        <p className="text-[11px] text-slate-300 leading-snug">
                           <span className="text-white font-bold">{log.worker}</span> {log.action}
                        </p>
                        <p className="text-[9px] text-brand-hover mt-1 font-black underline decoration-brand/30">
                           {log.order}
                        </p>
                     </div>
                  ))}
               </div>
            </Card>

            <button className="w-full py-5 rounded-2xl bg-brand/10 border border-brand/20 text-brand-hover text-[10px] font-black uppercase tracking-widest hover:bg-brand/20 transition-all flex items-center justify-center gap-2 shadow-lg">
               Drukuj Karty Produkcyjne <RefreshCcw className="w-3.5 h-3.5" />
            </button>
         </div>
      </div>
    </AppShell>
  );
}

function SummaryTile({ label, value, icon: Icon, color }: any) {
   return (
      <Card className="p-5 bg-panel-solid/30 border-white/5 flex items-center gap-4">
         <div className={clsx("p-3 rounded-2xl bg-white/5", color)}>
            <Icon className="w-6 h-6" />
         </div>
         <div>
            <div className="text-[10px] font-black text-slate-500 uppercase tracking-widest">{label}</div>
            <div className="text-2xl font-black text-white italic">{value}</div>
         </div>
      </Card>
   );
}

function StationCard({ station, index }: { station: any, index: number }) {
   const icons: any = {
      'CNC': RefreshCcw,
      'Oklejanie': Hammer,
      'Lakiernia': Palette,
      'Montaz': Package,
      'Biuro': Monitor,
      'Logistyka': Truck
   };
   const Icon = icons[station.id] || icons[station.name] || Activity;

   return (
      <motion.div
         initial={{ opacity: 0, scale: 0.95, y: 10 }}
         animate={{ opacity: 1, scale: 1, y: 0 }}
         transition={{ delay: index * 0.1 }}
      >
         <Card className={clsx(
           "p-6 h-full transition-all border-l-4",
           station.status === 'BUSY' ? "border-brand border-l-brand bg-brand/5 shadow-brand-glow" :
           station.status === 'IDLE' ? "border-white/5 border-l-slate-600 bg-white/2" :
           "border-emerald-500/20 border-l-emerald-500 bg-emerald-500/5"
         )}>
            <div className="flex items-center justify-between mb-6">
               <div className="flex items-center gap-3">
                  <div className={clsx(
                    "p-2.5 rounded-xl",
                    station.status === 'BUSY' ? "bg-brand/20 text-brand-hover" : "bg-white/5 text-slate-400"
                  )}>
                     <Icon className="w-5 h-5" />
                  </div>
                  <div>
                     <h3 className="text-sm font-black uppercase tracking-widest text-white italic">{station.name}</h3>
                     <p className="text-[9px] text-slate-500 font-black uppercase">{station.position || 'Studio'}</p>
                  </div>
               </div>
               <div className={clsx(
                  "px-2.5 py-1 rounded-full text-[9px] font-black uppercase tracking-widest italic",
                  station.status === 'BUSY' ? "bg-brand/10 text-brand-hover border border-brand/20" :
                  station.status === 'IDLE' ? "bg-white/5 text-slate-500 border border-white/5 font-normal" :
                  "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
               )}>
                  {station.status === 'BUSY' ? 'W TRAKCIE' : station.status === 'IDLE' ? 'CZEKA' : 'GOTOWE'}
               </div>
            </div>

            {station.active_job ? (
               <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-canvas-deep/50 border border-white/5">
                     <div className="text-[9px] font-black text-slate-600 uppercase tracking-widest mb-1">Zadanie Aktywne</div>
                     <div className="text-xs font-bold text-white truncate">{station.active_job.title}</div>
                  </div>
                  <div className="flex items-center gap-4">
                     <div className="flex -space-x-2">
                        {station.workers.map((w: string, i: number) => (
                           <div key={i} className="w-8 h-8 rounded-full bg-brand-soft border-2 border-canvas-deep flex items-center justify-center text-[10px] font-bold text-white shadow-lg">
                              {w.substring(0, 2).toUpperCase()}
                           </div>
                        ))}
                     </div>
                     <div className="text-[10px] text-slate-400 italic">
                        Realizacja: <strong>{station.progress}%</strong>
                     </div>
                  </div>
                  {/* Progress bar */}
                  <div className="w-full h-1 bg-white/5 rounded-full overflow-hidden">
                     <motion.div
                       initial={{ width: 0 }}
                       animate={{ width: `${station.progress}%` }}
                       className="h-full bg-brand shadow-brand-glow"
                     />
                  </div>
               </div>
            ) : (
               <div className="py-8 flex flex-col items-center justify-center text-center opacity-40">
                  <RefreshCcw className="w-8 h-8 text-slate-600 mb-3" />
                  <span className="text-[10px] font-black uppercase text-slate-600 tracking-widest">Oczekiwanie na skan...</span>
               </div>
            )}
         </Card>
      </motion.div>
   );
}


