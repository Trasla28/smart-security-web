"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm, type UseFormReturn } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import * as Dialog from "@radix-ui/react-dialog";
import { Plus, Edit2, Trash2, X } from "lucide-react";
import { cn } from "@/lib/utils";
import api from "@/lib/api";
import type { SLA } from "@/types/admin";

const PRIORITY_CONFIG: Record<string, { label: string; className: string }> = {
  low: { label: "Baja", className: "bg-gray-100 text-gray-600" },
  medium: { label: "Media", className: "bg-blue-100 text-blue-700" },
  high: { label: "Alta", className: "bg-orange-100 text-orange-700" },
  urgent: { label: "Urgente", className: "bg-red-100 text-red-700" },
};

const slaSchema = z.object({
  priority: z.string().optional(),
  response_hours: z.coerce.number().positive("Debe ser mayor a 0"),
  resolution_hours: z.coerce.number().positive("Debe ser mayor a 0"),
  is_active: z.boolean().default(true),
});

type SLAForm = z.infer<typeof slaSchema>;

const inputClass =
  "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2c4e]";
const labelClass = "block text-sm font-medium text-gray-700 mb-1";

function SLAFormFields({
  form,
  showActive,
}: {
  form: UseFormReturn<SLAForm>;
  showActive?: boolean;
}) {
  return (
    <>
      <div>
        <label className={labelClass}>Prioridad (opcional)</label>
        <select {...form.register("priority")} className={inputClass}>
          <option value="">— Sin prioridad específica —</option>
          <option value="low">Baja</option>
          <option value="medium">Media</option>
          <option value="high">Alta</option>
          <option value="urgent">Urgente</option>
        </select>
      </div>
      <div>
        <label className={labelClass}>Horas de respuesta</label>
        <input
          type="number"
          step="0.5"
          min="0.5"
          {...form.register("response_hours")}
          className={inputClass}
        />
        {form.formState.errors.response_hours && (
          <p className="text-xs text-red-500 mt-1">
            {form.formState.errors.response_hours.message}
          </p>
        )}
      </div>
      <div>
        <label className={labelClass}>Horas de resolución</label>
        <input
          type="number"
          step="0.5"
          min="0.5"
          {...form.register("resolution_hours")}
          className={inputClass}
        />
        {form.formState.errors.resolution_hours && (
          <p className="text-xs text-red-500 mt-1">
            {form.formState.errors.resolution_hours.message}
          </p>
        )}
      </div>
      {showActive && (
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="sla_is_active"
            {...form.register("is_active")}
            className="rounded"
          />
          <label htmlFor="sla_is_active" className="text-sm text-gray-700">
            SLA activo
          </label>
        </div>
      )}
    </>
  );
}

