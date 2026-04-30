"use client";

import clsx from "clsx";
import {
  STATUS_BORDER_CLASS,
  STATUS_DOT_CLASS,
  STATUS_LABEL,
  getModuleStatus,
  type ModuleStatus,
} from "@/config/moduleStatus";

export function ModuleStatusDot({ href, className }: { href: string; className?: string }) {
  const status = getModuleStatus(href);
  if (!status) return null;
  return (
    <span
      className={clsx(
        "absolute right-1 top-1 h-1.5 w-1.5 rounded-full",
        STATUS_DOT_CLASS[status],
        className
      )}
      title={STATUS_LABEL[status]}
    />
  );
}

export function ModuleStatusPill({
  status,
  className,
}: {
  status: ModuleStatus;
  className?: string;
}) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[10px] font-black uppercase tracking-widest",
        STATUS_BORDER_CLASS[status],
        className
      )}
    >
      <span className={clsx("h-1.5 w-1.5 rounded-full", STATUS_DOT_CLASS[status])} />
      {STATUS_LABEL[status]}
    </span>
  );
}

export function PageStatusPill({ href, className }: { href: string; className?: string }) {
  const status = getModuleStatus(href);
  if (!status) return null;
  return <ModuleStatusPill status={status} className={className} />;
}
