import { CardShell } from "./card-shell"
import type { ProfileCompletenessResponse } from "@/lib/api/types"

const BAR_COLOR = (pct: number) =>
  pct === 100 ? "var(--fk-green)" : pct >= 60 ? "var(--fk-blue)" : "var(--fk-brand)"

export function ProfileCompleteness({ data }: { data: ProfileCompletenessResponse }) {
  const { overall_score, top_suggestion, sections, enrichment_status } = data

  return (
    <CardShell title="Profile Completeness">
      <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
        {/* Left: big score */}
        <div style={{ flexShrink: 0, minWidth: 80 }}>
          <div style={{ fontSize: 44, fontWeight: 700, letterSpacing: "-0.035em", lineHeight: 1, color: "var(--fk-ink)" }}>
            {overall_score}%
          </div>
          <div style={{ fontSize: 12, color: "var(--fk-ink-3)", marginTop: 4 }}>
            {overall_score >= 80 ? "Looking great!" : overall_score >= 50 ? "Getting there" : "Needs work"}
          </div>
          {/* Enrichment dots */}
          <div style={{ display: "flex", flexDirection: "column", gap: 5, marginTop: 16 }}>
            {Object.entries(enrichment_status).map(([key, done]) => (
              <div key={key} style={{ display: "flex", alignItems: "center", gap: 7 }}>
                <span style={{
                  width: 7, height: 7, borderRadius: "50%", flexShrink: 0,
                  background: done ? "var(--fk-green)" : "var(--fk-ink-5)",
                }} />
                <span style={{
                  fontSize: 12, color: done ? "var(--fk-ink-2)" : "var(--fk-ink-4)",
                  textTransform: "capitalize",
                }}>{key}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Right: section bars */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 12 }}>
          {sections.map((s) => (
            <div key={s.name}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
                <span style={{ fontSize: 12.5, color: "var(--fk-ink-2)", fontWeight: 500 }}>{s.name}</span>
                <span style={{ fontSize: 12, color: "var(--fk-ink-4)", fontFamily: "var(--font-geist-mono,monospace)" }}>
                  {s.score}/{s.max}
                </span>
              </div>
              <div style={{ height: 8, borderRadius: 999, background: "var(--fk-well)", overflow: "hidden" }}>
                <div style={{
                  height: "100%", borderRadius: 999,
                  width: `${s.pct}%`,
                  background: BAR_COLOR(s.pct),
                  transition: "width .4s ease",
                }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Suggestion */}
      {top_suggestion && (
        <div style={{
          marginTop: 16, padding: "10px 14px", borderRadius: 12,
          background: "var(--fk-card-2)", border: "1px solid var(--fk-line)",
          fontSize: 13, color: "var(--fk-ink-2)", lineHeight: 1.5,
        }}>
          💡 {top_suggestion}
        </div>
      )}
    </CardShell>
  )
}
