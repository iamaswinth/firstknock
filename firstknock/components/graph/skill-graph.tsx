"use client"
import { useEffect, useRef, useState, useCallback } from "react"
import { GraphFilters, type TypeFilter, type SourceFilter } from "./graph-filters"
import { NodeDrawer } from "./node-drawer"
import type { GraphNode, GraphLink, GraphCommunity } from "@/lib/api/types"

interface SkillGraphProps {
  nodes: GraphNode[]
  links: GraphLink[]
  communities: GraphCommunity[]
}

// Category → FK accent color
const CATEGORY_COLOR: Record<string, string> = {
  language:  "#2f6af0",  // blue
  framework: "#14a05a",  // green
  tool:      "#ef7b2e",  // orange (brand)
  database:  "#7c3aed",  // purple
  concept:   "#e6457f",  // pink
  other:     "#64748b",  // slate fallback
}

function getNodeFill(node: GraphNode, communities: GraphCommunity[]): string {
  if (node.type === "Person")      return "#14161b"
  if (node.type === "Company")     return "#14161b"
  if (node.type === "Institution") return "#c8c6c0"
  if (node.type === "Project")     return "#dbe7ff"
  if (node.type === "Skill") {
    const community = communities.find((c) => c.id === node.community_id)
    if (community) return community.color
    const cat = (node.properties?.category as string | undefined) ?? ""
    return CATEGORY_COLOR[cat] ?? CATEGORY_COLOR.other
  }
  return "#94a3b8"
}

function inferredFill(hex: string): string {
  // Strip alpha if present, re-add at 65%
  const base = hex.length > 7 ? hex.slice(0, 7) : hex
  return base + "a6"
}

function nodeVisible(
  node: GraphNode,
  typeFilter: TypeFilter,
  sourceFilter: SourceFilter,
  communityFilter: number | null
): boolean {
  if (typeFilter !== "All") {
    const map: Record<TypeFilter, string[]> = {
      All: [], Skills: ["Skill"], Companies: ["Company", "Institution"], Projects: ["Project"],
    }
    if (!map[typeFilter].includes(node.type)) return false
  }
  if (sourceFilter !== "All" && node.type === "Skill") {
    if (sourceFilter === "Explicit" && node.source_type !== "explicit") return false
    if (sourceFilter === "Inferred" && !["inferred", "graph_algo"].includes(node.source_type ?? "")) return false
  }
  if (communityFilter !== null && node.type === "Skill" && node.community_id !== communityFilter) return false
  return true
}

// Node radius in Orb simulation pixels (NOT screen pixels — zoom-invariant)
function getNodeSize(node: GraphNode): number {
  if (node.type === "Person")      return 14
  if (node.type === "Company")     return 9
  if (node.type === "Project")     return 8
  if (node.type === "Institution") return 7
  if (node.type === "Skill") {
    if (node.source_type === "graph_algo") return 4
    if (node.source_type === "inferred")   return 6
    return 8  // explicit
  }
  return 6
}

