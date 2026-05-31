"use client"
import { Nav } from "@/components/layout/nav"
import { TitleBar } from "@/components/layout/title-bar"
import { Footer } from "@/components/layout/footer"

interface EmptyDashboardProps {
  name?: string
  onUpload: () => void
}

export function EmptyDashboard({ name, onUpload }: EmptyDashboardProps) {
  return (
    <div
      style={{
        background: "var(--fk-page)",
        minHeight: "100vh",
        width: "100%",
        maxWidth: 1500,
        margin: "0 auto",
        padding: "18px 22px 26px",
        display: "flex",
        flexDirection: "column",
      }}
    >
        <Nav name={name ?? "AD"} onUpload={onUpload} />
        <TitleBar onUpload={onUpload} />

        {/* Ghost bento + overlay */}
        <div style={{ position: "relative", flex: 1, minHeight: 600 }}>
          {/* Ghost grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(12, 1fr)", gap: 16, opacity: 0.35, filter: "blur(1px)", pointerEvents: "none" }}>
            <GhostCard style={{ gridColumn: "span 8", minHeight: 560 }} />
            <div style={{ gridColumn: "span 4", display: "flex", flexDirection: "column", gap: 16 }}>
              <GhostCard style={{ height: 200 }} />
              <GhostCard style={{ flex: 1, minHeight: 200 }} />
            </div>
            <GhostCard style={{ gridColumn: "span 4", height: 220 }} />
            <GhostCard style={{ gridColumn: "span 4", height: 220 }} />
            <GhostCard style={{ gridColumn: "span 4", height: 220 }} />
            <GhostCard style={{ gridColumn: "span 7", height: 300 }} />
            <GhostCard style={{ gridColumn: "span 5", height: 300 }} />
            <GhostCard style={{ gridColumn: "span 6", height: 160 }} />
            <GhostCard style={{ gridColumn: "span 3", height: 160 }} />
            <GhostCard style={{ gridColumn: "span 3", height: 160 }} />
          </div>

          {/* CTA overlay */}
          <div style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 20,
          }}>
            {/* Icon */}
            <div style={{
              width: 64, height: 64, borderRadius: 20,
              background: "var(--fk-card)",
              border: "1px solid var(--fk-line)",
              boxShadow: "var(--fk-shadow)",
              display: "grid", placeItems: "center",
            }}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--fk-ink-3)" strokeWidth="1.5">
                <path d="M12 3.5l7 4v9l-7 4-7-4v-9l7-4Z" strokeLinejoin="round" />
                <path d="M12 3.5v13M5 7.5l7 4 7-4" />
              </svg>
            </div>

            {/* Text */}
            <div style={{ textAlign: "center", maxWidth: 360 }}>
              <p style={{ fontSize: 22, fontWeight: 600, letterSpacing: "-0.02em", color: "var(--fk-ink)", margin: 0 }}>
                Your knowledge graph lives here.
              </p>
              <p style={{ fontSize: 14, color: "var(--fk-ink-3)", margin: "8px 0 0", lineHeight: 1.55 }}>
                Upload your résumé and we'll parse it, build a skill graph, enrich it with GitHub and company data, and infer hidden skills.
              </p>
            </div>

            {/* Upload button */}
            <button
              onClick={onUpload}
              style={{
                display: "inline-flex", alignItems: "center", gap: 8,
                height: 44, padding: "0 20px",
                background: "var(--fk-ink)", color: "#fff",
                borderRadius: 12, fontSize: 14, fontWeight: 600,
                border: "none", cursor: "pointer",
                boxShadow: "0 2px 8px rgba(20,22,27,0.18)",
              }}
            >
              <svg width="15" height="15" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M10 13V4M7 7l3-3 3 3" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M3 13v2a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-2" strokeLinecap="round" />
              </svg>
              Upload résumé
            </button>
          </div>
        </div>

        <Footer />
    </div>
  )
}

function GhostCard({ style }: { style?: React.CSSProperties }) {
  return (
    <div style={{
      background: "var(--fk-card)",
      border: "2px dashed var(--fk-line-2)",
      borderRadius: "var(--fk-radius-lg)",
      ...style,
    }} />
  )
}
