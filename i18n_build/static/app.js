/* NUNG NOL STAY — shared behaviour for the static multilingual site.
   Analytics events fire through gtag() when a GA4 property is configured
   (see GA4_MEASUREMENT_ID in i18n_build/build.py). Keep this file dependency-free. */
(function () {
  "use strict";
  var cfg = window.SITE_CONFIG || {};
  var page = cfg.page || "home";
  var lang = cfg.lang || "ko";
  var room = cfg.room || "";

  function track(name, params) {
    var payload = Object.assign({ page_language: lang, page_type: page }, params || {});
    try {
      if (typeof window.gtag === "function") {
        window.gtag("event", name, payload);
      } else if (window.dataLayer) {
        window.dataLayer.push(Object.assign({ event: name }, payload));
      }
    } catch (e) {
      /* analytics must never break the page */
    }
  }

  /* Every Airbnb button is an external booking jump. */
  document.addEventListener("click", function (ev) {
    var el = ev.target.closest ? ev.target.closest("[data-airbnb]") : null;
    if (!el) return;
    var which = el.getAttribute("data-airbnb");
    track(which === "orot" ? "orot_airbnb_click" : "heyum_airbnb_click", {
      room: which,
      link_url: el.getAttribute("href"),
      link_text: (el.textContent || "").trim().slice(0, 60),
      placement: el.getAttribute("data-placement") || "unknown"
    });
  }, false);

  /* Language switcher */
  document.querySelectorAll("[data-lang-switch]").forEach(function (a) {
    a.addEventListener("click", function () {
      track("language_switch", {
        from_language: lang,
        to_language: a.getAttribute("data-lang-switch"),
        target_url: a.getAttribute("href")
      });
    });
  });

  /* Room detail view */
  if (page === "room" && room) {
    var seen = false;
    var fire = function () {
      if (seen) return;
      seen = true;
      track("room_detail_view", { room: room });
    };
    if ("IntersectionObserver" in window) {
      var marker = document.querySelector("[data-room-view-marker]");
      if (marker) {
        new IntersectionObserver(function (entries, obs) {
          entries.forEach(function (en) {
            if (en.isIntersecting) {
              fire();
              obs.disconnect();
            }
          });
        }, { threshold: 0.25 }).observe(marker);
      } else {
        fire();
      }
    } else {
      fire();
    }
  }

  /* Soft reveal of sections */
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduced) document.documentElement.classList.remove("js");
  var items = document.querySelectorAll(".reveal");
  if (reduced || !("IntersectionObserver" in window)) {
    items.forEach(function (el) { el.classList.add("in"); });
  } else {
    var io = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (en) {
        if (en.isIntersecting) {
          en.target.classList.add("in");
          obs.unobserve(en.target);
        }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
    items.forEach(function (el) { io.observe(el); });
  }
})();
