export interface DashboardSummary {
  total_open: number;
  total_in_progress: number;
  total_pending: number;
  total_escalated: number;
  total_resolved_today: number;
  total_closed_today: number;
  avg_resolution_hours: number | null;
  sla_compliance_pct: number | null;
  new_today: number;
}

export interface TicketsByAreaItem {
  area_id: string | null;
  area_name: string;
  total: number;
  open: number;
  in_progress: number;
  resolved: number;
}

export interface TicketsByStatusItem {
  status: string;
  count: number;
  percentage: number;
}

export interface SLAComplianceResponse {
  total_with_sla: number;
  resolved_on_time: number;
  compliance_pct: number;
  by_priority: { priority: string; total: number; on_time: number; pct: number }[];
}

export interface AgentPerformanceItem {
  agent_id: string;
  agent_name: string;
  assigned_total: number;
  resolved_total: number;
  avg_resolution_hours: number | null;
  sla_compliance_pct: number | null;
}

export interface UserPerformanceItem {
  user_id: string;
  user_name: string;
  user_email: string;
  role: string;
  assigned_total: number;
  resolved_total: number;
  closed_total: number;
  active_total: number;
  avg_resolution_hours: number | null;
  avg_first_response_hours: number | null;
  sla_breached_total: number;
  sla_compliance_pct: number | null;
  tickets_reopened: number;
  reopen_rate_pct: number | null;
  performance_score: number;
  score_label: string;
}

export interface UrgencyAbuseItem {
  user_id: string;
  user_name: string;
  area_name: string | null;
  total_tickets: number;
  urgent_tickets: number;
  urgent_pct: number;
  prev_period_pct: number | null;
  trend: string;
}

export interface AdminUser {
  id: string;
  tenant_id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  is_archived: boolean;
  avatar_url: string | null;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Area {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  manager_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AreaMember {
  id: string;
  full_name: string;
  email: string;
  role: string;
  is_primary: boolean;
}

export interface Category {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  default_area_id: string | null;
  default_agent_id: string | null;
  requires_approval: boolean;
  approver_role: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SLA {
  id: string;
  tenant_id: string;
  category_id: string | null;
  priority: string | null;
  response_hours: number;
  resolution_hours: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RecurringTemplate {
  id: string;
  tenant_id: string;
  title: string;
  description: string | null;
  category_id: string | null;
  area_id: string | null;
  priority: string;
  assigned_to: string | null;
  recurrence_type: string;
  recurrence_value: number | null;
  recurrence_day: number | null;
  if_holiday_action: string;
  is_active: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface TenantConfig {
  id: string;
  tenant_id: string;
  logo_url: string | null;
  primary_color: string;
  auth_method: string;
  auto_close_days: number;
  urgency_abuse_threshold: number;
  urgency_report_visible_to: string | null;
  timezone: string;
  working_hours_start: string;
  working_hours_end: string;
  working_days: number[];
  weekly_report_enabled: boolean;
  weekly_report_day: number;
  weekly_report_recipients: string[];
  updated_at: string;
}
