import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'
import { CheckCircle2, XCircle, X } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Toast {
  id: number
  title: string
  description?: string
  variant: 'success' | 'error'
}

interface ToastContextValue {
  success: (title: string, description?: string) => void
  error: (title: string, description?: string) => void
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined)
let nextId = 1

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((t) => t.id !== id))
  }, [])

  const push = useCallback(
    (variant: Toast['variant'], title: string, description?: string) => {
      const id = nextId++
      setToasts((current) => [...current, { id, title, description, variant }])
      setTimeout(() => dismiss(id), 5000)
    },
    [dismiss],
  )

  const value: ToastContextValue = {
    success: (title, description) => push('success', title, description),
    error: (title, description) => push('error', title, description),
  }

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-[100] flex w-full max-w-sm flex-col gap-2">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={cn(
              'pointer-events-auto flex items-start gap-2.5 rounded-lg border border-border bg-card p-3.5 text-sm shadow-lg',
            )}
          >
            {toast.variant === 'success' ? (
              <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-500" />
            ) : (
              <XCircle className="mt-0.5 size-4 shrink-0 text-destructive" />
            )}
            <div className="flex-1">
              <p className="font-medium text-foreground">{toast.title}</p>
              {toast.description && <p className="text-muted-foreground">{toast.description}</p>}
            </div>
            <button
              onClick={() => dismiss(toast.id)}
              className="text-muted-foreground hover:text-foreground"
              aria-label="Fechar"
            >
              <X className="size-3.5" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast precisa ser usado dentro de um <ToastProvider>')
  return ctx
}
