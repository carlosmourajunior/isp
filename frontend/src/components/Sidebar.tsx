import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Router,
  Copy,
  WifiOff,
  UserX,
  ScanLine,
  Users,
  Boxes,
  Network,
  Thermometer,
  ListChecks,
  Clock,
  Search,
  X,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface NavItem {
  to: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  end?: boolean
}

interface NavGroup {
  label: string
  items: NavItem[]
}

const navGroups: NavGroup[] = [
  {
    label: 'Visão Geral',
    items: [{ to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true }],
  },
  {
    label: 'ONUs',
    items: [
      { to: '/onus', label: 'Todas as ONUs', icon: Router },
      { to: '/onus/duplicadas', label: 'Duplicadas', icon: Copy },
      { to: '/onus/sem-mac', label: 'Sem MAC', icon: ScanLine },
      { to: '/onus/sem-cliente', label: 'Sem Cliente Fibra', icon: UserX },
      { to: '/onus/offline', label: 'Oper. State Down', icon: WifiOff },
      { to: '/mac-addresses', label: 'MAC Addresses', icon: ScanLine },
    ],
  },
  {
    label: 'Clientes & Fibra',
    items: [
      { to: '/clientes-fibra', label: 'Clientes Fibra', icon: Users },
      { to: '/ftth-boxes', label: 'Caixas FTTH', icon: Boxes },
    ],
  },
  {
    label: 'Rede',
    items: [
      { to: '/portas', label: 'Ocupação de Portas', icon: Network },
      { to: '/temperature-alerts', label: 'Alertas de Temperatura', icon: Thermometer },
    ],
  },
  {
    label: 'Operação',
    items: [
      { to: '/tasks', label: 'Tarefas', icon: ListChecks },
      { to: '/scheduler', label: 'Scheduler', icon: Clock },
      { to: '/search', label: 'Busca', icon: Search },
    ],
  },
]

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="flex flex-1 flex-col gap-5 overflow-y-auto px-3 py-4">
      {navGroups.map((group) => (
        <div key={group.label}>
          <p className="mb-1.5 px-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground/70">
            {group.label}
          </p>
          <div className="flex flex-col gap-0.5">
            {group.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                onClick={onNavigate}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-2.5 rounded-md border-l-2 px-2.5 py-1.5 text-sm transition-colors',
                    isActive
                      ? 'border-primary bg-primary/10 font-medium text-primary'
                      : 'border-transparent text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                  )
                }
              >
                <item.icon className="size-4 shrink-0" />
                <span className="truncate">{item.label}</span>
              </NavLink>
            ))}
          </div>
        </div>
      ))}
    </nav>
  )
}

function Brand() {
  return (
    <div className="flex h-14 items-center gap-2 border-b border-border px-4">
      <div className="flex size-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
        <Network className="size-4" />
      </div>
      <span className="font-semibold text-foreground">ISP · Rede</span>
    </div>
  )
}

export function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-60 flex-col border-r border-border bg-card md:flex">
      <Brand />
      <NavLinks />
    </aside>
  )
}

export function MobileSidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 md:hidden">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <aside className="absolute inset-y-0 left-0 flex w-64 flex-col border-r border-border bg-card">
        <div className="flex h-14 items-center justify-between border-b border-border px-4">
          <div className="flex items-center gap-2">
            <div className="flex size-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <Network className="size-4" />
            </div>
            <span className="font-semibold text-foreground">ISP · Rede</span>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            aria-label="Fechar menu"
          >
            <X className="size-5" />
          </button>
        </div>
        <NavLinks onNavigate={onClose} />
      </aside>
    </div>
  )
}
