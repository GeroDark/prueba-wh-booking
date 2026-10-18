/*
 * Booking card: refresh the price breakdown from the server whenever dates or guests change.
 * The server (GET .../quote/) is the only place where prices and availability are computed;
 * this script just displays the answer, inserting text with textContent (never HTML).
 */
(function () {
  "use strict";

  var form = document.querySelector("[data-booking-form]");
  if (!form) return;

  var quoteBox = form.querySelector("[data-quote]");
  var guests = form.querySelector('input[name="guests"]');
  var lastRequest = 0;

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function row(label, amount, modifier) {
    var wrapper = el("div", "price-lines__row" + (modifier ? " price-lines__row--" + modifier : ""));
    wrapper.appendChild(el("dt", null, label));
    wrapper.appendChild(el("dd", null, amount));
    return wrapper;
  }

  function render(data) {
    quoteBox.replaceChildren();
    if (!data.ok) {
      var alert = el("div", "booking-form__alert");
      alert.setAttribute("role", "alert");
      data.errors.forEach(function (message) { alert.appendChild(el("p", null, message)); });
      quoteBox.appendChild(alert);
      return;
    }
    var list = el("dl", "price-lines");
    data.lines.forEach(function (line) { list.appendChild(row(line.label, line.amount)); });
    list.appendChild(row(quoteBox.dataset.totalLabel || "Total", data.total, "total"));
    quoteBox.appendChild(list);
  }

  function refresh() {
    var checkIn = form.querySelector('input[name="check_in"]').value;
    var checkOut = form.querySelector('input[name="check_out"]').value;
    if (!checkIn || !checkOut) {
      quoteBox.replaceChildren();
      return;
    }
    var params = new URLSearchParams({ check_in: checkIn, check_out: checkOut, guests: guests.value || 1 });
    var requestId = ++lastRequest;
    quoteBox.setAttribute("aria-busy", "true");
    fetch(form.dataset.quoteUrl + "?" + params.toString(), { headers: { Accept: "application/json" } })
      .then(function (response) { return response.json(); })
      .then(function (data) {
        if (requestId === lastRequest) render(data); // ignore answers to older requests
      })
      .catch(function () { /* the server validates again on submit */ })
      .finally(function () { quoteBox.removeAttribute("aria-busy"); });
  }

  form.addEventListener("daterange:change", refresh);
  guests.addEventListener("change", refresh);
})();
