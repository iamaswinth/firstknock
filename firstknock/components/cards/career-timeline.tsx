"use client"

import { useState } from "react"
import { CardShell } from "./card-shell"
import type { TimelineEvent, CompanyDetail } from "@/lib/api/types"

interface CareerTimelineProps {
  events: TimelineEvent[]
  totalMonths: number | null | undefined
}

interface Bar {
  id: string
  event: TimelineEvent
  label: string
  start: Date
  end: Date
  current: boolean
  months: number
  color: string
}

interface Group {
  name: string
  bars: Bar[]
}

const CHART_COLORS = [
  "var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)",
  "var(--chart-5)", "var(--chart-6)", "var(--chart-7)", "var(--chart-8)",
]

const STRIPES =
  "repeating-linear-gradient(45deg, rgba(255,255,255,0.18) 0 6px, rgba(255,255,255,0) 6px 12px)"

const MONTH_ABBR = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

function parseDate(value: string | null | undefined): Date | null {
  if (!value) return null
  const m = value.match(/^(\d{4})(?:-(\d{1,2}))?(?:-(\d{1,2}))?/)
  if (!m) return null
  const d = new Date(Number(m[1]), m[2] ? Number(m[2]) - 1 : 0, m[3] ? Number(m[3]) : 1)
  return Number.isNaN(d.getTime()) ? null : d
}

function monthsBetween(start: Date, end: Date): number {
  return Math.max(1, (end.getFullYear() - start.getFullYear()) * 12 + (end.getMonth() - start.getMonth()))
}

function formatDuration(months: number): string {
  const y = Math.floor(months / 12)
  const mo = months % 12
  if (y === 0) return `${mo} mo`
  if (mo === 0) return `${y} yr`
  return `${y} yr ${mo} mo`
}

function formatFunding(amount: number | null, roundType: string | null): string | null {
  if (!amount) return null
  const formatted = amount >= 1_000_000
    ? `$${(amount / 1_000_000).toFixed(0)}M`
    : `$${(amount / 1_000).toFixed(0)}K`
  return roundType ? `${formatted} ${roundType}` : formatted
}

const ROW_H  = 34
const BAR_H  = 22
const AXIS_H = 40   // row 1 (years, top 0–18px) + row 2 (months, 18–38px)

