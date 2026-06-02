"use client"

export type TypeFilter = "All" | "Skills" | "Work" | "Projects" | "Education"

interface GraphFiltersProps {
  typeFilter: TypeFilter
  onTypeChange: (f: TypeFilter) => void
}

const TYPE_OPTS: TypeFilter[] = ["All", "Skills", "Work", "Projects", "Education"]

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

export function GraphFilters({ typeFilter, onTypeChange }: GraphFiltersProps) {
  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <span className="text-[11px] fk-mono mr-1" style={{ color: "var(--fk-ink-4)" }}>show</span>
      {TYPE_OPTS.map((t) => (
        <Chip key={t} active={typeFilter === t} onClick={() => onTypeChange(t)}>{t}</Chip>
      ))}
    </div>
  )
}
