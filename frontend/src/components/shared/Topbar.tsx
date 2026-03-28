"use client";

import { signOut } from "next-auth/react";
import { useSession } from "next-auth/react";
import { LogOut, User } from "lucide-react";
import { NotificationBell } from "@/components/NotificationBell";
import { useWebSocket } from "@/hooks/useWebSocket";

export function Topbar() {
  const { data: session } = useSession();
  useWebSocket(session?.access_token ?? null);

  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6 fixed top-0 right-0 left-60 z-30">
      <div />
      <div className="flex items-center gap-3">
        <NotificationBell />
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <User className="w-4 h-4" />
          <span className="hidden sm:inline">{session?.user?.name}</span>
        </div>
        <button
          onClick={() => signOut({ callbackUrl: "/login" })}
          className="p-1.5 text-gray-400 hover:text-gray-700 rounded transition-colors"
          title="Cerrar sesión"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}
