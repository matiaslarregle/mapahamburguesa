# ☁️ Configuración de Cloudflare

## 1) Crear cuenta + dominio

1. Ir a https://dash.cloudflare.com/sign-up
2. Agregar el dominio `mapahamburguesa.com` (o el que uses)
3. Cloudflare escanea los DNS existentes
4. Cambiar los nameservers en tu registrador (GoDaddy, Namecheap, etc.)
   a los que Cloudflare te da

## 2) Configurar DNS

En **DNS → Records**, agregar:

| Tipo | Nombre | Destino | Proxy |
|---|---|---|---|
| CNAME | api | `mapahamburguesa-api.onrender.com` (o IP del Droplet) | ✅ Proxied |
| CNAME | www | `mapahamburguesa.b-cdn.net` (Spaces CDN) | ✅ Proxied |
| CNAME | @ | `mapahamburguesa.b-cdn.net` | ✅ Proxied |

> Las requests llegan a Cloudflare, que las reenvía a tu origin
> (DO Spaces o DO Droplet). Tu origin nunca queda expuesto.

## 3) SSL/TLS

1. **SSL/TLS → Overview** → modo "Full (Strict)"
2. **Edge Certificates → Always Use HTTPS** → ON
3. (Droplet) generar cert con `certbot` y subir el origin cert a Cloudflare:
   **SSL/TLS → Origin Server → Create Certificate**

## 4) Turnstile

1. **Security → Turnstile** → Add widget
2. Nombre: `mapahamburguesa-web`
3. Hostname: `mapahamburguesa.com` (y `localhost` para dev)
4. Widget mode: **Managed** (recomendado) o **Invisible**
5. Crear → copiar **Site Key** y **Secret Key**
6. Pegar en `.env` del backend y en `index.html` del frontend

## 5) WAF / Rate limiting (opcional pero recomendado)

### Rate limiting rules

- **Security → WAF → Rate limit rules → Create rule**
- Nombre: `Protección API`
- If: `(http.request.uri.path eq "/places/") and (http.request.method eq "POST")`
  - OR `(http.request.uri.path eq "/places/*/reviews") and (http.request.method eq "POST")`
  - OR `(http.request.uri.path eq "/places/*/photos") and (http.request.method eq "POST")`
- Then: Block for 600s si requests > 5 / 60s por IP

### WAF Custom Rules (anti-bot)

- **Security → WAF → Custom rules**
- Regla 1: bloquear países que no te importan (opcional)
- Regla 2: bot score < 30 → challenge
- Regla 3: ASN conocido de scrapers → block

## 6) Caching (frontend)

- **Caching → Configuration → Caching level**: Standard
- **Speed → Optimization → Auto Minify**: HTML, CSS, JS ✅
- **Speed → Optimization → Brotli**: ON

## 7) Page Rules (opcional)

- `api.mapahamburguesa.com/*` → Cache level: Bypass
- `mapahamburguesa.com/assets/*` → Cache level: Cache Everything, Edge TTL: 1 month

## 8) Access (opcional, para el panel admin)

- **Access → Applications → Add**
- Nombre: `MapaHamburguesa Admin`
- Domain: `mapahamburguesa.com/admin*`
- Policy: Allow solo tu email (o lista de admins)
- Esto pone un login de Cloudflare ANTES de tu app — protección extra

## 9) Logs

- **Analytics → Traffic** → ver requests, bandwidth, threats
- **Security → Events** → ver challenges, blocks, etc.

## 10) Modo desarrollo (localhost)

Para que Turnstile funcione en `http://localhost:5500`:

1. **Turnstile → widget → Hostnames** → agregar `localhost`
2. NO es necesario agregar DNS para localhost
3. Asegurate que `TURNSTILE_FAIL_OPEN=true` en `.env` para tests sin secret
