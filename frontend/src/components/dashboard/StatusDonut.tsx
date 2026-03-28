"use client";

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { TicketsByStatusItem } from "@/types/admin";

const STATUS_COLORS: Record<string, string> = {
  open: "#3b82f6",
  in_progress: "#f59e0b",
  pending: "#f97316",
  escalated: "#ef4444",
  resolved: "#22c55e",
  closed: "#6b7280",
};

const STATUS_LABELS: Record<string, string> = {
  open: "Abierto",
  in_progress: "En proceso",
  pending: "Pendiente",
  escalated: "Escalado",
  resolved: "Resuelto",
  closed: "Cerrado",
};

export function StatusDonut({ data }: { data: TicketsByStatusItem[] }) {
  if (!data.length)
    return (
      <p className="text-sm text-gray-400 text-center py-8">
        Sin datos disponibles.
      </p>
    );

  const chartData = data.map((d) => ({
    name: STATUS_LABELS[d.status] ?? d.status,
    value: d.count,
    color: STATUS_COLORS[d.status] ?? "#6b7280",
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={100}
          paddingAngle={2}
          dataKey="value"
        >
          {chartData.map((entry, index) => (
            <Cell key={index} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip formatter={(value, name) => [`${value} tickets`, name]} />
        <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
      </PieChart>
    </ResponsiveContainer>
  );
}
