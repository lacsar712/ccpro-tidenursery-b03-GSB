const TOKEN_KEY = 'tn_token'
const USER_KEY = 'tn_user'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export type AuthUser = {
  id: number
  username: string
  role: string
  display_name: string
}

export function getUser(): AuthUser | null {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as AuthUser
  } catch {
    return null
  }
}

export function setUser(user: AuthUser) {
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearAuth() {
  clearToken()
  localStorage.removeItem(USER_KEY)
}

let userPromise: Promise<AuthUser | null> | null = null

// 已登录但本地无用户信息（旧会话）时，用 /me 引导一次
export function ensureUser(): Promise<AuthUser | null> {
  const cached = getUser()
  if (cached) return Promise.resolve(cached)
  if (!getToken()) return Promise.resolve(null)
  if (!userPromise) {
    userPromise = api<AuthUser>('/api/auth/me')
      .then((u) => {
        setUser(u)
        return u
      })
      .catch(() => null)
  }
  return userPromise
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers || {})
  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const res = await fetch(path, { ...options, headers })
  if (res.status === 204) return undefined as T

  const text = await res.text()
  let data: unknown = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = { detail: text }
  }

  if (!res.ok) {
    const detail =
      typeof data === 'object' && data && 'detail' in data
        ? String((data as { detail: unknown }).detail)
        : `请求失败 (${res.status})`
    throw new Error(detail)
  }
  return data as T
}

export async function login(username: string, password: string) {
  const body = new URLSearchParams()
  body.set('username', username)
  body.set('password', password)
  return api<{
    access_token: string
    token_type: string
    user: {
      id: number
      username: string
      role: string
      display_name: string
    }
  }>('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
}
