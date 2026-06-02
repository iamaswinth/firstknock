"use client"
import { AnimatePresence, motion } from "framer-motion"
import type { SkillContextNode } from "@/lib/api/types"

interface NodeDrawerProps {
  node: SkillContextNode | null
  onClose: () => void
}

export function NodeDrawer({ node, onClose }: NodeDrawerProps) {
  return (
    <AnimatePresence>
      {node && (
        <motion.div
          initial={{ x: 20, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 20, opacity: 0 }}
          transition={{ duration: 0.2, ease: "easeOut" }}
          className="absolute top-0 right-0 h-full w-80 flex flex-col z-20 overflow-y-auto"
          style={{
            background: "var(--fk-card)",
            borderLeft: "1px solid var(--fk-line)",
            borderRadius: "0 var(--fk-radius-lg) var(--fk-radius-lg) 0",
          }}
        >
          {/* Header */}
          <div className="flex items-start justify-between p-5 pb-4">
            <div>
              <span
                className="text-[13px] fk-mono px-2 py-0.5 rounded"
                style={{ background: "var(--fk-card-2)", color: "var(--fk-ink-4)" }}
              >
                {node.type}
              </span>
              <h3 className="text-[17px] font-semibold mt-2" style={{ color: "var(--fk-ink)" }}>
                {node.name}
              </h3>
            </div>
            <button
              onClick={onClose}
              className="w-7 h-7 flex items-center justify-center rounded-full hover:bg-[var(--fk-card-2)] transition-colors mt-0.5"
              style={{ color: "var(--fk-ink-4)" }}
            >
              ✕
            </button>
          </div>

          <div className="px-5 pb-5 flex flex-col gap-4">
            {node.type === "Company" && <CompanyDetail node={node} />}
            {node.type === "Project" && <ProjectDetail node={node} />}
            {node.type === "Institution" && <InstitutionDetail node={node} />}
            {node.type === "Person" && <PersonDetail />}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-2 py-2 border-b" style={{ borderColor: "var(--fk-line)" }}>
      <span className="text-[13px]" style={{ color: "var(--fk-ink-3)" }}>{label}</span>
      <span className="text-[13px] font-medium text-right" style={{ color: "var(--fk-ink)" }}>{value}</span>
    </div>
  )
}

function CompanyDetail({ node }: { node: SkillContextNode }) {
  const props = node.properties as Record<string, string | number | null>
  return (
    <div className="flex flex-col">
      {props.stage && <Row label="Stage" value={String(props.stage)} />}
      {props.industry && <Row label="Industry" value={String(props.industry)} />}
      {props.headcount && <Row label="Headcount" value={String(props.headcount)} />}
      {props.headquarters && <Row label="HQ" value={String(props.headquarters)} />}
      {props.total_funding_usd && (
        <Row label="Total Funding" value={`$${(Number(props.total_funding_usd) / 1_000_000).toFixed(1)}M`} />
      )}
      {props.last_round_type && <Row label="Last Round" value={String(props.last_round_type)} />}
      {props.business_model && <Row label="Model" value={String(props.business_model)} />}
      {props.ceo && <Row label="CEO" value={String(props.ceo)} />}
    </div>
  )
}

function ProjectDetail({ node }: { node: SkillContextNode }) {
  const props = node.properties as Record<string, string | number | null>
  return (
    <div className="flex flex-col">
      {props.stars !== undefined && <Row label="Stars" value={`★ ${props.stars}`} />}
      {props.primary_language && <Row label="Language" value={String(props.primary_language)} />}
      {props.description && (
        <p className="text-[14px] leading-relaxed mt-1" style={{ color: "var(--fk-ink-2)" }}>
          {String(props.description)}
        </p>
      )}
    </div>
  )
}

/**
 * Extracts a 4-digit year from whatever format a resume might produce.
 * Handles: integer, float (2020.0), numeric string ("2020"), "Sep 2024",
 * "2024-09", "2024-09-01", "Present" / "current" → null.
 */
function safeYear(val: unknown): string | null {
  if (val === null || val === undefined || val === "") return null
  const s = String(val).trim()
  if (/^(present|current|now|ongoing)$/i.test(s)) return null
  // Bare number or float: "2020" / "2020.0"
  const bare = Number(s)
  if (isFinite(bare) && bare >= 1900 && bare <= 2100) return String(Math.round(bare))
  // ISO date prefix: "2024-09" or "2024-09-01"
  const iso = s.match(/^(\d{4})-\d{2}/)
  if (iso) return iso[1]
  // "Sep 2024" or "September 2024"
  const mon = s.match(/(?:^|\s)(\d{4})$/)
  if (mon) return mon[1]
  return null
}

function InstitutionDetail({ node }: { node: SkillContextNode }) {
  const props = node.properties as Record<string, unknown>
  const start = safeYear(props.start_year)
  const end   = safeYear(props.end_year)
  const period = start && end ? `${start} – ${end}` : start ?? end ?? null
  return (
    <div className="flex flex-col">
      {props.degree       && <Row label="Degree"       value={String(props.degree)} />}
      {props.field        && <Row label="Field"        value={String(props.field)} />}
      {period             && <Row label="Period"       value={period} />}
      {props.ranking_tier && <Row label="Ranking tier" value={String(props.ranking_tier)} />}
    </div>
  )
}

function PersonDetail() {
  return (
    <p className="text-[14px] leading-relaxed" style={{ color: "var(--fk-ink-3)" }}>
      This is you — the central node of your knowledge graph. Every skill, company, and project connects back here.
    </p>
  )
}
