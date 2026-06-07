"use client"
import { useState, useRef, useEffect, DragEvent } from "react"
import { X, Upload, Check } from "lucide-react"
import { Dialog } from "@base-ui/react/dialog"
import { useAuth } from "@/providers/auth-provider"
import { useAuth as useClerkAuth } from "@clerk/nextjs"
import { authedRequest, authedPostForm } from "@/lib/api/client"
import { ProcessingStatus } from "@/components/upload/processing-status"
import { useQueryClient } from "@tanstack/react-query"

type Step = "upload" | "processing" | "done"

export interface ResumeContext {
  name?: string
  githubUrl?: string
  linkedinUrl?: string
  companyNames: string[]
  projectCount: number
  skillCount: number
}

interface UploadModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** If set, calls POST /resume/{reingestResumeId}/reingest instead of POST /ingest */
  reingestResumeId?: string
}

export function UploadModal({ open, onOpenChange, reingestResumeId }: UploadModalProps) {
  const { user, saveResume } = useAuth()
  const { getToken } = useClerkAuth()
  const queryClient = useQueryClient()

  const [step, setStep] = useState<Step>("upload")
  const [file, setFile] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [resumeId, setResumeId] = useState<string | null>(null)
  const [resumeStatus, setResumeStatus] = useState("queued")
  const [resumeCtx, setResumeCtx] = useState<ResumeContext>({ companyNames: [], projectCount: 0, skillCount: 0 })
  const inputRef = useRef<HTMLInputElement>(null)

  // Reset state when modal opens
  useEffect(() => {
    if (open) {
      setStep("upload")
      setFile(null)
      setError(null)
      setResumeId(null)
      setResumeStatus("queued")
      setResumeCtx({ companyNames: [], projectCount: 0, skillCount: 0 })
      setLoading(false)
    }
  }, [open])

  // Poll Resume.status until enrichment completes or pipeline fails
  useEffect(() => {
    if (step !== "processing" || !resumeId) return
    const id = setInterval(async () => {
      try {
        const res = await authedRequest<{
          status: string
          user_id: string
          identity?: { name?: string; github_url?: string; linkedin_url?: string }
          experience?: { company?: string }[]
          projects?: unknown[]
          skills?: Record<string, unknown[]>
        }>(`/resume/${resumeId}`, getToken)
        setResumeStatus(res.status)
        // Update context whenever new data arrives from the DB
        if (res.identity || res.experience || res.skills) {
          const skillCount = res.skills
            ? Object.values(res.skills).reduce((n, v) => n + (Array.isArray(v) ? v.length : 0), 0)
            : 0
          setResumeCtx({
            name: res.identity?.name,
            githubUrl: res.identity?.github_url,
            linkedinUrl: res.identity?.linkedin_url,
            companyNames: (res.experience ?? []).map(e => e.company).filter(Boolean) as string[],
            projectCount: (res.projects ?? []).length,
            skillCount,
          })
        }
        if (res.status === "enriched") {
          clearInterval(id)
          saveResume({ userId: res.user_id, resumeId })
          queryClient.invalidateQueries()
          setStep("done")
          setTimeout(() => onOpenChange(false), 1800)
        } else if (res.status === "failed") {
          clearInterval(id)
          setError("Processing failed — please try uploading again.")
          setStep("upload")
        }
      } catch { /* keep polling */ }
    }, 3000)
    return () => clearInterval(id)
  }, [step, resumeId, saveResume, queryClient, onOpenChange])

  function onDrop(e: DragEvent) {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f && (f.type === "application/pdf" || f.name.endsWith(".docx"))) {
      setFile(f)
    }
  }

  async function handleUpload() {
    if (!file) return
    setLoading(true)
    setError(null)
    try {
      const form = new FormData()
      form.append("file", file)
      const path = reingestResumeId
        ? `/resume/${reingestResumeId}/reingest`
        : "/ingest"
      const res = await authedPostForm<{ resume_id: string; user_id: string }>(path, form, getToken)
      // Save userId right away so dashboard knows a resume exists
      saveResume({ userId: res.user_id, resumeId: res.resume_id, name: file.name })
      setResumeId(res.resume_id)
      setStep("processing")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed — is the backend running?")
      setLoading(false)
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Backdrop
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 50,
            background: "rgba(20,22,27,0.35)",
            backdropFilter: "blur(4px)",
            transition: "opacity 0.2s",
          }}
        />
        <Dialog.Popup
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 51,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 24,
            pointerEvents: "none",
          }}
        >
          <div
            style={{
              width: "100%",
              maxWidth: 480,
              background: "var(--fk-card)",
              border: "1px solid var(--fk-line)",
              borderRadius: "var(--fk-radius-lg)",
              boxShadow: "0 4px 6px rgba(20,22,27,0.04), 0 20px 50px rgba(20,22,27,0.14)",
              padding: 28,
              pointerEvents: "all",
            }}
          >
            {step === "upload" && (
              <UploadStep
                file={file}
                setFile={setFile}
                dragging={dragging}
                setDragging={setDragging}
                onDrop={onDrop}
                inputRef={inputRef}
                email={user?.email ?? ""}
                loading={loading}
                error={error}
                onUpload={handleUpload}
                onClose={() => onOpenChange(false)}
                isReingest={!!reingestResumeId}
              />
            )}
            {step === "processing" && (
              <ProcessingStep status={resumeStatus} context={resumeCtx} />
            )}
            {step === "done" && (
              <DoneStep onClose={() => onOpenChange(false)} />
            )}
          </div>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