export default function AdminSLAsPage() {
  const qc = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [editSLA, setEditSLA] = useState<SLA | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<SLA | null>(null);

  const { data: slas = [], isLoading } = useQuery({
    queryKey: ["admin-slas"],
    queryFn: async () => {
      const res = await api.get<SLA[]>("/admin/slas");
      return res.data;
    },
  });

  const createMutation = useMutation({
    mutationFn: (d: SLAForm) =>
      api.post("/admin/slas", d).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-slas"] });
      setCreateOpen(false);
      createForm.reset();
    },
  });

  const editMutation = useMutation({
    mutationFn: ({ id, ...d }: SLAForm & { id: string }) =>
      api.patch(`/admin/slas/${id}`, d).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-slas"] });
      setEditSLA(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) =>
      api.delete(`/admin/slas/${id}`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-slas"] });
      setDeleteConfirm(null);
    },
  });

  const createForm = useForm<SLAForm>({
    resolver: zodResolver(slaSchema),
    defaultValues: { is_active: true },
  });
  const editForm = useForm<SLAForm>({ resolver: zodResolver(slaSchema) });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">SLAs</h1>
        <Dialog.Root open={createOpen} onOpenChange={setCreateOpen}>
          <Dialog.Trigger asChild>
            <button className="flex items-center gap-1.5 px-4 py-2 bg-[#1a2c4e] text-white rounded-lg text-sm font-medium hover:bg-[#243d6a] transition-colors">
              <Plus className="w-4 h-4" /> Nuevo SLA
            </button>
          </Dialog.Trigger>
          <Dialog.Portal>
            <Dialog.Overlay className="fixed inset-0 bg-black/40 z-50" />
            <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-xl shadow-xl p-6 w-full max-w-md z-50">
              <div className="flex items-center justify-between mb-5">
                <Dialog.Title className="font-semibold text-gray-900">
                  Nuevo SLA
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
                <SLAFormFields form={createForm} />
                {createMutation.isError && (
                  <p className="text-xs text-red-500">
                    Error al crear SLA. Intenta nuevamente.
                  </p>
                )}
                <div className="flex gap-2 pt-2">
                  <button
                    type="submit"
                    disabled={createMutation.isPending}
                    className="flex-1 py-2 bg-[#1a2c4e] text-white rounded-lg text-sm font-medium disabled:opacity-60"
                  >
                    {createMutation.isPending ? "Creando..." : "Crear SLA"}
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

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-6 space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-10 bg-gray-100 rounded animate-pulse" />
            ))}
          </div>
        ) : slas.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-8">
            No hay SLAs configurados.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-5 py-3 text-left font-medium text-gray-500">
                  Prioridad
                </th>
                <th className="px-5 py-3 text-right font-medium text-gray-500">
                  Respuesta
                </th>
                <th className="px-5 py-3 text-right font-medium text-gray-500">
                  Resolución
                </th>
                <th className="px-5 py-3 text-left font-medium text-gray-500">
                  Estado
                </th>
                <th className="px-5 py-3 text-right font-medium text-gray-500">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {slas.map((s) => {
                const prioCfg = s.priority
                  ? (PRIORITY_CONFIG[s.priority] ?? {
                      label: s.priority,
                      className: "bg-gray-100 text-gray-600",
                    })
                  : null;
                return (
                  <tr key={s.id} className="hover:bg-gray-50">
                    <td className="px-5 py-3">
                      {prioCfg ? (
                        <span
                          className={cn(
                            "px-2 py-0.5 rounded-full text-xs font-medium",
                            prioCfg.className
                          )}
                        >
                          {prioCfg.label}
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400">
                          Sin prioridad
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-right text-gray-600">
                      {s.response_hours}h
                    </td>
                    <td className="px-5 py-3 text-right text-gray-600">
                      {s.resolution_hours}h
                    </td>
                    <td className="px-5 py-3">
                      <span
                        className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                          s.is_active
                            ? "bg-green-100 text-green-700"
                            : "bg-gray-100 text-gray-500"
                        }`}
                      >
                        {s.is_active ? "Activo" : "Inactivo"}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-right space-x-2">
                      <button
                        onClick={() => {
                          setEditSLA(s);
                          editForm.reset({
                            priority: s.priority ?? "",
                            response_hours: s.response_hours,
                            resolution_hours: s.resolution_hours,
                            is_active: s.is_active,
                          });
                        }}
                        className="p-1 text-gray-400 hover:text-gray-700"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setDeleteConfirm(s)}
                        className="p-1 text-gray-400 hover:text-red-600"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Edit modal */}
      <Dialog.Root
        open={!!editSLA}
        onOpenChange={(o) => !o && setEditSLA(null)}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/40 z-50" />
          <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-xl shadow-xl p-6 w-full max-w-md z-50">
            <div className="flex items-center justify-between mb-5">
              <Dialog.Title className="font-semibold text-gray-900">
                Editar SLA
              </Dialog.Title>
              <Dialog.Close>
                <X className="w-4 h-4 text-gray-400" />
              </Dialog.Close>
            </div>
            <form
              onSubmit={editForm.handleSubmit((d) =>
                editMutation.mutate({ id: editSLA!.id, ...d })
              )}
              className="space-y-4"
            >
              <SLAFormFields form={editForm} showActive />
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

      {/* Delete confirm */}
      <Dialog.Root
        open={!!deleteConfirm}
        onOpenChange={(o) => !o && setDeleteConfirm(null)}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/40 z-50" />
          <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-xl shadow-xl p-6 w-full max-w-sm z-50">
            <Dialog.Title className="font-semibold text-gray-900 mb-2">
              Eliminar SLA
            </Dialog.Title>
            <p className="text-sm text-gray-600 mb-5">
              ¿Estás seguro de que deseas eliminar este SLA? Esta acción no se
              puede deshacer.
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => deleteMutation.mutate(deleteConfirm!.id)}
                disabled={deleteMutation.isPending}
                className="flex-1 py-2 bg-red-600 text-white rounded-lg text-sm font-medium disabled:opacity-60"
              >
                {deleteMutation.isPending ? "Eliminando..." : "Eliminar"}
              </button>
              <Dialog.Close asChild>
                <button className="flex-1 py-2 border border-gray-300 rounded-lg text-sm">
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
