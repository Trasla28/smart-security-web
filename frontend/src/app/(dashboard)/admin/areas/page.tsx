"use client";

import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm, type UseFormReturn } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import * as Dialog from "@radix-ui/react-dialog";
import {
  Plus, Edit2, ChevronDown, ChevronRight,
  X, Users, Trash2, AlertTriangle,
} from "lucide-react";
import api from "@/lib/api";
import type { Area, AreaMember, AdminUser } from "@/types/admin";

// member_ids is managed as plain React state — NOT inside react-hook-form
const areaSchema = z.object({
  name: z.string().min(1, "El nombre es requerido"),
  description: z.string().optional(),
  manager_id: z.string().optional(),
});

type AreaForm = z.infer<typeof areaSchema>;

const inputClass =
  "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2c4e]";
const labelClass = "block text-sm font-medium text-gray-700 mb-1";

// ---------------------------------------------------------------------------
// Members panel (expanded view per area row)
// ---------------------------------------------------------------------------

function MembersPanel({ area }: { area: Area }) {
  const { data: members = [], isLoading } = useQuery({
    queryKey: ["area-members", area.id],
    queryFn: async () => {
      const res = await api.get<AreaMember[]>(`/areas/${area.id}/members`);
      return res.data;
    },
  });

  if (isLoading)
    return (
      <div className="px-5 pb-4">
        <div className="h-8 bg-gray-100 rounded animate-pulse" />
      </div>
    );

  const manager = members.find((m) => m.id === area.manager_id) ?? null;
  const team = members.filter((m) => m.id !== area.manager_id);

  return (
    <div className="px-5 pb-4 border-t border-gray-100 pt-3 space-y-3">
      <div>
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
          Responsable
        </p>
        {manager ? (
          <div className="flex items-center gap-2 text-xs">
            <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-[#1a2c4e] text-white font-semibold text-xs">
              {manager.full_name.charAt(0).toUpperCase()}
            </span>
            <span className="text-gray-800 font-medium">{manager.full_name}</span>
            <span className="text-gray-400">{manager.email}</span>
            <span className="px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded text-xs font-medium">
              Responsable
            </span>
          </div>
        ) : (
          <p className="text-xs text-gray-400 italic">Sin responsable asignado.</p>
        )}
      </div>

      <div>
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5 flex items-center gap-1">
          <Users className="w-3 h-3" /> Equipo ({team.length})
        </p>
        {team.length === 0 ? (
          <p className="text-xs text-gray-400 italic">Sin miembros en el equipo.</p>
        ) : (
          <div className="space-y-1">
            {team.map((m) => (
              <div key={m.id} className="flex items-center gap-2 text-xs">
                <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-gray-200 text-gray-600 font-semibold text-xs">
                  {m.full_name.charAt(0).toUpperCase()}
                </span>
                <span className="text-gray-800 font-medium">{m.full_name}</span>
                <span className="text-gray-400">{m.email}</span>
                <span className="px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded text-xs">
                  {m.role}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Form fields (name / description / manager) — no member_ids here
// ---------------------------------------------------------------------------

function AreaFormFields({ form }: { form: UseFormReturn<AreaForm> }) {
  const { data: users = [], isLoading: loadingUsers } = useQuery({
    queryKey: ["users-list"],
    queryFn: async () => {
      const res = await api.get<{ items: AdminUser[] }>("/users?size=100&is_active=true");
      return res.data.items;
    },
    staleTime: 60_000,
  });

  return (
    <>
      <div>
        <label className={labelClass}>Nombre</label>
        <input {...form.register("name")} className={inputClass} />
        {form.formState.errors.name && (
          <p className="text-xs text-red-500 mt-1">
            {form.formState.errors.name.message}
          </p>
        )}
      </div>

      <div>
        <label className={labelClass}>Descripción</label>
        <textarea {...form.register("description")} className={inputClass} rows={2} />
      </div>

      <div>
        <label className={labelClass}>Responsable (opcional)</label>
        <select
          {...form.register("manager_id")}
          className={inputClass}
          disabled={loadingUsers}
        >
          <option value="">
            {loadingUsers ? "Cargando usuarios…" : "— Sin responsable —"}
          </option>
          {users.map((u) => (
            <option key={u.id} value={u.id}>
              {u.full_name} ({u.email})
            </option>
          ))}
        </select>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Team member checklist — pure state, no react-hook-form
// ---------------------------------------------------------------------------

function TeamChecklist({
  excludeId,
  selectedIds,
  onChange,
}: {
  excludeId?: string;
  selectedIds: string[];
  onChange: (ids: string[]) => void;
}) {
  const { data: users = [], isLoading } = useQuery({
    queryKey: ["users-list"],
    queryFn: async () => {
      const res = await api.get<{ items: AdminUser[] }>("/users?size=100&is_active=true");
      return res.data.items;
    },
    staleTime: 60_000,
  });

  const available = users.filter((u) => u.id !== excludeId);

  function toggle(id: string) {
    onChange(
      selectedIds.includes(id)
        ? selectedIds.filter((x) => x !== id)
        : [...selectedIds, id]
    );
  }

  if (isLoading)
    return <div className="h-24 bg-gray-100 rounded-lg animate-pulse" />;

  if (available.length === 0)
    return <p className="text-xs text-gray-400 italic py-2">No hay usuarios disponibles.</p>;

  return (
    <div className="border border-gray-300 rounded-lg max-h-44 overflow-y-auto divide-y divide-gray-100">
      {available.map((u) => (
        <label
          key={u.id}
          className="flex items-center gap-3 px-3 py-2 cursor-pointer hover:bg-gray-50 select-none"
        >
          <input
            type="checkbox"
            checked={selectedIds.includes(u.id)}
            onChange={() => toggle(u.id)}
            className="w-4 h-4 rounded accent-[#1a2c4e]"
          />
          <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-gray-200 text-gray-600 font-semibold text-xs flex-shrink-0">
            {u.full_name.charAt(0).toUpperCase()}
          </span>
          <span className="text-sm text-gray-800 flex-1 min-w-0 truncate">
            {u.full_name}{" "}
            <span className="text-gray-400 text-xs">({u.email})</span>
          </span>
        </label>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function AdminAreasPage() {
  const qc = useQueryClient();

  const [createOpen, setCreateOpen] = useState(false);
  const [editArea, setEditArea] = useState<Area | null>(null);
  const [deleteArea, setDeleteArea] = useState<Area | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // member_ids as plain state — separate from react-hook-form
  const [createMemberIds, setCreateMemberIds] = useState<string[]>([]);
  const [editMemberIds, setEditMemberIds] = useState<string[]>([]);

  const createForm = useForm<AreaForm>({ resolver: zodResolver(areaSchema) });
  const editForm = useForm<AreaForm>({ resolver: zodResolver(areaSchema) });

  // Pre-load current team when an area is opened for editing
  const { data: editAreaMembers = [], isSuccess: editMembersLoaded } = useQuery({
    queryKey: ["area-members-form", editArea?.id],
    queryFn: async () => {
      const res = await api.get<AreaMember[]>(`/areas/${editArea!.id}/members`);
      return res.data;
    },
    enabled: !!editArea,
    staleTime: 0,
  });

  const initializedRef = useRef<string | null>(null);
  useEffect(() => {
    if (!editArea || !editMembersLoaded) return;
    if (initializedRef.current === editArea.id) return;
    initializedRef.current = editArea.id;
    const teamIds = editAreaMembers
      .filter((m) => m.id !== editArea.manager_id)
      .map((m) => m.id);
    setEditMemberIds(teamIds);
  }, [editArea, editMembersLoaded, editAreaMembers]);

  // Areas list
  const { data: areas = [], isLoading } = useQuery({
    queryKey: ["admin-areas"],
    queryFn: async () => {
      const res = await api.get<Area[]>("/areas");
      return res.data;
    },
  });

  // --- Create ---
  const createMutation = useMutation({
    mutationFn: async (d: AreaForm) => {
      const area: Area = await api.post("/areas", d).then((r) => r.data);
      await Promise.all(
        createMemberIds.map((uid) =>
          api.post(`/areas/${area.id}/members`, { user_id: uid, is_primary: false })
        )
      );
      return area;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-areas"] });
      setCreateOpen(false);
      createForm.reset();
      setCreateMemberIds([]);
    },
  });

  // --- Edit ---
  const editMutation = useMutation({
    mutationFn: async ({ id, managerId, ...d }: AreaForm & { id: string; managerId: string }) => {
      await api.patch(`/areas/${id}`, d);
      const currentRes = await api.get<AreaMember[]>(`/areas/${id}/members`);
      const currentTeamIds = currentRes.data
        .filter((m) => m.id !== managerId)
        .map((m) => m.id);
      const toAdd = editMemberIds.filter((uid) => !currentTeamIds.includes(uid));
      const toRemove = currentTeamIds.filter((uid) => !editMemberIds.includes(uid));
      await Promise.all([
        ...toAdd.map((uid) =>
          api.post(`/areas/${id}/members`, { user_id: uid, is_primary: false })
        ),
        ...toRemove.map((uid) => api.delete(`/areas/${id}/members/${uid}`)),
      ]);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-areas"] });
      qc.invalidateQueries({ queryKey: ["area-members"] });
      setEditArea(null);
      setEditMemberIds([]);
      initializedRef.current = null;
    },
  });

  // --- Delete ---
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/areas/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-areas"] });
      setDeleteArea(null);
    },
  });

  const watchedManagerId = editForm.watch("manager_id");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Áreas</h1>

        {/* Create dialog */}
        <Dialog.Root
          open={createOpen}
          onOpenChange={(o) => {
            setCreateOpen(o);
            if (!o) { createForm.reset(); setCreateMemberIds([]); }
          }}
        >
          <Dialog.Trigger asChild>
            <button className="flex items-center gap-1.5 px-4 py-2 bg-[#1a2c4e] text-white rounded-lg text-sm font-medium hover:bg-[#243d6a] transition-colors">
              <Plus className="w-4 h-4" /> Nueva área
            </button>
          </Dialog.Trigger>
          <Dialog.Portal>
            <Dialog.Overlay className="fixed inset-0 bg-black/40 z-50" />
            <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-xl shadow-xl p-6 w-full max-w-md z-50 max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between mb-5">
                <Dialog.Title className="font-semibold text-gray-900">Nueva área</Dialog.Title>
                <Dialog.Close><X className="w-4 h-4 text-gray-400" /></Dialog.Close>
              </div>
              <form
                onSubmit={createForm.handleSubmit((d) => createMutation.mutate(d))}
                className="space-y-4"
              >
                <AreaFormFields form={createForm} />
                <div>
                  <label className={labelClass}>
                    Equipo{" "}
                    <span className="text-gray-400 font-normal">
                      ({createMemberIds.length} seleccionados)
                    </span>
                  </label>
                  <TeamChecklist
                    excludeId={createForm.watch("manager_id")}
                    selectedIds={createMemberIds}
                    onChange={setCreateMemberIds}
                  />
                </div>
                {createMutation.isError && (
                  <p className="text-xs text-red-500">Error al crear área. Intenta nuevamente.</p>
                )}
                <div className="flex gap-2 pt-2">
                  <button
                    type="submit"
                    disabled={createMutation.isPending}
                    className="flex-1 py-2 bg-[#1a2c4e] text-white rounded-lg text-sm font-medium disabled:opacity-60"
                  >
                    {createMutation.isPending ? "Creando..." : "Crear área"}
                  </button>
                  <Dialog.Close asChild>
                    <button type="button" className="px-4 py-2 border border-gray-300 rounded-lg text-sm">
                      Cancelar
                    </button>
                  </Dialog.Close>
                </div>
              </form>
            </Dialog.Content>
          </Dialog.Portal>
        </Dialog.Root>
      </div>

      {/* Areas list */}
      <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
        {isLoading ? (
          <div className="p-6 space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-12 bg-gray-100 rounded animate-pulse" />
            ))}
          </div>
        ) : areas.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-8">No hay áreas creadas.</p>
        ) : (
          areas.map((area) => (
            <div key={area.id}>
              <div className="flex items-center gap-3 px-5 py-4 hover:bg-gray-50">
                <button
                  onClick={() => setExpandedId(expandedId === area.id ? null : area.id)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  {expandedId === area.id
                    ? <ChevronDown className="w-4 h-4" />
                    : <ChevronRight className="w-4 h-4" />}
                </button>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900 text-sm">{area.name}</p>
                  {area.description && (
                    <p className="text-xs text-gray-400 truncate">{area.description}</p>
                  )}
                </div>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                  area.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
                }`}>
                  {area.is_active ? "Activa" : "Inactiva"}
                </span>
                <button
                  onClick={() => {
                    initializedRef.current = null;
                    setEditMemberIds([]);
                    setEditArea(area);
                    editForm.reset({
                      name: area.name,
                      description: area.description ?? "",
                      manager_id: area.manager_id ?? "",
                    });
                  }}
                  className="p-1 text-gray-400 hover:text-gray-700"
                  title="Editar área"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setDeleteArea(area)}
                  className="p-1 text-gray-400 hover:text-red-600"
                  title="Eliminar área"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
              {expandedId === area.id && <MembersPanel area={area} />}
            </div>
          ))
        )}
      </div>

      {/* Edit dialog */}
      <Dialog.Root
        open={!!editArea}
        onOpenChange={(o) => {
          if (!o) {
            setEditArea(null);
            setEditMemberIds([]);
            initializedRef.current = null;
          }
        }}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/40 z-50" />
          <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-xl shadow-xl p-6 w-full max-w-md z-50 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-5">
              <Dialog.Title className="font-semibold text-gray-900">Editar área</Dialog.Title>
              <Dialog.Close><X className="w-4 h-4 text-gray-400" /></Dialog.Close>
            </div>
            <form
              onSubmit={editForm.handleSubmit((d) =>
                editMutation.mutate({
                  id: editArea!.id,
                  managerId: d.manager_id ?? "",
                  ...d,
                })
              )}
              className="space-y-4"
            >
              <AreaFormFields form={editForm} />
              <div>
                <label className={labelClass}>
                  Equipo{" "}
                  <span className="text-gray-400 font-normal">
                    ({editMemberIds.length} seleccionados)
                  </span>
                </label>
                {!editMembersLoaded ? (
                  <div className="h-24 bg-gray-100 rounded-lg animate-pulse" />
                ) : (
                  <TeamChecklist
                    excludeId={watchedManagerId}
                    selectedIds={editMemberIds}
                    onChange={setEditMemberIds}
                  />
                )}
              </div>
              {editMutation.isError && (
                <p className="text-xs text-red-500">Error al guardar cambios. Intenta nuevamente.</p>
              )}
              <div className="flex gap-2 pt-2">
                <button
                  type="submit"
                  disabled={editMutation.isPending}
                  className="flex-1 py-2 bg-[#1a2c4e] text-white rounded-lg text-sm font-medium disabled:opacity-60"
                >
                  {editMutation.isPending ? "Guardando..." : "Guardar"}
                </button>
                <Dialog.Close asChild>
                  <button type="button" className="px-4 py-2 border border-gray-300 rounded-lg text-sm">
                    Cancelar
                  </button>
                </Dialog.Close>
              </div>
            </form>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      {/* Delete confirmation dialog */}
      <Dialog.Root
        open={!!deleteArea}
        onOpenChange={(o) => !o && setDeleteArea(null)}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/40 z-50" />
          <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-xl shadow-xl p-6 w-full max-w-sm z-50">
            <div className="flex flex-col items-center text-center gap-3">
              <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-red-600" />
              </div>
              <Dialog.Title className="font-semibold text-gray-900 text-lg">
                ¿Eliminar área?
              </Dialog.Title>
              <p className="text-sm text-gray-600">
                Estás a punto de eliminar el área{" "}
                <span className="font-semibold text-gray-900">{deleteArea?.name}</span>{" "}
                junto con su responsable y todo su equipo. Los tickets y categorías
                asociados perderán la referencia al área.
              </p>
              <p className="text-xs text-red-600 font-medium">
                Esta acción no se puede deshacer.
              </p>
            </div>
            {deleteMutation.isError && (
              <p className="text-xs text-red-500 text-center mt-3">
                Error al eliminar. Intenta nuevamente.
              </p>
            )}
            <div className="flex gap-2 mt-6">
              <button
                onClick={() => deleteMutation.mutate(deleteArea!.id)}
                disabled={deleteMutation.isPending}
                className="flex-1 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-60"
              >
                {deleteMutation.isPending ? "Eliminando..." : "Sí, eliminar"}
              </button>
              <Dialog.Close asChild>
                <button type="button" className="flex-1 py-2 border border-gray-300 rounded-lg text-sm">
                  Cancelar
                </button>
              </Dialog.Close>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
