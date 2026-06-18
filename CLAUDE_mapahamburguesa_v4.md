# CLAUDE.md — MapaHamburguesa v4

Documento de especificaciones completo para el desarrollo de MapaHamburguesa, una app web colaborativa y georreferenciada para mapear hamburgueserías en la Provincia de Buenos Aires. Esta versión utiliza Supabase como BaaS y DO Spaces para frontend y almacenamiento.

---

## 1. Visión general del proyecto

**Nombre:** MapaHamburguesa  
**Stack:**
- **Frontend:** HTML + JS vanilla + Leaflet.js, hosteado en DigitalOcean Spaces (CDN).
- **Backend:** FastAPI (Python) en DigitalOcean Droplet.
- **Base de datos / Auth / Storage:** Supabase (PostgreSQL + Auth + Storage).
- **LLM onboarding:** Gemini via Google AI Studio.
- **Email:** Resend (API HTTP).
- **Seguridad:** Cloudflare (proxy + Turnstile).

**Auth:** Google OAuth 2.0 gestionado por Supabase Auth.  
**Deploy:** DO Spaces (frontend) + DO Droplet (FastAPI) + Supabase cloud.  
**MVP:** Adrogué → V2: toda la Provincia de Buenos Aires.

### Recursos cloud y su rol académico

| Servicio | Tipo | Rol |
|---|---|---|
| Supabase | BaaS / DBaaS | DB + Auth + Storage |
| DigitalOcean Droplet | IaaS | FastAPI |
| DigitalOcean Spaces | PaaS / CDN | Frontend estático + fotos |
| Gemini (Google AI Studio) | SaaS / LLM | Asistente de onboarding |
| Resend | SaaS | Mailing transaccional |
| Cloudflare | SaaS | Proxy + protección anti-bots |

---

## 2. Estructura de carpetas

```
mapahamburguesa/
├── backend/
│   ├── main.py                    # Entry point FastAPI
│   ├── config.py                  # Variables de entorno (.env)
│   ├── database.py                # Cliente Supabase (supabase-py)
│   ├── routers/
│   │   ├── auth.py                # Google OAuth endpoints (via Supabase Auth)
│   │   ├── places.py              # CRUD locales
│   │   ├── reviews.py             # CRUD reviews
│   │   ├── photos.py              # Upload fotos a Supabase Storage
│   │   ├── suggestions.py         # Sugerencias de edición
│   │   └── admin.py               # Panel de moderación
│   ├── services/
│   │   ├── supabase_service.py    # Wrapper del cliente supabase-py
│   │   ├── storage_service.py     # Upload/delete fotos en Supabase Storage
│   │   ├── email_service.py       # Notificaciones vía Resend
│   │   └── gemini_service.py      # Asistente de onboarding
│   ├── dependencies.py            # get_current_user, get_admin_user
│   └── requirements.txt
│
├── frontend/
│   ├── index.html                 # Mapa principal
│   ├── admin.html                 # Panel de moderación
│   ├── css/
│   │   ├── main.css
│   │   ├── sidebar.css
│   │   └── admin.css
│   ├── js/
│   │   ├── supabaseClient.js      # init: supabase.createClient(URL, ANON_KEY)
│   │   ├── auth.js                # login/logout con Google
│   │   ├── api.js                 # wrappers: fetchPlaces, createPlace, approvePlace…
│   │   ├── map.js                 # Leaflet, markers, clustering, heatmap
│   │   ├── sidebar.js             # Panel lateral de detalle
│   │   ├── filters.js             # Filtros del mapa
│   │   ├── forms.js               # Formularios: agregar local, review, sugerencia
│   │   ├── admin.js               # Lógica admin.html
│   │   └── imageResize.js         # Comprime imágenes a 1200px en el cliente
│   └── assets/
│       ├── icons/                 # Markers SVG custom
│       └── img/
│
├── supabase/
│   ├── migrations/
│   │   ├── 0001_extensions.sql
│   │   ├── 0002_profiles.sql
│   │   ├── 0003_burger_places.sql
│   │   ├── 0004_reviews.sql
│   │   ├── 0005_photos.sql
│   │   ├── 0006_edit_suggestions.sql
│   │   ├── 0007_triggers.sql
│   │   └── 0008_rls_policies.sql
│   └── seed/
│       └── adrogue.sql            # Carga inicial de locales mockeados de Adrogué
│
├── .env.example
├── docker-compose.yml             # Desarrollo local
├── README.md
└── CLAUDE.md                      # Este archivo
```

---

