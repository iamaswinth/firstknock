import { CardShell } from "./card-shell"
import type { PinnedRepo } from "@/lib/api/types"

const LANG_COLOR: Record<string, string> = {
  TypeScript: "#2f6af0", JavaScript: "#e6b400",
  Python: "#14a05a", Rust: "#dea584", Go: "#00add8",
}

export function PinnedRepos({ repos, githubUser }: { repos: PinnedRepo[]; githubUser?: string }) {
  return (
    <CardShell
      title="Pinned Repositories"
      sub={githubUser ? `${repos.length} from github.com/${githubUser}` : `${repos.length} repos`}
      id="projects"
    >
      <div style={{ paddingTop: 4 }}>
        <div style={{ display: "flex", flexDirection: "column" }}>
          {repos.map((p, i) => (
            <div key={p.name} style={{
              padding: "14px 0",
              boxShadow: i > 0 ? "0 -1px 0 var(--fk-line)" : "none",
            }}>
              {/* Top row */}
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                {/* Repo icon box */}
                <div style={{
                  width: 32, height: 32, borderRadius: 9,
                  background: "var(--fk-card-2)", border: "1px solid var(--fk-line)",
                  color: "var(--fk-ink-2)", display: "grid", placeItems: "center", flexShrink: 0,
                }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path d="M6 4h11a2 2 0 0 1 2 2v13H7a2 2 0 0 1-2-2V4Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
                    <path d="M7 17h12M9 8h6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
                  </svg>
                </div>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 14.5, fontWeight: 600, color: "var(--fk-ink)" }}>{p.name}</span>
                    {p.is_new && (
                      <span style={{
                        display: "inline-flex", alignItems: "center",
                        height: 24, padding: "0 10px", borderRadius: 999,
                        fontSize: 12, fontWeight: 600,
                        background: "var(--fk-green-bg)", color: "var(--fk-green)",
                      }}>New</span>
                    )}
                  </div>
                </div>

                {/* Language */}
                <span style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 12.5, color: "var(--fk-ink-3)" }}>
                  <span style={{ width: 9, height: 9, borderRadius: "50%", background: LANG_COLOR[p.primary_language] ?? "#999" }} />
                  {p.primary_language}
                </span>

                {/* Stars */}
                <span style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 12.5, color: "var(--fk-ink-3)" }}>
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 4l2.3 5 5.4.5-4.1 3.6 1.2 5.3L12 21l-4.8 2.5 1.2-5.3L4.3 9.5 9.7 9 12 4Z" />
                  </svg>
                  {p.stars}
                </span>
              </div>

              <p style={{ fontSize: 13, color: "var(--fk-ink-3)", lineHeight: 1.5, margin: "7px 0 0" }}>
                {p.readme_summary || p.topics.join(", ")}
              </p>

              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 9 }}>
                {p.extracted_skills.slice(0, 5).map((s) => (
                  <span key={s} style={{
                    padding: "4px 10px", fontSize: 12, fontWeight: 500,
                    color: "var(--fk-ink-2)", background: "var(--fk-card-2)",
                    border: "1px solid var(--fk-line)", borderRadius: 8,
                  }}>{s}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </CardShell>
  )
}
