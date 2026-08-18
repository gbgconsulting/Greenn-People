import { AlertTriangle, ArrowRight } from "lucide-react"
import { attention } from "@/lib/data"
import { cn } from "@/lib/utils"

export function AttentionPanel() {
  return (
    <section
      aria-label="Pendências que precisam de atenção"
      className="flex flex-col rounded-xl border border-border bg-card p-5"
    >
      <div className="flex items-center gap-2">
        <AlertTriangle className="size-4 text-destructive" aria-hidden="true" />
        <h2 className="text-sm font-semibold text-card-foreground">Precisa de atenção</h2>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">
        {attention.length} pendências antes do encerramento
      </p>

      <ul className="mt-4 flex flex-col gap-2">
        {attention.map((item) => (
          <li key={item.id}>
            <a
              href="#"
              className="group flex items-center gap-3 rounded-lg border border-border bg-background p-3 transition-colors hover:border-ring/40"
            >
              <span
                className={cn(
                  "mt-0.5 size-2 shrink-0 rounded-full",
                  item.severity === "alta" ? "bg-destructive" : "bg-chart-2",
                )}
                aria-hidden="true"
              />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-card-foreground">{item.name}</p>
                <p className="truncate text-xs text-muted-foreground">{item.reason}</p>
              </div>
              <ArrowRight
                className="size-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5"
                aria-hidden="true"
              />
            </a>
          </li>
        ))}
      </ul>

      <button className="mt-4 rounded-md border border-border py-2 text-sm font-medium text-card-foreground transition-colors hover:bg-muted">
        Enviar lembretes
      </button>
    </section>
  )
}
