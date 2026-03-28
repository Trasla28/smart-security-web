"use client";

import { Suspense } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { useSession } from "next-auth/react";
import { useQuery } from "@tanstack/react-query";
import { useTicketList } from "@/hooks/useTickets";
import { TicketTable } from "@/components/tickets/TicketTable";
import Link from "next/link";
import { Plus, ChevronLeft, ChevronRight, UserCircle } from "lucide-react";
import api from "@/lib/api";

const STATUSES = [
  { value: "", label: "Todos los estados" },
  { value: "open", label: "Abiertos" },
  { value: "in_progress", label: "En proceso" },
  { value: "pending", label: "Pendientes" },
  { value: "escalated", label: "Escalados" },
  { value: "resolved", label: "Resueltos" },
  { value: "closed", label: "Cerrados" },
];

const PRIORITIES = [
  { value: "", label: "Todas las prioridades" },
  { value: "urgent", label: "Urgente" },
  { value: "high", label: "Alta" },
  { value: "medium", label: "Media" },
  { value: "low", label: "Baja" },
];

const SORT_OPTIONS = [
  { value: "created_at", label: "Más recientes primero" },
  { value: "priority", label: "Por prioridad (Urgente → Baja)" },
];

const selectClass =
  "px-3 py-1.5 border border-gray-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#1a2c4e] w-full";

interface UserOption { id: string; full_name: string; role: string }

function TicketListContent() {
  const { data: session } = useSession();
  const currentUserId = session?.user?.id ?? "";
  const role = session?.user?.role ?? "requester";

  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const status = searchParams.get("status") ?? "";
  const priority = searchParams.get("priority") ?? "";
  const assigned_to = searchParams.get("assigned_to") ?? "";
  const sort_by = searchParams.get("sort_by") ?? "created_at";
  const page = Number(searchParams.get("page") ?? "1");
  const size = 20;

  const { data, isLoading } = useTicketList({ status, priority, assigned_to, sort_by, page, size });

  // Fetch agents/users for the assignee filter (only for admins/supervisors)
  const { data: usersData = [] } = useQuery<UserOption[]>({
    queryKey: ["users-filter"],
    queryFn: async () => {
      const res = await api.get<{ items: UserOption[] }>("/users", { params: { size: 200 } });
      return res.data.items ?? [];
    },
    enabled: role === "admin" || role === "supervisor",
  });

  const agents = usersData.filter((u) => u.role === "agent" || u.role === "admin" || u.role === "supervisor");

  function setParam(key: string, value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (value) params.set(key, value);
    else params.delete(key);
    params.delete("page");
    router.push(`${pathname}?${params.toString()}`);
  }

  function setPage(p: number) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("page", String(p));
    router.push(`${pathname}?${params.toString()}`);
  }

  function setMyTickets() {
    const params = new URLSearchParams(searchParams.toString());
    params.set("assigned_to", currentUserId);
    params.delete("page");
    router.push(`${pathname}?${params.toString()}`);
  }

  function clearFilters() {
    router.push(pathname);
  }

  const hasActiveFilters = status || priority || assigned_to || sort_by !== "created_at";
  const isMyTickets = assigned_to === currentUserId;

  return (
    <>
      {data && (
        <p className="text-sm text-gray-500 mt-0.5">
          {data.total} ticket{data.total !== 1 ? "s" : ""} encontrado{data.total !== 1 ? "s" : ""}
          {isMyTickets && <span className="ml-2 text-xs bg-[#1a2c4e] text-white px-2 py-0.5 rounded-full">Mis tickets</span>}
        </p>
      )}

      <div className="bg-white rounded-xl border border-gray-200 p-4">
        {/* Filters */}
        <div className="flex flex-wrap gap-3 mb-5 items-end">
          {/* Quick filter: Mis tickets */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Acceso rápido</label>
            <button
              onClick={isMyTickets ? clearFilters : setMyTickets}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                isMyTickets
                  ? "bg-[#1a2c4e] text-white border-[#1a2c4e]"
                  : "bg-white text-gray-700 border-gray-200 hover:border-[#1a2c4e] hover:text-[#1a2c4e]"
              }`}
            >
              <UserCircle className="w-4 h-4" />
              Mis tickets
            </button>
          </div>

          {/* Estado */}
          <div className="flex flex-col gap-1 min-w-[160px]">
            <label className="text-xs text-gray-500">Estado</label>
            <select value={status} onChange={(e) => setParam("status", e.target.value)} className={selectClass}>
              {STATUSES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </div>

          {/* Prioridad */}
          <div className="flex flex-col gap-1 min-w-[160px]">
            <label className="text-xs text-gray-500">Prioridad</label>
            <select value={priority} onChange={(e) => setParam("priority", e.target.value)} className={selectClass}>
              {PRIORITIES.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
            </select>
          </div>

          {/* Asignado a — solo admin/supervisor ven la lista completa; agentes solo ven sus propios */}
          {(role === "admin" || role === "supervisor") && (
            <div className="flex flex-col gap-1 min-w-[180px]">
              <label className="text-xs text-gray-500">Asignado a</label>
              <select
                value={assigned_to}
                onChange={(e) => setParam("assigned_to", e.target.value)}
                className={selectClass}
              >
                <option value="">Todos los agentes</option>
                {agents.map((u) => (
                  <option key={u.id} value={u.id}>{u.full_name}</option>
                ))}
              </select>
            </div>
          )}

          {/* Ordenar por */}
          <div className="flex flex-col gap-1 min-w-[210px]">
            <label className="text-xs text-gray-500">Ordenar por</label>
            <select value={sort_by} onChange={(e) => setParam("sort_by", e.target.value)} className={selectClass}>
              {SORT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>

          {/* Limpiar filtros */}
          {hasActiveFilters && (
            <div className="flex flex-col gap-1 justify-end">
              <label className="text-xs text-transparent select-none">·</label>
              <button
                onClick={clearFilters}
                className="px-3 py-1.5 text-sm text-gray-500 hover:text-red-600 border border-gray-200 rounded-lg hover:border-red-300 transition-colors"
              >
                Limpiar filtros
              </button>
            </div>
          )}
        </div>

        <TicketTable tickets={data?.items ?? []} isLoading={isLoading} />

        {data && data.pages > 1 && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-100">
            <p className="text-xs text-gray-400">Página {data.page} de {data.pages}</p>
            <div className="flex gap-1">
              <button
                onClick={() => setPage(page - 1)}
                disabled={page <= 1}
                className="p-1.5 rounded border border-gray-200 disabled:opacity-40 hover:bg-gray-50"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setPage(page + 1)}
                disabled={page >= data.pages}
                className="p-1.5 rounded border border-gray-200 disabled:opacity-40 hover:bg-gray-50"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

export default function TicketsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Tickets</h1>
        <Link
          href="/tickets/new"
          className="flex items-center gap-1.5 px-4 py-2 bg-[#1a2c4e] text-white rounded-lg text-sm font-medium hover:bg-[#243d6a] transition-colors"
        >
          <Plus className="w-4 h-4" /> Nueva solicitud
        </Link>
      </div>

      <Suspense fallback={
        <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-14 bg-gray-100 rounded-lg animate-pulse" />
          ))}
        </div>
      }>
        <TicketListContent />
      </Suspense>
    </div>
  );
}
