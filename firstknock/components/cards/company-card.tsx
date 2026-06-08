"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Building2, X, Globe, Users, MapPin, Calendar, DollarSign, Link2, Briefcase, Pencil, Share2, MoreHorizontal } from "lucide-react"
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
  const [activeTab, setActiveTab] = useState<"roles" | "team" | "investors">("roles")

  const detail      = events[0]?.company_detail
  const name        = events[0]?.entity ?? ""
  const totalMonths = events.reduce((sum, e) => sum + (e.months ?? 0), 0)
  const tenurePct   = Math.min(Math.round((totalMonths / 60) * 100), 100)
  const firstRole   = events[0]?.label.split("·")[0].trim() ?? ""
  const hasLinks    = !!(detail?.website || detail?.linkedin_url)
  const hasTeam     = !!(detail?.ceo || detail?.founders?.length)
  const hasInvestors = !!(detail?.key_investors?.length)

  const matchedExp = resume_experience.filter(e =>
    e.company.toLowerCase().includes(name.toLowerCase()) ||
    name.toLowerCase().includes(e.company.toLowerCase())
  )

  function fmtDate(iso: string | null | undefined): string {
    if (!iso) return "Present"
    try { return new Date(iso).toLocaleDateString("en-US", { month: "short", year: "numeric" }) }
    catch { return iso.slice(0, 7) }
  }

  const headerBtn = (child: React.ReactNode, onClick?: () => void) => (
    <button
      onClick={onClick}
      style={{ display: "flex", alignItems: "center", justifyContent: "center", width: 30, height: 30, borderRadius: 7, border: "1px solid var(--fk-line)", background: "transparent", cursor: "pointer", color: "var(--fk-ink-3)" }}
    >
      {child}
    </button>
  )

  return (
    <>
      {/* Backdrop */}
      <motion.div
        onClick={onClose}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
        style={{ position: "fixed", inset: 0, zIndex: 100, background: "rgba(0,0,0,0.45)", backdropFilter: "blur(4px)" }}
      />

      {/* Drawer panel */}
      <motion.div
        initial={{ x: "calc(100% + 16px)" }}
        animate={{ x: 0 }}
        exit={{ x: "calc(100% + 16px)" }}
        transition={{ type: "spring", stiffness: 320, damping: 32 }}
        style={{
          position: "fixed", top: 12, right: 12, bottom: 12, zIndex: 101,
          width: "min(560px, calc(100vw - 24px))",
          overflowY: "auto",
          background: "var(--fk-card)", border: "1px solid var(--fk-line)",
          borderRadius: "var(--fk-radius-lg)",
          boxShadow: "0 24px 64px rgba(0,0,0,0.18)",
        }}
      >

        {/* ── Header bar ── */}
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "14px 20px", borderBottom: "1px solid var(--fk-line)",
          position: "sticky", top: 0, background: "var(--fk-card)", zIndex: 1,
        }}>
          {headerBtn(<X size={15} />, onClose)}
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            {headerBtn(<Pencil size={14} />)}
            {headerBtn(<Share2 size={14} />)}
            {headerBtn(<MoreHorizontal size={14} />)}
          </div>
        </div>

        {/* ── Title block ── */}
        <div style={{ padding: "20px 24px 0", display: "flex", alignItems: "flex-start", gap: 14 }}>
          <CompanyLogo logoUrl={detail?.logo_url ?? null} name={name} size={48} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
              <h2 style={{ fontSize: 26, fontWeight: 700, color: "var(--fk-ink)", margin: 0, lineHeight: 1.2 }}>{name}</h2>
              {stageBadge(detail?.stage ?? null)}
            </div>
            {detail?.industry && (
              <div style={{ fontSize: 15, color: "var(--fk-ink-4)", marginTop: 4 }}>{detail.industry}</div>
            )}
          </div>
        </div>

        {/* ── Metadata rows ── */}
        <div style={{ padding: "14px 24px 0" }}>
          {detail?.founded     && <MetaRow icon={<Calendar   size={14} />} label="Founded"       value={String(detail.founded)} />}
          {detail?.headquarters && <MetaRow icon={<MapPin     size={14} />} label="Headquarters"  value={detail.headquarters} />}
          {detail?.headcount   && <MetaRow icon={<Users       size={14} />} label="Headcount"     value={`~${detail.headcount.toLocaleString()}`} />}
          {detail?.total_funding_usd && <MetaRow icon={<DollarSign size={14} />} label="Total Funding" value={fmtUsd(detail.total_funding_usd)} />}

          {/* Tenure progress row */}
          {totalMonths > 0 && (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 0", borderBottom: "1px solid var(--fk-line-2)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Briefcase size={14} color="var(--fk-ink-4)" />
                <span style={{ fontSize: 15, color: "var(--fk-ink-4)", fontWeight: 500 }}>Tenure</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div style={{ width: 100, height: 6, borderRadius: 999, background: "var(--fk-line)", overflow: "hidden" }}>
                  <div style={{ width: `${tenurePct}%`, height: "100%", background: "var(--fk-blue)", borderRadius: 999 }} />
                </div>
                <span style={{ fontSize: 15, color: "var(--fk-ink-3)", fontWeight: 500, minWidth: 40, textAlign: "right" }}>
                  {fmtMonths(totalMonths)}
                </span>
              </div>
            </div>
          )}

          {/* Your role row */}
          {firstRole && (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 0", borderBottom: "1px solid var(--fk-line-2)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Building2 size={14} color="var(--fk-ink-4)" />
                <span style={{ fontSize: 15, color: "var(--fk-ink-4)", fontWeight: 500 }}>Your Role</span>
              </div>
              <span style={{ fontSize: 15, color: "var(--fk-ink-2)", fontWeight: 500 }}>{firstRole}</span>
            </div>
          )}
        </div>

        {/* ── Description block ── */}
        {detail?.description && (
          <div style={{ padding: "16px 24px 0" }}>
            <div style={{ background: "var(--fk-card-2)", borderRadius: 10, padding: "14px 16px", fontSize: 15, color: "var(--fk-ink-3)", lineHeight: 1.65 }}>
              {detail.description}
            </div>
          </div>
        )}

        {/* ── Links section ── */}
        {hasLinks && (
          <div style={{ padding: "16px 24px 0" }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: "var(--fk-ink-4)", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: 10 }}>Links</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {detail?.website && (
                <a href={detail.website} target="_blank" rel="noopener noreferrer" style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "9px 14px", background: "var(--fk-card-2)", border: "1px solid var(--fk-line)", borderRadius: 10, textDecoration: "none", color: "var(--fk-ink-2)", fontSize: 15, fontWeight: 500 }}>
                  <Globe size={15} color="var(--fk-ink-3)" />
                  Website
                  <span style={{ fontSize: 13, color: "var(--fk-ink-4)" }}>
                    {detail.website.replace(/^https?:\/\/(www\.)?/, "").split("/")[0]}
                  </span>
                </a>
              )}
              {detail?.linkedin_url && (
                <a href={detail.linkedin_url} target="_blank" rel="noopener noreferrer" style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "9px 14px", background: "var(--fk-card-2)", border: "1px solid var(--fk-line)", borderRadius: 10, textDecoration: "none", color: "var(--fk-ink-2)", fontSize: 15, fontWeight: 500 }}>
                  <Link2 size={14} color="#0a66c2" />
                  LinkedIn
                </a>
              )}
            </div>
          </div>
        )}

        {/* ── Tabs ── */}
        <div style={{ padding: "20px 24px 0" }}>
          <div style={{ display: "flex", borderBottom: "1px solid var(--fk-line)" }}>
            {([
              { key: "roles"     as const, label: "Roles",     count: events.length },
              { key: "team"      as const, label: "Team",      count: 0 },
              { key: "investors" as const, label: "Investors", count: detail?.key_investors?.length ?? 0 },
            ]).map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                style={{
                  display: "inline-flex", alignItems: "center", gap: 6,
                  padding: "8px 14px", border: "none", background: "transparent",
                  cursor: "pointer", fontSize: 14, fontWeight: 500,
                  color: activeTab === tab.key ? "var(--fk-ink)" : "var(--fk-ink-4)",
                  borderBottom: activeTab === tab.key ? "2px solid var(--fk-blue)" : "2px solid transparent",
                  marginBottom: -1, transition: "color 0.12s",
                }}
              >
                {tab.label}
                {tab.count > 0 && (
                  <span style={{
                    fontSize: 11, fontWeight: 700, padding: "1px 6px", borderRadius: 999,
                    background: activeTab === tab.key ? "var(--fk-blue)" : "var(--fk-line)",
                    color: activeTab === tab.key ? "#fff" : "var(--fk-ink-4)",
                  }}>
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </div>

          <div style={{ paddingTop: 16, paddingBottom: 24 }}>

            {/* Roles tab */}
            {activeTab === "roles" && events.map((ev, i) => {
              const title   = ev.label.split("·")[0].trim()
              const period  = `${fmtDate(ev.start_date)} – ${ev.is_current ? "Present" : fmtDate(ev.end_date)}`
              const bullets = matchedExp.find(e => e.title === title)?.description ?? []
              return (
                <div key={ev.id} style={{ paddingBottom: 16, marginBottom: i < events.length - 1 ? 16 : 0, borderBottom: i < events.length - 1 ? "1px dashed var(--fk-line)" : "none" }}>
                  <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                    <input type="checkbox" readOnly style={{ marginTop: 3, width: 14, height: 14, accentColor: "var(--fk-blue)", flexShrink: 0, cursor: "default" }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 15, fontWeight: 600, color: "var(--fk-ink)" }}>{title}</div>
                      <div style={{ fontSize: 13, color: "var(--fk-ink-4)", marginTop: 3 }}>
                        {period}{ev.months ? ` · ${fmtMonths(ev.months)}` : ""}
                      </div>
                      {bullets.length > 0 && (
                        <div style={{ marginTop: 8, fontSize: 14, color: "var(--fk-ink-3)", lineHeight: 1.6 }}>
                          {bullets.slice(0, 2).map((b, bi) => (
                            <div key={bi} style={{ marginBottom: 4 }}>· {b}</div>
                          ))}
                        </div>
                      )}
                      {ev.tech_stack.length > 0 && (
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginTop: 8 }}>
                          {ev.tech_stack.map(t => (
                            <span key={t} style={{ fontSize: 12, padding: "2px 8px", borderRadius: 999, background: "var(--fk-card-2)", color: "var(--fk-ink-3)", border: "1px solid var(--fk-line)" }}>
                              {t}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <CompanyLogo logoUrl={detail?.logo_url ?? null} name={name} size={24} />
                  </div>
                </div>
              )
            })}

            {/* Team tab */}
            {activeTab === "team" && (
              hasTeam ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  {detail?.ceo       && <TeamRow label="CEO"      names={[detail.ceo]} />}
                  {detail?.founders?.length ? <TeamRow label="Founders" names={detail.founders} /> : null}
                </div>
              ) : <ModalEmptyState message="No team information available" />
            )}

            {/* Investors tab */}
            {activeTab === "investors" && (
              hasInvestors ? (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {detail!.key_investors!.map(inv => (
                    <span key={inv} style={{ fontSize: 14, padding: "5px 12px", borderRadius: 999, background: "var(--fk-card-2)", color: "var(--fk-ink-3)", border: "1px solid var(--fk-line)", fontWeight: 500 }}>
                      {inv}
                    </span>
                  ))}
                </div>
              ) : <ModalEmptyState message="No investor data available" />
            )}

          </div>
        </div>
      </motion.div>
    </>
  )
}

function MetaRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 0", borderBottom: "1px solid var(--fk-line-2)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--fk-ink-4)" }}>
        {icon}
        <span style={{ fontSize: 15, fontWeight: 500 }}>{label}</span>
      </div>
      <span style={{ fontSize: 15, color: "var(--fk-ink-2)", fontWeight: 500 }}>{value}</span>
    </div>
  )
}

function TeamRow({ label, names }: { label: string; names: string[] }) {
  const initials = names[0].split(/\s+/).slice(0, 2).map(w => w[0] ?? "").join("").toUpperCase()
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
      <div style={{ width: 34, height: 34, borderRadius: "50%", background: "var(--fk-card-2)", border: "1px solid var(--fk-line)", display: "grid", placeItems: "center", fontSize: 13, fontWeight: 700, color: "var(--fk-ink-3)", flexShrink: 0 }}>
        {initials}
      </div>
      <div>
        <div style={{ fontSize: 11, fontWeight: 600, color: "var(--fk-ink-4)", textTransform: "uppercase", letterSpacing: "0.06em" }}>{label}</div>
        <div style={{ fontSize: 15, color: "var(--fk-ink)", marginTop: 2 }}>{names.join(", ")}</div>
      </div>
    </div>
  )
}

function ModalEmptyState({ message }: { message: string }) {
  return (
    <div style={{ textAlign: "center", padding: "24px 0", fontSize: 13, color: "var(--fk-ink-4)" }}>
      {message}
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
            <div style={{ fontSize: 14, color: "var(--fk-ink-4)", marginTop: 2 }}>{detail.industry}</div>
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
