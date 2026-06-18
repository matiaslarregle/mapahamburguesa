# 🤖 Cloudflare Turnstile — Configuración detallada

## ¿Qué es?

Es el reemplazo de Google reCAPTCHA de Cloudflare. Es **gratis, sin tracking**
y mucho menos invasivo. Ofrece:

- Widget visible (managed) → muestra un checkbox "I'm not a robot"
- Widget invisible → ejecuta análisis en segundo plano
- Modo "managed" decide automáticamente qué mostrar según el riesgo

## Obtener claves

1. https://dash.cloudflare.com → **Security → Turnstile**
2. **Add widget**:
   - Widget name: `Mapahamburguesa Web`
   - Hostname: `mapahamburguesa.com` (principal)
   - Click + **Add hostname**: `localhost` (para dev)
3. Widget mode: **Managed** (default)
4. Submit
5. En la lista, expandir el widget → ver:
   - **Site Key** (público, va en el frontend)
   - **Secret Key** (privado, va en el backend)

## Modos de widget

| Modo | Cuándo se muestra | Uso |
|---|---|---|
| **Managed** | CF decide según riesgo | Default, recomendado |
| **Non-Interactive** | Siempre visible pero sin interacción del user | Formularios críticos |
| **Invisible** | Solo spinner | UX limpia, sin branding |

## Tipos de error que detecta

- Bots automatizados
- Scripts con headless browsers
- Patrones de requests abusivos
- IPs en listas negras

## ¿Qué pasa si está mal configurado?

- Site key incorrecta → widget no renderiza, frontend tira error
- Secret key incorrecta → backend rechaza todos los tokens (fail-closed)
- Hostname no autorizado → tokens se rechazan

## Límites

- 1 millón de verificaciones gratis por mes
- Después: $1 / 1000 verificaciones (muy barato)

## Testing local

```js
// En DevTools console
await window.cfTurnstile.getToken(document.getElementById("form-add-place"));
// Devuelve un string largo tipo "0.AB.CD..." si está OK
