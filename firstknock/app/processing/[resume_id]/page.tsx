"use client"
import { use, useEffect } from "react"
import { useRouter } from "next/navigation"
import { useResumePoll } from "@/lib/api/hooks/use-resume-poll"
import { ProcessingStatus } from "@/components/upload/processing-status"

export default function ProcessingPage({
  params,
  searchParams,
}: {
  params: Promise<{ resume_id: string }>
  searchParams: Promise<{ user_id?: string }>
}) {
  const { resume_id } = use(params)
  const { user_id } = use(searchParams)
  const router = useRouter()
  const { data, isError } = useResumePoll(resume_id)

  useEffect(() => {
    if (data?.status === "enriched" && user_id) {
      router.push(`/profile/${user_id}`)
    }
  }, [data?.status, user_id, router])

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center gap-8 px-4"
      style={{ background: "var(--fk-outer)" }}
    >
      <div
        className="w-full max-w-sm rounded-2xl p-8"
        style={{
          background: "var(--fk-card)",
          border: "1px solid var(--fk-line)",
          boxShadow: "var(--fk-shadow)",
        }}
      >
        <div className="mb-6">
          <h2 className="text-lg font-semibold" style={{ color: "var(--fk-ink)" }}>
            Building your graph…
          </h2>
          <p className="text-sm mt-1" style={{ color: "var(--fk-ink-3)" }}>
            This takes 15–45 seconds. Hang tight.
          </p>
        </div>

        {isError ? (
          <p className="text-sm" style={{ color: "var(--fk-pink)" }}>
            Something went wrong. Please try again.
          </p>
        ) : (
          <ProcessingStatus status={data?.status ?? "extracted"} />
        )}
      </div>
    </div>
  )
}
