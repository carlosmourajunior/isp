// Guarda os tokens JWT fora do React (módulo simples, sem dependências) para
// que o interceptor do axios em api.ts consiga ler/limpar o token sem
// precisar importar o AuthContext (evita ciclo de import).
const ACCESS_KEY = 'isp_access_token'
const REFRESH_KEY = 'isp_refresh_token'
const USERNAME_KEY = 'isp_username'

type Listener = (accessToken: string | null) => void
const listeners = new Set<Listener>()

let accessToken: string | null = localStorage.getItem(ACCESS_KEY)

export function getAccessToken(): string | null {
  return accessToken
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY)
}

export function getStoredUsername(): string | null {
  return localStorage.getItem(USERNAME_KEY)
}

export function setTokens(access: string, refresh?: string, username?: string) {
  accessToken = access
  localStorage.setItem(ACCESS_KEY, access)
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
  if (username) localStorage.setItem(USERNAME_KEY, username)
  listeners.forEach((listener) => listener(accessToken))
}

export function clearTokens() {
  accessToken = null
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
  localStorage.removeItem(USERNAME_KEY)
  listeners.forEach((listener) => listener(null))
}

/** Chamado pelo AuthProvider para reagir a mudanças de token feitas pelo interceptor do axios. */
export function onTokenChange(listener: Listener): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}
