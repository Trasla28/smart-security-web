"use client";

import { useSession } from "next-auth/react";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { data: session, status } = useSession();

  if (status === "loading") return null;

  if (session?.user?.role !== "admin") {
    return (
      <div className="flex flex-col items-center justify-center min-h-64 text-center">
        <p className="text-4xl mb-4">🔒</p>
        <h2 className="text-lg font-semibold text-gray-800">Acceso denegado</h2>
        <p className="text-sm text-gray-500 mt-1">
          No tienes permisos para ver esta sección.
        </p>
      </div>
    );
  }

  return <>{children}</>;
}
