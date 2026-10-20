/*
 * Date range picker ([data-date-range]) for the search bars and the booking card.
 * Without JS the form shows two native date inputs. With JS, flatpickr shows a single
 * "arrival - departure" field and writes the dates back into those inputs (YYYY-MM-DD),
 * so the server always receives the same fields and keeps validating them.
 *
 * Optional data attributes:
 *   data-min-date / data-max-date   bookable window (YYYY-MM-DD, default min: today)
 *   data-max-nights                 longest stay that can be selected
 *   data-disabled-source            id of a json_script with taken nights [{from, to}]
 *   data-span-error                 message when a range crosses a taken night
 * After a valid change the container fires a bubbling "daterange:change" event.
 */
(function () {
  "use strict";

  if (typeof flatpickr === "undefined") return;

  var lang = document.documentElement.lang || "es";
  var locale = lang === "es" && flatpickr.l10ns.es ? flatpickr.l10ns.es : "default";
  var displayFormat = lang === "es" ? "j M Y" : "M j, Y";
  var DAY = 24 * 60 * 60 * 1000;

  function iso(date) {
    return flatpickr.formatDate(date, "Y-m-d");
  }

  function readDisabled(container) {
    var source = container.dataset.disabledSource && document.getElementById(container.dataset.disabledSource);
    return source ? JSON.parse(source.textContent) : [];
  }

  function crossesTakenNight(start, end, disabled) {
    // Nights of the stay: start ... end - 1 day. ISO strings compare correctly as text.
    var firstNight = iso(start);
    var lastNight = iso(new Date(end.getTime() - DAY));
    return disabled.some(function (range) {
      return range.from <= lastNight && range.to >= firstNight;
    });
  }

  function isTakenNight(day, disabled) {
    var night = iso(day);
    return disabled.some(function (range) {
      return range.from <= night && range.to >= night;
    });
  }

  // Which days cannot be clicked depends on what is being chosen (D33):
  // - arrival: the taken nights;
  // - departure (arrival already picked): days whose stay would include a taken night. The
  //   departure day itself may be the first night of another booking: leaving the morning
  //   someone else arrives is valid (half-open stays, D06).
  function isDayDisabled(day, disabled, arrival) {
    if (arrival && day > arrival) return crossesTakenNight(arrival, day, disabled);
    return isTakenNight(day, disabled);
  }

  document.querySelectorAll("[data-date-range]").forEach(function (container) {
    var inputs = container.querySelectorAll('input[type="date"]');
    if (inputs.length !== 2) return;
    var checkIn = inputs[0];
    var checkOut = inputs[1];
    var disabled = readDisabled(container);
    var maxNights = Number(container.dataset.maxNights) || 0;
    var errorBox = container.querySelector("[data-range-error]");

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

    function showError(message) {
      if (!errorBox) return;
      errorBox.textContent = message || "";
      errorBox.hidden = !message;
    }

    var initial = [checkIn.value, checkOut.value].filter(Boolean);
    var initialDates = initial.map(function (value) {
      return flatpickr.parseDate(value, "Y-m-d");
    });
    var picker;

    function dayDisabled(day) {
      // While flatpickr starts, the dates come from the page (e.g. a search with dates).
      var selected = picker ? picker.selectedDates : initialDates;
      if (selected.length === 1) return isDayDisabled(day, disabled, selected[0]);
      // A chosen departure that is another booking's first night stays selectable.
      if (selected.length === 2 && iso(day) === iso(selected[1])) return false;
      return isTakenNight(day, disabled);
    }

    picker = flatpickr(display, {
      mode: "range",
      locale: locale,
      minDate: container.dataset.minDate || "today",
      maxDate: container.dataset.maxDate || null,
      disable: disabled.length ? [dayDisabled] : [],
      dateFormat: "Y-m-d",
      showMonths: window.matchMedia("(min-width: 768px)").matches ? 2 : 1,
      defaultDate: initial.length === 2 ? initial : null,
      formatDate: function (date) {
        return flatpickr.formatDate(date, displayFormat, flatpickr.l10ns[lang] || flatpickr.l10ns.default);
      },
      onChange: function (dates) {
        showError("");
        // The arrival was picked: recompute which departures are possible.
        if (disabled.length && dates.length < 2) picker.redraw();
        if (dates.length === 2 && crossesTakenNight(dates[0], dates[1], disabled)) {
          showError(container.dataset.spanError);
          picker.clear();
          checkIn.value = "";
          checkOut.value = "";
          return;
        }
        if (dates.length === 2 && maxNights && (dates[1] - dates[0]) / DAY > maxNights) {
          // Clamp to the longest bookable stay (triggers onChange again with the new range).
          picker.setDate([dates[0], new Date(dates[0].getTime() + maxNights * DAY)], true);
          return;
        }
        checkIn.value = dates[0] ? iso(dates[0]) : "";
        checkOut.value = dates[1] ? iso(dates[1]) : "";
        if (dates.length === 2) {
          container.dispatchEvent(new CustomEvent("daterange:change", { bubbles: true }));
        }
      },
    });
  });
})();
