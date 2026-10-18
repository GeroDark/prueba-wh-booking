/*
 * Checkout helpers. Comfort only: without JavaScript every field still works and the server
 * validates everything (D35).
 * - The phone code follows the nationality until the guest picks a code themselves.
 * - Card number in groups of four with the brand shown while typing; expiry as MM/YY.
 * - The test cards of the simulated gateway fill the form with one click.
 * - Demo only: a number that is not a test card is stopped here, so a real card number never
 *   leaves the browser. Without JavaScript the server refuses it and stores nothing (D11).
 */
(function () {
  "use strict";

  var form = document.querySelector("[data-checkout-form]");
  if (!form) return;

  function setValue(input, value) {
    input.value = value;
    input.dispatchEvent(new Event("input", { bubbles: true })); // clears stale errors
  }

  // Phone code follows the nationality

  var nationality = form.querySelector('[name="nationality"]');
  var phoneRegion = form.querySelector('[name="phone_region"]');
  if (nationality && phoneRegion) {
    var regionChosen = phoneRegion.value !== "" && phoneRegion.value !== nationality.value;
    phoneRegion.addEventListener("change", function () {
      regionChosen = true;
    });
    nationality.addEventListener("change", function () {
      var option = phoneRegion.querySelector('option[value="' + nationality.value + '"]');
      if (!regionChosen && option) setValue(phoneRegion, nationality.value);
    });
  }

  // Card number and expiry

  var number = form.querySelector('[name="card_number"]');
  var expiry = form.querySelector('[name="expiry"]');
  var cvc = form.querySelector('[name="cvc"]');
  var brandLabel = form.querySelector("[data-card-brand]");
  if (!number) return;

  // Same ranges as apps/payments/cards.py; the server decides.
  function brandOf(digits) {
    if (/^3[47]/.test(digits)) return "amex";
    if (/^4/.test(digits)) return "visa";
    var two = Number(digits.slice(0, 2));
    var six = Number((digits + "000000").slice(0, 6));
    if ((two >= 51 && two <= 55) || (six >= 222100 && six <= 272099)) return "mastercard";
    return "";
  }

  var BRAND_NAMES = { visa: "Visa", mastercard: "Mastercard", amex: "Amex" };

  var testCards = Array.prototype.map.call(form.querySelectorAll("[data-test-card]"), function (button) {
    return button.dataset.testCard.replace(/\D/g, "");
  });
  var demoNotice = form.querySelector("[data-demo-message]");

  // Read by form-feedback.js: an invalid field blocks the submit and shows this message.
  function guardDemo(digits) {
    if (!demoNotice) return;
    // While typing, the start of a test card ("4242 4242") is not flagged yet.
    var realCard =
      digits.length >= 12 &&
      !testCards.some(function (card) {
        return card.indexOf(digits) === 0;
      });
    number.setCustomValidity(realCard ? demoNotice.dataset.demoMessage : "");
  }

  function groups(digits, brand) {
    // American Express prints 4-6-5; the others, groups of four.
    var sizes = brand === "amex" ? [4, 6, 5] : [4, 4, 4, 4, 3];
    var parts = [];
    var position = 0;
    sizes.forEach(function (size) {
      if (position < digits.length) parts.push(digits.slice(position, position + size));
      position += size;
    });
    return parts.join(" ");
  }

  function formatNumber() {
    var digits = number.value.replace(/\D/g, "").slice(0, 19);
    var brand = brandOf(digits);
    brandLabel.textContent = BRAND_NAMES[brand] || "";
    guardDemo(digits);
    // Only reformat while typing at the end, so editing in the middle keeps the caret in place.
    if (number.selectionStart === number.value.length) number.value = groups(digits, brand);
  }

  number.addEventListener("input", formatNumber);
  formatNumber();

  if (expiry) {
    expiry.addEventListener("input", function (event) {
      if (event.inputType === "deleteContentBackward") return;
      var digits = expiry.value.replace(/\D/g, "").slice(0, 4);
      if (expiry.selectionStart === expiry.value.length) {
        expiry.value = digits.length > 2 ? digits.slice(0, 2) + "/" + digits.slice(2) : digits;
      }
    });
  }

  form.querySelectorAll("[data-test-card]").forEach(function (button) {
    button.addEventListener("click", function () {
      var digits = button.dataset.testCard.replace(/\D/g, "");
      var nextYear = String((new Date().getFullYear() + 2) % 100).padStart(2, "0");
      setValue(number, digits);
      formatNumber();
      if (expiry) setValue(expiry, "12/" + nextYear);
      if (cvc) setValue(cvc, brandOf(digits) === "amex" ? "1234" : "123");
      number.focus();
    });
  });
})();
