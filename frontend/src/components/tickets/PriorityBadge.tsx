import { cn } from "@/lib/utils";
import type { TicketPriority } from "@/types/ticket";

const CONFIG: Record<TicketPriority, { label: string; className: string }> = {
  low:    { label: "Baja",    className: "bg-gray-100 text-gray-600" },
  medium: { label: "Media",   className: "bg-blue-100 text-blue-700" },
  high:   { label: "Alta",    className: "bg-orange-100 text-orange-700" },
  urgent: { label: "Urgente", className: "bg-red-100 text-red-700" },
};

export function PriorityBadge({ priority }: { priority: TicketPriority }) {
  const { label, className } = CONFIG[priority] ?? { label: priority, className: "bg-gray-100 text-gray-600" };
  return (
    <span className={cn("inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium", className)}>
      {label}
    </span>
  );
}
