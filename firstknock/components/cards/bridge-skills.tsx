import { CardShell } from "./card-shell"
import type { BridgeSkill } from "@/lib/api/types"

const NOTES: Record<string, string> = {
  FastAPI:    "Connects backend, agent and data clusters. Your strongest hub.",
  Python:     "Underlies almost every project · 4 clusters touched.",
  Docker:     "Joins shipping flow across web + agent stacks.",
  TypeScript: "Bridges frontend work into LangGraph orchestration UIs.",
}

const STRIPE = "repeating-linear-gradient(135deg, rgba(255,255,255,.28) 0 2px, transparent 2px 6px)"

export function BridgeSkills({ bridgeSkills }: { bridgeSkills: BridgeSkill[] | null }) {
  if (!bridgeSkills) {
    return (
      <CardShell title="Bridge Skills" sub="MAGE betweenness centrality" id="skills">
        <p style={{ fontSize: 14, color: "var(--fk-ink-3)" }}>
          MAGE not installed — community analysis unavailable.
        </p>
      </CardShell>
    )
  }

  return (
    <CardShell title="Bridge Skills" sub="MAGE betweenness centrality" id="skills">
      <div style={{ display: "flex", flexDirection: "column" }}>
        {bridgeSkills.map((b, i) => (
          <div key={b.name} style={{
            display: "flex", gap: 13, alignItems: "flex-start", padding: "13px 0",
            boxShadow: i > 0 ? "0 -1px 0 var(--fk-line)" : "none",
          }}>
            {/* Rank badge */}
            <div style={{
              width: 28, height: 28, borderRadius: 8,
              background: "var(--fk-card-2)", border: "1px solid var(--fk-line)",
              color: "var(--fk-ink-3)", display: "grid", placeItems: "center",
              fontSize: 12, fontWeight: 700, flexShrink: 0,
            }}>
              {i + 1}
            </div>

            <div style={{ flex: 1, minWidth: 0 }}>
              {/* Name + cat + centrality */}
              <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 7 }}>
                <span style={{ fontSize: 14, fontWeight: 600, color: "var(--fk-ink)" }}>{b.name}</span>
                <span style={{ fontSize: 12, color: "var(--fk-ink-4)" }}>{b.category}</span>
                <span style={{ marginLeft: "auto", fontSize: 14, fontWeight: 700, color: "var(--fk-blue)" }}>
                  {b.centrality.toFixed(2)}
                </span>
              </div>

              {/* Bar */}
              <div style={{ height: 8, borderRadius: 999, background: "var(--fk-well)", overflow: "hidden" }}>
                <div style={{
                  height: "100%", borderRadius: 999,
                  width: `${b.centrality * 100}%`,
                  backgroundColor: "var(--fk-blue)",
                  backgroundImage: STRIPE,
                  backgroundSize: "9px 9px",
                }} />
              </div>

              {NOTES[b.name] && (
                <div style={{ marginTop: 6, fontSize: 12.5, color: "var(--fk-ink-3)", lineHeight: 1.4 }}>
                  {NOTES[b.name]}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </CardShell>
  )
}
