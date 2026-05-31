const STORAGE_KEY = "fk_resumes"

export interface FKResumeRecord {
  userId: string
  resumeId: string
  name?: string
  ingestedAt: string
}

function read(): Record<string, FKResumeRecord> {
  if (typeof window === "undefined") return {}
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null") ?? {}
  } catch {
    return {}
  }
}

function write(store: Record<string, FKResumeRecord>) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(store))
}

export function getResume(clerkId: string): FKResumeRecord | null {
  return read()[clerkId] ?? null
}

export function saveResume(clerkId: string, data: { userId: string; resumeId: string; name?: string }) {
  const store = read()
  store[clerkId] = { ...data, ingestedAt: new Date().toISOString() }
  write(store)
}

export function clearResume(clerkId: string) {
  const store = read()
  delete store[clerkId]
  write(store)
}
