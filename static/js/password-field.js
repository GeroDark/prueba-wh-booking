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

    // Lowercase, uppercase, digits, other symbols: "contraseña123" only uses two kinds.
    function characterKinds(password) {
      return [/\p{Ll}/u, /\p{Lu}/u, /\d/, /[^\p{L}\d]/u].filter(function (kind) {
        return kind.test(password);
      }).length;
    }

    function evaluate() {
      var value = input.value;
      var results = {
        length: value.length >= 8,
        // Anything that is not a letter, as in the server's [\d\W_]: ñ and é are letters there.
        "number-or-symbol": /[^\p{L}\p{M}]/u.test(value),
        personal: value.length > 0 && !containsPersonalData(value),
      };
      var passed = 0;
      Object.keys(results).forEach(function (rule) {
        var item = wrapper.querySelector('[data-rule="' + rule + '"]');
        item.classList.toggle("is-valid", results[rule]);
        if (results[rule]) passed += 1;
      });
      var allRules = passed === Object.keys(results).length;
      var level = !allRules ? "weak" : value.length >= 12 && characterKinds(value) >= 3 ? "strong" : "medium";
      strength.textContent = strength.dataset["label" + level.charAt(0).toUpperCase() + level.slice(1)];
      strength.dataset.level = level;
      wrapper.classList.toggle("is-touched", value.length > 0);
      // Read by form-feedback.js: the form is not sent while a rule of the checklist fails.
      input.setCustomValidity(value && !allRules ? wrapper.dataset.rulesMessage : "");
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
