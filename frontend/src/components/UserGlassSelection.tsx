"use client";

import { motion, useMotionValue, useSpring, useTransform, type MotionValue } from "framer-motion";
import { ChevronRight } from "lucide-react";
import React, { useState, useEffect, useRef } from "react";

interface Technician {
  id: number;
  name: string;
  role: string;
  avatar_color: string;
  user_color?: string;
  pin_code: string;
  status?: string;
}

interface Props {
  users: Technician[];
  onSelect: (tech: Technician) => void;
}

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

export default function UserGlassSelection({ users, onSelect }: Props) {
  const [time, setTime] = useState("");
  const scrollY = useMotionValue(0);
  const springScroll = useSpring(scrollY, { stiffness: 100, damping: 25 });
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const timer = setInterval(() => {
      setTime(new Date().toLocaleTimeString("pl-PL", { hour: "2-digit", minute: "2-digit" }));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const ITEM_HEIGHT = 100;
  const totalHeight = users.length * ITEM_HEIGHT;

  useEffect(() => {
    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      const current = scrollY.get();
      // Scroll limiters
      const next = current - e.deltaY;
      const limit = -(totalHeight - 300);
      if (next > 100) return;
      if (next < limit - 100) return;
      scrollY.set(next);
    };

    const el = containerRef.current;
    if (el) {
      el.addEventListener("wheel", handleWheel, { passive: false });
    }
    return () => el?.removeEventListener("wheel", handleWheel);
  }, [totalHeight, scrollY]);

  return (
    <div
      ref={containerRef}
      className="relative w-[680px] h-[780px] bg-slate-950/40 backdrop-blur-3xl border border-white/[0.03] rounded-[40px] shadow-[0_60px_120px_rgba(0,0,0,0.7)] overflow-hidden flex flex-col group/panel"
    >
      {/* Industrial Corner Brackets */}
      <div className="absolute top-6 left-6 w-8 h-8 border-t-2 border-l-2 border-blue-500/30 rounded-tl-lg pointer-events-none" />
      <div className="absolute top-6 right-6 w-8 h-8 border-t-2 border-r-2 border-blue-500/30 rounded-tr-lg pointer-events-none" />
      <div className="absolute bottom-6 left-6 w-8 h-8 border-b-2 border-l-2 border-blue-500/30 rounded-bl-lg pointer-events-none" />
      <div className="absolute bottom-6 right-6 w-8 h-8 border-b-2 border-r-2 border-blue-500/30 rounded-br-lg pointer-events-none" />

      {/* Internal technical ring/glow */}
      <div className="absolute inset-2 border border-white/[0.02] rounded-[36px] pointer-events-none" />

      {/* Header */}
      <div className="h-24 px-12 flex items-center justify-between border-b border-white/[0.03] bg-white/[0.02] relative overflow-hidden">
        <div className="absolute top-0 left-0 w-1/4 h-[2px] bg-gradient-to-r from-blue-500 to-transparent" />
        <div className="flex flex-col">
          <h2 className="text-3xl font-black italic tracking-tighter uppercase leading-none">
            Witaj w <span className="text-blue-400">TECH_modu</span>
          </h2>
          <div className="flex items-center gap-4 mt-2">
            <span className="text-[8px] font-black text-blue-500/60 uppercase tracking-[0.3em]">Industrial OS v2.4</span>
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500/50 animate-pulse" />
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
           <div className="text-blue-400 font-mono text-2xl font-bold tracking-widest">{time || "14:37"}</div>
           <span className="text-[8px] font-bold text-slate-600 uppercase tracking-widest">Local GMT+2</span>
        </div>
      </div>

      <div className="flex-1 relative flex">
        {/* Left Arc Scale / Gauge effect - made more subtle */}
        <div className="absolute left-[-260px] top-1/2 -translate-y-1/2 w-[520px] h-[520px] border-[1px] border-white/[0.02] rounded-full pointer-events-none">
           {/* Tick marks along the inner edge */}
           <div className="absolute inset-0">
             {Array.from({length: 40}).map((_, i) => (
                <div
                  key={i}
                  className="absolute w-3 h-[1px] bg-blue-500/10 origin-right"
                  style={{
                    right: 0,
                    top: '50%',
                    transform: `rotate(${i * 4.5 - 90}deg) translateX(-230px)`
                  }}
                />
             ))}
           </div>

           {/* Moving indicator */}
           <motion.div
             style={{
               rotate: useTransform(springScroll, (v) => (v / totalHeight) * 120 - 90)
             }}
             className="absolute inset-0 flex items-center justify-end pr-2"
           >
              <div className="w-6 h-6 rounded-full bg-blue-500 shadow-[0_0_20px_rgba(59,130,246,0.8)] border-4 border-slate-900" />
           </motion.div>
        </div>

        {/* User Nodes following the curve */}
        <div className="flex-1 relative overflow-hidden h-full">
           <div className="absolute inset-0 z-10 flex items-center">
             {users.map((user, i) => (
               <UserNode
                 key={user.id}
                 user={user}
                 index={i}
                 scrollY={springScroll}
                 onSelect={onSelect}
                 itemHeight={ITEM_HEIGHT}
               />
             ))}
           </div>
        </div>
      </div>

      {/* Decorative Blueprint Corner */}
      <div className="absolute bottom-[-20px] right-[-20px] opacity-10 pointer-events-none scale-150">
         <div className="w-40 h-40 border border-blue-500/40 rounded-sm rotate-12" />
         <div className="absolute inset-4 border border-blue-500/20 rounded-sm -rotate-6" />
      </div>

      {/* Bottom masking */}
      <div className="absolute bottom-0 left-0 right-0 h-40 bg-gradient-to-t from-slate-950 to-transparent pointer-events-none z-20" />
      <div className="absolute top-20 left-0 right-0 h-40 bg-gradient-to-b from-slate-950 to-transparent pointer-events-none z-20" />
    </div>
  );
}

interface UserNodeProps {
  user: Technician;
  index: number;
  scrollY: MotionValue<number>;
  onSelect: (tech: Technician) => void;
  itemHeight: number;
}

function UserNode({ user, index, scrollY, onSelect, itemHeight }: UserNodeProps) {
  const radius = 380;
  const angleRange = 60;

  const yOffset = useTransform(scrollY, (v) => index * itemHeight + v);
  const angle = useTransform(yOffset, (v) => (v / 600) * angleRange);

  const x = useTransform(angle, (a) => Math.cos((a * Math.PI) / 180) * radius - radius + 140);
  const y = useTransform(angle, (a) => Math.sin((a * Math.PI) / 180) * radius);

  const opacity = useTransform(angle, [-50, -30, 0, 30, 50], [0, 0.4, 1, 0.4, 0]);
  const scale = useTransform(angle, [-30, 0, 30], [0.85, 1.05, 0.85]);

  return (
    <motion.div
      style={{ x, y, opacity, scale }}
      className="absolute left-0 top-1/2 -translate-y-1/2 w-[480px]"
    >
      <button
        onClick={() => onSelect(user)}
        className="flex items-center gap-6 group w-full text-left p-6 rounded-[32px] transition-all hover:bg-white/[0.03] border border-transparent hover:border-white/5 relative overflow-hidden group/btn"
      >
        {/* Subtle hover card glow */}
        <div className="absolute inset-0 bg-blue-500/[0.02] opacity-0 group-hover/btn:opacity-100 transition-opacity" />

        <div className="relative">
          <div
             className="w-20 h-20 rounded-2xl border border-white/10 flex items-center justify-center p-1 group-hover/btn:border-blue-400 group-hover/btn:scale-105 transition-all shadow-xl bg-slate-900/40 backdrop-blur-md"
          >
             <div
               className="w-full h-full rounded-xl flex items-center justify-center font-black text-2xl text-white shadow-2xl relative overflow-hidden"
               style={{ backgroundColor: user.user_color || user.avatar_color || "#1e3a5f" }}
             >
                <div className="absolute inset-0 bg-gradient-to-br from-white/20 to-transparent" />
                <span className="relative z-10">{getInitials(user.name)}</span>
             </div>
          </div>
          {/* Active ring indicator matching mockup */}
          <div className="absolute inset-[-6px] border border-blue-400/10 rounded-[30px] pointer-events-none opacity-0 group-hover/btn:opacity-100 transition-all scale-110 group-hover/btn:scale-100" />
        </div>

        <div className="flex flex-col flex-1">
          <div className="text-2xl font-black text-white group-hover/btn:text-blue-300 transition-colors tracking-tight italic uppercase">
            {user.name}
          </div>
          <div className="text-[9px] text-slate-500 font-bold uppercase tracking-[0.2em] mt-1">{user.role || "Operator"}</div>
          <div className="flex items-center gap-2 mt-2">
             <div className="px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center gap-1.5 translate-y-[-2px]">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)] animate-pulse" />
                <span className="text-[8px] font-black text-emerald-400 uppercase tracking-tighter">Active</span>
             </div>
          </div>
        </div>

        <div className="w-10 h-10 rounded-full border border-white/5 flex items-center justify-center opacity-0 group-hover/btn:opacity-100 group-hover/btn:translate-x-2 transition-all">
          <ChevronRight className="w-5 h-5 text-blue-500" />
        </div>
      </button>
    </motion.div>
  );
}
