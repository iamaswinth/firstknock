"use client"
import { useAuth } from "@clerk/nextjs"
import { useQuery } from "@tanstack/react-query"
import { authedRequest } from "../client"
import type { ProfileResponse } from "../types"

export function useProfile(userId: string) {
  const { getToken } = useAuth()
  return useQuery({
    queryKey: ["profile", userId],
    queryFn: () => authedRequest<ProfileResponse>(`/profile/${userId}`, getToken),
    staleTime: 5 * 60 * 1000,
    enabled: !!userId,
  })
}
