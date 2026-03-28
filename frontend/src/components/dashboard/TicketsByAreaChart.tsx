"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { TicketsByAreaItem } from "@/types/admin";

export function TicketsByAreaChart({ data }: { data: TicketsByAreaItem[] }) {
  if (!data.length)
    return (
      <p className="text-sm text-gray-400 text-center py-8">
        Sin datos disponibles.
      </p>
    );

  const chartData = data.map((d) => ({
    name:
      d.area_name.length > 18 ? d.area_name.slice(0, 18) + "…" : d.area_name,
    Abiertos: d.open,
    "En proceso": d.in_progress,
    Resueltos: d.resolved,
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart
        data={chartData}
        layout="vertical"
        margin={{ top: 0, right: 20, left: 0, bottom: 0 }}
      >
        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" tick={{ fontSize: 11 }} />
        <YAxis
          type="category"
          dataKey="name"
          tick={{ fontSize: 11 }}
          width={110}
        />
        <Tooltip />
        <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="Abiertos" fill="#3b82f6" radius={[0, 3, 3, 0] as [number, number, number, number]} />
        <Bar dataKey="En proceso" fill="#f59e0b" radius={[0, 3, 3, 0] as [number, number, number, number]} />
        <Bar dataKey="Resueltos" fill="#22c55e" radius={[0, 3, 3, 0] as [number, number, number, number]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
