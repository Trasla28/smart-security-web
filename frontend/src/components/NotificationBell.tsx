"use client";

import { useEffect, useRef, useState } from "react";
import { Bell } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { es } from "date-fns/locale";
import { useRouter } from "next/navigation";

import api from "@/lib/api";
import { useNotificationStore } from "@/store/notificationStore";
import type { Notification } from "@/types/notification";

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  const { notifications, unreadCount, setNotifications, markOneRead, markAllRead } =
    useNotificationStore();

  // Load initial notifications on mount
  useEffect(() => {
    api
      .get<{ items: Notification[] }>("/notifications?size=20")
      .then((res) => setNotifications(res.data.items))
      .catch(() => {});
  }, [setNotifications]);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  async function handleMarkAllRead() {
    await api.post("/notifications/read-all").catch(() => {});
    markAllRead();
  }

  async function handleMarkOneRead(id: string) {
    await api.patch(`/notifications/${id}/read`).catch(() => {});
    markOneRead(id);
  }

  async function handleNotificationClick(n: Notification) {
    if (!n.is_read) await handleMarkOneRead(n.id);
    if (n.ticket_id) {
      setOpen(false);
      router.push(`/tickets/${n.ticket_id}`);
    }
  }

  return (
    <div ref={dropdownRef} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="relative p-2 rounded-full hover:bg-gray-100 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
        aria-label="Notificaciones"
      >
        <Bell className="w-5 h-5 text-gray-600" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white leading-none">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-lg border border-gray-100 z-50">
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
            <span className="font-semibold text-sm text-gray-800">Notificaciones</span>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="text-xs text-blue-600 hover:underline"
              >
                Marcar todas como leídas
              </button>
            )}
          </div>

          <ul className="max-h-80 overflow-y-auto divide-y divide-gray-50">
            {notifications.length === 0 && (
              <li className="px-4 py-6 text-center text-sm text-gray-400">
                Sin notificaciones
              </li>
            )}
            {notifications.map((n) => (
              <li
                key={n.id}
                onClick={() => handleNotificationClick(n)}
                className={`px-4 py-3 cursor-pointer hover:bg-gray-50 transition-colors ${
                  !n.is_read ? "bg-blue-50" : ""
                }`}
              >
                <div className="flex items-start gap-2">
                  {!n.is_read && (
                    <span className="mt-1.5 flex-shrink-0 h-2 w-2 rounded-full bg-blue-500" />
                  )}
                  <div className={!n.is_read ? "" : "pl-4"}>
                    <p className="text-sm font-medium text-gray-800 leading-snug">{n.title}</p>
                    {n.body && (
                      <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{n.body}</p>
                    )}
                    <p className="text-xs text-gray-400 mt-1">
                      {formatDistanceToNow(new Date(n.created_at), {
                        addSuffix: true,
                        locale: es,
                      })}
                    </p>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
