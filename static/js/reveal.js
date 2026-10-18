/*
 * Fade-in on scroll for [data-reveal] elements. The hidden state only applies when JS runs
 * (html.js) and the visitor has not asked for reduced motion, so content is never lost.
 */
(function () {
  "use strict";

  var elements = document.querySelectorAll("[data-reveal]");
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (reduceMotion || !("IntersectionObserver" in window)) {
    elements.forEach(function (element) {
      element.classList.add("is-visible");
    });
    return;
  }

  var observer = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { rootMargin: "0px 0px -10% 0px" }
  );

  elements.forEach(function (element) {
    observer.observe(element);
  });
})();
