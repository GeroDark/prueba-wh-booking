/*
 * Live feedback for forms with [data-validate] (sign up, sign in, checkout).
 *
 * - An error disappears as soon as the field is edited, so a message such as "Enter your email
 *   address" never stays next to a field that already has a value.
 * - A field is checked when the visitor leaves it, and every field on submit (the form is not
 *   sent while something is wrong, which also keeps the typed password).
 * - The messages come from the server form (data-error-*), so they read the same in both
 *   languages. This is only a convenience: the server validates everything again (D35).
 */
(function () {
  "use strict";

  var FIELDS = "input:not([type=hidden]):not([type=checkbox]):not([type=radio]), select, textarea";

  function messageFor(input) {
    var validity = input.validity;
    if (validity.valueMissing) return input.dataset.errorRequired || input.validationMessage;
    if (validity.typeMismatch || validity.patternMismatch) {
      return input.dataset.errorInvalid || input.validationMessage;
    }
    if (validity.rangeUnderflow) return input.dataset.errorMin || input.validationMessage;
    if (validity.rangeOverflow) return input.dataset.errorMax || input.validationMessage;
    if (validity.badInput) return input.dataset.errorInvalid || input.validationMessage;
    if (validity.customError) return input.validationMessage;
    return "";
  }

  function errorId(input) {
    return input.id + "-error";
  }

  function describedBy(input) {
    return (input.getAttribute("aria-describedby") || "").split(" ").filter(Boolean);
  }

  function clearError(input) {
    var wrapper = input.closest(".form-field");
    if (!wrapper || !wrapper.classList.contains("has-error")) return;
    wrapper.classList.remove("has-error");
    input.removeAttribute("aria-invalid");
    var box = document.getElementById(errorId(input));
    if (box) box.remove();
    var ids = describedBy(input).filter(function (id) {
      return id !== errorId(input);
    });
    if (ids.length) input.setAttribute("aria-describedby", ids.join(" "));
    else input.removeAttribute("aria-describedby");
  }

  function showError(input, message) {
    var wrapper = input.closest(".form-field");
    if (!wrapper) return;
    clearError(input);
    var box = document.createElement("div");
    box.className = "form-field__errors";
    box.id = errorId(input);
    var paragraph = document.createElement("p");
    paragraph.textContent = message;
    box.appendChild(paragraph);
    wrapper.appendChild(box);
    wrapper.classList.add("has-error");
    input.setAttribute("aria-invalid", "true");
    input.setAttribute("aria-describedby", describedBy(input).concat(box.id).join(" "));
  }

  function check(input) {
    var message = messageFor(input);
    if (message) showError(input, message);
    else clearError(input);
    return !message;
  }

  document.querySelectorAll("form[data-validate]").forEach(function (form) {
    form.addEventListener("input", function (event) {
      if (event.target.matches(FIELDS)) clearError(event.target);
    });

    form.addEventListener("focusout", function (event) {
      var input = event.target;
      var wrapper = input.closest(".form-field");
      // Leaving an empty field just after the page loads is not an error yet, and moving to a
      // control of the same field (the "show password" button) is not leaving it.
      if (!input.matches(FIELDS) || input.value === "") return;
      if (wrapper && event.relatedTarget && wrapper.contains(event.relatedTarget)) return;
      check(input);
    });

    form.addEventListener("submit", function (event) {
      var invalid = Array.prototype.filter.call(form.querySelectorAll(FIELDS), function (input) {
        return !check(input);
      });
      if (invalid.length) {
        event.preventDefault();
        invalid[0].focus();
      }
    });
  });
})();
