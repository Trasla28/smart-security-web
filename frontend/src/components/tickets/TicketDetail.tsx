"use client";

import { useState, useRef } from "react";
import { useSession } from "next-auth/react";
import { useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow, format } from "date-fns";
import { es } from "date-fns/locale";
import { Lock, MessageSquare, Clock, User, Tag, MapPin, Calendar, AlertTriangle, Paperclip, FileText, Download, X, Image } from "lucide-react";
import { StatusBadge } from "./StatusBadge";
import { PriorityBadge } from "./PriorityBadge";
import { SLAIndicator } from "./SLAIndicator";
import {
  useTicket,
  useTicketComments,
  useTicketHistory,
  useTicketAttachments,
  useAddComment,
  useChangeStatus,
  useAssignTicket,
  useResolveTicket,
  useCloseTicket,
  useReopenTicket,
  ticketKeys,
} from "@/hooks/useTickets";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { cn } from "@/lib/utils";
import type { TicketStatus } from "@/types/ticket";

const ACCEPTED_TYPES = ".pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png,.webp";
const MAX_SIZE_MB = 10;

const ACTION_LABELS: Record<string, string> = {
  created: "Ticket creado",
  updated: "Ticket actualizado",
  status_changed: "Estado cambiado",
  assigned: "Asignado",
  escalated: "Escalado",
  reopened: "Reabierto",
  comment_added: "Comentario agregado",
};

interface TicketDetailProps {
  ticketId: string;
}

