/*
 * Results map (Airbnb style): one price pin per property on the current page.
 * - Hovering or focusing a card highlights its pin, and vice versa.
 * - Clicking a pin opens a mini card linking to the property.
 * - On small screens a floating button switches between the list and the map.
 * Pin data comes from the server (json_script); text is inserted with textContent, never as HTML.
 */
(function () {
  "use strict";

  var canvas = document.getElementById("results-map");
  var dataElement = document.getElementById("map-markers");
  if (!canvas || !dataElement || typeof L === "undefined") return;

  var markersData = JSON.parse(dataElement.textContent);
  var map = L.map(canvas, { zoomControl: true, scrollWheelZoom: true });

  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);

  var markers = {};
  var points = [];

  function element(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  }

  function popupContent(item) {
    var link = element("a", "map-card");
    link.href = item.url;
    if (item.image) {
      var image = element("img", "map-card__image");
      image.src = item.image;
      image.alt = "";
      link.appendChild(image);
    }
    var body = element("span", "map-card__body");
    body.appendChild(element("strong", "map-card__title", item.title));
    body.appendChild(element("span", "map-card__location", item.location));
    body.appendChild(element("span", "map-card__price", item.price));
    link.appendChild(body);
    return link;
  }

  function pinIcon(item) {
    var pin = element("span", "price-pin", item.price);
    return L.divIcon({ className: "price-pin-wrapper", html: pin.outerHTML, iconSize: null });
  }

  // Nearby pins merge into a cluster showing how many properties it holds; a click zooms in.
  var cluster = L.markerClusterGroup({
    showCoverageOnHover: false,
    maxClusterRadius: 48,
    disableClusteringAtZoom: 16, // street level: always show individual prices
    iconCreateFunction: function (group) {
      var count = element("span", "cluster-pin", String(group.getChildCount()));
      return L.divIcon({ className: "cluster-pin-wrapper", html: count.outerHTML, iconSize: null });
    },
  });
  map.addLayer(cluster);

  function setActive(id, active) {
    var marker = markers[id];
    if (!marker) return;
    // If the pin is inside a cluster, highlight the cluster instead.
    var visible = cluster.getVisibleParent(marker) || marker;
    var node = visible.getElement && visible.getElement();
    if (!node) return;
    node.classList.toggle("is-active", active);
    if (visible.setZIndexOffset) visible.setZIndexOffset(active ? 1000 : 0);
  }

  markersData.forEach(function (item) {
    var marker = L.marker([item.lat, item.lng], {
      icon: pinIcon(item),
      title: item.title,
      keyboard: true,
      riseOnHover: true,
    });
    cluster.addLayer(marker);
    marker.bindPopup(popupContent(item), { closeButton: false, className: "map-card-popup", offset: [0, -6] });
    marker.on("mouseover", function () { setActive(item.id, true); });
    marker.on("mouseout", function () { setActive(item.id, false); });
    markers[item.id] = marker;
    points.push([item.lat, item.lng]);
  });

  function fit() {
    if (points.length === 1) {
      map.setView(points[0], 14);
    } else if (points.length > 1) {
      map.fitBounds(cluster.getBounds(), { padding: [48, 48], maxZoom: 14 });
    } else {
      map.setView([15, -45], 2); // No results: show the Americas and Spain.
    }
  }
  fit();

  document.querySelectorAll("[data-property-id]").forEach(function (card) {
    var id = Number(card.dataset.propertyId);
    ["mouseenter", "focusin"].forEach(function (name) {
      card.addEventListener(name, function () { setActive(id, true); });
    });
    ["mouseleave", "focusout"].forEach(function (name) {
      card.addEventListener(name, function () { setActive(id, false); });
    });
  });

  var toggle = document.querySelector("[data-map-toggle]");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var showing = document.body.classList.toggle("is-map-open");
      toggle.setAttribute("aria-pressed", String(showing));
      toggle.querySelector("span").textContent = showing ? toggle.dataset.labelList : toggle.dataset.labelMap;
      // Leaflet must measure the container again once it becomes visible.
      setTimeout(function () {
        map.invalidateSize();
        fit();
      }, 50);
    });
  }
})();
