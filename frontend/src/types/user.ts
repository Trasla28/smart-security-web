export type UserRole = "admin" | "supervisor" | "agent" | "requester";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  is_archived: boolean;
  avatar_url: string | null;
  tenant_id: string;
}
