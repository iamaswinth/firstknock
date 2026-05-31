"use client"
import { useUser, useClerk } from "@clerk/nextjs"
import { createContext, useContext, useEffect, useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import { getResume, saveResume as storeResume, clearResume } from "@/lib/auth"

interface AuthUser {
  email: string
  clerkId: string
  userId: string
  resumeId: string
  name?: string
}

interface AuthContextValue {
  user: AuthUser | null
  isAuthed: boolean
  hasResume: boolean
  logout: () => void
  saveResume: (data: { userId: string; resumeId: string; name?: string }) => void
  clearResumeData: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { user: clerkUser, isLoaded, isSignedIn } = useUser()
  const { signOut } = useClerk()
  const router = useRouter()
  const [resumeData, setResumeData] = useState<{ userId: string; resumeId: string; name?: string } | null>(null)

  useEffect(() => {
    if (!isLoaded || !isSignedIn || !clerkUser) return
    const stored = getResume(clerkUser.id)
    if (stored) setResumeData({ userId: stored.userId, resumeId: stored.resumeId, name: stored.name })
  }, [isLoaded, isSignedIn, clerkUser?.id])

  const logout = useCallback(() => {
    signOut(() => router.push("/login"))
  }, [signOut, router])

  const saveResume = useCallback((data: { userId: string; resumeId: string; name?: string }) => {
    if (!clerkUser) return
    storeResume(clerkUser.id, data)
    setResumeData(data)
  }, [clerkUser])

  const clearResumeData = useCallback(() => {
    if (!clerkUser) return
    clearResume(clerkUser.id)
    setResumeData(null)
  }, [clerkUser])

  const user: AuthUser | null = isSignedIn && clerkUser
    ? {
        email: clerkUser.primaryEmailAddress?.emailAddress ?? "",
        clerkId: clerkUser.id,
        userId: resumeData?.userId ?? "",
        resumeId: resumeData?.resumeId ?? "",
        name: resumeData?.name ?? clerkUser.firstName ?? undefined,
      }
    : null

  return (
    <AuthContext.Provider value={{
      user,
      isAuthed: !!isSignedIn,
      hasResume: !!(resumeData?.userId),
      logout,
      saveResume,
      clearResumeData,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}
