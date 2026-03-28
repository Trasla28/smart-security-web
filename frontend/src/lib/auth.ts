import type { AuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";

const API_URL = process.env.API_URL ?? "";

export const authOptions: AuthOptions = {
  providers: [
    CredentialsProvider({
      id: "credentials",
      name: "Email y contraseña",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Contraseña", type: "password" },
        tenant_slug: { label: "Tenant", type: "text" },
        azure_token: { label: "Azure Token", type: "text" },
      },
      async authorize(credentials) {
        if (!credentials) return null;

        let access_token: string;

        if (credentials.azure_token) {
          access_token = credentials.azure_token;
        } else {
          const loginRes = await fetch(`${API_URL}/api/v1/auth/login`, {
            method: "POST",
            body: JSON.stringify({
              email: credentials.email,
              password: credentials.password,
              tenant_slug: credentials.tenant_slug,
            }),
            headers: { "Content-Type": "application/json" },
          });
          if (!loginRes.ok) return null;
          const data = await loginRes.json();
          access_token = data.access_token;
        }

        const meRes = await fetch(`${API_URL}/api/v1/auth/me`, {
          headers: { Authorization: `Bearer ${access_token}` },
        });
        if (!meRes.ok) return null;
        const user = await meRes.json();

        return {
          id: user.id,
          name: user.full_name,
          email: user.email,
          access_token,
          role: user.role,
          tenant_id: user.tenant_id,
        };
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.access_token = user.access_token;
        token.role = user.role;
        token.tenant_id = user.tenant_id;
        token.user_id = user.id;
      }
      return token;
    },
    async session({ session, token }) {
      session.access_token = token.access_token;
      session.user.id = token.user_id;
      session.user.role = token.role;
      session.user.tenant_id = token.tenant_id;
      return session;
    },
  },
  pages: {
    signIn: "/login",
    error: "/login",
  },
  session: {
    strategy: "jwt",
    maxAge: 30 * 24 * 60 * 60,
  },
};
