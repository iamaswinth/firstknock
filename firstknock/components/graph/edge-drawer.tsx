"use client"
import { AnimatePresence, motion } from "framer-motion"
import type { SkillContextLink } from "@/lib/api/types"

interface EdgeDrawerProps {
  link: SkillContextLink | null
  onClose: () => void
}

export function EdgeDrawer({ link, onClose }: EdgeDrawerProps) {
  return (
    <AnimatePresence>
      {link && (
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
          <div className="flex items-start justify-between p-5 pb-4">
            <div>
              <span
                className="text-[13px] fk-mono px-2 py-0.5 rounded"
                style={{ background: "var(--fk-card-2)", color: "var(--fk-ink-4)" }}
              >
                {link.type.replace(/_/g, " ")}
              </span>
              <h3 className="text-[17px] font-semibold mt-2" style={{ color: "var(--fk-ink)" }}>
                {link.type === "WORKED_AT"
                  ? String(link.properties?.title ?? "Experience")
                  : link.type === "STUDIED_AT"
                  ? String(link.properties?.degree ?? "Education")
                  : link.type}
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
            {link.type === "WORKED_AT" && <WorkedAtDetail props={link.properties ?? {}} />}
            {link.type === "STUDIED_AT" && <StudiedAtDetail props={link.properties ?? {}} />}
            {(link.type === "USED_SKILL" || link.type === "USES") && (
              <p className="text-[13px]" style={{ color: "var(--fk-ink-3)" }}>
                Confidence:{" "}
                <span style={{ color: "var(--fk-ink)" }}>
                  {link.properties?.confidence != null
                    ? `${Math.round(Number(link.properties.confidence) * 100)}%`
                    : "—"}
                </span>
              </p>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div
      className="flex items-start justify-between gap-2 py-2 border-b"
      style={{ borderColor: "var(--fk-line)" }}
    >
      <span className="text-[13px]" style={{ color: "var(--fk-ink-3)" }}>{label}</span>
      <span className="text-[13px] font-medium text-right" style={{ color: "var(--fk-ink)" }}>{value}</span>
    </div>
  )
}

function formatDate(val: unknown): string {
  if (!val) return "Present"
  const s = String(val).trim()
  if (!s || /^(present|current|now)$/i.test(s)) return "Present"
  // YYYY-MM → "MMM YYYY"
  const m = s.match(/^(\d{4})-(\d{2})/)
  if (m) {
    const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    const mon = months[parseInt(m[2], 10) - 1]
    return mon ? `${mon} ${m[1]}` : s
  }
  return s
}

function WorkedAtDetail({ props }: { props: Record<string, unknown> }) {
  const start      = formatDate(props.start_date)
  const end        = formatDate(props.end_date)
  const months     = props.months != null ? Number(props.months) : null
  const duration   = months != null ? `${months} mo` : null
  const period     = `${start} – ${end}${duration ? ` · ${duration}` : ""}`

  const description = Array.isArray(props.description)
    ? (props.description as unknown[]).map(String)
    : props.description ? [String(props.description)] : []

  const skills = Array.isArray(props.skills_used)
    ? (props.skills_used as unknown[]).map(String)
    : Array.isArray(props.linkedin_job_skills)
    ? (props.linkedin_job_skills as unknown[]).map(String)
    : []

  return (
    <div className="flex flex-col gap-3">
      <Row label="Period" value={period} />
      {props.location && <Row label="Location" value={String(props.location)} />}

      {description.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <span className="text-[11px] fk-mono uppercase" style={{ color: "var(--fk-ink-4)" }}>
            Highlights
          </span>
          <ul className="flex flex-col gap-1.5">
            {description.map((bullet, i) => (
              <li key={i} className="flex gap-2">
                <span style={{ color: "var(--fk-brand)", marginTop: 3, flexShrink: 0 }}>–</span>
                <span className="text-[13px] leading-relaxed" style={{ color: "var(--fk-ink-2)" }}>
                  {bullet}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {skills.length > 0 && (
        <div className="flex flex-col gap-2">
          <span className="text-[11px] fk-mono uppercase" style={{ color: "var(--fk-ink-4)" }}>
            Skills used
          </span>
          <div className="flex flex-wrap gap-1.5">
            {skills.map((s) => (
              <span
                key={s}
                className="px-2 py-0.5 rounded-full text-[12px] font-medium"
                style={{ background: "var(--fk-card-2)", color: "var(--fk-ink-2)" }}
              >
                {s}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function StudiedAtDetail({ props }: { props: Record<string, unknown> }) {
  const start = props.start_year ? String(props.start_year) : null
  const end   = props.end_year   ? String(props.end_year)   : null
  const period = start && end ? `${start} – ${end}` : start ?? end ?? null
  return (
    <div className="flex flex-col">
      {props.field  && <Row label="Field"  value={String(props.field)} />}
      {period       && <Row label="Period" value={period} />}
    </div>
  )
}
