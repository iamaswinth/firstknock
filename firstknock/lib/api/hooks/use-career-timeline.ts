"use client"
import { useAuth } from "@clerk/nextjs"
import { useQuery } from "@tanstack/react-query"
import { authedRequest } from "../client"
import type { CareerTimelineResponse } from "../types"

export function useCareerTimeline(userId: string) {
  const { getToken } = useAuth()
  return useQuery({
    queryKey: ["career-timeline", userId],
    queryFn: () => authedRequest<CareerTimelineResponse>(`/career-timeline/${userId}`, getToken),
    staleTime: 5 * 60 * 1000,
    enabled: !!userId,
  })
}
