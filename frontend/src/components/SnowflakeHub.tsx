"use client";

import { motion } from "framer-motion";
import {
  Compass,
  Database,
  Wallet,
  Settings,
  LayoutDashboard,
  FilePlus2,
  Cog,
  ChevronRight,
  Layers,
  Box,
  Clock,
  TriangleAlert,
  Monitor,
  Lightbulb,
  TestTube2,
  Telescope
  ,
  Scissors,
  Landmark
} from "lucide-react";
import Link from "next/link";
import React from "react";
import { useCurrentUser } from "@/services/user-context";

const MODULES = [
  {
    id: "workspace",
    label: "Workspace",
    icon: LayoutDashboard,
    href: "/workspace",
    color: "from-blue-500 to-cyan-400",
  },
  {
    id: "orders",
    label: "Nowe zamowienie",
    icon: FilePlus2,
    href: "/orders/new",
    color: "from-emerald-500 to-teal-400",
  },
  {
    id: "services",
    label: "Uslugi",
    icon: Scissors,
    href: "/services",
    color: "from-fuchsia-500 to-pink-500",
  },
  {
    id: "wall",
    label: "Sciana",
    icon: Compass,
    href: "/wall",
    color: "from-red-500 to-orange-400",
  },
  {
    id: "time",
    label: "Czas Pracy (RCP)",
    icon: Clock,
    href: "/time-tracking",
    color: "from-cyan-500 to-blue-400",
  },
  {
    id: "database",
    label: "Bazy danych",
    icon: Database,
    href: "/database",
    color: "from-orange-500 to-amber-400",
  },
  {
    id: "settings",
    label: "Ustawienia",
    icon: Settings,
    href: "/settings",
    color: "from-slate-500 to-slate-400",
  },
  {
    id: "finance",
    label: "Finanse Firmy",
    icon: Wallet,
    href: "/finance/global",
    color: "from-emerald-500 to-emerald-400",
  },
  {
    id: "cashboxes",
    label: "Kasy",
    icon: Landmark,
    href: "/cashboxes",
    color: "from-lime-500 to-emerald-400",
  },
  {
    id: "cri",
    label: "KRI",
    icon: TriangleAlert,
    href: "/cri",
    color: "from-red-600 to-orange-500",
  },
  {
    id: "jasnowidz",
    label: "Jasnowidz AI",
    icon: Telescope,
    href: "/ai/predictions",
    color: "from-brand-hover to-purple-600",
  },
  {
    id: "sim",
    label: "Symulacje",
    icon: TestTube2,
    href: "/simulations",
    color: "from-purple-500 to-pink-500",
  },
  {
    id: "help",
    label: "Centrum Wiedzy",
    icon: Lightbulb,
    href: "/help",
    color: "from-yellow-400 to-amber-500",
  },
];

