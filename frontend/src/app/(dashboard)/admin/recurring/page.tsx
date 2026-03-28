"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm, type UseFormReturn } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import * as Dialog from "@radix-ui/react-dialog";
import { Plus, Edit2, X } from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import api from "@/lib/api";
import type { RecurringTemplate } from "@/types/admin";

const PRIORITY_LABELS: Record<string, string> = {
  low: "Baja",
  medium: "Media",
  high: "Alta",
  urgent: "Urgente",
};

const RECURRENCE_LABELS: Record<string, string> = {
  daily: "Diario",
  weekly: "Semanal",
  monthly: "Mensual",
  day_of_month: "Día del mes",
};

const templateSchema = z.object({
  title: z.string().min(1, "El título es requerido"),
  description: z.string().optional(),
  priority: z.enum(["low", "medium", "high", "urgent"]).default("medium"),
  recurrence_type: z.enum(["daily", "weekly", "monthly", "day_of_month"]),
  recurrence_value: z.coerce.number().optional(),
  if_holiday_action: z
    .enum(["skip", "next_business_day", "prev_business_day"])
    .default("skip"),
});

type TemplateForm = z.infer<typeof templateSchema>;

const inputClass =
  "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2c4e]";
const labelClass = "block text-sm font-medium text-gray-700 mb-1";

