"use client"
import { useAuth } from "@clerk/nextjs"
import { useQuery } from "@tanstack/react-query"
import { authedRequest } from "../client"
import type { RoleFitResponse } from "../types"

export function useRoles(userId: string) {
  const { getToken } = useAuth()
  return useQuery({
    queryKey: ["roles", userId],
    queryFn: () => authedRequest<RoleFitResponse>(`/profile/${userId}/roles`, getToken),
    staleTime: 5 * 60 * 1000,
    enabled: !!userId,
  })
}
