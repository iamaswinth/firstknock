"use client"
import { AnimatePresence, motion } from "framer-motion"
import type { GraphNode, GraphCommunity } from "@/lib/api/types"

interface NodeDrawerProps {
  node: GraphNode | null
  communities: GraphCommunity[]
  onClose: () => void
}

export function NodeDrawer({ node, communities, onClose }: NodeDrawerProps) {
  const community = node?.community_id
    ? communities.find((c) => c.id === node.community_id)
    : null

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
                className="text-[11px] fk-mono px-2 py-0.5 rounded"
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
            {node.type === "Skill" && <SkillDetail node={node} community={community} />}
            {node.type === "Company" && <CompanyDetail node={node} />}
            {node.type === "Project" && <ProjectDetail node={node} />}
            {node.type === "Person" && <PersonDetail />}
            {node.type === "Institution" && <InstitutionDetail node={node} />}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-2 py-2 border-b" style={{ borderColor: "var(--fk-line)" }}>
      <span className="text-[12px]" style={{ color: "var(--fk-ink-3)" }}>{label}</span>
      <span className="text-[12px] font-medium text-right" style={{ color: "var(--fk-ink)" }}>{value}</span>
    </div>
  )
}

function SkillDetail({ node, community }: { node: GraphNode; community: GraphCommunity | null | undefined }) {
  const props = node.properties as Record<string, string>
  const isInferred = node.source_type === "inferred" || node.source_type === "graph_algo"
  return (
    <>
      <div className="flex flex-col">
        {props.category && <Row label="Category" value={props.category} />}
        {community && (
          <Row
            label="Community"
            value={
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full" style={{ background: community.color }} />
                {community.name}
              </span>
            }
          />
        )}
        {node.confidence !== null && node.confidence !== undefined && (
          <Row label="Confidence" value={`${Math.round(node.confidence * 100)}%`} />
        )}
        {node.source_type && <Row label="Source" value={node.source_type} />}
      </div>
      {isInferred && props.reason && (
        <div className="rounded-xl p-3" style={{ background: "var(--fk-blue-bg)" }}>
          <p className="text-[11px] font-semibold mb-1" style={{ color: "var(--fk-blue)" }}>
            Why we infer this
          </p>
          <p className="text-[12px] leading-relaxed" style={{ color: "var(--fk-ink-2)" }}>
            {props.reason}
          </p>
        </div>
      )}
    </>
  )
}

function CompanyDetail({ node }: { node: GraphNode }) {
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

function ProjectDetail({ node }: { node: GraphNode }) {
  const props = node.properties as Record<string, string | number | null>
  return (
    <div className="flex flex-col">
      {props.stars !== undefined && <Row label="Stars" value={`★ ${props.stars}`} />}
      {props.primary_language && <Row label="Language" value={String(props.primary_language)} />}
      {props.description && (
        <p className="text-[12px] leading-relaxed mt-1" style={{ color: "var(--fk-ink-2)" }}>
          {String(props.description)}
        </p>
      )}
    </div>
  )
}

function InstitutionDetail({ node }: { node: GraphNode }) {
  const props = node.properties as Record<string, string>
  return (
    <div className="flex flex-col">
      {props.ranking_tier && <Row label="Ranking tier" value={props.ranking_tier} />}
    </div>
  )
}

function PersonDetail() {
  return (
    <p className="text-[13px] leading-relaxed" style={{ color: "var(--fk-ink-3)" }}>
      This is you — the central node of your knowledge graph. Every skill, company, project, and institution connects back here.
    </p>
  )
}
