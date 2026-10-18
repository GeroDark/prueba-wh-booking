/*
 * Countdown of the hold on the checkout page. Purely informative: the server checks the
 * expiry again before charging. At zero the page reloads and the server explains what happened.
 */
(function () {
  "use strict";

  var timer = document.querySelector("[data-hold-timer]");
  if (!timer) return;

  var output = timer.querySelector("[data-hold-timer-value]");
  var expiresAt = new Date(timer.dataset.expiresAt).getTime();

  function pad(value) {
    return String(value).padStart(2, "0");
  }

  function tick() {
    var remaining = Math.max(0, Math.round((expiresAt - Date.now()) / 1000));
    output.textContent = pad(Math.floor(remaining / 60)) + ":" + pad(remaining % 60);
    timer.classList.toggle("is-ending", remaining <= 60);
    if (remaining === 0) {
      window.location.reload();
      return;
    }
    window.setTimeout(tick, 1000);
  }

  tick();
})();
