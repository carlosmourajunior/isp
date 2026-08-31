import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AuthProvider, RequireAuth } from '@/lib/auth'
import { ThemeProvider } from '@/lib/theme'
import { Layout } from '@/components/Layout'
import { LoginPage } from '@/pages/LoginPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { PlaceholderPage } from '@/pages/PlaceholderPage'

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
                <Route path="/onus" element={<PlaceholderPage title="Todas as ONUs" />} />
                <Route path="/onus/duplicadas" element={<PlaceholderPage title="ONUs Duplicadas" />} />
                <Route path="/onus/sem-mac" element={<PlaceholderPage title="ONUs sem MAC" />} />
                <Route path="/onus/sem-cliente" element={<PlaceholderPage title="ONUs sem Cliente Fibra" />} />
                <Route path="/onus/offline" element={<PlaceholderPage title="ONUs com Oper. State Down" />} />
                <Route path="/onus/porta/:slot/:port" element={<PlaceholderPage title="Detalhes da Porta" />} />
                <Route path="/mac-addresses" element={<PlaceholderPage title="MAC Addresses" />} />

                {/* Clientes & Fibra */}
                <Route path="/clientes-fibra" element={<PlaceholderPage title="Clientes Fibra" />} />
                <Route path="/ftth-boxes" element={<PlaceholderPage title="Caixas FTTH" />} />

                {/* Rede */}
                <Route path="/portas" element={<PlaceholderPage title="Ocupação de Portas" />} />
                <Route path="/temperature-alerts" element={<PlaceholderPage title="Alertas de Temperatura" />} />

                {/* Operação */}
                <Route path="/tasks" element={<PlaceholderPage title="Tarefas" />} />
                <Route path="/scheduler" element={<PlaceholderPage title="Scheduler" />} />
                <Route path="/search" element={<PlaceholderPage title="Busca" />} />
              </Route>
            </Routes>
          </AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  )
}

export default App
