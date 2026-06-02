"use client"
import { useAuth } from "@clerk/nextjs"
import { useQuery } from "@tanstack/react-query"
import { authedRequest } from "../client"
import type { SkillContextResponse } from "../types"

export function useSkillContext(userId: string) {
  const { getToken } = useAuth()
  return useQuery({
    queryKey: ["skill-context", userId],
    queryFn: () => authedRequest<SkillContextResponse>(`/skill-context/${userId}`, getToken),
    staleTime: 5 * 60 * 1000,
    enabled: !!userId,
  })
}
