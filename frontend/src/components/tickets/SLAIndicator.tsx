import { cn } from "@/lib/utils";
import { formatDistanceToNow } from "date-fns";
import { es } from "date-fns/locale";
import type { SLAStatus } from "@/types/ticket";

interface SLAIndicatorProps {
  slaStatus: SLAStatus | null;
  slaPercentage: number | null;
  slaDueAt: string | null;
  compact?: boolean;
}

export function SLAIndicator({ slaStatus, slaPercentage, slaDueAt, compact = false }: SLAIndicatorProps) {
  if (!slaStatus || slaDueAt === null) return null;

  const colorClass = {
    ok: "bg-green-500",
    warning: "bg-yellow-500",
    breached: "bg-red-500",
  }[slaStatus];

  const trackClass = {
    ok: "bg-green-100",
    warning: "bg-yellow-100",
    breached: "bg-red-100",
  }[slaStatus];

  const pct = Math.min(100, slaPercentage ?? 0);
  const dueDate = new Date(slaDueAt);
  const isBreached = slaStatus === "breached";

  if (compact) {
    return (
      <span className={cn("inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full", {
        "bg-green-100 text-green-700": slaStatus === "ok",
        "bg-yellow-100 text-yellow-700": slaStatus === "warning",
        "bg-red-100 text-red-700": slaStatus === "breached",
      })}>
        <span className={cn("w-1.5 h-1.5 rounded-full", colorClass)} />
        {isBreached ? "SLA vencido" : "SLA activo"}
      </span>
    );
  }

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-gray-500">
        <span>SLA — {isBreached ? "Vencido" : formatDistanceToNow(dueDate, { addSuffix: true, locale: es })}</span>
        <span>{Math.round(pct)}%</span>
      </div>
      <div className={cn("w-full h-1.5 rounded-full", trackClass)}>
        <div className={cn("h-1.5 rounded-full transition-all", colorClass)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
