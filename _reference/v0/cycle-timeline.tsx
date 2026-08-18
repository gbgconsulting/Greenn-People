import { Check } from "lucide-react"
import { cycle, stages } from "@/lib/data"
import { cn } from "@/lib/utils"

export function CycleTimeline() {
  return (
    <section
      aria-label="Progresso do ciclo de avaliação"
      className="rounded-xl border border-border bg-card p-5"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-card-foreground">Ciclo de avaliação</h2>
          <p className="text-xs text-muted-foreground">
            {cycle.daysLeft} dias restantes para o encerramento
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-mono text-2xl font-medium tabular-nums text-card-foreground">
            {cycle.progress}%
          </span>
          <span className="text-xs text-muted-foreground">concluído</span>
        </div>
      </div>

      <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary transition-all"
          style={{ width: `${cycle.progress}%` }}
        />
      </div>

      <ol className="mt-6 grid gap-4 sm:grid-cols-5">
        {stages.map((stage, i) => (
          <li key={stage.key} className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "flex size-6 shrink-0 items-center justify-center rounded-full border text-xs font-medium",
                  stage.done && "border-primary bg-primary text-primary-foreground",
                  stage.current && "border-primary bg-accent text-accent-foreground",
                  !stage.done && !stage.current && "border-border bg-card text-muted-foreground",
                )}
              >
                {stage.done ? <Check className="size-3.5" aria-hidden="true" /> : i + 1}
              </span>
              {i < stages.length - 1 && (
                <span
                  className={cn("h-px flex-1", stage.done ? "bg-primary" : "bg-border")}
                  aria-hidden="true"
                />
              )}
            </div>
            <span
              className={cn(
                "text-xs font-medium leading-tight text-pretty",
                stage.current ? "text-card-foreground" : "text-muted-foreground",
              )}
            >
              {stage.label}
            </span>
          </li>
        ))}
      </ol>
    </section>
  )
}
