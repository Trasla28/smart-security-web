"use client";

import { useSession } from "next-auth/react";
import {
  useDashboardSummary,
  useTicketsByArea,
  useTicketsByStatus,
  useAgentPerformance,
} from "@/hooks/useDashboard";
import { StatsRow } from "@/components/dashboard/StatsRow";
import { TicketsByAreaChart } from "@/components/dashboard/TicketsByAreaChart";
import { StatusDonut } from "@/components/dashboard/StatusDonut";

function LoadingCard({ h = "h-40" }: { h?: string }) {
  return <div className={`${h} bg-gray-100 rounded-xl animate-pulse`} />;
}

export default function DashboardPage() {
  const { data: session } = useSession();
  const role = session?.user?.role ?? "requester";

  const { data: summary, isLoading: loadingSummary } = useDashboardSummary();
  const { data: byArea, isLoading: loadingArea } = useTicketsByArea();
  const { data: byStatus, isLoading: loadingStatus } = useTicketsByStatus();
  const { data: agents, isLoading: loadingAgents } = useAgentPerformance();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Resumen de la actividad de tickets
        </p>
      </div>

      {/* Stats row */}
      {loadingSummary ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <LoadingCard key={i} h="h-24" />
          ))}
        </div>
      ) : summary ? (
        <StatsRow summary={summary} />
      ) : null}

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">
            Tickets por área
          </h2>
          {loadingArea ? (
            <LoadingCard />
          ) : (
            <TicketsByAreaChart data={byArea ?? []} />
          )}
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">
            Distribución por estado
          </h2>
          {loadingStatus ? (
            <LoadingCard />
          ) : (
            <StatusDonut data={byStatus ?? []} />
          )}
        </div>
      </div>

      {/* Agent performance — admin/supervisor only */}
      {(role === "admin" || role === "supervisor") && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">
            Desempeño por agente
          </h2>
          {loadingAgents ? (
            <LoadingCard h="h-32" />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-left">
                    <th className="pb-2 font-medium text-gray-500">Agente</th>
                    <th className="pb-2 font-medium text-gray-500 text-right">
                      Asignados
                    </th>
                    <th className="pb-2 font-medium text-gray-500 text-right">
                      Resueltos
                    </th>
                    <th className="pb-2 font-medium text-gray-500 text-right">
                      Prom. resolución
                    </th>
                    <th className="pb-2 font-medium text-gray-500 text-right">
                      Cumpl. SLA
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {(agents ?? []).map((a) => (
                    <tr key={a.agent_id}>
                      <td className="py-2 font-medium text-gray-800">
                        {a.agent_name}
                      </td>
                      <td className="py-2 text-right text-gray-600">
                        {a.assigned_total}
                      </td>
                      <td className="py-2 text-right text-gray-600">
                        {a.resolved_total}
                      </td>
                      <td className="py-2 text-right text-gray-600">
                        {a.avg_resolution_hours !== null
                          ? `${Math.round(a.avg_resolution_hours)}h`
                          : "—"}
                      </td>
                      <td className="py-2 text-right">
                        {a.sla_compliance_pct !== null ? (
                          <span
                            className={
                              a.sla_compliance_pct >= 80
                                ? "text-green-600"
                                : "text-red-600"
                            }
                          >
                            {Math.round(a.sla_compliance_pct)}%
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
