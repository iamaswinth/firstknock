"use client"

import { useState } from "react"
import { AnimatePresence } from "framer-motion"
import { Search, SlidersHorizontal, MoreVertical, Check } from "lucide-react"
import type { TimelineEvent, ExperienceEntry } from "@/lib/api/types"
import {
  CompanyDetailModal,
  CompanyLogo,
  fmtMonths,
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

// ── StatusBadge ───────────────────────────────────────────────────────────────

function StatusBadge({ isCurrent, stage }: { isCurrent: boolean; stage: string | null }) {
  if (isCurrent) {
    return (
      <span style={{
        display: "inline-flex", alignItems: "center", gap: 5,
        padding: "4px 12px", borderRadius: 999,
        background: "var(--fk-green)", color: "#fff",
        fontSize: 12, fontWeight: 600, whiteSpace: "nowrap",
      }}>
        <Check size={11} strokeWidth={2.5} /> Active
      </span>
    )
  }
  if (stage) return stageBadge(stage)
  return (
    <span style={{
      display: "inline-flex", alignItems: "center",
      padding: "4px 12px", borderRadius: 999,
      background: "var(--fk-card-2)",
      border: "1px solid var(--fk-line)",
      color: "var(--fk-ink-4)",
      fontSize: 12, fontWeight: 600, whiteSpace: "nowrap",
    }}>
      Past
    </span>
  )
}

// ── Column grid definition ────────────────────────────────────────────────────

const COL = "40px 1fr 200px 130px 140px 40px"

// ── ColHeader ─────────────────────────────────────────────────────────────────

function ColHeader() {
  const label = (text: string) => (
    <span style={{
      fontSize: 11, fontWeight: 600, color: "var(--fk-ink-4)",
      textTransform: "uppercase", letterSpacing: "0.07em",
    }}>
      {text}
    </span>
  )
  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: COL,
      alignItems: "center",
      padding: "10px 20px",
      background: "var(--fk-card-2)",
      borderBottom: "1px solid var(--fk-line)",
    }}>
      <div>
        <input
          type="checkbox"
          style={{ width: 14, height: 14, accentColor: "var(--fk-brand)", cursor: "pointer" }}
        />
      </div>
      <div>{label("Company")}</div>
      <div>{label("Date Range")}</div>
      <div>{label("Duration")}</div>
      <div>{label("Status")}</div>
      <div />
    </div>
  )
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
  const [menuHovered, setMenuHovered] = useState(false)

  const primary   = events[0]
  const detail    = primary?.company_detail
  const name      = primary?.entity ?? ""
  const isCurrent = events.some(e => e.is_current)
  const totalMonths = events.reduce((s, e) => s + (e.months ?? 0), 0)

  const startDate = [...events].sort((a, b) =>
    (a.start_date ?? "").localeCompare(b.start_date ?? "")
  )[0]?.start_date
  const endDate   = isCurrent ? null : events[0]?.end_date
  const dateRange = `${fmtDate(startDate)} – ${isCurrent ? "Present" : fmtDate(endDate)}`

  return (
    <>
      <div
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        onClick={() => setOpen(true)}
        style={{
          display: "grid",
          gridTemplateColumns: COL,
          alignItems: "center",
          padding: "14px 20px",
          background: hovered ? "var(--fk-card-2)" : "transparent",
          borderBottom: isLast ? "none" : "1px solid var(--fk-line)",
          transition: "background 0.12s",
          cursor: "pointer",
        }}
      >
        {/* Checkbox */}
        <div onClick={e => e.stopPropagation()} style={{ display: "flex", alignItems: "center" }}>
          <input
            type="checkbox"
            style={{ width: 14, height: 14, accentColor: "var(--fk-brand)", cursor: "pointer" }}
          />
        </div>

        {/* Company name + industry */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, minWidth: 0 }}>
          <CompanyLogo logoUrl={detail?.logo_url ?? null} name={name} size={40} />
          <div style={{ minWidth: 0 }}>
            <div style={{
              fontSize: 16, fontWeight: 700, color: "var(--fk-ink)", lineHeight: 1.25,
              whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
            }}>
              {name}
            </div>
            <div style={{ fontSize: 12, color: "var(--fk-ink-4)", marginTop: 2, minHeight: 16 }}>
              {detail?.industry ?? ""}
            </div>
          </div>
        </div>

        {/* Date range */}
        <div style={{ fontSize: 14, color: "var(--fk-ink-3)" }}>
          {dateRange}
        </div>

        {/* Duration */}
        <div style={{ fontSize: 14, color: "var(--fk-ink-3)" }}>
          {totalMonths > 0 ? fmtMonths(totalMonths) : "—"}
        </div>

        {/* Status */}
        <div>
          <StatusBadge isCurrent={isCurrent} stage={detail?.stage ?? null} />
        </div>

        {/* 3-dot menu */}
        <div
          onClick={e => { e.stopPropagation(); setOpen(true) }}
          onMouseEnter={() => setMenuHovered(true)}
          onMouseLeave={() => setMenuHovered(false)}
          style={{
            display: "flex", alignItems: "center", justifyContent: "center",
            width: 28, height: 28, borderRadius: 6,
            background: menuHovered ? "var(--fk-line)" : "transparent",
            cursor: "pointer",
            opacity: hovered ? 1 : 0,
            transition: "opacity 0.12s, background 0.12s",
          }}
        >
          <MoreVertical size={15} color="var(--fk-ink-3)" />
        </div>
      </div>

      <AnimatePresence>
        {open && (
          <CompanyDetailModal
            events={events}
            resume_experience={resume_experience}
            onClose={() => setOpen(false)}
          />
        )}
      </AnimatePresence>
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
  const grouped   = new Map<string, TimelineEvent[]>()
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
      <div style={{
        padding: "24px 28px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}>
        <div>
          <div style={{ fontSize: 20, fontWeight: 600, letterSpacing: "-0.01em", color: "var(--fk-ink)" }}>
            Companies
          </div>
          <div style={{ fontSize: 14, color: "var(--fk-ink-3)", marginTop: 2 }}>
            {companies.length} {companies.length === 1 ? "company" : "companies"} you&apos;ve worked at
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <button style={{
            display: "flex", alignItems: "center", justifyContent: "center",
            width: 34, height: 34, borderRadius: 8,
            background: "transparent", border: "1px solid var(--fk-line)",
            cursor: "pointer",
          }}>
            <Search size={15} color="var(--fk-ink-3)" />
          </button>
          <button style={{
            display: "inline-flex", alignItems: "center", gap: 6,
            padding: "7px 14px", borderRadius: 8,
            background: "transparent", border: "1px solid var(--fk-line)",
            fontSize: 14, fontWeight: 500, color: "var(--fk-ink-2)",
            cursor: "pointer",
          }}>
            <SlidersHorizontal size={13} />
            Filters
          </button>
        </div>
      </div>

      {/* Divider */}
      <div style={{ height: 1, background: "var(--fk-line)" }} />

      {/* Column headers */}
      <ColHeader />

      {/* Rows */}
      <div style={{ overflowX: "auto" }}>
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
