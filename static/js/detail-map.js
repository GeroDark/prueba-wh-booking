/*
 * Map of one property.
 * - Property page: a ~300 m circle over the approximate area. The exact point is not in the
 *   page; it is shown only after the booking is paid (D27).
 * - Confirmation page ([data-exact]): a pin on the exact point.
 */
(function () {
  "use strict";

  var canvas = document.getElementById("property-map");
  if (!canvas || typeof L === "undefined") return;

  var center = [Number(canvas.dataset.lat), Number(canvas.dataset.lng)];
  // The map sits inside the page, so a plain scroll must keep scrolling the page.
  // Gesture handling (as in embedded Google Maps): Ctrl/⌘ + wheel zooms, drag moves,
  // two fingers move it on touch screens, and a hint explains it when needed.
  var options = { scrollWheelZoom: false };
  // The plugin registers itself as a map handler (it adds `gestureHandlingOptions` to the defaults).
  if ("gestureHandlingOptions" in L.Map.prototype.options) {
    options = {
      gestureHandling: true,
      gestureHandlingOptions: {
        duration: 1500,
        text: {
          touch: canvas.dataset.hintTouch,
          scroll: canvas.dataset.hintScroll,
          scrollMac: canvas.dataset.hintScrollMac,
        },
      },
    };
  }
  var exact = "exact" in canvas.dataset;
  var map = L.map(canvas, options).setView(center, exact ? 16 : 15);

  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);

  if (exact) {
    L.circleMarker(center, {
      radius: 9,
      color: "#ffffff",
      weight: 3,
      fillColor: "#232324",
      fillOpacity: 1,
    }).addTo(map);
    return;
  }

  L.circle(center, {
    radius: 300,
    color: "#232324",
    weight: 1.5,
    fillColor: "#232324",
    fillOpacity: 0.15,
  }).addTo(map);
})();
