"use client"
import { cn } from "@/lib/utils"
import type { GraphCommunity } from "@/lib/api/types"

export type TypeFilter = "All" | "Skills" | "Companies" | "Projects"
export type SourceFilter = "All" | "Explicit" | "Inferred"

interface GraphFiltersProps {
  typeFilter: TypeFilter
  sourceFilter: SourceFilter
  communityFilter: number | null
  communities: GraphCommunity[]
  onTypeChange: (f: TypeFilter) => void
  onSourceChange: (f: SourceFilter) => void
  onCommunityChange: (id: number | null) => void
}

const TYPE_OPTS: TypeFilter[] = ["All", "Skills", "Companies", "Projects"]
const SOURCE_OPTS: SourceFilter[] = ["All", "Explicit", "Inferred"]

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className="px-2.5 py-1 rounded-full text-xs font-medium transition-colors"
      style={{
        background: active ? "var(--fk-ink)" : "var(--fk-card-2)",
        color: active ? "#fff" : "var(--fk-ink-3)",
      }}
    >
      {children}
    </button>
  )
}

export function GraphFilters({
  typeFilter, sourceFilter, communityFilter, communities,
  onTypeChange, onSourceChange, onCommunityChange,
}: GraphFiltersProps) {
  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <span className="text-[11px] fk-mono mr-1" style={{ color: "var(--fk-ink-4)" }}>type</span>
      {TYPE_OPTS.map((t) => (
        <Chip key={t} active={typeFilter === t} onClick={() => onTypeChange(t)}>{t}</Chip>
      ))}
      <div className="w-px h-4 mx-1" style={{ background: "var(--fk-line)" }} />
      <span className="text-[11px] fk-mono mr-1" style={{ color: "var(--fk-ink-4)" }}>source</span>
      {SOURCE_OPTS.map((s) => (
        <Chip key={s} active={sourceFilter === s} onClick={() => onSourceChange(s)}>{s}</Chip>
      ))}
      {communities.length > 0 && (
        <>
          <div className="w-px h-4 mx-1" style={{ background: "var(--fk-line)" }} />
          {communities.map((c) => (
            <Chip
              key={c.id}
              active={communityFilter === c.id}
              onClick={() => onCommunityChange(communityFilter === c.id ? null : c.id)}
            >
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: c.color }} />
                {c.name}
              </span>
            </Chip>
          ))}
        </>
      )}
    </div>
  )
}
