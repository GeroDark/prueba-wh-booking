/*
 * Forms with a [data-submit-once] button cannot be sent twice by a double click.
 * First layer of protection only: the server is idempotent as well (see D11).
 */
(function () {
  "use strict";

  document.addEventListener("submit", function (event) {
    var button = event.target.querySelector("[data-submit-once]");
    if (!button) return;
    if (button.dataset.submitting) {
      event.preventDefault();
      return;
    }
    button.dataset.submitting = "true";
    button.setAttribute("aria-disabled", "true");
    button.classList.add("is-loading");
  });
})();
