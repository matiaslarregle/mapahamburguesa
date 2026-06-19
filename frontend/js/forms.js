/**
 * Formularios: handlers de submit para los modales.
 * Maneja Turnstile de forma unificada.
 * Expone: window.formsApp
 */
(function () {
  const formsApp = {
    // ============================================================
    // INIT
    // ============================================================
    init() {
      // Botón "Agregar local" en el header
      document
        .getElementById("btn-add-place")
        ?.addEventListener("click", () => this.openPlaceModal());

      // Cerrar modal con data-close-modal
      document.querySelectorAll("[data-close-modal]").forEach((btn) => {
        btn.addEventListener("click", () => this.hideModal(btn.dataset.closeModal));
      });

      // Cerrar modal clickeando el backdrop
      document.querySelectorAll(".modal").forEach((modal) => {
        modal.addEventListener("click", (e) => {
          if (e.target === modal) this.hideModal(modal.id);
        });
      });

      // Submits
      document.getElementById("form-add-place")?.addEventListener("submit", (e) =>
        this.handleAddPlace(e)
      );
      document.getElementById("form-review")?.addEventListener("submit", (e) =>
        this.handleReview(e)
      );
      document.getElementById("form-suggestion")?.addEventListener("submit", (e) =>
        this.handleSuggestion(e)
      );

      // Rating stars
      this.initRatingStars();

      // Asistente IA (no usa Turnstile, es público)
      document
        .getElementById("btn-open-assistant")
        ?.addEventListener("click", () => this.showModal("modal-assistant"));
      document
        .getElementById("form-assistant")
        ?.addEventListener("submit", (e) => this.handleAssistant(e));
    },

    // ============================================================
    // HELPER UNIFICADO: TURNSTILE + SUBMIT
    // ============================================================
    /**
     * Flujo común para los 4 handlers con Turnstile:
     * 1. Lee datos del form (JSON o FormData)
     * 2. Obtiene token de Turnstile
     * 3. Inyecta token en payload o FormData
     * 4. Llama a la función `submit(payload, token)` que devuelve una Promise
     * 5. Resetea el widget Turnstile
     * 6. Cierra el modal y muestra toast
     */
    async submitWithTurnstile({
      event,
      useFormData = false,
      submit, // (payloadOrFormData, token) => Promise
      successMessage,
      onSuccess,
    }) {
      event.preventDefault();
      const formEl = event.target;
      const closeModalId = formEl.closest(".modal")?.id;

      try {
        // 1) Token de Turnstile
        const token = await this.getTurnstileToken(formEl);

        // 2) Datos del form
        let payload;
        if (useFormData) {
          payload = new FormData(formEl);
          payload.append("cf_turnstile_token", token);
        } else {
          payload = this.getFormData(formEl);
          payload.cf_turnstile_token = token;
        }

        // 3) Ejecutar submit del caller
        await submit(payload, token);

        // 4) Éxito → resetear form, Turnstile y cerrar modal
        formEl.reset();
        if (window.cfTurnstile) window.cfTurnstile.reset(formEl);
        if (closeModalId) this.hideModal(closeModalId);

        if (successMessage) window.toast(successMessage, "success");
        if (onSuccess) await onSuccess();
      } catch (err) {
        // 5) Error: no cerramos modal, reseteamos Turnstile para reintento
        if (window.cfTurnstile) window.cfTurnstile.reset(formEl);
        window.toast("Error: " + err.message, "error");
      }
    },

    /**
     * Obtiene el token de Turnstile desde el form.
     * Si no hay widget embebido, intenta el método "invisible".
     */
    async getTurnstileToken(formEl) {
      if (!window.cfTurnstile) {
        throw new Error("Turnstile no inicializado");
      }
      return await window.cfTurnstile.getToken(formEl);
    },

    // ============================================================
    // MODAL: AGREGAR LOCAL
    // ============================================================
    openPlaceModal() {
      window.auth.getCurrentUser().then((u) => {
        if (!u) {
          window.toast("Iniciá sesión para agregar un local", "info");
          window.auth.loginWithGoogle();
          return;
        }
        this.showModal("modal-add-place");
      });
    },

    handleAddPlace(e) {
      return this.submitWithTurnstile({
        event: e,
        useFormData: false,
        submit: (payload) => window.api.places.create(payload),
        successMessage: "🎉 ¡Local enviado! Quedó pendiente de aprobación.",
      });
    },

    // ============================================================
    // MODAL: REVIEW
    // ============================================================
    openReviewModal(placeId, btn) {
      const form = document.getElementById("form-review");
      form.elements["place_id"].value = placeId;
      form.elements["rating"].value = "";
      form.elements["comment"].value = "";
      // Limpiar foto
      const photoInput = document.getElementById("review-photo-input");
      const photoPreview = document.getElementById("review-photo-preview");
      if (photoInput) photoInput.value = "";
      if (photoPreview) photoPreview.style.display = "none";
      this.previewStars(0, true);
      this.showModal("modal-review");

      // Preview de foto
      photoInput?.addEventListener("change", function() {
        const file = this.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (e) => {
          document.getElementById("review-photo-img").src = e.target.result;
          photoPreview.style.display = "block";
        };
        reader.readAsDataURL(file);
      });
      document.getElementById("review-photo-clear")?.addEventListener("click", function() {
        photoInput.value = "";
        photoPreview.style.display = "none";
      });
    },

    handleReview(e) {
      return this.submitWithTurnstile({
        event: e,
        useFormData: false,
        submit: async (payload) => {
          if (!payload.rating) {
            throw new Error("Elegí un rating con las estrellas");
          }
          const placeId = payload.place_id;
          // 1. Crear la review
          const review = await window.api.reviews.create(placeId, {
            rating: Number(payload.rating),
            comment: payload.comment,
            cf_turnstile_token: payload.cf_turnstile_token,
          });
          // 2. Si hay foto, subirla
          const photoInput = document.getElementById("review-photo-input");
          const file = photoInput?.files?.[0];
          if (file) {
            try {
              const resized = await window.imageResizer?.resize(file) || file;
              const formData = new FormData();
              formData.append("file", resized);
              // Token fresco para el upload de foto
              let photoToken = "";
              try { photoToken = await window.cfTurnstile?.getToken?.(e.target) || ""; } catch(_) {}
              formData.append("cf_turnstile_token", photoToken);
              await window.api.photos.uploadWithFormData(placeId, formData);
            } catch (photoErr) {
              console.warn("Review publicada pero falló la foto:", photoErr);
            }
          }
          return review;
        },
        successMessage: "⭐ Review publicada",
        onSuccess: async () => {
          // Refrescar el sidebar y el mapa
          const placeId = e.target.elements["place_id"].value;
          if (window.sidebarApp?.currentPlaceId === placeId) {
            await window.sidebarApp.open(placeId);
          }
          if (window.mapApp) await window.mapApp.loadPlaces();
        },
      });
    },

    // ============================================================
    // MODAL: SUGERENCIA DE EDICIÓN
    // ============================================================
    openSuggestionModal(placeId) {
      const form = document.getElementById("form-suggestion");
      form.elements["place_id"].value = placeId;
      form.elements["field_name"].value = "phone";
      form.elements["new_value"].value = "";
      this.showModal("modal-suggestion");
    },

    handleSuggestion(e) {
      return this.submitWithTurnstile({
        event: e,
        useFormData: false,
        submit: (payload) =>
          window.api.suggestions.create(
            payload.place_id,
            payload.field_name,
            payload.new_value,
            payload.cf_turnstile_token
          ),
        successMessage: "✏️ Sugerencia enviada para revisión",
      });
    },

    // ============================================================
    // PHOTO UPLOAD (desde el sidebar)
    // ============================================================
    /**
     * Sube una foto con Turnstile.
     * Se llama desde sidebar.js cuando el user hace click en "Agregar foto".
     * Usa FormData (multipart) y token en FormData.
     */
    async uploadPhoto(placeId, file) {
      try {
        // 1) Resize client-side (si está disponible)
        let fileToUpload = file;
        if (window.imageResize) {
          try {
            fileToUpload = await window.imageResize(file);
          } catch (e) {
            console.warn("Resize falló, subiendo original:", e);
          }
        }

        // 2) Crear un form invisible con un widget Turnstile embebido
        //    para poder tokenizar sin un modal visible
        const tempForm = await this.getOrCreateTurnstileForm();

        // 3) Token
        const token = await this.getTurnstileToken(tempForm);

        // 4) FormData con file + token
        const formData = new FormData();
        formData.append("file", fileToUpload);
        formData.append("cf_turnstile_token", token);

        // 5) Subir (usamos la misma signature de api.photos.upload,
        //    pero la modificamos para aceptar un FormData custom)
        await window.api.photos.uploadWithFormData(placeId, formData);

        window.toast("📸 Foto subida con éxito", "success");

        // 6) Reset Turnstile
        if (window.cfTurnstile) window.cfTurnstile.reset(tempForm);

        // 7) Refrescar sidebar
        if (window.sidebarApp?.currentPlaceId === placeId) {
          await window.sidebarApp.open(placeId);
        }
      } catch (err) {
        window.toast("Error al subir foto: " + err.message, "error");
        throw err;
      }
    },

    /**
     * Crea (si no existe) un form oculto con un widget Turnstile embebido
     * para los casos donde necesitamos tokenizar sin abrir un modal
     * (por ejemplo, upload de fotos desde el sidebar).
     */
    getOrCreateTurnstileForm() {
      return new Promise((resolve) => {
        let form = document.getElementById("cf-temp-form");
        if (!form) {
          form = document.createElement("form");
          form.id = "cf-temp-form";
          form.style.cssText =
            "position:absolute; left:-9999px; top:-9999px; pointer-events:none;";
          form.innerHTML = `<div class="cf-turnstile"></div>`;
          document.body.appendChild(form);
        }
        if (!window.cfTurnstile?.SITE_KEY) {
          resolve(form);
          return;
        }
        // Esperar a que Turnstile renderice
        const check = () => {
          if (form.querySelector(".cf-turnstile")?.dataset.rendered === "true") {
            resolve(form);
          } else {
            setTimeout(check, 200);
          }
        };
        check();
      });
    },

    // ============================================================
    // MODAL: ASISTENTE IA (sin Turnstile — endpoint público)
    // ============================================================
    async handleAssistant(e) {
      e.preventDefault();
      const input = document.getElementById("assistant-input");
      const msg = input.value.trim();
      if (!msg) return;
      input.value = "";

      this.appendAssistantMsg("user", msg);

      const center = window.mapApp?.map?.getCenter();
      try {
        const res = await window.api.assistant.suggest(
          msg,
          center?.lat,
          center?.lng,
          10
        );
        this.appendAssistantMsg("bot", res.message);

        if (res.suggested_places?.length) {
          const html = res.suggested_places
            .map(
              (p) =>
                `<button class="btn btn-secondary btn-sm" data-place-id="${this.esc(p.name)}" data-pid="${p.id}">${this.esc(p.name)}</button>`
            )
            .join(" ");
          const div = document.createElement("div");
          div.style.cssText =
            "display:flex; flex-wrap:wrap; gap:4px; margin-top:8px;";
          div.innerHTML = html;
          div.querySelectorAll("[data-pid]").forEach((btn) => {
            btn.addEventListener("click", () => {
              this.hideModal("modal-assistant");
              window.sidebarApp?.open(btn.dataset.pid);
            });
          });
          this.appendAssistantMsg("bot", div.outerHTML);
        }
      } catch (err) {
        this.appendAssistantMsg("bot", "❌ " + err.message);
      }
    },

    appendAssistantMsg(role, html) {
      const container = document.getElementById("assistant-messages");
      const div = document.createElement("div");
      div.className = `assistant-msg assistant-${role}`;
      div.innerHTML = html;
      container.appendChild(div);
      container.scrollTop = container.scrollHeight;
    },

    // ============================================================
    // RATING STARS
    // ============================================================
    initRatingStars() {
      const container = document.getElementById("rating-input");
      if (!container) return;
      const stars = container.querySelectorAll(".star");
      stars.forEach((star) => {
        star.addEventListener("mouseenter", () =>
          this.previewStars(star.dataset.value)
        );
        star.addEventListener("mouseleave", () =>
          this.previewStars(0, true)
        );
        star.addEventListener("click", () =>
          this.setRating(star.dataset.value)
        );
      });
    },

    previewStars(value, reset = false) {
      const stars = document.querySelectorAll("#rating-input .star");
      const current = reset
        ? document.getElementById("rating-value").value
        : value;
      stars.forEach((s) => {
        s.classList.toggle("active", Number(s.dataset.value) <= Number(current));
      });
    },

    setRating(value) {
      document.getElementById("rating-value").value = value;
      this.previewStars(value);
    },

    // ============================================================
    // MODAL HELPERS
    // ============================================================
    showModal(id) {
      document.getElementById(id).classList.remove("hidden");
    },

    hideModal(id) {
      document.getElementById(id).classList.add("hidden");
    },

    getFormData(form) {
      const fd = new FormData(form);
      const obj = {};
      for (const [k, v] of fd.entries()) {
        if (v === "" || v === null) continue;
        if (k === "has_delivery") obj[k] = true;
        else if (["lat", "lng"].includes(k)) obj[k] = Number(v);
        else obj[k] = v;
      }
      return obj;
    },

    esc(s) {
      if (s === null || s === undefined) return "";
      return String(s).replace(/[&<>"']/g, (c) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      }[c]));
    },
  };

  window.formsApp = formsApp;
})();
  window.formsApp = formsApp;
})();
