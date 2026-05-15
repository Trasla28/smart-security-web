"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm, type UseFormReturn } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import * as Dialog from "@radix-ui/react-dialog";
import { Plus, Edit2, X, User, Calendar, Clock, Search } from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import api from "@/lib/api";
import type { RecurringTemplate } from "@/types/admin";

// ---------------------------------------------------------------------------
// Constantes de display
// ---------------------------------------------------------------------------

const PRIORITY_LABELS: Record<string, string> = {
  low: "Baja",
  medium: "Media",
  high: "Alta",
  urgent: "Urgente",
};

const PRIORITY_COLORS: Record<string, string> = {
  low: "bg-gray-100 text-gray-600",
  medium: "bg-blue-100 text-blue-700",
  high: "bg-orange-100 text-orange-700",
  urgent: "bg-red-100 text-red-700",
};

const WEEKDAY_LABELS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
const MONTH_LABELS = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

function recurrenceLabel(t: RecurringTemplate): string {
  if (t.recurrence_type === "daily") return "Diario";
  if (t.recurrence_type === "weekly") {
    const day = t.recurrence_day !== null ? WEEKDAY_LABELS[t.recurrence_day] : "—";
    return `Semanal · ${day}`;
  }
  if (t.recurrence_type === "day_of_month" || t.recurrence_type === "monthly") {
    return `Día ${t.recurrence_value ?? "?"} de cada mes`;
  }
  if (t.recurrence_type === "yearly") {
    const month = t.recurrence_month ? MONTH_LABELS[t.recurrence_month - 1] : "—";
    return `${t.recurrence_value ?? "?"} de ${month} (anual)`;
  }
  return t.recurrence_type;
}

// ---------------------------------------------------------------------------
// Schema del formulario
// ---------------------------------------------------------------------------

const templateSchema = z
  .object({
    title: z.string().min(1, "El título es requerido"),
    description: z.string().optional(),
    priority: z.enum(["low", "medium", "high", "urgent"]).default("medium"),
    assigned_to: z.string().min(1, "El responsable es requerido"),
    area_id: z.string().optional(),
    category_id: z.string().optional(),
    due_days: z.coerce.number().int().min(1).optional(),
    recurrence_type: z.enum(["day_of_month", "weekly", "yearly"]),
    // Día del mes (1-31) — para day_of_month y yearly
    recurrence_value: z.coerce.number().int().min(1).max(31).optional(),
    // Día de semana (0=Lunes … 6=Domingo) — para weekly
    recurrence_day: z.coerce.number().int().min(0).max(6).optional(),
    // Mes (1-12) — solo para yearly
    recurrence_month: z.coerce.number().int().min(1).max(12).optional(),
    if_holiday_action: z
      .enum(["previous_business_day", "next_business_day", "same_day"])
      .default("previous_business_day"),
  })
  .superRefine((val, ctx) => {
    if (val.recurrence_type === "day_of_month" && !val.recurrence_value) {
      ctx.addIssue({ code: "custom", path: ["recurrence_value"], message: "Indica el día del mes" });
    }
    if (val.recurrence_type === "weekly" && val.recurrence_day === undefined) {
      ctx.addIssue({ code: "custom", path: ["recurrence_day"], message: "Selecciona el día de la semana" });
    }
    if (val.recurrence_type === "yearly") {
      if (!val.recurrence_value)
        ctx.addIssue({ code: "custom", path: ["recurrence_value"], message: "Indica el día del mes" });
      if (!val.recurrence_month)
        ctx.addIssue({ code: "custom", path: ["recurrence_month"], message: "Selecciona el mes" });
    }
  });

type TemplateForm = z.infer<typeof templateSchema>;

// ---------------------------------------------------------------------------
// Estilos compartidos
// ---------------------------------------------------------------------------

const inputClass =
  "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2c4e]";
const labelClass = "block text-sm font-medium text-gray-700 mb-1";

// ---------------------------------------------------------------------------
// Campos del formulario
// ---------------------------------------------------------------------------

