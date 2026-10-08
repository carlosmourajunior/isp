interface Option {
  label: string
  value: string
}

interface SelectFilterProps {
  label: string
  value: string
  options: Option[]
  onChange: (value: string) => void
}

/** Todos os filtros usam '' como "sem filtro" (não manda o parâmetro pra API). */
export function SelectFilter({ label, value, options, onChange }: SelectFilterProps) {
  return (
    <label className="flex items-center gap-1.5 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 rounded-md border border-input bg-background px-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <option value="">Todos</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  )
}
