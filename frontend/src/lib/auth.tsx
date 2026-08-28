import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { api } from './api'
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  getStoredUsername,
  onTokenChange,
  setTokens,
} from './tokenStore'

interface AuthContextValue {
  isAuthenticated: boolean
  username: string | null
  isLoading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [accessToken, setAccessToken] = useState(getAccessToken())
  const [username, setUsername] = useState<string | null>(getStoredUsername())
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => onTokenChange(setAccessToken), [])

  useEffect(() => {
    // Só o refresh token sobrevive a um F5 (o access token vive em memória).
    // Ao montar, se houver refresh token mas nenhum access token ainda,
    // tenta renovar antes de mandar o usuário pro login.
    async function bootstrap() {
      if (!getAccessToken() && getRefreshToken()) {
        try {
          const response = await api.post('/auth/refresh/', { refresh: getRefreshToken() })
          setTokens(response.data.access)
        } catch {
          clearTokens()
        }
      }
      setIsLoading(false)
    }
    bootstrap()
  }, [])

  async function login(user: string, password: string) {
    const response = await api.post('/auth/login/', { username: user, password })
    setTokens(response.data.access, response.data.refresh, user)
    setUsername(user)
  }

  function logout() {
    clearTokens()
    setUsername(null)
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated: !!accessToken, username, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth precisa ser usado dentro de um <AuthProvider>')
  return ctx
}

export function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center text-muted-foreground">
        Carregando…
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <>{children}</>
}
