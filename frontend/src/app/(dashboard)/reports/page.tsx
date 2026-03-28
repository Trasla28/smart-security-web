"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { useUserPerformance, useUrgencyAbuse } from "@/hooks/useDashboard";
import {
  TrendingUp, TrendingDown, Minus, Trophy, Clock, CheckCircle,
  AlertTriangle, RefreshCw, Star, Users, BarChart2, ChevronDown,
} from "lucide-react";
import type { UserPerformanceItem } from "@/types/admin";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const PERIOD_OPTIONS = [
  { label: "Últimos 7 días", value: 7 },
  { label: "Últimos 30 días", value: 30 },
  { label: "Últimos 60 días", value: 60 },
  { label: "Últimos 90 días", value: 90 },
];

const ROLE_LABEL: Record<string, string> = {
  admin: "Admin", supervisor: "Supervisor", agent: "Agente", requester: "Solicitante",
};

function scoreColor(score: number) {
  if (score >= 90) return "bg-emerald-100 text-emerald-700 border-emerald-200";
  if (score >= 75) return "bg-blue-100 text-blue-700 border-blue-200";
  if (score >= 60) return "bg-yellow-100 text-yellow-700 border-yellow-200";
  return "bg-red-100 text-red-700 border-red-200";
}

function scoreBar(score: number) {
  if (score >= 90) return "bg-emerald-500";
  if (score >= 75) return "bg-blue-500";
  if (score >= 60) return "bg-yellow-500";
  return "bg-red-500";
}

function medal(rank: number) {
  if (rank === 0) return "🥇";
  if (rank === 1) return "🥈";
  if (rank === 2) return "🥉";
  return `${rank + 1}`;
}

function fmtHours(h: number | null): string {
  if (h === null || h === undefined) return "—";
  if (h < 1) return `${Math.round(h * 60)} min`;
  if (h < 24) return `${h.toFixed(1)} h`;
  return `${(h / 24).toFixed(1)} días`;
}

