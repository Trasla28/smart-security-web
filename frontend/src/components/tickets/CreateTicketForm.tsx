"use client";

import { useState, useRef } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Paperclip, X, Search } from "lucide-react";
import api from "@/lib/api";
import { useCreateTicket } from "@/hooks/useTickets";
import { cn } from "@/lib/utils";

const schema = z.object({
  title: z.string().min(3, "Mínimo 3 caracteres").max(500),
  description: z.string().min(1, "La descripción es requerida"),
  priority: z.enum(["low", "medium", "high", "urgent"]),
  category_id: z.string().optional(),
  area_id: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

interface UserOption { id: string; full_name: string; email: string; role: string }

const ACCEPTED_TYPES = ".pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png,.webp";
const MAX_SIZE_MB = 10;

const ROLE_LABEL: Record<string, string> = {
  admin: "Admin", supervisor: "Supervisor", agent: "Agente", requester: "Solicitante",
};

function UserPicker({
  label,
  hint,
  value,
  onChange,
  multi,
  users,
}: {
  label: string;
  hint?: string;
  value: UserOption | UserOption[] | null;
  onChange: (u: UserOption) => void;
  multi?: boolean;
  users: UserOption[];
}) {
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);

  const selected = multi ? (value as UserOption[]) : value ? [value as UserOption] : [];
  const selectedIds = new Set(selected.map((u) => u.id));

  const filtered = users.filter(
    (u) =>
      !selectedIds.has(u.id) &&
      (u.full_name.toLowerCase().includes(search.toLowerCase()) ||
        u.email.toLowerCase().includes(search.toLowerCase()))
  );

  const inputClass = "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2c4e] focus:border-transparent";
  const labelClass = "block text-sm font-medium text-gray-700 mb-1";

  return (
    <div>
      <label className={labelClass}>{label}</label>
      <div className="relative">
        <div
          className={cn(inputClass, "flex flex-wrap gap-1.5 min-h-[40px] cursor-text")}
          onClick={() => setOpen(true)}
        >
          {selected.map((u) => (
            <span key={u.id} className="inline-flex items-center gap-1 bg-[#1a2c4e] text-white text-xs rounded-full px-2.5 py-0.5">
              {u.full_name}
              <button
                type="button"
                onMouseDown={(e) => { e.stopPropagation(); onChange(u); }}
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
          <div className="flex items-center gap-1.5 flex-1 min-w-[140px]">
            <Search className="w-3.5 h-3.5 text-gray-400 shrink-0" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onFocus={() => setOpen(true)}
              onBlur={() => setTimeout(() => setOpen(false), 150)}
              placeholder={selected.length === 0 ? "Buscar por nombre o correo..." : ""}
              className="flex-1 text-sm outline-none bg-transparent"
            />
          </div>
        </div>

        {open && filtered.length > 0 && (
          <ul className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
            {filtered.map((u) => (
              <li
                key={u.id}
                onMouseDown={() => { onChange(u); if (!multi) setOpen(false); setSearch(""); }}
                className="flex items-center justify-between px-3 py-2 hover:bg-gray-50 cursor-pointer"
              >
                <div>
                  <p className="text-sm font-medium text-gray-800">{u.full_name}</p>
                  <p className="text-xs text-gray-400">{u.email}</p>
                </div>
                <span className="text-xs text-gray-400">{ROLE_LABEL[u.role] ?? u.role}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
      {hint && <p className="text-xs text-gray-400 mt-1">{hint}</p>}
    </div>
  );
}

export function CreateTicketForm() {
  const router = useRouter();
  const createTicket = useCreateTicket();

  const [assignedTo, setAssignedTo] = useState<UserOption | null>(null);
  const [notifyUsers, setNotifyUsers] = useState<UserOption[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [fileError, setFileError] = useState<string | null>(null);

  const { data: areasData } = useQuery({
    queryKey: ["areas"],
    queryFn: async () => {
      const res = await api.get<{ items: { id: string; name: string }[] }>("/areas");
      return res.data.items ?? [];
    },
  });

  const { data: categories } = useQuery({
    queryKey: ["categories-public"],
    queryFn: async () => {
      const res = await api.get<{ id: string; name: string }[]>("/admin/categories?active_only=true");
      return res.data;
    },
  });

  const { data: usersData = [] } = useQuery({
    queryKey: ["users-picker"],
    queryFn: async () => {
      const res = await api.get<{ items: UserOption[] }>("/users", { params: { size: 100 } });
      return res.data.items ?? [];
    },
  });

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { priority: "medium" },
  });

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    setFileError(null);
    const selected = Array.from(e.target.files ?? []);
    for (const f of selected) {
      if (f.size > MAX_SIZE_MB * 1024 * 1024) {
        setFileError(`"${f.name}" supera los ${MAX_SIZE_MB} MB.`);
        return;
      }
    }
    setFiles((prev) => {
      const names = new Set(prev.map((f) => f.name));
      return [...prev, ...selected.filter((f) => !names.has(f.name))];
    });
    e.target.value = "";
  }

  function toggleNotify(user: UserOption) {
    setNotifyUsers((prev) =>
      prev.some((u) => u.id === user.id) ? prev.filter((u) => u.id !== user.id) : [...prev, user]
    );
  }

  async function onSubmit(data: FormData) {
    try {
      const result = await createTicket.mutateAsync({
        title: data.title,
        description: data.description,
        priority: data.priority,
        category_id: data.category_id || undefined,
        area_id: data.area_id || undefined,
        assigned_to: assignedTo?.id || undefined,
        notify_user_ids: notifyUsers.length > 0 ? notifyUsers.map((u) => u.id) : undefined,
      });

      for (const file of files) {
        const form = new FormData();
        form.append("file", file);
        await api.post(`/tickets/${result.id}/attachments`, form, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      }

      router.push(`/tickets/${result.id}`);
    } catch {
      // error tracked via createTicket.isError
    }
  }

  const inputClass = "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2c4e] focus:border-transparent";
  const labelClass = "block text-sm font-medium text-gray-700 mb-1";
  const errorClass = "text-xs text-red-600 mt-1";

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">

      {/* Asignar a — antes del título */}
      <UserPicker
        label="Asignar a"
        hint="Persona responsable de atender este ticket. Si se deja vacío se aplica la asignación automática por categoría."
        value={assignedTo}
        onChange={(u) => setAssignedTo((prev) => prev?.id === u.id ? null : u)}
        multi={false}
        users={usersData}
      />

      {/* Título */}
      <div>
        <label className={labelClass}>Título *</label>
        <input {...register("title")} className={inputClass} placeholder="Describe brevemente el problema o solicitud" />
        {errors.title && <p className={errorClass}>{errors.title.message}</p>}
      </div>

      {/* Descripción */}
      <div>
        <label className={labelClass}>Descripción *</label>
        <textarea
          {...register("description")}
          rows={5}
          className={cn(inputClass, "resize-none")}
          placeholder="Proporciona todos los detalles necesarios para atender tu solicitud..."
        />
        {errors.description && <p className={errorClass}>{errors.description.message}</p>}
      </div>

      {/* Prioridad / Categoría / Área */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <label className={labelClass}>Prioridad</label>
          <select {...register("priority")} className={inputClass}>
            <option value="low">Baja</option>
            <option value="medium">Media</option>
            <option value="high">Alta</option>
            <option value="urgent">Urgente</option>
          </select>
        </div>
        <div>
          <label className={labelClass}>Categoría</label>
          <select {...register("category_id")} className={inputClass}>
            <option value="">Sin categoría</option>
            {categories?.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className={labelClass}>Área</label>
          <select {...register("area_id")} className={inputClass}>
            <option value="">Sin área</option>
            {areasData?.map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Adjuntos */}
      <div>
        <label className={labelClass}>Adjuntos</label>
        <div className="border border-dashed border-gray-300 rounded-lg p-4 bg-gray-50">
          <input ref={fileInputRef} type="file" multiple accept={ACCEPTED_TYPES} onChange={handleFileChange} className="hidden" />
          <button type="button" onClick={() => fileInputRef.current?.click()} className="flex items-center gap-2 text-sm text-[#1a2c4e] font-medium hover:underline">
            <Paperclip className="w-4 h-4" />
            Adjuntar archivo (PDF, Word, Excel, imágenes — máx. {MAX_SIZE_MB} MB)
          </button>
          {fileError && <p className={errorClass + " mt-2"}>{fileError}</p>}
          {files.length > 0 && (
            <ul className="mt-3 space-y-1">
              {files.map((f) => (
                <li key={f.name} className="flex items-center justify-between text-sm bg-white border border-gray-200 rounded px-3 py-1.5">
                  <span className="truncate max-w-xs text-gray-700">{f.name}</span>
                  <button type="button" onClick={() => setFiles((p) => p.filter((x) => x.name !== f.name))} className="ml-2 text-gray-400 hover:text-red-500">
                    <X className="w-3.5 h-3.5" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Notificar a */}
      <UserPicker
        label="Notificar a"
        hint="Personas que recibirán una notificación al crear el ticket (sin ser el responsable)."
        value={notifyUsers}
        onChange={toggleNotify}
        multi={true}
        users={usersData.filter((u) => u.id !== assignedTo?.id)}
      />

      {createTicket.isError && (
        <p className="text-sm text-red-600">No se pudo crear el ticket. Intenta de nuevo.</p>
      )}

      <div className="flex gap-3 pt-2">
        <button
          type="submit"
          disabled={createTicket.isPending}
          className="px-5 py-2.5 bg-[#1a2c4e] text-white rounded-lg text-sm font-medium hover:bg-[#243d6a] disabled:opacity-60 transition-colors"
        >
          {createTicket.isPending ? "Creando..." : "Crear ticket"}
        </button>
        <button type="button" onClick={() => router.back()} className="px-5 py-2.5 border border-gray-300 text-gray-700 rounded-lg text-sm hover:bg-gray-50 transition-colors">
          Cancelar
        </button>
      </div>
    </form>
  );
}