// ── Step 1: Upload ──────────────────────────────────────────────────────────

interface UploadStepProps {
  file: File | null
  setFile: (f: File | null) => void
  dragging: boolean
  setDragging: (d: boolean) => void
  onDrop: (e: DragEvent<HTMLDivElement>) => void
  inputRef: React.RefObject<HTMLInputElement | null>
  email: string
  loading: boolean
  error: string | null
  onUpload: () => void
  onClose: () => void
  isReingest?: boolean
}

function UploadStep({ file, setFile, dragging, setDragging, onDrop, inputRef, email, loading, error, onUpload, onClose, isReingest }: UploadStepProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <p style={{ fontSize: 20, fontWeight: 600, letterSpacing: "-0.015em", color: "var(--fk-ink)", margin: 0 }}>
            {isReingest ? "Update your résumé" : "Analyse your résumé"}
          </p>
          <p style={{ fontSize: 13, color: "var(--fk-ink-3)", margin: "4px 0 0", lineHeight: 1.5 }}>
            {isReingest
              ? "Upload a new file — your old data will be replaced."
              : "We'll parse it, build a skill graph, and infer hidden skills."}
          </p>
        </div>
        <button
          onClick={onClose}
          style={{
            width: 28, height: 28, borderRadius: 8,
            background: "var(--fk-card-2)", border: "none",
            display: "grid", placeItems: "center",
            color: "var(--fk-ink-3)", cursor: "pointer", flexShrink: 0,
          }}
        >
          <X size={14} strokeWidth={2} />
        </button>
      </div>

      {/* Drop zone */}
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        style={{
          border: `2px dashed ${dragging ? "var(--fk-brand)" : "var(--fk-line-2)"}`,
          borderRadius: 14,
          padding: "32px 24px",
          textAlign: "center",
          cursor: "pointer",
          background: dragging ? "rgba(239,123,46,0.04)" : "var(--fk-card)",
          transition: "border-color .15s, background .15s",
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx"
          style={{ display: "none" }}
          onChange={(e) => e.target.files?.[0] && setFile(e.target.files[0])}
        />
        {/* Upload icon */}
        <div style={{
          width: 44, height: 44, borderRadius: 12,
          background: "var(--fk-well)",
          display: "grid", placeItems: "center",
          margin: "0 auto 12px",
        }}>
          <Upload size={20} strokeWidth={1.5} color="var(--fk-ink-3)" />
        </div>
        {file ? (
          <>
            <p style={{ fontSize: 14, fontWeight: 600, color: "var(--fk-ink)", margin: 0 }}>{file.name}</p>
            <p style={{ fontSize: 12, color: "var(--fk-ink-3)", margin: "4px 0 0" }}>
              {(file.size / 1024).toFixed(0)} KB — click to change
            </p>
          </>
        ) : (
          <>
            <p style={{ fontSize: 14, fontWeight: 500, color: "var(--fk-ink)", margin: 0 }}>
              Drop your résumé here
            </p>
            <p style={{ fontSize: 12, color: "var(--fk-ink-3)", margin: "4px 0 0" }}>
              PDF or DOCX · up to 10 MB
            </p>
          </>
        )}
      </div>

      {/* Email (pre-filled, read-only) */}
      <div>
        <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "var(--fk-ink-3)", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.06em" }}>
          Email
        </label>
        <input
          type="email"
          value={email}
          readOnly
          style={{
            height: 38, width: "100%", boxSizing: "border-box",
            border: "1px solid var(--fk-line-2)", borderRadius: 10,
            padding: "0 12px", fontSize: 13,
            background: "var(--fk-well)", color: "var(--fk-ink-3)",
            outline: "none",
          }}
        />
      </div>

      {error && (
        <p style={{ fontSize: 13, color: "var(--fk-pink)", margin: 0 }}>{error}</p>
      )}

      <button
        onClick={handleUpload}
        disabled={!file || loading}
        style={{
          height: 42, width: "100%", borderRadius: 12,
          background: "var(--fk-ink)", color: "#fff",
          fontSize: 14, fontWeight: 600, border: "none",
          cursor: file && !loading ? "pointer" : "not-allowed",
          opacity: file && !loading ? 1 : 0.4,
          transition: "opacity .15s",
        }}
      >
        {loading ? "Uploading…" : isReingest ? "Update résumé →" : "Analyse résumé →"}
      </button>
    </div>
  )

  function handleUpload() {
    onUpload()
  }
}

// ── Step 2: Processing ──────────────────────────────────────────────────────

function ProcessingStep({ status, context }: { status: string; context: ResumeContext }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div>
        <p style={{ fontSize: 20, fontWeight: 600, letterSpacing: "-0.015em", color: "var(--fk-ink)", margin: 0 }}>
          Building your profile
        </p>
        <p style={{ fontSize: 13, color: "var(--fk-ink-3)", margin: "4px 0 0" }}>
          Hang tight — usually done in under a minute.
        </p>
      </div>

      <ProcessingStatus status={status} context={context} />

      <div style={{ display: "flex", alignItems: "center", gap: 8, paddingTop: 4 }}>
        <span style={{
          width: 8, height: 8, borderRadius: "50%",
          background: "var(--fk-brand)",
          display: "inline-block",
          animation: "fk-blink 1.4s ease-in-out infinite",
        }} />
        <span style={{ fontSize: 12, color: "var(--fk-ink-3)", fontFamily: "var(--font-geist-mono), monospace" }}>
          Processing…
        </span>
      </div>
    </div>
  )
}

// ── Step 3: Done ────────────────────────────────────────────────────────────

function DoneStep({ onClose }: { onClose: () => void }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 20, padding: "8px 0" }}>
      {/* Green check */}
      <div style={{
        width: 56, height: 56, borderRadius: "50%",
        background: "var(--fk-green)",
        display: "grid", placeItems: "center",
      }}>
        <Check size={24} strokeWidth={2.4} color="#fff" />
      </div>

      <div style={{ textAlign: "center" }}>
        <p style={{ fontSize: 20, fontWeight: 600, letterSpacing: "-0.015em", color: "var(--fk-ink)", margin: 0 }}>
          Your graph is ready ✦
        </p>
        <p style={{ fontSize: 13, color: "var(--fk-ink-3)", margin: "6px 0 0" }}>
          Closing in a moment…
        </p>
      </div>

      <button
        onClick={onClose}
        style={{
          height: 42, width: "100%", borderRadius: 12,
          background: "var(--fk-ink)", color: "#fff",
          fontSize: 14, fontWeight: 600, border: "none",
          cursor: "pointer",
        }}
      >
        View dashboard
      </button>
    </div>
  )
}
