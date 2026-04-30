"use client";

import React from "react";
import clsx from "clsx";
import Link from "next/link";

/* ---------- Button ---------- */
type BtnProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  as?: "button";
};
type LinkBtnProps = {
  href: string;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  as: "link";
  children: React.ReactNode;
  className?: string;
};
export function Button(props: BtnProps | LinkBtnProps) {
  const variant = props.variant ?? "primary";
  const base = clsx(
    "inline-flex items-center justify-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold transition-colors whitespace-nowrap",
    variant === "primary" &&
      "bg-blue-600 hover:bg-blue-500 text-white shadow-[0_0_20px_rgba(37,99,235,0.3)] border border-blue-400/30",
    variant === "secondary" &&
      "bg-[#1a1a1c] border border-white/10 hover:border-white/20 text-slate-200 shadow-xl",
    variant === "ghost" && "text-slate-400 hover:text-white hover:bg-white/5",
    variant === "danger" &&
      "bg-red-600/90 hover:bg-red-500 text-white shadow-[0_0_20px_rgba(239,68,68,0.2)]"
  );
  if ("as" in props && props.as === "link") {
    return (
      <Link href={props.href} className={clsx(base, props.className)}>
        {props.children}
      </Link>
    );
  }
  const { className, size: _size, ...rest } = props as BtnProps;
  return <button className={clsx(base, className)} {...rest} />;
}

/* ---------- Card ---------- */
export function Card({
  className,
  children,
  title,
  icon,
  padded = true,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & {
  padded?: boolean;
  title?: string;
  icon?: React.ReactNode;
}) {
  return (
    <div
      className={clsx(
        "bg-[#161618]/80 border border-white/5 rounded-2xl overflow-hidden backdrop-blur-xl shadow-2xl",
        className
      )}
      {...props}
    >
      {title && (
        <div className="px-6 py-4 border-b border-subtle flex items-center justify-between">
          <div className="flex items-center gap-2">
            {icon && <div className="text-slate-400">{icon}</div>}
            <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
          </div>
        </div>
      )}
      <div className={clsx(padded && "p-6")}>{children}</div>
    </div>
  );
}

/* ---------- StatCard ---------- */
export function StatCard({
  label,
  value,
  hint,
  tone = "default",
  icon,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
  tone?: "default" | "brand" | "success" | "warn" | "danger";
  icon?: React.ReactNode;
}) {
  const toneCls =
    tone === "brand"
      ? "border-blue-500/30 bg-blue-500/5 shadow-[0_0_30px_rgba(59,130,246,0.05)]"
      : tone === "success"
      ? "border-emerald-500/30 bg-emerald-500/5 shadow-[0_0_30px_rgba(16,185,129,0.05)]"
      : tone === "warn"
      ? "border-amber-500/30 bg-amber-500/5 shadow-[0_0_30px_rgba(245,158,11,0.05)]"
      : tone === "danger"
      ? "border-red-500/30 bg-red-500/5 shadow-[0_0_30px_rgba(239,68,68,0.05)]"
      : "border-white/5 bg-[#1a1a1c]/60 shadow-xl";

  return (
    <div className={clsx("rounded-card border p-5", toneCls)}>
      <div className="flex items-center justify-between mb-3">
        <span className="eyebrow">{label}</span>
        {icon && <div className="text-slate-400">{icon}</div>}
      </div>
      <div className="text-2xl font-bold text-white tracking-tight">{value}</div>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

/* ---------- Section ---------- */
export function Section({
  title,
  action,
  children,
  className,
}: {
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={className}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="eyebrow">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}
