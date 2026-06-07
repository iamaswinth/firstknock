"use client"
import { Check } from "lucide-react"
import type { ResumeContext } from "./upload-modal"

// Matches exact status strings set by update_resume_status() in the backend.
// Sequence: queued → parsing → extracting → resolving → persisting → inferring
//           → enriching → compiling → graph_building → enriched
const ALL_STAGES = [
  "parsing",
  "extracting",
  "resolving",
  "persisting",
  "inferring",
  "enriching",
  "compiling",
  "graph_building",
] as const

type Stage = typeof ALL_STAGES[number]

const STAGE_TITLE: Record<Stage, string> = {
  parsing:       "Reading your résumé",
  extracting:    "Extracting with AI",
  resolving:     "Resolving entities",
  persisting:    "Saving your profile",
  inferring:     "Inferring hidden skills",
  enriching:     "Enriching from GitHub & LinkedIn",
  compiling:     "Compiling your full profile",
  graph_building:"Building your skill graph",
}

const STAGE_DONE: Record<Stage, string> = {
  parsing:       "Document parsed successfully",
  extracting:    "Career history extracted",
  resolving:     "Skills and dates normalised",
  persisting:    "Profile saved",
  inferring:     "Hidden skills discovered",
  enriching:     "External profiles enriched",
  compiling:     "Profile compiled",
  graph_building:"Knowledge graph ready",
}

function buildActiveCopy(stage: Stage, ctx: ResumeContext): string {
  const { name, githubUrl, linkedinUrl, companyNames, skillCount } = ctx

  switch (stage) {
    case "parsing":
      return "Pulling raw text out of your document…"

    case "extracting":
      return "Claude is reading your career history, skills, and projects…"

    case "resolving":
      return "Canonicalising skill names, normalising dates, matching companies…"

    case "persisting":
      return "Writing your extracted data to the database…"

    case "inferring": {
      if (companyNames.length >= 2) {
        const list = companyNames.slice(0, 2).join(" and ")
        return `Looking for skills implied by your work at ${list}…`
      }
      if (companyNames.length === 1) {
        return `Looking for skills implied by your work at ${companyNames[0]}…`
      }
      return "Looking for skills implied by your projects and roles…"
    }

    case "enriching": {
      const parts: string[] = []
      if (githubUrl) {
        const handle = githubUrl.replace(/^https?:\/\/(www\.)?github\.com\//i, "").replace(/\/$/, "")
        parts.push(`github.com/${handle}`)
      }
      if (linkedinUrl) parts.push("LinkedIn")
      if (companyNames.length > 0) parts.push(`${companyNames.length} compan${companyNames.length === 1 ? "y" : "ies"}`)
      if (parts.length > 0) return `Fetching ${parts.join(", ")}…`
      return "Fetching your open-source work and company data…"
    }

    case "compiling": {
      const co = companyNames.length
      if (co > 0 && linkedinUrl) return `Reconciling your résumé with data from ${co} compan${co === 1 ? "y" : "ies"} and LinkedIn…`
      if (co > 0)                return `Reconciling your résumé with data from ${co} compan${co === 1 ? "y" : "ies"}…`
      return "Reconciling your résumé, LinkedIn, and company data together…"
    }

    case "graph_building": {
      const skills  = skillCount > 0 ? `${skillCount} skills` : "your skills"
      const coLabel = companyNames.length > 0 ? `${companyNames.length} compan${companyNames.length === 1 ? "y" : "ies"}` : "your career"
      const prefix  = name ? `${name.split(" ")[0]}'s` : "your"
      return `Connecting ${prefix} ${skills} across ${coLabel}…`
    }
  }
}

const STATUS_PROGRESS: Record<string, { done: Stage[]; active: Stage | null }> = {
  queued:        { done: [],                                                                                            active: null },
  parsing:       { done: [],                                                                                            active: "parsing" },
  extracting:    { done: ["parsing"],                                                                                   active: "extracting" },
  resolving:     { done: ["parsing", "extracting"],                                                                     active: "resolving" },
  persisting:    { done: ["parsing", "extracting", "resolving"],                                                       active: "persisting" },
  // "extracted" is set internally by save_extracted_resume() between persisting and inferring
  extracted:     { done: ["parsing", "extracting", "resolving", "persisting"],                                         active: "inferring" },
  inferring:     { done: ["parsing", "extracting", "resolving", "persisting"],                                         active: "inferring" },
  enriching:     { done: ["parsing", "extracting", "resolving", "persisting", "inferring"],                           active: "enriching" },
  compiling:     { done: ["parsing", "extracting", "resolving", "persisting", "inferring", "enriching"],              active: "compiling" },
  graph_building:{ done: ["parsing", "extracting", "resolving", "persisting", "inferring", "enriching", "compiling"], active: "graph_building" },
  enriched:      { done: [...ALL_STAGES],                                                                               active: null },
}

interface ProcessingStatusProps {
  status: string
  context?: ResumeContext
}

export function ProcessingStatus({ status, context = { companyNames: [], projectCount: 0, skillCount: 0 } }: ProcessingStatusProps) {
  const progress = STATUS_PROGRESS[status] ?? { done: [], active: null }
  const doneSet  = new Set(progress.done)

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
      {ALL_STAGES.map((stage) => {
        const isDone   = doneSet.has(stage)
        const isActive = progress.active === stage

        if (isDone)   return <DoneRow   key={stage} stage={stage} />
        if (isActive) return <ActiveRow key={stage} stage={stage} activeCopy={buildActiveCopy(stage, context)} />
        return <PendingRow key={stage} stage={stage} />
      })}
    </div>
  )
}

