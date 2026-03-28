"use client";

import { useEffect, useRef, useCallback } from "react";
import type { Notification } from "@/types/notification";
import { useNotificationStore } from "@/store/notificationStore";

const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL ?? "";
const MAX_RETRIES = 8;
const BASE_DELAY_MS = 1000;

export function useWebSocket(token: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmountedRef = useRef(false);

  const addNotification = useNotificationStore((s) => s.addNotification);

  const connect = useCallback(() => {
    if (!token || unmountedRef.current) return;

    const url = `${WS_BASE_URL}/api/v1/notifications/ws?token=${token}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data as string);
        // Ignore heartbeat pings
        if (data.type === "ping") return;
        addNotification(data as Notification);
      } catch {
        // Malformed message — ignore
      }
    };

    ws.onclose = () => {
      if (unmountedRef.current) return;
      const retries = retriesRef.current;
      if (retries >= MAX_RETRIES) return;

      // Exponential backoff: 1s, 2s, 4s, 8s … capped at 30s
      const delay = Math.min(BASE_DELAY_MS * 2 ** retries, 30_000);
      retriesRef.current += 1;
      timeoutRef.current = setTimeout(connect, delay);
    };

    ws.onerror = () => {
      ws.close();
    };

    ws.onopen = () => {
      retriesRef.current = 0;
    };
  }, [token, addNotification]);

  useEffect(() => {
    unmountedRef.current = false;
    connect();

    return () => {
      unmountedRef.current = true;
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      wsRef.current?.close();
    };
  }, [connect]);
}
