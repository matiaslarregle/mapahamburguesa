/**
 * Sidebar: panel de detalle de un local.
 * Estructura modular: estados (loading/error/empty/ok) + render separado.
 * Expone: window.sidebarApp
 */
(function () {
  const sidebarApp = {
    // ---------- Refs ----------
    el: null,
    overlayEl: null,
    contentEl: null,
    currentPlaceId: null,
    currentPlace: null,
    currentUser: null,
    galleryIndex: 0,
    galleryImages: [],

    // ====================== INIT ======================
    init() {
      this.el = document.getElementById("sidebar");
      this.overlayEl = document.getElementById("sidebar-overlay");
      this.contentEl = document.getElementById("sidebar-content");

      // Cerrar sidebar
      document
        .getElementById("btn-close-sidebar")
        .addEventListener("click", () => this.close());
      this.overlayEl.addEventListener("click", () => this.close());
      document.addEventListener("keydown", (e) => {
        if (
          e.key === "Escape" &&
          !this.el.classList.contains("hidden") &&
          this.isTopModal()  // no cerrar si hay un modal encima
        ) {
          this.close();
        }
      });

      // Galería lightbox
      this.initGallery();
    },

    isTopModal() {
      const openModals = [...document.querySelectorAll(".modal:not(.hidden)")];
      return openModals.length === 0;
    },

    // ====================== OPEN / CLOSE ======================
    async open(placeId) {
      this.currentPlaceId = placeId;
      this.el.classList.remove("hidden");
      this.overlayEl.classList.remove("hidden");
      this.el.setAttribute("aria-hidden", "false");
      this.renderLoading();

      try {
        const [place, user] = await Promise.all([
          window.api.places.get(placeId),
          window.auth ? window.auth.getCurrentUser() : Promise.resolve(null),
        ]);

        if (!place) throw new Error("Local no encontrado");

        this.currentPlace = place;
        this.currentUser = user;

        // Traer fotos y reviews en paralelo
        const [photos, reviews] = await Promise.all([
          window.api.photos.list(placeId).catch(() => []),
          window.api.reviews.list(placeId).catch(() => []),
        ]);

        this.render(place, photos, reviews);
      } catch (err) {
        console.error("Error abriendo sidebar:", err);
        this.renderError(err.message);
      }
    },

    close() {
      this.el.classList.add("hidden");
      this.overlayEl.classList.add("hidden");
      this.el.setAttribute("aria-hidden", "true");
      this.currentPlaceId = null;
      this.currentPlace = null;
    },

    // ====================== ESTADOS DE RENDER ======================
    renderLoading() {
      this.contentEl.innerHTML = `
        <div class="sidebar-loading">
          <div class="spinner"></div>
          <p>Cargando…</p>
        </div>`;
    },

    renderError(message) {
      this.contentEl.innerHTML = `
        <div class="sidebar-error">
          <div class="emoji">😕</div>
          <p>${this.esc(message)}</p>
          <button class="btn btn-secondary" onclick="window.sidebarApp.close()">Cerrar</button>
        </div>`;
    },

    render(place, photos, reviews) {
      const userHasReview = this.currentUser
        ? reviews.find((r) => r.user_id === this.currentUser.id)
        : null;
      const isOpen = this.isOpenNow(place.schedule);
      const html = `
        ${this.renderHeader(place)}
        ${this.renderRating(place)}
        ${this.renderTags(place, isOpen)}
        ${this.renderActions(userHasReview)}
        ${this.renderContact(place)}
        ${this.renderSchedule(place)}
        ${this.renderPayments(place)}
        ${this.renderHighlights(place)}
        ${this.renderGallery(photos)}
        ${this.renderReviews(reviews, userHasReview, photos)}
        ${this.renderFooter(place)}
      `;
      this.contentEl.innerHTML = html;
      this.bindActions();
    },

    // ====================== SUB-RENDERS ======================
    renderHeader(place) {
      return `
        <h1 id="sidebar-title" class="place-name">${this.esc(place.name)}</h1>
        <p class="place-address">📍 ${this.esc(place.address)}, ${this.esc(place.city)} (${this.esc(place.partido)})</p>
      `;
    },

    renderRating(place) {
      const rating = place.avg_rating || 0;
      const stars = "★".repeat(Math.round(rating)) + "☆".repeat(5 - Math.round(rating));
      return `
        <div class="rating-bar">
          <span class="rating-stars">${stars}</span>
          <span class="rating-number">${rating.toFixed(1)}</span>
          <span class="rating-count">(${place.review_count || 0} reviews)</span>
        </div>
      `;
    },

    renderTags(place, isOpen) {
      return `
        <div class="tag-row">
          ${place.place_type  ? `<span class="tag">${this.typeLabel(place.place_type)}</span>` : ""}
          ${place.price_range ? `<span class="tag">${this.priceLabel(place.price_range)}</span>` : ""}
          ${isOpen !== null   ? `<span class="tag ${isOpen ? "tag-open" : "tag-closed"}">${isOpen ? "🟢 Abierto" : "🔴 Cerrado"}</span>` : ""}
          ${place.has_delivery ? `<span class="tag tag-delivery">🛵 Delivery</span>` : ""}
        </div>
      `;
    },

    renderActions(userHasReview) {
      if (!this.currentUser) {
        return `
          <div class="sidebar-actions">
            <button class="btn btn-secondary btn-block" id="btn-login-from-sidebar">
              🔐 Iniciá sesión para dejar review, sugerir cambios o subir fotos
            </button>
          </div>
        `;
      }
      return `
        <div class="sidebar-actions">
          <button class="btn btn-primary" data-action="review" ${userHasReview ? "disabled title='Ya dejaste tu review'" : ""}>
            ${userHasReview ? "✓ Ya dejaste review" : "⭐ Dejar review"}
          </button>
          <button class="btn btn-secondary" data-action="suggest">✏️ Sugerir</button>

        </div>
      `;
    },

    renderContact(place) {
      const phoneClean = (place.phone || "").replace(/\D/g, "");
      const waLink = phoneClean ? `https://wa.me/${phoneClean}` : null;
      const igUser = (place.instagram || "").replace("@", "");
      const igLink = igUser ? `https://instagram.com/${igUser}` : null;

      if (!place.phone && !place.website && !igLink) return "";

      return `
        <div class="sidebar-section">
          <h3>📞 Contacto</h3>
          ${place.phone  ? `<a class="contact-link" href="tel:${this.esc(place.phone)}">📞 ${this.esc(place.phone)}</a>` : ""}
          ${waLink       ? `<a class="contact-link" href="${waLink}" target="_blank" rel="noopener">💬 WhatsApp</a>` : ""}
          ${place.website ? `<a class="contact-link" href="${this.esc(place.website)}" target="_blank" rel="noopener">🌐 Sitio web</a>` : ""}
          ${igLink       ? `<a class="contact-link" href="${igLink}" target="_blank" rel="noopener">📷 @${this.esc(igUser)}</a>` : ""}
        </div>
      `;
    },

    renderSchedule(place) {
      if (!place.schedule || !Object.keys(place.schedule).length) return "";
      const days = [
        { key: "lun", label: "Lunes" },
        { key: "mar", label: "Martes" },
        { key: "mie", label: "Miércoles" },
        { key: "jue", label: "Jueves" },
        { key: "vie", label: "Viernes" },
        { key: "sab", label: "Sábado" },
        { key: "dom", label: "Domingo" },
      ];
      const todayKey = ["dom", "lun", "mar", "mie", "jue", "vie", "sab"][new Date().getDay()];
      return `
        <div class="sidebar-section">
          <h3>🕐 Horarios</h3>
          <div class="schedule">
            ${days
              .map(
                (d) => `
              <span class="schedule-day ${d.key === todayKey ? "schedule-today" : ""}">${d.label}</span>
              <span class="schedule-time">${this.esc(place.schedule[d.key] || "Cerrado")}</span>
            `
              )
              .join("")}
          </div>
        </div>
      `;
    },

    renderPayments(place) {
      if (!place.payment_methods?.length) return "";
      return `
        <div class="sidebar-section">
          <h3>💳 Acepta</h3>
          <div class="tag-row">
            ${place.payment_methods.map((m) => `<span class="tag">${this.paymentLabel(m)}</span>`).join("")}
          </div>
        </div>
      `;
    },

    renderHighlights(place) {
      if (!place.menu_highlights) return "";
      return `
        <div class="sidebar-section">
          <h3>🍔 Lo que se destaca</h3>
          <p>${this.esc(place.menu_highlights)}</p>
        </div>
      `;
    },

    renderGallery(photos) {
      if (!photos.length) return "";
      return `
        <div class="sidebar-section">
          <h3>📸 Fotos (${photos.length})</h3>
          <div class="photo-gallery">
            ${photos
              .map(
                (ph, i) =>
                  `<img src="${ph.url}" alt="Foto ${i + 1}" loading="lazy" data-photo-index="${i}" />`
              )
              .join("")}
          </div>
        </div>
      `;
    },

    renderReviews(reviews, userHasReview, photos = []) {
      const canEdit = userHasReview && this.currentUser;
      return `
        <div class="sidebar-section">
          <h3>⭐ Reviews (${reviews.length})</h3>
          ${reviews.length === 0
            ? `<p class="reviews-empty">Todavía no hay reviews. ¡Sé el primero en opinar!</p>`
            : reviews
                .map((r) => this.renderReviewItem(r, canEdit, photos.filter(p => p.review_id === r.id)))
                .join("")
          }
        </div>
      `;
    },

    renderReviewItem(r, canEdit, reviewPhotos = []) {
      const author = r.profiles?.name || "Usuario";
      const avatar = r.profiles?.avatar_url;
      const date = new Date(r.created_at).toLocaleDateString("es-AR", {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
      const isOwn = this.currentUser && r.user_id === this.currentUser.id;
      const stars = "★".repeat(r.rating) + "☆".repeat(5 - r.rating);

      return `
        <div class="review-item" data-review-id="${r.id}">
          <div class="review-header">
            <div class="review-author-info">
              ${avatar
                ? `<img src="${avatar}" alt="" class="review-avatar" />`
                : `<div class="review-avatar review-avatar-default">${author.charAt(0).toUpperCase()}</div>`
              }
              <div>
                <span class="review-author">${this.esc(author)}${isOwn ? " (vos)" : ""}</span>
                <span class="review-date">${date}</span>
              </div>
            </div>
            <span class="review-stars">${stars}</span>
          </div>
          ${r.comment ? `<p class="review-comment">${this.esc(r.comment)}</p>` : ""}
          ${reviewPhotos.length ? `
            <div class="review-photos">
              ${reviewPhotos.map((ph) => `<img src="${ph.url}" alt="Foto de review" class="review-photo" loading="lazy" />`).join("")}
            </div>` : ""}
          ${isOwn ? `
            <div class="review-actions">
              <button class="btn btn-ghost btn-sm" data-review-action="edit" data-review-id="${r.id}">Editar</button>
              <button class="btn btn-ghost btn-sm" data-review-action="delete" data-review-id="${r.id}">Borrar</button>
            </div>
          ` : ""}
        </div>
      `;
    },

    renderFooter(place) {
      return `
        <div class="sidebar-footer">
          <p class="sidebar-source">Datos aportados por la comunidad 🍔</p>
          <a href="https://www.google.com/maps/search/?api=1&query=${place.lat},${place.lng}"
             target="_blank" rel="noopener" class="btn btn-ghost btn-block">
            🗺️ Ver en Google Maps
          </a>
        </div>
      `;
    },

    // ====================== ACTIONS ======================
    bindActions() {
      // Botones [data-action] (review, suggest, photo)
      this.contentEl.querySelectorAll("[data-action]").forEach((btn) => {
        btn.addEventListener("click", () =>
          this.handleAction(btn.dataset.action, btn)
        );
      });

      // Login desde sidebar
      this.contentEl
        .querySelector("#btn-login-from-sidebar")
        ?.addEventListener("click", () => window.auth.loginWithGoogle());

      // Galería → lightbox
      this.contentEl.querySelectorAll(".photo-gallery img").forEach((img) => {
        img.addEventListener("click", () => {
          this.galleryIndex = Number(img.dataset.photoIndex);
          this.openGallery();
        });
      });

      // Fotos dentro de reviews → lightbox
      this.contentEl.querySelectorAll(".review-photo").forEach((img) => {
        img.addEventListener("click", () => {
          this.galleryImages = [...this.contentEl.querySelectorAll(".review-photo")].map(i => i.src);
          this.galleryIndex = [...this.contentEl.querySelectorAll(".review-photo")].indexOf(img);
          document.getElementById("modal-gallery").classList.remove("hidden");
          this.renderGalleryImage();
        });
      });

      // Acciones de review (editar/borrar)
      this.contentEl.querySelectorAll("[data-review-action]").forEach((btn) => {
        btn.addEventListener("click", () =>
          this.handleReviewAction(btn.dataset.reviewAction, btn.dataset.reviewId)
        );
      });
    },

    handleAction(action, btn) {
      if (!this.currentUser) {
        window.auth.loginWithGoogle();
        return;
      }
      if (action === "review" && window.formsApp) {
        window.formsApp.openReviewModal(this.currentPlaceId, btn);
      }
      if (action === "suggest" && window.formsApp) {
        window.formsApp.openSuggestionModal(this.currentPlaceId);
      }
      if (action === "photo") {
        this.uploadPhoto();
      }
    },

    async handleReviewAction(action, reviewId) {
      if (action === "delete") {
        if (!confirm("¿Borrar tu review?")) return;
        try {
          await window.api.reviews.delete(this.currentPlaceId, reviewId);
          window.toast("🗑️ Review eliminada", "success");
          await this.open(this.currentPlaceId); // refresh
          if (window.mapApp) await window.mapApp.loadPlaces();
        } catch (err) {
          window.toast("Error: " + err.message, "error");
        }
      }
      if (action === "edit") {
        // Abrir el modal de review pre-cargado
        if (window.formsApp?.openReviewEditModal) {
          window.formsApp.openReviewEditModal(this.currentPlaceId, reviewId);
        } else {
          window.toast("Edición de review no implementada", "info");
        }
      }
    },

    async uploadPhoto() {
      const input = document.createElement("input");
      input.type = "file";
      input.accept = "image/*";
      input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        try {
          if (window.formsApp?.uploadPhoto) {
            await window.formsApp.uploadPhoto(this.currentPlaceId, file);
          } else {
            let fileToUpload = file;
            if (window.imageResize) {
              fileToUpload = await window.imageResize(file);
            }
            await window.api.photos.upload(this.currentPlaceId, fileToUpload);
            window.toast("📸 Foto subida con éxito", "success");
            await this.open(this.currentPlaceId);
          }
        } catch (err) {
          console.error("uploadPhoto error:", err);
        }
      };
      input.click();
    },

    // ====================== GALLERY LIGHTBOX ======================
    initGallery() {
      const modal = document.getElementById("modal-gallery");
      document.getElementById("gallery-prev")?.addEventListener("click", () =>
        this.galleryNav(-1)
      );
      document.getElementById("gallery-next")?.addEventListener("click", () =>
        this.galleryNav(1)
      );
      modal?.querySelectorAll("[data-close-modal]").forEach((btn) =>
        btn.addEventListener("click", () => this.closeGallery())
      );
      document.addEventListener("keydown", (e) => {
        if (modal?.classList.contains("hidden")) return;
        if (e.key === "ArrowLeft") this.galleryNav(-1);
        if (e.key === "ArrowRight") this.galleryNav(1);
      });
    },

    openGallery() {
      // Necesitamos el array de URLs → lo tomamos del render actual
      this.galleryImages = [
        ...this.contentEl.querySelectorAll(".photo-gallery img"),
      ].map((img) => img.src);
      if (!this.galleryImages.length) return;

      document.getElementById("modal-gallery").classList.remove("hidden");
      this.renderGalleryImage();
    },

    closeGallery() {
      document.getElementById("modal-gallery").classList.add("hidden");
    },

    galleryNav(delta) {
      this.galleryIndex =
        (this.galleryIndex + delta + this.galleryImages.length) %
        this.galleryImages.length;
      this.renderGalleryImage();
    },

    renderGalleryImage() {
      const url = this.galleryImages[this.galleryIndex];
      document.getElementById("gallery-image").src = url;
      document.getElementById("gallery-counter").textContent =
        `${this.galleryIndex + 1} / ${this.galleryImages.length}`;
    },

    // ====================== HELPERS ======================
    isOpenNow(schedule) {
      if (!schedule) return null;
      const days = ["dom", "lun", "mar", "mie", "jue", "vie", "sab"];
      const now = new Date();
      const ar = new Date(now.getTime() - 3 * 60 * 60 * 1000);
      const dayKey = days[ar.getUTCDay()];
      const todayHours = schedule[dayKey];
      if (!todayHours || todayHours.toLowerCase() === "cerrado") return false;
      const match = todayHours.match(/(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})/);
      if (!match) return null;
      const [, h1, m1, h2, m2] = match.map(Number);
      const cur = ar.getUTCHours() * 60 + ar.getUTCMinutes();
      const from = h1 * 60 + m1;
      const to = h2 * 60 + m2;
      return cur >= from && cur <= to;
    },

    typeLabel(t) {
      return (
        {
          fast_food: "🍔 Fast food",
          gourmet: "👨‍🍳 Gourmet",
          dark_kitchen: "🌙 Dark kitchen",
          food_truck: "🚚 Food truck",
          other: "📦 Otro",
        }[t] || t
      );
    },

    priceLabel(p) {
      return { cheap: "💰 Barato", mid: "💵 Medio", expensive: "💎 Caro" }[p] || p;
    },

    paymentLabel(m) {
      return (
        {
          efectivo: "💵 Efectivo",
          debito: "💳 Débito",
          credito: "💳 Crédito",
          mp: "🟦 MercadoPago",
          uala: "🟨 Ualá",
          transferencia: "🏦 Transferencia",
        }[m] || m
      );
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

  window.sidebarApp = sidebarApp;
})();
