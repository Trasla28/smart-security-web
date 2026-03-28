export type NotificationType =
  | "ticket_created"
  | "ticket_assigned"
  | "status_changed"
  | "comment_added"
  | "sla_warning"
  | "sla_breached"
  | "ticket_resolved";

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  body: string | null;
  ticket_id: string | null;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}
