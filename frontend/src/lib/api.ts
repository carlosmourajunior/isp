import axios, { type InternalAxiosRequestConfig } from 'axios'
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from './tokenStore'

const baseURL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api'

export const api = axios.create({ baseURL })

api.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

interface RetryableConfig extends InternalAxiosRequestConfig {
  _retry?: boolean
}

let refreshPromise: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken()
  if (!refresh) return null

  try {
    // Usa axios "puro" (não a instância `api`) para não reentrar no interceptor.
    const response = await axios.post(`${baseURL}/auth/refresh/`, { refresh })
    const newAccess = response.data.access as string
    setTokens(newAccess)
    return newAccess
  } catch {
    clearTokens()
    return null
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as RetryableConfig | undefined

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true

      if (!refreshPromise) {
        refreshPromise = refreshAccessToken().finally(() => {
          refreshPromise = null
        })
      }

      const newAccess = await refreshPromise
      if (newAccess) {
        originalRequest.headers.Authorization = `Bearer ${newAccess}`
        return api(originalRequest)
      }
    }

    return Promise.reject(error)
  },
)
