"use client"
import { useEffect, useRef, useState, useCallback } from "react"
import { GraphFilters, type TypeFilter } from "./graph-filters"
import { NodeDrawer } from "./node-drawer"
import type { SkillContextNode, SkillContextLink } from "@/lib/api/types"

interface SkillGraphProps {
  nodes: SkillContextNode[]
  links: SkillContextLink[]
}

const CATEGORY_COLOR: Record<string, string> = {
  language:  "#2f6af0",
  framework: "#14a05a",
  tool:      "#ef7b2e",
  database:  "#7c3aed",
  concept:   "#e6457f",
  other:     "#64748b",
}

function getNodeFill(node: SkillContextNode): string {
  if (node.type === "Person")      return "#14161b"
  if (node.type === "Company")     return "#14161b"
  if (node.type === "Institution") return "#c8c6c0"
  if (node.type === "Project")     return "#dbe7ff"
  if (node.type === "Skill") {
    const cat = (node.properties?.category as string | undefined) ?? ""
    return CATEGORY_COLOR[cat] ?? CATEGORY_COLOR.other
  }
  return "#94a3b8"
}

function getNodeSize(node: SkillContextNode): number {
  if (node.type === "Person")      return 14
  if (node.type === "Company")     return 9
  if (node.type === "Project")     return 8
  if (node.type === "Institution") return 7
  return 7  // Skill
}

function nodeVisible(node: SkillContextNode, typeFilter: TypeFilter): boolean {
  if (typeFilter === "All") return true
  if (node.type === "Person") return true  // always show center node
  if (typeFilter === "Skills")    return node.type === "Skill"
  if (typeFilter === "Work")      return node.type === "Company"
  if (typeFilter === "Projects")  return node.type === "Project"
  if (typeFilter === "Education") return node.type === "Institution"
  return true
}

