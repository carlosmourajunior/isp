import { useState, type ReactNode } from 'react'
import { Button, type ButtonProps } from '@/components/ui/button'

interface ConfirmDialogProps {
  open: boolean
  title: string
  description?: ReactNode
  confirmLabel?: string
  cancelLabel?: string
  confirmVariant?: ButtonProps['variant']
  isLoading?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = 'Confirmar',
  cancelLabel = 'Cancelar',
  confirmVariant = 'default',
  isLoading = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-black/50" onClick={onCancel} />
      <div className="relative w-full max-w-sm rounded-xl border border-border bg-card p-5 shadow-lg">
        <h2 className="text-base font-semibold text-foreground">{title}</h2>
        {description && <div className="mt-1.5 text-sm text-muted-foreground">{description}</div>}
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="outline" size="sm" onClick={onCancel} disabled={isLoading}>
            {cancelLabel}
          </Button>
          <Button variant={confirmVariant} size="sm" onClick={onConfirm} disabled={isLoading}>
            {isLoading ? 'Aguarde…' : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  )
}

/** Hook simples para controlar um ConfirmDialog de ação única (ex: deletar 1 item por vez). */
export function useConfirmDialog<T>() {
  const [target, setTarget] = useState<T | null>(null)
  return {
    target,
    isOpen: target !== null,
    open: (value: T) => setTarget(value),
    close: () => setTarget(null),
  }
}
