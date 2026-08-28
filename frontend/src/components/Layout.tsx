import { NavLink, Outlet } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { useAuth } from '@/lib/auth'
import { Button } from '@/components/ui/button'

const navItems = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/onus', label: 'ONUs' },
  { to: '/onus/duplicadas', label: 'Duplicadas' },
  { to: '/mac-addresses', label: 'MAC Addresses' },
  { to: '/ftth-boxes', label: 'Caixas FTTH' },
  { to: '/clientes-fibra', label: 'Clientes Fibra' },
  { to: '/temperature-alerts', label: 'Temperatura' },
  { to: '/tasks', label: 'Tarefas' },
  { to: '/scheduler', label: 'Scheduler' },
]

export function Layout() {
  const { username, logout } = useAuth()

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3">
          <span className="font-semibold text-foreground">ISP · Gestão de Rede</span>
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground">{username}</span>
            <Button variant="outline" size="sm" onClick={logout}>
              Sair
            </Button>
          </div>
        </div>
        <nav className="mx-auto flex max-w-7xl gap-1 overflow-x-auto px-4 pb-2">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  'shrink-0 rounded-md px-3 py-1.5 text-sm transition-colors',
                  isActive
                    ? 'bg-secondary text-secondary-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
