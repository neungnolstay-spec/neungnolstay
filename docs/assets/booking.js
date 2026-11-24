/* NEUNGNOL STAY — direct booking calendar + request form.
   Live availability from Firebase RTDB /neungnol_booking_v1 (separate from the
   staff checklist at /neungnol_v1). Degrades to a phone/notice state if the
   database cannot be reached. */
(function () {
  "use strict";
  var root = document.querySelector("[data-booking]");
  if (!root) return;

  var cfg = window.SITE_CONFIG || {};
  var langEl = root.querySelector("[data-bk-lang]");
  var S = {};
  try { S = JSON.parse(langEl ? langEl.textContent : "{}"); } catch (e) { S = {}; }

  var FB_VERSION = "10.14.1";
  var FB_CONFIG = {
    apiKey: "AIzaSyDlcF9T8yqhfesUv5XkROKjJdezFq2CHFM",
    authDomain: "neungnol-checklist.firebaseapp.com",
    databaseURL: "https://neungnol-checklist-default-rtdb.asia-southeast1.firebasedatabase.app",
    projectId: "neungnol-checklist",
    storageBucket: "neungnol-checklist.firebasestorage.app",
    messagingSenderId: "449371435334",
    appId: "1:449371435334:web:neungnolstay"
  };
  var PATH = "/neungnol_booking_v1";
  var LOCALES = { ko: "ko-KR", en: "en-US", ja: "ja-JP", "zh-cn": "zh-CN", "zh-tw": "zh-TW" };
  var DEFAULT_RATES = {
    heyum: { wd: 500000, fri: 600000, sat: 1100000 },
    orot: { wd: 500000, fri: 600000, sat: 1100000 }
  };

  var state = {
    room: root.getAttribute("data-room") || "heyum",
    lang: root.getAttribute("data-lang") || "ko",
    base: parseInt(root.getAttribute("data-base"), 10) || 8,
    max: parseInt(root.getAttribute("data-max"), 10) || 12,
    extra: parseInt(root.getAttribute("data-extra"), 10) || 30000,
    ci: null,
    co: null,
    adults: 2,
    children: 0,
    infants: 0,
    view: null,
    blocks: {},
    bookings: {},
    settings: null,
    live: false,
    sending: false
  };
  state.view = startOfMonth(new Date());

  var calA = root.querySelector("[data-bk-cal]");
  var calB = root.querySelector("[data-bk-cal2]");
  var ciVal = root.querySelector("[data-bk-ci-val]");
  var coVal = root.querySelector("[data-bk-co-val]");
  var monthNow = root.querySelector("[data-bk-month]");
  var totalEl = root.querySelector("[data-bk-total]");
  var detailEl = root.querySelector("[data-bk-detail]");
  var form = root.querySelector("[data-bk-form]");
  var msgEl = root.querySelector("[data-bk-msg]");
  var submitBtn = root.querySelector("[data-bk-submit]");
  var doneEl = root.querySelector("[data-bk-done]");
  var refEl = root.querySelector("[data-bk-ref]");
  var altLink = null;
  var bankBox = root.querySelector("[data-bk-bank]");
  var bankLine = root.querySelector("[data-bk-bank-line]");
  var bankNote = root.querySelector("[data-bk-bank-note]");

  /* ---------- dates ---------- */
  function ymd(d) {
    var m = d.getMonth() + 1, day = d.getDate();
    return d.getFullYear() + "-" + (m < 10 ? "0" + m : m) + "-" + (day < 10 ? "0" + day : day);
  }
  function parseD(s) {
    var p = String(s || "").split("-");
    return new Date(+p[0], (+p[1] || 1) - 1, +p[2] || 1);
  }
  function addDays(d, n) {
    var x = new Date(d.getTime());
    x.setDate(x.getDate() + n);
    return x;
  }
  function startOfMonth(d) { return new Date(d.getFullYear(), d.getMonth(), 1); }
  function today0() { var n = new Date(); return new Date(n.getFullYear(), n.getMonth(), n.getDate()); }
  function nights() {
    if (!state.ci || !state.co) return 0;
    return Math.round((parseD(state.co) - parseD(state.ci)) / 86400000);
  }
  function fmtDate(s) {
    if (!s) return "—";
    return new Intl.DateTimeFormat(LOCALES[state.lang] || "ko-KR", {
      month: "short", day: "numeric", weekday: "short"
    }).format(parseD(s));
  }
  function fmtMonth(d) {
    return new Intl.DateTimeFormat(LOCALES[state.lang] || "ko-KR", {
      year: "numeric", month: "long"
    }).format(d);
  }
  function money(n) {
    return "₩" + Math.round(n).toLocaleString("en-US");
  }
  function shortPrice(p) {
    if (state.lang === "ko") return Math.round(p / 10000) + "만";
    if (p >= 1000000) return "₩" + (p / 1000000) + "M";
    return "₩" + Math.round(p / 1000) + "k";
  }

  /* ---------- availability & rates ---------- */
  function blocksFor(room) {
    /* 마감일은 /blocks 하나로만 판단한다.
       - 외부 예약(iCal)·직접 차단: 관리자가 등록
       - 확정 예약: 관리자가 확정할 때 reason="booking" 으로 자동 기록
       예약자 개인정보(/bookings)는 공개로 읽지 않는다. */
    var out = {};
    var b = state.blocks[room] || {};
    Object.keys(b).forEach(function (k) { if (b[k]) out[k] = true; });
    return out;
  }
  function ratesFor(room) {
    var r = (state.settings && state.settings.rates && state.settings.rates[room]) || {};
    var def = DEFAULT_RATES[room] || DEFAULT_RATES.heyum;
    return {
      wd: Number(r.wd) > 0 ? Number(r.wd) : def.wd,
      fri: Number(r.fri) > 0 ? Number(r.fri) : def.fri,
      sat: Number(r.sat) > 0 ? Number(r.sat) : def.sat
    };
  }
  function rateOf(room, dateStr) {
    var ov = state.settings && state.settings.overrides && state.settings.overrides[room];
    if (ov && Number(ov[dateStr]) > 0) return Number(ov[dateStr]);
    /* 네이버 플레이스 실판매 요금 시드(settings.naverRates) → 없으면 기본 평일/금/토 */
    var nr = state.settings && state.settings.naverRates && state.settings.naverRates[room];
    if (nr && Number(nr[dateStr]) > 0) return Number(nr[dateStr]);
    var r = ratesFor(room);
    var d = parseD(dateStr).getDay();
    if (d === 6) return r.sat;
    if (d === 5) return r.fri;
    return r.wd;
  }
  function sumPrice(room, from, to) {
    var total = 0, d = parseD(from), end = parseD(to), guard = 0;
    while (d < end && guard++ < 400) {
      total += rateOf(room, ymd(d));
      d = addDays(d, 1);
    }
    return total;
  }

  /* ---------- calendar ---------- */
  function renderCal(el, monthDate) {
    if (!el) return;
    var blocked = blocksFor(state.room);
    var y = monthDate.getFullYear(), m = monthDate.getMonth();
    var first = new Date(y, m, 1);
    var days = new Date(y, m + 1, 0).getDate();
    var lead = first.getDay();
    var today = today0();

    el.textContent = "";
    var head = document.createElement("div");
    head.className = "bk-cal__head";
    head.textContent = fmtMonth(monthDate);
    el.appendChild(head);

    var dow = document.createElement("div");
    dow.className = "bk-cal__dow";
    var wdFmt = new Intl.DateTimeFormat(LOCALES[state.lang] || "ko-KR", { weekday: "narrow" });
    var base = new Date(2024, 0, 7); /* a Sunday */
    for (var i = 0; i < 7; i++) {
      var c = document.createElement("span");
      c.textContent = wdFmt.format(addDays(base, i));
      dow.appendChild(c);
    }
    el.appendChild(dow);

    var grid = document.createElement("div");
    grid.className = "bk-cal__grid";
    for (var b = 0; b < lead; b++) {
      var blank = document.createElement("span");
      blank.className = "bk-day bk-day--blank";
      grid.appendChild(blank);
    }
    for (var day = 1; day <= days; day++) {
      var d = new Date(y, m, day);
      var key = ymd(d);
      var past = d < today;
      var off = !!blocked[key];
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "bk-day";
      btn.setAttribute("data-date", key);
      if (past) { btn.disabled = true; btn.classList.add("is-past"); }
      else if (off) { btn.disabled = true; btn.classList.add("is-off"); btn.title = S.closed || ""; }
      if (key === state.ci) btn.classList.add("is-ci");
      if (key === state.co) btn.classList.add("is-co");
      if (state.ci && state.co && key > state.ci && key < state.co) btn.classList.add("in-range");
      if (state.ci && !state.co && key > state.ci) btn.classList.add("after-ci");

      var num = document.createElement("span");
      num.textContent = String(day);
      btn.appendChild(num);
      if (!past && !off) {
        var em = document.createElement("em");
        em.textContent = shortPrice(rateOf(state.room, key));
        btn.appendChild(em);
      }
      grid.appendChild(btn);
    }
    el.appendChild(grid);
  }

  function renderCalendars() {
    renderCal(calA, state.view);
    renderCal(calB, new Date(state.view.getFullYear(), state.view.getMonth() + 1, 1));
    if (monthNow) monthNow.textContent = fmtMonth(state.view);
    var prev = root.querySelector("[data-bk-prev]");
    if (prev) prev.disabled = state.view <= startOfMonth(today0());
  }

  function renderDates() {
    if (ciVal) ciVal.textContent = fmtDate(state.ci);
    if (coVal) coVal.textContent = fmtDate(state.co);
  }

  /* ---------- price summary ---------- */
  function guestCount() { return state.adults + state.children; }
  function extraGuests() { return Math.max(0, guestCount() - state.base); }

  function renderSummary() {
    var n = nights();
    if (!n) {
      if (totalEl) totalEl.textContent = "—";
      if (detailEl) detailEl.textContent = S.pick_dates || "";
      return;
    }
    var stay = sumPrice(state.room, state.ci, state.co);
    var extra = extraGuests() * state.extra * n;
    var total = stay + extra;
    if (totalEl) totalEl.textContent = money(total);
    var parts = [(S.price_each || "{price} × {n}").replace("{price}", money(stay / n)).replace("{n}", String(n))];
    if (extra > 0) {
      parts.push((S.extra || "") + " " + extraGuests() + " × " + money(state.extra) + " × " + n);
    }
    if (detailEl) detailEl.textContent = parts.join(" · ");
  }

  function renderGuests() {
    ["adults", "children", "infants"].forEach(function (k) {
      var el = root.querySelector('[data-bk-num="' + k + '"]');
      if (el) el.textContent = String(state[k]);
      root.querySelectorAll('[data-bk-step="' + k + '"]').forEach(function (btn) {
        var dir = parseInt(btn.getAttribute("data-dir"), 10);
        var min = k === "adults" ? 1 : 0;
        var max = k === "infants" ? 5 : state.max;
        var next = state[k] + dir;
        btn.disabled = next < min || (k !== "infants" && guestCount() + dir > state.max) || next > max;
      });
    });
  }

  function renderAll() {
    renderCalendars();
    renderDates();
    renderSummary();
    renderGuests();
  }

  /* ---------- interaction ---------- */
  function setMsg(text, kind) {
    if (!msgEl) return;
    msgEl.textContent = text || "";
    msgEl.className = "bk-msg" + (kind ? " bk-msg--" + kind : "");
  }

  function selectRoom(room) {
    if (!room || room === state.room) return;
    state.room = room;
    root.setAttribute("data-room", room);
    state.ci = null;
    state.co = null;
    root.querySelectorAll("[data-bk-room]").forEach(function (b) {
      var on = b.getAttribute("data-bk-room") === room;
      b.classList.toggle("is-on", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
    setMsg("");
    renderAll();
  }

  /* 홈·객실 카드의 예약 버튼: 이 페이지의 예약창으로 이동하면서 그 객실을 선택한다 */
  document.addEventListener("click", function (ev) {
    var btn = ev.target.closest ? ev.target.closest("[data-book-room]") : null;
    if (!btn || root.contains(btn)) return;
    var room = btn.getAttribute("data-book-room");
    selectRoom(room);
    track("booking_cta", { room: room, placement: btn.getAttribute("data-placement") || "" });
  });

  root.addEventListener("click", function (ev) {
    var day = ev.target.closest ? ev.target.closest(".bk-day[data-date]") : null;
    if (day && !day.disabled) {
      pick(day.getAttribute("data-date"));
      return;
    }
    var step = ev.target.closest ? ev.target.closest("[data-bk-step]") : null;
    if (step) {
      var key = step.getAttribute("data-bk-step");
      var dir = parseInt(step.getAttribute("data-dir"), 10);
      var min = key === "adults" ? 1 : 0;
      var next = state[key] + dir;
      if (key !== "infants" && next + (key === "adults" ? state.children : state.adults) > state.max) return;
      if (next < min || (key === "infants" && next > 5)) return;
      state[key] = next;
      renderGuests();
      renderSummary();
      return;
    }
    var roomBtn = ev.target.closest ? ev.target.closest("[data-bk-room]") : null;
    if (roomBtn) {
      var room = roomBtn.getAttribute("data-bk-room");
      if (room === state.room) return;
      selectRoom(room);
      track("booking_room_switch", { room: room });
      return;
    }
    var prev = ev.target.closest ? ev.target.closest("[data-bk-prev]") : null;
    if (prev) {
      state.view = new Date(state.view.getFullYear(), state.view.getMonth() - 1, 1);
      renderCalendars();
      return;
    }
    var nextM = ev.target.closest ? ev.target.closest("[data-bk-next]") : null;
    if (nextM) {
      var maxMonth = new Date(today0().getFullYear(), today0().getMonth() + 11, 1);
      var cand = new Date(state.view.getFullYear(), state.view.getMonth() + 1, 1);
      if (cand <= maxMonth) state.view = cand;
      renderCalendars();
      return;
    }
    var jumpCi = ev.target.closest ? ev.target.closest("[data-bk-ci]") : null;
    if (jumpCi) { state.ci = null; state.co = null; setMsg(""); renderAll(); return; }
    var jumpCo = ev.target.closest ? ev.target.closest("[data-bk-co]") : null;
    if (jumpCo) { state.co = null; setMsg(""); renderAll(); return; }
    var again = ev.target.closest ? ev.target.closest("[data-bk-again]") : null;
    if (again) {
      state.ci = null;
      state.co = null;
      state.adults = 2;
      state.children = 0;
      state.infants = 0;
      if (form) { form.hidden = false; form.reset(); }
      if (doneEl) doneEl.hidden = true;
      setMsg("");
      renderAll();
    }
  });

  function pick(date) {
    setMsg("");
    if (!state.ci || (state.ci && state.co)) {
      state.ci = date;
      state.co = null;
    } else if (date <= state.ci) {
      state.ci = date;
      state.co = null;
    } else {
      var blocked = blocksFor(state.room);
      var d = parseD(state.ci), end = parseD(date), bad = false, guard = 0;
      while (d < end && guard++ < 400) {
        if (blocked[ymd(d)]) { bad = true; break; }
        d = addDays(d, 1);
      }
      if (bad) {
        state.ci = date;
        state.co = null;
        setMsg(S.err_closed || "", "error");
      } else {
        state.co = date;
        track("booking_dates_selected", { room: state.room, nights: nights() });
      }
    }
    renderAll();
  }

  /* ---------- form ---------- */
  function validPhone(v) {
    var digits = String(v || "").replace(/[^0-9]/g, "");
    return digits.length >= 9 && digits.length <= 15;
  }

  if (form) {
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      if (state.sending) return;
      var data = new FormData(form);
      var name = String(data.get("name") || "").trim();
      var phone = String(data.get("phone") || "").trim();
      var email = String(data.get("email") || "").trim();
      var message = String(data.get("message") || "").trim();

      if (!state.ci || !state.co) return setMsg(S.err_dates || "", "error");
      if (nights() < 1) return setMsg(S.err_order || "", "error");
      if (!name || name.length < 2) return setMsg(S.err_name || "", "error");
      if (!validPhone(phone)) return setMsg(S.err_phone || "", "error");
      if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) return setMsg(S.err_email || "", "error");
      if (!state.live) return setMsg(S.err_offline || "", "error");

      var blocked = blocksFor(state.room);
      var d = parseD(state.ci), end = parseD(state.co), guard = 0;
      while (d < end && guard++ < 400) {
        if (blocked[ymd(d)]) return setMsg(S.err_closed || "", "error");
        d = addDays(d, 1);
      }

      var n = nights();
      var total = sumPrice(state.room, state.ci, state.co) + extraGuests() * state.extra * n;
      var amenities = [];
      form.querySelectorAll('input[name="amenity"]:checked').forEach(function (cb) { amenities.push(cb.value); });
      var payload = {
        room: state.room,
        checkin: state.ci,
        checkout: state.co,
        nights: n,
        adults: state.adults,
        children: state.children,
        infants: state.infants,
        name: name,
        phone: phone,
        email: email,
        message: message,
        amenitiesRequested: amenities,
        total: total,
        currency: "KRW",
        status: "pending",
        source: "direct",
        lang: state.lang,
        createdAt: Date.now()
      };

      state.sending = true;
      if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = S.submitting || "…"; }
      setMsg("");
      var done = function (err, ref) {
        state.sending = false;
        if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = S.submit || ""; }
        if (err) {
          setMsg(S.err_send || "", "error");
          return;
        }
        var key = ref && ref.key ? ref.key : "";
        var refNo = "NN-" + state.ci.replace(/-/g, "").slice(2) + "-" + key.slice(-4).toUpperCase();
        if (refEl) refEl.textContent = refNo;
        showBank();
        if (form) form.hidden = true;
        if (doneEl) doneEl.hidden = false;
        track("booking_request_sent", { room: state.room, nights: n, guests: guestCount(), value: total, ref: refNo });
        /* 내 예약 조회용 지문 — 접수번호 + 연락처 뒤 4자리로만 찾을 수 있다
           (예약 목록을 공개하지 않기 위한 장치) */
        writeLookup(refNo, phone, key);
      };

      try {
        var newRef = db.ref(PATH + "/bookings").push(payload, function (err) { done(err, newRef); });
      } catch (e) {
        done(new Error("push"));
      }
    });
  }

  /* ---------- bank ---------- */
  function showBank() {
    if (!bankBox) return;
    var bank = state.settings && state.settings.bank;
    var line = "";
    if (bank) {
      var parts = [];
      if (bank.bank) parts.push(bank.bank);
      if (bank.account) parts.push(bank.account);
      if (bank.holder) parts.push(bank.holder);
      line = parts.join(" ");
    }
    if (line) {
      bankBox.hidden = false;
      if (bankLine) bankLine.textContent = line;
      if (bankNote) bankNote.textContent = bank && bank.note ? bank.note : "";
    } else {
      bankBox.hidden = false;
      if (bankLine) bankLine.textContent = S.bank_empty || "";
      if (bankNote) bankNote.textContent = "";
    }
  }

  /* ---------- 내 예약 조회 지문 ----------
     접수번호 + 연락처 뒤 4자리 → SHA-256 지문(/lookup)으로 예약 id를 찾는다.
     이렇게 하면 예약 목록을 공개하지 않아도 본인 예약만 열 수 있다. */
  function sha256hex(s) {
    try {
      if (!(window.crypto && window.crypto.subtle && window.TextEncoder)) return Promise.reject(new Error("nocrypto"));
      return window.crypto.subtle.digest("SHA-256", new TextEncoder().encode(s)).then(function (buf) {
        return Array.prototype.map.call(new Uint8Array(buf), function (b) {
          return ("00" + b.toString(16)).slice(-2);
        }).join("");
      });
    } catch (e) { return Promise.reject(e); }
  }
  function lookupKey(refNo, phone) {
    var p4 = String(phone || "").replace(/[^0-9]/g, "").slice(-4);
    return sha256hex("neungnol|" + String(refNo || "").trim().toUpperCase() + "|" + p4);
  }
  function writeLookup(refNo, phone, key) {
    if (!db || !refNo || !key) return;
    lookupKey(refNo, phone).then(function (h) {
      db.ref(PATH + "/lookup/" + h).set({ id: key, createdAt: Date.now() }).catch(function () {});
    }, function () { /* 지문 미지원 브라우저에서는 조회 지문을 생략 */ });
  }

  /* ---------- firebase ---------- */
  var db = null;
  var started = false;
  var timeoutId = null;
  var liveRefs = [];

  function track(name, params) {
    var payload = Object.assign({ page_language: state.lang, room: state.room }, params || {});
    try {
      if (typeof window.gtag === "function") window.gtag("event", name, payload);
      else if (window.dataLayer) window.dataLayer.push(Object.assign({ event: name }, payload));
    } catch (e) { /* analytics never breaks booking */ }
  }

  function offline(msg) {
    state.live = false;
    if (submitBtn) submitBtn.disabled = true;
    setMsg(msg || S.err_offline || "", "error");
  }

  /* 공개 화면은 마감일(/blocks)과 공개 설정값(요금·계좌)만 읽는다.
     예약 목록(/bookings)은 잠겨 있어 읽지 않는다. */
  function markLive() {
    try {
      state.live = true;
      setMsg("");
      if (submitBtn) submitBtn.disabled = false;
    } catch (e) { /* noop */ }
  }

  function onBlocks(value) {
    state.blocks = value || {};
    markLive();
    renderAll();
  }

  function onSetting(key) {
    return function (snap) {
      state.settings = state.settings || {};
      state.settings[key] = snap && snap.val ? snap.val() : null;
      markLive();
      renderAll();
    };
  }

  function boot() {
    if (started) return;
    started = true;
    var finish = function (err) {
      if (err) { offline(); return; }
      try {
        var app = null;
        (firebase.apps || []).forEach(function (a) { if (a.name === "nns-booking") app = a; });
        if (!app) app = firebase.initializeApp(FB_CONFIG, "nns-booking");
        db = app.database();
        var fail = function () { offline(); };
        liveRefs.push(db.ref(PATH + "/blocks"));
        liveRefs[0].on("value", function (snap) { onBlocks(snap.val()); }, fail);
        ["rates", "overrides", "naverRates", "bank"].forEach(function (k) {
          var r = db.ref(PATH + "/settings/" + k);
          liveRefs.push(r);
          r.on("value", onSetting(k), fail);
        });
      } catch (e) {
        offline();
      }
    };
    if (window.firebase && window.firebase.database) { finish(null); return; }
    var base = "https://www.gstatic.com/firebasejs/" + FB_VERSION + "/";
    var addScript = function (src, ok, fail) {
      var s = document.createElement("script");
      s.src = src;
      s.async = false;
      s.onload = ok;
      s.onerror = fail;
      document.head.appendChild(s);
    };
    /* app-compat → database-compat 순서를 지켜야 compat shim 이 초기화된다 */
    addScript(base + "firebase-app-compat.js", function () {
      addScript(base + "firebase-database-compat.js", function () { finish(null); },
        function () { finish(new Error("sdk")); });
    }, function () { finish(new Error("sdk")); });
    timeoutId = window.setTimeout(function () {
      if (!state.live) offline(S.err_offline || "");
    }, 12000);
  }

  /* 첫 화면 렌더는 즉시, Firebase 연결은 예약 영역이 보일 때 */
  renderAll();
  if (submitBtn) submitBtn.disabled = true;
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { obs.disconnect(); boot(); }
      });
    }, { rootMargin: "200px 0px" });
    io.observe(root);
  } else {
    boot();
  }
  window.addEventListener("pagehide", function () {
    if (timeoutId) window.clearTimeout(timeoutId);
    try {
      liveRefs.forEach(function (r) { try { r.off(); } catch (e) { /* noop */ } });
      liveRefs = [];
      if (db) db.goOffline();
    } catch (e) { /* teardown */ }
  });
})();
