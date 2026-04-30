"use client";

import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Card } from "@/components/ui";
import {
  Lightbulb,
  Map,
  ChevronRight,
  FilePlus2,
  Compass,
  Clock,
  Wallet,
  Monitor,
  TriangleAlert,
  ArrowRight,
  Target,
  Box,
  Cpu
} from "lucide-react";
import { motion } from "framer-motion";

const STEPS = [
  {
    title: "1. KREACJA I KLIENT",
    desc: "Zacznij od 'Nowego Zamowienia'. Wprowadz dane kontrahenta i ustal budzet. System automatycznie zaozy karte projektu.",
    icon: FilePlus2,
    color: "text-emerald-400",
    bg: "bg-emerald-500/10"
  },
  {
    title: "2. IMPORT 3D & POMIAR",
    desc: "Zaimportuj pliki .project z programow GIBLAB lub 3D Konstruktor. System wyczyta formatki i okucia. Dodaj pomiary z ImageMeter Pro.",
    icon: Box,
    color: "text-blue-400",
    bg: "bg-blue-500/10"
  },
  {
    title: "3. TECHNIKA (SCIANA)",
    desc: "W module 'Sciana' nanies punkty instalacyjne (prad, woda, gaz). To kluczowe, aby meble pasoway do przyaczy na montazu.",
    icon: Compass,
    color: "text-red-400",
    bg: "bg-red-500/10"
  },
  {
    title: "4. PRODUKCJA LIVE",
    desc: "Pracownicy loguja sie w Kiosku RCP. W 'Panelu Produkcji' widzisz na zywo postep prac na lakierni, CNC i montazu.",
    icon: Monitor,
    color: "text-indigo-400",
    bg: "bg-indigo-500/10"
  },
  {
    title: "5. FINANSE I EXPORT",
    desc: "Sprawdz rentownosc w 'Finansach Firmy'. Wyeksportuj listy ciec do GIBLAB, aby maszyny CNC mogy zaczac prace.",
    icon: Cpu,
    color: "text-orange-400",
    bg: "bg-orange-500/10"
  }
];

export default function HelpPage() {
  return (
    <AppShell>
      <PageHeader
        eyebrow="Onboarding System"
        title={<>Centrum <span className="text-brand-hover">Wiedzy</span></>}
        subtitle="Zintegrowany przepyw pracy: od GIBLAB/3D Konstruktor po montaz u klienta."
      />

      <div className="max-w-4xl mx-auto space-y-12 py-10">
         <div className="text-center space-y-4">
            <div className="inline-flex p-4 rounded-3xl bg-brand/10 border border-brand/20 text-brand-hover shadow-brand-glow mb-4">
               <Map className="w-10 h-10" />
            </div>
            <h2 className="text-3xl font-black italic tracking-tighter uppercase text-white">Ecosystem TECH_modu</h2>
            <p className="text-slate-500 text-sm max-w-lg mx-auto leading-relaxed">
               Nasz system to pomost miedzy projektowaniem w <strong>3D Konstruktor / GIBLAB</strong>, a rzeczywista produkcja i finansami.
            </p>
         </div>

         <div className="relative">
            <div className="absolute left-10 md:left-1/2 top-0 bottom-0 w-px bg-white/5 -translate-x-1/2 hidden md:block" />

            <div className="space-y-16">
               {STEPS.map((step, idx) => (
                 <motion.div
                   key={step.title}
                   initial={{ opacity: 0, x: idx % 2 === 0 ? -20 : 20 }}
                   whileInView={{ opacity: 1, x: 0 }}
                   viewport={{ once: true }}
                   className={`flex flex-col md:flex-row items-center gap-8 ${idx % 2 !== 0 ? 'md:flex-row-reverse' : ''}`}
                 >
                    <div className="relative z-10">
                       <div className={`w-20 h-20 rounded-3xl ${step.bg} border border-white/10 flex items-center justify-center p-5 shadow-2xl`}>
                          <step.icon className={`w-full h-full ${step.color}`} />
                       </div>
                       <div className="absolute -bottom-2 -right-2 w-8 h-8 rounded-full bg-canvas-deep border border-white/5 flex items-center justify-center text-[10px] font-black text-white">
                          0{idx + 1}
                       </div>
                    </div>

                    <Card className="flex-1 p-8 bg-panel-solid/40 hover:border-brand-hover/30 transition-all border-white/5 group relative overflow-hidden">
                       <div className="absolute top-0 right-0 w-32 h-32 bg-brand/5 rounded-full -mr-16 -mt-16 blur-3xl pointer-events-none" />
                       <h3 className={`text-lg font-black tracking-widest ${step.color} mb-3 italic`}>{step.title}</h3>
                       <p className="text-sm text-slate-400 leading-relaxed">
                          {step.desc}
                       </p>
                    </Card>
                 </motion.div>
               ))}
            </div>
         </div>

         <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-20">
            <Card className="p-6 border-brand-ring/10 bg-panel-solid/40">
               <div className="flex items-center gap-3 mb-4">
                  <Box className="w-5 h-5 text-blue-400" />
                  <h4 className="text-xs font-black uppercase tracking-widest text-white">Import .PROJECT</h4>
               </div>
               <p className="text-[11px] text-slate-500 leading-relaxed mb-4">
                  Obsugujemy natywny format <strong>3D Konstruktor</strong>. System mapuje materiay (pyty, obrzeza) bezposrednio na Twoje stany magazynowe w TECH_modu.
               </p>
               <div className="text-[9px] font-bold text-blue-400/60 uppercase">Manual: Importuj w 'Nowe Zamowienie' &rarr; Krok 3</div>
            </Card>

            <Card className="p-6 border-brand-ring/10 bg-panel-solid/40">
               <div className="flex items-center gap-3 mb-4">
                  <Cpu className="w-5 h-5 text-orange-400" />
                  <h4 className="text-xs font-black uppercase tracking-widest text-white">Eksport GIBLAB (CSV)</h4>
               </div>
               <p className="text-[11px] text-slate-500 leading-relaxed mb-4">
                  Generuj listy ciec zgodne z <strong>GIBLAB</strong>. Pozwala to na unikniecie recznego przepisywania wymiarow na maszynach panelowych i CNC.
               </p>
               <div className="text-[9px] font-bold text-orange-400/60 uppercase">Manual: Pobierz plik w 'Workspace' lub 'Produkcja'</div>
            </Card>
         </div>

         <div className="pt-20">
            <Card className="bg-gradient-to-br from-brand to-indigo-700 border-none p-10 text-center relative overflow-hidden text-white shadow-brand-glow">
                <Target className="w-12 h-12 mx-auto mb-6 opacity-50" />
                <h3 className="text-2xl font-black uppercase italic tracking-tighter mb-4">Gotowy do pracy?</h3>
                <p className="text-blue-100 text-sm max-w-lg mx-auto mb-8">
                   Zacznij od wprowadzenia pierwszego klienta lub zaimportuj istniejacy projekt z 3D Konstruktor.
                </p>
                <div className="flex flex-wrap justify-center gap-4">
                   <button className="px-8 py-3 rounded-xl bg-white text-brand font-black uppercase tracking-widest text-[10px] hover:bg-slate-100 transition-all">
                      Nowe Zamowienie
                   </button>
                   <button className="px-8 py-3 rounded-xl bg-black/20 border border-white/20 text-white font-black uppercase tracking-widest text-[10px] hover:bg-black/30 transition-all">
                      Centrum Filmow Pomocy
                   </button>
                </div>
            </Card>
         </div>
      </div>
    </AppShell>
  );
}
