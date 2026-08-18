import { collaborators, type PdiStatus, type EvalStage } from "@/lib/data"
import { cn } from "@/lib/utils"

const pdiLabel: Record<PdiStatus, string> = {
  concluido: "Concluído",
  "em-dia": "Em dia",
  atrasado: "Atrasado",
  "nao-iniciado": "Não iniciado",
}

const pdiStyle: Record<PdiStatus, string> = {
  concluido: "bg-accent text-accent-foreground",
  "em-dia": "bg-secondary text-secondary-foreground",
  atrasado: "bg-destructive/10 text-destructive",
  "nao-iniciado": "bg-muted text-muted-foreground",
}

const stageLabel: Record<EvalStage, string> = {
  "auto-avaliacao": "Autoavaliação",
  "avaliacao-gestor": "Avaliação do gestor",
  calibracao: "Calibração",
  feedback: "Feedback",
  concluido: "Encerrado",
}

export function TeamTable() {
  return (
    <section
      aria-label="Colaboradores no ciclo"
      className="overflow-hidden rounded-xl border border-border bg-card"
    >
      <div className="flex items-center justify-between gap-3 border-b border-border px-5 py-4">
        <div>
          <h2 className="text-sm font-semibold text-card-foreground">Colaboradores</h2>
          <p className="text-xs text-muted-foreground">Acompanhamento individual do ciclo e PDI</p>
        </div>
        <button className="rounded-md px-2 py-1 text-xs font-medium text-primary transition-colors hover:bg-accent">
          Ver todos
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
              <th scope="col" className="px-5 py-3 font-medium">Colaborador</th>
              <th scope="col" className="px-5 py-3 font-medium">Etapa</th>
              <th scope="col" className="px-5 py-3 font-medium">PDI</th>
              <th scope="col" className="px-5 py-3 font-medium">Status</th>
              <th scope="col" className="px-5 py-3 text-right font-medium">Nota</th>
            </tr>
          </thead>
          <tbody>
            {collaborators.map((c) => (
              <tr
                key={c.id}
                className="border-b border-border last:border-0 transition-colors hover:bg-muted/50"
              >
                <td className="px-5 py-3.5">
                  <div className="flex items-center gap-3">
                    <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-secondary text-xs font-semibold text-secondary-foreground">
                      {c.initials}
                    </span>
                    <div className="min-w-0">
                      <p className="truncate font-medium text-card-foreground">{c.name}</p>
                      <p className="truncate text-xs text-muted-foreground">{c.role}</p>
                    </div>
                  </div>
                </td>
                <td className="px-5 py-3.5 text-muted-foreground">{stageLabel[c.stage]}</td>
                <td className="px-5 py-3.5">
                  <div className="flex items-center gap-2.5">
                    <div className="h-1.5 w-20 overflow-hidden rounded-full bg-muted">
                      <div
                        className={cn(
                          "h-full rounded-full",
                          c.pdiStatus === "atrasado" ? "bg-destructive/70" : "bg-primary",
                        )}
                        style={{ width: `${c.pdiProgress}%` }}
                      />
                    </div>
                    <span className="font-mono text-xs tabular-nums text-muted-foreground">
                      {c.pdiProgress}%
                    </span>
                  </div>
                </td>
                <td className="px-5 py-3.5">
                  <span
                    className={cn(
                      "inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium",
                      pdiStyle[c.pdiStatus],
                    )}
                  >
                    {pdiLabel[c.pdiStatus]}
                  </span>
                </td>
                <td className="px-5 py-3.5 text-right">
                  <span className="font-mono text-sm font-medium tabular-nums text-card-foreground">
                    {c.score !== null ? c.score.toFixed(1) : "—"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
