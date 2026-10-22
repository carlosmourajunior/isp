import { lazy, Suspense } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, RequireAuth } from '@/lib/auth'
import { ThemeProvider } from '@/lib/theme'
import { ToastProvider } from '@/lib/toast'
import { Layout } from '@/components/Layout'
import { LoginPage } from '@/pages/LoginPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { OnusPage } from '@/pages/onus/OnusPage'
import { SinalPage } from '@/pages/sinal/SinalPage'
import { PortDetailPage } from '@/pages/onus/PortDetailPage'
import { MacAddressesPage } from '@/pages/onus/MacAddressesPage'
import { ClientesFibraPage } from '@/pages/ClientesFibraPage'
import { OltsPage } from '@/pages/OltsPage'
import { PortasPage } from '@/pages/PortasPage'
import { TemperatureAlertsPage } from '@/pages/TemperatureAlertsPage'
import { TasksPage } from '@/pages/TasksPage'
import { SchedulerPage } from '@/pages/SchedulerPage'
import { SearchPage } from '@/pages/SearchPage'
import { VistoriasPage } from '@/pages/vistorias/VistoriasPage'
import { VistoriaPage } from '@/pages/vistorias/VistoriaPage'

// Carregada sob demanda: traz o Leaflet (mapa), que não precisa pesar nas outras telas.
const CtosPage = lazy(() => import('@/pages/ctos/CtosPage').then((m) => ({ default: m.CtosPage })))

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
})

function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <BrowserRouter>
            <AuthProvider>
              <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route
                  element={
                    <RequireAuth>
                      <Layout />
                    </RequireAuth>
                  }
                >
                  <Route path="/" element={<DashboardPage />} />

                  {/* ONUs */}
                  <Route path="/onus" element={<OnusPage />} />
                  <Route path="/sinal" element={<SinalPage />} />
                  {/* Endereços antigos (favoritos/links): viraram filtros das páginas novas. */}
                  <Route path="/onus/duplicadas" element={<Navigate to="/onus?situacao=duplicadas" replace />} />
                  <Route path="/onus/sem-mac" element={<Navigate to="/onus?situacao=sem-mac" replace />} />
                  <Route path="/onus/sem-cliente" element={<Navigate to="/onus?situacao=sem-cliente" replace />} />
                  <Route path="/onus/offline" element={<Navigate to="/onus?situacao=offline" replace />} />
                  <Route path="/onus/sinal-baixo" element={<Navigate to="/sinal?faixa=critico" replace />} />
                  <Route path="/onus/sinal-alerta" element={<Navigate to="/sinal?faixa=alerta" replace />} />
                  <Route path="/onus/porta/:slot/:port" element={<PortDetailPage />} />
                  <Route path="/mac-addresses" element={<MacAddressesPage />} />

                  {/* Clientes & Fibra */}
                  <Route path="/clientes-fibra" element={<ClientesFibraPage />} />
                  <Route path="/ftth-boxes" element={<Navigate to="/ctos" replace />} />
                  <Route
                    path="/ctos"
                    element={
                      <Suspense fallback={<div className="py-10 text-center text-muted-foreground">Carregando…</div>}>
                        <CtosPage />
                      </Suspense>
                    }
                  />
                  <Route path="/vistorias" element={<VistoriasPage />} />
                  <Route path="/vistorias/:id" element={<VistoriaPage />} />

                  {/* Rede */}
                  <Route path="/olts" element={<OltsPage />} />
                  <Route path="/portas" element={<PortasPage />} />
                  <Route path="/temperature-alerts" element={<TemperatureAlertsPage />} />

                  {/* Operação */}
                  <Route path="/tasks" element={<TasksPage />} />
                  <Route path="/scheduler" element={<SchedulerPage />} />
                  <Route path="/search" element={<SearchPage />} />
                </Route>
              </Routes>
            </AuthProvider>
          </BrowserRouter>
        </ToastProvider>
      </QueryClientProvider>
    </ThemeProvider>
  )
}

export default App
