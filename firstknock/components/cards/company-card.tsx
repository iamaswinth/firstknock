"use client"

import { useState } from "react"
import { Building2, X, ExternalLink, Globe, Users, MapPin, Calendar, DollarSign, Link2 } from "lucide-react"
import type { TimelineEvent, ExperienceEntry } from "@/lib/api/types"

// ── helpers ───────────────────────────────────────────────────────────────────

export function fmtMonths(months: number | null): string {
  if (!months) return ""
  const y = Math.floor(months / 12)
  const m = months % 12
  if (y && m) return `${y}y ${m}m`
  if (y) return `${y}y`
  return `${m}m`
}

export function fmtUsd(val: number | null): string {
  if (!val) return "—"
  if (val >= 1_000_000_000) return `$${(val / 1_000_000_000).toFixed(1)}B`
  if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(0)}M`
  return `$${(val / 1_000).toFixed(0)}K`
}

const STAGE_STYLE: Record<string, { bg: string; color: string }> = {
  "seed":     { bg: "rgba(245,158,11,0.12)", color: "#b45309" },
  "series-a": { bg: "rgba(59,130,246,0.12)", color: "#1d4ed8" },
  "series-b": { bg: "rgba(59,130,246,0.12)", color: "#1d4ed8" },
  "series-c": { bg: "rgba(59,130,246,0.12)", color: "#1d4ed8" },
  "public":   { bg: "rgba(16,185,129,0.12)", color: "#065f46" },
  "private":  { bg: "rgba(107,114,128,0.1)", color: "#374151" },
}

export function stageBadge(stage: string | null) {
  if (!stage) return null
  const s = STAGE_STYLE[stage.toLowerCase()] ?? { bg: "rgba(107,114,128,0.1)", color: "#374151" }
  const label = stage === "series-a" ? "Series A" : stage === "series-b" ? "Series B" : stage === "series-c" ? "Series C" : stage.charAt(0).toUpperCase() + stage.slice(1)
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", padding: "2px 8px",
      borderRadius: 999, fontSize: 12, fontWeight: 600,
      background: s.bg, color: s.color,
    }}>
      {label}
    </span>
  )
}

// ── Logo ──────────────────────────────────────────────────────────────────────

export function CompanyLogo({ logoUrl, name, size = 44 }: { logoUrl: string | null; name: string; size?: number }) {
  const [failed, setFailed] = useState(false)

  if (logoUrl && !failed) {
    return (
      <img
        src={logoUrl} alt={name} onError={() => setFailed(true)}
        style={{ width: size, height: size, borderRadius: 10, objectFit: "contain", background: "#fff", border: "1px solid var(--fk-line)", flexShrink: 0 }}
      />
    )
  }
  const initials = name.split(/\s+/).slice(0, 2).map(w => w[0] ?? "").join("").toUpperCase()
  const hue = name.split("").reduce((a, c) => a + c.charCodeAt(0), 0) % 360
  return (
    <div style={{
      width: size, height: size, borderRadius: 10, flexShrink: 0,
      background: `hsl(${hue},50%,92%)`, color: `hsl(${hue},50%,35%)`,
      display: "grid", placeItems: "center", fontSize: size * 0.35,
      fontWeight: 700, border: "1px solid var(--fk-line)",
    }}>
      {initials || <Building2 size={size * 0.45} />}
    </div>
  )
}

// ── Modal ─────────────────────────────────────────────────────────────────────

interface ModalProps {
  events: TimelineEvent[]
  resume_experience: ExperienceEntry[]
  onClose: () => void
}

export function CompanyDetailModal({ events, resume_experience, onClose }: ModalProps) {
  const detail = events[0]?.company_detail
  const name = events[0]?.entity ?? ""

  const matchedExp = resume_experience.filter(e =>
    e.company.toLowerCase().includes(name.toLowerCase()) ||
    name.toLowerCase().includes(e.company.toLowerCase())
  )

  const totalMonths = events.reduce((sum, e) => sum + (e.months ?? 0), 0)

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: "fixed", inset: 0, zIndex: 100,
          background: "rgba(0,0,0,0.45)", backdropFilter: "blur(4px)",
        }}
      />
      {/* Panel */}
      <div style={{
        position: "fixed", top: "50%", left: "50%", zIndex: 101,
        transform: "translate(-50%,-50%)",
        width: "min(680px, calc(100vw - 32px))",
        maxHeight: "calc(100vh - 48px)",
        overflowY: "auto",
        background: "var(--fk-card)",
        border: "1px solid var(--fk-line)",
        borderRadius: "var(--fk-radius-lg)",
        boxShadow: "0 24px 64px rgba(0,0,0,0.18)",
      }}>
        {/* Header */}
        <div style={{ padding: "24px 28px 20px", display: "flex", alignItems: "flex-start", gap: 16 }}>
          <CompanyLogo logoUrl={detail?.logo_url ?? null} name={name} size={56} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
              <h2 style={{ fontSize: 22, fontWeight: 700, color: "var(--fk-ink)", margin: 0 }}>{name}</h2>
              {stageBadge(detail?.stage ?? null)}
              {detail?.domain && (
                <span style={{ fontSize: 12, padding: "2px 8px", borderRadius: 999, background: "var(--fk-card-2)", color: "var(--fk-ink-3)", border: "1px solid var(--fk-line)" }}>
                  {detail.domain}
                </span>
              )}
            </div>
            {detail?.industry && (
              <div style={{ fontSize: 14, color: "var(--fk-ink-3)", marginTop: 4 }}>{detail.industry}</div>
            )}
            <div style={{ display: "flex", gap: 10, marginTop: 10, flexWrap: "wrap" }}>
              {detail?.website && (
                <a href={detail.website} target="_blank" rel="noopener noreferrer" style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 13, color: "var(--fk-ink-3)", textDecoration: "none" }}>
                  <Globe size={12} /> Website
                </a>
              )}
              {detail?.linkedin_url && (
                <a href={detail.linkedin_url} target="_blank" rel="noopener noreferrer" style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 13, color: "#0a66c2", textDecoration: "none" }}>
                  <Link2 size={12} /> LinkedIn
                </a>
              )}
            </div>
          </div>
          <button onClick={onClose} style={{ border: "none", background: "none", cursor: "pointer", color: "var(--fk-ink-3)", padding: 4, borderRadius: 6 }}>
            <X size={18} />
          </button>
        </div>

        <div style={{ height: 1, background: "var(--fk-line)", margin: "0 28px" }} />

        {/* Description */}
        {detail?.description && (
          <div style={{ padding: "18px 28px 0", fontSize: 15, color: "var(--fk-ink-3)", lineHeight: 1.65 }}>
            {detail.description}
          </div>
        )}

        {/* Stats grid */}
        {detail && (
          <div style={{ padding: "18px 28px 0", display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px,1fr))", gap: 12 }}>
            {detail.founded && (
              <StatChip icon={<Calendar size={13} />} label="Founded" value={String(detail.founded)} />
            )}
            {detail.headcount && (
              <StatChip icon={<Users size={13} />} label="Headcount" value={`~${detail.headcount.toLocaleString()}`} />
            )}
            {detail.headquarters && (
              <StatChip icon={<MapPin size={13} />} label="HQ" value={detail.headquarters} />
            )}
            {detail.total_funding_usd && (
              <StatChip icon={<DollarSign size={13} />} label="Total Funding" value={fmtUsd(detail.total_funding_usd)} />
            )}
          </div>
        )}

        {/* Investors */}
        {detail?.key_investors?.length ? (
          <div style={{ padding: "16px 28px 0" }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: "var(--fk-ink-4)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8 }}>Investors</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {detail.key_investors.map(inv => (
                <span key={inv} style={{ fontSize: 13, padding: "3px 9px", borderRadius: 999, background: "var(--fk-card-2)", color: "var(--fk-ink-3)", border: "1px solid var(--fk-line)" }}>
                  {inv}
                </span>
              ))}
            </div>
          </div>
        ) : null}

        {/* People */}
        {(detail?.ceo || detail?.founders?.length) ? (
          <div style={{ padding: "16px 28px 0", display: "flex", gap: 24 }}>
            {detail?.ceo && <PersonInfo label="CEO" name={detail.ceo} />}
            {detail?.founders?.length ? <PersonInfo label="Founders" name={detail.founders.join(", ")} /> : null}
          </div>
        ) : null}

        {/* Your time here */}
        <div style={{ margin: "20px 28px 0" }}>
          <div style={{ height: 1, background: "var(--fk-line)" }} />
          <div style={{ padding: "16px 0 0" }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: "var(--fk-ink)", marginBottom: 14 }}>
              Your time here · {fmtMonths(totalMonths)}
            </div>
            {events.map(ev => {
              const title = ev.label.split("·")[0].trim()
              const period = [ev.start_date?.slice(0, 7), ev.end_date?.slice(0, 7) ?? "Present"].join(" – ")
              const bullets = matchedExp.find(e => e.title === title)?.description ?? []
              return (
                <div key={ev.id} style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 15, fontWeight: 600, color: "var(--fk-ink)" }}>{title}</div>
                  <div style={{ fontSize: 13, color: "var(--fk-ink-4)", marginTop: 2 }}>{period} · {fmtMonths(ev.months)}</div>
                  {ev.tech_stack.length > 0 && (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginTop: 8 }}>
                      {ev.tech_stack.map(t => (
                        <span key={t} style={{ fontSize: 12, padding: "2px 8px", borderRadius: 999, background: "var(--fk-card-2)", color: "var(--fk-ink-3)", border: "1px solid var(--fk-line)" }}>
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                  {bullets.length > 0 && (
                    <ul style={{ margin: "8px 0 0 16px", padding: 0, listStyle: "disc" }}>
                      {bullets.map((b, i) => (
                        <li key={i} style={{ fontSize: 14, color: "var(--fk-ink-3)", lineHeight: 1.55, marginBottom: 3 }}>{b}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        <div style={{ height: 24 }} />
      </div>
    </>
  )
}

function StatChip({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 3, padding: "10px 12px", background: "var(--fk-card-2)", borderRadius: 10, border: "1px solid var(--fk-line)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 5, color: "var(--fk-ink-4)", fontSize: 12 }}>
        {icon} {label}
      </div>
      <div style={{ fontSize: 14, fontWeight: 600, color: "var(--fk-ink)" }}>{value}</div>
    </div>
  )
}

function PersonInfo({ label, name }: { label: string; name: string }) {
  return (
    <div>
      <div style={{ fontSize: 12, color: "var(--fk-ink-4)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 3 }}>{label}</div>
      <div style={{ fontSize: 14, color: "var(--fk-ink)" }}>{name}</div>
    </div>
  )
}

// ── Card ──────────────────────────────────────────────────────────────────────

interface CompanyCardProps {
  events: TimelineEvent[]
  resume_experience: ExperienceEntry[]
}

export function CompanyCard({ events, resume_experience }: CompanyCardProps) {
  const [open, setOpen] = useState(false)
  const primary = events[0]
  const detail = primary?.company_detail
  const name = primary?.entity ?? ""
  const title = primary?.label.split("·")[0].trim() ?? ""
  const totalMonths = events.reduce((sum, e) => sum + (e.months ?? 0), 0)

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        style={{
          display: "flex", flexDirection: "column", gap: 12,
          width: 260, minHeight: 180, flexShrink: 0,
          padding: "18px 20px",
          background: "var(--fk-card)",
          border: "1px solid var(--fk-line)",
          borderRadius: "var(--fk-radius-lg)",
          boxShadow: "var(--fk-shadow)",
          cursor: "pointer", textAlign: "left",
          transition: "box-shadow 0.15s, transform 0.15s",
        }}
        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.boxShadow = "0 4px 20px rgba(0,0,0,0.12)"; (e.currentTarget as HTMLElement).style.transform = "translateY(-2px)" }}
        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.boxShadow = "var(--fk-shadow)"; (e.currentTarget as HTMLElement).style.transform = "translateY(0)" }}
      >
        {/* Logo + stage */}
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
          <CompanyLogo logoUrl={detail?.logo_url ?? null} name={name} size={44} />
          {stageBadge(detail?.stage ?? null)}
        </div>

        {/* Name */}
        <div>
          <div style={{ fontSize: 16, fontWeight: 700, color: "var(--fk-ink)", lineHeight: 1.3 }}>{name}</div>
          {detail?.industry && (
            <div style={{ fontSize: 13, color: "var(--fk-ink-4)", marginTop: 2 }}>{detail.industry}</div>
          )}
        </div>

        {/* Role + duration */}
        <div style={{ marginTop: "auto" }}>
          <div style={{ fontSize: 14, color: "var(--fk-ink-3)", fontWeight: 500, lineHeight: 1.3 }}>
            {title}
          </div>
          {totalMonths > 0 && (
            <div style={{ fontSize: 12, color: "var(--fk-ink-4)", marginTop: 3 }}>
              {fmtMonths(totalMonths)}
            </div>
          )}
        </div>
      </button>

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
