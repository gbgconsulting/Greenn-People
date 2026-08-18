"use client"

import { cn } from "@/lib/utils"

type RatingScaleProps = {
  name: string
  value: number | null
  onChange: (value: number) => void
}

const labels = ["Abaixo", "Em desenv.", "Atende", "Supera", "Referência"]

export function RatingScale({ name, value, onChange }: RatingScaleProps) {
  return (
    <div
      role="radiogroup"
      aria-label={`Nota para ${name}`}
      className="flex flex-wrap gap-2"
    >
      {[1, 2, 3, 4, 5].map((n) => {
        const active = value === n
        return (
          <button
            key={n}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(n)}
            className={cn(
              "flex min-w-16 flex-1 flex-col items-center gap-1 rounded-lg border px-2 py-2 text-center transition-colors",
              active
                ? "border-primary bg-accent text-accent-foreground"
                : "border-border bg-card text-muted-foreground hover:border-ring/50 hover:text-foreground",
            )}
          >
            <span className="font-mono text-sm font-semibold tabular-nums">{n}</span>
            <span className="text-[11px] leading-tight text-pretty">{labels[n - 1]}</span>
          </button>
        )
      })}
    </div>
  )
}
