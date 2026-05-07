"use client";

import { Suspense, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { signIn } from "next-auth/react";

function GoogleCallbackContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    const token = searchParams.get("token");
    if (!token) {
      router.replace("/login?error=google_failed");
      return;
    }
    signIn("credentials", { google_token: token, redirect: false }).then((result) => {
      if (result?.error) {
        router.replace("/login?error=google_failed");
      } else {
        router.replace("/");
      }
    });
  }, [searchParams, router]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <p className="text-gray-500 text-sm">Iniciando sesión con Google...</p>
    </div>
  );
}

export default function GoogleCallbackPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-500 text-sm">Cargando...</p>
      </div>
    }>
      <GoogleCallbackContent />
    </Suspense>
  );
}
