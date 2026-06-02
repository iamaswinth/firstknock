"use client"
import { Check, Loader2 } from "lucide-react"

const ALL_STAGES = [
  "parse", "normalize", "extract", "resolve", "persist",
  "graph", "inference", "enrichment", "embedding",
]

const STAGE_LABELS: Record<string, string> = {
  parse:      "Parsing document",
  normalize:  "Normalising data",
  extract:    "Extracting with AI",
  resolve:    "Resolving entities",
  persist:    "Saving to database",
  graph:      "Building graph",
  inference:  "Inferring hidden skills",
  enrichment: "Enriching from GitHub & companies",
  embedding:  "Generating embeddings",
}

// Maps backend Resume.status → which stages are done and which is currently active.
// "enriched" is the terminal status set by the enrichment Celery task.
const STATUS_PROGRESS: Record<string, { done: string[]; active: string | null }> = {
  queued:        { done: [],                                                          active: null },
  parsing:       { done: [],                                                          active: "parse" },
  extracting:    { done: ["parse", "normalize"],                                      active: "extract" },
  resolving:     { done: ["parse", "normalize", "extract"],                          active: "resolve" },
  persisting:    { done: ["parse", "normalize", "extract", "resolve"],               active: "persist" },
  graph_building:{ done: ["parse", "normalize", "extract", "resolve", "persist"],    active: "graph" },
  inferring:     { done: ["parse", "normalize", "extract", "resolve", "persist", "graph"],           active: "inference" },
  enriching:     { done: ["parse", "normalize", "extract", "resolve", "persist", "graph", "inference"], active: "enrichment" },
  enriched:      { done: ALL_STAGES,                                                  active: null },
  // legacy / fallback values
  extracted:     { done: ["parse", "normalize", "extract", "resolve", "persist"],    active: "graph" },
}

interface ProcessingStatusProps {
  status: string
}

export function ProcessingStatus({ status }: ProcessingStatusProps) {
  const progress = STATUS_PROGRESS[status] ?? { done: [], active: null }
  const doneSet = new Set(progress.done)

  return (
    <div className="w-full flex flex-col gap-2">
      {ALL_STAGES.map((stage) => {
        const isDone   = doneSet.has(stage)
        const isActive = progress.active === stage
        const isQueued = !isDone && !isActive

        return (
          <div key={stage} className="flex items-center gap-3">
            <div className="w-5 h-5 flex items-center justify-center shrink-0">
              {isDone ? (
                <CheckIcon />
              ) : isActive ? (
                <SpinnerIcon />
              ) : (
                <div className="w-1.5 h-1.5 rounded-full" style={{ background: "var(--fk-ink-5)" }} />
              )}
            </div>
            <span
              className="text-sm"
              style={{
                color: isDone
                  ? "var(--fk-ink)"
                  : isActive
                  ? "var(--fk-ink-2)"
                  : "var(--fk-ink-4)",
                fontWeight: isActive ? 500 : 400,
              }}
            >
              {STAGE_LABELS[stage]}
            </span>
          </div>
        )
      })}
    </div>
  )
}

function CheckIcon() {
  return (
    <div style={{
      width: 16, height: 16, borderRadius: "50%",
      background: "var(--fk-green-bg)",
      display: "grid", placeItems: "center",
    }}>
      <Check size={10} strokeWidth={2} color="var(--fk-green)" />
    </div>
  )
}

function SpinnerIcon() {
  return <Loader2 size={16} strokeWidth={2} color="var(--fk-brand)" className="animate-spin" />
}
