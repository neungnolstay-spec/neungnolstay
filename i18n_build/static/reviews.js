/* NEUNGNOL STAY — room guest reviews (Firebase live list + guest write form).
   reviews/{room}/{id} = {name, rating, text, lang, textKo, createdAt, source}
   Static reviews in the page JSON are only used when Firebase has none. */
(function () {
  "use strict";
  var NNS = window.NNS;
  var list = document.querySelector("[data-reviews]");
  if (!NNS || !list) return;

  var room = (NNS.cfg || {}).room || "";
  var pageLang = (NNS.cfg || {}).lang || "ko";
  if (!room) return;

  var fb = document.querySelector("[data-rv-fallback]");
  var fallback = [];
  try { fallback = JSON.parse(fb ? fb.textContent : "[]") || []; } catch (e) { fallback = []; }

  var avgEl = document.querySelector("[data-rv-avg]");
  var starsEl = document.querySelector("[data-rv-stars]");
  var countEl = document.querySelector("[data-rv-count]");
  var emptyEl = document.querySelector("[data-rv-empty]");
  var openBtn = document.querySelector("[data-rv-open]");
  var form = document.querySelector("[data-rv-form]");
  var msgEl = document.querySelector("[data-rv-msg]");
  var submitBtn = document.querySelector("[data-rv-submit]");
  var cancelBtn = document.querySelector("[data-rv-cancel]");
  var starBox = document.querySelector("[data-rv-stars-pick]");
  var starVal = document.querySelector("[data-rv-star-val]");

  var S = readStrings();
  var starPick = 5;
  var sending = false;
  var lastItems = [];

  function readStrings() {
    var out = {};
    var el = document.querySelector("[data-rv-strings]");
    if (!el) return out;
    try { out = JSON.parse(el.textContent) || {}; } catch (e) { out = {}; }
    return out;
  }
  function txt(key, fallbackText) { return S[key] || fallbackText || ""; }

  function stars(n) {
    var v = Math.max(0, Math.min(5, Math.round(n)));
    return "★".repeat(v) + "☆".repeat(5 - v);
  }
  function fmtNum(n) { return (Math.round(n * 10) / 10).toFixed(1); }

  function renderScore(items) {
    if (!items.length) {
      if (avgEl) avgEl.textContent = "—";
      if (starsEl) starsEl.textContent = "";
      if (countEl) countEl.textContent = txt("count", "{n} reviews").replace("{n}", "0");
      return;
    }
    var sum = 0;
    items.forEach(function (it) { sum += Number(it.rating) || 0; });
    var avg = sum / items.length;
    if (avgEl) avgEl.textContent = fmtNum(avg);
    if (starsEl) starsEl.textContent = stars(avg);
    if (countEl) countEl.textContent = txt("count", "{n} reviews").replace("{n}", String(items.length));
  }

  function card(item) {
    var li = document.createElement("li");
    li.className = "review";
    li.setAttribute("data-review-id", item.id || "");

    var st = document.createElement("div");
    st.className = "review__stars";
    st.setAttribute("aria-label", (Number(item.rating) || 5) + " / 5");
    st.textContent = stars(Number(item.rating) || 5);
    li.appendChild(st);

    var p = document.createElement("p");
    p.className = "review__text";
    p.textContent = item.text || "";
    li.appendChild(p);

    var by = document.createElement("div");
    by.className = "review__by";
    var ava = document.createElement("span");
    ava.className = "review__ava";
    ava.setAttribute("aria-hidden", "true");
    ava.textContent = String(item.name || "?").slice(0, 1);
    var nm = document.createElement("b");
    nm.textContent = item.name || "";
    by.appendChild(ava);
    by.appendChild(nm);
    li.appendChild(by);

    localize(li, p, item);
    return li;
  }

  /** 다른 언어로 쓰인 후기는 화면 언어로 번역해 보여 주고, 원문 보기를 함께 둔다. */
  function localize(li, p, item) {
    var src = String(item.lang || "").toLowerCase();
    var original = item.text || "";
    var shown = false;

    function applyTranslated(translated, isTranslated) {
      if (!isTranslated) return;
      p.textContent = translated;
      var note = document.createElement("div");
      note.className = "rv-trans";
      var tag = document.createElement("span");
      tag.textContent = txt("translated", "Auto-translated");
      var toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "rv-trans__btn";
      toggle.textContent = txt("original", "Show original");
      toggle.addEventListener("click", function () {
        shown = !shown;
        p.textContent = shown ? original : translated;
        toggle.textContent = shown ? txt("translated", "Auto-translated") : txt("original", "Show original");
      });
      note.appendChild(tag);
      note.appendChild(toggle);
      li.insertBefore(note, li.querySelector(".review__by"));
    }

    if (!src || src === pageLang) return;
    if (pageLang === "ko" && item.textKo) {
      applyTranslated(item.textKo, true);
      return;
    }
    queue(function (done) {
      NNS.translate(original, pageLang, function (err, res) {
        if (!err && res && res.text && res.text !== original) applyTranslated(res.text, true);
        done();
      });
    });
  }

  /* 번역 요청은 한 번에 하나씩 (무료 엔드포인트 배려) */
  var queueList = [];
  var busy = false;
  function queue(fn) {
    queueList.push(fn);
    if (busy) return;
    busy = true;
    (function run() {
      var next = queueList.shift();
      if (!next) { busy = false; return; }
      next(function () { window.setTimeout(run, 120); });
    })();
  }

  function render(items) {
    lastItems = items;
    list.textContent = "";
    items.forEach(function (it) { list.appendChild(card(it)); });
    if (emptyEl) emptyEl.hidden = items.length > 0;
    renderScore(items);
  }

  function normalize(raw) {
    var out = [];
    Object.keys(raw || {}).forEach(function (id) {
      var r = raw[id] || {};
      if (r.deleted) return;
      out.push({
        id: id,
        name: String(r.name || ""),
        rating: Number(r.rating) || 5,
        text: String(r.text || ""),
        lang: String(r.lang || ""),
        textKo: String(r.textKo || ""),
        createdAt: Number(r.createdAt) || 0
      });
    });
    out.sort(function (a, b) { return b.createdAt - a.createdAt; });
    return out;
  }

  /* ---------- form ---------- */
  function setMsg(text, ok) {
    if (!msgEl) return;
    msgEl.textContent = text || "";
    msgEl.className = "rv-msg" + (text ? (ok ? " is-ok" : " is-error") : "");
  }
  function paintStars() {
    if (!starBox) return;
    Array.prototype.forEach.call(starBox.querySelectorAll("[data-rv-star]"), function (b) {
      var on = Number(b.getAttribute("data-rv-star")) <= starPick;
      b.classList.toggle("is-on", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
    if (starVal) starVal.textContent = String(starPick);
  }
  if (starBox) {
    starBox.addEventListener("click", function (ev) {
      var b = ev.target.closest ? ev.target.closest("[data-rv-star]") : null;
      if (!b) return;
      starPick = Number(b.getAttribute("data-rv-star")) || 5;
      paintStars();
    });
    paintStars();
  }
  if (openBtn && form) {
    openBtn.addEventListener("click", function () {
      form.hidden = false;
      openBtn.hidden = true;
      setMsg("");
      var first = form.querySelector('input[name="name"]');
      if (first) first.focus();
      NNS.track("review_form_open", { room: room });
    });
  }
  if (cancelBtn && form && openBtn) {
    cancelBtn.addEventListener("click", function () {
      form.hidden = true;
      openBtn.hidden = false;
      setMsg("");
    });
  }

  function validDone(items) { render(items); }

  if (form) {
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      if (sending) return;
      var data = new FormData(form);
      var name = String(data.get("name") || "").trim();
      var text = String(data.get("text") || "").trim();
      if (name.length < 1) { setMsg(txt("err_name", "Please enter your name.")); return; }
      if (text.length < 5) { setMsg(txt("err_text", "Please write at least 5 characters.")); return; }

      sending = true;
      if (submitBtn) { submitBtn.disabled = true; submitBtn.dataset.label = submitBtn.textContent; submitBtn.textContent = txt("submitting", "…"); }
      setMsg("");

      NNS.withDb("nns-reviews", function (err, db) {
        if (err || !db) { finish(); setMsg(txt("err_send", "Could not post.")); return; }
        /* 한국어가 아닌 후기는 한국어 번역본도 함께 저장 → 관리자가 바로 읽는다 */
        NNS.translate(text, "ko", function (terr, res) {
          var textKo = (!terr && res && res.text) ? res.text : "";
          var detected = (!terr && res && res.src) ? res.src : pageLang;
          var payload = {
            name: name.slice(0, 40),
            rating: starPick,
            text: text.slice(0, 1200),
            textKo: textKo,
            lang: detected || pageLang,
            pageLang: pageLang,
            room: room,
            source: "guest",
            createdAt: Date.now()
          };
          db.ref(NNS.PATH + "/reviews/" + room).push(payload, function (perr) {
            if (perr) { finish(); setMsg(txt("err_send", "Could not post.")); return; }
            finish();
            setMsg(txt("thanks", "Thank you."), true);
            form.reset();
            starPick = 5;
            paintStars();
            NNS.track("review_posted", { room: room, rating: payload.rating });
            window.setTimeout(function () {
              if (form && openBtn) { form.hidden = true; openBtn.hidden = false; }
            }, 2400);
          });
        });
      });

      function finish() {
        sending = false;
        if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = submitBtn.dataset.label || ""; }
      }
    });
  }

  /* ---------- boot ---------- */
  render(fallback.map(function (rv, i) {
    return { id: "static-" + i, name: rv.name, rating: rv.rating, text: rv.text, lang: "ko", textKo: rv.text, createdAt: 0 };
  }));

  NNS.withDb("nns-reviews", function (err, db) {
    if (err || !db) return;
    db.ref(NNS.PATH + "/reviews/" + room).on("value", function (snap) {
      var items = normalize(snap.val());
      if (!items.length) return; /* 비어 있으면 정적 후기 유지 */
      validDone(items);
    }, function () { /* 연결 실패: 정적 후기 유지 */ });
  });
})();
