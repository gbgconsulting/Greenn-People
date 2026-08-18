"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  LayoutDashboard,
  Users,
  Target,
  ClipboardCheck,
  Grid3x3,
  CalendarRange,
  GaugeCircle,
  BarChart3,
  Settings,
  LifeBuoy,
} from "lucide-react"
import { cn } from "@/lib/utils"

const navGroups = [
  {
    label: "Colaborador",
    items: [
      { label: "Meu painel", icon: LayoutDashboard, href: "/colaborador" },
      { label: "Avaliação do ciclo", icon: ClipboardCheck, href: "/avaliacao" },
      { label: "Minha classificação", icon: Grid3x3, href: "/ninebox" },
    ],
  },
  {
    label: "Governança",
    items: [
      { label: "Ciclos", icon: CalendarRange, href: "/ciclos" },
      { label: "Painel admin", icon: BarChart3, href: "/painel" },
      { label: "Aderência", icon: GaugeCircle, href: "/aderencia" },
      { label: "Painel do gestor", icon: Users, href: "/" },
      { label: "Matriz de talentos", icon: Grid3x3, href: "/ninebox" },
    ],
  },
]

const footerNav = [
  { label: "Configurações", icon: Settings, href: "/" },
  { label: "Ajuda", icon: LifeBuoy, href: "/" },
]

export function Sidebar() {
  const pathname = usePathname()
  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar lg:flex">
      <div className="flex h-16 items-center gap-2.5 border-b border-sidebar-border px-6">
        <div className="flex size-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <Target className="size-4" aria-hidden="true" />
        </div>
        <span className="text-[15px] font-semibold tracking-tight text-sidebar-foreground">
          Ciclo
        </span>
      </div>

      <nav className="flex flex-1 flex-col gap-5 overflow-y-auto px-3 py-5" aria-label="Navegação principal">
        {navGroups.map((group) => (
          <div key={group.label} className="flex flex-col gap-1">
            <p className="px-3 pb-1 text-xs font-medium uppercase tracking-wider text-muted-foreground">
              {group.label}
            </p>
            {group.items.map((item, i) => {
              const active = item.href === pathname
              return (
                <Link
                  key={`${item.label}-${i}`}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
                  )}
                >
                  <item.icon className="size-[18px]" aria-hidden="true" />
                  {item.label}
                </Link>
              )
            })}
          </div>
        ))}
      </nav>

      <div className="flex flex-col gap-1 px-3 pb-4">
        {footerNav.map((item) => (
          <Link
            key={item.label}
            href={item.href}
            className="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-sidebar-accent/60 hover:text-sidebar-foreground"
          >
            <item.icon className="size-[18px]" aria-hidden="true" />
            {item.label}
          </Link>
        ))}
      </div>

      <div className="flex items-center gap-3 border-t border-sidebar-border px-4 py-3">
        <div className="flex size-9 items-center justify-center rounded-full bg-accent text-sm font-semibold text-accent-foreground">
          MR
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-sidebar-foreground">Marina Ribeiro</p>
          <p className="truncate text-xs text-muted-foreground">Gestora · Produto</p>
        </div>
      </div>
    </aside>
  )
}
