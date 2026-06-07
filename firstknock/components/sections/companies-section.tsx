"use client"

import { useState } from "react"
import { ChevronRight } from "lucide-react"
import type { TimelineEvent, ExperienceEntry } from "@/lib/api/types"
import {
  CompanyDetailModal,
  CompanyLogo,
  fmtMonths,
  fmtUsd,
  stageBadge,
} from "@/components/cards/company-card"

// ── helpers ───────────────────────────────────────────────────────────────────

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "Present"
  try {
    return new Date(iso).toLocaleDateString("en-US", { month: "short", year: "numeric" })
  } catch {
    return iso.slice(0, 7)
  }
}

// ── CompanyRow ────────────────────────────────────────────────────────────────

function CompanyRow({
  events,
  resume_experience,
  isLast,
}: {
  events: TimelineEvent[]
  resume_experience: ExperienceEntry[]
  isLast: boolean
}) {
  const [open, setOpen] = useState(false)
  const [hovered, setHovered] = useState(false)

  const primary = events[0]
  const detail = primary?.company_detail
  const name = primary?.entity ?? ""
  const isCurrent = events.some(e => e.is_current)
  const totalMonths = events.reduce((s, e) => s + (e.months ?? 0), 0)
  const title = primary?.label.split("·")[0].trim() ?? ""

  // chronologically earliest start → latest end
  const startDate = [...events].sort((a, b) =>
    (a.start_date ?? "").localeCompare(b.start_date ?? "")
  )[0]?.start_date
  const endDate = isCurrent ? null : events[0]?.end_date
  const dateRange = `${fmtDate(startDate)} – ${isCurrent ? "Present" : fmtDate(endDate)}`

  return (
    <>
      <div style={{ position: "relative" }}>
        {/* Timeline dot */}
        <div
          className={isCurrent ? "fk-dot-current" : undefined}
          style={{
            position: "absolute",
            left: 22,
            top: "50%",
            transform: "translateY(-50%)",
            width: 12, height: 12,
            borderRadius: "50%",
            background: isCurrent ? "var(--fk-green)" : "var(--fk-ink-5)",
            border: "2px solid var(--fk-card)",
            zIndex: 1,
          }}
        />

        <button
          onClick={() => setOpen(true)}
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
          style={{
            display: "flex", alignItems: "center", gap: 16,
            width: "100%",
            padding: "16px 24px 16px 0",
            background: hovered ? "var(--fk-card-2)" : "transparent",
            border: "none",
            borderBottom: isLast ? "none" : "1px solid var(--fk-line)",
            cursor: "pointer", textAlign: "left",
            transition: "background 0.12s",
          }}
        >
          {/* Logo — inset to align with spine */}
          <div style={{ flexShrink: 0, marginLeft: 44 }}>
            <CompanyLogo logoUrl={detail?.logo_url ?? null} name={name} size={40} />
          </div>

          {/* Company name + industry */}
          <div style={{ flex: "0 0 220px", minWidth: 0 }}>
            <div style={{
              fontSize: 16, fontWeight: 700, color: "var(--fk-ink)", lineHeight: 1.25,
              whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
            }}>
              {name}
            </div>
            {detail?.industry ? (
              <div style={{ fontSize: 13, color: "var(--fk-ink-4)", marginTop: 2 }}>
                {detail.industry}
              </div>
            ) : <div style={{ height: 18 }} />}
          </div>

          {/* Role + date range */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{
              fontSize: 14, fontWeight: 500, color: "var(--fk-ink-2)", lineHeight: 1.25,
              whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
            }}>
              {title}
            </div>
            <div style={{ fontSize: 13, color: "var(--fk-ink-4)", marginTop: 2 }}>
              {dateRange}
            </div>
          </div>

          {/* Badges: duration + stage + funding */}
          <div style={{ display: "flex", alignItems: "center", gap: 6, flexShrink: 0 }}>
            {totalMonths > 0 && (
              <span style={{
                fontSize: 12, fontWeight: 500,
                padding: "3px 10px", borderRadius: 999,
                background: "var(--fk-card-2)",
                border: "1px solid var(--fk-line)",
                color: "var(--fk-ink-3)",
                whiteSpace: "nowrap",
              }}>
                {fmtMonths(totalMonths)}
              </span>
            )}
            {stageBadge(detail?.stage ?? null)}
            {detail?.total_funding_usd ? (
              <span style={{
                fontSize: 12, fontWeight: 500,
                padding: "3px 10px", borderRadius: 999,
                background: "rgba(47,106,240,0.08)",
                border: "1px solid rgba(47,106,240,0.15)",
                color: "var(--fk-blue)",
                whiteSpace: "nowrap",
              }}>
                {fmtUsd(detail.total_funding_usd)}
              </span>
            ) : null}
          </div>

          {/* Chevron */}
          <ChevronRight
            size={16}
            color="var(--fk-ink-5)"
            style={{
              flexShrink: 0,
              transition: "transform 0.12s",
              transform: hovered ? "translateX(3px)" : "translateX(0)",
            }}
          />
        </button>
      </div>

      {open && (
        <CompanyDetailModal
          events={events}
          resume_experience={resume_experience}
          onClose={() => setOpen(false)}
        />
      )}
    </>
  )
}

// ── Section ───────────────────────────────────────────────────────────────────

interface CompaniesSectionProps {
  events: TimelineEvent[]
  resume_experience: ExperienceEntry[]
}

export function CompaniesSection({ events, resume_experience }: CompaniesSectionProps) {
  const expEvents = events.filter(e => e.type === "experience")
  const grouped = new Map<string, TimelineEvent[]>()
  for (const ev of expEvents) {
    const key = ev.entity.toLowerCase().trim()
    if (!grouped.has(key)) grouped.set(key, [])
    grouped.get(key)!.push(ev)
  }

  const companies = Array.from(grouped.values())
  if (!companies.length) return null

  return (
    <section style={{
      background: "var(--fk-card)",
      border: "1px solid var(--fk-line)",
      borderRadius: "var(--fk-radius-lg)",
      boxShadow: "var(--fk-shadow)",
      overflow: "hidden",
      width: "100%",
    }}>
      {/* Header */}
      <div style={{ padding: "22px 24px 16px" }}>
        <div style={{ fontSize: 20, fontWeight: 600, letterSpacing: "-0.01em", color: "var(--fk-ink)" }}>
          Companies
        </div>
        <div style={{ fontSize: 15, color: "var(--fk-ink-3)", marginTop: 2 }}>
          {companies.length} {companies.length === 1 ? "company" : "companies"} you&apos;ve worked at
        </div>
      </div>

      {/* Divider */}
      <div style={{ height: 1, background: "var(--fk-line)", margin: "0 0 0 0" }} />

      {/* Timeline list */}
      <div style={{ position: "relative", padding: "0 0 0 0" }}>
        {/* Vertical spine */}
        <div style={{
          position: "absolute",
          left: 27, top: 0, bottom: 0,
          width: 1,
          background: "var(--fk-line-2)",
          pointerEvents: "none",
        }} />

        {companies.map((evs, i) => (
          <CompanyRow
            key={evs[0].entity}
            events={evs}
            resume_experience={resume_experience}
            isLast={i === companies.length - 1}
          />
        ))}
      </div>
    </section>
  )
}
