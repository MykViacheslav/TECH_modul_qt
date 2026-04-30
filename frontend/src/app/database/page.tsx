"use client";

import React from "react";
import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Card, Button } from "@/components/ui";
import {
  Database,
  BookOpen,
  Warehouse,
  ReceiptText,
  ChevronRight,
  ArrowUpRight,
  ExternalLink,
  Zap,
  ShieldCheck,
  Activity,
  Box,
  FileText
} from "lucide-react";
import Link from "next/link";

export default function DatabaseHubPage() {
  const BASES = [
    {
      id: "library",
      title: "Biblioteka Materialow",
      subtitle: "MSI Central Registry",
      desc: "Kompletny katalog producentow (EGGER, Blum, Swiss Krono). Parametry techniczne, dekory i cenniki.",
      icon: Database,
      href: "/database/library",
      color: "text-brand",
      bg: "bg-brand/10",
      stats: [
        { label: "Pozycje", val: "1,240" },
        { label: "Producenci", val: "12" }
      ]
    },
    {
      id: "knowledge",
      title: "Baza Wiedzy Technicznej",
      subtitle: "Engineering Wiki",
      desc: "Instrukcje montazu, zasady obrobki CNC, standardy lakiernicze i certyfikaty.",
      icon: BookOpen,
      href: "/database/knowledge",
      color: "text-blue-400",
      bg: "bg-blue-400/10",
      stats: [
        { label: "Artykuly", val: "84" },
        { label: "Manuals", val: "15" }
      ]
    },
    {
      id: "warehouse",
      title: "Magazyn i Zapasy",
      subtitle: "Inventory Management",
      desc: "Stany magazynowe w czasie rzeczywistym, przyjecia towaru, rezerwacje pod projekty.",
      icon: Warehouse,
      href: "/database/warehouse",
      color: "text-amber-400",
      bg: "bg-amber-400/10",
      stats: [
        { label: "Wartosc", val: "142k" },
        { label: "Alert", val: "3" }
      ]
    },
    {
      id: "invoices",
      title: "Faktury i Import",
      subtitle: "Invoice Review",
      desc: "Import PDF faktur, reczna weryfikacja pozycji i bezpieczny confirm/export do dostaw.",
      icon: ReceiptText,
      href: "/database/invoices",
      color: "text-emerald-400",
      bg: "bg-emerald-400/10",
      stats: [
        { label: "Tryb", val: "Phase 1" },
        { label: "Review", val: "Manual" }
      ]
    }
  ];

  return (
    <AppShell>
      <PageHeader
        eyebrow="Tech Modul Management"
        title={<>Centralny <span className="text-brand-hover">Hub Danych</span></>}
        subtitle="Zarzadzanie fundamentem technicznym produkcji: od parametrow materialowych po instrukcje montazu."
      />

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 mb-12">
        {BASES.map(base => (
          <Link key={base.id} href={base.href} className="group">
            <Card className="h-full flex flex-col border-subtle hover:border-brand/40 hover:bg-brand/[0.02] transition-all duration-300 relative overflow-hidden">
               <div className={`absolute -right-8 -top-8 w-32 h-32 ${base.bg} rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity`} />

               <div className="flex items-start justify-between mb-6">
                 <div className={`p-4 rounded-2xl ${base.bg} ${base.color} border border-white/5`}>
                   <base.icon size={28} />
                 </div>
                 <div className="text-slate-600 group-hover:text-brand transition-colors">
                   <ArrowUpRight size={24} />
                 </div>
               </div>

               <div className="flex-1">
                 <h3 className="text-[10px] font-black tracking-widest text-slate-500 uppercase mb-1">{base.subtitle}</h3>
                 <h2 className="text-2xl font-bold text-white mb-3 group-hover:text-brand transition-colors">{base.title}</h2>
                 <p className="text-sm text-slate-400 leading-relaxed">{base.desc}</p>
               </div>

               <div className="mt-8 flex items-center gap-4 pt-6 border-t border-subtle font-mono text-[10px] font-bold">
                 {base.stats.map(s => (
                   <div key={s.label} className="flex gap-2 bg-canvas-deep px-3 py-1.5 rounded-lg border border-subtle">
                     <span className="text-slate-500">{s.label}:</span>
                     <span className="text-slate-200">{s.val}</span>
                   </div>
                 ))}
               </div>
            </Card>
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 pb-20">
         <Link href="/admin/projects">
          <Card className="bg-panel-solid/40 border-subtle flex flex-col justify-center items-center py-10 text-center group cursor-pointer hover:bg-white/5 transition-colors h-full">
              <div className="w-14 h-14 rounded-full bg-slate-800 flex items-center justify-center text-slate-500 mb-4 group-hover:bg-slate-700 group-hover:text-brand transition-colors">
                <FileText size={24} />
              </div>
              <h4 className="font-bold text-slate-200">Zarządzaj Projektami</h4>
              <p className="text-[10px] text-slate-500 mt-1 uppercase font-black">Admin / Projects</p>
          </Card>
         </Link>

         <Link href="/admin/orders">
          <Card className="bg-panel-solid/40 border-subtle flex flex-col justify-center items-center py-10 text-center group cursor-pointer hover:bg-white/5 transition-colors h-full">
              <div className="w-14 h-14 rounded-full bg-slate-800 flex items-center justify-center text-slate-500 mb-4 group-hover:bg-slate-700 group-hover:text-amber-400 transition-colors">
                <ReceiptText size={24} />
              </div>
              <h4 className="font-bold text-slate-200">Zarządzaj Zamówieniami</h4>
              <p className="text-[10px] text-slate-500 mt-1 uppercase font-black">Admin / Orders</p>
          </Card>
         </Link>

         <Link href="/admin/backups">
          <Card className="bg-panel-solid/40 border-subtle flex flex-col justify-center items-center py-10 text-center group cursor-pointer hover:bg-white/5 transition-colors h-full">
              <div className="w-14 h-14 rounded-full bg-slate-800 flex items-center justify-center text-slate-500 mb-4 group-hover:bg-slate-700 group-hover:text-emerald-400 transition-colors">
                <ShieldCheck size={24} />
              </div>
              <h4 className="font-bold text-slate-200">Backupy i Bezpieczeństwo</h4>
              <p className="text-[10px] text-slate-500 mt-1 uppercase font-black">Admin / Backups</p>
          </Card>
         </Link>
      </div>

      <div className="fixed bottom-0 left-0 right-0 bg-canvas-deep/80 backdrop-blur-xl border-t border-white/5 px-8 h-12 flex items-center justify-between pointer-events-none">
         <div className="flex items-center gap-6">
            <div className="flex items-center gap-2 text-[10px] font-bold text-slate-500">
               <Activity size={10} className="text-emerald-500 animate-pulse" />
               SERVER: ONLINE
            </div>
            <div className="flex items-center gap-2 text-[10px] font-bold text-slate-500">
               <Box size={10} />
               RESOURCES: 100%
            </div>
         </div>
         <div className="flex gap-4">
            <span className="text-[10px] font-bold text-slate-600">DATABASE_ENGINE_SQLITE_V3</span>
            <span className="text-[10px] font-bold text-slate-600">MSI_ROUTING: ACTIVE</span>
         </div>
      </div>
    </AppShell>
  );
}
