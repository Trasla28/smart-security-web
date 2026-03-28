import type { DefaultSession } from "next-auth";

declare module "next-auth" {
  interface Session {
    access_token: string;
    user: {
      id: string;
      role: string;
      tenant_id: string;
    } & DefaultSession["user"];
  }
  interface User {
    access_token: string;
    role: string;
    tenant_id: string;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    access_token: string;
    role: string;
    tenant_id: string;
    user_id: string;
  }
}
