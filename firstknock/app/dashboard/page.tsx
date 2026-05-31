"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/providers/auth-provider"
import { useAuth as useClerkAuth } from "@clerk/nextjs"
import { useQueryClient } from "@tanstack/react-query"
import { authedDelete } from "@/lib/api/client"
import type { DeleteResumeResponse } from "@/lib/api/types"
import { DashboardContent } from "@/components/dashboard/dashboard-content"
import { EmptyDashboard } from "@/components/dashboard/empty-dashboard"
import { UploadModal } from "@/components/upload/upload-modal"

export default function DashboardPage() {
  const { user, clearResumeData } = useAuth()
  const { getToken } = useClerkAuth()
  const queryClient = useQueryClient()
  const router = useRouter()

  const [modalOpen, setModalOpen] = useState(false)
  const [reingestOpen, setReingestOpen] = useState(false)

  async function handleDelete() {
    const resumeId = user?.resumeId
    if (!resumeId) return
    try {
      await authedDelete<DeleteResumeResponse>(`/resume/${resumeId}`, getToken)
    } catch {
      // If delete fails (e.g. already gone), still clear local state
    }
    queryClient.clear()
    clearResumeData()
    router.push("/")
  }

  return (
    <>
      {user?.userId ? (
        <DashboardContent
          userId={user.userId}
          onOpenUploadModal={() => setModalOpen(true)}
          onReingest={() => setReingestOpen(true)}
          onDelete={handleDelete}
        />
      ) : (
        <EmptyDashboard
          name={user?.name ?? user?.email?.split("@")[0]}
          onUpload={() => setModalOpen(true)}
        />
      )}

      {/* Fresh ingest modal */}
      <UploadModal
        open={modalOpen}
        onOpenChange={setModalOpen}
      />

      {/* Reingest modal — passes current resumeId to call /resume/{id}/reingest */}
      <UploadModal
        open={reingestOpen}
        onOpenChange={setReingestOpen}
        reingestResumeId={user?.resumeId}
      />
    </>
  )
}
