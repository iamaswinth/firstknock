import type { BridgeSkill } from "@/lib/api/types"

interface InsightProps { bridgeSkills: BridgeSkill[] | null }

export function Insight({ bridgeSkills }: InsightProps) {
  const top = bridgeSkills?.[0]

  return (
    <section style={{
      position: "relative", overflow: "hidden",
      border: "none", color: "#fff",
      background: "radial-gradient(120% 140% at 85% 10%, #f7a23f 0%, #ed6aa6 32%, #7f7be0 60%, #2f5fd0 80%, #14245e 100%)",
      borderRadius: "var(--fk-radius-lg)",
      boxShadow: "var(--fk-shadow)",
      flex: "1 1 auto", width: "100%",
      display: "flex", flexDirection: "column",
    }}>
      <div style={{ padding: 22, display: "flex", flexDirection: "column", flex: 1 }}>
        {/* Insight tag */}
        <div style={{ alignSelf: "flex-start" }}>
          <span style={{
            display: "inline-flex", alignItems: "center", gap: 6,
            padding: "5px 11px", borderRadius: 999,
            fontSize: 12, fontWeight: 600, color: "#fff",
            background: "rgba(255,255,255,0.18)", backdropFilter: "blur(4px)",
            border: "1px solid rgba(255,255,255,0.25)",
          }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 3l1.6 5.4L19 10l-5.4 1.6L12 17l-1.6-5.4L5 10l5.4-1.6L12 3Z" />
            </svg>
            Insight
          </span>
        </div>

        {top ? (
          <>
            <div style={{ fontSize: 64, fontWeight: 700, letterSpacing: "-0.04em", lineHeight: 1, marginTop: "auto" }}>
              {Math.round(top.centrality * 100)}%
            </div>
            <div style={{ fontSize: 18, fontWeight: 600, marginTop: 14, lineHeight: 1.3 }}>
              {top.name} is your strongest bridge skill.
            </div>
            <div style={{ fontSize: 13, lineHeight: 1.5, marginTop: 8, color: "rgba(255,255,255,0.85)" }}>
              It links your skill communities — highest betweenness centrality in your graph.
            </div>
          </>
        ) : (
          <p style={{ marginTop: "auto", fontSize: 13, color: "rgba(255,255,255,0.7)" }}>
            Graph analysis pending. Re-ingest to generate insights.
          </p>
        )}
      </div>
    </section>
  )
}
