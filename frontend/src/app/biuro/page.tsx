"use client";

import Link from "next/link";
import {
  CalendarClock,
  ClipboardList,
  Database,
  FileText,
  FolderOpen,
  Layers,
  Package,
  Receipt,
  Scissors,
  Wallet,
  Wrench,
} from "lucide-react";
import AppShell from "@/components/AppShell";

const officeTiles = [
  {
    href: "/orders/new",
    title: "Zlecenia i wyceny",
    desc: "Nowe zlecenie, klient, pozycje, specyfikacja, materialy i platnosci.",
    icon: FileText,
    tone: "border-blue-500/35 bg-blue-500/10 text-blue-200",
  },
  {
    href: "/orders/offer",
    title: "Oferta dla klienta",
    desc: "Widok oferty, podsumowanie i material do rozmowy z klientem.",
    icon: Receipt,
    tone: "border-cyan-500/35 bg-cyan-500/10 text-cyan-200",
  },
  {
    href: "/workspace/import",
    title: "Rozkroje / import",
    desc: "Import plikow, formatki, dane do dalszej produkcji i CNC.",
    icon: Scissors,
    tone: "border-amber-500/35 bg-amber-500/10 text-amber-200",
  },
  {
    href: "/configuration",
    title: "Formatki / BOM",
    desc: "Zestawienie formatek, moduly, materialy i techniczne dane projektu.",
    icon: Layers,
    tone: "border-indigo-500/35 bg-indigo-500/10 text-indigo-200",
  },
  {
    href: "/database/clients",
    title: "Baza klientow",
    desc: "Kontrahenci, adresy, telefony i dane do zlecen.",
    icon: Database,
    tone: "border-emerald-500/35 bg-emerald-500/10 text-emerald-200",
  },
  {
    href: "/procurement/availability",
    title: "Materialy",
    desc: "Dostepnosc materialow, braki i przygotowanie zakupow.",
    icon: Package,
    tone: "border-teal-500/35 bg-teal-500/10 text-teal-200",
  },
  {
    href: "/finance",
    title: "Finanse / koszt",
    desc: "Wycena, marza, VAT, kasa i kontrola kosztow projektu.",
    icon: Wallet,
    tone: "border-yellow-500/35 bg-yellow-500/10 text-yellow-200",
  },
  {
    href: "/services",
    title: "Uslugi",
    desc: "Montaz, serwis, transport, pomiar i prace dodatkowe.",
    icon: Wrench,
    tone: "border-slate-400/35 bg-slate-500/10 text-slate-200",
  },
  {
    href: "/calendar",
    title: "Terminy",
    desc: "Pomiary, montaże, poprawki i plan pracy biura.",
    icon: CalendarClock,
    tone: "border-rose-500/35 bg-rose-500/10 text-rose-200",
  },
  {
    href: "/production/handoff",
    title: "Przekazanie na produkcje",
    desc: "Akceptacje warsztatu, gotowosc i zamkniecie danych dla hali.",
    icon: ClipboardList,
    tone: "border-orange-500/35 bg-orange-500/10 text-orange-200",
  },
];

export default function BiuroPage() {
  return (
    <AppShell>
      <div className="h-full overflow-auto custom-scrollbar bg-[#1e1e1e] p-3 text-slate-100">
        <div className="mb-3 flex items-end justify-between gap-3 border-b border-white/10 pb-3">
          <div>
            <div className="text-[10px] font-black uppercase tracking-[0.22em] text-blue-400">
              Centrum pracy biura
            </div>
            <h1 className="mt-1 text-2xl font-black text-white">BIURO</h1>
            <p className="mt-1 text-sm text-slate-400">
              Zlecenia, wyceny, rozkroje, materialy, klienci i przekazanie do produkcji w jednym miejscu.
            </p>
          </div>
          <Link
            href="/orders/new"
            className="rounded-sm border border-blue-500/35 bg-blue-600/20 px-3 py-2 text-[12px] font-black uppercase tracking-wider text-blue-100 hover:bg-blue-600/30"
          >
            Nowe zlecenie
          </Link>
        </div>

        <div className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-5">
          {officeTiles.map((tile) => {
            const Icon = tile.icon;
            return (
              <Link
                key={tile.href}
                href={tile.href}
                className="group min-h-[118px] rounded-md border border-white/10 bg-[#242424] p-3 transition-colors hover:border-blue-500/40 hover:bg-[#2a2d33]"
              >
                <div className="mb-3 flex items-center justify-between gap-2">
                  <div className={`rounded-sm border p-2 ${tile.tone}`}>
                    <Icon className="h-4 w-4" strokeWidth={1.7} />
                  </div>
                  <span className="text-[18px] leading-none text-slate-600 transition-colors group-hover:text-blue-300">
                    →
                  </span>
                </div>
                <div className="text-[13px] font-black text-white">{tile.title}</div>
                <div className="mt-1 text-[11px] leading-5 text-slate-400">{tile.desc}</div>
              </Link>
            );
          })}
        </div>

        <div className="mt-3 grid grid-cols-1 gap-2 xl:grid-cols-3">
          <section className="rounded-md border border-white/10 bg-[#202020] p-3">
            <div className="mb-2 text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">
              Najczesciej uzywane w biurze
            </div>
            <div className="grid grid-cols-2 gap-2 text-[12px]">
              <Link className="rounded border border-white/10 px-3 py-2 hover:bg-white/5" href="/orders/new">
                Zlecenie + wycena
              </Link>
              <Link className="rounded border border-white/10 px-3 py-2 hover:bg-white/5" href="/workspace/import">
                Import / rozkroj
              </Link>
              <Link className="rounded border border-white/10 px-3 py-2 hover:bg-white/5" href="/database/clients">
                Klient
              </Link>
              <Link className="rounded border border-white/10 px-3 py-2 hover:bg-white/5" href="/procurement/execution">
                Zakupy
              </Link>
            </div>
          </section>

          <section className="rounded-md border border-white/10 bg-[#202020] p-3 xl:col-span-2">
            <div className="mb-2 text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">
              Kolejnosc pracy
            </div>
            <div className="grid grid-cols-1 gap-2 text-[12px] md:grid-cols-5">
              {["Klient", "Wycena", "Rozkroj", "Materialy", "Produkcja"].map((step, index) => (
                <div key={step} className="rounded border border-[#39465a] bg-[#111827] px-3 py-2">
                  <div className="text-[10px] text-slate-500">Krok {index + 1}</div>
                  <div className="font-bold text-slate-100">{step}</div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </AppShell>
  );
}
