"use client";

import { ArrowRight } from "lucide-react";

export type OperationPreviewRow = {
  key: string;
  name?: string;
  label: string;
  before: string;
  after: string;
  unit?: string;
};

type Props = {
  title: string;
  rows: OperationPreviewRow[];
  warnings?: string[];
  maxHeightClassName?: string;
};

export default function OperationPreviewList({
  title,
  rows,
  warnings = [],
  maxHeightClassName = "max-h-[220px]",
}: Props) {
  return (
    <div>
      <p className="eyebrow mb-3">
        {title} ({rows.length})
      </p>

      {warnings.length > 0 && (
        <div className="mb-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
          {warnings.join(" | ")}
        </div>
      )}

      <div className={`space-y-2 overflow-y-auto pr-1 ${maxHeightClassName}`}>
        {rows.map((row) => (
          <div
            key={row.key}
            className="bg-canvas-deep border border-subtle rounded-lg px-3 py-2 flex items-center justify-between text-sm"
          >
            <div>
              <p className="text-slate-200 font-medium">{row.name || "Modul"}</p>
              <p className="text-xs text-slate-500">{row.label}</p>
            </div>
            <div className="flex items-center gap-2 font-mono text-sm">
              <span className="text-slate-500 line-through">{row.before}</span>
              <ArrowRight className="w-3 h-3 text-slate-600" />
              <span className="text-emerald-400 font-semibold">{row.after}</span>
              {row.unit ? <span className="text-xs text-slate-600">{row.unit}</span> : null}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

