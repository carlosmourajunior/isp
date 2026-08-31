import { Construction } from 'lucide-react'

export function PlaceholderPage({ title }: { title: string }) {
  return (
    <div>
      <h1 className="mb-6 text-xl font-semibold text-foreground">{title}</h1>
      <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border py-20 text-center">
        <Construction className="size-8 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">
          Esta página ainda não foi migrada nesta fase da modernização do frontend.
        </p>
      </div>
    </div>
  )
}
