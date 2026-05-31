import { CardShell } from "./card-shell"
import type { InferredSkillDetail } from "@/lib/api/types"

export function InferredSkills({ skills }: { skills: InferredSkillDetail[] }) {
  const sorted = [...skills].sort((a, b) => b.confidence - a.confidence).slice(0, 5)

  return (
    <CardShell title="Inferred Skills" sub="not on the résumé — derived from context">
      <div style={{ paddingTop: 4 }}>
        <div style={{ display: "flex", flexDirection: "column" }}>
          {sorted.map((s, i) => {
            const high = s.confidence >= 0.85
            const via = (s as { via?: string[] }).via ?? []

            return (
              <div key={s.name} style={{
                display: "flex", gap: 13, padding: "15px 0",
                boxShadow: i > 0 ? "0 -1px 0 var(--fk-line)" : "none",
              }}>
                {/* Check circle */}
                <div style={{
                  width: 22, height: 22, flexShrink: 0,
                  borderRadius: "50%",
                  border: high ? "none" : "1.8px solid var(--fk-line-2)",
                  background: high ? "var(--fk-blue)" : "transparent",
                  display: "grid", placeItems: "center",
                  marginTop: 1, color: "#fff",
                }}>
                  {high && (
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                      <path d="M5 12.5 10 17l9-10" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </div>

                <div style={{ flex: 1, minWidth: 0 }}>
                  {/* Name + confidence */}
                  <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
                    <span style={{ fontSize: 14.5, fontWeight: 600, color: "var(--fk-ink)" }}>{s.name}</span>
                    <span style={{
                      marginLeft: "auto", fontSize: 11.5, fontWeight: 700,
                      padding: "2px 9px", borderRadius: 999,
                      background: high ? "var(--fk-green-bg)" : "var(--fk-card-2)",
                      color: high ? "var(--fk-green)" : "var(--fk-ink-3)",
                    }}>
                      {Math.round(s.confidence * 100)}%
                    </span>
                  </div>

                  {s.reason && (
                    <div style={{ fontSize: 13, color: "var(--fk-ink-3)", lineHeight: 1.5, margin: "5px 0 9px" }}>
                      {s.reason}
                    </div>
                  )}

                  {/* Reasoning chain */}
                  <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 6 }}>
                    <span style={{ fontSize: 11, fontWeight: 600, color: "var(--fk-ink-4)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                      via
                    </span>
                    {via.map((v, vi) => (
                      <span key={v} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                        {vi > 0 && <span style={{ color: "var(--fk-ink-4)" }}>·</span>}
                        <span style={{
                          padding: "4px 10px", fontSize: 12, fontWeight: 500,
                          color: "var(--fk-ink-2)", background: "var(--fk-card-2)",
                          border: "1px solid var(--fk-line)", borderRadius: 8,
                        }}>{v}</span>
                      </span>
                    ))}
                    <span style={{ color: "var(--fk-ink-4)" }}>
                      <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
                        <path d="M5 12h13m0 0-5-5m5 5-5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </span>
                    <span style={{
                      padding: "4px 10px", fontSize: 12, fontWeight: 500,
                      color: "var(--fk-ink-3)", background: "transparent",
                      border: "1px dashed var(--fk-line-2)", borderRadius: 8,
                    }}>{s.name}</span>
                    {s.inferred_by && (
                      <span style={{
                        marginLeft: "auto", fontSize: 11, fontFamily: "var(--font-geist-mono,monospace)",
                        color: "var(--fk-ink-3)", background: "var(--fk-card-2)",
                        padding: "2px 7px", borderRadius: 6,
                      }}>{s.inferred_by}</span>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </CardShell>
  )
}