function TemplateFormFields({
  form,
}: {
  form: UseFormReturn<TemplateForm>;
}) {
  return (
    <>
      <div>
        <label className={labelClass}>Título</label>
        <input {...form.register("title")} className={inputClass} />
        {form.formState.errors.title && (
          <p className="text-xs text-red-500 mt-1">
            {form.formState.errors.title.message}
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
        <label className={labelClass}>Prioridad</label>
        <select {...form.register("priority")} className={inputClass}>
          <option value="low">Baja</option>
          <option value="medium">Media</option>
          <option value="high">Alta</option>
          <option value="urgent">Urgente</option>
        </select>
      </div>
      <div>
        <label className={labelClass}>Tipo de recurrencia</label>
        <select {...form.register("recurrence_type")} className={inputClass}>
          <option value="daily">Diario</option>
          <option value="weekly">Semanal</option>
          <option value="monthly">Mensual</option>
          <option value="day_of_month">Día del mes</option>
        </select>
      </div>
      <div>
        <label className={labelClass}>
          Valor de recurrencia (opcional — ej. cada N días)
        </label>
        <input
          type="number"
          min="1"
          {...form.register("recurrence_value")}
          className={inputClass}
        />
      </div>
      <div>
        <label className={labelClass}>Si es festivo</label>
        <select {...form.register("if_holiday_action")} className={inputClass}>
          <option value="skip">Omitir</option>
          <option value="next_business_day">Siguiente día hábil</option>
          <option value="prev_business_day">Día hábil anterior</option>
        </select>
      </div>
    </>
  );
}

export default function AdminRecurringPage() {
  const qc = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [editTemplate, setEditTemplate] = useState<RecurringTemplate | null>(
    null
  );

  const { data: templates = [], isLoading } = useQuery({
    queryKey: ["admin-recurring"],
    queryFn: async () => {
      const res = await api.get<RecurringTemplate[]>("/admin/recurring");
      return res.data;
    },
  });

  const createMutation = useMutation({
    mutationFn: (d: TemplateForm) =>
      api.post("/admin/recurring", d).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-recurring"] });
      setCreateOpen(false);
      createForm.reset();
    },
  });

  const editMutation = useMutation({
    mutationFn: ({ id, ...d }: TemplateForm & { id: string }) =>
      api.patch(`/admin/recurring/${id}`, d).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-recurring"] });
      setEditTemplate(null);
    },
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      api.patch(`/admin/recurring/${id}`, { is_active }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-recurring"] });
    },
  });

  const createForm = useForm<TemplateForm>({
    resolver: zodResolver(templateSchema),
    defaultValues: {
      priority: "medium",
      recurrence_type: "daily",
      if_holiday_action: "skip",
    },
  });
  const editForm = useForm<TemplateForm>({ resolver: zodResolver(templateSchema) });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">
          Plantillas recurrentes
        </h1>
        <Dialog.Root open={createOpen} onOpenChange={setCreateOpen}>
          <Dialog.Trigger asChild>
            <button className="flex items-center gap-1.5 px-4 py-2 bg-[#1a2c4e] text-white rounded-lg text-sm font-medium hover:bg-[#243d6a] transition-colors">
              <Plus className="w-4 h-4" /> Nueva plantilla
            </button>
          </Dialog.Trigger>
          <Dialog.Portal>
            <Dialog.Overlay className="fixed inset-0 bg-black/40 z-50" />
            <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-xl shadow-xl p-6 w-full max-w-md z-50 max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between mb-5">
                <Dialog.Title className="font-semibold text-gray-900">
                  Nueva plantilla
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
                <TemplateFormFields form={createForm} />
                {createMutation.isError && (
                  <p className="text-xs text-red-500">
                    Error al crear plantilla. Intenta nuevamente.
                  </p>
                )}
                <div className="flex gap-2 pt-2">
                  <button
                    type="submit"
                    disabled={createMutation.isPending}
                    className="flex-1 py-2 bg-[#1a2c4e] text-white rounded-lg text-sm font-medium disabled:opacity-60"
                  >
                    {createMutation.isPending ? "Creando..." : "Crear plantilla"}
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
        ) : templates.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-8">
            No hay plantillas recurrentes.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-5 py-3 text-left font-medium text-gray-500">
                  Título
                </th>
                <th className="px-5 py-3 text-left font-medium text-gray-500">
                  Recurrencia
                </th>
                <th className="px-5 py-3 text-left font-medium text-gray-500">
                  Prioridad
                </th>
                <th className="px-5 py-3 text-left font-medium text-gray-500">
                  Próxima ejecución
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
              {templates.map((t) => (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-medium text-gray-900">
                    {t.title}
                  </td>
                  <td className="px-5 py-3 text-gray-600">
                    {RECURRENCE_LABELS[t.recurrence_type] ?? t.recurrence_type}
                    {t.recurrence_value ? ` (c/${t.recurrence_value})` : ""}
                  </td>
                  <td className="px-5 py-3 text-gray-600">
                    {PRIORITY_LABELS[t.priority] ?? t.priority}
                  </td>
                  <td className="px-5 py-3 text-xs text-gray-400">
                    {t.next_run_at
                      ? format(new Date(t.next_run_at), "d MMM yyyy HH:mm", {
                          locale: es,
                        })
                      : "—"}
                  </td>
                  <td className="px-5 py-3">
                    <button
                      onClick={() =>
                        toggleMutation.mutate({
                          id: t.id,
                          is_active: !t.is_active,
                        })
                      }
                      disabled={toggleMutation.isPending}
                      className={`text-xs font-medium px-2 py-0.5 rounded-full transition-colors ${
                        t.is_active
                          ? "bg-green-100 text-green-700 hover:bg-green-200"
                          : "bg-gray-100 text-gray-500 hover:bg-gray-200"
                      }`}
                    >
                      {t.is_active ? "Activa" : "Inactiva"}
                    </button>
                  </td>
                  <td className="px-5 py-3 text-right">
                    <button
                      onClick={() => {
                        setEditTemplate(t);
                        editForm.reset({
                          title: t.title,
                          description: t.description ?? "",
                          priority: t.priority as TemplateForm["priority"],
                          recurrence_type:
                            t.recurrence_type as TemplateForm["recurrence_type"],
                          recurrence_value: t.recurrence_value ?? undefined,
                          if_holiday_action:
                            t.if_holiday_action as TemplateForm["if_holiday_action"],
                        });
                      }}
                      className="p-1 text-gray-400 hover:text-gray-700"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Edit modal */}
      <Dialog.Root
        open={!!editTemplate}
        onOpenChange={(o) => !o && setEditTemplate(null)}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/40 z-50" />
          <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-xl shadow-xl p-6 w-full max-w-md z-50 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-5">
              <Dialog.Title className="font-semibold text-gray-900">
                Editar plantilla
              </Dialog.Title>
              <Dialog.Close>
                <X className="w-4 h-4 text-gray-400" />
              </Dialog.Close>
            </div>
            <form
              onSubmit={editForm.handleSubmit((d) =>
                editMutation.mutate({ id: editTemplate!.id, ...d })
              )}
              className="space-y-4"
            >
              <TemplateFormFields form={editForm} />
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
