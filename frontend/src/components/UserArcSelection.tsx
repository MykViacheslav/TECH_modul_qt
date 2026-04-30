"use client";

import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { User, ChevronUp, ChevronDown } from "lucide-react";
import React, { useEffect, useRef } from "react";
import clsx from "clsx";

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

export default function UserArcSelection({ users, onSelect }: Props) {
  const scrollY = useMotionValue(0);
  const springScroll = useSpring(scrollY, { stiffness: 100, damping: 20 });
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleWheel = (e: WheelEvent) => {
      const current = scrollY.get();
      // Sensitivity adjustment
      scrollY.set(current - e.deltaY * 0.5);
    };

    const container = containerRef.current;
    if (container) {
      container.addEventListener("wheel", handleWheel, { passive: false });
    }
    return () => {
      if (container) {
        container.removeEventListener("wheel", handleWheel);
      }
    };
  }, [scrollY]);

  // Height of each item in the scroll logic
  const ITEM_HEIGHT = 120;
  const totalHeight = users.length * ITEM_HEIGHT;

  return (
    <div
      ref={containerRef}
      className="relative w-[500px] h-[600px] bg-[#0d1528]/80 backdrop-blur-xl border border-white/10 rounded-[32px] overflow-hidden shadow-2xl flex"
    >
      {/* Decorative side accent */}
      <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-transparent via-brand to-transparent opacity-50" />

      {/* Scroll indicator overlay */}
      <div className="absolute right-4 top-1/2 -translate-y-1/2 flex flex-col items-center gap-4 text-slate-700 pointer-events-none">
        <ChevronUp size={16} />
        <div className="w-[1px] h-32 bg-slate-800 relative">
           <motion.div
             style={{
               top: useTransform(springScroll, (v) => {
                 const p = Math.abs(v % totalHeight) / totalHeight;
                 return `${p * 100}%`;
               })
             }}
             className="absolute left-1/2 -translate-x-1/2 w-4 h-1 bg-brand-hover"
           />
        </div>
        <ChevronDown size={16} />
      </div>

      <div className="flex-1 relative flex items-center justify-center">
        <div className="absolute left-[-200px] w-[800px] h-[800px] rounded-full border border-white/5 opacity-20 pointer-events-none" />

        {/* The Arc items */}
        <div className="relative w-full h-full flex items-center">
          {users.map((user, i) => (
            <UserArcNode
              key={user.id}
              user={user}
              index={i}
              total={users.length}
              scrollY={springScroll}
              onSelect={onSelect}
              itemHeight={ITEM_HEIGHT}
            />
          ))}
        </div>
      </div>

      {/* Glass gradient overlay top/bottom */}
      <div className="absolute top-0 left-0 right-0 h-24 bg-gradient-to-b from-[#0d1528] to-transparent pointer-events-none z-20" />
      <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-[#0d1528] to-transparent pointer-events-none z-20" />
    </div>
  );
}

function UserArcNode({
  user,
  index,
  total,
  scrollY,
  onSelect,
  itemHeight
}: {
  user: Technician;
  index: number;
  total: number;
  scrollY: any;
  onSelect: (u: Technician) => void;
  itemHeight: number;
}) {
  // Center point calculation
  // We want the items to follow a vertical arc
  const angleRange = 80; // Total arc angle in degrees
  const radius = 350;    // Radius of the arc

  // Position relative to the center of the scroll
  const yPos = useTransform(scrollY, (v) => {
    const offset = index * itemHeight + (v as number);
    // Simple wrap-around if needed, or just standard offset
    return offset;
  });

  // Calculate angle based on yPos
  // We map vertical position to an angle on the circle
  // 0 vertical = 0 degrees (middle)
  const angle = useTransform(yPos, (v) => {
    // 300 is half of the container height
    return (v / 600) * angleRange;
  });

  // Circular coordinates
  // Center of circle is off-screen to the left (e.g. at x = -radius)
  const x = useTransform(angle, (a) => Math.cos((a * Math.PI) / 180) * radius - radius + 60);
  const y = useTransform(angle, (a) => Math.sin((a * Math.PI) / 180) * radius);

  // Styling based on proximity to center (a = 0)
  const opacity = useTransform(angle, [-60, -30, 0, 30, 60], [0, 0.4, 1, 0.4, 0]);
  const scale = useTransform(angle, [-45, 0, 45], [0.7, 1.1, 0.7]);
  const blur = useTransform(angle, [-45, 0, 45], ["4px", "0px", "4px"]);

  return (
    <motion.div
      style={{
        x,
        y: useTransform(y, (v) => v), // Could add manual offset here if needed
        opacity,
        scale,
        filter: useTransform(blur, (v) => `blur(${v})`),
        position: "absolute",
        left: "40px",
        top: "calc(50% - 40px)", // Centered anchor
      }}
      className="z-10"
    >
      <motion.button
        whileHover={{ scale: 1.15, x: 10 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => onSelect(user)}
        className="flex items-center gap-6 group"
      >
        <div
          className="w-20 h-20 rounded-2xl border border-white/20 shadow-2xl flex items-center justify-center relative overflow-hidden group-hover:border-brand-hover transition-colors"
          style={{ backgroundColor: user.user_color || user.avatar_color || "#1e3a5f" }}
        >
          <div className="absolute inset-0 bg-gradient-to-br from-white/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          <span className="text-white font-black text-2xl drop-shadow-lg relative z-10">{getInitials(user.name)}</span>
        </div>

        <div className="flex flex-col items-start translate-y-1">
          <span className="text-xl font-black italic uppercase tracking-tighter text-white group-hover:text-brand-hover transition-colors">
            {user.name}
          </span>
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
            {user.role}
          </span>
        </div>
      </motion.button>
    </motion.div>
  );
}
