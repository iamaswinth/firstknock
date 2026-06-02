"use client"
import { useState, useRef, DragEvent } from "react"
import { Upload } from "lucide-react"
import { useRouter } from "next/navigation"
import { apiClient } from "@/lib/api/client"
import type { IngestResponse } from "@/lib/api/types"

export function Dropzone() {
  const router = useRouter()
  const inputRef = useRef<HTMLInputElement>(null)
  const [email, setEmail] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function onDrop(e: DragEvent) {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) setFile(f)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!file || !email) return
    setLoading(true)
    setError(null)
    try {
      const form = new FormData()
      form.append("file", file)
      form.append("email", email)
      const res = await apiClient.postForm<IngestResponse>("/ingest", form)
      router.push(`/processing/${res.resume_id}?user_id=${res.user_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed")
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-lg flex flex-col gap-4">
      {/* Drop zone */}
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className="relative flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed cursor-pointer transition-colors p-10"
        style={{
          borderColor: dragging ? "var(--fk-brand)" : "var(--fk-line-2)",
          background: dragging ? "rgba(239,123,46,0.04)" : "var(--fk-card)",
        }}
      >
        <UploadIcon />
        {file ? (
          <div className="text-center">
            <p className="text-sm font-medium" style={{ color: "var(--fk-ink)" }}>{file.name}</p>
            <p className="text-xs mt-1" style={{ color: "var(--fk-ink-3)" }}>
              {(file.size / 1024).toFixed(0)} KB — click to change
            </p>
          </div>
        ) : (
          <div className="text-center">
            <p className="text-sm font-medium" style={{ color: "var(--fk-ink)" }}>
              Drop your résumé here
            </p>
            <p className="text-xs mt-1" style={{ color: "var(--fk-ink-3)" }}>
              PDF or DOCX · up to 10 MB
            </p>
          </div>
        )}
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && setFile(e.target.files[0])}
        />
      </div>

      {/* Email */}
      <input
        type="email"
        placeholder="your@email.com"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
        className="w-full px-4 py-3 rounded-xl border text-sm outline-none transition-colors"
        style={{
          background: "var(--fk-card)",
          borderColor: "var(--fk-line-2)",
          color: "var(--fk-ink)",
        }}
      />

      {error && (
        <p className="text-sm" style={{ color: "var(--fk-pink)" }}>{error}</p>
      )}

      <button
        type="submit"
        disabled={!file || !email || loading}
        className="w-full py-3 rounded-xl text-sm font-semibold text-white transition-opacity disabled:opacity-40"
        style={{ background: "var(--fk-ink)" }}
      >
        {loading ? "Uploading…" : "Analyse my résumé →"}
      </button>
    </form>
  )
}

function UploadIcon() {
  return (
    <div
      className="w-12 h-12 rounded-2xl flex items-center justify-center"
      style={{ background: "var(--fk-card-2)" }}
    >
      <Upload size={20} strokeWidth={1.5} color="var(--fk-ink-3)" />
    </div>
  )
}
