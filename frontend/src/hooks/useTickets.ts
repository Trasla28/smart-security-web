"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Ticket, TicketListItem, Comment, TicketHistory, Attachment } from "@/types/ticket";
import type { PaginatedResponse } from "@/types/api";

// --- Query keys ---
export const ticketKeys = {
  all: ["tickets"] as const,
  list: (filters: TicketFilters) => ["tickets", "list", filters as Record<string, unknown>] as const,
  detail: (id: string) => ["tickets", id] as const,
  comments: (id: string) => ["tickets", id, "comments"] as const,
  history: (id: string) => ["tickets", id, "history"] as const,
  attachments: (id: string) => ["tickets", id, "attachments"] as const,
};

export interface TicketFilters {
  page?: number;
  size?: number;
  status?: string;
  priority?: string;
  area_id?: string;
  category_id?: string;
  assigned_to?: string;
  sort_by?: string;
}

// --- Queries ---
export function useTicketList(filters: TicketFilters = {}) {
  return useQuery({
    queryKey: ticketKeys.list(filters),
    queryFn: async () => {
      const params = Object.fromEntries(
        Object.entries(filters).filter(([, v]) => v !== undefined && v !== "")
      );
      const res = await api.get<PaginatedResponse<TicketListItem>>("/tickets", { params });
      return res.data;
    },
  });
}

export function useTicket(id: string) {
  return useQuery({
    queryKey: ticketKeys.detail(id),
    queryFn: async () => {
      const res = await api.get<Ticket>(`/tickets/${id}`);
      return res.data;
    },
    enabled: !!id,
  });
}

export function useTicketComments(ticketId: string) {
  return useQuery({
    queryKey: ticketKeys.comments(ticketId),
    queryFn: async () => {
      const res = await api.get<Comment[]>(`/tickets/${ticketId}/comments`);
      return res.data;
    },
    enabled: !!ticketId,
  });
}

export function useTicketHistory(ticketId: string) {
  return useQuery({
    queryKey: ticketKeys.history(ticketId),
    queryFn: async () => {
      const res = await api.get<TicketHistory[]>(`/tickets/${ticketId}/history`);
      return res.data;
    },
    enabled: !!ticketId,
  });
}

export function useTicketAttachments(ticketId: string) {
  return useQuery({
    queryKey: ticketKeys.attachments(ticketId),
    queryFn: async () => {
      const res = await api.get<Attachment[]>(`/tickets/${ticketId}/attachments`);
      return res.data;
    },
    enabled: !!ticketId,
  });
}

// --- Mutations ---
export function useCreateTicket() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: { title: string; description: string; priority: string; category_id?: string; area_id?: string; assigned_to?: string; notify_user_ids?: string[] }) => {
      const res = await api.post<Ticket>("/tickets", data);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ticketKeys.all }),
  });
}

export function useUploadAttachment(ticketId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const res = await api.post(`/tickets/${ticketId}/attachments`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ticketKeys.attachments(ticketId) }),
  });
}

export function useUpdateTicket(ticketId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<{ title: string; description: string; priority: string; category_id: string; area_id: string }>) => {
      const res = await api.patch<Ticket>(`/tickets/${ticketId}`, data);
      return res.data;
    },
    onSuccess: (updated) => {
      qc.setQueryData(ticketKeys.detail(ticketId), updated);
      qc.invalidateQueries({ queryKey: ticketKeys.all });
    },
  });
}

export function useChangeStatus(ticketId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (status: string) => {
      const res = await api.post<Ticket>(`/tickets/${ticketId}/status`, { status });
      return res.data;
    },
    onSuccess: (updated) => {
      qc.setQueryData(ticketKeys.detail(ticketId), updated);
      qc.invalidateQueries({ queryKey: ticketKeys.all });
    },
  });
}

export function useAssignTicket(ticketId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (agent_id: string) => {
      const res = await api.post<Ticket>(`/tickets/${ticketId}/assign`, { agent_id });
      return res.data;
    },
    onSuccess: (updated) => {
      qc.setQueryData(ticketKeys.detail(ticketId), updated);
      qc.invalidateQueries({ queryKey: ticketKeys.all });
    },
  });
}

export function useEscalateTicket(ticketId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: { reason: string; area_id?: string }) => {
      const res = await api.post<Ticket>(`/tickets/${ticketId}/escalate`, data);
      return res.data;
    },
    onSuccess: (updated) => {
      qc.setQueryData(ticketKeys.detail(ticketId), updated);
      qc.invalidateQueries({ queryKey: ticketKeys.all });
    },
  });
}

export function useResolveTicket(ticketId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await api.post<Ticket>(`/tickets/${ticketId}/resolve`);
      return res.data;
    },
    onSuccess: (updated) => {
      qc.setQueryData(ticketKeys.detail(ticketId), updated);
      qc.invalidateQueries({ queryKey: ticketKeys.all });
    },
  });
}

export function useCloseTicket(ticketId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await api.post<Ticket>(`/tickets/${ticketId}/close`);
      return res.data;
    },
    onSuccess: (updated) => {
      qc.setQueryData(ticketKeys.detail(ticketId), updated);
      qc.invalidateQueries({ queryKey: ticketKeys.all });
    },
  });
}

export function useReopenTicket(ticketId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (reason: string) => {
      const res = await api.post<Ticket>(`/tickets/${ticketId}/reopen`, { reason });
      return res.data;
    },
    onSuccess: (updated) => {
      qc.setQueryData(ticketKeys.detail(ticketId), updated);
      qc.invalidateQueries({ queryKey: ticketKeys.all });
    },
  });
}

export function useAddComment(ticketId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: { body: string; is_internal: boolean }) => {
      const res = await api.post<Comment>(`/tickets/${ticketId}/comments`, data);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ticketKeys.comments(ticketId) }),
  });
}
