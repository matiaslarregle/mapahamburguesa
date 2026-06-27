/**
 * Mapa Leaflet: init, fetch de locales, markers con clustering, heatmap.
 * Expone: window.mapApp
 */
(function () {
  const mapApp = {
    map: null,
    cluster: null,
    heatLayer: null,
    showHeatmap: false,
    places: [],
    markersByPlaceId: {},
    visitedPlaceIds: new Set(),

    // Color del marker según place_type
    typeColors: {
      fast_food:   "#ff6b35",
      gourmet:     "#c44d00",
      dark_kitchen:"#6a4c93",
      food_truck:  "#06a77d",
      other:       "#666",
    },

    // ---------- INIT ----------
    init() {
      this.map = L.map("map", {
        center: [-34.8, -58.2], // Adrogué como default
        zoom: 12,
        zoomControl: true,
      });

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution:
          '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      }).addTo(this.map);

      // Cluster
      this.cluster = L.markerClusterGroup({
        maxClusterRadius: 60,
        disableClusteringAtZoom: 16,
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false,
      });
      this.map.addLayer(this.cluster);

      // Geolocalización del usuario (best-effort)
      this.tryLocate();

      // Toggle heatmap con tecla "h"
      document.addEventListener("keydown", (e) => {
        if (e.key.toLowerCase() === "h" && !e.target.matches("input, textarea")) {
          this.toggleHeatmap();
        }
      });

      console.log("🗺️ Mapa inicializado");
    },

    tryLocate() {
      if (!navigator.geolocation) return;
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          this.map.setView([pos.coords.latitude, pos.coords.longitude], 13);
        },
        () => {}, // silencio si el user rechaza
        { enableHighAccuracy: false, timeout: 5000 }
      );
    },

    // ---------- FETCH + RENDER ----------
    async loadPlaces(filters = {}) {
      try {
        // Cargar locales visitados si el usuario está logueado
        if (window.auth) {
          const user = await window.auth.getCurrentUser();
          if (user) {
            try {
              const visited = await window.api.places.getVisited();
              this.visitedPlaceIds = new Set(visited.visited_place_ids || []);
            } catch (_) {}
          }
        }

        const res = await window.api.places.list({
          limit: 200,
          ...filters,
        });
        this.places = res.items || [];
        this.renderMarkers();
        if (this.showHeatmap) this.renderHeatmap();
      } catch (err) {
        console.error("Error cargando locales:", err);
        this.showToast("Error al cargar los locales", "error");
      }
    },

    renderMarkers() {
      this.cluster.clearLayers();
      this.markersByPlaceId = {};

      this.places.forEach((p) => {
        const icon = this.makeIcon(p);
        const marker = L.marker([p.lat, p.lng], { icon, title: p.name });

        marker.on("click", () => {
          if (window.sidebarApp) window.sidebarApp.open(p.id);
        });

        // Mini popup on hover (no abre sidebar)
        marker.bindTooltip(
          `<strong>${this.escape(p.name)}</strong><br>
           <small>${this.escape(p.address)}</small><br>
           ${"★".repeat(Math.round(p.avg_rating || 0))} ${(p.avg_rating || 0).toFixed(1)}
           (${p.review_count || 0} reviews)`,
          { direction: "top", offset: [0, -10] }
        );

        this.cluster.addLayer(marker);
        this.markersByPlaceId[p.id] = marker;
      });
    },

    makeIcon(place) {
      const color = this.typeColors[place.place_type] || "#666";
      const rating = (place.avg_rating || 0).toFixed(1);
      const visited = this.visitedPlaceIds.has(place.id);
      return L.divIcon({
        className: "custom-marker",
        html: `
          <div style="
            background: ${visited ? "#22c55e" : color};
            color: white;
            width: 36px;
            height: 36px;
            border-radius: 50% 50% 50% 0;
            transform: rotate(-45deg);
            border: ${visited ? "2px solid #16a34a" : "2px solid white"};
            box-shadow: 0 2px 6px rgba(0,0,0,0.3);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 11px;
            font-weight: 700;
          ">
            <span style="transform: rotate(45deg);">${visited ? "✓" : rating}</span>
          </div>
        `,
        iconSize: [36, 36],
        iconAnchor: [18, 36],
      });
    },

    // ---------- HEATMAP ----------
    toggleHeatmap() {
      this.showHeatmap = !this.showHeatmap;
      if (this.showHeatmap) {
        this.renderHeatmap();
      } else if (this.heatLayer) {
        this.map.removeLayer(this.heatLayer);
        this.heatLayer = null;
      }
    },

    renderHeatmap() {
      if (this.heatLayer) this.map.removeLayer(this.heatLayer);
      const points = this.places.map((p) => [p.lat, p.lng, p.review_count || 1]);
      if (!points.length) return;
      this.heatLayer = L.heatLayer(points, {
        radius: 35,
        blur: 25,
        maxZoom: 17,
        gradient: { 0.2: "#06a77d", 0.4: "#ffc107", 0.7: "#e85d04", 1.0: "#c1121f" },
      }).addTo(this.map);
    },

    // ---------- UTILS ----------
    focusPlace(placeId) {
      const place = this.places.find((p) => p.id === placeId);
      if (!place) return;
      this.map.setView([place.lat, place.lng], 16, { animate: true });
      const marker = this.markersByPlaceId[placeId];
      if (marker) marker.openTooltip();
    },

    escape(s) {
      if (!s) return "";
      const div = document.createElement("div");
      div.textContent = s;
      return div.innerHTML;
    },

    showToast(msg, type = "info") {
      if (window.toast) window.toast(msg, type);
    },
  };

  window.mapApp = mapApp;
})();
