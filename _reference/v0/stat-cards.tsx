import { ArrowUpRight, ArrowDownRight } from "lucide-react"
import { kpis } from "@/lib/data"
import { cn } from "@/lib/utils"

export function StatCards() {
  return (
    <section aria-label="Indicadores do ciclo" className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {kpis.map((kpi) => {
        const up = kpi.trend === "up"
        const Icon = up ? ArrowUpRight : ArrowDownRight
        return (
          <div
            key={kpi.label}
            className="rounded-xl border border-border bg-card p-5 transition-colors hover:border-ring/40"
          >
            <p className="text-sm text-muted-foreground">{kpi.label}</p>
            <div className="mt-3 flex items-end justify-between gap-2">
              <span className="font-mono text-3xl font-medium tracking-tight text-card-foreground tabular-nums">
                {kpi.value}
              </span>
              <span
                className={cn(
                  "mb-1 inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-xs font-medium",
                  up ? "bg-accent text-accent-foreground" : "bg-destructive/10 text-destructive",
                )}
              >
                <Icon className="size-3" aria-hidden="true" />
                {kpi.delta}
              </span>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">{kpi.hint}</p>
          </div>
        )
      })}
    </section>
  )
}
