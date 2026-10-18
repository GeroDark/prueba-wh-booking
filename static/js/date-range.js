/*
 * Date range picker for search bars ([data-date-range]).
 * Without JS the form shows two native date inputs. With JS, flatpickr shows a single
 * "arrival - departure" field and writes the dates back into those inputs (YYYY-MM-DD),
 * so the server always receives the same fields.
 */
(function () {
  "use strict";

  if (typeof flatpickr === "undefined") return;

  var lang = document.documentElement.lang || "es";
  var locale = lang === "es" && flatpickr.l10ns.es ? flatpickr.l10ns.es : "default";
  var displayFormat = lang === "es" ? "j M Y" : "M j, Y";

  document.querySelectorAll("[data-date-range]").forEach(function (container) {
    var inputs = container.querySelectorAll('input[type="date"]');
    if (inputs.length !== 2) return;
    var checkIn = inputs[0];
    var checkOut = inputs[1];

    var display = document.createElement("input");
    display.type = "text";
    display.readOnly = true;
    display.className = checkIn.className + " search-bar__range";
    display.placeholder = container.dataset.placeholder || "";
    // The visible field takes over the id, so the existing <label for> keeps pointing at it.
    display.id = checkIn.id;

    checkIn.removeAttribute("id");
    checkIn.type = "hidden";
    checkOut.type = "hidden";
    container.querySelector(".search-bar__dates").prepend(display);
    container.classList.add("is-enhanced");

    var initial = [checkIn.value, checkOut.value].filter(Boolean);

    flatpickr(display, {
      mode: "range",
      locale: locale,
      minDate: "today",
      dateFormat: "Y-m-d",
      showMonths: window.matchMedia("(min-width: 768px)").matches ? 2 : 1,
      defaultDate: initial.length === 2 ? initial : null,
      formatDate: function (date) {
        return flatpickr.formatDate(date, displayFormat, flatpickr.l10ns[lang] || flatpickr.l10ns.default);
      },
      onChange: function (dates) {
        checkIn.value = dates[0] ? flatpickr.formatDate(dates[0], "Y-m-d") : "";
        checkOut.value = dates[1] ? flatpickr.formatDate(dates[1], "Y-m-d") : "";
      },
    });
  });
})();
