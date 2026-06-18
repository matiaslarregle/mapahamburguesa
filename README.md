# MapaHamburguesa

App web colaborativa para mapear hamburgueserías en la Provincia de Buenos Aires.

## Stack

- Frontend: HTML/JS vanilla + Leaflet
- Backend: FastAPI + Supabase
- Auth: Google OAuth con Supabase Auth
- IA: Gemini
- Email: Resend

## Estructura

```text
mapahamburguesa/
├── backend/       # FastAPI
├── frontend/      # HTML/JS estático
├── supabase/      # Migraciones + seed
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Setup Local En VS Code

### 1. Backend

Desde la raíz del proyecto:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy backend\.env.example backend\.env
```

Completá `backend\.env` con tus credenciales reales de Supabase. Después levantá la API:

```bash
uvicorn backend.main:app --reload
```

Docs locales: http://localhost:8000/docs

### 2. Frontend

En otra terminal:

```bash
cd frontend
python -m http.server 5500
```

Abrí http://localhost:5500

Antes de usar login/datos reales, reemplazá `SUPABASE_URL` y `SUPABASE_ANON_KEY` en `frontend/js/supabaseClient.js`.

Para activar Cloudflare Turnstile en el frontend, completá `window.CF_TURNSTILE_SITE_KEY` en `frontend/index.html` con la site key real. En desarrollo podés dejarla vacía si `TURNSTILE_FAIL_OPEN=true` en `backend/.env`.

### 3. Supabase

1. Crear proyecto en https://supabase.com
2. Habilitar Google provider en Authentication > Providers
3. Aplicar migraciones desde `supabase/migrations`
4. Cargar `supabase/seed/adrogue.sql` si querés datos iniciales

## Docker

```bash
docker compose up --build
```

La API queda en http://localhost:8000

## Notas

- El backend se corre como paquete Python: `backend.main:app`.
- El frontend debe servirse desde la carpeta `frontend`, donde están `index.html`, `admin.html`, `css/` y `js/`.
- No subas `backend/.env`; está ignorado por Git.
- En producción, configurá `TURNSTILE_FAIL_OPEN=false` y agregá los origins reales a `CORS_ORIGINS`.
