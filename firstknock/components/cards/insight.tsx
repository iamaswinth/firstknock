import { Sparkles } from "lucide-react"
import type { BridgeSkill, RoleMatch } from "@/lib/api/types"

interface InsightProps {
  bridgeSkills: BridgeSkill[] | null
  roles: RoleMatch[] | null
}

export function Insight({ bridgeSkills, roles }: InsightProps) {
  const top = bridgeSkills?.[0]
  const topRoles = roles?.slice(0, 3) ?? []

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
      <div style={{ padding: 22, display: "flex", flexDirection: "column", flex: 1, gap: 0 }}>
        {/* Tag */}
        <div style={{ alignSelf: "flex-start" }}>
          <span style={{
            display: "inline-flex", alignItems: "center", gap: 6,
            padding: "5px 11px", borderRadius: 999,
            fontSize: 13, fontWeight: 600, color: "#fff",
            background: "rgba(255,255,255,0.18)", backdropFilter: "blur(4px)",
            border: "1px solid rgba(255,255,255,0.25)",
          }}>
            <Sparkles size={13} />
            Insight
          </span>
        </div>

        {/* Role titles */}
        {topRoles.length > 0 ? (
          <div style={{ marginTop: 20, display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "rgba(255,255,255,0.6)" }}>
              Best-fit roles
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 7 }}>
              {topRoles.map((r, i) => (
                <span key={r.title} style={{
                  display: "inline-flex", alignItems: "center",
                  padding: "6px 12px", borderRadius: 999, fontSize: 14, fontWeight: 600,
                  background: i === 0 ? "rgba(255,255,255,0.28)" : "rgba(255,255,255,0.14)",
                  border: "1px solid rgba(255,255,255,0.25)",
                  color: "#fff",
                }}>
                  {r.title}
                </span>
              ))}
            </div>
          </div>
        ) : (
          <p style={{ marginTop: 20, fontSize: 13, color: "rgba(255,255,255,0.65)" }}>
            Role analysis pending.
          </p>
        )}

        {/* Divider */}
        <div style={{ height: 1, background: "rgba(255,255,255,0.2)", margin: "20px 0" }} />

        {/* Bridge skill */}
        {top ? (
          <>
            <div style={{ fontSize: 48, fontWeight: 700, letterSpacing: "-0.04em", lineHeight: 1 }}>
              {Math.round(top.centrality * 100)}%
            </div>
            <div style={{ fontSize: 16, fontWeight: 600, marginTop: 10, lineHeight: 1.3 }}>
              {top.name} is your bridge skill.
            </div>
            <div style={{ fontSize: 14, lineHeight: 1.5, marginTop: 6, color: "rgba(255,255,255,0.8)" }}>
              Highest betweenness centrality in your graph.
            </div>
          </>
        ) : (
          <p style={{ fontSize: 13, color: "rgba(255,255,255,0.65)" }}>
            Graph analysis pending — re-ingest to generate.
          </p>
        )}
      </div>
    </section>
  )
}
