const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new Error(`${res.status} ${res.statusText}${text ? `: ${text}` : ""}`)
  }
  return res.json() as Promise<T>
}

export type GetToken = () => Promise<string | null>

export async function authedRequest<T>(
  path: string,
  getToken: GetToken,
  init?: RequestInit,
): Promise<T> {
  const token = await getToken()
  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string>),
  }
  if (token) headers["Authorization"] = `Bearer ${token}`

  return request<T>(path, { ...init, headers })
}

export async function authedPostForm<T>(
  path: string,
  form: FormData,
  getToken: GetToken,
): Promise<T> {
  const token = await getToken()
  const headers: Record<string, string> = {}
  if (token) headers["Authorization"] = `Bearer ${token}`

  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers,
    body: form,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new Error(`${res.status} ${res.statusText}${text ? `: ${text}` : ""}`)
  }
  return res.json() as Promise<T>
}

export async function authedDelete<T>(
  path: string,
  getToken: GetToken,
): Promise<T> {
  const token = await getToken()
  const headers: Record<string, string> = { "Content-Type": "application/json" }
  if (token) headers["Authorization"] = `Bearer ${token}`
  return request<T>(path, { method: "DELETE", headers })
}

export const apiClient = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  postForm: <T>(path: string, form: FormData) =>
    request<T>(path, { method: "POST", headers: {}, body: form }),
}
