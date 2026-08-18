const distribution = [
  { band: "4.5 – 5.0", label: "Excede", count: 6 },
  { band: "3.5 – 4.4", label: "Atende plenamente", count: 19 },
  { band: "2.5 – 3.4", label: "Atende", count: 9 },
  { band: "0.0 – 2.4", label: "Abaixo", count: 2 },
]

const total = distribution.reduce((acc, d) => acc + d.count, 0)
const max = Math.max(...distribution.map((d) => d.count))

export function ScoreDistribution() {
  return (
    <section
      aria-label="Distribuição de notas do time"
      className="rounded-xl border border-border bg-card p-5"
    >
      <h2 className="text-sm font-semibold text-card-foreground">Distribuição de notas</h2>
      <p className="mt-1 text-xs text-muted-foreground">
        {total} avaliações consolidadas até agora
      </p>

      <div className="mt-5 flex flex-col gap-4">
        {distribution.map((d) => (
          <div key={d.band}>
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-sm text-card-foreground">{d.label}</span>
              <span className="font-mono text-xs tabular-nums text-muted-foreground">
                {d.band}
              </span>
            </div>
            <div className="mt-1.5 flex items-center gap-3">
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary/85"
                  style={{ width: `${(d.count / max) * 100}%` }}
                />
              </div>
              <span className="w-6 text-right font-mono text-sm font-medium tabular-nums text-card-foreground">
                {d.count}
              </span>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
