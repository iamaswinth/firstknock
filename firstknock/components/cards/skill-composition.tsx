import { ChevronUp } from "lucide-react"
import { CardShell } from "./card-shell"
import type { SkillsResponse } from "@/lib/api/types"

const FILL_GRADIENT = (color: string) =>
  `repeating-linear-gradient(135deg, rgba(255,255,255,.28) 0 2px, transparent 2px 6px)`

interface SkillCompositionProps { skills: SkillsResponse }

export function SkillComposition({ skills }: SkillCompositionProps) {
  const explicit = skills.explicit
  const inferred = skills.inferred
  const total = skills.total
  const inferredCount = inferred.length
  const communities = new Set(
    [...explicit, ...inferred].map((s) => (s as { community_id?: number }).community_id).filter(Boolean)
  ).size

  const cats = [
    { label: "Frameworks",   n: explicit.filter((s) => s.category === "framework").length, color: "var(--fk-green)", cls: "green" },
    { label: "Languages",    n: explicit.filter((s) => s.category === "language").length,  color: "var(--fk-blue)",  cls: "blue" },
    { label: "Tools & infra",n: explicit.filter((s) => !["framework","language"].includes(s.category)).length, color: "var(--fk-pink)", cls: "pink" },
  ]
  const max = Math.max(...cats.map((c) => c.n), 1)

  return (
    <CardShell title="Skill Composition">
      {/* Score row */}
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <div style={{ fontSize: 52, fontWeight: 700, letterSpacing: "-0.04em", lineHeight: 1, color: "var(--fk-ink)" }}>
          {total}
        </div>
        <span style={{
          display: "inline-flex", alignItems: "center", gap: 4,
          height: 26, padding: "0 10px", borderRadius: 999,
          fontSize: 14, fontWeight: 600, color: "var(--fk-green)",
          background: "var(--fk-card)", boxShadow: "var(--fk-shadow-sm)", border: "1px solid var(--fk-line)",
        }}>
          <ChevronUp size={12} strokeWidth={2.2} />
          {inferredCount} inferred
        </span>
      </div>

      <div style={{ fontSize: 14, color: "var(--fk-ink-3)", marginTop: 6 }}>
        {explicit.length} explicit · {inferredCount} inferred across {communities || 4} communities
      </div>

      {/* Bars */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16, marginTop: 22 }}>
        {cats.map((c) => (
          <div key={c.label} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
              <span style={{ fontSize: 14, color: "var(--fk-ink-2)", fontWeight: 500 }}>{c.label}</span>
              <span style={{ fontSize: 14, fontWeight: 700, color: "var(--fk-ink)" }}>{c.n}</span>
            </div>
            <div style={{ height: 12, borderRadius: 999, background: "var(--fk-well)", overflow: "hidden" }}>
              <div style={{
                height: "100%",
                borderRadius: 999,
                width: `${38 + (c.n / max) * 62}%`,
                backgroundColor: c.color,
                backgroundImage: FILL_GRADIENT(c.color),
                backgroundSize: "9px 9px",
              }} />
            </div>
          </div>
        ))}
      </div>
    </CardShell>
  )
}
