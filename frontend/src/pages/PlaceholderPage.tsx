export function PlaceholderPage({ title }: { title: string }) {
  return (
    <div>
      <h1 className="mb-2 text-xl font-semibold text-foreground">{title}</h1>
      <p className="text-sm text-muted-foreground">
        Página ainda não migrada nesta fase da modernização do frontend.
      </p>
    </div>
  )
}
