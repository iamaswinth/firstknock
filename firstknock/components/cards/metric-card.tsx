import { CardShell } from "./card-shell"
import { DotMatrix } from "@/components/shared/dot-matrix"

interface MetricCardProps {
  title: string
  value: string
  peakLabel: string
  peak: string
  delta: string
  color: "green" | "blue"
  sub: string
}

export function MetricCard({ title, value, peakLabel, peak, delta, color, sub }: MetricCardProps) {
  const deltaColor = color === "green" ? "var(--fk-green)" : "var(--fk-blue)"

  return (
    <CardShell title={title}>
      <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
        {/* Left: big number */}
        <div style={{ fontSize: 44, fontWeight: 700, letterSpacing: "-0.035em", lineHeight: 1, color: "var(--fk-ink)" }}>
          {value}
        </div>

        {/* Center: peak tag + dot matrix */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 16, padding: "4px 0" }}>
          <span style={{
            display: "inline-flex", alignItems: "center", gap: 5,
            padding: "5px 11px", borderRadius: 999,
            fontSize: 13, fontWeight: 600, color: "var(--fk-ink-2)",
            background: "var(--fk-card)", boxShadow: "var(--fk-shadow-sm)", border: "1px solid var(--fk-line)",
          }}>
            {peakLabel} <b style={{ color: "var(--fk-ink)" }}>{peak}</b>
          </span>
          <DotMatrix color={color} peakCol={6} />
        </div>

        {/* Right: sub + delta */}
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 13, color: "var(--fk-ink-3)" }}>{sub}</div>
          <div style={{ fontSize: 18, fontWeight: 700, marginTop: 2, color: deltaColor }}>{delta}</div>
        </div>
      </div>
    </CardShell>
  )
}
