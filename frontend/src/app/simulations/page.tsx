"use client";

import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Card, Button } from "@/components/ui";
import {
  Play,
  RotateCcw,
  ShoppingCart,
  Cpu,
  DollarSign,
  ChevronRight,
  Sparkles,
  Search,
  CheckCircle2,
  Trash2
} from "lucide-react";
import { useState } from "react";
import { motion } from "framer-motion";
import clsx from "clsx";

export default function SimulationsPage() {
  const [activeSim, setActiveSim] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([]);

  const addLog = (msg: string) => {
    setLogs(prev => [msg, ...prev].slice(0, 10));
  };

  const runSimPurchase = () => {
    setActiveSim("shopping");
    addLog(" Start symulacji: Zakup czesciowy (Hurtownia Wieczorek)");
    setTimeout(() => addLog(" Znaleziono brak: 10x Zawias BLUM w projekcie #SZAFA-01"), 1000);
    setTimeout(() => addLog(" Akcja: Kupiono 5 sztuk (poowa) za 45.00 PLN"), 2500);
    setTimeout(() => addLog(" Wynik: Status projektu zmieniony na 'Czesciowo Dostarczony'"), 4000);
  };

  const runSimCnc = () => {
    setActiveSim("cnc");
    addLog(" Start symulacji: Ciecie CNC");
    setTimeout(() => addLog(" Zadanie wysane do Terminala CNC-01"), 1000);
    setTimeout(() => addLog(" Operator Jan zacza prace (Timer ON)"), 2500);
    setTimeout(() => addLog(" Magazyn: Pobrano 4 arkusze Dab Sonoma 18mm"), 4000);
    setTimeout(() => addLog(" Gotowe: Elementy przesuniete do Lakierni"), 5500);
  };

  const runSimFinance = () => {
    setActiveSim("finance");
    addLog(" Start symulacji: Optymalizacja Zysku");
    setTimeout(() => addLog(" Analiza 20 projektow..."), 1000);
    setTimeout(() => addLog(" Rekomendacja: Dokoncz zbior elementow 'Biuro Bis', by odblokowac 12 000 PLN"), 3000);
    setTimeout(() => addLog(" Akcja: Podniesienie priorytetu zlecenia"), 4500);
  };

  return (
    <AppShell>
      <PageHeader
        eyebrow="Development & Training"
        title={<>Centrum <span className="text-brand-hover">Symulacji Systemowych</span></>}
        subtitle="Sprawdz jak system reaguje na zdarzenia produkcyjne i finansowe."
      />

      <div className="max-w-6xl mx-auto py-8 grid grid-cols-1 lg:grid-cols-4 gap-8">
         {/* SIMULATION SELECTOR */}
         <div className="lg:col-span-3 space-y-6">
            <h3 className="eyebrow-brand px-2">Wybierz Symulacje do uruchomienia</h3>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
               <SimCard
                 title="Zakupy i Ceny"
                 desc="Symuluj zakup 5/10 zawiasow w hurtowni Wieczorek i sprawdz budzet."
                 icon={<ShoppingCart />}
                 onClick={runSimPurchase}
                 active={activeSim === 'shopping'}
                 color="emerald"
               />
               <SimCard
                 title="Praca CNC"
                 desc="Uruchom proces ciecia, zuzycie materiau i rejestracje czasu."
                 icon={<Cpu />}
                 onClick={runSimCnc}
                 active={activeSim === 'cnc'}
                 color="brand"
               />
               <SimCard
                 title="Radar Zysku"
                 desc="Zobacz jak AI wybiera projekt do dokonczenia dla najlepszego wyniku."
                 icon={<DollarSign />}
                 onClick={runSimFinance}
                 active={activeSim === 'finance'}
                 color="amber"
               />
            </div>

            {/* LIVE SIMULATION VIEW */}
            <Card className="min-h-[400px] border-white/5 bg-panel-solid/20 relative overflow-hidden flex flex-col">
               <div className="absolute top-0 right-0 p-8 opacity-[0.03]">
                  {activeSim === 'cnc' && <Cpu size={200} />}
                  {activeSim === 'shopping' && <ShoppingCart size={200} />}
                  {activeSim === 'finance' && <DollarSign size={200} />}
               </div>

               <div className="p-8 flex-1">
                  {!activeSim ? (
                    <div className="h-full flex flex-col items-center justify-center text-center opacity-30">
                       <Sparkles size={48} className="mb-4" />
                       <p className="text-sm font-black uppercase tracking-widest">Wybierz symulacje z gory aby zaczac</p>
                    </div>
                  ) : (
                    <div className="space-y-6">
                       <div className="flex items-center gap-2 mb-8">
                          <span className="w-2 h-2 rounded-full bg-brand animate-pulse" />
                          <span className="text-[10px] font-black uppercase tracking-widest text-brand-hover">Symulacja w toku...</span>
                       </div>

                       <div className="space-y-4">
                          {logs.map((log, i) => (
                             <motion.div
                               key={i}
                               initial={{ opacity: 0, x: -10 }}
                               animate={{ opacity: 1, x: 0 }}
                               className="flex items-center gap-3 text-sm font-bold text-slate-300"
                             >
                                <ChevronRight size={14} className="text-brand" /> {log}
                             </motion.div>
                          ))}
                       </div>
                    </div>
                  )}
               </div>
            </Card>
         </div>

         {/* STATS PANEL */}
         <div className="space-y-6">
            <h3 className="eyebrow-brand">Status Systemu</h3>
            <Card className="p-6 bg-canvas-deep border-white/5">
                <div className="space-y-6">
                   <div className="flex flex-col">
                      <span className="text-[8px] font-black text-slate-600 uppercase mb-1">Materiay na stanie</span>
                      <span className="text-xl font-black italic">1,240 szt.</span>
                   </div>
                   <div className="flex flex-col">
                      <span className="text-[8px] font-black text-slate-600 uppercase mb-1">Wydajnosc CNC</span>
                      <span className="text-xl font-black text-emerald-500 italic">94%</span>
                   </div>
                   <div className="flex flex-col">
                      <span className="text-[8px] font-black text-slate-600 uppercase mb-1">Pynnosc (Cash Flow)</span>
                      <span className="text-xl font-black text-brand-hover italic">Doskonaa</span>
                   </div>
                </div>
                <Button className="w-full mt-8 bg-panel-solid border-white/5 text-[10px] font-black uppercase">Zresetuj Dane</Button>
            </Card>

            <div className="p-6 rounded-3xl bg-brand/10 border border-brand/20">
               <div className="flex items-center gap-2 mb-3">
                  <Sparkles size={16} className="text-brand-hover" />
                  <span className="text-[9px] font-black text-brand-hover uppercase tracking-widest">Zadanie dla Ciebie</span>
               </div>
               <p className="text-[11px] text-slate-400 leading-relaxed font-bold">
                  Dodaj teraz pierwsze stanowisko produkcyjne (CNC) w module konfiguracji serwera.
               </p>
            </div>
         </div>
      </div>
    </AppShell>
  );
}

function SimCard({ title, desc, icon, onClick, active, color }: any) {
  return (
    <Card
      onClick={onClick}
      className={clsx(
        "p-6 cursor-pointer transition-all hover:scale-105 active:scale-95 group",
        active ? `border-${color}-500 bg-${color}-500/10` : "border-white/5 bg-panel-solid/30"
      )}
    >
       <div className={clsx(
         "w-12 h-12 rounded-2xl flex items-center justify-center mb-4 transition-all",
         active ? `bg-${color}-500 text-white` : "bg-white/5 text-slate-500 group-hover:text-white group-hover:bg-white/10"
       )}>
          {icon}
       </div>
       <h4 className="text-sm font-black uppercase italic text-white mb-2">{title}</h4>
       <p className="text-[11px] text-slate-500 leading-normal font-bold line-clamp-2">{desc}</p>
    </Card>
  );
}
