"use client"

import { useState, useEffect, useRef } from "react"
import { Link2, Calendar, RotateCcw, ChevronDown, Upload, Trash2 } from "lucide-react"

interface TitleBarProps {
  syncDate?: string
  resumeName?: string
  totalMonths?: number | null
  onUpload?: () => void
  onReingest?: () => void
  onDelete?: () => void
}

export function TitleBar({ syncDate = "May 29", resumeName = "resume.pdf", onUpload, onReingest, onDelete }: TitleBarProps) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  // Close on outside click
  useEffect(() => {
    if (!menuOpen && !confirmDelete) return
    function onOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
        setConfirmDelete(false)
      }
    }
    document.addEventListener("mousedown", onOutside)
    return () => document.removeEventListener("mousedown", onOutside)
  }, [menuOpen, confirmDelete])

  return (
    <div id="top" style={{ display: "flex", alignItems: "center", gap: 16, margin: "22px 0 18px", flexWrap: "wrap" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <h1 style={{ margin: 0, fontSize: 38, fontWeight: 600, letterSpacing: "-0.025em", color: "var(--fk-ink)" }}>
          Overview
        </h1>
        <button style={{
          width: 30, height: 30, borderRadius: "50%",
          border: "1px solid var(--fk-line-2)", background: "var(--fk-card)",
          display: "grid", placeItems: "center", color: "var(--fk-ink-3)", cursor: "pointer",
        }}>
          <Link2 size={15} strokeWidth={1.7} />
        </button>
      </div>

      <div style={{ flex: 1 }} />

      {/* Synced pill */}
      <button style={pillStyle}>
        <Calendar size={15} strokeWidth={1.7} />
        <span>Synced · {syncDate}</span>
      </button>

      <span style={{ color: "var(--fk-ink-4)", fontSize: 13, padding: "0 2px" }}>from</span>

      {/* Resume pill + dropdown */}
      <div ref={menuRef} style={{ position: "relative" }}>
        <button
          style={{ ...pillStyle, background: menuOpen ? "var(--fk-card-2)" : "var(--fk-card)" }}
          onClick={() => { setMenuOpen((v) => !v); setConfirmDelete(false) }}
          title="Manage resume"
        >
          <RotateCcw size={15} strokeWidth={1.7} />
          <span>{resumeName}</span>
          <ChevronDown size={14} strokeWidth={1.8} style={{ transform: menuOpen ? "rotate(180deg)" : "none", transition: "transform .15s" }} />
        </button>

        {/* Dropdown menu */}
        {menuOpen && !confirmDelete && (
          <div style={{
            position: "absolute", top: "calc(100% + 6px)", right: 0, zIndex: 100,
            background: "var(--fk-card)", border: "1px solid var(--fk-line)",
            borderRadius: 12, boxShadow: "var(--fk-shadow)", minWidth: 200,
            overflow: "hidden",
          }}>
            {/* Filename row */}
            <div style={{ padding: "10px 14px 8px", borderBottom: "1px solid var(--fk-line-2)" }}>
              <div style={{ fontSize: 11, color: "var(--fk-ink-4)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 3 }}>
                Current resume
              </div>
              <div style={{ fontSize: 13, color: "var(--fk-ink-2)", fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {resumeName}
              </div>
            </div>

            {/* Update action */}
            <button
              onClick={() => { setMenuOpen(false); onReingest?.() }}
              style={menuItemStyle}
            >
              <Upload size={14} strokeWidth={1.7} />
              Update resume
            </button>

            {/* Delete action */}
            <button
              onClick={() => { setMenuOpen(false); setConfirmDelete(true) }}
              style={{ ...menuItemStyle, color: "var(--fk-pink)" }}
            >
              <Trash2 size={14} strokeWidth={1.7} />
              Delete resume
            </button>
          </div>
        )}

        {/* Delete confirmation */}
        {confirmDelete && (
          <div style={{
            position: "absolute", top: "calc(100% + 6px)", right: 0, zIndex: 100,
            background: "var(--fk-card)", border: "1px solid var(--fk-line)",
            borderRadius: 12, boxShadow: "var(--fk-shadow)", width: 260,
            padding: 16, display: "flex", flexDirection: "column", gap: 14,
          }}>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600, color: "var(--fk-ink)", marginBottom: 5 }}>
                Delete all resume data?
              </div>
              <div style={{ fontSize: 12.5, color: "var(--fk-ink-3)", lineHeight: 1.5 }}>
                This removes your profile, skill graph, and all inferred data. It cannot be undone.
              </div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={() => setConfirmDelete(false)}
                style={{ flex: 1, height: 34, borderRadius: 8, border: "1px solid var(--fk-line-2)", background: "var(--fk-card-2)", fontSize: 13, fontWeight: 500, color: "var(--fk-ink-2)", cursor: "pointer" }}
              >
                Cancel
              </button>
              <button
                onClick={() => { setConfirmDelete(false); onDelete?.() }}
                style={{ flex: 1, height: 34, borderRadius: 8, border: "none", background: "var(--fk-pink)", fontSize: 13, fontWeight: 600, color: "#fff", cursor: "pointer" }}
              >
                Delete
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

const pillStyle: React.CSSProperties = {
  display: "inline-flex", alignItems: "center", gap: 8,
  height: 38, padding: "0 13px",
  background: "var(--fk-card)", border: "1px solid var(--fk-line-2)",
  borderRadius: 11, fontSize: 13, fontWeight: 500, color: "var(--fk-ink-2)",
  cursor: "pointer",
}

const menuItemStyle: React.CSSProperties = {
  display: "flex", alignItems: "center", gap: 10,
  width: "100%", padding: "10px 14px",
  background: "transparent", border: "none",
  fontSize: 13, fontWeight: 500, color: "var(--fk-ink-2)",
  cursor: "pointer", textAlign: "left",
}
