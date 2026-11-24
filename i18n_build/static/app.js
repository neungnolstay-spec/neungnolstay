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

  /* Floor plan lightbox: full plan on screen, or 1:1 with scroll */
  var planOpen = document.querySelector("[data-plan-open]");
  var lb = document.getElementById("plan-lightbox");
  if (planOpen && lb) {
    var stage = lb.querySelector("[data-plan-stage]");
    var zoomBtn = lb.querySelector("[data-plan-zoom]");
    var closeBtn = lb.querySelector("[data-plan-close]");
    var labelActual = (zoomBtn && zoomBtn.getAttribute("data-label-actual")) || "";
    var labelFit = (zoomBtn && zoomBtn.getAttribute("data-label-fit")) || labelActual;
    var lastFocus = null;

    var setActual = function (on) {
      if (on) {
        var img = stage.querySelector("img");
        if (img) {
          /* one image pixel per device pixel, so labels stay crisp without pointless upscaling */
          var dpr = window.devicePixelRatio || 1;
          var w = img.naturalWidth || parseInt(img.getAttribute("width"), 10) || 0;
          if (w) stage.style.setProperty("--plan-w", Math.round(w / dpr) + "px");
        }
      }
      stage.classList.toggle("is-actual", on);
      if (zoomBtn) {
        zoomBtn.setAttribute("aria-pressed", on ? "true" : "false");
        zoomBtn.textContent = on ? labelFit : labelActual;
      }
    };
    var centreOnPlan = function () {
      var img = stage.querySelector("img");
      if (!img) return;
      var ir = img.getBoundingClientRect();
      if (!ir.width) return;
      stage.scrollLeft = Math.max(0, (ir.width - stage.clientWidth) / 2);
      stage.scrollTop = Math.max(0, ir.height * 0.62 - stage.clientHeight / 2);
    };
    var open = function (ev) {
      ev.preventDefault();
      lastFocus = document.activeElement;
      lb.hidden = false;
      document.documentElement.classList.add("plan-open");
      /* narrow screens: open already zoomed in, since a plan fitted to a phone is unreadable */
      var narrow = window.innerWidth < 720;
      setActual(narrow);
      if (narrow) {
        window.requestAnimationFrame(centreOnPlan);
        var lbImg = stage.querySelector("img");
        if (lbImg && !lbImg.complete) {
          lbImg.addEventListener("load", function () {
            if (narrow && stage.classList.contains("is-actual")) window.requestAnimationFrame(centreOnPlan);
          });
        }
      }
      if (closeBtn) closeBtn.focus();
      track("floor_plan_zoom", { room: room });
    };
    var close = function () {
      lb.hidden = true;
      document.documentElement.classList.remove("plan-open");
      if (lastFocus && lastFocus.focus) lastFocus.focus();
    };

    planOpen.addEventListener("click", open);
    if (closeBtn) closeBtn.addEventListener("click", close);
    if (zoomBtn) zoomBtn.addEventListener("click", function () {
      setActual(!stage.classList.contains("is-actual"));
    });
    lb.addEventListener("click", function (ev) {
      if (ev.target === lb || ev.target === stage) close();
    });
    document.addEventListener("keydown", function (ev) {
      if (lb.hidden) return;
      if (ev.key === "Escape") close();
    });
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
