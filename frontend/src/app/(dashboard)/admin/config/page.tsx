"use client";

import { useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Save } from "lucide-react";
import api from "@/lib/api";
import type { TenantConfig } from "@/types/admin";

const DAY_LABELS = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];
const WEEK_DAY_OPTIONS = [
  { value: 1, label: "Lunes" },
  { value: 2, label: "Martes" },
  { value: 3, label: "Miércoles" },
  { value: 4, label: "Jueves" },
  { value: 5, label: "Viernes" },
  { value: 6, label: "Sábado" },
  { value: 7, label: "Domingo" },
];

const configSchema = z.object({
  primary_color: z.string().regex(/^#[0-9a-fA-F]{6}$/, "Color inválido"),
  auto_close_days: z.coerce.number().int().positive(),
  urgency_abuse_threshold: z.coerce.number().min(0).max(100),
  timezone: z.string().min(1),
  working_hours_start: z.string(),
  working_hours_end: z.string(),
  working_days: z.array(z.number()),
  weekly_report_enabled: z.boolean(),
  weekly_report_day: z.coerce.number().int().min(1).max(7),
});

type ConfigForm = z.infer<typeof configSchema>;

const inputClass =
  "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2c4e]";
const labelClass = "block text-sm font-medium text-gray-700 mb-1";

export default function AdminConfigPage() {
  const qc = useQueryClient();

  const { data: config, isLoading } = useQuery({
    queryKey: ["admin-config"],
    queryFn: async () => {
      const res = await api.get<TenantConfig>("/admin/config");
      return res.data;
    },
  });

  const saveMutation = useMutation({
    mutationFn: (d: ConfigForm) =>
      api.patch("/admin/config", d).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-config"] });
    },
  });

  const {
    register,
    handleSubmit,
    control,
    reset,
    watch,
    setValue,
    formState: { errors, isDirty },
  } = useForm<ConfigForm>({
    resolver: zodResolver(configSchema),
  });

  useEffect(() => {
    if (config) {
      reset({
        primary_color: config.primary_color,
        auto_close_days: config.auto_close_days,
        urgency_abuse_threshold: config.urgency_abuse_threshold,
        timezone: config.timezone,
        working_hours_start: config.working_hours_start,
        working_hours_end: config.working_hours_end,
        working_days: config.working_days,
        weekly_report_enabled: config.weekly_report_enabled,
        weekly_report_day: config.weekly_report_day,
      });
    }
  }, [config, reset]);

  const workingDays = watch("working_days") ?? [];
  const weeklyEnabled = watch("weekly_report_enabled");

  function toggleDay(day: number) {
    if (workingDays.includes(day)) {
      setValue(
        "working_days",
        workingDays.filter((d) => d !== day),
        { shouldDirty: true }
      );
    } else {
      setValue("working_days", [...workingDays, day].sort(), {
        shouldDirty: true,
      });
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-14 bg-gray-100 rounded-xl animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">
          Configuración del tenant
        </h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Ajusta las preferencias globales del sistema.
        </p>
      </div>

      <form onSubmit={handleSubmit((d) => saveMutation.mutate(d))}>
        <div className="space-y-6">
          {/* Appearance */}
          <section className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
            <h2 className="text-sm font-semibold text-gray-700 border-b border-gray-100 pb-2">
              Apariencia
            </h2>
            <div>
              <label className={labelClass}>Color principal</label>
              <div className="flex items-center gap-3">
                <Controller
                  control={control}
                  name="primary_color"
                  render={({ field }) => (
                    <input
                      type="color"
                      {...field}
                      className="w-10 h-10 rounded border border-gray-300 cursor-pointer p-0.5"
                    />
                  )}
                />
                <input
                  {...register("primary_color")}
                  className={inputClass}
                  placeholder="#1a2c4e"
                />
              </div>
              {errors.primary_color && (
                <p className="text-xs text-red-500 mt-1">
                  {errors.primary_color.message}
                </p>
              )}
            </div>
          </section>

          {/* Tickets */}
          <section className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
            <h2 className="text-sm font-semibold text-gray-700 border-b border-gray-100 pb-2">
              Tickets
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className={labelClass}>
                  Cierre automático (días de inactividad)
                </label>
                <input
                  type="number"
                  min="1"
                  {...register("auto_close_days")}
                  className={inputClass}
                />
                {errors.auto_close_days && (
                  <p className="text-xs text-red-500 mt-1">
                    {errors.auto_close_days.message}
                  </p>
                )}
              </div>
              <div>
                <label className={labelClass}>
                  Umbral de abuso de urgencia (%)
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  {...register("urgency_abuse_threshold")}
                  className={inputClass}
                />
                {errors.urgency_abuse_threshold && (
                  <p className="text-xs text-red-500 mt-1">
                    {errors.urgency_abuse_threshold.message}
                  </p>
                )}
              </div>
            </div>
          </section>

          {/* Schedule */}
          <section className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
            <h2 className="text-sm font-semibold text-gray-700 border-b border-gray-100 pb-2">
              Horario laboral
            </h2>
            <div>
              <label className={labelClass}>Zona horaria</label>
              <input {...register("timezone")} className={inputClass} />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className={labelClass}>Hora de inicio</label>
                <input
                  type="time"
                  {...register("working_hours_start")}
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>Hora de fin</label>
                <input
                  type="time"
                  {...register("working_hours_end")}
                  className={inputClass}
                />
              </div>
            </div>
            <div>
              <label className={labelClass}>Días laborales</label>
              <div className="flex gap-2 flex-wrap">
                {DAY_LABELS.map((label, index) => (
                  <button
                    key={index}
                    type="button"
                    onClick={() => toggleDay(index)}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                      workingDays.includes(index)
                        ? "bg-[#1a2c4e] text-white border-[#1a2c4e]"
                        : "bg-white text-gray-600 border-gray-300 hover:border-gray-400"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          </section>

          {/* Weekly report */}
          <section className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
            <h2 className="text-sm font-semibold text-gray-700 border-b border-gray-100 pb-2">
              Reporte semanal
            </h2>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="weekly_report_enabled"
                {...register("weekly_report_enabled")}
                className="rounded"
              />
              <label
                htmlFor="weekly_report_enabled"
                className="text-sm text-gray-700"
              >
                Activar reporte semanal automático
              </label>
            </div>
            {weeklyEnabled && (
              <div>
                <label className={labelClass}>Día de envío</label>
                <select
                  {...register("weekly_report_day")}
                  className={inputClass}
                >
                  {WEEK_DAY_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </section>

          {/* Save */}
          <div className="flex items-center justify-between">
            {saveMutation.isSuccess && (
              <p className="text-sm text-green-600 font-medium">
                Configuración guardada correctamente.
              </p>
            )}
            {saveMutation.isError && (
              <p className="text-sm text-red-500">
                Error al guardar. Intenta nuevamente.
              </p>
            )}
            <div className="ml-auto">
              <button
                type="submit"
                disabled={saveMutation.isPending || !isDirty}
                className="flex items-center gap-2 px-5 py-2.5 bg-[#1a2c4e] text-white rounded-lg text-sm font-medium hover:bg-[#243d6a] transition-colors disabled:opacity-60"
              >
                <Save className="w-4 h-4" />
                {saveMutation.isPending ? "Guardando..." : "Guardar cambios"}
              </button>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
}
