"use client"

import { useState, useEffect, useRef } from "react"

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
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
            <path d="M10 13a4 4 0 0 0 5.66 0l2-2a4 4 0 1 0-5.66-5.66l-1 1M14 11a4 4 0 0 0-5.66 0l-2 2A4 4 0 1 0 6 18.66l1-1" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>

      <div style={{ flex: 1 }} />

      {/* Synced pill */}
      <button style={pillStyle}>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
          <rect x="4" y="5" width="16" height="16" rx="2.5" stroke="currentColor" strokeWidth="1.7" />
          <path d="M4 9h16M9 3v4M15 3v4" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
        </svg>
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
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
            <path d="M20 11a8 8 0 1 0-.5 3.5M20 5v6h-6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span>{resumeName}</span>
          <svg
            width="14" height="14" viewBox="0 0 24 24" fill="none"
            style={{ transform: menuOpen ? "rotate(180deg)" : "none", transition: "transform .15s" }}
          >
            <path d="m7 10 5 5 5-5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
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
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Update resume
            </button>

            {/* Delete action */}
            <button
              onClick={() => { setMenuOpen(false); setConfirmDelete(true) }}
              style={{ ...menuItemStyle, color: "var(--fk-pink)" }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M3 6h18M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6M10 11v6M14 11v6M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
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
