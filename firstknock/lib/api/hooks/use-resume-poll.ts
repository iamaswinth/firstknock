"use client"
import { useAuth } from "@clerk/nextjs"
import { useQuery } from "@tanstack/react-query"
import { authedRequest } from "../client"
import type { ResumeStatusResponse } from "../types"

export function useResumePoll(resumeId: string) {
  const { getToken } = useAuth()
  return useQuery({
    queryKey: ["resume", resumeId],
    queryFn: () => authedRequest<ResumeStatusResponse>(`/resume/${resumeId}`, getToken),
    refetchInterval: (query) =>
      query.state.data?.status === "enriched" ? false : 3000,
    enabled: !!resumeId,
  })
}
