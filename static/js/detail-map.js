/*
 * "Location" map of the property page: a ~300 m circle over the approximate area.
 * The exact point is not in the page; it is shown only after the booking is paid (D27).
 */
(function () {
  "use strict";

  var canvas = document.getElementById("property-map");
  if (!canvas || typeof L === "undefined") return;

  var center = [Number(canvas.dataset.lat), Number(canvas.dataset.lng)];
  // Page scroll must not zoom the map; zoom stays available with the buttons.
  var map = L.map(canvas, { scrollWheelZoom: false }).setView(center, 15);

  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);

  L.circle(center, {
    radius: 300,
    color: "#232324",
    weight: 1.5,
    fillColor: "#232324",
    fillOpacity: 0.15,
  }).addTo(map);
})();
