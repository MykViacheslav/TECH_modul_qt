"use client";

import React from "react";

type Props = {
  eyebrow?: React.ReactNode;
  title: React.ReactNode;
  subtitle?: string;
  actions?: React.ReactNode;
};

export default function PageHeader({ eyebrow, title, subtitle, actions }: Props) {
  return (
    <header className="flex flex-col gap-6 pb-6 mb-8 border-b border-subtle md:flex-row md:items-end md:justify-between">
      <div>
        {eyebrow && <p className="eyebrow-brand mb-2">{eyebrow}</p>}
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white">
          {title}
        </h1>
        {subtitle && (
          <p className="mt-2 text-sm text-slate-400 max-w-xl">{subtitle}</p>
        )}
      </div>
      {actions && <div className="flex flex-wrap gap-3">{actions}</div>}
    </header>
  );
}