export function CareerTimeline({ events, totalMonths }: CareerTimelineProps) {
  const now = new Date()
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const expEvents = events.filter((e) => e.type === "experience")
  const eduEvents = events.filter((e) => e.type === "education")

  // Build experience bars
  const expBars: Bar[] = expEvents
    .map((e, i): Bar | null => {
      let start = parseDate(e.start_date)
      // Synthesize start when is_current + months are available but date is missing
      if (!start && e.is_current && e.months) {
        start = new Date(now.getTime() - e.months * 30.44 * 86_400_000)
      }
      if (!start) return null
      const end = e.is_current ? now : parseDate(e.end_date) ?? now
      return {
        id: e.id,
        event: e,
        label: e.label,
        start,
        end,
        current: e.is_current,
        months: e.months ?? monthsBetween(start, end),
        color: CHART_COLORS[i % CHART_COLORS.length],
      }
    })
    .filter((b): b is Bar => b !== null)

  // Build education bars (backend normalizes start_year → start_date as "YYYY")
  const eduBars: Bar[] = eduEvents
    .map((e, i): Bar | null => {
      const endDate   = parseDate(e.end_date) ?? now
      const startDate = parseDate(e.start_date) ?? new Date(endDate.getFullYear() - 4, 0, 1)
      if (Number.isNaN(startDate.getTime())) return null
      return {
        id: e.id,
        event: e,
        label: e.label,
        start: startDate,
        end: endDate,
        current: !e.end_date,
        months: monthsBetween(startDate, endDate),
        color: CHART_COLORS[(i + 4) % CHART_COLORS.length],
      }
    })
    .filter((b): b is Bar => b !== null)

  const groups: Group[] = []
  if (expBars.length > 0) groups.push({ name: "Experience", bars: expBars })
  if (eduBars.length > 0) groups.push({ name: "Education",  bars: eduBars })

  const roleCount = expBars.length
  const yrs = totalMonths != null ? `${(totalMonths / 12).toFixed(1)} yrs · ` : ""
  const sub  = `${yrs}${roleCount} role${roleCount === 1 ? "" : "s"}`

  const selectedEvent = events.find((e) => e.id === selectedId) ?? null

  if (groups.length === 0) {
    return (
      <CardShell title="Career Timeline" sub={sub}>
        <div style={{ height: 220, display: "grid", placeItems: "center", color: "var(--fk-ink-4)", fontSize: 14 }}>
          No dated experience or education to plot yet — re-ingest to populate the timeline.
        </div>
      </CardShell>
    )
  }

  // Overall date range, snapped to whole years
  const allBars  = groups.flatMap((g) => g.bars)
  const minYear  = Math.min(...allBars.map((b) => b.start.getFullYear()))
  const maxYear  = Math.max(...allBars.map((b) => b.end.getFullYear()))
  const minBound = new Date(minYear, 0, 1).getTime()
  const maxBound = new Date(maxYear + 1, 0, 1).getTime()
  const span     = maxBound - minBound || 1

  const pct     = (t: number) => ((t - minBound) / span) * 100
  const nowPct  = pct(now.getTime())
  const showNow = now.getTime() >= minBound && now.getTime() <= maxBound

  // Month ticks for the axis
  const monthTicks: { date: Date; major: boolean }[] = []
  for (let y = minYear; y <= maxYear + 1; y++) {
    for (let mo = 0; mo < 12; mo++) {
      const d = new Date(y, mo, 1)
      if (d.getTime() < minBound || d.getTime() > maxBound) continue
      monthTicks.push({ date: d, major: mo === 0 })
    }
  }

  // Three-tier labelling so month labels never crowd: every 2 / 3 / 6 months
  const totalMonthsRange = (maxYear - minYear + 1) * 12
  const labelEvery = totalMonthsRange > 96 ? 6 : totalMonthsRange > 36 ? 3 : 2

  const chartHeight =
    AXIS_H + 4 +
    groups.reduce((h, g) => h + 24 + g.bars.length * ROW_H, 0) +
    8

  return (
    <CardShell title="Career Timeline" sub={sub}>
      {/* Gantt chart */}
      <div style={{ position: "relative", height: chartHeight, fontSize: 12 }}>

        {/* Month gridlines (subtle) */}
        {monthTicks.map(({ date, major }) => (
          <div
            key={`mgrid-${date.getTime()}`}
            style={{
              position: "absolute",
              left: `${pct(date.getTime())}%`,
              top: AXIS_H,
              bottom: 0,
              width: 1,
              background: major ? "var(--fk-line)" : "var(--fk-line-2)",
              opacity: major ? 1 : 0.5,
            }}
          />
        ))}

        {/* Now marker */}
        {showNow && (
          <div style={{ position: "absolute", left: `${nowPct}%`, top: 0, bottom: 0, width: 0, pointerEvents: "none" }}>
            <div style={{ position: "absolute", top: AXIS_H, bottom: 0, width: 1, background: "var(--fk-brand)", opacity: 0.6 }} />
            <div style={{ position: "absolute", top: 2, transform: "translateX(-50%)", color: "var(--fk-brand)", fontSize: 11, fontWeight: 600 }}>
              Now
            </div>
          </div>
        )}

        {/* Axis row 1: year labels */}
        {monthTicks
          .filter(({ major }) => major)
          .map(({ date }) => (
            <div
              key={`yr-${date.getFullYear()}`}
              style={{
                position: "absolute",
                left: `${pct(date.getTime())}%`,
                top: 0,
                transform: "translateX(3px)",
                color: "var(--fk-ink-3)",
                fontSize: 11,
                fontWeight: 600,
              }}
            >
              {date.getFullYear()}
            </div>
          ))}

        {/* Axis row 2: month labels — fix: use 1-indexed month so Dec (11+1=12) is always divisible */}
        {monthTicks
          .filter(({ date, major }) => !major && (date.getMonth() + 1) % labelEvery === 0)
          .map(({ date }) => (
            <div
              key={`mo-${date.getTime()}`}
              style={{
                position: "absolute",
                left: `${pct(date.getTime())}%`,
                top: 18,
                transform: "translateX(3px)",
                color: "var(--fk-ink-4)",
                fontSize: 10,
              }}
            >
              {MONTH_ABBR[date.getMonth()]}
            </div>
          ))}

        {/* Groups + bars */}
        {(() => {
          let offset = AXIS_H + 4
          return groups.map((g) => {
            const headerTop = offset
            offset += 24
            const rows = g.bars.map((b, idx) => {
              const left     = pct(b.start.getTime())
              const width    = Math.max(pct(b.end.getTime()) - left, 1.5)
              const barTop   = headerTop + 24 + idx * ROW_H
              const duration = formatDuration(b.months)
              const isSelected = selectedId === b.id

              return (
                <div
                  key={b.id}
                  role="button"
                  aria-pressed={isSelected}
                  title={`${b.label} · ${duration}`}
                  onClick={() => setSelectedId(isSelected ? null : b.id)}
                  style={{
                    position: "absolute",
                    left: `${left}%`,
                    width: `${width}%`,
                    top: barTop + (ROW_H - BAR_H) / 2,
                    height: BAR_H,
                    backgroundColor: b.color,
                    backgroundImage: STRIPES,
                    borderRadius: 6,
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    paddingInline: 8,
                    color: "#fff",
                    fontWeight: 500,
                    fontSize: 11.5,
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    boxShadow: isSelected
                      ? `0 0 0 2px #fff, 0 0 0 4px ${b.color}`
                      : "var(--fk-shadow-sm)",
                    cursor: "pointer",
                    transition: "box-shadow 0.15s ease",
                  }}
                >
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{b.label}</span>
                  <span style={{ flexShrink: 0, opacity: 0.85, fontWeight: 600, fontSize: 10.5 }}>· {duration}</span>
                </div>
              )
            })
            const block = (
              <div key={g.name}>
                <div
                  style={{
                    position: "absolute",
                    left: 0,
                    top: headerTop,
                    color: "var(--fk-ink-3)",
                    fontSize: 11,
                    fontWeight: 600,
                    textTransform: "uppercase",
                    letterSpacing: "0.04em",
                  }}
                >
                  {g.name}
                </div>
                {rows}
              </div>
            )
            offset += g.bars.length * ROW_H
            return block
          })
        })()}
      </div>

      {/* Detail panel — shown below the chart when a bar is selected */}
      {selectedEvent && (
        <DetailPanel event={selectedEvent} onClose={() => setSelectedId(null)} />
      )}
    </CardShell>
  )
}

