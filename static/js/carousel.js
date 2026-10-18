/*
 * Horizontal carousels ([data-carousel]): the track scrolls natively (touch, trackpad,
 * keyboard) with CSS scroll-snap; the arrow buttons scroll it by roughly one screen.
 */
(function () {
  "use strict";

  document.querySelectorAll("[data-carousel]").forEach(function (carousel) {
    var track = carousel.querySelector("[data-carousel-track]");
    var prev = carousel.querySelector("[data-carousel-prev]");
    var next = carousel.querySelector("[data-carousel-next]");
    if (!track || !prev || !next) return;

    function step() {
      return Math.max(track.clientWidth * 0.8, 200);
    }

    function update() {
      var maxScroll = track.scrollWidth - track.clientWidth - 2;
      prev.disabled = track.scrollLeft <= 2;
      next.disabled = track.scrollLeft >= maxScroll;
      carousel.classList.toggle("is-static", maxScroll <= 0);
    }

    prev.addEventListener("click", function () {
      track.scrollBy({ left: -step(), behavior: "smooth" });
    });
    next.addEventListener("click", function () {
      track.scrollBy({ left: step(), behavior: "smooth" });
    });
    track.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    update();
  });
})();
