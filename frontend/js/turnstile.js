/**
 * Cloudflare Turnstile — widget client-side.
 * - Renderiza el widget automáticamente en cualquier <div class="cf-turnstile" data-sitekey="...">
 * - Expone window.cfTurnstile.getToken(formId) para obtener el token antes de submit.
 * - Requiere el <script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
 *   en el HTML.
 */
(function () {
  const cfTurnstile = {
    SITE_KEY: window.CF_TURNSTILE_SITE_KEY || "", // ⚠️ setear en cada HTML

    // ---------- Render widgets on load ----------
    renderAll() {
      if (!this.SITE_KEY) {
        console.warn("CF_TURNSTILE_SITE_KEY no configurada — widget no se renderiza");
        return;
      }
      if (typeof window.turnstile === "undefined") {
        console.warn("Turnstile SDK no cargada todavía");
        return;
      }
      // Reemplaza data-sitekey de los divs si está vacío
      document.querySelectorAll(".cf-turnstile").forEach((el) => {
        if (!el.dataset.sitekey) el.dataset.sitekey = this.SITE_KEY;
        if (el.dataset.rendered === "true") return;
        try {
          window.turnstile.render(el, {
            sitekey: this.SITE_KEY,
            callback: (token) => {
              el.dataset.token = token;
              el.dispatchEvent(new CustomEvent("turnstile:success", { detail: { token } }));
            },
            "error-callback": () => {
              el.dataset.token = "";
              el.dispatchEvent(new CustomEvent("turnstile:error"));
            },
            "expired-callback": () => {
              el.dataset.token = "";
              console.warn("Turnstile token expirado");
            },
          });
          el.dataset.rendered = "true";
        } catch (err) {
          console.error("Error renderizando Turnstile:", err);
        }
      });
    },

    // ---------- Get token for a given form ----------
    async getToken(formEl) {
      if (!this.SITE_KEY) {
        console.warn("CF_TURNSTILE_SITE_KEY no configurada — enviando token vacío");
        return "";
      }

      // 1) Si hay widget embebido en el form, tomar su token
      const widget = formEl?.querySelector(".cf-turnstile");
      if (widget) {
        if (widget.dataset.token) return widget.dataset.token;
        // Esperar el callback
        return new Promise((resolve, reject) => {
          const timer = setTimeout(
            () => reject(new Error("Turnstile: timeout esperando token")),
            8000
          );
          widget.addEventListener(
            "turnstile:success",
            (e) => {
              clearTimeout(timer);
              resolve(e.detail.token);
            },
            { once: true }
          );
          widget.addEventListener(
            "turnstile:error",
            () => {
              clearTimeout(timer);
              reject(new Error("Turnstile: error al generar token"));
            },
            { once: true }
          );
        });
      }

      // 2) Modo "invisible" (sin widget): usar ejecución implícita
      if (typeof window.turnstile === "undefined") {
        throw new Error("Turnstile SDK no cargada");
      }
      return new Promise((resolve, reject) => {
        window.turnstile.execute(this.SITE_KEY, {
          callback: (token) => resolve(token),
          "error-callback": (err) => reject(new Error("Turnstile error: " + err)),
        });
      });
    },

    // ---------- Reset widget ----------
    reset(formEl) {
      const widget = formEl?.querySelector(".cf-turnstile");
      if (widget && widget.dataset.rendered === "true" && window.turnstile) {
        window.turnstile.reset(widget);
        widget.dataset.token = "";
      }
    },
  };

  window.cfTurnstile = cfTurnstile;

  // Auto-render cuando la SDK esté lista
  document.addEventListener("DOMContentLoaded", () => cfTurnstile.renderAll());
  // Si la SDK se carga async, también disparamos en window.load
  window.addEventListener("load", () => cfTurnstile.renderAll());
})();
