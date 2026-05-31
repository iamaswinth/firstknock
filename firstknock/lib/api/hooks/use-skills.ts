"use client"
import { useAuth } from "@clerk/nextjs"
import { useQuery } from "@tanstack/react-query"
import { authedRequest } from "../client"
import type { SkillsResponse } from "../types"

export function useSkills(userId: string) {
  const { getToken } = useAuth()
  return useQuery({
    queryKey: ["skills", userId],
    queryFn: () => authedRequest<SkillsResponse>(`/skills/${userId}`, getToken),
    staleTime: 5 * 60 * 1000,
    enabled: !!userId,
  })
}
