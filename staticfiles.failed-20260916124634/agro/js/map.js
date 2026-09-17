/**
 * E-Shelle Agro — Carte Leaflet pour la localisation des acteurs
 * Nécessite : <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css">
 *             <script src="https://unpkg.com/leaflet/dist/leaflet.js">
 */

(function() {
  'use strict';

  /**
   * Initialise une carte Leaflet dans #mapContainer
   * @param {number} lat  - Latitude du marqueur central
   * @param {number} lng  - Longitude du marqueur central
   * @param {string} nom  - Nom pour le popup
   */
  window.initAgroMap = function(lat, lng, nom) {
    const container = document.getElementById('mapContainer');
    if (!container || typeof L === 'undefined') return;

    const map = L.map('mapContainer').setView([lat, lng], 10);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 18,
    }).addTo(map);

    // Marqueur personnalisé vert
    const icon = L.divIcon({
      html: '<div style="background:#2D6A4F;width:28px;height:28px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);border:3px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.3)"></div>',
      iconSize:   [28, 28],
      iconAnchor: [14, 28],
      className:  'agro-map-marker',
    });

    L.marker([lat, lng], { icon })
      .addTo(map)
      .bindPopup('<strong>' + escHtml(nom) + '</strong>')
      .openPopup();
  };

  /**
   * Affiche plusieurs acteurs sur une carte
   * @param {Array} acteurs - [{lat, lng, nom, slug, type}]
   */
  window.initAgroMapActeurs = function(acteurs) {
    const container = document.getElementById('mapActeurs');
    if (!container || typeof L === 'undefined' || !acteurs.length) return;

    const map = L.map('mapActeurs').setView([5, 15], 4);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 18,
    }).addTo(map);

    acteurs.forEach(function(a) {
      if (!a.lat || !a.lng) return;
      L.circleMarker([a.lat, a.lng], {
        radius:      8,
        fillColor:   '#2D6A4F',
        fillOpacity: 0.85,
        color:       '#fff',
        weight:      2,
      })
      .addTo(map)
      .bindPopup(
        '<strong><a href="/agro/profil/' + escAttr(a.slug) + '/">' + escHtml(a.nom) + '</a></strong><br>'
        + '<small class="text-muted">' + escHtml(a.type) + '</small>'
      );
    });
  };

  function escHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
  function escAttr(str) {
    if (!str) return '';
    return String(str).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

})();
