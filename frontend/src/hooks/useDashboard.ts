"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type {
  DashboardSummary,
  TicketsByAreaItem,
  TicketsByStatusItem,
  AgentPerformanceItem,
  UrgencyAbuseItem,
  UserPerformanceItem,
} from "@/types/admin";

export function useDashboardSummary() {
  return useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: async () => {
      const res = await api.get<DashboardSummary>("/dashboard/summary");
      return res.data;
    },
  });
}

export function useTicketsByArea() {
  return useQuery({
    queryKey: ["dashboard", "by-area"],
    queryFn: async () => {
      const res = await api.get<TicketsByAreaItem[]>("/dashboard/tickets-by-area");
      return res.data;
    },
  });
}

export function useTicketsByStatus() {
  return useQuery({
    queryKey: ["dashboard", "by-status"],
    queryFn: async () => {
      const res = await api.get<TicketsByStatusItem[]>("/dashboard/tickets-by-status");
      return res.data;
    },
  });
}

export function useAgentPerformance() {
  return useQuery({
    queryKey: ["dashboard", "agent-performance"],
    queryFn: async () => {
      const res = await api.get<AgentPerformanceItem[]>("/dashboard/agent-performance");
      return res.data;
    },
  });
}

export function useUserPerformance(days: number = 30) {
  return useQuery({
    queryKey: ["dashboard", "user-performance", days],
    queryFn: async () => {
      const res = await api.get<UserPerformanceItem[]>(`/dashboard/user-performance?days=${days}`);
      return res.data;
    },
  });
}

export function useUrgencyAbuse() {
  return useQuery({
    queryKey: ["dashboard", "urgency-abuse"],
    queryFn: async () => {
      const res = await api.get<UrgencyAbuseItem[]>("/dashboard/urgency-abuse");
      return res.data;
    },
  });
}