export function SkillGraph({ nodes, links, communities }: SkillGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const orbRef = useRef<unknown>(null)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [hoveredName, setHoveredName] = useState<string | null>(null)
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("All")
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>("All")
  const [communityFilter, setCommunityFilter] = useState<number | null>(null)
  const [counts, setCounts] = useState({ nodes: nodes.length, edges: links.length })

  const handleSelectNode = useCallback((node: GraphNode) => {
    setSelectedNode((prev) => (prev?.id === node.id ? null : node))
  }, [])

  useEffect(() => {
    if (!containerRef.current || !nodes.length) return
    let destroyed = false

    async function init() {
      try {
        const { Orb, DefaultView, OrbEventType } = await import("@memgraph/orb")

        const filteredNodes = nodes.filter((n) =>
          nodeVisible(n, typeFilter, sourceFilter, communityFilter)
        )
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

        // ── Orb with tuned DefaultView ────────────────────────────────────────
        const orb = new Orb(containerRef.current!, {
          view: (context) => new DefaultView(context, {
            simulation: {
              // Collision keeps nodes from piling on top of each other.
              // radius = minimum center-to-center separation / 2.
              collision: { radius: 22, strength: 1, iterations: 2 },
              // Link distance = ideal length of each edge in sim coords.
              links: { distance: 80, iterations: 1 },
              // manyBody: negative strength = repulsion. Stronger = more spread.
              manyBody: {
                strength: -180,
                theta: 0.9,
                distanceMin: 5,
                distanceMax: 350,
              },
            },
            render: {
              // Labels are hidden at rest; shown only when a node is hovered/selected.
              labelsIsEnabled: false,
              labelsOnEventIsEnabled: true,
              // Dim non-hovered nodes to 15% opacity on hover.
              contextAlphaOnEventIsEnabled: true,
              contextAlphaOnEvent: 0.15,
              // Transparent — the canvas div's CSS white bg shows through.
              backgroundColor: null,
              minZoom: 0.15,
              maxZoom: 6,
            },
            isSimulationAnimated: true,
          }),
        })
        orbRef.current = orb

        // Spread GraphNode directly so orbNode.data IS the GraphNode
        const orbNodes = filteredNodes.map((n) => ({ ...n }))
        const orbEdges = filteredLinks.map((l, i) => ({
          id: `e-${i}`,
          start: l.source,
          end: l.target,
          relType: l.type,
        }))

        orb.data.setup({ nodes: orbNodes, edges: orbEdges })

        // ── Node styles ───────────────────────────────────────────────────────
        orb.data.getNodes().forEach((orbNode: { data: GraphNode; style: Record<string, unknown> }) => {
          const gn        = orbNode.data as GraphNode
          const isPerson  = gn.type === "Person"
          const isCompany = gn.type === "Company"
          const isInferred = gn.source_type === "inferred" || gn.source_type === "graph_algo"
          const baseFill  = getNodeFill(gn, communities)
          const fill      = isInferred ? inferredFill(baseFill) : baseFill
          const size      = getNodeSize(gn)

          orbNode.style = {
            size,
            color:          fill,
            colorHover:     isPerson ? "#2a2c33" : baseFill,
            colorSelected:  baseFill,
            // Dark nodes have no border; coloured skills get a white ring for definition
            borderColor:        isPerson || isCompany ? "transparent" : "#ffffff",
            borderColorHover:   "#14161b",
            borderColorSelected:"#14161b",
            borderWidth:         isPerson || isCompany ? 0 : 1.5,
            borderWidthSelected: 2.5,
            // Label — Orb renders this when labelsOnEventIsEnabled triggers
            label:     gn.name ?? "",
            fontSize:  isPerson ? 11 : 10,
            fontColor: "#14161b",
            fontFamily:"Geist, Inter, system-ui, sans-serif",
          }

          // Inferred: colored border instead of white so they read as "derived"
          if (isInferred) {
            orbNode.style.borderColor = baseFill
            orbNode.style.borderWidth = 1.5
          }
        })

        // ── Edge styles ───────────────────────────────────────────────────────
        orb.data.getEdges().forEach((orbEdge: { data: { relType?: string }; style: Record<string, unknown> }) => {
          const relType   = orbEdge.data.relType ?? ""
          const isImplies = relType === "SKILL_IMPLIES" || relType === "IMPLIES"
          orbEdge.style = {
            color:      "#c0bcb7",
            colorHover: "#43464d",
            width:      isImplies ? 1 : 1.3,
            widthHover: 2,
            dashArray:  isImplies ? [5, 4] : undefined,
          }
        })

        // ── Events ────────────────────────────────────────────────────────────
        orb.events.on(OrbEventType.NODE_CLICK, (e: { node?: { data: GraphNode } }) => {
          if (e.node) handleSelectNode(e.node.data as GraphNode)
        })
        orb.events.on(OrbEventType.NODE_HOVER, (e: { node?: { data: GraphNode } }) => {
          setHoveredName(e.node ? ((e.node.data as GraphNode).name ?? null) : null)
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
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, links, communities, typeFilter, sourceFilter, communityFilter])

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
        <GraphFilters
          typeFilter={typeFilter}
          sourceFilter={sourceFilter}
          communityFilter={communityFilter}
          communities={communities}
          onTypeChange={setTypeFilter}
          onSourceChange={setSourceFilter}
          onCommunityChange={setCommunityFilter}
        />
      </div>

      {/* Canvas */}
      <div
        className="relative mx-4 mb-3 rounded-xl overflow-hidden"
        style={{ height: 460, background: "#ffffff", border: "1px solid var(--fk-line)" }}
      >
        <div ref={containerRef} className="w-full h-full" />

        {/* Hovered node name tooltip */}
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

        <NodeDrawer
          node={selectedNode}
          communities={communities}
          onClose={() => setSelectedNode(null)}
        />
      </div>

      {/* Counts + legend */}
      <div
        className="flex items-center gap-4 px-5 py-3 border-t text-[11px] fk-mono"
        style={{ borderColor: "var(--fk-line)", color: "var(--fk-ink-4)" }}
      >
        <span><b style={{ color: "var(--fk-ink)" }}>{counts.nodes}</b> nodes</span>
        <span><b style={{ color: "var(--fk-ink)" }}>{counts.edges}</b> edges</span>
        {communityFilter !== null && (
          <span style={{ color: communities.find((c) => c.id === communityFilter)?.color }}>
            {communities.find((c) => c.id === communityFilter)?.name}
          </span>
        )}
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
