"use client";

import AppShell from "@/components/AppShell";
import PageHeader from "@/components/PageHeader";
import { Card, Button } from "@/components/ui";
import { 
  Monitor, 
  Cpu, 
  Layers, 
  Settings, 
  Activity,
  ArrowRight
} from "lucide-react";
import Link from "next/link";

export default function StationsPage() {
  const stations = [
    {
      id: "cnc",
      title: "Centrum CNC",
      description: "Kolejka zleceÅ„ dla maszyn CNC, statusy wycinania i raportowanie problemÃ³w.",
      icon: <Cpu className="w-8 h-8" />,
      color: "from-blue-500 to-cyan-500",
      href: "/stations/cnc"
    },
    {
      id: "assembly",
      title: "MontaÅ¼ / Assembly",
      description: "Lista szafek do skÅ‚adania, instrukcje i statusy ukoÅ„czenia.",
      icon: <Layers className="w-8 h-8" />,
      color: "from-purple-500 to-indigo-500",
      href: "/stations/assembly",
      disabled: true
    },
    {
      id: "edge",
      title: "Okleiniarka / Edge",
      description: "Zlecenia oklejania krawÄ™dzi, metryki wydajnoÅ›ci.",
      icon: <Settings className="w-8 h-8" />,
      color: "from-emerald-500 to-teal-500",
      href: "/stations/edge",
      disabled: true
    }
  ];

  return (
    <AppShell>
      <PageHeader
        eyebrow="Produkcja"
        title="Stanowiska Operacyjne"
        subtitle="Wybierz swoje stanowisko pracy, aby zarzÄ…dzaÄ‡ zadaniami w czasie rzeczywistym."
      />

      <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6 pb-20">
        {stations.map((s) => (
          <Card 
            key={s.id} 
            className={s.disabled ? "opacity-50 grayscale cursor-not-allowed" : "group hover:border-brand-ring/50 transition-all duration-300"}
            padded={false}
          >
            <div className={`h-2 bg-gradient-to-r ${s.color} rounded-t-panel`} />
            <div className="p-6 space-y-4">
              <div className="flex justify-between items-start">
                <div className="p-3 rounded-2xl bg-white/5 border border-white/10 group-hover:bg-brand-soft group-hover:border-brand-ring/30 transition-colors">
                  {s.icon}
                </div>
                {s.disabled && (
                  <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500 bg-white/5 px-2 py-1 rounded">
                    WkrÃ³tce
                  </span>
                )}
              </div>
              
              <div>
                <h3 className="text-xl font-bold text-white group-hover:text-brand transition-colors">{s.title}</h3>
                <p className="text-slate-400 text-sm mt-2 leading-relaxed">
                  {s.description}
                </p>
              </div>

              {!s.disabled ? (
                <Link 
                  href={s.href}
                  className="inline-flex items-center gap-2 text-sm font-semibold text-brand hover:gap-3 transition-all"
                >
                  OtwÃ³rz stanowisko <ArrowRight className="w-4 h-4" />
                </Link>
              ) : (
                <div className="text-sm font-semibold text-slate-600">
                  NiedostÄ™pne
                </div>
              )}
            </div>
          </Card>
        ))}
      </div>
    </AppShell>
  );
}