export default function SnowflakeHub() {
  const radius = 240;
  const [user, setUser] = useCurrentUser();
  const angleStart = -90;
  const angleStep = 360 / MODULES.length;

  return (
    <div className="relative w-full h-[600px] flex items-center justify-center overflow-hidden">
      {/* Background glow for the whole mechanical hub */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="w-[500px] h-[500px] bg-brand/10 rounded-full blur-[120px] animate-pulse" />
      </div>

      {/* Central Hub - User Identity */}
      <motion.div
        initial={{ scale: 0, rotate: -180 }}
        animate={{ scale: 1, rotate: 0 }}
        transition={{ type: "spring", damping: 15, stiffness: 100 }}
        className="relative z-50 group/hub"
      >
        <Link href="/" onClick={() => setUser(null)} className="block relative cursor-pointer">
          <div className="w-36 h-36 rounded-full bg-gradient-to-br from-brand via-brand-hover to-blue-600 p-1 shadow-[0_0_80px_rgba(59,130,246,0.6)] group-hover/hub:scale-105 transition-transform duration-500">
            <div className="w-full h-full rounded-full bg-[#050a18] flex flex-col items-center justify-center border border-white/10 relative overflow-hidden">
              {/* Spinning mechanical background */}
              <Cog className="absolute w-24 h-24 text-brand/10 animate-[spin_20s_linear_infinite]" />

              <div className="relative z-10 flex flex-col items-center">
                <div className="w-12 h-12 rounded-full border-2 border-brand-hover flex items-center justify-center text-white font-black text-xl mb-1 shadow-inner bg-brand/20">
                  {user?.initials || "T"}
                </div>
                <span className="text-[11px] font-black tracking-widest uppercase text-white">
                  {user?.name?.split(' ')[0] || "TECH"}
                </span>
                <span className="text-[8px] font-bold text-brand-hover uppercase tracking-[0.2em] mt-1">
                  Wyloguj / Zmien
                </span>
              </div>
            </div>
          </div>
        </Link>
      </motion.div>

      {/* Branches and Nodes */}
      {MODULES.map((m, i) => {
        const angle = angleStart + i * angleStep;
        const rad = (angle * Math.PI) / 180;
        const x = Math.cos(rad) * radius;
        const y = Math.sin(rad) * radius;

        return (
          <React.Fragment key={m.id}>
            {/* Branch line */}
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: radius - 60, opacity: 0.3 }}
              transition={{ delay: 0.3 + i * 0.1, duration: 0.8 }}
              className="absolute h-[2px] bg-gradient-to-r from-brand/40 to-transparent origin-left z-10 pointer-events-none"
              style={{
                left: "calc(50% )",
                top: "calc(50% - 1px)",
                transform: `rotate(${angle}deg) translateX(60px)`,
              }}
            />

            {/* Node */}
            <motion.div
              initial={{ opacity: 0, x: 0, y: 0 }}
              animate={{ opacity: 1, x, y }}
              transition={{
                type: "spring",
                damping: 20,
                stiffness: 80,
                delay: 0.5 + i * 0.1
              }}
              className="absolute z-30"
            >
              <Link href={m.href} className="group relative block">
                {/* Node Orb */}
                <div className={`w-20 h-20 rounded-2xl bg-panel-raised border border-subtle group-hover:border-brand-hover transition-all duration-300 flex items-center justify-center glass shadow-xl group-hover:shadow-brand/40 group-hover:-translate-y-1`}>
                  <div className={`absolute inset-0 bg-gradient-to-br ${m.color} opacity-5 group-hover:opacity-20 transition-opacity rounded-2xl`} />
                  <m.icon className={`w-8 h-8 text-white/50 group-hover:text-white transition-colors`} strokeWidth={1.5} />

                  {/* Label (Always visible but subtle) */}
                  <div className="absolute -bottom-8 left-1/2 -translate-x-1/2 whitespace-nowrap opacity-40 group-hover:opacity-100 transition-all">
                    <span className="text-[10px] font-bold text-white uppercase tracking-widest">
                      {m.label}
                    </span>
                  </div>

                  {/* Enhanced Tooltip-style (On Hover) */}
                  <div className="absolute -top-12 left-1/2 -translate-x-1/2 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-all group-hover:-top-14">
                    <span className="px-3 py-1.5 rounded-lg bg-brand border border-white/20 text-[11px] font-black text-white shadow-2xl flex items-center gap-2 uppercase tracking-tighter italic">
                      Otworz {m.label}
                      <ChevronRight className="w-3 h-3 text-white" />
                    </span>
                  </div>

                  {/* Connecting Dot (Radial connector point) */}
                  <div className={`absolute w-1.5 h-1.5 rounded-full bg-brand/60 shadow-[0_0_8px_rgba(59,130,246,0.6)]`}
                    style={{
                      left: '50%',
                      top: '50%',
                      transform: 'translate(-50%, -50%)',
                      marginLeft: Math.cos((angle + 180) * Math.PI / 180) * 40,
                      marginTop: Math.sin((angle + 180) * Math.PI / 180) * 40
                    }}
                  />
                </div>
              </Link>
            </motion.div>
          </React.Fragment>
        );
      })}

      {/* Pulse Rings */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        {[1, 2, 3].map((r) => (
          <motion.div
            key={r}
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 2.5, opacity: 0 }}
            transition={{
              duration: 4,
              repeat: Infinity,
              delay: r * 1.3,
              ease: "easeOut"
            }}
            className="absolute w-64 h-64 border border-brand/20 rounded-full"
          />
        ))}
      </div>
    </div>
  );
}
