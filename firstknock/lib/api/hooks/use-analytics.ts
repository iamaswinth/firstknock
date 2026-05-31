"use client"
import { useAuth } from "@clerk/nextjs"
import { useQuery } from "@tanstack/react-query"
import { authedRequest } from "../client"
import type { AnalyticsResponse } from "../types"

export function useAnalytics(userId: string) {
  const { getToken } = useAuth()
  return useQuery({
    queryKey: ["analytics", userId],
    queryFn: () => authedRequest<AnalyticsResponse>(`/analytics/${userId}`, getToken),
    staleTime: 5 * 60 * 1000,
    enabled: !!userId,
  })
}
