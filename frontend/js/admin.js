/**
 * Panel de administración.
 * Verifica que el usuario sea admin/moderator, carga stats, pendientes, etc.
 */
(function () {
  const adminApp = {
    currentUser: null,

    init: async function () {
      // 1) Auth check
      this.currentUser = await window.auth.getCurrentUser();
      if (!this.currentUser) {
        window.location.href = "index.html";
        return;
      }
      if (!window.auth.isModerator(this.currentUser)) {
        alert("No tenés permisos para acceder a este panel.");
        window.location.href = "index.html";
        return;
      }

      // 2) Pintar nombre
      document.getElementById("admin-user-name").textContent =
        `Hola, ${this.currentUser.name}`;

      // 3) Logout
      document
        .getElementById("btn-admin-logout")
        .addEventListener("click", () => window.auth.logout());

      // 4) Tabs
      document.querySelectorAll(".tab").forEach((tab) => {
        tab.addEventListener("click", () => this.switchTab(tab.dataset.tab));
      });

      // 5) Cargar datos iniciales
      await this.loadStats();
      await this.loadPendingPlaces();
      await this.loadPendingSuggestions();
    },

    // ====================== TABS ======================
    switchTab(tabName) {
      document.querySelectorAll(".tab").forEach((t) =>
        t.classList.toggle("active", t.dataset.tab === tabName)
      );
      document.querySelectorAll(".tab-content").forEach((c) =>
        c.classList.toggle("active", c.id === `tab-${tabName}`)
      );
    },

    // ====================== STATS ======================
    async loadStats() {
      try {
        const stats = await window.api.admin.stats();
        document.getElementById("stat-places-approved").textContent =
          stats.places_approved ?? 0;
        document.getElementById("stat-places-pending").textContent =
          stats.places_pending ?? 0;
        document.getElementById("stat-suggestions-pending").textContent =
          stats.suggestions_pending ?? 0;
        document.getElementById("stat-users").textContent = stats.users_total ?? 0;

        // Badges en tabs
        if (stats.places_pending > 0) {
          const b = document.getElementById("badge-places");
          b.textContent = stats.places_pending;
          b.classList.remove("hidden");
        }
        if (stats.suggestions_pending > 0) {
          const b = document.getElementById("badge-suggestions");
          b.textContent = stats.suggestions_pending;
          b.classList.remove("hidden");
        }
      } catch (err) {
        console.error("Error stats:", err);
      }
    },

    // ====================== PENDING PLACES ======================
    async loadPendingPlaces() {
      const list = document.getElementById("pending-places-list");
      list.innerHTML = '<div class="loading">Cargando…</div>';
      try {
        const places = await window.api.admin.pendingPlaces();
        if (!places.length) {
          list.innerHTML = `
            <div class="empty-state">
              <div class="emoji">🎉</div>
              <p>No hay locales pendientes.</p>
            </div>`;
          return;
        }
        list.innerHTML = places
          .map(
            (p) => `
          <div class="admin-card" data-place-id="${p.id}">
            <div class="admin-card-info">
              <h3>${this.esc(p.name)}</h3>
              <p>📍 ${this.esc(p.address)}, ${this.esc(p.city)} (${this.esc(p.partido)})</p>
              ${p.phone ? `<p>📞 ${this.esc(p.phone)}</p>` : ""}
              ${p.place_type ? `<p>🏷️ ${p.place_type}</p>` : ""}
              ${p.menu_highlights ? `<p>🍔 ${this.esc(p.menu_highlights)}</p>` : ""}
              <p style="font-size: 11px; color: #999;">Subido: ${new Date(
                p.created_at
              ).toLocaleString("es-AR")}</p>
            </div>
            <div class="admin-card-actions">
              <button class="btn btn-success" data-action="approve" data-id="${p.id}">
                ✓ Aprobar
              </button>
              <button class="btn btn-danger" data-action="reject" data-id="${p.id}">
                ✗ Rechazar
              </button>
            </div>
          </div>`
          )
          .join("");

        // Listeners
        list.querySelectorAll("[data-action]").forEach((btn) => {
          btn.addEventListener("click", () =>
            this.handlePlaceAction(btn.dataset.action, btn.dataset.id)
          );
        });
      } catch (err) {
        list.innerHTML = `<p style="color: var(--color-danger);">Error: ${err.message}</p>`;
      }
    },

    async handlePlaceAction(action, placeId) {
      if (!confirm(`¿${action === "approve" ? "Aprobar" : "Rechazar"} este local?`))
        return;
      try {
        if (action === "approve") {
          await window.api.admin.approvePlace(placeId);
          window.toast("✅ Local aprobado", "success");
        } else {
          await window.api.admin.rejectPlace(placeId);
          window.toast("🚫 Local rechazado", "info");
        }
        await this.loadPendingPlaces();
        await this.loadStats();
      } catch (err) {
        window.toast("Error: " + err.message, "error");
      }
    },

    // ====================== PENDING SUGGESTIONS ======================
    async loadPendingSuggestions() {
      const list = document.getElementById("pending-suggestions-list");
      list.innerHTML = '<div class="loading">Cargando…</div>';
      try {
        const suggestions = await window.api.admin.pendingSuggestions();
        if (!suggestions.length) {
          list.innerHTML = `
            <div class="empty-state">
              <div class="emoji">✨</div>
              <p>No hay sugerencias pendientes.</p>
            </div>`;
          return;
        }
        list.innerHTML = suggestions
          .map(
            (s) => `
          <div class="admin-card">
            <div class="admin-card-info">
              <h3>${this.esc(s.places?.name || "Local")}</h3>
              <p>👤 Sugerido por: ${this.esc(s.profiles?.name || "anónimo")}</p>
              <p>📝 <strong>${this.esc(s.field_name)}</strong></p>
              ${
                s.old_value
                  ? `<p style="color: #b71c1c; text-decoration: line-through;">Antes: ${this.esc(
                      s.old_value
                    )}</p>`
                  : ""
              }
              <p style="color: #1b5e20;">Propuesto: <strong>${this.esc(s.new_value)}</strong></p>
            </div>
            <div class="admin-card-actions">
              <button class="btn btn-success" data-action="approve" data-id="${s.id}">
                ✓ Aplicar
              </button>
              <button class="btn btn-danger" data-action="reject" data-id="${s.id}">
                ✗ Rechazar
              </button>
            </div>
          </div>`
          )
          .join("");

        list.querySelectorAll("[data-action]").forEach((btn) => {
          btn.addEventListener("click", () =>
            this.handleSuggestionAction(btn.dataset.action, btn.dataset.id)
          );
        });
      } catch (err) {
        list.innerHTML = `<p style="color: var(--color-danger);">Error: ${err.message}</p>`;
      }
    },

    async handleSuggestionAction(action, suggestionId) {
      if (!confirm(`¿${action === "approve" ? "Aplicar" : "Rechazar"} esta sugerencia?`))
        return;
      try {
        if (action === "approve") {
          await window.api.admin.approveSuggestion(suggestionId);
          window.toast("✅ Sugerencia aplicada al local", "success");
        } else {
          await window.api.admin.rejectSuggestion(suggestionId);
          window.toast("🚫 Sugerencia rechazada", "info");
        }
        await this.loadPendingSuggestions();
        await this.loadStats();
      } catch (err) {
        window.toast("Error: " + err.message, "error");
      }
    },

    esc(s) {
      if (s === null || s === undefined) return "";
      return String(s).replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
      }[c]));
    },
  };

  window.adminApp = adminApp;
  document.addEventListener("DOMContentLoaded", () => adminApp.init());
})();
