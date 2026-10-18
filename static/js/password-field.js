/*
 * New-password fields ([data-password-field]): show/hide button and the live checklist of the
 * design. The rules mirror the server validators (length, number or symbol, no personal data);
 * the server always validates again and also rejects common passwords.
 */
(function () {
  "use strict";

  document.querySelectorAll("[data-password-field]").forEach(function (wrapper) {
    var input = wrapper.querySelector('input[type="password"]');
    var form = wrapper.closest("form");
    var toggle = wrapper.querySelector("[data-password-toggle]");
    var strength = wrapper.querySelector("[data-strength]");
    if (!input || !form) return;

    function fieldValue(name) {
      var field = form.querySelector('[name="' + name + '"]');
      return field ? field.value.toLowerCase() : "";
    }

    function containsPersonalData(password) {
      var pieces = [fieldValue(wrapper.dataset.emailField).split("@")[0]].concat(
        fieldValue(wrapper.dataset.nameField).split(/[\s.\-_]+/)
      );
      var lowered = password.toLowerCase();
      return pieces.some(function (piece) {
        return piece.length >= 3 && lowered.indexOf(piece) !== -1;
      });
    }

    function evaluate() {
      var value = input.value;
      var results = {
        length: value.length >= 8,
        "number-or-symbol": /[\d\W_]/.test(value),
        personal: value.length > 0 && !containsPersonalData(value),
      };
      var passed = 0;
      Object.keys(results).forEach(function (rule) {
        var item = wrapper.querySelector('[data-rule="' + rule + '"]');
        item.classList.toggle("is-valid", results[rule]);
        if (results[rule]) passed += 1;
      });
      var level = passed === 3 && value.length >= 12 ? "strong" : passed === 3 ? "medium" : "weak";
      strength.textContent = strength.dataset["label" + level.charAt(0).toUpperCase() + level.slice(1)];
      strength.dataset.level = level;
      wrapper.classList.toggle("is-touched", value.length > 0);
    }

    ["input", "change"].forEach(function (name) {
      input.addEventListener(name, evaluate);
    });
    form.addEventListener("input", function (event) {
      if (event.target !== input) evaluate(); // e-mail or name changed
    });
    evaluate();

    if (toggle) {
      toggle.addEventListener("click", function () {
        var show = input.type === "password";
        input.type = show ? "text" : "password";
        toggle.setAttribute("aria-pressed", String(show));
        toggle.querySelector("[data-icon-show]").hidden = show;
        toggle.querySelector("[data-icon-hide]").hidden = !show;
        toggle.querySelector("[data-toggle-label]").textContent = show
          ? toggle.dataset.labelHide
          : toggle.dataset.labelShow;
      });
    }
  });
})();
