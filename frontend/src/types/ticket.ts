export type TicketStatus = "open" | "in_progress" | "pending" | "escalated" | "resolved" | "closed";
export type TicketPriority = "low" | "medium" | "high" | "urgent";
export type SLAStatus = "ok" | "warning" | "breached";

export interface UserBrief {
  id: string;
  full_name: string;
  email: string;
  avatar_url: string | null;
}

export interface AreaBrief { id: string; name: string; }
export interface CategoryBrief { id: string; name: string; }

export interface TicketListItem {
  id: string;
  ticket_number: string;
  title: string;
  status: TicketStatus;
  priority: TicketPriority;
  sla_due_at: string | null;
  sla_breached: boolean;
  sla_status: SLAStatus | null;
  created_at: string;
  updated_at: string;
  requester: UserBrief | null;
  assignee: UserBrief | null;
  area: AreaBrief | null;
  category: CategoryBrief | null;
}

export interface Ticket {
  id: string;
  tenant_id: string;
  ticket_number: string;
  title: string;
  description: string;
  status: TicketStatus;
  priority: TicketPriority;
  category_id: string | null;
  area_id: string | null;
  requester_id: string;
  assigned_to: string | null;
  sla_id: string | null;
  sla_due_at: string | null;
  sla_breached: boolean;
  sla_status: SLAStatus | null;
  sla_percentage: number | null;
  first_response_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  is_recurring_instance: boolean;
  reopen_count: number;
  created_at: string;
  updated_at: string;
  requester: UserBrief | null;
  assignee: UserBrief | null;
  area: AreaBrief | null;
  category: CategoryBrief | null;
}

export interface Comment {
  id: string;
  ticket_id: string;
  author_id: string;
  body: string;
  is_internal: boolean;
  created_at: string;
  updated_at: string;
  author: UserBrief | null;
}

export interface TicketHistory {
  id: string;
  ticket_id: string;
  actor_id: string | null;
  action: string;
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  created_at: string;
  actor: { id: string; full_name: string; email: string } | null;
}

export interface Attachment {
  id: string;
  ticket_id: string;
  comment_id: string | null;
  filename: string;
  file_size: number;
  mime_type: string;
  uploaded_by: string;
  created_at: string;
  download_url: string | null;
}
