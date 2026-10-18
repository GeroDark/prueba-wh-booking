/*
 * Dependent district select: after choosing a city, only its districts are offered.
 * Without JS the select lists every district grouped by city, and the server validates
 * that the district belongs to the city.
 */
(function () {
  "use strict";

  var dataElement = document.getElementById("districts-by-city");
  if (!dataElement) return;
  var districtsByCity = JSON.parse(dataElement.textContent);

  document.querySelectorAll("form").forEach(function (form) {
    var city = form.querySelector("[data-city-select]");
    var district = form.querySelector("[data-district-select]");
    if (!city || !district) return;

    var allOptions = district.innerHTML;
    var emptyLabel = district.options[0] ? district.options[0].textContent : "";

    function refresh() {
      var selected = district.value;
      var districts = districtsByCity[city.value];
      if (!districts) {
        district.innerHTML = allOptions;
      } else {
        district.innerHTML = "";
        district.add(new Option(emptyLabel, ""));
        districts.forEach(function (item) {
          district.add(new Option(item.name, item.id));
        });
      }
      district.value = Array.prototype.some.call(district.options, function (option) {
        return option.value === selected;
      })
        ? selected
        : "";
    }

    city.addEventListener("change", refresh);
    refresh();
  });
})();