export function SkillGraph({ nodes, links }: SkillGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const orbRef = useRef<unknown>(null)
  const [selectedNode, setSelectedNode] = useState<SkillContextNode | null>(null)
  const [hoveredName, setHoveredName] = useState<string | null>(null)
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("All")
  const [counts, setCounts] = useState({ nodes: nodes.length, edges: links.length })

  const handleSelectNode = useCallback((node: SkillContextNode) => {
    setSelectedNode((prev) => (prev?.id === node.id ? null : node))
  }, [])

  useEffect(() => {
    if (!containerRef.current || !nodes.length) return
    let destroyed = false

    async function init() {
      try {
        const { Orb, DefaultView, OrbEventType } = await import("@memgraph/orb")

        const filteredNodes = nodes.filter((n) => nodeVisible(n, typeFilter))
        const filteredNodeIds = new Set(filteredNodes.map((n) => n.id))
        const filteredLinks = links.filter(
          (l) => filteredNodeIds.has(l.source) && filteredNodeIds.has(l.target)
        )
        setCounts({ nodes: filteredNodes.length, edges: filteredLinks.length })

        if (destroyed) return

        if (orbRef.current) {
          try { (orbRef.current as { destroy: () => void }).destroy() } catch {}
          orbRef.current = null
        }
        containerRef.current!.innerHTML = ""

        const orb = new Orb(containerRef.current!, {
          view: (context) => new DefaultView(context, {
            simulation: {
              collision: { radius: 22, strength: 1, iterations: 2 },
              links: { distance: 80, iterations: 1 },
              manyBody: { strength: -180, theta: 0.9, distanceMin: 5, distanceMax: 350 },
            },
            render: {
              labelsIsEnabled: false,
              labelsOnEventIsEnabled: true,
              contextAlphaOnEventIsEnabled: true,
              contextAlphaOnEvent: 0.15,
              backgroundColor: null,
              minZoom: 0.15,
              maxZoom: 6,
            },
            isSimulationAnimated: true,
          }),
        })
        orbRef.current = orb

        const orbNodes = filteredNodes.map((n) => ({ ...n }))
        const orbEdges = filteredLinks.map((l, i) => ({
          id: `e-${i}`,
          start: l.source,
          end: l.target,
          relType: l.type,
        }))

        orb.data.setup({ nodes: orbNodes, edges: orbEdges })

        orb.data.getNodes().forEach((orbNode: { data: SkillContextNode; style: Record<string, unknown> }) => {
          const gn        = orbNode.data
          const isPerson  = gn.type === "Person"
          const isCompany = gn.type === "Company"
          const fill      = getNodeFill(gn)
          const size      = getNodeSize(gn)

          orbNode.style = {
            size,
            color:           fill,
            colorHover:      isPerson ? "#2a2c33" : fill,
            colorSelected:   fill,
            borderColor:     isPerson || isCompany ? "transparent" : "#ffffff",
            borderColorHover:    "#14161b",
            borderColorSelected: "#14161b",
            borderWidth:         isPerson || isCompany ? 0 : 1.5,
            borderWidthSelected: 2.5,
            label:     gn.name ?? "",
            fontSize:  isPerson ? 11 : 10,
            fontColor: "#14161b",
            fontFamily:"Geist, Inter, system-ui, sans-serif",
          }
        })

        orb.data.getEdges().forEach((orbEdge: { style: Record<string, unknown> }) => {
          orbEdge.style = {
            color:      "#c0bcb7",
            colorHover: "#43464d",
            width:      1.3,
            widthHover: 2,
          }
        })

        orb.events.on(OrbEventType.NODE_CLICK, (e: { node?: { data: SkillContextNode } }) => {
          if (e.node) handleSelectNode(e.node.data)
        })
        orb.events.on(OrbEventType.NODE_HOVER, (e: { node?: { data: SkillContextNode } }) => {
          setHoveredName(e.node ? (e.node.data.name ?? null) : null)
        })

        orb.view.render(() => {
          if (!destroyed) orb.view.recenter()
        })
      } catch (err) {
        console.error("Orb init error:", err)
      }
    }

    init()

    return () => {
      destroyed = true
      if (orbRef.current) {
        try { (orbRef.current as { destroy: () => void }).destroy() } catch {}
        orbRef.current = null
      }
      if (containerRef.current) containerRef.current.innerHTML = ""
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, links, typeFilter])

  return (
    <div
      className="flex flex-col"
      style={{
        background: "var(--fk-card)",
        border: "1px solid var(--fk-line)",
        borderRadius: "var(--fk-radius-lg)",
        boxShadow: "var(--fk-shadow)",
        flex: 1,
      }}
    >
      {/* Header */}
      <div className="flex items-start justify-between px-5 pt-5 pb-3">
        <div>
          <h2 className="text-[18px] font-semibold" style={{ color: "var(--fk-ink)" }}>Skill Graph</h2>
          <p className="text-[13px] mt-0.5" style={{ color: "var(--fk-ink-3)" }}>Your knowledge graph</p>
        </div>
      </div>

      {/* Filters */}
      <div className="px-5 pb-3">
        <GraphFilters typeFilter={typeFilter} onTypeChange={setTypeFilter} />
      </div>

      {/* Canvas */}
      <div
        className="relative mx-4 mb-3 rounded-xl overflow-hidden"
        style={{ height: 460, background: "#ffffff", border: "1px solid var(--fk-line)" }}
      >
        <div ref={containerRef} className="w-full h-full" />

        {hoveredName && !selectedNode && (
          <div
            style={{
              position: "absolute", bottom: 12, left: "50%", transform: "translateX(-50%)",
              background: "var(--fk-ink)", color: "#fff",
              padding: "4px 12px", borderRadius: 999,
              fontSize: 12, fontWeight: 500, pointerEvents: "none",
              whiteSpace: "nowrap",
            }}
          >
            {hoveredName}
          </div>
        )}

        <NodeDrawer node={selectedNode} onClose={() => setSelectedNode(null)} />
      </div>

      {/* Counts + legend */}
      <div
        className="flex items-center gap-4 px-5 py-3 border-t text-[11px] fk-mono"
        style={{ borderColor: "var(--fk-line)", color: "var(--fk-ink-4)" }}
      >
        <span><b style={{ color: "var(--fk-ink)" }}>{counts.nodes}</b> nodes</span>
        <span><b style={{ color: "var(--fk-ink)" }}>{counts.edges}</b> edges</span>
        <div className="flex items-center gap-3 ml-auto">
          {Object.entries(CATEGORY_COLOR).slice(0, 5).map(([cat, color]) => (
            <span key={cat} className="flex items-center gap-1">
              <span style={{ width: 7, height: 7, borderRadius: "50%", background: color, display: "inline-block" }} />
              <span style={{ fontSize: 10, textTransform: "capitalize" }}>{cat}</span>
            </span>
          ))}
        </div>
      </div>

      {/* AI prompt bar */}
      <div
        className="mx-4 mb-4 px-4 py-2.5 rounded-xl flex items-center gap-2"
        style={{ background: "var(--fk-card-2)", border: "1px solid var(--fk-line)" }}
      >
        <span style={{ color: "var(--fk-brand)" }}>✦</span>
        <span className="text-[13px]" style={{ color: "var(--fk-ink-4)" }}>
          Ask the graph — coming soon…
        </span>
      </div>
    </div>
  )
}
