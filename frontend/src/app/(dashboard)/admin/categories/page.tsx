"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm, type UseFormReturn } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import * as Dialog from "@radix-ui/react-dialog";
import { Plus, Edit2, X } from "lucide-react";
import api from "@/lib/api";
import type { Category } from "@/types/admin";

const categorySchema = z.object({
  name: z.string().min(1, "El nombre es requerido"),
  description: z.string().optional(),
  default_area_id: z.string().optional(),
  default_agent_id: z.string().optional(),
  requires_approval: z.boolean().default(false),
});

type CategoryForm = z.infer<typeof categorySchema>;

const inputClass =
  "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2c4e]";
const labelClass = "block text-sm font-medium text-gray-700 mb-1";

function CategoryFormFields({
  form,
}: {
  form: UseFormReturn<CategoryForm>;
}) {
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
        <label className={labelClass}>ID de área por defecto (opcional)</label>
        <input
          {...form.register("default_area_id")}
          className={inputClass}
          placeholder="UUID del área"
        />
      </div>
      <div>
        <label className={labelClass}>ID de agente por defecto (opcional)</label>
        <input
          {...form.register("default_agent_id")}
          className={inputClass}
          placeholder="UUID del agente"
        />
      </div>
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="requires_approval"
          {...form.register("requires_approval")}
          className="rounded"
        />
        <label htmlFor="requires_approval" className="text-sm text-gray-700">
          Requiere aprobación
        </label>
      </div>
    </>
  );
}

export default function AdminCategoriesPage() {
  const qc = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [editCategory, setEditCategory] = useState<Category | null>(null);

  const { data: categories = [], isLoading } = useQuery({
    queryKey: ["admin-categories"],
    queryFn: async () => {
      const res = await api.get<Category[]>("/admin/categories");
      return res.data;
    },
  });

  const createMutation = useMutation({
    mutationFn: (d: CategoryForm) =>
      api.post("/admin/categories", d).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-categories"] });
      setCreateOpen(false);
      createForm.reset();
    },
  });

  const editMutation = useMutation({
    mutationFn: ({ id, ...d }: CategoryForm & { id: string }) =>
      api.patch(`/admin/categories/${id}`, d).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-categories"] });
      setEditCategory(null);
    },
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      api.patch(`/admin/categories/${id}`, { is_active }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-categories"] });
    },
  });

  const createForm = useForm<CategoryForm>({
    resolver: zodResolver(categorySchema),
    defaultValues: { requires_approval: false },
  });
  const editForm = useForm<CategoryForm>({
    resolver: zodResolver(categorySchema),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Categorías</h1>
        <Dialog.Root open={createOpen} onOpenChange={setCreateOpen}>
          <Dialog.Trigger asChild>
            <button className="flex items-center gap-1.5 px-4 py-2 bg-[#1a2c4e] text-white rounded-lg text-sm font-medium hover:bg-[#243d6a] transition-colors">
              <Plus className="w-4 h-4" /> Nueva categoría
            </button>
          </Dialog.Trigger>
          <Dialog.Portal>
            <Dialog.Overlay className="fixed inset-0 bg-black/40 z-50" />
            <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-xl shadow-xl p-6 w-full max-w-md z-50">
              <div className="flex items-center justify-between mb-5">
                <Dialog.Title className="font-semibold text-gray-900">
                  Nueva categoría
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
                <CategoryFormFields form={createForm} />
                {createMutation.isError && (
                  <p className="text-xs text-red-500">
                    Error al crear categoría. Intenta nuevamente.
                  </p>
                )}
                <div className="flex gap-2 pt-2">
                  <button
                    type="submit"
                    disabled={createMutation.isPending}
                    className="flex-1 py-2 bg-[#1a2c4e] text-white rounded-lg text-sm font-medium disabled:opacity-60"
                  >
                    {createMutation.isPending ? "Creando..." : "Crear categoría"}
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
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-10 bg-gray-100 rounded animate-pulse" />
            ))}
          </div>
        ) : categories.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-8">
            No hay categorías creadas.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-5 py-3 text-left font-medium text-gray-500">
                  Nombre
                </th>
                <th className="px-5 py-3 text-left font-medium text-gray-500">
                  Aprobación
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
              {categories.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3">
                    <p className="font-medium text-gray-900">{c.name}</p>
                    {c.description && (
                      <p className="text-xs text-gray-400">{c.description}</p>
                    )}
                  </td>
                  <td className="px-5 py-3">
                    {c.requires_approval ? (
                      <span className="text-xs text-amber-600 font-medium">
                        Requiere aprobación
                      </span>
                    ) : (
                      <span className="text-xs text-gray-400">No</span>
                    )}
                  </td>
                  <td className="px-5 py-3">
                    <button
                      onClick={() =>
                        toggleMutation.mutate({
                          id: c.id,
                          is_active: !c.is_active,
                        })
                      }
                      disabled={toggleMutation.isPending}
                      className={`text-xs font-medium px-2 py-0.5 rounded-full transition-colors ${
                        c.is_active
                          ? "bg-green-100 text-green-700 hover:bg-green-200"
                          : "bg-gray-100 text-gray-500 hover:bg-gray-200"
                      }`}
                    >
                      {c.is_active ? "Activa" : "Inactiva"}
                    </button>
                  </td>
                  <td className="px-5 py-3 text-right">
                    <button
                      onClick={() => {
                        setEditCategory(c);
                        editForm.reset({
                          name: c.name,
                          description: c.description ?? "",
                          default_area_id: c.default_area_id ?? "",
                          default_agent_id: c.default_agent_id ?? "",
                          requires_approval: c.requires_approval,
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
        open={!!editCategory}
        onOpenChange={(o) => !o && setEditCategory(null)}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/40 z-50" />
          <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-xl shadow-xl p-6 w-full max-w-md z-50">
            <div className="flex items-center justify-between mb-5">
              <Dialog.Title className="font-semibold text-gray-900">
                Editar categoría
              </Dialog.Title>
              <Dialog.Close>
                <X className="w-4 h-4 text-gray-400" />
              </Dialog.Close>
            </div>
            <form
              onSubmit={editForm.handleSubmit((d) =>
                editMutation.mutate({ id: editCategory!.id, ...d })
              )}
              className="space-y-4"
            >
              <CategoryFormFields form={editForm} />
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
