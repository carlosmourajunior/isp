import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AuthProvider, RequireAuth } from '@/lib/auth'
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
              <Route path="/onus" element={<PlaceholderPage title="ONUs" />} />
              <Route path="/onus/duplicadas" element={<PlaceholderPage title="ONUs Duplicadas" />} />
              <Route path="/mac-addresses" element={<PlaceholderPage title="MAC Addresses" />} />
              <Route path="/ftth-boxes" element={<PlaceholderPage title="Caixas FTTH" />} />
              <Route path="/clientes-fibra" element={<PlaceholderPage title="Clientes Fibra" />} />
              <Route path="/temperature-alerts" element={<PlaceholderPage title="Alertas de Temperatura" />} />
              <Route path="/tasks" element={<PlaceholderPage title="Tarefas" />} />
              <Route path="/scheduler" element={<PlaceholderPage title="Scheduler" />} />
            </Route>
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
