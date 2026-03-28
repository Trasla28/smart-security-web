"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession } from "next-auth/react";
import {
  LayoutDashboard,
  Ticket,
  Plus,
  BarChart2,
  Users,
  MapPin,
  Tag,
  Clock,
  RefreshCw,
  Settings,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  roles?: string[];
}

const mainNav: NavItem[] = [
  { label: "Dashboard", href: "/", icon: <LayoutDashboard className="w-4 h-4" /> },
  { label: "Tickets", href: "/tickets", icon: <Ticket className="w-4 h-4" /> },
  { label: "Nueva solicitud", href: "/tickets/new", icon: <Plus className="w-4 h-4" /> },
  { label: "Reportes", href: "/reports", icon: <BarChart2 className="w-4 h-4" />, roles: ["admin", "supervisor"] },
];

const adminNav: NavItem[] = [
  { label: "Usuarios", href: "/admin/users", icon: <Users className="w-4 h-4" /> },
  { label: "Áreas", href: "/admin/areas", icon: <MapPin className="w-4 h-4" /> },
  { label: "Categorías", href: "/admin/categories", icon: <Tag className="w-4 h-4" /> },
  { label: "SLAs", href: "/admin/slas", icon: <Clock className="w-4 h-4" /> },
  { label: "Recurrentes", href: "/admin/recurring", icon: <RefreshCw className="w-4 h-4" /> },
  { label: "Configuración", href: "/admin/config", icon: <Settings className="w-4 h-4" /> },
];

export function Sidebar() {
  const pathname = usePathname();
  const { data: session } = useSession();
  const role = session?.user?.role ?? "requester";
  const [adminOpen, setAdminOpen] = useState(pathname.startsWith("/admin"));

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <aside className="fixed inset-y-0 left-0 w-60 bg-[#1a2c4e] flex flex-col z-40">
      <div className="px-5 py-5 border-b border-white/10">
        <span className="text-white font-bold text-lg tracking-tight">SS Tickets</span>
        <p className="text-white/50 text-xs mt-0.5">Smart Security</p>
      </div>

      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-0.5">
        {mainNav
          .filter((item) => !item.roles || item.roles.includes(role))
          .map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
                isActive(item.href)
                  ? "bg-white/15 text-white font-medium"
                  : "text-white/70 hover:text-white hover:bg-white/10"
              )}
            >
              {item.icon}
              {item.label}
            </Link>
          ))}

        {role === "admin" && (
          <div className="pt-2">
            <button
              onClick={() => setAdminOpen((v) => !v)}
              className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/10 transition-colors"
            >
              <span className="flex items-center gap-3">
                <Settings className="w-4 h-4" />
                Administración
              </span>
              {adminOpen ? (
                <ChevronDown className="w-3 h-3" />
              ) : (
                <ChevronRight className="w-3 h-3" />
              )}
            </button>
            {adminOpen && (
              <div className="ml-4 mt-0.5 space-y-0.5 border-l border-white/10 pl-3">
                {adminNav.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex items-center gap-2 px-2 py-1.5 rounded-md text-xs transition-colors",
                      isActive(item.href)
                        ? "bg-white/15 text-white font-medium"
                        : "text-white/60 hover:text-white hover:bg-white/10"
                    )}
                  >
                    {item.icon}
                    {item.label}
                  </Link>
                ))}
              </div>
            )}
          </div>
        )}
      </nav>

      <div className="px-4 py-3 border-t border-white/10">
        <p className="text-white/60 text-xs truncate">{session?.user?.name}</p>
        <p className="text-white/40 text-xs capitalize">{role}</p>
      </div>
    </aside>
  );
}