function DoneRow({ stage }: { stage: Stage }) {
  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "6px 8px", borderRadius: 6 }}>
      <div style={{ marginTop: 1, flexShrink: 0 }}>
        <div style={{
          width: 16, height: 16, borderRadius: "50%",
          background: "var(--fk-green-bg)",
          display: "grid", placeItems: "center",
        }}>
          <Check size={9} strokeWidth={2.5} color="var(--fk-green)" />
        </div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
        <span style={{ fontSize: 13, fontWeight: 400, color: "var(--fk-ink-2)", lineHeight: "1.4" }}>
          {STAGE_TITLE[stage]}
        </span>
        <span style={{ fontSize: 11, color: "var(--fk-ink-4)", lineHeight: "1.4" }}>
          {STAGE_DONE[stage]}
        </span>
      </div>
    </div>
  )
}

function ActiveRow({ stage, activeCopy }: { stage: Stage; activeCopy: string }) {
  return (
    <div style={{
      display: "flex", alignItems: "flex-start", gap: 10,
      padding: "8px 10px",
      borderRadius: 6,
      borderLeft: "2px solid var(--fk-brand)",
      background: "rgba(239,123,46,0.04)",
      margin: "2px 0",
    }}>
      <div style={{ marginTop: 3, flexShrink: 0 }}>
        <div style={{
          width: 8, height: 8, borderRadius: "50%",
          background: "var(--fk-brand)",
          animation: "fk-blink 1.4s ease-in-out infinite",
        }} />
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 3, flex: 1, minWidth: 0 }}>
        <span style={{ fontSize: 13, fontWeight: 500, color: "var(--fk-ink)", lineHeight: "1.4" }}>
          {STAGE_TITLE[stage]}
        </span>
        <span style={{
          fontSize: 11,
          lineHeight: "1.4",
          background: "linear-gradient(90deg, var(--fk-ink-3) 0%, var(--fk-brand) 45%, var(--fk-ink-3) 80%)",
          backgroundSize: "500px 100%",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          backgroundClip: "text",
          animation: "fk-shimmer 2.2s linear infinite",
          display: "inline-block",
        }}>
          {activeCopy}
        </span>
      </div>
    </div>
  )
}

function PendingRow({ stage }: { stage: Stage }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "5px 8px", borderRadius: 6 }}>
      <div style={{ flexShrink: 0 }}>
        <div style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--fk-ink-5)" }} />
      </div>
      <span style={{ fontSize: 13, fontWeight: 400, color: "var(--fk-ink-5)", lineHeight: "1.4" }}>
        {STAGE_TITLE[stage]}
      </span>
    </div>
  )
}
