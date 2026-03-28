"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import * as Dialog from "@radix-ui/react-dialog";
import { Plus, Edit2, Archive, X } from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import api from "@/lib/api";
import { cn } from "@/lib/utils";
import type { AdminUser } from "@/types/admin";
import type { PaginatedResponse } from "@/types/api";

const ROLE_CONFIG: Record<string, { label: string; className: string }> = {
  admin: { label: "Admin", className: "bg-purple-100 text-purple-700" },
  supervisor: { label: "Supervisor", className: "bg-blue-100 text-blue-700" },
  agent: { label: "Agente", className: "bg-teal-100 text-teal-700" },
  requester: { label: "Solicitante", className: "bg-gray-100 text-gray-600" },
};

const createSchema = z.object({
  full_name: z.string().min(2),
  email: z.string().email(),
  role: z.enum(["admin", "supervisor", "agent", "requester"]),
  password: z.string().min(8).optional(),
});

const editSchema = z.object({
  full_name: z.string().min(2).optional(),
  role: z.enum(["admin", "supervisor", "agent", "requester"]).optional(),
  is_active: z.boolean().optional(),
});

type CreateForm = z.infer<typeof createSchema>;
type EditForm = z.infer<typeof editSchema>;

const inputClass =
  "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2c4e]";
const labelClass = "block text-sm font-medium text-gray-700 mb-1";