## 3. Base de datos — Esquema PostgreSQL (Supabase)

### Extensiones requeridas
```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS cube;
CREATE EXTENSION IF NOT EXISTS earthdistance;
```

### Tabla `profiles`
Ligada 1:1 a `auth.users` de Supabase.
```sql
CREATE TABLE public.profiles (
    id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    name        VARCHAR(255) NOT NULL,
    avatar_url  TEXT,
    role        VARCHAR(20) NOT NULL DEFAULT 'user',  -- 'user' | 'moderator' | 'admin'
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Tabla `burger_places`
```sql
CREATE TABLE public.burger_places (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    address         TEXT NOT NULL,
    city            VARCHAR(100) NOT NULL,
    partido         VARCHAR(100) NOT NULL,
    lat             DECIMAL(10, 8) NOT NULL,
    lng             DECIMAL(11, 8) NOT NULL,
    phone           VARCHAR(50),
    website         TEXT,
    instagram       VARCHAR(100),
    facebook        VARCHAR(100),
    price_range     VARCHAR(10),        -- 'cheap' | 'mid' | 'expensive'
    place_type      VARCHAR(30),        -- 'fast_food' | 'gourmet' | 'dark_kitchen' | 'food_truck' | 'other'
    has_delivery    BOOLEAN DEFAULT FALSE,
    payment_methods TEXT[],             -- ['efectivo', 'debito', 'credito', 'mp', 'uala']
    schedule        JSONB,              -- {"lun": "12:00-23:00", ...}
    menu_highlights TEXT,
    status          VARCHAR(20) DEFAULT 'pending',  -- 'pending' | 'approved' | 'rejected'
    avg_rating      DECIMAL(3, 2) DEFAULT 0,
    review_count    INTEGER DEFAULT 0,
    added_by        UUID REFERENCES public.profiles(id),
    approved_by     UUID REFERENCES public.profiles(id),
    approved_at     TIMESTAMP WITH TIME ZONE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_places_location ON burger_places USING GIST (ll_to_earth(lat, lng));
CREATE INDEX idx_places_status   ON burger_places(status);
CREATE INDEX idx_places_partido  ON burger_places(partido);
```

### Tabla `reviews`
```sql
CREATE TABLE public.reviews (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    place_id    UUID NOT NULL REFERENCES public.burger_places(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES public.profiles(id),
    rating      SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment     TEXT,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (place_id, user_id)
);
```

### Tabla `photos`
```sql
CREATE TABLE public.photos (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    place_id    UUID NOT NULL REFERENCES public.burger_places(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES public.profiles(id),
    url         TEXT NOT NULL,          -- URL pública en Supabase Storage
    is_cover    BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Tabla `edit_suggestions`
```sql
CREATE TABLE public.edit_suggestions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    place_id        UUID NOT NULL REFERENCES public.burger_places(id) ON DELETE CASCADE,
    suggested_by    UUID NOT NULL REFERENCES public.profiles(id),
    field_name      VARCHAR(100) NOT NULL,
    old_value       TEXT,
    new_value       TEXT NOT NULL,
    status          VARCHAR(20) DEFAULT 'pending',  -- 'pending' | 'approved' | 'rejected'
    reviewed_by     UUID REFERENCES public.profiles(id),
    reviewed_at     TIMESTAMP WITH TIME ZONE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Trigger: recalcular `avg_rating`
```sql
CREATE OR REPLACE FUNCTION recalculate_place_rating()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    UPDATE public.burger_places
    SET avg_rating   = (SELECT COALESCE(AVG(rating), 0) FROM public.reviews WHERE place_id = COALESCE(NEW.place_id, OLD.place_id)),
        review_count = (SELECT COUNT(*)                  FROM public.reviews WHERE place_id = COALESCE(NEW.place_id, OLD.place_id)),
        updated_at   = NOW()
    WHERE id = COALESCE(NEW.place_id, OLD.place_id);
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_recalculate_rating
AFTER INSERT OR UPDATE OR DELETE ON public.reviews
FOR EACH ROW EXECUTE FUNCTION recalculate_place_rating();
```

---

## 4. Endpoints de la API (FastAPI)

### Autenticación — `/auth`
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/auth/google` | Inicia flujo OAuth via Supabase Auth |
| GET | `/auth/callback` | Callback de Supabase, devuelve JWT |
| GET | `/auth/me` | Datos del usuario autenticado |
| POST | `/auth/logout` | Invalida la sesión |

### Locales — `/places`
| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/places` | Pública | Lista locales aprobados (con filtros) |
| GET | `/places/{id}` | Pública | Detalle de un local |
| POST | `/places` | Usuario | Crear local (`status=pending`) |
| PUT | `/places/{id}` | Admin | Editar local directamente |
| DELETE | `/places/{id}` | Admin | Eliminar local |
| GET | `/places/pending` | Admin | Locales pendientes |
| PATCH | `/places/{id}/approve` | Admin | Aprobar local |
| PATCH | `/places/{id}/reject` | Admin | Rechazar local |

**Query params de `/places`:**
- `partido`, `ciudad`, `tipo`, `precio`, `delivery`, `abierto_ahora`, `metodo_pago`
- `lat`, `lng`, `radio_km` — búsqueda por proximidad
- `limit`, `offset` — paginación

### Reviews — `/places/{id}/reviews`
| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/places/{id}/reviews` | Pública | Lista reviews |
| POST | `/places/{id}/reviews` | Usuario | Crear review (1 por usuario/local) |
| PUT | `/places/{id}/reviews/{review_id}` | Usuario propio | Editar propia review |
| DELETE | `/places/{id}/reviews/{review_id}` | Usuario / Admin | Borrar review |

### Fotos — `/places/{id}/photos`
| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/places/{id}/photos` | Pública | Lista fotos |
| POST | `/places/{id}/photos` | Usuario | Subir foto (multipart/form-data) |
| DELETE | `/places/{id}/photos/{photo_id}` | Usuario propio / Admin | Borrar foto |
| PATCH | `/places/{id}/photos/{photo_id}/cover` | Admin | Marcar como portada |

### Sugerencias — `/places/{id}/suggestions`
| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| POST | `/places/{id}/suggestions` | Usuario | Crear sugerencia |
| GET | `/suggestions/pending` | Admin | Lista sugerencias pendientes |
| PATCH | `/suggestions/{id}/approve` | Admin | Aprobar sugerencia |
| PATCH | `/suggestions/{id}/reject` | Admin | Rechazar sugerencia |

### Asistente IA — `/assistant`
| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| POST | `/assistant/suggest` | Pública | Recibe preferencias, devuelve sugerencias de locales via Gemini |

---

## 5. Variables de entorno (`.env`)

```env
# Supabase
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=       # Solo en backend, NUNCA en frontend

# Google OAuth (configurado en Supabase Auth)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# JWT
SECRET_KEY=
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# DigitalOcean Spaces (fotos y frontend)
DO_SPACES_KEY=
DO_SPACES_SECRET=
DO_SPACES_REGION=nyc3
DO_SPACES_BUCKET=mapahamburguesa
DO_SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com

# Resend (emails)
RESEND_API_KEY=

# Gemini
GEMINI_API_KEY=

# App
ENVIRONMENT=development
FRONTEND_URL=http://localhost:5500
CORS_ORIGINS=["http://localhost:5500","https://tudominio.com"]
```

---

## 6. Flujos principales

### Flujo: Agregar un local
1. Usuario logueado completa el formulario en el frontend.
2. `POST /places` → local se guarda con `status = 'pending'`.
3. El admin ve el local en `/places/pending`.
4. Admin aprueba → `status = 'approved'` + email de notificación vía Resend.
5. El local aparece en el mapa.

### Flujo: Onboarding IA
1. Usuario nuevo describe sus preferencias al asistente.
2. `POST /assistant/suggest` → FastAPI filtra locales de Supabase según preferencias.
3. Gemini recibe los resultados y redacta una respuesta conversacional.
4. Frontend muestra la sugerencia al usuario.

### Flujo: Sugerir edición
1. Usuario logueado clickea "Sugerir edición" en el panel lateral.
2. `POST /places/{id}/suggestions` → queda en `pending`.
3. Admin aprueba → se actualiza el campo en `burger_places`.

---

## 7. Reglas de negocio

- Un usuario solo puede dejar **una review por local**. Constraint `UNIQUE (place_id, user_id)`.
- `avg_rating` se recalcula con trigger PostgreSQL en INSERT / UPDATE / DELETE sobre `reviews`.
- Locales con `status = 'pending'` o `'rejected'` no aparecen en `/places` público.
- Solo `role = 'admin'` o `'moderator'` accede a endpoints de moderación.
- `schedule` es JSONB con claves `lun`, `mar`, `mie`, `jue`, `vie`, `sab`, `dom`.
- Fotos se suben a **Supabase Storage** (bucket `place-photos`). Máximo **10 fotos por local**.
- Imágenes se redimensionan a máximo 1200px de ancho **en el cliente** antes de subir.

---

## 8. Frontend — Comportamiento clave

### Mapa (`map.js`)
- Tiles: **OpenStreetMap** (gratuito, sin API key).
- Plugin **Leaflet.markercluster** para agrupar markers con zoom.
- Plugin **Leaflet.heat** para heatmap de densidad.
- Al hacer click en un marker → abre el **panel lateral**.
- Markers con color/ícono distinto según `place_type`.

### Panel lateral (`sidebar.js`)
- Nombre, dirección, partido, rating con estrellas, reviews count.
- Tipo + precio + horarios (resalta si está abierto ahora).
- Teléfono/WhatsApp (link directo), redes sociales, métodos de pago.
- Galería de fotos (carrusel).
- Lista de reviews.
- Botones "Dejar review", "Sugerir edición", "Agregar foto" (solo usuarios logueados).
- Se cierra al hacer click fuera o presionar Escape.

### Filtros (`filters.js`)
- Dropdown partido/ciudad, tipo de local, precio.
- Toggle delivery, toggle abierto ahora.
- Checkbox métodos de pago.
- Botón "Limpiar filtros".

---

## 9. Fases de desarrollo

### Fase 1 — Infraestructura base
- [ ] Crear proyecto Supabase, copiar credenciales
- [ ] Habilitar Google provider en Supabase Auth
- [ ] Escribir migraciones SQL (tablas + triggers + RLS)
- [ ] `supabase db push` y verificar en Studio
- [ ] Crear bucket `place-photos` en Storage
- [ ] Configurar DO Droplet (Ubuntu + Nginx + Gunicorn)
- [ ] Configurar DO Spaces + CDN para el frontend

### Fase 2 — Backend FastAPI
- [ ] Estructura de carpetas y config.py
- [ ] Conexión a Supabase via `supabase-py`
- [ ] Endpoints de `/places` con filtros
- [ ] Auth vía Supabase + JWT
- [ ] Endpoints de reviews, fotos, sugerencias
- [ ] Endpoints de admin (approve/reject)
- [ ] Integración Resend para emails
- [ ] Deploy en Droplet con Nginx + SSL (Certbot)

### Fase 3 — Frontend mapa
- [ ] HTML base + Leaflet con tiles OSM
- [ ] `supabaseClient.js` con ANON_KEY
- [ ] Fetch de locales y renderizado de markers
- [ ] Clustering + Heatmap
- [ ] Panel lateral completo
- [ ] Filtros
- [ ] Login con Google
- [ ] Formularios: agregar local, review, sugerencia, foto
- [ ] Panel admin (`admin.html`)
- [ ] Deploy a DO Spaces

### Fase 4 — Asistente IA (Gemini)
- [ ] `gemini_service.py` en FastAPI
- [ ] Endpoint `POST /assistant/suggest`
- [ ] Integración en frontend (modal de onboarding)

### Fase 5 — Polish y datos reales
- [ ] Script de seed con datos mockeados de Adrogué (mínimo 10 locales)
- [ ] Pruebas de carga
- [ ] Configurar Cloudflare (DNS + Turnstile en endpoints sensibles)

---

## 10. Dependencias Python

### Backend (`backend/requirements.txt`)
```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
supabase>=2.4.0
pydantic[email]>=2.7.0
pydantic-settings>=2.2.0
python-jose[cryptography]>=3.3.0
httpx>=0.27.0
python-multipart>=0.0.9
Pillow>=10.3.0
google-generativeai>=0.5.0
resend>=0.8.0
```

---

## 11. Notas para Claude Code

- Usar **async/await** en todos los endpoints FastAPI.
- Los UUIDs se generan en la DB con `gen_random_uuid()`, no en Python.
- `schedule` es JSONB; manejarlo como `dict` en Python.
- Para el filtro `abierto_ahora`, convertir la hora actual a UTC-3 (Argentina) antes de comparar.
- Las fotos se redimensionan a máximo 1200px de ancho **en el cliente** (`imageResize.js`) antes de subir a Supabase Storage.
- El panel lateral del frontend se cierra al hacer click fuera o presionar Escape.
- Para desarrollo local de Supabase: `supabase start` levanta todo en Docker.
- El trigger `recalculate_place_rating` debe ejecutarse también en `DELETE` — no olvidar el `AFTER DELETE`.
- Cloudflare Turnstile protege los endpoints de creación de locales y reviews. Verificar el token en FastAPI antes de procesar.
- Para el seed de datos mockeados: mínimo 10 locales en Adrogué con reviews distribuidas en los últimos 14 días.