function TemplateFormFields({
  form,
  agents,
  areas,
  categories,
}: {
  form: UseFormReturn<TemplateForm>;
  agents: { id: string; full_name: string; role: string }[];
  areas: { id: string; name: string }[];
  categories: { id: string; name: string }[];
}) {
  const recurrenceType = form.watch("recurrence_type");

  return (
    <div className="space-y-4">
      {/* Título */}
      <div>
        <label className={labelClass}>Título *</label>
        <input {...form.register("title")} className={inputClass} placeholder="Ej: Informe Mensual Proveedores" />
        {form.formState.errors.title && (
          <p className="text-xs text-red-500 mt-1">{form.formState.errors.title.message}</p>
        )}
      </div>

      {/* Descripción */}
      <div>
        <label className={labelClass}>Descripción</label>
        <textarea {...form.register("description")} className={inputClass} rows={2}
          placeholder="Instrucciones o contexto del ticket recurrente" />
      </div>

      {/* Responsable */}
      <div>
        <label className={labelClass}>Responsable *</label>
        <select {...form.register("assigned_to")} className={inputClass}>
          <option value="">Seleccionar responsable...</option>
          {agents.map((u) => (
            <option key={u.id} value={u.id}>{u.full_name}</option>
          ))}
        </select>
        {form.formState.errors.assigned_to && (
          <p className="text-xs text-red-500 mt-1">{form.formState.errors.assigned_to.message}</p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3">
        {/* Área */}
        <div>
          <label className={labelClass}>Área</label>
          <select {...form.register("area_id")} className={inputClass}>
            <option value="">Sin área</option>
            {areas.map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
        </div>

        {/* Categoría */}
        <div>
          <label className={labelClass}>Categoría</label>
          <select {...form.register("category_id")} className={inputClass}>
            <option value="">Sin categoría</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {/* Prioridad */}
        <div>
          <label className={labelClass}>Prioridad</label>
          <select {...form.register("priority")} className={inputClass}>
            <option value="low">Baja</option>
            <option value="medium">Media</option>
            <option value="high">Alta</option>
            <option value="urgent">Urgente</option>
          </select>
        </div>

        {/* Días para completar */}
        <div>
          <label className={labelClass}>Días para completar</label>
          <input
            type="number"
            min="1"
            {...form.register("due_days")}
            className={inputClass}
            placeholder="Ej: 3"
          />
          <p className="text-xs text-gray-400 mt-0.5">Días desde la creación hasta el vencimiento</p>
        </div>
      </div>

      {/* Separador recurrencia */}
      <div className="border-t border-gray-100 pt-3">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Frecuencia</p>

        {/* Tipo */}
        <div className="mb-3">
          <label className={labelClass}>Tipo de recurrencia *</label>
          <select {...form.register("recurrence_type")} className={inputClass}>
            <option value="day_of_month">Día del mes</option>
            <option value="weekly">Día de la semana</option>
            <option value="yearly">Fecha específica del año</option>
          </select>
        </div>

        {/* Campos condicionales según tipo */}
        {recurrenceType === "day_of_month" && (
          <div>
            <label className={labelClass}>¿Qué día del mes? *</label>
            <input
              type="number"
              min="1"
              max="31"
              {...form.register("recurrence_value")}
              className={inputClass}
              placeholder="Ej: 3  (día 3 de cada mes)"
            />
            {form.formState.errors.recurrence_value && (
              <p className="text-xs text-red-500 mt-1">{form.formState.errors.recurrence_value.message}</p>
            )}
          </div>
        )}

        {recurrenceType === "weekly" && (
          <div>
            <label className={labelClass}>¿Qué día de la semana? *</label>
            <select {...form.register("recurrence_day")} className={inputClass}>
              <option value="">Seleccionar día...</option>
              {WEEKDAY_LABELS.map((d, i) => (
                <option key={i} value={i}>{d}</option>
              ))}
            </select>
            {form.formState.errors.recurrence_day && (
              <p className="text-xs text-red-500 mt-1">{form.formState.errors.recurrence_day.message}</p>
            )}
          </div>
        )}

        {recurrenceType === "yearly" && (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Mes *</label>
              <select {...form.register("recurrence_month")} className={inputClass}>
                <option value="">Seleccionar mes...</option>
                {MONTH_LABELS.map((m, i) => (
                  <option key={i + 1} value={i + 1}>{m}</option>
                ))}
              </select>
              {form.formState.errors.recurrence_month && (
                <p className="text-xs text-red-500 mt-1">{form.formState.errors.recurrence_month.message}</p>
              )}
            </div>
            <div>
              <label className={labelClass}>Día *</label>
              <input
                type="number"
                min="1"
                max="31"
                {...form.register("recurrence_value")}
                className={inputClass}
                placeholder="Ej: 15"
              />
              {form.formState.errors.recurrence_value && (
                <p className="text-xs text-red-500 mt-1">{form.formState.errors.recurrence_value.message}</p>
              )}
            </div>
          </div>
        )}

        {/* Acción en festivo */}
        <div className="mt-3">
          <label className={labelClass}>Si cae en festivo o fin de semana</label>
          <select {...form.register("if_holiday_action")} className={inputClass}>
            <option value="previous_business_day">Crear el día hábil anterior</option>
            <option value="next_business_day">Crear el siguiente día hábil</option>
            <option value="same_day">Crear igual (aunque sea festivo)</option>
          </select>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Página principal
// ---------------------------------------------------------------------------

export default function AdminRecurringPage() {
  const qc = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [editTemplate, setEditTemplate] = useState<RecurringTemplate | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "inactive">("all");

  const { data: templates = [], isLoading } = useQuery({
    queryKey: ["admin-recurring"],
    queryFn: async () => {
      const res = await api.get<RecurringTemplate[]>("/admin/recurring");
      return res.data;
    },
  });

  const { data: agents = [] } = useQuery({
    queryKey: ["users-agents"],
    queryFn: async () => {
      const res = await api.get<{ items: { id: string; full_name: string; role: string }[] }>(
        "/users", { params: { size: 200 } }
      );
      return (res.data.items ?? []).filter((u) =>
        ["admin", "supervisor", "agent"].includes(u.role)
      );
    },
  });

  const { data: areas = [] } = useQuery({
    queryKey: ["areas-list"],
    queryFn: async () => {
      const res = await api.get<{ id: string; name: string }[]>("/areas");
      return res.data;
    },
  });

  const { data: categories = [] } = useQuery({
    queryKey: ["categories-list"],
    queryFn: async () => {
      const res = await api.get<{ id: string; name: string; is_active: boolean }[]>("/admin/categories");
      return res.data.filter((c) => c.is_active);
    },
  });

  function buildPayload(d: TemplateForm) {
    return {
      title: d.title,
      description: d.description || null,
      priority: d.priority,
      assigned_to: d.assigned_to || null,
      area_id: d.area_id || null,
      category_id: d.category_id || null,
      due_days: d.due_days ?? null,
      recurrence_type: d.recurrence_type,
      recurrence_value: d.recurrence_value ?? null,
      recurrence_day: d.recurrence_day !== undefined ? Number(d.recurrence_day) : null,
      recurrence_month: d.recurrence_month ?? null,
      if_holiday_action: d.if_holiday_action,
    };
  }

  const createMutation = useMutation({
    mutationFn: (d: TemplateForm) => api.post("/admin/recurring", buildPayload(d)).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-recurring"] });
      setCreateOpen(false);
      createForm.reset();
    },
  });

  const editMutation = useMutation({
    mutationFn: ({ id, ...d }: TemplateForm & { id: string }) =>
      api.patch(`/admin/recurring/${id}`, buildPayload(d)).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-recurring"] });
      setEditTemplate(null);
    },
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      api.patch(`/admin/recurring/${id}`, { is_active }).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-recurring"] }),
  });

  const createForm = useForm<TemplateForm>({
    resolver: zodResolver(templateSchema),
    defaultValues: { priority: "medium", recurrence_type: "day_of_month", if_holiday_action: "previous_business_day" },
  });

  const editForm = useForm<TemplateForm>({ resolver: zodResolver(templateSchema) });

  function openEdit(t: RecurringTemplate) {
    setEditTemplate(t);
    editForm.reset({
      title: t.title,
      description: t.description ?? "",
      priority: t.priority as TemplateForm["priority"],
      assigned_to: t.assigned_to ?? "",
      area_id: t.area_id ?? "",
      category_id: t.category_id ?? "",
      due_days: t.due_days ?? undefined,
      recurrence_type: (t.recurrence_type === "monthly" ? "day_of_month" : t.recurrence_type) as TemplateForm["recurrence_type"],
      recurrence_value: t.recurrence_value ?? undefined,
      recurrence_day: t.recurrence_day ?? undefined,
      recurrence_month: t.recurrence_month ?? undefined,
      if_holiday_action: t.if_holiday_action as TemplateForm["if_holiday_action"],
    });
  }

  const formProps = { agents, areas, categories };

  const q = search.toLowerCase();
  const filtered = templates.filter((t) => {
    const matchesSearch =
      q === "" ||
      t.title.toLowerCase().includes(q) ||
      (t.assignee?.full_name ?? "").toLowerCase().includes(q);
    const matchesStatus =
      statusFilter === "all" ||
      (statusFilter === "active" && t.is_active) ||
      (statusFilter === "inactive" && !t.is_active);
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Plantillas recurrentes</h1>
          <p className="text-sm text-gray-500 mt-0.5">Tickets que se crean automáticamente según un calendario definido</p>
        </div>
        <Dialog.Root open={createOpen} onOpenChange={setCreateOpen}>
          <Dialog.Trigger asChild>
            <button className="flex items-center gap-1.5 px-4 py-2 bg-[#1a2c4e] text-white rounded-lg text-sm font-medium hover:bg-[#243d6a] transition-colors">
              <Plus className="w-4 h-4" /> Nueva plantilla
            </button>
          </Dialog.Trigger>
          <Dialog.Portal>
            <Dialog.Overlay className="fixed inset-0 bg-black/40 z-50" />
            <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-xl shadow-xl p-6 w-full max-w-lg z-50 max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between mb-5">
                <Dialog.Title className="font-semibold text-gray-900">Nueva plantilla recurrente</Dialog.Title>
                <Dialog.Close><X className="w-4 h-4 text-gray-400" /></Dialog.Close>
              </div>
              <form onSubmit={createForm.handleSubmit((d) => createMutation.mutate(d))} className="space-y-4">
                <TemplateFormFields form={createForm} {...formProps} />
                {createMutation.isError && (
                  <p className="text-xs text-red-500">Error al crear la plantilla. Intenta nuevamente.</p>
                )}
                <div className="flex gap-2 pt-2">
                  <button type="submit" disabled={createMutation.isPending}
                    className="flex-1 py-2 bg-[#1a2c4e] text-white rounded-lg text-sm font-medium disabled:opacity-60">
                    {createMutation.isPending ? "Creando..." : "Crear plantilla"}
                  </button>
                  <Dialog.Close asChild>
                    <button type="button" className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Cancelar</button>
                  </Dialog.Close>
                </div>
              </form>
            </Dialog.Content>
          </Dialog.Portal>
        </Dialog.Root>
      </div>

      {/* Filtros */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
          <input
            type="text"
            placeholder="Buscar por título o responsable..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2c4e]"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as typeof statusFilter)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2c4e] bg-white"
        >
          <option value="all">Todas</option>
          <option value="active">Activas</option>
          <option value="inactive">Inactivas</option>
        </select>
        {(search || statusFilter !== "all") && (
          <span className="text-xs text-gray-500">
            {filtered.length} de {templates.length} plantilla{templates.length !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-6 space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-10 bg-gray-100 rounded animate-pulse" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-10">
            {templates.length === 0
              ? "No hay plantillas recurrentes."
              : "Ninguna plantilla coincide con los filtros."}
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-5 py-3 text-left font-medium text-gray-500">Plantilla</th>
                <th className="px-5 py-3 text-left font-medium text-gray-500">Frecuencia</th>
                <th className="px-5 py-3 text-left font-medium text-gray-500">Responsable</th>
                <th className="px-5 py-3 text-left font-medium text-gray-500">Vence en</th>
                <th className="px-5 py-3 text-left font-medium text-gray-500">Próxima creación</th>
                <th className="px-5 py-3 text-left font-medium text-gray-500">Estado</th>
                <th className="px-5 py-3 text-right font-medium text-gray-500">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map((t) => (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3">
                    <p className="font-medium text-gray-900">{t.title}</p>
                    <span className={`inline-block mt-0.5 text-xs font-medium px-1.5 py-0.5 rounded-full ${PRIORITY_COLORS[t.priority] ?? "bg-gray-100 text-gray-600"}`}>
                      {PRIORITY_LABELS[t.priority] ?? t.priority}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-gray-600 text-xs">{recurrenceLabel(t)}</td>
                  <td className="px-5 py-3">
                    {t.assignee ? (
                      <div className="flex items-center gap-1.5">
                        <div className="w-6 h-6 rounded-full bg-[#1a2c4e] flex items-center justify-center text-xs font-semibold text-white shrink-0">
                          {t.assignee.full_name.charAt(0).toUpperCase()}
                        </div>
                        <span className="text-gray-700 text-xs">{t.assignee.full_name}</span>
                      </div>
                    ) : (
                      <span className="text-gray-400 text-xs flex items-center gap-1">
                        <User className="w-3.5 h-3.5" /> Sin asignar
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-3 text-xs text-gray-500">
                    {t.due_days ? (
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5 text-gray-400" />
                        {t.due_days} día{t.due_days !== 1 ? "s" : ""}
                      </span>
                    ) : (
                      <span className="text-gray-300">—</span>
                    )}
                  </td>
                  <td className="px-5 py-3 text-xs text-gray-400">
                    {t.next_run_at ? (
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5" />
                        {format(new Date(t.next_run_at), "d MMM yyyy", { locale: es })}
                      </span>
                    ) : "—"}
                  </td>
                  <td className="px-5 py-3">
                    <button
                      onClick={() => toggleMutation.mutate({ id: t.id, is_active: !t.is_active })}
                      disabled={toggleMutation.isPending}
                      className={`text-xs font-medium px-2 py-0.5 rounded-full transition-colors ${
                        t.is_active ? "bg-green-100 text-green-700 hover:bg-green-200" : "bg-gray-100 text-gray-500 hover:bg-gray-200"
                      }`}
                    >
                      {t.is_active ? "Activa" : "Inactiva"}
                    </button>
                  </td>
                  <td className="px-5 py-3 text-right">
                    <button onClick={() => openEdit(t)} className="p-1 text-gray-400 hover:text-gray-700">
                      <Edit2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Modal de edición */}
      <Dialog.Root open={!!editTemplate} onOpenChange={(o) => !o && setEditTemplate(null)}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/40 z-50" />
          <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-xl shadow-xl p-6 w-full max-w-lg z-50 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-5">
              <Dialog.Title className="font-semibold text-gray-900">Editar plantilla</Dialog.Title>
              <Dialog.Close><X className="w-4 h-4 text-gray-400" /></Dialog.Close>
            </div>
            <form
              onSubmit={editForm.handleSubmit((d) => editMutation.mutate({ id: editTemplate!.id, ...d }))}
              className="space-y-4"
            >
              <TemplateFormFields form={editForm} {...formProps} />
              {editMutation.isError && (
                <p className="text-xs text-red-500">Error al guardar cambios. Intenta nuevamente.</p>
              )}
              <div className="flex gap-2 pt-2">
                <button type="submit" disabled={editMutation.isPending}
                  className="flex-1 py-2 bg-[#1a2c4e] text-white rounded-lg text-sm font-medium disabled:opacity-60">
                  {editMutation.isPending ? "Guardando..." : "Guardar cambios"}
                </button>
                <Dialog.Close asChild>
                  <button type="button" className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Cancelar</button>
                </Dialog.Close>
              </div>
            </form>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
