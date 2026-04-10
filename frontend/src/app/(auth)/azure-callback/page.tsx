"use client";

import { Suspense, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { signIn } from "next-auth/react";

function AzureCallbackContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    const token = searchParams.get("token");
    if (!token) {
      router.replace("/login?error=azure_failed");
      return;
    }
    signIn("credentials", { azure_token: token, redirect: false }).then((result) => {
      if (result?.error) {
        router.replace("/login?error=azure_failed");
      } else {
        router.replace("/");
      }
    });
  }, [searchParams, router]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <p className="text-gray-500 text-sm">Iniciando sesión con Microsoft...</p>
    </div>
  );
}

export default function AzureCallbackPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-500 text-sm">Cargando...</p>
      </div>
    }>
      <AzureCallbackContent />
    </Suspense>
  );
}
