"use client"

import { useState } from "react"
import { X, GitBranch, ExternalLink, Star, GitFork, Clock } from "lucide-react"
import type { ProjectEntry, PinnedRepo } from "@/lib/api/types"

// ── Modal ─────────────────────────────────────────────────────────────────────

interface ProjectModalProps {
  project: ProjectEntry
  repo: PinnedRepo | null
  onClose: () => void
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ padding: "16px 28px 0" }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: "var(--fk-ink-4)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8 }}>
        {label}
      </div>
      {children}
    </div>
  )
}

function PillList({ items, color }: { items: string[]; color: "brand" | "indigo" | "teal" | "green" }) {
  const palettes = {
    brand:  { bg: "rgba(239,123,46,0.1)",   text: "var(--fk-brand)",  border: "rgba(239,123,46,0.2)"   },
    indigo: { bg: "rgba(99,102,241,0.1)",   text: "#4f46e5",          border: "rgba(99,102,241,0.2)"   },
    teal:   { bg: "rgba(20,184,166,0.1)",   text: "#0d9488",          border: "rgba(20,184,166,0.2)"   },
    green:  { bg: "rgba(16,185,129,0.1)",   text: "#059669",          border: "rgba(16,185,129,0.2)"   },
  }
  const p = palettes[color]
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
      {items.map(s => (
        <span key={s} style={{ fontSize: 13, padding: "3px 9px", borderRadius: 999, background: p.bg, color: p.text, border: `1px solid ${p.border}` }}>
          {s}
        </span>
      ))}
    </div>
  )
}

function _formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString("en-US", { month: "short", year: "numeric" })
  } catch {
    return iso
  }
}

function ProjectModal({ project, repo, onClose }: ProjectModalProps) {
  const stars   = project.stars   ?? repo?.stars
  const forks   = project.forks   ?? repo?.forks
  const lang    = project.primary_language ?? repo?.primary_language

  return (
    <>
      <div
        onClick={onClose}
        style={{ position: "fixed", inset: 0, zIndex: 100, background: "rgba(0,0,0,0.45)", backdropFilter: "blur(4px)" }}
      />
      <div style={{
        position: "fixed", top: "50%", left: "50%", zIndex: 101,
        transform: "translate(-50%,-50%)",
        width: "min(620px, calc(100vw - 32px))",
        maxHeight: "calc(100vh - 48px)",
        overflowY: "auto",
        background: "var(--fk-card)",
        border: "1px solid var(--fk-line)",
        borderRadius: "var(--fk-radius-lg)",
        boxShadow: "0 24px 64px rgba(0,0,0,0.18)",
      }}>
        {/* Header */}
        <div style={{ padding: "24px 28px 20px", display: "flex", alignItems: "flex-start", gap: 12 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
              <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--fk-ink)", margin: 0 }}>{project.name}</h2>
              <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--fk-ink-4)" }}>
                {stars != null && <span style={{ display: "flex", alignItems: "center", gap: 3 }}><Star size={11} /> {stars}</span>}
                {forks != null && <span style={{ display: "flex", alignItems: "center", gap: 3 }}><GitFork size={11} /> {forks}</span>}
                {lang && <span style={{ padding: "1px 7px", borderRadius: 999, background: "var(--fk-card-2)", border: "1px solid var(--fk-line)" }}>{lang}</span>}
                {project.last_pushed && (
                  <span style={{ display: "flex", alignItems: "center", gap: 3 }}>
                    <Clock size={11} /> {_formatDate(project.last_pushed)}
                  </span>
                )}
              </div>
            </div>

            {/* Meta badges */}
            {(project.domain || project.category || project.customer_type) && (
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8 }}>
                {project.domain && (
                  <span style={{ fontSize: 12, padding: "2px 8px", borderRadius: 999, background: "rgba(20,184,166,0.1)", color: "#0d9488", border: "1px solid rgba(20,184,166,0.2)" }}>
                    {project.domain}
                  </span>
                )}
                {project.category && (
                  <span style={{ fontSize: 12, padding: "2px 8px", borderRadius: 999, background: "var(--fk-card-2)", color: "var(--fk-ink-3)", border: "1px solid var(--fk-line)" }}>
                    {project.category}
                  </span>
                )}
                {project.customer_type && (
                  <span style={{ fontSize: 12, padding: "2px 8px", borderRadius: 999, background: "rgba(99,102,241,0.08)", color: "#4f46e5", border: "1px solid rgba(99,102,241,0.18)" }}>
                    {project.customer_type}
                  </span>
                )}
              </div>
            )}

            <div style={{ display: "flex", gap: 10, marginTop: 10 }}>
              {project.github_url && (
                <a href={project.github_url} target="_blank" rel="noopener noreferrer"
                  style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 13, color: "var(--fk-ink-3)", textDecoration: "none" }}>
                  <GitBranch size={12} /> GitHub
                </a>
              )}
              {project.url && (
                <a href={project.url} target="_blank" rel="noopener noreferrer"
                  style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 13, color: "var(--fk-ink-3)", textDecoration: "none" }}>
                  <ExternalLink size={12} /> Live
                </a>
              )}
            </div>
          </div>
          <button onClick={onClose} style={{ border: "none", background: "none", cursor: "pointer", color: "var(--fk-ink-3)", padding: 4, borderRadius: 6 }}>
            <X size={18} />
          </button>
        </div>

        <div style={{ height: 1, background: "var(--fk-line)", margin: "0 28px" }} />

        {/* Description */}
        <div style={{ padding: "18px 28px 0", fontSize: 15, color: "var(--fk-ink-3)", lineHeight: 1.65 }}>
          {project.description || repo?.readme_summary || "No description available."}
        </div>

        {/* Problem Solved */}
        {project.problem_solved && (
          <Section label="Problem Solved">
            <p style={{ fontSize: 14, color: "var(--fk-ink-3)", lineHeight: 1.65, margin: 0 }}>{project.problem_solved}</p>
          </Section>
        )}

        {/* Use Case */}
        {project.use_case && (
          <Section label="Use Case">
            <p style={{ fontSize: 14, color: "var(--fk-ink-3)", lineHeight: 1.65, margin: 0 }}>{project.use_case}</p>
          </Section>
        )}

        {/* Tech stack */}
        {project.tech_stack.length > 0 && (
          <Section label="Tech Stack">
            <PillList items={project.tech_stack} color="brand" />
          </Section>
        )}

        {/* Skills detected from GitHub */}
        {repo?.extracted_skills?.length ? (
          <Section label="Detected from Repo">
            <PillList items={repo.extracted_skills} color="brand" />
          </Section>
        ) : null}

        {/* Topics */}
        {repo?.topics?.length ? (
          <Section label="Topics">
            <PillList items={repo.topics} color="indigo" />
          </Section>
        ) : null}

        {/* Similar Companies */}
        {project.similar_companies?.length ? (
          <Section label="Similar Companies">
            <PillList items={project.similar_companies} color="teal" />
          </Section>
        ) : null}

        {/* Job Relevance */}
        {project.transferable_job_relevance?.length ? (
          <Section label="Job Relevance">
            <PillList items={project.transferable_job_relevance} color="green" />
          </Section>
        ) : null}

        <div style={{ height: 28 }} />
      </div>
    </>
  )
}

