/**
 * Filtros: aplica, limpia, carga dinámicamente opciones.
 */
(function () {
  const filtersApp = {
    init() {
      this.populatePartidos();
      document
        .getElementById("btn-apply-filters")
        .addEventListener("click", () => this.apply());
      document
        .getElementById("btn-clear-filters")
        .addEventListener("click", () => this.clear());
    },

    async populatePartidos() {
      // Pedimos hasta 200 locales solo para extraer partidos únicos
      try {
        const res = await window.api.places.list({ limit: 200 });
        const partidos = [...new Set((res.items || []).map((p) => p.partido))].sort();
        const sel = document.getElementById("filter-partido");
        partidos.forEach((p) => {
          const opt = document.createElement("option");
          opt.value = p;
          opt.textContent = p;
          sel.appendChild(opt);
        });
      } catch (err) {
        console.warn("No se pudieron cargar partidos:", err);
      }
    },

    collect() {
      return {
        partido: this.val("filter-partido") || null,
        place_type: this.val("filter-tipo") || null,
        price_range: this.val("filter-precio") || null,
        has_delivery: this.checked("filter-delivery") ? true : null,
        // abierto_ahora se calcula en backend (no implementado en Parte 3, lo dejamos null)
        payment_method: this.collectPayment() || null,
      };
    },

    collectPayment() {
      const checked = [...document.querySelectorAll(".checkbox-pill input:checked")];
      return checked.length ? checked[0].value : null;
    },

    async apply() {
      const filters = this.collect();
      window.toast("🔍 Aplicando filtros…", "info");
      if (window.mapApp) await window.mapApp.loadPlaces(filters);
      window.toast(`✅ ${window.mapApp?.places.length || 0} locales`, "success");
    },

    clear() {
      ["filter-partido", "filter-tipo", "filter-precio"].forEach((id) => {
        document.getElementById(id).value = "";
      });
      document.getElementById("filter-delivery").checked = false;
      document.getElementById("filter-abierto").checked = false;
      document
        .querySelectorAll(".checkbox-pill input")
        .forEach((c) => (c.checked = false));
      document.getElementById("search-input").value = "";
      if (window.mapApp) window.mapApp.loadPlaces();
    },

    val(id) {
      return document.getElementById(id).value || null;
    },
    checked(id) {
      return document.getElementById(id).checked;
    },
  };

  window.filtersApp = filtersApp;
})();
