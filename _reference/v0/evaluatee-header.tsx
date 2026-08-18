import { stages } from "@/lib/data"
import { cn } from "@/lib/utils"

const evaluatee = {
  name: "Eduardo Santos",
  role: "Engenheiro de Software Jr.",
  team: "Engenharia",
  initials: "ES",
  stage: "avaliacao-gestor",
}

export function EvaluateeHeader() {
  return (
    <section
      aria-label="Colaborador em avaliação"
      className="flex flex-col gap-4 rounded-xl border border-border bg-card p-5 sm:flex-row sm:items-center sm:justify-between"
    >
      <div className="flex items-center gap-4">
        <div className="flex size-12 shrink-0 items-center justify-center rounded-full bg-accent text-base font-semibold text-accent-foreground">
          {evaluatee.initials}
        </div>
        <div>
          <h2 className="text-base font-semibold tracking-tight text-card-foreground">
            {evaluatee.name}
          </h2>
          <p className="text-sm text-muted-foreground">
            {evaluatee.role} · {evaluatee.team}
          </p>
        </div>
      </div>

      <ol className="flex flex-wrap items-center gap-2">
        {stages.map((s) => (
          <li
            key={s.key}
            className={cn(
              "rounded-full px-2.5 py-1 text-xs font-medium",
              s.key === evaluatee.stage
                ? "bg-primary text-primary-foreground"
                : s.done
                  ? "bg-accent text-accent-foreground"
                  : "bg-secondary text-muted-foreground",
            )}
          >
            {s.label}
          </li>
        ))}
      </ol>
    </section>
  )
}