// ── Card ──────────────────────────────────────────────────────────────────────

interface ProjectCardProps {
  project: ProjectEntry
  repo: PinnedRepo | null
}

export function ProjectCard({ project, repo }: ProjectCardProps) {
  const [open, setOpen] = useState(false)
  const visibleStack = project.tech_stack.slice(0, 3)
  const extraCount = project.tech_stack.length - 3
  const stars = project.stars ?? repo?.stars
  const lang  = project.primary_language ?? repo?.primary_language

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        style={{
          display: "flex", flexDirection: "column", gap: 10,
          width: 260, minHeight: 180, flexShrink: 0,
          padding: "18px 20px",
          background: "var(--fk-card)",
          border: "1px solid var(--fk-line)",
          borderRadius: "var(--fk-radius-lg)",
          boxShadow: "var(--fk-shadow)",
          cursor: "pointer", textAlign: "left",
          transition: "box-shadow 0.15s, transform 0.15s",
        }}
        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.boxShadow = "0 4px 20px rgba(0,0,0,0.12)"; (e.currentTarget as HTMLElement).style.transform = "translateY(-2px)" }}
        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.boxShadow = "var(--fk-shadow)"; (e.currentTarget as HTMLElement).style.transform = "translateY(0)" }}
      >
        {/* Top row */}
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {project.github_url && <GitBranch size={14} color="var(--fk-ink-4)" />}
          {project.url && <ExternalLink size={14} color="var(--fk-ink-4)" />}
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6 }}>
            {lang && (
              <span style={{ fontSize: 11, padding: "1px 6px", borderRadius: 999, background: "var(--fk-card-2)", color: "var(--fk-ink-4)", border: "1px solid var(--fk-line)" }}>
                {lang}
              </span>
            )}
            {stars != null && (
              <span style={{ display: "flex", alignItems: "center", gap: 3, fontSize: 12, color: "var(--fk-ink-4)" }}>
                <Star size={11} /> {stars}
              </span>
            )}
          </div>
        </div>

        {/* Name + description */}
        <div>
          <div style={{ fontSize: 16, fontWeight: 700, color: "var(--fk-ink)", lineHeight: 1.3 }}>{project.name}</div>
          <div style={{
            fontSize: 13, color: "var(--fk-ink-3)", marginTop: 4, lineHeight: 1.5,
            display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden",
          }}>
            {project.description}
          </div>
        </div>

        {/* Domain badge */}
        {project.domain && (
          <div style={{ display: "flex", gap: 4 }}>
            <span style={{ fontSize: 11, padding: "2px 7px", borderRadius: 999, background: "rgba(20,184,166,0.1)", color: "#0d9488", border: "1px solid rgba(20,184,166,0.15)" }}>
              {project.domain}
            </span>
          </div>
        )}

        {/* Tech stack */}
        {visibleStack.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: "auto" }}>
            {visibleStack.map(t => (
              <span key={t} style={{ fontSize: 12, padding: "2px 7px", borderRadius: 999, background: "var(--fk-card-2)", color: "var(--fk-ink-3)", border: "1px solid var(--fk-line)" }}>
                {t}
              </span>
            ))}
            {extraCount > 0 && (
              <span style={{ fontSize: 12, padding: "2px 7px", borderRadius: 999, background: "var(--fk-card-2)", color: "var(--fk-ink-4)" }}>+{extraCount}</span>
            )}
          </div>
        )}
      </button>

      {open && (
        <ProjectModal project={project} repo={repo} onClose={() => setOpen(false)} />
      )}
    </>
  )
}
