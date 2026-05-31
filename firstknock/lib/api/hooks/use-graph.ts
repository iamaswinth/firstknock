"use client"
import { useAuth } from "@clerk/nextjs"
import { useQuery } from "@tanstack/react-query"
import { authedRequest } from "../client"
import type { GraphResponse } from "../types"

export function useGraph(userId: string) {
  const { getToken } = useAuth()
  return useQuery({
    queryKey: ["graph", userId],
    queryFn: () => authedRequest<GraphResponse>(`/graph/${userId}`, getToken),
    staleTime: 5 * 60 * 1000,
    enabled: !!userId,
  })
}
