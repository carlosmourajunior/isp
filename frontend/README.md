# Frontend (React)

SPA que substitui os templates Django do sistema ISP. Fala com o backend
só via API REST/JWT em `/api/` (ver `../API_DOCUMENTATION.md` e
`../olt/api_urls.py`). Não usa SSR nem proxy — o browser chama o backend
diretamente pela URL configurada em `VITE_API_URL`.

## Stack

- Vite + React + TypeScript
- Tailwind CSS v4 + shadcn/ui (componentes em `src/components/ui`, copiados
  pro projeto — use `npx shadcn@latest add <componente>` pra trazer mais)
- TanStack Query (data fetching/cache/polling) e TanStack Table (listagens)
- React Router
- Axios com interceptor de refresh automático de token JWT

## Rodando localmente (fora do Docker)

```bash
cp .env.example .env.local   # ajuste VITE_API_URL se o backend não estiver em localhost:8000
npm install
npm run dev                  # http://localhost:5173
```

Precisa do backend rodando (`make start` na raiz do projeto) e do
`FRONTEND_URL` no `.env` da raiz incluindo `http://localhost:5173`
(CORS).

## Rodando via Docker

```bash
make frontend-build   # a partir da raiz do projeto - builda e sobe o serviço "frontend"
```

Sobe em `http://localhost:3000`, servido por nginx a partir do build de
produção (`npm run build`). A URL da API fica embutida no build via
`VITE_API_URL` (arg do `docker-compose.yml`, lido do `.env` da raiz).

## Autenticação

Login chama `POST /api/auth/login/` (`src/lib/auth.tsx`). O access token
vive só em memória; o refresh token fica em `localStorage` para sobreviver
a um F5. Um interceptor do axios (`src/lib/api.ts`) renova o access token
automaticamente em qualquer 401.

## Estado da migração

Ver o plano de modernização do frontend para o mapeamento completo de
páginas. Hoje só o dashboard (`/`) está de fato ligado à API; o resto das
rotas em `src/App.tsx` são placeholders.