// ── Detail Panel ─────────────────────────────────────────────────────────────

function DetailPanel({ event, onClose }: { event: TimelineEvent; onClose: () => void }) {
  const d = event.company_detail

  return (
    <div
      style={{
        marginTop: 16,
        borderTop: "1px solid var(--fk-line)",
        paddingTop: 16,
        display: "flex",
        flexDirection: "column",
        gap: 12,
        animation: "fadeSlideIn 0.18s ease",
      }}
    >
      {/* Header row */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 15, fontWeight: 700, color: "var(--fk-ink)", letterSpacing: "-0.01em" }}>
            {event.entity}
          </div>
          <div style={{ fontSize: 12.5, color: "var(--fk-ink-3)", marginTop: 2 }}>
            {event.type === "experience"
              ? event.label.split(" · ")[0]   // title part
              : event.field ?? event.label}
          </div>
        </div>
        <button
          onClick={onClose}
          style={{
            width: 28, height: 28, borderRadius: "50%",
            border: "1px solid var(--fk-line-2)",
            background: "transparent",
            color: "var(--fk-ink-4)",
            display: "grid", placeItems: "center",
            cursor: "pointer", flexShrink: 0,
            fontSize: 14,
          }}
        >
          ×
        </button>
      </div>

      {event.type === "experience" && d ? (
        <CompanyDetailGrid detail={d} techStack={event.tech_stack} />
      ) : event.type === "education" ? (
        <EducationDetailGrid event={event} />
      ) : null}
    </div>
  )
}

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  if (!value) return null
  return (
    <div style={{ display: "flex", gap: 8, alignItems: "baseline" }}>
      <span style={{ fontSize: 11, color: "var(--fk-ink-4)", fontWeight: 600, textTransform: "uppercase",
        letterSpacing: "0.04em", minWidth: 90, flexShrink: 0 }}>
        {label}
      </span>
      <span style={{ fontSize: 13, color: "var(--fk-ink-2)" }}>{value}</span>
    </div>
  )
}

function CompanyDetailGrid({ detail: d, techStack }: { detail: CompanyDetail; techStack: string[] }) {
  const funding = formatFunding(d.total_funding_usd, d.last_round_type)
  const roundAmt = d.last_round_amount_usd
    ? formatFunding(d.last_round_amount_usd, d.last_round_type)
    : null

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
      <DetailRow label="Industry"   value={d.industry} />
      <DetailRow label="Stage"      value={d.stage} />
      <DetailRow label="Founded"    value={d.founded} />
      <DetailRow label="Headcount"  value={d.headcount ? `~${d.headcount.toLocaleString()}` : null} />
      <DetailRow label="HQ"         value={d.headquarters} />
      <DetailRow label="Funding"    value={funding} />
      {roundAmt && roundAmt !== funding && <DetailRow label="Last round" value={roundAmt} />}
      <DetailRow label="CEO"        value={d.ceo} />
      {d.website && (
        <DetailRow
          label="Website"
          value={
            <a
              href={d.website.startsWith("http") ? d.website : `https://${d.website}`}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "var(--fk-brand)", textDecoration: "none" }}
            >
              {d.website.replace(/^https?:\/\//, "")}
            </a>
          }
        />
      )}
      {d.key_investors.length > 0 && (
        <DetailRow label="Investors" value={d.key_investors.slice(0, 4).join(", ")} />
      )}
      {d.founders.length > 0 && (
        <DetailRow label="Founders" value={d.founders.join(", ")} />
      )}
      {techStack.length > 0 && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 4 }}>
          {techStack.map((s) => (
            <span
              key={s}
              style={{
                fontSize: 11, fontWeight: 500,
                padding: "2px 8px", borderRadius: 999,
                background: "var(--fk-well)",
                border: "1px solid var(--fk-line)",
                color: "var(--fk-ink-3)",
              }}
            >
              {s}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

function EducationDetailGrid({ event }: { event: TimelineEvent }) {
  const [degree, institution] = event.label.split(" · ")
  const start = event.start_date ? event.start_date.slice(0, 4) : null
  const end   = event.end_date   ? event.end_date.slice(0, 4)   : "Present"
  const years = start ? `${start} – ${end}` : end

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
      <DetailRow label="Degree"      value={degree} />
      <DetailRow label="Institution" value={institution} />
      <DetailRow label="Field"       value={event.field} />
      <DetailRow label="Years"       value={years} />
    </div>
  )
}
