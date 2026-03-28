"use client";

import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { es } from "date-fns/locale";
import { StatusBadge } from "./StatusBadge";
import { PriorityBadge } from "./PriorityBadge";
import { SLAIndicator } from "./SLAIndicator";
import type { TicketListItem } from "@/types/ticket";

interface TicketTableProps {
  tickets: TicketListItem[];
  isLoading?: boolean;
}

export function TicketTable({ tickets, isLoading }: TicketTableProps) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-14 bg-gray-100 rounded-lg animate-pulse" />
        ))}
      </div>
    );
  }

  if (tickets.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400">
        <p className="text-sm">No hay tickets que mostrar.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left">
            <th className="pb-3 pr-4 font-medium text-gray-500 w-24">#</th>
            <th className="pb-3 pr-4 font-medium text-gray-500">Título</th>
            <th className="pb-3 pr-4 font-medium text-gray-500 w-32">Estado</th>
            <th className="pb-3 pr-4 font-medium text-gray-500 w-28">Prioridad</th>
            <th className="pb-3 pr-4 font-medium text-gray-500 w-32">Área</th>
            <th className="pb-3 pr-4 font-medium text-gray-500 w-36">Asignado</th>
            <th className="pb-3 pr-4 font-medium text-gray-500 w-28">SLA</th>
            <th className="pb-3 font-medium text-gray-500 w-28">Creado</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {tickets.map((ticket) => (
            <tr key={ticket.id} className="hover:bg-gray-50 transition-colors">
              <td className="py-3 pr-4">
                <Link href={`/tickets/${ticket.id}`} className="font-mono text-xs text-[#1a2c4e] hover:underline">
                  {ticket.ticket_number}
                </Link>
              </td>
              <td className="py-3 pr-4">
                <Link href={`/tickets/${ticket.id}`} className="font-medium text-gray-900 hover:text-[#1a2c4e] line-clamp-1">
                  {ticket.title}
                </Link>
                {ticket.category && (
                  <p className="text-xs text-gray-400 mt-0.5">{ticket.category.name}</p>
                )}
              </td>
              <td className="py-3 pr-4">
                <StatusBadge status={ticket.status} />
              </td>
              <td className="py-3 pr-4">
                <PriorityBadge priority={ticket.priority} />
              </td>
              <td className="py-3 pr-4 text-gray-600 text-xs">
                {ticket.area?.name ?? <span className="text-gray-300">—</span>}
              </td>
              <td className="py-3 pr-4 text-xs text-gray-600">
                {ticket.assignee?.full_name ?? <span className="text-gray-300">Sin asignar</span>}
              </td>
              <td className="py-3 pr-4">
                <SLAIndicator
                  slaStatus={ticket.sla_status}
                  slaPercentage={null}
                  slaDueAt={ticket.sla_due_at}
                  compact
                />
              </td>
              <td className="py-3 text-xs text-gray-400">
                {formatDistanceToNow(new Date(ticket.created_at), { addSuffix: true, locale: es })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
