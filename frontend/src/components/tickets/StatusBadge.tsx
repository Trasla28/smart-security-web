import { cn } from "@/lib/utils";
import type { TicketStatus } from "@/types/ticket";

const CONFIG: Record<TicketStatus, { label: string; className: string }> = {
  open:        { label: "Abierto",      className: "bg-blue-100 text-blue-700" },
  in_progress: { label: "En proceso",   className: "bg-yellow-100 text-yellow-700" },
  pending:     { label: "Pendiente",    className: "bg-orange-100 text-orange-700" },
  escalated:   { label: "Escalado",     className: "bg-red-100 text-red-700" },
  resolved:    { label: "Resuelto",     className: "bg-green-100 text-green-700" },
  closed:      { label: "Cerrado",      className: "bg-gray-100 text-gray-600" },
};

export function StatusBadge({ status }: { status: TicketStatus }) {
  const { label, className } = CONFIG[status] ?? { label: status, className: "bg-gray-100 text-gray-600" };
  return (
    <span className={cn("inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium", className)}>
      {label}
    </span>
  );
}
