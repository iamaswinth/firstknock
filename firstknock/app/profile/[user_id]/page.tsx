"use client"
import { use, useState } from "react"
import { DashboardContent } from "@/components/dashboard/dashboard-content"
import { UploadModal } from "@/components/upload/upload-modal"

export default function ProfilePage({
  params,
}: {
  params: Promise<{ user_id: string }>
}) {
  const { user_id } = use(params)
  const [modalOpen, setModalOpen] = useState(false)

  return (
    <>
      <DashboardContent
        userId={user_id}
        onOpenUploadModal={() => setModalOpen(true)}
      />
      <UploadModal open={modalOpen} onOpenChange={setModalOpen} />
    </>
  )
}
