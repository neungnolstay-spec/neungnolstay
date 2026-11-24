/* NEUNGNOL STAY — room photo gallery: category filter + full-screen lightbox.
   Dependency-free. Data comes from <script type="application/json" data-gal-data>. */
(function () {
  "use strict";
  var dataEl = document.querySelector("[data-gal-data]");
  var lb = document.getElementById("gallery-lightbox");
  if (!dataEl || !lb) return;

  var items = [];
  try {
    items = JSON.parse(dataEl.textContent || "[]");
  } catch (e) {
    items = [];
  }
  if (!items.length) return;

  /* ---------- category filter ---------- */
  var grid = document.querySelector("[data-gal-grid]");
  var chips = Array.prototype.slice.call(document.querySelectorAll("[data-gal-filter]"));
  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      var cat = chip.getAttribute("data-gal-filter");
      chips.forEach(function (c) {
        var on = c === chip;
        c.classList.toggle("is-on", on);
        c.setAttribute("aria-pressed", on ? "true" : "false");
      });
      if (!grid) return;
      Array.prototype.slice.call(grid.children).forEach(function (li) {
        var show = cat === "all" || li.getAttribute("data-cat") === cat;
        li.hidden = !show;
      });
    });
  });

  /* ---------- lightbox ---------- */
  var imgEl = lb.querySelector("[data-gal-img]");
  var capEl = lb.querySelector("[data-gal-cap]");
  var countEl = lb.querySelector("[data-gal-count]");
  var prevBtn = lb.querySelector("[data-gal-prev]");
  var nextBtn = lb.querySelector("[data-gal-next]");
  var closeBtn = lb.querySelector("[data-gal-close]");
  var index = 0;
  var lastFocus = null;

  function preload(i) {
    if (i < 0 || i >= items.length) return;
    var im = new Image();
    im.src = items[i].full;
  }

  function show(i) {
    index = Math.max(0, Math.min(items.length - 1, i));
    var it = items[index];
    imgEl.src = it.full;
    imgEl.alt = it.cap;
    if (it.w && it.h) {
      imgEl.setAttribute("width", it.w);
      imgEl.setAttribute("height", it.h);
    }
    capEl.textContent = it.cap;
    countEl.textContent = (index + 1) + " / " + items.length;
    preload(index + 1);
    preload(index - 1);
  }

  function open(i) {
    lastFocus = document.activeElement;
    lb.hidden = false;
    document.documentElement.classList.add("gal-open");
    show(i);
    if (closeBtn) closeBtn.focus();
  }

  function close() {
    lb.hidden = true;
    document.documentElement.classList.remove("gal-open");
    imgEl.removeAttribute("src");
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  document.addEventListener("click", function (ev) {
    var opener = ev.target.closest ? ev.target.closest("[data-gal-open]") : null;
    if (!opener) return;
    ev.preventDefault();
    var n = parseInt(opener.getAttribute("data-gal-open"), 10);
    open(isNaN(n) ? 0 : n);
  });

  if (prevBtn) prevBtn.addEventListener("click", function () { show(index - 1); });
  if (nextBtn) nextBtn.addEventListener("click", function () { show(index + 1); });
  if (closeBtn) closeBtn.addEventListener("click", close);
  lb.addEventListener("click", function (ev) {
    if (ev.target === lb || ev.target.classList.contains("gal-lb__stage")) close();
  });

  document.addEventListener("keydown", function (ev) {
    if (lb.hidden) return;
    if (ev.key === "Escape") close();
    else if (ev.key === "ArrowLeft") show(index - 1);
    else if (ev.key === "ArrowRight") show(index + 1);
  });

  /* swipe */
  var sx = 0, sy = 0;
  lb.addEventListener("touchstart", function (ev) {
    if (ev.touches.length !== 1) return;
    sx = ev.touches[0].clientX;
    sy = ev.touches[0].clientY;
  }, { passive: true });
  lb.addEventListener("touchend", function (ev) {
    if (!ev.changedTouches.length) return;
    var dx = ev.changedTouches[0].clientX - sx;
    var dy = ev.changedTouches[0].clientY - sy;
    if (Math.abs(dx) > 44 && Math.abs(dx) > Math.abs(dy)) {
      show(index + (dx < 0 ? 1 : -1));
    }
  }, { passive: true });
})();
