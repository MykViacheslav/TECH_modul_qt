"use client";

import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { User } from "lucide-react";
import React, { useEffect } from "react";

interface Technician {
  id: number;
  name: string;
  role: string;
  avatar_color: string;
  user_color?: string;
  pin_code: string;
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

export default function UserRadialHub({ users, onSelect }: Props) {
  const rotation = useMotionValue(0);
  const springRotation = useSpring(rotation, { stiffness: 180, damping: 24 });

  useEffect(() => {
    const handleWheel = (e: WheelEvent) => {
      const current = rotation.get();
      const next = current - e.deltaY * 0.08;
      rotation.set(next);
    };

    window.addEventListener("wheel", handleWheel, { passive: true });

    return () => {
      window.removeEventListener("wheel", handleWheel);
    };
  }, [rotation]);

  const count = Math.max(users.length, 1);

  return (
    <div className="relative w-full h-[640px] flex items-center justify-center select-none overflow-hidden touch-none">
      {/* Background radial highlight */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="w-[820px] h-[820px] bg-brand/10 rounded-full blur-[120px]" />
      </div>

      {/* Circular hub shell */}
      <div className="relative z-20 w-[560px] h-[560px] rounded-full border border-white/10 bg-gradient-to-b from-white/[0.05] to-white/[0.02] shadow-[0_0_80px_rgba(6,26,78,0.45)]">
        <div className="absolute inset-7 rounded-full border border-white/10 bg-[#08112a]/70" />
        <div className="absolute inset-[86px] rounded-full border border-white/10 bg-[#0a1330]/65" />
        <div className="absolute inset-[148px] rounded-full border border-white/5 bg-[#0a1228]/50" />
      </div>

      {/* Orbit surface */}
      <motion.div
        drag="y"
        onDrag={(_, info) => {
          const current = rotation.get();
          rotation.set(current + info.delta.y * 0.55);
        }}
        className="absolute inset-0 z-40 flex items-center justify-center cursor-grab active:cursor-grabbing"
      >
        <div className="relative w-[560px] h-[560px]">
          {users.map((user, i) => {
            return (
              <UserNode
                key={user.id}
                user={user}
                index={i}
                count={count}
                rotation={springRotation}
                onSelect={onSelect}
              />
            );
          })}
        </div>
      </motion.div>
    </div>
  );
}

function UserNode({
  user,
  index,
  count,
  rotation,
  onSelect,
}: {
  user: Technician;
  index: number;
  count: number;
  rotation: any;
  onSelect: (u: Technician) => void;
}) {
  const baseAngle = (index / Math.max(count, 1)) * 360 - 90;
  const radius = 200;

  const angle = useTransform(rotation, (r: any) => baseAngle + (Number(r) || 0));
  const x = useTransform(angle, (a: any) => Math.cos((Number(a) * Math.PI) / 180) * radius);
  const y = useTransform(angle, (a: any) => Math.sin((Number(a) * Math.PI) / 180) * radius);

  // Top arc = closest to user
  const depth = useTransform(
    angle,
    (a: any) => (Math.cos(((Number(a) + 90) * Math.PI) / 180) + 1) / 2
  );
  const scale = useTransform(depth, [0, 1], [0.58, 1.12]);
  const opacity = useTransform(depth, [0, 1], [0.35, 1]);
  const blur = useTransform(depth, [0, 1], ["6px", "0px"]);
  const zIndex = useTransform(depth, [0, 1], [1, 20]);
  const labelOpacity = useTransform(depth, [0.2, 0.65, 1], [0, 0.55, 1]);

  return (
    <motion.div
      style={{
        x,
        y,
        scale,
        opacity,
        filter: `blur(${blur})`,
        zIndex,
      }}
      className="absolute left-1/2 top-1/2 -ml-12 -mt-12 flex flex-col items-center group"
    >
      <button
        onClick={() => onSelect(user)}
        className="relative flex flex-col items-center transition-all duration-300 focus:outline-none"
      >
        <div
          className="w-24 h-24 rounded-full border-2 border-white/15 group-hover:border-brand-hover shadow-2xl flex items-center justify-center ring-8 ring-[#0a0f1e]/55 transition-all duration-500 group-hover:shadow-brand/20 group-hover:scale-105"
          style={{ backgroundColor: user.user_color || user.avatar_color || "#1e3a5f" }}
        >
          <span className="text-white font-black text-2xl drop-shadow-md">{getInitials(user.name)}</span>
        </div>

        <motion.div style={{ opacity: labelOpacity }} className="absolute top-full mt-3 flex flex-col items-center gap-0.5">
          <p className="text-sm font-black text-white uppercase tracking-tighter italic">
            {user.name}
          </p>
          <p className="text-[9px] font-bold text-brand-hover uppercase tracking-[0.2em]">
            {user.role}
          </p>
        </motion.div>
      </button>
    </motion.div>
  );
}
