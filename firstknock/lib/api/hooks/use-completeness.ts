"use client"
import { useAuth } from "@clerk/nextjs"
import { useQuery } from "@tanstack/react-query"
import { authedRequest } from "../client"
import type { ProfileCompletenessResponse } from "../types"

export function useCompleteness(userId: string) {
  const { getToken } = useAuth()
  return useQuery({
    queryKey: ["completeness", userId],
    queryFn: () =>
      authedRequest<ProfileCompletenessResponse>(
        `/profile/${userId}/completeness`,
        getToken,
      ),
    staleTime: 5 * 60 * 1000,
    enabled: !!userId,
  })
}