export default function AdminUsersPage() {
  const qc = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [editUser, setEditUser] = useState<AdminUser | null>(null);
  const [archiveConfirm, setArchiveConfirm] = useState<AdminUser | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-users"],
    queryFn: async () => {
      const res = await api.get<PaginatedResponse<AdminUser>>("/users?size=100");
      return res.data.items;
    },
  });

  const createMutation = useMutation({
    mutationFn: (d: CreateForm) => api.post("/users", d).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      setModalOpen(false);
      createForm.reset();
    },
  });

  const editMutation = useMutation({
    mutationFn: ({ id, ...d }: EditForm & { id: string }) =>
      api.patch(`/users/${id}`, d).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      setEditUser(null);
    },
  });

  const archiveMutation = useMutation({
    mutationFn: (id: string) =>
      api.post(`/users/${id}/archive`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      setArchiveConfirm(null);
    },
  });

  const createForm = useForm<CreateForm>({ resolver: zodResolver(createSchema) });
  const editForm = useForm<EditForm>({ resolver: zodResolver(editSchema) });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Usuarios</h1>
        <Dialog.Root open={modalOpen} onOpenChange={setModalOpen}>
          <Dialog.Trigger asChild>
            <button className="flex items-center gap-1.5 px-4 py-2 bg-[#1a2c4e] text-white rounded-lg text-sm font-medium hover:bg-[#243d6a] transition-colors">
              <Plus className="w-4 h-4" /> Nuevo usuario
            </button>
          </Dialog.Trigger>
          <Dialog.Portal>
            <Dialog.Overlay className="fixed inset-0 bg-black/40 z-50" />
            <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-xl shadow-xl p-6 w-full max-w-md z-50">
              <div className="flex items-center justify-between mb-5">
                <Dialog.Title className="font-semibold text-gray-900">
                  Nuevo usuario
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
                <div>
                  <label className={labelClass}>Nombre completo</label>
                  <input
                    {...createForm.register("full_name")}
                    className={inputClass}
                  />
                  {createForm.formState.errors.full_name && (
                    <p className="text-xs text-red-500 mt-1">
                      {createForm.formState.errors.full_name.message}
                    </p>
                  )}
                </div>
                <div>
                  <label className={labelClass}>Email</label>
                  <input
                    type="email"
                    {...createForm.register("email")}
                    className={inputClass}
                  />
                  {createForm.formState.errors.email && (
                    <p className="text-xs text-red-500 mt-1">
                      {createForm.formState.errors.email.message}
                    </p>
                  )}
                </div>
                <div>
                  <label className={labelClass}>Rol</label>
                  <select {...createForm.register("role")} className={inputClass}>
                    <option value="requester">Solicitante</option>
                    <option value="agent">Agente</option>
                    <option value="supervisor">Supervisor</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
                <div>
                  <label className={labelClass}>Contraseña</label>
                  <input
                    type="password"
                    {...createForm.register("password")}
                    className={inputClass}
                    placeholder="Mínimo 8 caracteres"
                  />
                </div>
                {createMutation.isError && (
                  <p className="text-xs text-red-500">
                    Error al crear usuario. Intenta nuevamente.
                  </p>
                )}
                <div className="flex gap-2 pt-2">
                  <button
                    type="submit"
                    disabled={createMutation.isPending}
                    className="flex-1 py-2 bg-[#1a2c4e] text-white rounded-lg text-sm font-medium disabled:opacity-60"
                  >
                    {createMutation.isPending ? "Creando..." : "Crear usuario"}
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
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-5 py-3 text-left font-medium text-gray-500">
                  Nombre
                </th>
                <th className="px-5 py-3 text-left font-medium text-gray-500">
                  Rol
                </th>
                <th className="px-5 py-3 text-left font-medium text-gray-500">
                  Estado
                </th>
                <th className="px-5 py-3 text-left font-medium text-gray-500">
                  Último acceso
                </th>
                <th className="px-5 py-3 text-right font-medium text-gray-500">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {(data ?? []).map((u) => {
                const roleCfg = ROLE_CONFIG[u.role] ?? {
                  label: u.role,
                  className: "bg-gray-100 text-gray-600",
                };
                return (
                  <tr key={u.id} className="hover:bg-gray-50">
                    <td className="px-5 py-3">
                      <p className="font-medium text-gray-900">{u.full_name}</p>
                      <p className="text-xs text-gray-400">{u.email}</p>
                    </td>
                    <td className="px-5 py-3">
                      <span
                        className={cn(
                          "px-2 py-0.5 rounded-full text-xs font-medium",
                          roleCfg.className
                        )}
                      >
                        {roleCfg.label}
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      {u.is_archived ? (
                        <span className="text-xs text-gray-400">Archivado</span>
                      ) : u.is_active ? (
                        <span className="text-xs text-green-600 font-medium">
                          Activo
                        </span>
                      ) : (
                        <span className="text-xs text-red-500">Inactivo</span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-xs text-gray-400">
                      {u.last_login_at
                        ? format(new Date(u.last_login_at), "d MMM yyyy", {
                            locale: es,
                          })
                        : "Nunca"}
                    </td>
                    <td className="px-5 py-3 text-right space-x-2">
                      <button
                        onClick={() => {
                          setEditUser(u);
                          editForm.reset({
                            full_name: u.full_name,
                            role: u.role as EditForm["role"],
                            is_active: u.is_active,
                          });
                        }}
                        className="p-1 text-gray-400 hover:text-gray-700"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      {!u.is_archived && (
                        <button
                          onClick={() => setArchiveConfirm(u)}
                          className="p-1 text-gray-400 hover:text-red-600"
                        >
                          <Archive className="w-4 h-4" />
                        </button>
                      )}
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
        open={!!editUser}
        onOpenChange={(o) => !o && setEditUser(null)}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/40 z-50" />
          <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-xl shadow-xl p-6 w-full max-w-md z-50">
            <div className="flex items-center justify-between mb-5">
              <Dialog.Title className="font-semibold text-gray-900">
                Editar usuario
              </Dialog.Title>
              <Dialog.Close>
                <X className="w-4 h-4 text-gray-400" />
              </Dialog.Close>
            </div>
            <form
              onSubmit={editForm.handleSubmit((d) =>
                editMutation.mutate({ id: editUser!.id, ...d })
              )}
              className="space-y-4"
            >
              <div>
                <label className={labelClass}>Nombre completo</label>
                <input
                  {...editForm.register("full_name")}
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>Rol</label>
                <select
                  {...editForm.register("role")}
                  className={inputClass}
                >
                  <option value="requester">Solicitante</option>
                  <option value="agent">Agente</option>
                  <option value="supervisor">Supervisor</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_active"
                  {...editForm.register("is_active")}
                  className="rounded"
                />
                <label htmlFor="is_active" className="text-sm text-gray-700">
                  Usuario activo
                </label>
              </div>
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

      {/* Archive confirm */}
      <Dialog.Root
        open={!!archiveConfirm}
        onOpenChange={(o) => !o && setArchiveConfirm(null)}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/40 z-50" />
          <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-xl shadow-xl p-6 w-full max-w-sm z-50">
            <Dialog.Title className="font-semibold text-gray-900 mb-2">
              Archivar usuario
            </Dialog.Title>
            <p className="text-sm text-gray-600 mb-5">
              ¿Estás seguro de que deseas archivar a{" "}
              <strong>{archiveConfirm?.full_name}</strong>? Ya no podrá acceder
              al sistema.
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => archiveMutation.mutate(archiveConfirm!.id)}
                disabled={archiveMutation.isPending}
                className="flex-1 py-2 bg-red-600 text-white rounded-lg text-sm font-medium disabled:opacity-60"
              >
                {archiveMutation.isPending ? "Archivando..." : "Archivar"}
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
