import { useEffect, useState } from 'react'
import { ensureUser, type AuthUser } from '../api/client'

export function useCurrentUser(): AuthUser | null {
  const [user, setUser] = useState<AuthUser | null>(() => {
    try {
      return ensureUserCached()
    } catch {
      return null
    }
  })

  useEffect(() => {
    let alive = true
    ensureUser().then((u) => {
      if (alive) setUser(u)
    })
    return () => {
      alive = false
    }
  }, [])

  return user
}

// localStorage 同步读取，避免首屏闪烁；拿不到则由 effect 异步补齐
function ensureUserCached(): AuthUser | null {
  const raw = localStorage.getItem('tn_user')
  return raw ? (JSON.parse(raw) as AuthUser) : null
}
