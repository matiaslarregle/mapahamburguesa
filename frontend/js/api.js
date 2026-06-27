/**
 * Wrappers de fetch a FastAPI.
 * Adjunta automáticamente el Bearer token si hay sesión.
 * Base URL configurable vía window.API_BASE_URL.
 */
(function () {
  const api = {
    BASE_URL: window.API_BASE_URL || "https://mapahamburguesa-api-glmc.onrender.com",

    // ====================== Helper genérico ======================
    async request(path, options = {}) {
      const url = `${this.BASE_URL}${path}`;
      const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      };

      // Adjuntar token si existe
      if (window.auth && !options.skipAuth) {
        const token = await window.auth.getAccessToken();
        if (token) headers["Authorization"] = `Bearer ${token}`;
      }

      const res = await fetch(url, { ...options, headers });
      const ct = res.headers.get("content-type") || "";

      let body;
      if (ct.includes("application/json")) {
        body = await res.json().catch(() => null);
      } else {
        body = await res.text();
      }

      if (!res.ok) {
        const detail =
          (body && body.detail) || res.statusText || "Error desconocido";
        const err = new Error(detail);
        err.status = res.status;
        err.body = body;
        throw err;
      }
      return body;
    },

    // ====================== Auth ======================
    auth: {
      me: () => api.request("/auth/me"),
    },

    // ====================== Places ======================
    places: {
      /**
       * Listar locales con filtros opcionales.
       */
      list(params = {}) {
        const qs = new URLSearchParams(
          Object.entries(params).filter(([_, v]) => v !== null && v !== undefined && v !== "")
        ).toString();
        return api.request(`/places/${qs ? "?" + qs : ""}`);
      },

      getVisited() {
        return api.request("/places/visited");
      },

      get(id) {
        return api.request(`/places/${id}`);
      },

      create(data) {
        return api.request(`/places/`, {
          method: "POST",
          body: JSON.stringify(data),
        });
      },

      update(id, data) {
        return api.request(`/places/${id}`, {
          method: "PUT",
          body: JSON.stringify(data),
        });
      },

      delete(id) {
        return api.request(`/places/${id}`, { method: "DELETE" });
      },
    },

    // ====================== Reviews ======================
    reviews: {
      list(placeId) {
        return api.request(`/places/${placeId}/reviews`);
      },
      create(placeId, data) {
        return api.request(`/places/${placeId}/reviews`, {
          method: "POST",
          body: JSON.stringify(data),
        });
      },
      update(placeId, reviewId, data) {
        return api.request(`/places/${placeId}/reviews/${reviewId}`, {
          method: "PUT",
          body: JSON.stringify(data),
        });
      },
      delete(placeId, reviewId) {
        return api.request(`/places/${placeId}/reviews/${reviewId}`, {
          method: "DELETE",
        });
      },
    },

    // ====================== Photos ======================
    photos: {
      list(placeId) {
        return api.request(`/places/${placeId}/photos`);
      },

      /**
       * Upload de foto vía FormData.
       * NO usar el wrapper genérico porque necesitamos multipart.
       */
      async upload(placeId, file, isCover = false) {
        const url = `${api.BASE_URL}/places/${placeId}/photos`;
        const formData = new FormData();
        formData.append("file", file);
        if (isCover) formData.append("is_cover", "true");

        const headers = {};
        if (window.auth) {
          const token = await window.auth.getAccessToken();
          if (token) headers["Authorization"] = `Bearer ${token}`;
        }

        const res = await fetch(url, { method: "POST", body: formData, headers });
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail || "Error al subir la foto");
        }
        return res.json();
      },

      async uploadWithFormData(placeId, formData) {
        const url = `${api.BASE_URL}/places/${placeId}/photos`;
        const headers = {};
        if (window.auth) {
          const token = await window.auth.getAccessToken();
          if (token) headers["Authorization"] = `Bearer ${token}`;
        }

        const res = await fetch(url, { method: "POST", body: formData, headers });
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail || "Error al subir la foto");
        }
        return res.json();
      },

      delete(placeId, photoId) {
        return api.request(`/places/${placeId}/photos/${photoId}`, {
          method: "DELETE",
        });
      },

      setCover(placeId, photoId) {
        return api.request(`/places/${placeId}/photos/${photoId}/cover`, {
          method: "PATCH",
        });
      },
    },

    // ====================== Suggestions ======================
    suggestions: {
      create(placeId, fieldName, newValue, turnstileToken = null) {
        const body = { field_name: fieldName, new_value: newValue };
        if (turnstileToken) body.cf_turnstile_token = turnstileToken;
        return api.request(`/places/${placeId}/suggestions`, {
          method: "POST",
          body: JSON.stringify(body),
        });
      },
    },

    // ====================== Admin ======================
    admin: {
      stats: () => api.request("/admin/stats"),
      pendingPlaces: () => api.request("/admin/places/pending"),
      approvePlace: (id) =>
        api.request(`/admin/places/${id}/approve`, { method: "PATCH" }),
      rejectPlace: (id) =>
        api.request(`/admin/places/${id}/reject`, { method: "PATCH" }),
      pendingSuggestions: () => api.request("/admin/suggestions/pending"),
      approveSuggestion: (id) =>
        api.request(`/admin/suggestions/${id}/approve`, { method: "PATCH" }),
      rejectSuggestion: (id) =>
        api.request(`/admin/suggestions/${id}/reject`, { method: "PATCH" }),
    },

    // ====================== Assistant (Gemini) ======================
    assistant: {
      suggest(message, lat = null, lng = null, radiusKm = 10) {
        return api.request("/assistant/suggest", {
          method: "POST",
          body: JSON.stringify({
            message,
            lat,
            lng,
            radius_km: radiusKm,
          }),
          skipAuth: true, // público
        });
      },
    },
  };

  window.api = api;
})();
