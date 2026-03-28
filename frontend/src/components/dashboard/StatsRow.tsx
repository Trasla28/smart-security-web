import type { ReactNode } from "react";
import { Ticket, Clock, CheckCircle, TrendingUp } from "lucide-react";
import type { DashboardSummary } from "@/types/admin";

interface StatsRowProps {
  summary: DashboardSummary;
}

function StatCard({
  icon,
  value,
  label,
  sub,
}: {
  icon: ReactNode;
  value: string | number;
  label: string;
  sub?: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 flex items-start gap-4">
      <div className="p-2 bg-[#1a2c4e]/10 rounded-lg text-[#1a2c4e]">{icon}</div>
      <div>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        <p className="text-sm text-gray-500">{label}</p>
        {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

export function StatsRow({ summary }: StatsRowProps) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard
        icon={<Ticket className="w-5 h-5" />}
        value={summary.total_open}
        label="Abiertos"
        sub={`+${summary.new_today} nuevos hoy`}
      />
      <StatCard
        icon={<Clock className="w-5 h-5" />}
        value={summary.total_in_progress}
        label="En proceso"
        sub={`${summary.total_pending} pendientes`}
      />
      <StatCard
        icon={<CheckCircle className="w-5 h-5" />}
        value={summary.total_resolved_today}
        label="Resueltos hoy"
      />
      <StatCard
        icon={<TrendingUp className="w-5 h-5" />}
        value={
          summary.sla_compliance_pct !== null
            ? `${Math.round(summary.sla_compliance_pct)}%`
            : "—"
        }
        label="Cumplimiento SLA"
        sub={
          summary.avg_resolution_hours !== null
            ? `Promedio: ${Math.round(summary.avg_resolution_hours)}h`
            : undefined
        }
      />
    </div>
  );
}
