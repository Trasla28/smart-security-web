"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { signIn } from "next-auth/react";

function AzureCallbackContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = searchParams.get("token");
    if (!token) {
      setError("No se recibió el token de Microsoft.");
      return;
    }

    signIn("credentials", {
      azure_token: token,
      tenant_slug: "smart-security",
      redirect: false,
    }).then((result) => {
      if (result?.error) {
        setError("No se pudo completar el inicio de sesión con Microsoft.");
      } else {
        router.push("/");
      }
    });
  }, [searchParams, router]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full p-8 bg-white rounded-xl shadow-sm border border-gray-100 text-center space-y-4">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-red-100">
            <span className="text-red-600 font-bold text-lg">!</span>
          </div>
          <p className="text-sm text-red-700">{error}</p>
          <button
            onClick={() => router.push("/login")}
            className="px-4 py-2 bg-[#1a2c4e] text-white rounded-lg text-sm font-medium hover:bg-[#243d6a]"
          >
            Volver al login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center space-y-3">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-[#1a2c4e] animate-pulse">
          <span className="text-white font-bold text-lg">SS</span>
        </div>
        <p className="text-sm text-gray-500">Verificando autenticación con Microsoft...</p>
      </div>
    </div>
  );
}

export default function AzureCallbackPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-sm text-gray-500">Cargando...</p>
      </div>
    }>
      <AzureCallbackContent />
    </Suspense>
  );
}
