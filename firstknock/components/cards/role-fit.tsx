import { CardShell } from "./card-shell"
import type { RoleMatch } from "@/lib/api/types"

const RANK_BG = ["rgba(239,123,46,0.12)", "rgba(47,106,240,0.1)", "rgba(20,160,90,0.1)"]
const RANK_COLOR = ["var(--fk-brand)", "var(--fk-blue)", "var(--fk-green)"]

export function RoleFit({ roles }: { roles: RoleMatch[] }) {
  if (!roles.length) {
    return (
      <CardShell title="Role Fit" sub="AI-matched roles from your profile">
        <p style={{ fontSize: 13, color: "var(--fk-ink-3)" }}>
          Role analysis pending — try re-ingesting your résumé.
        </p>
      </CardShell>
    )
  }

  return (
    <CardShell title="Role Fit" sub="AI-matched roles from your profile">
      <div style={{ paddingTop: 4 }}>
        <div style={{ display: "flex", flexDirection: "column" }}>
          {roles.map((role, i) => (
            <div key={role.title} style={{
              display: "flex", gap: 13, padding: "13px 0",
              boxShadow: i > 0 ? "0 -1px 0 var(--fk-line)" : "none",
            }}>
              <div style={{
                width: 28, height: 28, borderRadius: 8, flexShrink: 0,
                background: RANK_BG[i] ?? "var(--fk-card-2)",
                color: RANK_COLOR[i] ?? "var(--fk-ink-3)",
                display: "grid", placeItems: "center",
                fontSize: 12, fontWeight: 700,
              }}>
                {i + 1}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: "var(--fk-ink)" }}>{role.title}</div>
                <div style={{ fontSize: 13, color: "var(--fk-ink-3)", lineHeight: 1.5, marginTop: 4 }}>
                  {role.reason}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </CardShell>
  )
}
