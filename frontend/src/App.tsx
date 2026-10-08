import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AuthProvider, RequireAuth } from '@/lib/auth'
import { ThemeProvider } from '@/lib/theme'
import { ToastProvider } from '@/lib/toast'
import { Layout } from '@/components/Layout'
import { LoginPage } from '@/pages/LoginPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { AllOnusPage } from '@/pages/onus/AllOnusPage'
import { DuplicatedOnusPage } from '@/pages/onus/DuplicatedOnusPage'
import { OnusWithoutMacPage } from '@/pages/onus/OnusWithoutMacPage'
import { OnusWithoutClientPage } from '@/pages/onus/OnusWithoutClientPage'
import { OnusOfflinePage } from '@/pages/onus/OnusOfflinePage'
import { OnusLowSignalPage } from '@/pages/onus/OnusLowSignalPage'
import { OnusSignalWarningPage } from '@/pages/onus/OnusSignalWarningPage'
import { PortDetailPage } from '@/pages/onus/PortDetailPage'
import { MacAddressesPage } from '@/pages/onus/MacAddressesPage'
import { ClientesFibraPage } from '@/pages/ClientesFibraPage'
import { FtthBoxesPage } from '@/pages/FtthBoxesPage'
import { OltsPage } from '@/pages/OltsPage'
import { PortasPage } from '@/pages/PortasPage'
import { TemperatureAlertsPage } from '@/pages/TemperatureAlertsPage'
import { TasksPage } from '@/pages/TasksPage'
import { SchedulerPage } from '@/pages/SchedulerPage'
import { SearchPage } from '@/pages/SearchPage'

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
                  <Route path="/onus" element={<AllOnusPage />} />
                  <Route path="/onus/duplicadas" element={<DuplicatedOnusPage />} />
                  <Route path="/onus/sem-mac" element={<OnusWithoutMacPage />} />
                  <Route path="/onus/sem-cliente" element={<OnusWithoutClientPage />} />
                  <Route path="/onus/offline" element={<OnusOfflinePage />} />
                  <Route path="/onus/sinal-baixo" element={<OnusLowSignalPage />} />
                  <Route path="/onus/sinal-alerta" element={<OnusSignalWarningPage />} />
                  <Route path="/onus/porta/:slot/:port" element={<PortDetailPage />} />
                  <Route path="/mac-addresses" element={<MacAddressesPage />} />

                  {/* Clientes & Fibra */}
                  <Route path="/clientes-fibra" element={<ClientesFibraPage />} />
                  <Route path="/ftth-boxes" element={<FtthBoxesPage />} />

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