// ---------------------------------------------------------------------------
// Summary cards
// ---------------------------------------------------------------------------
function SummaryCards({ data }: { data: UserPerformanceItem[] }) {
  const totalResolved = data.reduce((s, u) => s + u.resolved_total, 0);
  const totalBreached = data.reduce((s, u) => s + u.sla_breached_total, 0);
  const totalReopened = data.reduce((s, u) => s + u.tickets_reopened, 0);
  const avgScore = data.length > 0 ? Math.round(data.reduce((s, u) => s + u.performance_score, 0) / data.length) : 0;

  const cards = [
    { label: "Tickets resueltos", value: totalResolved, icon: <CheckCircle className="w-5 h-5 text-emerald-500" />, color: "text-emerald-600" },
    { label: "Tickets vencidos (SLA)", value: totalBreached, icon: <AlertTriangle className="w-5 h-5 text-red-500" />, color: "text-red-600" },
    { label: "Tickets reabiertos", value: totalReopened, icon: <RefreshCw className="w-5 h-5 text-orange-500" />, color: "text-orange-600" },
    { label: "Score promedio equipo", value: `${avgScore}/100`, icon: <Star className="w-5 h-5 text-blue-500" />, color: "text-blue-600" },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((c) => (
        <div key={c.label} className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-3">
          <div className="p-2 bg-gray-50 rounded-lg">{c.icon}</div>
          <div>
            <p className="text-xs text-gray-500">{c.label}</p>
            <p className={`text-xl font-bold ${c.color}`}>{c.value}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Performance Table
// ---------------------------------------------------------------------------
function PerformanceTable({ data, isLoading }: { data: UserPerformanceItem[]; isLoading: boolean }) {
  const sorted = [...data].sort((a, b) => b.performance_score - a.performance_score);

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-14 bg-gray-100 rounded animate-pulse" />
        ))}
      </div>
    );
  }

  if (sorted.length === 0) {
    return (
      <p className="text-sm text-gray-400 text-center py-10">
        No hay datos de agentes en el período seleccionado.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm min-w-[900px]">
        <thead>
          <tr className="border-b border-gray-200 text-left">
            <th className="pb-3 font-medium text-gray-500 w-8">#</th>
            <th className="pb-3 font-medium text-gray-500">Agente</th>
            <th className="pb-3 font-medium text-gray-500 text-center">Asignados</th>
            <th className="pb-3 font-medium text-gray-500 text-center">Resueltos</th>
            <th className="pb-3 font-medium text-gray-500 text-center">Activos</th>
            <th className="pb-3 font-medium text-gray-500 text-center">T. Resolución</th>
            <th className="pb-3 font-medium text-gray-500 text-center">1ª Respuesta</th>
            <th className="pb-3 font-medium text-gray-500 text-center">SLA %</th>
            <th className="pb-3 font-medium text-gray-500 text-center">Vencidos</th>
            <th className="pb-3 font-medium text-gray-500 text-center">Reabiertos</th>
            <th className="pb-3 font-medium text-gray-500 text-center">Score / Bono</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {sorted.map((u, idx) => (
            <tr key={u.user_id} className="hover:bg-gray-50 transition-colors">
              <td className="py-3.5 text-base">{medal(idx)}</td>
              <td className="py-3.5">
                <p className="font-medium text-gray-900">{u.user_name}</p>
                <p className="text-xs text-gray-400">{u.user_email} · {ROLE_LABEL[u.role] ?? u.role}</p>
              </td>
              <td className="py-3.5 text-center font-medium text-gray-700">{u.assigned_total}</td>
              <td className="py-3.5 text-center">
                <span className="font-medium text-emerald-600">{u.resolved_total}</span>
                {u.assigned_total > 0 && (
                  <span className="text-xs text-gray-400 ml-1">
                    ({Math.round(u.resolved_total / u.assigned_total * 100)}%)
                  </span>
                )}
              </td>
              <td className="py-3.5 text-center text-gray-500">{u.active_total}</td>
              <td className="py-3.5 text-center">
                <span className={u.avg_resolution_hours !== null && u.avg_resolution_hours <= 8 ? "text-emerald-600 font-medium" : "text-gray-700"}>
                  {fmtHours(u.avg_resolution_hours)}
                </span>
              </td>
              <td className="py-3.5 text-center">
                <span className={u.avg_first_response_hours !== null && u.avg_first_response_hours <= 1 ? "text-emerald-600 font-medium" : "text-gray-700"}>
                  {fmtHours(u.avg_first_response_hours)}
                </span>
              </td>
              <td className="py-3.5 text-center">
                {u.sla_compliance_pct !== null ? (
                  <span className={
                    u.sla_compliance_pct >= 90 ? "text-emerald-600 font-medium" :
                    u.sla_compliance_pct >= 70 ? "text-yellow-600 font-medium" :
                    "text-red-600 font-medium"
                  }>
                    {u.sla_compliance_pct}%
                  </span>
                ) : <span className="text-gray-400">—</span>}
              </td>
              <td className="py-3.5 text-center">
                {u.sla_breached_total > 0 ? (
                  <span className="text-red-600 font-medium">{u.sla_breached_total}</span>
                ) : <span className="text-emerald-600 font-medium">0</span>}
              </td>
              <td className="py-3.5 text-center">
                {u.tickets_reopened > 0 ? (
                  <span className="text-orange-600 font-medium">
                    {u.tickets_reopened}
                    {u.reopen_rate_pct !== null && (
                      <span className="text-xs text-gray-400 ml-1">({u.reopen_rate_pct}%)</span>
                    )}
                  </span>
                ) : <span className="text-emerald-600 font-medium">0</span>}
              </td>
              <td className="py-3.5 text-center">
                <div className="flex flex-col items-center gap-1">
                  <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full border ${scoreColor(u.performance_score)}`}>
                    {u.performance_score}/100 · {u.score_label}
                  </span>
                  <div className="w-20 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${scoreBar(u.performance_score)}`} style={{ width: `${u.performance_score}%` }} />
                  </div>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Urgency Abuse Tab (existing)
// ---------------------------------------------------------------------------
function UrgencyAbuseTab({ days }: { days: number }) {
  const { data: abuse = [], isLoading } = useUrgencyAbuse();

  const TrendIcon = ({ trend }: { trend: string }) => {
    if (trend === "worsened") return <TrendingUp className="w-4 h-4 text-red-500" />;
    if (trend === "improved") return <TrendingDown className="w-4 h-4 text-green-500" />;
    return <Minus className="w-4 h-4 text-gray-400" />;
  };

  if (isLoading) {
    return <div className="space-y-2">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-10 bg-gray-100 rounded animate-pulse" />)}</div>;
  }

  if (abuse.length === 0) {
    return <p className="text-sm text-gray-400 text-center py-8">No hay casos de abuso detectados en el período.</p>;
  }

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-gray-200 text-left">
          <th className="pb-3 font-medium text-gray-500">Usuario</th>
          <th className="pb-3 font-medium text-gray-500">Área</th>
          <th className="pb-3 font-medium text-gray-500 text-right">Total</th>
          <th className="pb-3 font-medium text-gray-500 text-right">Urgentes</th>
          <th className="pb-3 font-medium text-gray-500 text-right">% Urgentes</th>
          <th className="pb-3 font-medium text-gray-500 text-center">Tendencia</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-100">
        {abuse.map((a) => (
          <tr key={a.user_id}>
            <td className="py-3 font-medium text-gray-900">{a.user_name}</td>
            <td className="py-3 text-gray-500">{a.area_name ?? "—"}</td>
            <td className="py-3 text-right text-gray-600">{a.total_tickets}</td>
            <td className="py-3 text-right text-orange-600 font-medium">{a.urgent_tickets}</td>
            <td className="py-3 text-right">
              <span className={`font-medium ${a.urgent_pct >= 50 ? "text-red-600" : "text-orange-500"}`}>
                {Math.round(a.urgent_pct)}%
              </span>
            </td>
            <td className="py-3 flex justify-center"><TrendIcon trend={a.trend} /></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function ReportsPage() {
  const { data: session } = useSession();
  const role = session?.user?.role ?? "requester";
  const [activeTab, setActiveTab] = useState<"performance" | "urgency">("performance");
  const [days, setDays] = useState(30);
  const { data: perfData = [], isLoading } = useUserPerformance(days);

  if (role !== "admin" && role !== "supervisor") {
    return (
      <div className="flex flex-col items-center justify-center min-h-64 text-center">
        <p className="text-4xl mb-4">🔒</p>
        <h2 className="text-lg font-semibold text-gray-800">Acceso denegado</h2>
        <p className="text-sm text-gray-500 mt-1">No tienes permisos para ver esta sección.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Reportes de rendimiento</h1>
          <p className="text-sm text-gray-500 mt-0.5">Métricas por agente para decisiones de gestión y bonos</p>
        </div>
        {/* Period selector */}
        <div className="relative">
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="appearance-none pl-3 pr-8 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#1a2c4e] cursor-pointer"
          >
            {PERIOD_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <ChevronDown className="absolute right-2.5 top-2.5 w-4 h-4 text-gray-400 pointer-events-none" />
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 gap-1">
        <button
          onClick={() => setActiveTab("performance")}
          className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "performance" ? "border-[#1a2c4e] text-[#1a2c4e]" : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          <Trophy className="w-4 h-4" />
          Rendimiento por agente
        </button>
        <button
          onClick={() => setActiveTab("urgency")}
          className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "urgency" ? "border-[#1a2c4e] text-[#1a2c4e]" : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          <AlertTriangle className="w-4 h-4" />
          Abuso de urgencia
        </button>
      </div>

      {activeTab === "performance" && (
        <>
          <SummaryCards data={perfData} />

          {/* Score legend */}
          <div className="flex flex-wrap gap-3 text-xs">
            <span className="font-medium text-gray-500">Score para bono:</span>
            {[
              { label: "🥇 Excelente (90-100)", cls: "bg-emerald-100 text-emerald-700 border border-emerald-200" },
              { label: "✅ Bueno (75-89)", cls: "bg-blue-100 text-blue-700 border border-blue-200" },
              { label: "⚠️ Regular (60-74)", cls: "bg-yellow-100 text-yellow-700 border border-yellow-200" },
              { label: "❌ Bajo (<60)", cls: "bg-red-100 text-red-700 border border-red-200" },
            ].map((l) => (
              <span key={l.label} className={`px-2.5 py-1 rounded-full font-medium ${l.cls}`}>{l.label}</span>
            ))}
          </div>

          {/* Score formula explanation */}
          <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 text-xs text-blue-800 space-y-1">
            <p className="font-semibold">¿Cómo se calcula el score?</p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-1">
              <div className="bg-white rounded-lg p-2 border border-blue-100">
                <p className="font-semibold">Eficiencia (40 pts)</p>
                <p className="text-blue-600 mt-0.5">% de tickets resueltos del total asignado</p>
              </div>
              <div className="bg-white rounded-lg p-2 border border-blue-100">
                <p className="font-semibold">Cumplimiento SLA (30 pts)</p>
                <p className="text-blue-600 mt-0.5">% de tickets resueltos dentro del plazo</p>
              </div>
              <div className="bg-white rounded-lg p-2 border border-blue-100">
                <p className="font-semibold">Calidad (20 pts)</p>
                <p className="text-blue-600 mt-0.5">Penaliza tickets reabiertos (-5 pts c/u)</p>
              </div>
              <div className="bg-white rounded-lg p-2 border border-blue-100">
                <p className="font-semibold">Respuesta (10 pts)</p>
                <p className="text-blue-600 mt-0.5">Penaliza SLA vencidos (-2 pts c/u)</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <PerformanceTable data={perfData} isLoading={isLoading} />
          </div>
        </>
      )}

      {activeTab === "urgency" && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="mb-4">
            <h2 className="text-sm font-semibold text-gray-800">Reporte de abuso de urgencia</h2>
            <p className="text-xs text-gray-500 mt-0.5">Usuarios que marcan tickets como urgentes con mayor frecuencia que el umbral configurado.</p>
          </div>
          <UrgencyAbuseTab days={days} />
        </div>
      )}
    </div>
  );
}
