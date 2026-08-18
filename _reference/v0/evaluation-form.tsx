"use client"

import { useMemo, useState } from "react"
import { Check } from "lucide-react"
import { Button } from "@/components/ui/button"
import { RatingScale } from "@/components/evaluation/rating-scale"
import { competencies } from "@/lib/data"
import { cn } from "@/lib/utils"

const competencyHints: Record<string, string> = {
  Colaboração: "Trabalho em equipe, apoio aos pares e compartilhamento de conhecimento.",
  Comunicação: "Clareza, escuta ativa e alinhamento com stakeholders.",
  Autonomia: "Capacidade de conduzir entregas com independência e iniciativa.",
  "Foco no cliente": "Decisões orientadas ao valor entregue ao usuário final.",
  "Domínio técnico": "Profundidade e aplicação prática das competências da função.",
}

export function EvaluationForm() {
  const [scores, setScores] = useState<Record<string, number | null>>(() =>
    Object.fromEntries(competencies.map((c) => [c.name, null])),
  )
  const [notes, setNotes] = useState("")
  const [submitted, setSubmitted] = useState(false)

  const filled = Object.values(scores).filter((v) => v !== null).length
  const total = competencies.length
  const average = useMemo(() => {
    const vals = Object.values(scores).filter((v): v is number => v !== null)
    if (vals.length === 0) return null
    return (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1)
  }, [scores])

  const complete = filled === total && notes.trim().length > 0

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      {/* Formulário */}
      <div className="flex flex-col gap-6 lg:col-span-2">
        <section aria-label="Avaliação por competência" className="rounded-xl border border-border bg-card">
          <header className="border-b border-border px-5 py-4">
            <h2 className="text-sm font-semibold text-card-foreground">Avaliação por competência</h2>
            <p className="text-xs text-muted-foreground">
              Selecione a nota de 1 a 5 para cada competência
            </p>
          </header>

          <ul className="divide-y divide-border">
            {competencies.map((c) => (
              <li key={c.name} className="flex flex-col gap-3 px-5 py-4">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-card-foreground">{c.name}</p>
                    <span className="rounded-full bg-secondary px-2 py-0.5 font-mono text-[11px] tabular-nums text-secondary-foreground">
                      auto {c.self}
                    </span>
                  </div>
                  <p className="mt-0.5 text-xs text-muted-foreground text-pretty">
                    {competencyHints[c.name]}
                  </p>
                </div>
                <RatingScale
                  name={c.name}
                  value={scores[c.name]}
                  onChange={(v) => setScores((prev) => ({ ...prev, [c.name]: v }))}
                />
              </li>
            ))}
          </ul>
        </section>

        <section aria-label="Feedback qualitativo" className="rounded-xl border border-border bg-card p-5">
          <label htmlFor="feedback" className="text-sm font-semibold text-card-foreground">
            Feedback qualitativo
          </label>
          <p className="text-xs text-muted-foreground">
            Destaque pontos fortes e oportunidades de desenvolvimento para o próximo ciclo.
          </p>
          <textarea
            id="feedback"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={5}
            placeholder="Escreva o feedback do ciclo..."
            className="mt-3 w-full resize-y rounded-md border border-input bg-background px-3 py-2 text-sm leading-relaxed text-foreground outline-none transition-colors placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/30"
          />
        </section>
      </div>

      {/* Resumo */}
      <aside className="flex flex-col gap-4">
        <div className="sticky top-24 flex flex-col gap-4 rounded-xl border border-border bg-card p-5">
          <div>
            <h2 className="text-sm font-semibold text-card-foreground">Resumo da avaliação</h2>
            <p className="text-xs text-muted-foreground">Atualiza conforme você preenche</p>
          </div>

          <div className="flex items-end justify-between rounded-lg bg-secondary px-4 py-3">
            <div>
              <p className="text-xs text-secondary-foreground">Nota final</p>
              <p className="text-xs text-muted-foreground">média das competências</p>
            </div>
            <span className="font-mono text-3xl font-medium tabular-nums text-card-foreground">
              {average ?? "—"}
            </span>
          </div>

          <div>
            <div className="mb-1.5 flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Competências avaliadas</span>
              <span className="font-mono tabular-nums text-card-foreground">
                {filled}/{total}
              </span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${(filled / total) * 100}%` }}
              />
            </div>
          </div>

          <ul className="flex flex-col gap-1.5 text-xs">
            <li className={cn("flex items-center gap-2", filled === total ? "text-card-foreground" : "text-muted-foreground")}>
              <span className={cn("flex size-4 items-center justify-center rounded-full border", filled === total ? "border-primary bg-primary text-primary-foreground" : "border-border")}>
                {filled === total && <Check className="size-2.5" aria-hidden="true" />}
              </span>
              Todas as competências avaliadas
            </li>
            <li className={cn("flex items-center gap-2", notes.trim() ? "text-card-foreground" : "text-muted-foreground")}>
              <span className={cn("flex size-4 items-center justify-center rounded-full border", notes.trim() ? "border-primary bg-primary text-primary-foreground" : "border-border")}>
                {notes.trim() && <Check className="size-2.5" aria-hidden="true" />}
              </span>
              Feedback qualitativo preenchido
            </li>
          </ul>

          <div className="flex flex-col gap-2 border-t border-border pt-4">
            <Button disabled={!complete} onClick={() => setSubmitted(true)} className="w-full">
              {submitted ? "Avaliação enviada" : "Enviar avaliação"}
            </Button>
            <Button variant="ghost" className="w-full text-muted-foreground">
              Salvar rascunho
            </Button>
          </div>

          {submitted && (
            <p className="rounded-md bg-accent px-3 py-2 text-center text-xs font-medium text-accent-foreground">
              Avaliação registrada com sucesso.
            </p>
          )}
        </div>
      </aside>
    </div>
  )
}
