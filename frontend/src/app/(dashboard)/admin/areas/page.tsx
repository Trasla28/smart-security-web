"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm, type UseFormReturn } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import * as Dialog from "@radix-ui/react-dialog";
import { Plus, Edit2, ChevronDown, ChevronRight, X, Users } from "lucide-react";
import api from "@/lib/api";
import type { Area, AreaMember } from "@/types/admin";

const areaSchema = z.object({
  name: z.string().min(1, "El nombre es requerido"),
  description: z.string().optional(),
  manager_id: z.string().optional(),
});

type AreaForm = z.infer<typeof areaSchema>;

const inputClass =
  "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2c4e]";
const labelClass = "block text-sm font-medium text-gray-700 mb-1";

function MembersPanel({ areaId }: { areaId: string }) {
  const { data: members = [], isLoading } = useQuery({
    queryKey: ["area-members", areaId],
    queryFn: async () => {
      const res = await api.get<AreaMember[]>(`/areas/${areaId}/members`);
      return res.data;
    },
  });

  if (isLoading)
    return (
      <div className="px-5 pb-4">
        <div className="h-8 bg-gray-100 rounded animate-pulse" />
      </div>
    );

  return (
    <div className="px-5 pb-4 border-t border-gray-100 pt-3">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1">
        <Users className="w-3 h-3" /> Miembros ({members.length})
      </p>
      {members.length === 0 ? (
        <p className="text-xs text-gray-400">Sin miembros asignados.</p>
      ) : (
        <div className="space-y-1">
          {members.map((m) => (
            <div key={m.id} className="flex items-center gap-2 text-xs">
              <span className="text-gray-800 font-medium">{m.full_name}</span>
              <span className="text-gray-400">{m.email}</span>
              {m.is_primary && (
                <span className="px-1.5 py-0.5 bg-blue-100 text-blue-600 rounded text-xs">
                  Principal
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function AreaFormFields({ form }: { form: UseFormReturn<AreaForm> }) {
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
        <textarea
          {...form.register("description")}
          className={inputClass}
          rows={2}
        />
      </div>
      <div>
        <label className={labelClass}>ID del responsable (opcional)</label>
        <input
          {...form.register("manager_id")}
          className={inputClass}
          placeholder="UUID del usuario responsable"
        />
      </div>
    </>
  );
}

export default function AdminAreasPage() {
  const qc = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [editArea, setEditArea] = useState<Area | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data: areas = [], isLoading } = useQuery({
    queryKey: ["admin-areas"],
    queryFn: async () => {
      const res = await api.get<{ items: Area[] }>("/areas");
      return res.data.items;
    },
  });

  const createMutation = useMutation({
    mutationFn: (d: AreaForm) => api.post("/areas", d).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-areas"] });
      setCreateOpen(false);
      createForm.reset();
    },
  });

  const editMutation = useMutation({
    mutationFn: ({ id, ...d }: AreaForm & { id: string }) =>
      api.patch(`/areas/${id}`, d).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-areas"] });
      setEditArea(null);
    },
  });

  const createForm = useForm<AreaForm>({ resolver: zodResolver(areaSchema) });
  const editForm = useForm<AreaForm>({ resolver: zodResolver(areaSchema) });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Áreas</h1>
        <Dialog.Root open={createOpen} onOpenChange={setCreateOpen}>
          <Dialog.Trigger asChild>
            <button className="flex items-center gap-1.5 px-4 py-2 bg-[#1a2c4e] text-white rounded-lg text-sm font-medium hover:bg-[#243d6a] transition-colors">
              <Plus className="w-4 h-4" /> Nueva área
            </button>
          </Dialog.Trigger>
          <Dialog.Portal>
            <Dialog.Overlay className="fixed inset-0 bg-black/40 z-50" />
            <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-xl shadow-xl p-6 w-full max-w-md z-50">
              <div className="flex items-center justify-between mb-5">
                <Dialog.Title className="font-semibold text-gray-900">
                  Nueva área
                </Dialog.Title>
                <Dialog.Close>
                  <X className="w-4 h-4 text-gray-400" />
                </Dialog.Close>
              </div>
              <form
                onSubmit={createForm.handleSubmit((d) =>
                  createMutation.mutate(d)
                )}
                className="space-y-4"
              >
                <AreaFormFields form={createForm} />
                {createMutation.isError && (
                  <p className="text-xs text-red-500">
                    Error al crear área. Intenta nuevamente.
                  </p>
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
                    <button
                      type="button"
                      className="px-4 py-2 border border-gray-300 rounded-lg text-sm"
                    >
                      Cancelar
                    </button>
                  </Dialog.Close>
                </div>
              </form>
            </Dialog.Content>
          </Dialog.Portal>
        </Dialog.Root>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
        {isLoading ? (
          <div className="p-6 space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-12 bg-gray-100 rounded animate-pulse" />
            ))}
          </div>
        ) : areas.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-8">
            No hay áreas creadas.
          </p>
        ) : (
          areas.map((area) => (
            <div key={area.id}>
              <div className="flex items-center gap-3 px-5 py-4 hover:bg-gray-50">
                <button
                  onClick={() =>
                    setExpandedId(expandedId === area.id ? null : area.id)
                  }
                  className="text-gray-400 hover:text-gray-600"
                >
                  {expandedId === area.id ? (
                    <ChevronDown className="w-4 h-4" />
                  ) : (
                    <ChevronRight className="w-4 h-4" />
                  )}
                </button>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900 text-sm">
                    {area.name}
                  </p>
                  {area.description && (
                    <p className="text-xs text-gray-400 truncate">
                      {area.description}
                    </p>
                  )}
                </div>
                <span
                  className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                    area.is_active
                      ? "bg-green-100 text-green-700"
                      : "bg-gray-100 text-gray-500"
                  }`}
                >
                  {area.is_active ? "Activa" : "Inactiva"}
                </span>
                <button
                  onClick={() => {
                    setEditArea(area);
                    editForm.reset({
                      name: area.name,
                      description: area.description ?? "",
                      manager_id: area.manager_id ?? "",
                    });
                  }}
                  className="p-1 text-gray-400 hover:text-gray-700"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
              </div>
              {expandedId === area.id && <MembersPanel areaId={area.id} />}
            </div>
          ))
        )}
      </div>

      {/* Edit modal */}
      <Dialog.Root
        open={!!editArea}
        onOpenChange={(o) => !o && setEditArea(null)}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/40 z-50" />
          <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-xl shadow-xl p-6 w-full max-w-md z-50">
            <div className="flex items-center justify-between mb-5">
              <Dialog.Title className="font-semibold text-gray-900">
                Editar área
              </Dialog.Title>
              <Dialog.Close>
                <X className="w-4 h-4 text-gray-400" />
              </Dialog.Close>
            </div>
            <form
              onSubmit={editForm.handleSubmit((d) =>
                editMutation.mutate({ id: editArea!.id, ...d })
              )}
              className="space-y-4"
            >
              <AreaFormFields form={editForm} />
              {editMutation.isError && (
                <p className="text-xs text-red-500">
                  Error al guardar cambios. Intenta nuevamente.
                </p>
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
                  <button
                    type="button"
                    className="px-4 py-2 border border-gray-300 rounded-lg text-sm"
                  >
                    Cancelar
                  </button>
                </Dialog.Close>
              </div>
            </form>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
