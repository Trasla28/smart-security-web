"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";

const schema = z.object({
  email: z.string().email("Email inválido"),
  password: z.string().min(1, "Contraseña requerida"),
  tenant_slug: z.string().min(1, "Tenant requerido"),
});

type FormData = z.infer<typeof schema>;

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [azureLoading, setAzureLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { tenant_slug: "smart-security" },
  });

  async function onSubmit(data: FormData) {
    setError(null);
    const result = await signIn("credentials", {
      ...data,
      redirect: false,
    });
    if (result?.error) {
      setError("Credenciales inválidas. Verifica tu email y contraseña.");
    } else {
      router.push("/");
    }
  }

  async function handleAzureLogin() {
    setAzureLoading(true);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/login/azure`
      );
      const data = await res.json();
      window.location.href = data.auth_url;
    } catch {
      setError("No se pudo iniciar el flujo de Azure AD.");
      setAzureLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-6 p-8 bg-white rounded-xl shadow-sm border border-gray-100">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-[#1a2c4e] mb-4">
            <span className="text-white font-bold text-lg">SS</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Smart Security Tickets</h1>
          <p className="text-sm text-gray-500 mt-1">Sistema de gestión de solicitudes</p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              {...register("email")}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2c4e] focus:border-transparent"
              placeholder="tu@empresa.com"
            />
            {errors.email && (
              <p className="text-xs text-red-600 mt-1">{errors.email.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Contraseña</label>
            <input
              type="password"
              {...register("password")}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2c4e] focus:border-transparent"
              placeholder="••••••••"
            />
            {errors.password && (
              <p className="text-xs text-red-600 mt-1">{errors.password.message}</p>
            )}
          </div>

          <input type="hidden" {...register("tenant_slug")} />

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-2.5 bg-[#1a2c4e] text-white rounded-lg text-sm font-medium hover:bg-[#243d6a] disabled:opacity-60 transition-colors"
          >
            {isSubmitting ? "Ingresando..." : "Ingresar"}
          </button>
        </form>

        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-200" />
          </div>
          <div className="relative flex justify-center text-xs">
            <span className="px-2 bg-white text-gray-400">o continúa con</span>
          </div>
        </div>

        <button
          type="button"
          onClick={handleAzureLogin}
          disabled={azureLoading}
          className="w-full py-2.5 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-60 transition-colors flex items-center justify-center gap-2"
        >
          <svg className="w-4 h-4" viewBox="0 0 21 21" fill="none">
            <rect x="1" y="1" width="9" height="9" fill="#f25022" />
            <rect x="11" y="1" width="9" height="9" fill="#7fba00" />
            <rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
            <rect x="11" y="11" width="9" height="9" fill="#ffb900" />
          </svg>
          {azureLoading ? "Redirigiendo..." : "Ingresar con Microsoft"}
        </button>
      </div>
    </div>
  );
}
