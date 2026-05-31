"use client"

const SYNC_STAGES = ["parse", "normalize", "extract", "resolve", "persist", "graph"]
const ASYNC_STAGES = ["enrichment", "inference", "embedding"]

const STAGE_LABELS: Record<string, string> = {
  parse:      "Parsing document",
  normalize:  "Normalising data",
  extract:    "Extracting with AI",
  resolve:    "Resolving entities",
  persist:    "Saving to database",
  graph:      "Building graph",
  enrichment: "Enriching from GitHub & companies",
  inference:  "Inferring hidden skills",
  embedding:  "Generating embeddings",
}

interface ProcessingStatusProps {
  status: string
}

export function ProcessingStatus({ status }: ProcessingStatusProps) {
  const enriched = status === "enriched"
  // Sync stages are always complete by the time we start polling
  const done = new Set(enriched ? [...SYNC_STAGES, ...ASYNC_STAGES] : SYNC_STAGES)

  return (
    <div className="w-full flex flex-col gap-2">
      {[...SYNC_STAGES, ...ASYNC_STAGES].map((stage, i) => {
        const isDone = done.has(stage)
        // First async stage is "active" (spinning) while enrichment is pending
        const isActive = !enriched && stage === "enrichment"
        // Later async stages are queued
        const isQueued = !enriched && ASYNC_STAGES.slice(1).includes(stage)

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
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <circle cx="8" cy="8" r="7" fill="var(--fk-green-bg)" />
      <path d="M5 8l2 2 4-4" stroke="var(--fk-green)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function SpinnerIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" className="animate-spin">
      <circle cx="8" cy="8" r="6" stroke="var(--fk-line-2)" strokeWidth="2" fill="none" />
      <path d="M8 2a6 6 0 0 1 6 6" stroke="var(--fk-brand)" strokeWidth="2" strokeLinecap="round" fill="none" />
    </svg>
  )
}