export function TicketDetail({ ticketId }: TicketDetailProps) {
  const { data: session } = useSession();
  const role = session?.user?.role ?? "requester";
  const userId = session?.user?.id;
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<"comments" | "history">("comments");
  const [commentBody, setCommentBody] = useState("");
  const [isInternal, setIsInternal] = useState(false);
  const [reopenReason, setReopenReason] = useState("");
  const [showReopenInput, setShowReopenInput] = useState(false);
  const [commentFiles, setCommentFiles] = useState<File[]>([]);
  const [fileError, setFileError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: ticket, isLoading } = useTicket(ticketId);
  const { data: comments = [] } = useTicketComments(ticketId);
  const { data: history = [] } = useTicketHistory(ticketId);
  const { data: attachments = [] } = useTicketAttachments(ticketId);

  const [assigneeId, setAssigneeId] = useState<string>("");
  const [assignError, setAssignError] = useState<string | null>(null);

  const { data: usersData = [] } = useQuery({
    queryKey: ["users-assign-picker"],
    queryFn: async () => {
      const res = await api.get<{ items: { id: string; full_name: string; role: string }[] }>(
        "/users",
        { params: { size: 100 } }
      );
      return (res.data.items ?? []).filter((u) => ["admin", "supervisor", "agent"].includes(u.role));
    },
    enabled: ["admin", "supervisor"].includes(role),
  });

  // For supervisors: fetch the ticket's area info to check if they can manage it
  const { data: areaMembers = [] } = useQuery({
    queryKey: ["area-members-check", ticket?.area_id],
    queryFn: async () => {
      const res = await api.get<{ id: string }[]>(`/areas/${ticket!.area_id}/members`);
      return res.data;
    },
    enabled: role === "supervisor" && !!ticket?.area_id,
  });

  const { data: areasData = [] } = useQuery({
    queryKey: ["areas-manager-check"],
    queryFn: async () => {
      const res = await api.get<{ id: string; manager_id: string | null }[]>("/areas");
      return res.data;
    },
    enabled: role === "supervisor",
  });

  const canAssign = (() => {
    if (role === "admin") return true;
    if (role !== "supervisor") return false;
    if (!ticket?.area_id) return false;
    const area = areasData.find((a) => a.id === ticket.area_id);
    const isManager = area?.manager_id === userId;
    const isMember = areaMembers.some((m) => m.id === userId);
    return isManager || isMember;
  })();

  const addComment = useAddComment(ticketId);
  const changeStatus = useChangeStatus(ticketId);
  const assignTicket = useAssignTicket(ticketId);
  const resolveTicket = useResolveTicket(ticketId);
  const closeTicket = useCloseTicket(ticketId);
  const reopenTicket = useReopenTicket(ticketId);

  if (isLoading || !ticket) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-1/2" />
        <div className="h-40 bg-gray-100 rounded" />
      </div>
    );
  }

  const canManageWorkflow = !!userId && userId === ticket.assigned_to;
  const canConfirmOrReopen = !!userId && userId === ticket.requester_id;
  const status = ticket.status as TicketStatus;

  async function handleStatusChange(newStatus: string) {
    await changeStatus.mutateAsync(newStatus);
  }

  function handleCommentFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    setFileError(null);
    const selected = Array.from(e.target.files ?? []);
    for (const f of selected) {
      if (f.size > MAX_SIZE_MB * 1024 * 1024) {
        setFileError(`"${f.name}" supera los ${MAX_SIZE_MB} MB.`);
        return;
      }
    }
    setCommentFiles((prev) => {
      const names = new Set(prev.map((f) => f.name));
      return [...prev, ...selected.filter((f) => !names.has(f.name))];
    });
    e.target.value = "";
  }

  function handleCommentPaste(e: React.ClipboardEvent<HTMLTextAreaElement>) {
    const items = Array.from(e.clipboardData.items);
    const imageItems = items.filter((item) => item.type.startsWith("image/"));
    if (imageItems.length === 0) return;
    e.preventDefault();
    for (const item of imageItems) {
      const file = item.getAsFile();
      if (!file) continue;
      const name = `imagen_pegada_${Date.now()}.png`;
      const namedFile = new File([file], name, { type: file.type });
      setCommentFiles((prev) => [...prev, namedFile]);
    }
  }

  async function handleSubmitComment(e: React.FormEvent) {
    e.preventDefault();
    if (!commentBody.trim() && commentFiles.length === 0) return;
    const comment = await addComment.mutateAsync({ body: commentBody, is_internal: isInternal });
    if (commentFiles.length > 0) {
      for (const file of commentFiles) {
        const form = new FormData();
        form.append("file", file);
        form.append("comment_id", comment.id);
        await api.post(`/tickets/${ticketId}/attachments`, form, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      }
      qc.invalidateQueries({ queryKey: ticketKeys.attachments(ticketId) });
    }
    setCommentBody("");
    setIsInternal(false);
    setCommentFiles([]);
    setFileError(null);
  }

  async function handleReopen() {
    if (!reopenReason.trim()) return;
    await reopenTicket.mutateAsync(reopenReason);
    setShowReopenInput(false);
    setReopenReason("");
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <span className="font-mono">{ticket.ticket_number}</span>
              {ticket.is_recurring_instance && (
                <span className="bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full text-xs">Recurrente</span>
              )}
            </div>
            <h1 className="text-xl font-bold text-gray-900">{ticket.title}</h1>
            <div className="flex items-center gap-2 flex-wrap">
              <StatusBadge status={status} />
              <PriorityBadge priority={ticket.priority} />
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap gap-2">
            {/* Agente asignado / supervisor / admin: mover ticket en proceso y resolver */}
            {canManageWorkflow && (status === "open" || status === "pending") && (
              <button
                onClick={() => handleStatusChange("in_progress")}
                disabled={changeStatus.isPending}
                className="px-3 py-1.5 bg-yellow-100 text-yellow-800 rounded-lg text-sm font-medium hover:bg-yellow-200 transition-colors"
              >
                En Proceso
              </button>
            )}
            {canManageWorkflow && (status === "in_progress" || status === "escalated") && (
              <button
                onClick={() => resolveTicket.mutate()}
                disabled={resolveTicket.isPending}
                className="px-3 py-1.5 bg-green-100 text-green-800 rounded-lg text-sm font-medium hover:bg-green-200 transition-colors"
              >
                Resolver
              </button>
            )}

            {/* Solicitante (o admin): confirmar resolución o reabrir */}
            {canConfirmOrReopen && status === "resolved" && (
              <button
                onClick={() => closeTicket.mutate()}
                disabled={closeTicket.isPending}
                className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors"
              >
                {closeTicket.isPending ? "Confirmando..." : "Confirmar resolución"}
              </button>
            )}
            {canConfirmOrReopen && (status === "resolved" || status === "closed") && (
              <button
                onClick={() => setShowReopenInput(true)}
                className="px-3 py-1.5 bg-blue-100 text-blue-800 rounded-lg text-sm font-medium hover:bg-blue-200 transition-colors"
              >
                Reabrir
              </button>
            )}
          </div>
        </div>

        {showReopenInput && (
          <div className="mt-4 p-4 bg-blue-50 rounded-lg space-y-2">
            <label className="text-sm font-medium text-gray-700">Razón para reabrir</label>
            <input
              value={reopenReason}
              onChange={(e) => setReopenReason(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2c4e]"
              placeholder="Explica por qué se reabre el ticket..."
            />
            <div className="flex gap-2">
              <button onClick={handleReopen} className="px-3 py-1.5 bg-[#1a2c4e] text-white rounded-lg text-sm">Confirmar</button>
              <button onClick={() => setShowReopenInput(false)} className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm">Cancelar</button>
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Description */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Descripción</h2>
            <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{ticket.description}</p>
          </div>

          {/* Adjuntos del ticket */}
          {attachments.filter((a) => !a.comment_id).length > 0 && (
            <AttachmentList attachments={attachments.filter((a) => !a.comment_id)} />
          )}

          {/* SLA */}
          {ticket.sla_status && (
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <SLAIndicator
                slaStatus={ticket.sla_status}
                slaPercentage={ticket.sla_percentage}
                slaDueAt={ticket.sla_due_at}
              />
            </div>
          )}

          {/* Comments / History tabs */}
          <div className="bg-white rounded-xl border border-gray-200">
            <div className="flex border-b border-gray-200">
              <button
                onClick={() => setActiveTab("comments")}
                className={cn("flex items-center gap-1.5 px-5 py-3 text-sm font-medium border-b-2 transition-colors", activeTab === "comments" ? "border-[#1a2c4e] text-[#1a2c4e]" : "border-transparent text-gray-500 hover:text-gray-700")}
              >
                <MessageSquare className="w-4 h-4" />
                Comentarios ({comments.length})
              </button>
              <button
                onClick={() => setActiveTab("history")}
                className={cn("flex items-center gap-1.5 px-5 py-3 text-sm font-medium border-b-2 transition-colors", activeTab === "history" ? "border-[#1a2c4e] text-[#1a2c4e]" : "border-transparent text-gray-500 hover:text-gray-700")}
              >
                <Clock className="w-4 h-4" />
                Historial ({history.length})
              </button>
            </div>

            <div className="p-5 space-y-4">
              {activeTab === "comments" && (
                <>
                  {comments.length === 0 && (
                    <p className="text-sm text-gray-400 text-center py-4">Sin comentarios aún.</p>
                  )}
                  {comments.map((c) => {
                    const commentAttachments = attachments.filter((a) => a.comment_id === c.id);
                    return (
                      <div
                        key={c.id}
                        className={cn("rounded-lg p-4 text-sm", c.is_internal ? "bg-amber-50 border border-amber-200" : "bg-gray-50")}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-medium text-gray-800">{c.author?.full_name ?? "Sistema"}</span>
                          <div className="flex items-center gap-2">
                            {c.is_internal && (
                              <span className="flex items-center gap-1 text-xs text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full">
                                <Lock className="w-3 h-3" /> Nota interna
                              </span>
                            )}
                            <span className="text-xs text-gray-400">
                              {formatDistanceToNow(new Date(c.created_at), { addSuffix: true, locale: es })}
                            </span>
                          </div>
                        </div>
                        {c.body && <p className="text-gray-700 whitespace-pre-wrap">{c.body}</p>}
                        {commentAttachments.length > 0 && (
                          <div className="mt-2 pt-2 border-t border-gray-200">
                            <AttachmentList attachments={commentAttachments} compact />
                          </div>
                        )}
                      </div>
                    );
                  })}

                  {/* Add comment form */}
                  {status !== "closed" && (
                    <form onSubmit={handleSubmitComment} className="pt-2 space-y-2">
                      <textarea
                        value={commentBody}
                        onChange={(e) => setCommentBody(e.target.value)}
                        onPaste={handleCommentPaste}
                        rows={3}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-[#1a2c4e]"
                        placeholder="Escribe un comentario... (puedes pegar imágenes directamente)"
                      />

                      {/* Files selected for this comment */}
                      {commentFiles.length > 0 && (
                        <ul className="space-y-1">
                          {commentFiles.map((f) => (
                            <li key={f.name} className="flex items-center justify-between text-xs bg-gray-50 border border-gray-200 rounded px-3 py-1.5">
                              <div className="flex items-center gap-1.5 min-w-0">
                                {f.type.startsWith("image/") ? <Image className="w-3.5 h-3.5 text-gray-400 shrink-0" /> : <FileText className="w-3.5 h-3.5 text-gray-400 shrink-0" />}
                                <span className="truncate text-gray-700">{f.name}</span>
                                <span className="text-gray-400 shrink-0">{(f.size / 1024).toFixed(0)} KB</span>
                              </div>
                              <button type="button" onClick={() => setCommentFiles((p) => p.filter((x) => x.name !== f.name))} className="ml-2 text-gray-400 hover:text-red-500 shrink-0">
                                <X className="w-3.5 h-3.5" />
                              </button>
                            </li>
                          ))}
                        </ul>
                      )}
                      {fileError && <p className="text-xs text-red-600">{fileError}</p>}

                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <div className="flex items-center gap-3">
                          {role !== "requester" && (
                            <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
                              <input type="checkbox" checked={isInternal} onChange={(e) => setIsInternal(e.target.checked)} className="rounded" />
                              Nota interna
                            </label>
                          )}
                          <input ref={fileInputRef} type="file" multiple accept={ACCEPTED_TYPES} onChange={handleCommentFileChange} className="hidden" />
                          <button
                            type="button"
                            onClick={() => fileInputRef.current?.click()}
                            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-[#1a2c4e] transition-colors"
                          >
                            <Paperclip className="w-4 h-4" />
                            Adjuntar
                          </button>
                        </div>
                        <button
                          type="submit"
                          disabled={(!commentBody.trim() && commentFiles.length === 0) || addComment.isPending}
                          className="px-4 py-1.5 bg-[#1a2c4e] text-white rounded-lg text-sm font-medium hover:bg-[#243d6a] disabled:opacity-50 transition-colors"
                        >
                          {addComment.isPending ? "Enviando..." : "Comentar"}
                        </button>
                      </div>
                    </form>
                  )}
                </>
              )}

              {activeTab === "history" && (
                <div className="space-y-3">
                  {history.length === 0 && (
                    <p className="text-sm text-gray-400 text-center py-4">Sin historial.</p>
                  )}
                  {history.map((h) => (
                    <div key={h.id} className="flex gap-3 text-sm">
                      <div className="w-1.5 h-1.5 rounded-full bg-gray-300 mt-2 flex-shrink-0" />
                      <div>
                        <span className="font-medium text-gray-700">{ACTION_LABELS[h.action] ?? h.action}</span>
                        {h.actor && <span className="text-gray-400 ml-1">por {h.actor.full_name}</span>}
                        <p className="text-xs text-gray-400 mt-0.5">
                          {format(new Date(h.created_at), "d MMM yyyy, HH:mm", { locale: es })}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Sidebar metadata */}
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
            <h3 className="text-sm font-semibold text-gray-700">Detalles</h3>
            <MetaRow icon={<Tag className="w-4 h-4" />} label="Estado"><StatusBadge status={status} /></MetaRow>
            <MetaRow icon={<AlertTriangle className="w-4 h-4" />} label="Prioridad"><PriorityBadge priority={ticket.priority} /></MetaRow>
            <MetaRow icon={<MapPin className="w-4 h-4" />} label="Área">{ticket.area?.name ?? <span className="text-gray-400 text-xs">Sin área</span>}</MetaRow>
            <MetaRow icon={<Tag className="w-4 h-4" />} label="Categoría">{ticket.category?.name ?? <span className="text-gray-400 text-xs">Sin categoría</span>}</MetaRow>
            <MetaRow icon={<User className="w-4 h-4" />} label="Solicitante">{ticket.requester?.full_name ?? "—"}</MetaRow>
            <MetaRow icon={<User className="w-4 h-4" />} label="Asignado">
              {ticket.assignee?.full_name ?? <span className="text-gray-400 text-xs">Sin asignar</span>}
            </MetaRow>
            {canAssign && status !== "closed" && (
              <div className="pt-1 space-y-2">
                <p className="text-xs text-gray-500 font-medium">{ticket.assignee ? "Reasignar a" : "Asignar a"}</p>
                <select
                  value={assigneeId}
                  onChange={(e) => { setAssigneeId(e.target.value); setAssignError(null); }}
                  className="w-full px-2 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2c4e]"
                >
                  <option value="">Seleccionar agente...</option>
                  {usersData.map((u) => (
                    <option key={u.id} value={u.id}>{u.full_name}</option>
                  ))}
                </select>
                {assignError && <p className="text-xs text-red-600">{assignError}</p>}
                <button
                  disabled={!assigneeId || assignTicket.isPending}
                  onClick={async () => {
                    if (!assigneeId) return;
                    try {
                      await assignTicket.mutateAsync(assigneeId);
                      setAssigneeId("");
                      setAssignError(null);
                    } catch {
                      setAssignError("No se pudo asignar. Verifica tus permisos.");
                    }
                  }}
                  className="w-full px-3 py-1.5 bg-[#1a2c4e] text-white rounded-lg text-sm font-medium hover:bg-[#243d6a] disabled:opacity-50 transition-colors"
                >
                  {assignTicket.isPending ? "Asignando..." : ticket.assignee ? "Reasignar" : "Asignar"}
                </button>
              </div>
            )}
            <MetaRow icon={<Calendar className="w-4 h-4" />} label="Creado">
              <span className="text-xs">{format(new Date(ticket.created_at), "d MMM yyyy, HH:mm", { locale: es })}</span>
            </MetaRow>
            {ticket.resolved_at && (
              <MetaRow icon={<Calendar className="w-4 h-4" />} label="Resuelto">
                <span className="text-xs">{format(new Date(ticket.resolved_at), "d MMM yyyy, HH:mm", { locale: es })}</span>
              </MetaRow>
            )}
            {ticket.reopen_count > 0 && (
              <MetaRow icon={<Clock className="w-4 h-4" />} label="Reaperturas">
                <span className="text-xs font-medium text-orange-600">{ticket.reopen_count}</span>
              </MetaRow>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function AttachmentList({ attachments, compact = false }: { attachments: import("@/types/ticket").Attachment[]; compact?: boolean }) {
  return (
    <div className={compact ? "" : "bg-white rounded-xl border border-gray-200 p-6"}>
      {!compact && (
        <h2 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
          <Paperclip className="w-4 h-4 text-gray-400" />
          Adjuntos ({attachments.length})
        </h2>
      )}
      <ul className="space-y-1.5">
        {attachments.map((a) => {
          const isImage = a.mime_type.startsWith("image/");
          return (
            <li key={a.id} className="flex items-center justify-between bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
              <div className="flex items-center gap-2 min-w-0">
                {isImage ? <Image className="w-4 h-4 text-gray-400 shrink-0" /> : <FileText className="w-4 h-4 text-gray-400 shrink-0" />}
                <div className="min-w-0">
                  <p className="text-sm text-gray-700 truncate">{a.filename}</p>
                  <p className="text-xs text-gray-400">{(a.file_size / 1024).toFixed(0)} KB · {a.mime_type.split("/")[1]?.toUpperCase()}</p>
                </div>
              </div>
              {a.download_url && (
                <a
                  href={`http://localhost:8000${a.download_url}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ml-3 flex items-center gap-1 text-xs text-[#1a2c4e] font-medium hover:underline shrink-0"
                >
                  <Download className="w-3.5 h-3.5" />
                  Descargar
                </a>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function MetaRow({ icon, label, children }: { icon: React.ReactNode; label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2">
      <span className="text-gray-400 mt-0.5 flex-shrink-0">{icon}</span>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-gray-400 mb-0.5">{label}</p>
        <div className="text-sm text-gray-700">{children}</div>
      </div>
    </div>
  );
}
