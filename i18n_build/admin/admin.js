/* NEUNGNOL STAY — host admin (예약 달력 · 예약 신청 관리 · 요금 설정).
   Firebase RTDB /neungnol_booking_v1. 직원 체크리스트(/neungnol_v1)는 건드리지 않는다. */
(function () {
  "use strict";

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
  /* 관리자 계정 — Firebase Auth 로그인(Google 또는 이메일)이 끝나야 DB에 접근할 수 있다 */
  var ADMIN_EMAIL = "eodnrdlrnrnf@gmail.com";
  /* 관리자로 인정하는 계정 — Firebase Auth에서 이메일 인증이 끝난 계정만 통과 */
  var ADMIN_EMAILS = ["eodnrdlrnrnf@gmail.com", "anseodnr@naver.com"];
  var SESSION_KEY = "nns_admin_session";
  var SESSION_MS = 12 * 3600 * 1000;
  var ROOM_NAME = { heyum: "헤윰 · 3층", orot: "오롯 · 6층" };
  var DEFAULT_RATES = {
    heyum: { wd: 500000, fri: 600000, sat: 1100000 },
    orot: { wd: 500000, fri: 600000, sat: 1100000 }
  };
  var DEFAULT_EXTRA = 30000;
  /* 예약·차단 출처 — 색상으로 구분 (네이버 초록 · 에어비앤비 파랑 · 직접 차콜/앰버) */
  var SOURCE = {
    naver: { label: "네이버 예약", short: "네이버", color: "#03C75A" },
    airbnb: { label: "에어비앤비", short: "에어비", color: "#0077FF" },
    direct: { label: "직접 예약", short: "직접", color: "#1C1C1C" },
    website: { label: "직접 예약", short: "직접", color: "#1C1C1C" },
    manual: { label: "직접 예약", short: "직접", color: "#1C1C1C" },
    other: { label: "기타 차단", short: "차단", color: "#8a847a" }
  };
  var PENDING_COLOR = "#D97706";
  /* 무료 비품·유아용품 (content/booking.py 의 amenities 키와 동일) */
  var AMENITY = {
    kidsroom: "키즈룸 개방",
    highchair: "아기 하이체어",
    sterilizer: "젖병소독기",
    babyshampoo: "유아샴푸",
    pillow: "유아동 베개",
    babydish: "유아식기",
    bedguard: "아기침대 안전가드"
  };
  function amenityLabels(b) {
    var arr = (b && b.amenitiesRequested) || [];
    if (typeof arr === "string") arr = [arr];
    return arr.map(function (k) { return AMENITY[k] || String(k); });
  }
  function amenityRow(b) {
    var labels = amenityLabels(b);
    if (!labels.length) return null;
    var box = el("div", "bk__amen");
    labels.forEach(function (l) { box.appendChild(el("span", null, "✓ " + l)); });
    return box;
  }
  var DEFAULT_TEMPLATES = {
    heyum: "안녕하세요 {name}님, 능놀스테이 헤윰입니다.\n\n" +
      "입실 {checkin} 15:00 / 퇴실 {checkout} 11:00\n" +
      "주소: 부산광역시 수영구 민락수변로 13 (3층)\n\n" +
      "· 건물 현관 도어락: {doorlock}\n" +
      "· 헤윰 객실 도어락: {roomlock}\n" +
      "· 주차: 민락회센터·민락어패류주차장 1대 무료 (도보 1분, 차종 사전 협의)\n\n" +
      "· 요청하신 무료 비품: {amenities}\n\n" +
      "입금 계좌: {account}\n" +
      "문의: {phone}\n\n" +
      "편안히 쉬다 가실 수 있도록 준비해 두겠습니다. 감사합니다.",
    orot: "안녕하세요 {name}님, 능놀스테이 오롯입니다.\n\n" +
      "입실 {checkin} 16:00 / 퇴실 {checkout} 12:00\n" +
      "주소: 부산광역시 수영구 민락수변로 13 (6층)\n\n" +
      "· 건물 현관 도어락: {doorlock}\n" +
      "· 오롯 객실 도어락: {roomlock}\n" +
      "· 주차: 민락회센터·민락어패류주차장 1대 무료 (도보 1분, 차종 사전 협의)\n\n" +
      "· 요청하신 무료 비품: {amenities}\n\n" +
      "입금 계좌: {account}\n" +
      "문의: {phone}\n\n" +
      "편안히 쉬다 가실 수 있도록 준비해 두겠습니다. 감사합니다."
  };
  var PHONE = "010-3098-2302";

  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  var db = null;
  var state = {
    ready: false,
    settings: null,
    blocks: {},
    bookings: {},
    reviews: {},
    inquiries: {},
    room: "heyum",
    reviewRoom: "heyum",
    inqFilter: "all",
    view: startOfMonth(new Date()),
    tab: "cal",
    filter: "all",
    pinInput: "",
    pendingPin: null,
    sel: null,
    lastSync: null
  };

  /* ---------- helpers ---------- */
  function ymd(d) {
    var m = d.getMonth() + 1, day = d.getDate();
    return d.getFullYear() + "-" + (m < 10 ? "0" + m : m) + "-" + (day < 10 ? "0" + day : day);
  }
  function parseD(s) {
    var p = String(s || "").split("-");
    return new Date(+p[0], (+p[1] || 1) - 1, +p[2] || 1);
  }
  function addDays(d, n) { var x = new Date(d.getTime()); x.setDate(x.getDate() + n); return x; }
  function startOfMonth(d) { return new Date(d.getFullYear(), d.getMonth(), 1); }
  function today0() { var n = new Date(); return new Date(n.getFullYear(), n.getMonth(), n.getDate()); }
  function money(n) { return "₩" + Math.round(Number(n) || 0).toLocaleString("ko-KR"); }
  function daysBetween(a, b) { return Math.round((parseD(b) - parseD(a)) / 86400000); }
  function dateRange(a, b) {
    var out = [], d = parseD(a), end = parseD(b), guard = 0;
    while (d <= end && guard++ < 400) { out.push(ymd(d)); d = addDays(d, 1); }
    return out;
  }
  function dateKo(s) {
    var d = parseD(s);
    var w = ["일", "월", "화", "수", "목", "금", "토"][d.getDay()];
    return (d.getMonth() + 1) + "월 " + d.getDate() + "일 (" + w + ")";
  }
  function ts(v) {
    if (!v) return "—";
    var d = new Date(v);
    return d.getFullYear() + "." + (d.getMonth() + 1) + "." + d.getDate() + " " +
      String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0");
  }
  function toast(text) {
    var el = $("#toast");
    if (!el) return;
    el.textContent = text;
    el.hidden = false;
    window.clearTimeout(toast._t);
    toast._t = window.setTimeout(function () { el.hidden = true; }, 2400);
  }
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = String(text);
    return n;
  }

  /* ---------- PIN ---------- */
  function hashPin(pin) {
    var s = "neungnol-stay|" + pin;
    if (window.crypto && window.crypto.subtle && window.TextEncoder) {
      return window.crypto.subtle.digest("SHA-256", new TextEncoder().encode(s)).then(function (buf) {
        var hex = Array.prototype.map.call(new Uint8Array(buf), function (b) {
          return ("00" + b.toString(16)).slice(-2);
        }).join("");
        return "s256:" + hex;
      });
    }
    var h = 5381;
    for (var i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0;
    return Promise.resolve("djb:" + (h >>> 0).toString(16));
  }

  function sessionValid() {
    try {
      var raw = window.sessionStorage.getItem(SESSION_KEY);
      if (!raw) return false;
      var o = JSON.parse(raw);
      return o && o.exp > Date.now();
    } catch (e) { return false; }
  }
  function startSession() {
    try { window.sessionStorage.setItem(SESSION_KEY, JSON.stringify({ exp: Date.now() + SESSION_MS })); } catch (e) {}
  }
  function endSession() {
    try { window.sessionStorage.removeItem(SESSION_KEY); } catch (e) {}
  }

  function renderPinDots() {
    $$("#pinDots i").forEach(function (dot, i) {
      dot.classList.toggle("on", i < state.pinInput.length);
    });
  }

  function submitPin(pin) {
    var msg = $("#lockMsg");
    var expected = state.settings && state.settings.pinHash;
    if (!expected) {
      state.pendingPin = pin;
      if (msg) msg.textContent = "설정을 불러오는 중입니다. 잠시만 기다려 주세요.";
      return;
    }
    state.pendingPin = null;
    hashPin(pin).then(function (h) {
      if (h === expected) {
        startSession();
        openApp();
      } else {
        if (msg) msg.textContent = "PIN이 맞지 않습니다.";
        state.pinInput = "";
        renderPinDots();
      }
    });
  }

  function openApp() {
    $("#lock").hidden = true;
    $("#app").hidden = false;
    renderAll();
  }

  /* ---------- firebase ---------- */
  function loadSdk() {
    return new Promise(function (resolve, reject) {
      if (window.firebase && window.firebase.database && window.firebase.auth) return resolve();
      var base = "https://www.gstatic.com/firebasejs/" + FB_VERSION + "/";
      var addScript = function (src, ok, fail) {
        var s = document.createElement("script");
        s.src = src;
        s.async = false;
        s.onload = ok;
        s.onerror = fail;
        document.head.appendChild(s);
      };
      /* app-compat → auth-compat → database-compat 순서 보장 */
      addScript(base + "firebase-app-compat.js", function () {
        addScript(base + "firebase-auth-compat.js", function () {
          addScript(base + "firebase-database-compat.js", function () { resolve(); },
            function () { reject(new Error("sdk:database")); });
        }, function () { reject(new Error("sdk:auth")); });
      }, function () { reject(new Error("sdk:app")); });
    });
  }

  function setSync(kind, text) {
    var elx = $("#syncState");
    if (!elx) return;
    elx.className = "sync" + (kind ? " is-" + kind : "");
    elx.textContent = text;
  }

  /* 인증(auth)과 DB는 같은 Firebase 앱 인스턴스를 써야 권한이 전달된다 */
  function ensureApp() {
    if (!firebase.apps || !firebase.apps.length) firebase.initializeApp(FB_CONFIG);
    return firebase.app();
  }

  function connect() {
    if (db) return;
    loadSdk().then(function () {
      var app = ensureApp();
      db = app.database();
      db.ref(PATH).on("value", function (snap) {
        var v = snap.val() || {};
        state.settings = v.settings || null;
        state.blocks = v.blocks || {};
        state.bookings = v.bookings || {};
        state.reviews = v.reviews || {};
        state.inquiries = v.inquiries || {};
        state.ready = true;
        state.lastSync = Date.now();
        setSync("live", "실시간 연결");
        var off = $("#lockOff");
        if (off) off.hidden = true;
        if (!state.settings) ensureSettings().then(function () { renderAll(); });
        if (state.pendingPin && state.settings) {
          var pin = state.pendingPin;
          state.pendingPin = null;
          state.pinInput = pin;
          submitPin(pin);
        }
        renderAll();
      }, function () {
        setSync("off", "연결 끊김");
        var off = $("#lockOff");
        if (off) off.hidden = false;
      });
      if (sessionValid()) { /* 앱은 데이터가 오면 열린다 */ }
      window.setTimeout(function () {
        if (!state.ready) {
          var off = $("#lockOff");
          if (off) off.hidden = false;
        }
      }, 9000);
    }).catch(function () {
      setSync("off", "연결 실패");
      var off = $("#lockOff");
      if (off) off.hidden = false;
    });
  }

  function ensureSettings() {
    if (state.settings || !db) return Promise.resolve();
    return hashPin("0000").then(function (hash) {
      return db.ref(PATH + "/settings").set({
        rates: DEFAULT_RATES,
        overrides: {},
        extraPerson: DEFAULT_EXTRA,
        baseGuests: 8,
        maxGuests: 12,
        pinHash: hash,
        version: 1,
        createdAt: Date.now(),
        updatedAt: Date.now()
      });
    });
  }

  /* ---------- derived ---------- */
  function bookingsArr() {
    return Object.keys(state.bookings).map(function (id) {
      var b = state.bookings[id] || {};
      b.id = id;
      return b;
    });
  }
  function srcKey(b) {
    var s = String((b && b.source) || "direct");
    if (s === "website" || s === "manual" || s === "homepage") return "direct";
    return SOURCE[s] ? s : "direct";
  }
  function srcOfBooking(b) {
    var k = srcKey(b);
    return SOURCE[k];
  }
  function blockSource(room, date) {
    var b = state.blocks[room] && state.blocks[room][date];
    if (!b) return null;
    var s = String((b && b.source) || "other");
    if (!SOURCE[s] || s === "direct") s = s === "naver" || s === "airbnb" ? s : "other";
    return SOURCE[s];
  }
  function coveringBookings(room, date) {
    return bookingsArr().filter(function (b) {
      if (b.room !== room) return false;
      if (b.status !== "pending" && b.status !== "confirmed") return false;
      return date >= b.checkin && date < b.checkout;
    });
  }
  function dayStatus(room, date) {
    var list = coveringBookings(room, date);
    var conf = list.filter(function (b) { return b.status === "confirmed"; });
    var pend = list.filter(function (b) { return b.status === "pending"; });
    var block = state.blocks[room] && state.blocks[room][date];
    if (conf.length) {
      /* 확정 예약이 차단보다 우선 (직접·네이버·에어비앤비 색으로 표시) */
      return { kind: "confirmed", items: conf.concat(pend), blocked: !!block, src: srcKey(conf[0]), label: srcOfBooking(conf[0]).short };
    }
    if (block) {
      var bs = blockSource(room, date);
      return { kind: "blocked", items: pend, blocked: true, src: (block.source || "other"), label: bs.short };
    }
    if (pend.length) {
      return { kind: "pending", items: pend, blocked: false, src: "pending", label: "대기" };
    }
    return { kind: "open", items: [], blocked: false, src: null, label: "" };
  }
  function rateOf(room, date) {
    var ov = state.settings && state.settings.overrides && state.settings.overrides[room];
    if (ov && Number(ov[date]) > 0) return Number(ov[date]);
    var nr = state.settings && state.settings.naverRates && state.settings.naverRates[room];
    if (nr && Number(nr[date]) > 0) return Number(nr[date]);
    var r = (state.settings && state.settings.rates && state.settings.rates[room]) || DEFAULT_RATES[room];
    var d = parseD(date).getDay();
    if (d === 6) return Number(r.sat) || DEFAULT_RATES[room].sat;
    if (d === 5) return Number(r.fri) || DEFAULT_RATES[room].fri;
    return Number(r.wd) || DEFAULT_RATES[room].wd;
  }
  function isOverride(room, date) {
    var ov = state.settings && state.settings.overrides && state.settings.overrides[room];
    return !!(ov && Number(ov[date]) > 0);
  }
  function isNaverRate(room, date) {
    var nr = state.settings && state.settings.naverRates && state.settings.naverRates[room];
    return !!(nr && Number(nr[date]) > 0);
  }

  /* ---------- calendar ---------- */
  function renderCalendar() {
    var grid = $("#calGrid");
    if (!grid) return;
    var y = state.view.getFullYear(), m = state.view.getMonth();
    var first = new Date(y, m, 1);
    var total = new Date(y, m + 1, 0).getDate();
    var lead = first.getDay();
    var today = today0();
    grid.textContent = "";
    for (var i = 0; i < lead; i++) grid.appendChild(el("div", "day is-blank"));

    for (var d = 1; d <= total; d++) {
      var date = new Date(y, m, d);
      var key = ymd(date);
      var st = dayStatus(state.room, key);
      var cell = el("button", "day");
      cell.type = "button";
      cell.setAttribute("data-date", key);
      if (date < today) cell.classList.add("is-past");
      if (key === ymd(today)) cell.classList.add("is-today");
      if (st.kind === "blocked") cell.classList.add("is-blocked");
      if (st.kind === "pending") cell.classList.add("is-pending");
      if (st.kind === "confirmed") cell.classList.add("is-booked");
      if (st.src) {
        cell.setAttribute("data-source", st.src);
        cell.classList.add("is-src-" + st.src);
      }
      cell.appendChild(el("span", "day__n", d));
      cell.appendChild(el("span", "day__p", Math.round(rateOf(state.room, key) / 10000) + "만" + (isOverride(state.room, key) ? " *" : "")));
      if (st.kind !== "open") {
        var cls = "day__s day__s--" + (st.kind === "blocked" ? st.src || "blocked" : st.kind);
        var badge = el("span", cls, st.label);
        if (st.src && (st.src === "naver" || st.src === "airbnb")) badge.style.background = SOURCE[st.src].color;
        cell.appendChild(badge);
      }
      if (state.sel && key >= state.sel.a && key <= state.sel.b) cell.classList.add("is-sel");
      grid.appendChild(cell);
    }

    var label = $("#monthLabel");
    if (label) label.textContent = y + "년 " + (m + 1) + "월";

    /* 이번 달 요약 */
    var monthStart = ymd(first), monthEnd = ymd(new Date(y, m + 1, 0));
    var stats = $("#calStats");
    if (stats) {
      stats.textContent = "";
      var mine = bookingsArr().filter(function (b) {
        return b.room === state.room && b.status !== "cancelled" && b.checkin <= monthEnd && b.checkout > monthStart;
      });
      var conf = mine.filter(function (b) { return b.status === "confirmed"; });
      var pend = mine.filter(function (b) { return b.status === "pending"; });
      var blockCount = Object.keys(state.blocks[state.room] || {}).filter(function (d) {
        return d >= monthStart && d <= monthEnd;
      }).length;
      var revenue = conf.reduce(function (sum, b) { return sum + (Number(b.total) || 0); }, 0);
      [
        ["확정 예약", conf.length, "건"],
        ["확인 대기", pend.length, "건"],
        ["외부 차단", blockCount, "일"],
        ["확정 금액", money(revenue), ""]
      ].forEach(function (s) {
        var box = el("div", "calstat");
        box.appendChild(el("span", null, s[0]));
        var bEl = el("b", null, s[1]);
        if (s[2]) bEl.appendChild(el("em", null, s[2]));
        box.appendChild(bEl);
        stats.appendChild(box);
      });
    }

    /* 이번 달 요약 목록 */
    var list = $("#monthList");
    if (list) {
      list.textContent = "";
      var rows = bookingsArr().filter(function (b) {
        return b.room === state.room && b.status !== "cancelled" &&
          b.checkin <= monthEnd && b.checkout > monthStart;
      }).sort(function (a, b) { return a.checkin < b.checkin ? -1 : 1; });
      if (!rows.length) {
        list.appendChild(el("p", "hint", "이 달에는 등록된 예약이 없습니다."));
      }
      rows.forEach(function (b) {
        var row = el("div", "mrow");
        var src = srcOfBooking(b);
        var chip = el("i", "mrow__src");
        chip.style.background = b.status === "confirmed" ? src.color : PENDING_COLOR;
        row.appendChild(chip);
        row.appendChild(el("b", null, dateKo(b.checkin).replace(/ \(.\)/, "") + " → " + dateKo(b.checkout).replace(/ \(.\)/, "")));
        row.appendChild(el("span", null, (b.name || "이름 없음") + " · " + (b.nights || daysBetween(b.checkin, b.checkout)) + "박 · " +
          (b.status === "confirmed" ? src.short + " 확정" : "승인 대기")));
        var btn = el("button", null, "보기");
        btn.addEventListener("click", function () { showTab("bookings"); });
        row.appendChild(btn);
        list.appendChild(row);
      });
    }
  }

  /* ---------- day sheet ---------- */
  function openSheet(range) {
    var a = range.a, b = range.b || range.a;
    state.sel = { a: a, b: b };
    renderCalendar();
    var sheet = $("#sheet");
    var title = $("#sheetTitle");
    var sub = $("#sheetSub");
    var body = $("#sheetBody");
    if (!sheet || !body) return;
    var n = dateRange(a, b).length;
    if (title) title.textContent = a === b ? dateKo(a) : dateKo(a) + " → " + dateKo(b);
    var kinds = {};
    dateRange(a, b).forEach(function (d) { kinds[dayStatus(state.room, d).kind] = true; });
    var now = kinds.confirmed ? "확정 예약 포함" : kinds.pending ? "직접예약 대기 포함" : kinds.blocked ? "외부예약 차단" : "예약 가능";
    if (sub) sub.textContent = n + "일 · " + ROOM_NAME[state.room] + " · " + now;

    body.textContent = "";

    /* 기존 예약 */
    var inRange = bookingsArr().filter(function (bk) {
      return bk.room === state.room && bk.status !== "cancelled" && bk.checkin <= b && bk.checkout > a;
    });
    inRange.forEach(function (bk) {
      var box = el("div", "bk " + (bk.status === "confirmed" ? "bk--confirmed" : "bk--pending"));
      var top = el("div", "bk__top");
      top.appendChild(el("span", "bk__name", bk.name || "이름 없음"));
      var src = srcOfBooking(bk);
      var srcBadge = el("span", "bk__src", src.label);
      srcBadge.style.background = src.color;
      top.appendChild(srcBadge);
      top.appendChild(el("span", "bk__state bk__state--" + bk.status, bk.status === "confirmed" ? "확정" : "승인 대기"));
      box.appendChild(top);
      box.appendChild(el("p", "bk__msg", dateKo(bk.checkin) + " → " + dateKo(bk.checkout) + " · " +
        (bk.phone || "연락처 없음") + " · " + money(bk.total)));
      var amenBox = amenityRow(bk);
      if (amenBox) box.appendChild(amenBox);
      var acts = el("div", "bk__acts");
      if (bk.status === "pending") {
        var ok = el("button", "btn btn--ok btn--sm", "예약 확정");
        ok.addEventListener("click", function () { setStatus(bk.id, "confirmed"); closeSheet(); });
        acts.appendChild(ok);
      }
      var chatBtn = el("button", "btn btn--line btn--sm", "💬 대화");
      chatBtn.addEventListener("click", function () { openChatSheet(bk); });
      acts.appendChild(chatBtn);
      if (bk.status === "confirmed") {
        var send = el("button", "btn btn--line btn--sm", "🔑 입실 안내");
        send.addEventListener("click", function () { openCheckinSheet(bk); });
        acts.appendChild(send);
      }
      var cancel = el("button", "btn btn--danger btn--sm", "예약 취소");
      cancel.addEventListener("click", function () {
        if (window.confirm("이 예약을 취소할까요? 해당 날짜가 다시 열립니다.")) {
          setStatus(bk.id, "cancelled");
          closeSheet();
        }
      });
      acts.appendChild(cancel);
      box.appendChild(acts);
      body.appendChild(box);
    });

    /* 외부 예약 / 차단 — 출처별 색상으로 달력에 표시된다 */
    var srcRow = el("div", "sheet__row sheet__row--wrap");
    [
      ["naver", "네이버 예약 (초록)"],
      ["airbnb", "에어비앤비 (파랑)"],
      ["other", "기타 차단 (회색)"]
    ].forEach(function (pair) {
      var srcBtn = el("button", "btn btn--src", pair[1]);
      srcBtn.style.borderColor = SOURCE[pair[0]].color;
      srcBtn.style.color = SOURCE[pair[0]].color;
      srcBtn.addEventListener("click", function () {
        var updates = {};
        dateRange(a, b).forEach(function (d) {
          updates[PATH + "/blocks/" + state.room + "/" + d] = {
            source: pair[0], reason: "external", createdAt: Date.now()
          };
        });
        db.ref().update(updates).then(function () { toast(n + "일 " + SOURCE[pair[0]].label + "으로 막았습니다."); closeSheet(); },
          function () { toast("저장하지 못했습니다. 연결을 확인해 주세요."); });
      });
      srcRow.appendChild(srcBtn);
    });
    var btnUnblock = el("button", "btn btn--line", "차단 해제");
    btnUnblock.addEventListener("click", function () {
      var updates = {}, kept = 0;
      dateRange(a, b).forEach(function (d) {
        var cur = state.blocks[state.room] && state.blocks[state.room][d];
        if (isBookingBlock(cur)) { kept++; return; }
        updates[PATH + "/blocks/" + state.room + "/" + d] = null;
      });
      if (!Object.keys(updates).length) {
        toast("확정 예약으로 막힌 날짜입니다. 예약을 취소하면 열립니다.");
        return;
      }
      db.ref().update(updates).then(function () {
        toast(kept ? "차단을 해제했습니다. (확정 예약 " + kept + "일은 그대로)" : "차단을 해제했습니다.");
        closeSheet();
      }, function () { toast("해제하지 못했습니다."); });
    });
    body.appendChild(el("div", "sheet__divider"));
    body.appendChild(el("p", "sheet__h", "외부 예약·차단 등록"));
    body.appendChild(srcRow);
    body.appendChild(btnUnblock);

    /* 요금 — 날짜(또는 드래그한 구간)의 1박 요금을 직접 수정 */
    body.appendChild(el("div", "sheet__divider"));
    body.appendChild(el("p", "sheet__h", "1박 요금 수정"));
    var nrMap = (state.settings && state.settings.naverRates && state.settings.naverRates[state.room]) || {};
    var naverRate = Number(nrMap[a]) || 0;
    var tiers = (state.settings && state.settings.rates && state.settings.rates[state.room]) || DEFAULT_RATES[state.room];
    var dow = parseD(a).getDay();
    var baseRate = Number(dow === 6 ? tiers.sat : dow === 5 ? tiers.fri : tiers.wd) || DEFAULT_RATES[state.room].wd;
    var cur = rateOf(state.room, a);
    var curSource = isOverride(state.room, a) ? "직접 지정" : (naverRate ? "네이버 실판매" : "기본 요금");

    var priceWrap = el("div", "sheet__field");
    priceWrap.appendChild(el("span", null, a === b ? "이 날짜의 1박 요금 (원)" : n + "일 각각의 1박 요금 (원)"));
    var input = document.createElement("input");
    input.type = "number";
    input.step = "10000";
    input.min = "0";
    input.value = String(cur);
    priceWrap.appendChild(input);
    body.appendChild(priceWrap);

    var info = el("p", "sheet__price-info",
      "현재 적용: " + curSource + " " + money(cur) +
      " · 네이버 실판매 " + (naverRate ? money(naverRate) : "없음") +
      " · 기본 " + money(baseRate));
    body.appendChild(info);

    var row = el("div", "sheet__row sheet__row--wrap");
    var savePrice = el("button", "btn btn--dark", "요금 적용");
    savePrice.addEventListener("click", function () {
      var val = parseInt(String(input.value).replace(/[^0-9]/g, ""), 10);
      if (!val || val < 0) return toast("요금을 입력해 주세요.");
      var updates = {};
      dateRange(a, b).forEach(function (d) { updates[PATH + "/settings/overrides/" + state.room + "/" + d] = val; });
      db.ref().update(updates).then(function () {
        toast(n + "일 요금을 " + money(val) + "로 저장했습니다.");
        closeSheet();
      }, function () { toast("요금을 저장하지 못했습니다."); });
    });
    var resetPrice = el("button", "btn btn--line", "지정 해제 (자동 요금)");
    resetPrice.addEventListener("click", function () {
      var updates = {};
      dateRange(a, b).forEach(function (d) { updates[PATH + "/settings/overrides/" + state.room + "/" + d] = null; });
      db.ref().update(updates).then(function () {
        toast("직접 지정을 해제했습니다. 네이버 실판매(없으면 기본) 요금이 적용됩니다.");
        closeSheet();
      }, function () { toast("변경하지 못했습니다."); });
    });
    row.appendChild(savePrice);
    row.appendChild(resetPrice);
    body.appendChild(row);

    /* 수동 예약 등록 */
    body.appendChild(el("div", "sheet__divider"));
    var manual = el("button", "btn btn--dark", "+ 이 기간 수동 예약 등록");
    manual.addEventListener("click", function () { openManualSheet(a, b); });
    body.appendChild(manual);

    sheet.hidden = false;
  }

  function closeSheet() {
    var sheet = $("#sheet");
    if (sheet) sheet.hidden = true;
    state.sel = null;
    renderCalendar();
  }

  function openManualSheet(a, b) {
    var sheet = $("#sheet");
    var title = $("#sheetTitle");
    var sub = $("#sheetSub");
    var body = $("#sheetBody");
    if (!sheet || !body) return;
    if (title) title.textContent = "수동 예약 등록";
    if (sub) sub.textContent = ROOM_NAME[state.room];
    body.textContent = "";

    function field(label, type, value, ph) {
      var wrap = el("label", "sheet__field");
      wrap.appendChild(el("span", null, label));
      var inp = document.createElement("input");
      inp.type = type;
      inp.value = value || "";
      if (ph) inp.placeholder = ph;
      wrap.appendChild(inp);
      body.appendChild(wrap);
      return inp;
    }
    var row1 = el("div", "sheet__row");
    var ciWrap = el("label", "sheet__field");
    ciWrap.appendChild(el("span", null, "체크인"));
    var ci = document.createElement("input");
    ci.type = "date";
    ci.value = a;
    ciWrap.appendChild(ci);
    var coWrap = el("label", "sheet__field");
    coWrap.appendChild(el("span", null, "체크아웃"));
    var co = document.createElement("input");
    co.type = "date";
    co.value = b === a ? ymd(addDays(parseD(a), 1)) : ymd(addDays(parseD(b), 1));
    coWrap.appendChild(co);
    row1.appendChild(ciWrap);
    row1.appendChild(coWrap);
    body.appendChild(row1);

    var name = field("예약자 이름", "text", "", "예: 홍길동");
    var phone = field("연락처", "tel", "", "010-0000-0000");
    var guests = field("인원 (성인 기준)", "number", "2");
    var memo = field("메모", "text", "", "에어비앤비 예약 등");

    var stWrap = el("label", "sheet__field");
    stWrap.appendChild(el("span", null, "출처"));
    var srcSel = document.createElement("select");
    [["direct", "직접 예약 (차콜)"], ["naver", "네이버 예약 (초록)"], ["airbnb", "에어비앤비 (파랑)"]].forEach(function (opt) {
      var o = document.createElement("option");
      o.value = opt[0];
      o.textContent = opt[1];
      srcSel.appendChild(o);
    });
    stWrap.appendChild(srcSel);
    body.appendChild(stWrap);

    var stWrap2 = el("label", "sheet__field");
    stWrap2.appendChild(el("span", null, "상태"));
    var select = document.createElement("select");
    [["confirmed", "확정 (날짜 마감)"], ["pending", "승인 대기"]].forEach(function (opt) {
      var o = document.createElement("option");
      o.value = opt[0];
      o.textContent = opt[1];
      select.appendChild(o);
    });
    stWrap2.appendChild(select);
    body.appendChild(stWrap2);

    var save = el("button", "btn btn--dark", "등록하기");
    save.addEventListener("click", function () {
      if (!ci.value || !co.value || ci.value >= co.value) return toast("체크인·체크아웃 날짜를 확인해 주세요.");
      var n = daysBetween(ci.value, co.value);
      var price = 0;
      dateRange(ci.value, ymd(addDays(parseD(co.value), -1))).forEach(function (d) { price += rateOf(state.room, d); });
      var payload = {
        room: state.room,
        checkin: ci.value,
        checkout: co.value,
        nights: n,
        adults: parseInt(guests.value, 10) || 2,
        children: 0,
        infants: 0,
        name: name.value.trim() || "수동 등록",
        phone: phone.value.trim(),
        email: "",
        message: memo.value.trim(),
        total: price,
        currency: "KRW",
        status: select.value,
        source: srcSel.value,
        createdAt: Date.now()
      };
      var newRef = db.ref(PATH + "/bookings").push(payload, function (err) {
        if (err) return toast("등록하지 못했습니다.");
        syncBookingBlocks(Object.assign({ id: newRef.key }, payload), payload.status);
        toast("수동 예약을 등록했습니다.");
        closeSheet();
      });
    });
    body.appendChild(save);
    var cancel = el("button", "btn btn--line", "취소");
    cancel.addEventListener("click", function () { closeSheet(); });
    body.appendChild(cancel);
    sheet.hidden = false;
  }

  /* 확정 예약은 공개 달력(/blocks)에도 '예약' 사유로 기록해
     예약자 개인정보(/bookings)를 공개하지 않고도 날짜가 막히게 한다. */
  function bookingNights(bk) {
    if (!bk || !bk.checkin || !bk.checkout) return [];
    return dateRange(bk.checkin, ymd(addDays(parseD(bk.checkout), -1)));
  }
  function isBookingBlock(b) {
    return !!(b && (b.reason === "booking" || b.byBooking));
  }
  function syncBookingBlocks(bk, status) {
    if (!db || !bk || !bk.room) return;
    var updates = {};
    bookingNights(bk).forEach(function (d) {
      var cur = (state.blocks && state.blocks[bk.room] && state.blocks[bk.room][d]) || null;
      if (status === "confirmed") {
        if (!cur || isBookingBlock(cur)) {
          updates[PATH + "/blocks/" + bk.room + "/" + d] = {
            reason: "booking", byBooking: true,
            source: bk.source || "direct", summary: "Reserved", updatedAt: Date.now()
          };
        }
      } else if (isBookingBlock(cur)) {
        updates[PATH + "/blocks/" + bk.room + "/" + d] = null;
      }
    });
    if (!Object.keys(updates).length) return;
    db.ref().update(updates).then(function () {}, function () {
      toast("예약 날짜 마감 표시를 저장하지 못했습니다.");
    });
  }

  function setStatus(id, status) {
    if (!db) return;
    var raw = state.bookings && state.bookings[id];
    var bk = raw ? Object.assign({ id: id }, raw) : null;
    db.ref(PATH + "/bookings/" + id + "/status").set(status).then(function () {
      syncBookingBlocks(bk, status);
      toast(status === "confirmed" ? "예약을 확정했습니다." : "예약을 취소했습니다.");
    }, function () { toast("변경하지 못했습니다."); });
  }

  /* ---------- bookings tab ---------- */
  function renderBookings() {
    var list = $("#bookingList");
    var empty = $("#bookingEmpty");
    if (!list) return;
    list.textContent = "";
    var rows = bookingsArr().sort(function (a, b) { return (b.createdAt || 0) - (a.createdAt || 0); });
    if (state.filter !== "all") rows = rows.filter(function (b) { return b.status === state.filter; });
    if (empty) empty.hidden = rows.length > 0;

    rows.forEach(function (b) {
      var card = el("article", "bk bk--" + (b.status || "pending"));
      var top = el("div", "bk__top");
      top.appendChild(el("span", "bk__name", b.name || "이름 없음"));
      top.appendChild(el("span", "bk__room", ROOM_NAME[b.room] || b.room));
      var stateLabel = { pending: "승인 대기", confirmed: "확정", cancelled: "취소" }[b.status] || b.status;
      var src = srcOfBooking(b);
      var srcBadge = el("span", "bk__src", src.label);
      srcBadge.style.background = src.color;
      top.appendChild(srcBadge);
      top.appendChild(el("span", "bk__state bk__state--" + b.status, stateLabel));
      card.appendChild(top);

      var grid = el("div", "bk__grid");
      function cell(k, v) {
        var d = el("div", null, k);
        d.appendChild(el("b", null, v));
        grid.appendChild(d);
      }
      cell("기간", dateKo(b.checkin) + " → " + dateKo(b.checkout));
      cell("숙박", (b.nights || daysBetween(b.checkin, b.checkout)) + "박");
      cell("인원", "성인 " + (b.adults || 0) + " · 아동 " + (b.children || 0) + " · 유아 " + (b.infants || 0));
      cell("합계", money(b.total));
      cell("접수", ts(b.createdAt));
      cell("접수 번호", b.id.slice(-6).toUpperCase());
      card.appendChild(grid);

      var contact = el("div", "bk__acts");
      if (b.phone) {
        var call = document.createElement("a");
        call.className = "btn btn--line btn--sm";
        call.href = "tel:" + String(b.phone).replace(/[^0-9+]/g, "");
        call.textContent = "전화 " + b.phone;
        contact.appendChild(call);
        var copy = el("button", "btn btn--line btn--sm", "번호 복사");
        copy.addEventListener("click", function () {
          var t = String(b.phone);
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(t).then(function () { toast("번호를 복사했습니다."); });
          } else {
            var ta = document.createElement("textarea");
            ta.value = t;
            document.body.appendChild(ta);
            ta.select();
            try { document.execCommand("copy"); toast("번호를 복사했습니다."); } catch (e) {}
            document.body.removeChild(ta);
          }
        });
        contact.appendChild(copy);
      }
      if (b.email) {
        var mail = document.createElement("a");
        mail.className = "btn btn--line btn--sm";
        mail.href = "mailto:" + b.email;
        mail.textContent = b.email;
        contact.appendChild(mail);
      }
      card.appendChild(contact);

      if (b.message) card.appendChild(el("p", "bk__msg", b.message));
      var amen = amenityRow(b);
      if (amen) card.appendChild(amen);

      var memoRow = el("div", "bk__memo");
      var memo = document.createElement("textarea");
      memo.placeholder = "메모 (입금 확인, 도착 시간 등)";
      memo.value = b.memo || "";
      memoRow.appendChild(memo);
      var saveMemo = el("button", "btn btn--line btn--sm", "메모 저장");
      saveMemo.addEventListener("click", function () {
        db.ref(PATH + "/bookings/" + b.id + "/memo").set(memo.value).then(function () { toast("메모를 저장했습니다."); });
      });
      memoRow.appendChild(saveMemo);
      card.appendChild(memoRow);

      var acts = el("div", "bk__acts");
      if (b.status === "pending") {
        var ok = el("button", "btn btn--ok btn--sm", "예약 확정");
        ok.addEventListener("click", function () { setStatus(b.id, "confirmed"); });
        acts.appendChild(ok);
      }
      var openChat = el("button", "btn btn--line btn--sm", "💬 대화창 열기");
      openChat.addEventListener("click", function () { openChatSheet(b); });
      acts.appendChild(openChat);
      if (b.status === "confirmed") {
        var send = el("button", "btn btn--line btn--sm", "입실 안내 보내기");
        send.addEventListener("click", function () { openCheckinSheet(b); });
        acts.appendChild(send);
      }
      if (b.status !== "cancelled") {
        var cancel = el("button", "btn btn--danger btn--sm", "예약 취소");
        cancel.addEventListener("click", function () {
          if (window.confirm("이 예약을 취소할까요? 해당 날짜가 다시 열립니다.")) setStatus(b.id, "cancelled");
        });
        acts.appendChild(cancel);
      } else {
        var restore = el("button", "btn btn--line btn--sm", "대기로 되돌리기");
        restore.addEventListener("click", function () { setStatus(b.id, "pending"); });
        acts.appendChild(restore);
      }
      card.appendChild(acts);
      list.appendChild(card);
    });

    var pending = bookingsArr().filter(function (b) { return b.status === "pending"; }).length;
    var badge = $("#pendingBadge");
    if (badge) {
      badge.textContent = String(pending);
      badge.hidden = pending === 0;
    }
  }

  /* ---------- rates tab ---------- */
  function renderRates() {
    var wrap = $("#rateCards");
    if (!wrap) return;
    var keep = {};
    $$(".ratecard input", wrap).forEach(function (inp) {
      keep[inp.getAttribute("data-room") + "-" + inp.getAttribute("data-tier")] = inp.value;
    });
    wrap.textContent = "";
    ["heyum", "orot"].forEach(function (room) {
      var r = (state.settings && state.settings.rates && state.settings.rates[room]) || DEFAULT_RATES[room];
      var card = el("div", "ratecard");
      card.appendChild(el("h3", null, ROOM_NAME[room]));
      [["wd", "평일 (일~목)"], ["fri", "금요일"], ["sat", "토요일"]].forEach(function (tier) {
        var label = el("label");
        label.appendChild(el("span", null, tier[1]));
        var inp = document.createElement("input");
        inp.type = "number";
        inp.step = "10000";
        inp.min = "0";
        inp.setAttribute("data-room", room);
        inp.setAttribute("data-tier", tier[0]);
        var saved = keep[room + "-" + tier[0]];
        inp.value = saved !== undefined && saved !== "" ? saved : String(r[tier[0]]);
        label.appendChild(inp);
        card.appendChild(label);
      });
      wrap.appendChild(card);
    });

    var ovList = $("#overrideList");
    if (ovList) {
      ovList.textContent = "";
      var ov = (state.settings && state.settings.overrides) || {};
      var rows = [];
      ["heyum", "orot"].forEach(function (room) {
        Object.keys(ov[room] || {}).forEach(function (date) {
          if (Number(ov[room][date]) > 0) rows.push({ room: room, date: date, price: Number(ov[room][date]) });
        });
      });
      rows.sort(function (a, b) { return a.date < b.date ? -1 : 1; });
      if (!rows.length) ovList.appendChild(el("p", "hint", "특정일 요금이 없습니다. 달력에서 날짜를 선택해 지정할 수 있습니다."));
      rows.forEach(function (row) {
        var line = el("div", "ovr__row");
        line.appendChild(el("b", null, row.date));
        line.appendChild(el("span", null, ROOM_NAME[row.room] + " · " + money(row.price)));
        var del = el("button", null, "삭제");
        del.addEventListener("click", function () {
          db.ref(PATH + "/settings/overrides/" + row.room + "/" + row.date).set(null).then(function () {
            toast("특정일 요금을 삭제했습니다.");
          });
        });
        line.appendChild(del);
        ovList.appendChild(line);
      });
    }
  }

  function saveRates() {
    if (!db) return;
    var payload = { heyum: {}, orot: {} };
    var bad = false;
    $$(".ratecard input").forEach(function (inp) {
      var room = inp.getAttribute("data-room");
      var tier = inp.getAttribute("data-tier");
      var val = parseInt(String(inp.value).replace(/[^0-9]/g, ""), 10);
      if (!val) bad = true;
      payload[room][tier] = val || 0;
    });
    if (bad) return toast("모든 요금을 입력해 주세요.");
    db.ref(PATH + "/settings/rates").set(payload).then(function () { toast("요금을 저장했습니다."); },
      function () { toast("저장하지 못했습니다."); });
  }

  /* ---------- settings ---------- */
  function renderMeta() {
    var b = bookingsArr();
    var blocks = 0;
    Object.keys(state.blocks).forEach(function (room) { blocks += Object.keys(state.blocks[room] || {}).length; });
    var mb = $("#metaBookings");
    if (mb) mb.textContent = b.length + "건 (대기 " + b.filter(function (x) { return x.status === "pending"; }).length +
      " · 확정 " + b.filter(function (x) { return x.status === "confirmed"; }).length + ")";
    var mk = $("#metaBlocks");
    if (mk) mk.textContent = blocks + "일";
    var mc = $("#metaCommunity");
    if (mc) {
      var rv = reviewsArr("heyum").length + reviewsArr("orot").length;
      var iq = inquiriesArr().length;
      var open = inquiriesArr().filter(function (q) { return !String(q.answerKo || "").trim(); }).length;
      mc.textContent = "리뷰 " + rv + " · 문의 " + iq + " (미답변 " + open + ")";
    }
    var ms = $("#metaSync");
    if (ms) ms.textContent = state.lastSync ? ts(state.lastSync) : "—";
  }

  /* ---------- reviews ---------- */
  function reviewsArr(room) {
    var raw = state.reviews[room] || {};
    return Object.keys(raw).map(function (id) {
      var r = raw[id] || {};
      r.id = id;
      return r;
    }).sort(function (a, b) { return (Number(b.createdAt) || 0) - (Number(a.createdAt) || 0); });
  }
  function starsOf(n) {
    var v = Math.max(0, Math.min(5, Math.round(Number(n) || 0)));
    return "★★★★★".slice(0, v) + "☆☆☆☆☆".slice(0, 5 - v);
  }

  function renderReviews() {
    var list = $("#reviewList");
    var empty = $("#reviewEmpty");
    if (!list) return;
    list.textContent = "";
    var rows = reviewsArr(state.reviewRoom);
    if (empty) empty.hidden = rows.length > 0;
    rows.forEach(function (r) {
      var card = el("article", "bk bk--review");
      var top = el("div", "bk__top");
      top.appendChild(el("span", "bk__name", r.name || "이름 없음"));
      top.appendChild(el("span", "bk__stars", starsOf(r.rating)));
      var lang = String(r.lang || "ko");
      top.appendChild(el("span", "bk__state", lang === "ko" ? "한국어" : lang.toUpperCase()));
      top.appendChild(el("span", "bk__state", ts(r.createdAt)));
      if (r.source === "guest") top.appendChild(el("span", "bk__state bk__state--pending", "고객 작성"));
      card.appendChild(top);

      var body = el("p", "bk__msg bk__msg--text", String(r.textKo || r.text || ""));
      card.appendChild(body);
      if (r.text && r.textKo && r.text !== r.textKo) {
        card.appendChild(el("p", "bk__orig", "원문: " + r.text));
      }

      var acts = el("div", "bk__acts");
      var edit = el("button", "btn btn--line btn--sm", "수정");
      edit.addEventListener("click", function () { openReviewSheet(state.reviewRoom, r); });
      acts.appendChild(edit);
      var del = el("button", "btn btn--danger btn--sm", "삭제");
      del.addEventListener("click", function () {
        if (!window.confirm("이 리뷰를 삭제할까요? 홈페이지에서도 바로 사라집니다.")) return;
        db.ref(PATH + "/reviews/" + state.reviewRoom + "/" + r.id).remove().then(function () { toast("리뷰를 삭제했습니다."); },
          function () { toast("삭제하지 못했습니다."); });
      });
      acts.appendChild(del);
      card.appendChild(acts);
      list.appendChild(card);
    });

    var total = 0;
    ["heyum", "orot"].forEach(function (r) { total += reviewsArr(r).length; });
    var badge = $("#reviewBadge");
    if (badge) { badge.textContent = String(total); badge.hidden = total === 0; }
  }

  function openReviewSheet(room, review) {
    var sheet = $("#sheet");
    var title = $("#sheetTitle");
    var sub = $("#sheetSub");
    var body = $("#sheetBody");
    if (!sheet || !body) return;
    var isEdit = !!(review && review.id);
    if (title) title.textContent = isEdit ? "리뷰 수정" : "리뷰 직접 등록";
    if (sub) sub.textContent = ROOM_NAME[room] + (isEdit ? "" : " · 홈페이지에 바로 표시");
    body.textContent = "";

    var nameWrap = el("label", "sheet__field");
    nameWrap.appendChild(el("span", null, "작성자 이름"));
    var nameInp = document.createElement("input");
    nameInp.type = "text";
    nameInp.value = (review && review.name) || "";
    nameInp.placeholder = "예: 김민수";
    nameWrap.appendChild(nameInp);
    body.appendChild(nameWrap);

    var rateWrap = el("label", "sheet__field");
    rateWrap.appendChild(el("span", null, "별점"));
    var rateSel = document.createElement("select");
    [5, 4, 3, 2, 1].forEach(function (n) {
      var o = document.createElement("option");
      o.value = String(n);
      o.textContent = starsOf(n) + " (" + n + ")";
      if (Number((review && review.rating) || 5) === n) o.selected = true;
      rateSel.appendChild(o);
    });
    rateWrap.appendChild(rateSel);
    body.appendChild(rateWrap);

    var textWrap = el("label", "sheet__field");
    textWrap.appendChild(el("span", null, "후기 내용 (한국어)"));
    var ta = document.createElement("textarea");
    ta.rows = 6;
    ta.value = (review && (review.textKo || review.text)) || "";
    ta.placeholder = "후기 내용을 적어 주세요";
    textWrap.appendChild(ta);
    body.appendChild(textWrap);

    var save = el("button", "btn btn--dark", isEdit ? "수정 저장" : "등록하기");
    save.addEventListener("click", function () {
      var name = nameInp.value.trim();
      var text = ta.value.trim();
      if (!name) return toast("이름을 입력해 주세요.");
      if (text.length < 5) return toast("후기 내용을 5자 이상 적어 주세요.");
      var payload = {
        name: name,
        rating: Number(rateSel.value) || 5,
        text: text,
        textKo: text,
        lang: "ko",
        source: "host",
        updatedAt: Date.now()
      };
      var ref = isEdit ? db.ref(PATH + "/reviews/" + room + "/" + review.id) : db.ref(PATH + "/reviews/" + room).push();
      if (!isEdit) payload.createdAt = Date.now();
      ref.update(payload).then(function () { toast(isEdit ? "리뷰를 수정했습니다." : "리뷰를 등록했습니다."); closeSheet(); },
        function () { toast("저장하지 못했습니다."); });
    });
    body.appendChild(save);
    var cancel = el("button", "btn btn--line", "닫기");
    cancel.addEventListener("click", closeSheet);
    body.appendChild(cancel);
    sheet.hidden = false;
  }

  /* ---------- inquiries ---------- */
  function inquiriesArr() {
    return Object.keys(state.inquiries).map(function (id) {
      var q = state.inquiries[id] || {};
      q.id = id;
      return q;
    }).sort(function (a, b) { return (Number(b.createdAt) || 0) - (Number(a.createdAt) || 0); });
  }

  function renderInquiries() {
    var list = $("#inquiryList");
    var empty = $("#inquiryEmpty");
    if (!list) return;
    list.textContent = "";
    var all = inquiriesArr();
    var rows = all.filter(function (q) {
      if (state.inqFilter === "open") return !String(q.answerKo || "").trim();
      if (state.inqFilter === "answered") return !!String(q.answerKo || "").trim();
      return true;
    });
    if (empty) empty.hidden = rows.length > 0;

    rows.forEach(function (q) {
      var card = el("article", "bk bk--inq");
      var top = el("div", "bk__top");
      top.appendChild(el("span", "bk__name", q.name || "이름 없음"));
      var lang = String(q.lang || "");
      if (lang && lang !== "ko") top.appendChild(el("span", "bk__state", lang.toUpperCase()));
      if (q.room && ROOM_NAME[q.room]) top.appendChild(el("span", "bk__state", ROOM_NAME[q.room]));
      top.appendChild(el("span", "bk__state", ts(q.createdAt)));
      top.appendChild(el("span", "bk__state " + (String(q.answerKo || "").trim() ? "bk__state--confirmed" : "bk__state--pending"),
        String(q.answerKo || "").trim() ? "답변완료" : "미답변"));
      card.appendChild(top);

      var orig = el("p", "bk__msg bk__msg--text", String(q.text || ""));
      card.appendChild(orig);
      if (q.textKo && q.textKo !== q.text) {
        var koBox = el("div", "bk__trans");
        koBox.appendChild(el("span", "bk__trans-k", "한국어 번역"));
        koBox.appendChild(el("p", "bk__msg bk__msg--text", String(q.textKo)));
        card.appendChild(koBox);
      } else if (lang && lang !== "ko") {
        var transBtn = el("button", "btn btn--line btn--sm", "한국어로 번역");
        transBtn.addEventListener("click", function () {
          transBtn.disabled = true;
          transBtn.textContent = "번역 중…";
          if (!window.NNS) { transBtn.textContent = "번역을 사용할 수 없습니다"; return; }
          window.NNS.translate(String(q.text || ""), "ko", function (err, res) {
            transBtn.disabled = false;
            if (err || !res || !res.text) { transBtn.textContent = "번역 실패 (다시 시도)"; return; }
            var box = el("div", "bk__trans");
            box.appendChild(el("span", "bk__trans-k", "한국어 번역"));
            box.appendChild(el("p", "bk__msg bk__msg--text", res.text));
            card.insertBefore(box, card.querySelector(".bk__acts"));
            transBtn.hidden = true;
            db.ref(PATH + "/inquiries/" + q.id + "/textKo").set(res.text);
          });
        });
        card.appendChild(transBtn);
      }

      if (q.contact) {
        var contact = el("div", "bk__acts");
        contact.appendChild(el("span", "bk__contact", "연락처: " + q.contact));
        var copyC = el("button", "btn btn--line btn--sm", "복사");
        copyC.addEventListener("click", function () {
          if (navigator.clipboard) navigator.clipboard.writeText(String(q.contact)).then(function () { toast("복사했습니다."); });
        });
        contact.appendChild(copyC);
        if (/@/.test(String(q.contact))) {
          var mail = document.createElement("a");
          mail.className = "btn btn--line btn--sm";
          mail.href = "mailto:" + q.contact;
          mail.textContent = "메일";
          contact.appendChild(mail);
        }
        card.appendChild(contact);
      }

      var ansWrap = el("div", "bk__memo");
      var ans = document.createElement("textarea");
      ans.placeholder = "답변 (한국어로 작성하면 고객 화면에서 그 나라 언어로 번역됩니다)";
      ans.rows = 3;
      ans.value = String(q.answerKo || "");
      ansWrap.appendChild(ans);
      card.appendChild(ansWrap);

      var acts = el("div", "bk__acts");
      var save = el("button", "btn btn--ok btn--sm", "답변 저장");
      save.addEventListener("click", function () {
        var text = ans.value.trim();
        if (!text) return toast("답변 내용을 적어 주세요.");
        db.ref(PATH + "/inquiries/" + q.id).update({
          answerKo: text,
          answeredAt: Date.now(),
          status: "answered"
        }).then(function () { toast("답변을 저장했습니다."); }, function () { toast("저장하지 못했습니다."); });
      });
      acts.appendChild(save);

      if (String(q.answerKo || "").trim() && lang && lang !== "ko" && window.NNS) {
        var prev = el("button", "btn btn--line btn--sm", "고객 언어로 미리보기");
        prev.addEventListener("click", function () {
          prev.disabled = true;
          prev.textContent = "번역 중…";
          window.NNS.translate(String(q.answerKo), lang === "zh-cn" ? "zh-cn" : lang === "zh-tw" ? "zh-tw" : lang, function (err, res) {
            prev.disabled = false;
            prev.textContent = "고객 언어로 미리보기";
            if (err || !res) return toast("번역하지 못했습니다.");
            window.alert("고객 화면 표시 (" + lang + ")\n\n" + res.text);
          });
        });
        acts.appendChild(prev);
      }

      var del = el("button", "btn btn--danger btn--sm", "문의 삭제");
      del.addEventListener("click", function () {
        if (!window.confirm("이 문의를 삭제할까요? 홈페이지에서도 사라집니다.")) return;
        db.ref(PATH + "/inquiries/" + q.id).remove().then(function () { toast("문의를 삭제했습니다."); },
          function () { toast("삭제하지 못했습니다."); });
      });
      acts.appendChild(del);
      card.appendChild(acts);
      list.appendChild(card);
    });

    var open = all.filter(function (q) { return !String(q.answerKo || "").trim(); }).length;
    var badge = $("#inquiryBadge");
    if (badge) { badge.textContent = String(open); badge.hidden = open === 0; }
  }

  /* ---------- check-in message ---------- */
  function templateFor(room) {
    var t = state.settings && state.settings.checkinTemplates;
    var tpl = t && typeof t[room] === "string" ? t[room] : "";
    return tpl || DEFAULT_TEMPLATES[room] || DEFAULT_TEMPLATES.heyum;
  }
  function bankLine() {
    var b = state.settings && state.settings.bank;
    if (!b) return "";
    return [b.bank, b.account, b.holder].filter(Boolean).join(" ");
  }
  function fillTemplate(tpl, bk) {
    var room = bk.room || "heyum";
    var n = Number(bk.nights) || daysBetween(bk.checkin, bk.checkout);
    var guests = (Number(bk.adults) || 0) + (Number(bk.children) || 0);
    var map = {
      "{name}": String(bk.name || ""),
      "{checkin}": dateKo(bk.checkin),
      "{checkout}": dateKo(bk.checkout),
      "{room}": ROOM_NAME[room] || room,
      "{nights}": String(n),
      "{guests}": String(guests),
      "{account}": bankLine(),
      "{amenities}": amenityLabels(bk).join(", ") || "없음",
      "{phone}": PHONE,
      "{doorlock}": "○○○○",
      "{roomlock}": "○○○○"
    };
    return String(tpl).replace(/\{[a-z]+\}/g, function (m) { return map[m] !== undefined ? map[m] : m; });
  }

  /* ---------- booking chat (host) ---------- */
  function openChatSheet(bk) {
    var sheet = $("#sheet");
    var title = $("#sheetTitle");
    var sub = $("#sheetSub");
    var body = $("#sheetBody");
    if (!sheet || !body) return;
    if (title) title.textContent = "대화 · " + (bk.name || "예약자");
    if (sub) sub.textContent = (ROOM_NAME[bk.room] || bk.room) + " · " + dateKo(bk.checkin) + " → " + dateKo(bk.checkout) +
      " · " + ({ pending: "승인 대기", confirmed: "확정", cancelled: "취소" }[bk.status] || bk.status);
    body.textContent = "";

    var list = el("ul", "chat chat--host");
    body.appendChild(list);
    var empty = el("p", "hint", "아직 메시지가 없습니다. 먼저 인사를 건네 보세요.");
    body.appendChild(empty);

    var wrap = el("div", "sheet__field");
    wrap.appendChild(el("span", null, "메시지 (한국어로 쓰면 게스트 화면에서 자동 번역됩니다)"));
    var ta = document.createElement("textarea");
    ta.rows = 3;
    ta.placeholder = "예: 입실 안내 드립니다. 도착 시간 알려 주세요.";
    wrap.appendChild(ta);
    body.appendChild(wrap);

    var send = el("button", "btn btn--dark", "메시지 보내기");
    var sending = false;
    send.addEventListener("click", function () {
      var text = ta.value.trim();
      if (!text) return toast("메시지를 입력해 주세요.");
      if (sending) return;
      sending = true;
      send.disabled = true;
      db.ref(PATH + "/bookingChats/" + bk.id).push({
        from: "host", text: text, textKo: text, lang: "ko", kind: "message", createdAt: Date.now()
      }, function (err) {
        sending = false;
        send.disabled = false;
        if (err) return toast("메시지를 보내지 못했습니다.");
        ta.value = "";
        toast("메시지를 보냈습니다.");
      });
    });
    body.appendChild(send);

    sheet.hidden = false;

    function renderChat(raw) {
      list.textContent = "";
      var items = Object.keys(raw || {}).map(function (k) { return raw[k] || {}; })
        .sort(function (a, b) { return (a.createdAt || 0) - (b.createdAt || 0); });
      items.forEach(function (m) {
        var mine = m.from === "host";
        var li = el("li", "chat__item " + (mine ? "is-host" : "is-me"));
        if (m.kind === "checkin") li.classList.add("is-checkin");
        var head = el("div", "chat__head");
        head.appendChild(document.createTextNode(mine ? "호스트(나)" : (bk.name || "게스트")));
        head.appendChild(el("span", "chat__when", ts(m.createdAt)));
        if (m.kind === "checkin") head.appendChild(el("span", "chat__kind", "CHECK-IN"));
        li.appendChild(head);
        li.appendChild(el("p", "chat__text", String(m.textKo || m.text || "")));
        if (!mine && m.lang && m.lang !== "ko" && m.textKo && m.textKo !== m.text) {
          li.appendChild(el("p", "bk__orig", "원문: " + m.text));
        }
        list.appendChild(li);
      });
      empty.hidden = items.length > 0;
    }

    var chatRef = db.ref(PATH + "/bookingChats/" + bk.id);
    var handler = function (snap) { renderChat(snap.val()); };
    chatRef.on("value", handler, function () {});
    var closeBtn = $("#sheetClose");
    function cleanup() {
      try { chatRef.off("value", handler); } catch (e) { /* noop */ }
      if (closeBtn) closeBtn.removeEventListener("click", cleanup);
    }
    if (closeBtn) closeBtn.addEventListener("click", cleanup);
    sheet.addEventListener("click", function once(ev) {
      if (ev.target === sheet) { cleanup(); sheet.removeEventListener("click", once); }
    });
  }

  function openCheckinSheet(bk) {
    var sheet = $("#sheet");
    var title = $("#sheetTitle");
    var sub = $("#sheetSub");
    var body = $("#sheetBody");
    if (!sheet || !body) return;
    if (title) title.textContent = "입실 안내 · " + (bk.name || "예약자");
    if (sub) sub.textContent = (ROOM_NAME[bk.room] || bk.room) + " · " + dateKo(bk.checkin) + " → " + dateKo(bk.checkout);
    body.textContent = "";

    var hint = el("p", "sheet__hint", "도어락 비밀번호(○○○○)는 보안상 저장하지 않습니다. 보내기 전에 직접 채워 주세요.");
    body.appendChild(hint);

    var wrap = el("label", "sheet__field");
    wrap.appendChild(el("span", null, "보낼 안내문 (수정 가능)"));
    var ta = document.createElement("textarea");
    ta.rows = 12;
    ta.value = fillTemplate(templateFor(bk.room || "heyum"), bk);
    wrap.appendChild(ta);
    body.appendChild(wrap);

    var phone = String(bk.phone || "").replace(/[^0-9+]/g, "");
    var sms = document.createElement("a");
    sms.className = "btn btn--dark btn--sm";
    sms.textContent = "문자 앱으로 보내기";
    var mail = document.createElement("a");
    mail.className = "btn btn--line btn--sm";
    mail.textContent = "이메일로 보내기";
    var copy = el("button", "btn btn--line btn--sm", "안내문 복사하기");

    var isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
    function refresh() {
      var text = ta.value;
      sms.href = "sms:" + phone + (isIOS ? "&body=" : "?body=") + encodeURIComponent(text);
      mail.href = "mailto:" + (bk.email || "") + "?subject=" + encodeURIComponent("능놀스테이 입실 안내") +
        "&body=" + encodeURIComponent(text);
      if (!phone) { sms.classList.add("is-off"); sms.removeAttribute("href"); }
      if (!bk.email) { mail.classList.add("is-off"); mail.removeAttribute("href"); }
    }
    ta.addEventListener("input", refresh);
    refresh();

    copy.addEventListener("click", function () {
      var text = ta.value;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function () { toast("안내문을 복사했습니다."); });
      } else {
        ta.select();
        try { document.execCommand("copy"); toast("안내문을 복사했습니다."); } catch (e) { /* noop */ }
      }
    });

    var sendChat = el("button", "btn btn--ok btn--sm", "대화창으로 보내기");
    sendChat.addEventListener("click", function () {
      db.ref(PATH + "/bookingChats/" + bk.id).push({
        from: "host", kind: "checkin", text: ta.value, textKo: ta.value, lang: "ko", createdAt: Date.now()
      }, function (err) {
        if (err) return toast("대화창으로 보내지 못했습니다.");
        toast("입실 안내를 대화창으로 보냈습니다.");
      });
    });

    var row = el("div", "sheet__row sheet__row--wrap");
    row.appendChild(sendChat);
    row.appendChild(sms);
    row.appendChild(mail);
    row.appendChild(copy);
    body.appendChild(row);
    if (!phone && !bk.email) {
      body.appendChild(el("p", "sheet__hint", "이 예약에는 연락처와 이메일이 없습니다. 안내문을 복사해 직접 보내 주세요."));
    }
    sheet.hidden = false;
    window.setTimeout(function () { ta.focus(); }, 60);
  }

  /* ---------- settings forms ---------- */
  function renderSettingsForms() {
    var bank = (state.settings && state.settings.bank) || {};
    var bf = $("#bankForm");
    if (bf && !bf.dataset.filled) {
      bf.elements.bank.value = bank.bank || "";
      bf.elements.account.value = bank.account || "";
      bf.elements.holder.value = bank.holder || "";
      bf.elements.note.value = bank.note || "";
      bf.dataset.filled = "1";
    }
    var cf = $("#checkinForm");
    if (cf && !cf.dataset.filled && state.ready) {
      cf.elements.heyum.value = templateFor("heyum");
      cf.elements.orot.value = templateFor("orot");
      cf.dataset.filled = "1";
    }

    var ical = (state.settings && state.settings.icalSync) || null;
    var synced = $("#icalSynced");
    var hey = $("#icalHeyum");
    var oro = $("#icalOrot");
    var note = $("#icalNote");
    if (synced) synced.textContent = ical && ical.syncedAtText ? ical.syncedAtText + " (에어비앤비 동기화 기준일)" : "아직 동기화 기록이 없습니다";
    if (hey) hey.textContent = ical && ical.rooms && ical.rooms.heyum ? (ical.rooms.heyum.nights + "박 차단 · " + (ical.rooms.heyum.ical || "")) : "—";
    if (oro) oro.textContent = ical && ical.rooms && ical.rooms.orot ? (ical.rooms.orot.nights + "박 차단 · " + (ical.rooms.orot.ical || "")) : "—";
    if (note) note.textContent = ical && ical.note ? ical.note : "에어비앤비 예약·차단 날짜는 달력에 파란색으로 표시됩니다.";

    var nr = (state.settings && state.settings.naverRates) || {};
    var info = $("#naverRateInfo");
    if (info) {
      var h = Object.keys(nr.heyum || {}).length;
      var o = Object.keys(nr.orot || {}).length;
      var at = (state.settings && state.settings.naverRatesUpdatedAt) || "";
      info.textContent = h || o
        ? "헤윰 " + h + "일 · 오롯 " + o + "일 요금 반영" + (at ? " (" + at + ")" : "") + " — 날짜별 실판매 요금이 달력에 그대로 표시됩니다."
        : "아직 날짜별 실판매 요금이 반영되지 않았습니다.";
    }
  }

  /* ---------- render ---------- */
  function renderAll() {
    if (!state.ready && !state.settings) {
      /* 데이터 오기 전에도 잠금 화면 PIN 검증은 가능해야 한다 */
    }
    if (!$("#app") || $("#app").hidden) return;
    renderCalendar();
    renderBookings();
    renderReviews();
    renderInquiries();
    renderRates();
    renderSettingsForms();
    renderMeta();
  }

  function showTab(name) {
    state.tab = name;
    $$(".tabs button").forEach(function (b) {
      b.classList.toggle("is-on", b.getAttribute("data-tab") === name);
    });
    $$(".panel").forEach(function (p) {
      p.classList.toggle("is-on", p.getAttribute("data-panel") === name);
    });
    renderAll();
  }

  /* ---------- 사장님 계정 인증 ---------- */
  var auth = null;
  var connected = false;

  function authMsg(text, kind) {
    var m = $("#authMsg");
    if (!m) return;
    m.textContent = text || "";
    m.className = "lock__msg" + (text ? (kind === "ok" ? " is-ok" : " is-error") : "");
  }

  function showPanel(name) {
    var pin = $("#pinPanel");
    var au = $("#authPanel");
    if (pin) pin.hidden = name !== "pin";
    if (au) au.hidden = name !== "auth";
  }

  function authErrText(err) {
    var c = (err && err.code) || "";
    if (c === "auth/popup-closed-by-user") return "로그인 창을 닫았습니다. 다시 시도해 주세요.";
    if (c === "auth/popup-blocked") return "팝업이 차단되었습니다. 이메일·비밀번호로 로그인해 주세요.";
    if (c === "auth/unauthorized-domain") return "이 주소는 Firebase에 승인되지 않았습니다.";
    if (c === "auth/email-already-in-use") return "이미 계정이 있습니다. [로그인]을 눌러 주세요. 구글로 만든 계정이면 구글 버튼을 씨 주세요.";
    if (c === "auth/wrong-password" || c === "auth/invalid-login-credentials" || c === "auth/invalid-credential") return "이메일 또는 비밀번호가 맞지 않습니다.";
    if (c === "auth/weak-password") return "비밀번호는 6자 이상으로 정해 주세요.";
    if (c === "auth/invalid-email") return "이메일 주소를 확인해 주세요.";
    if (c === "auth/account-exists-with-different-credential") return "같은 이메일이 다른 로그인 방식으로 이미 있습니다.";
    if (c === "auth/operation-not-allowed") return "이 로그인 방식이 아직 켜져 있지 않습니다.";
    if (c === "auth/network-request-failed") return "네트워크 연결을 확인해 주세요.";
    return "로그인하지 못했습니다" + (c ? " (" + c + ")" : "");
  }

  function afterAuth(user) {
    var email = String((user && user.email) || "").toLowerCase();
    var allowed = !!(user && ADMIN_EMAILS.indexOf(email) >= 0 && user.emailVerified);
    var resend = $("#authResend");
    if (resend) resend.hidden = true;
    if (allowed) {
      var out = $("#authOut");
      if (out) out.hidden = true;
      authMsg("");
      showPanel("pin");
      if (!connected) { connected = true; connect(); }
      return;
    }
    showPanel("auth");
    var o = $("#authOut");
    if (o) o.hidden = !user;
    if (!user) { authMsg(""); return; }
    if (ADMIN_EMAILS.indexOf(email) < 0) {
      authMsg("이 계정(" + email + ")은 관리자 계정이 아닙니다. 로그아웃 후 " + ADMIN_EMAIL + " 로 로그인해 주세요.");
    } else {
      authMsg("이메일 인증이 아직 끝나지 않았습니다. " + email + " 받은편지함의 인증 메일 링크를 누른 뒤 새로고침해 주세요.");
      if (resend) resend.hidden = false;
    }
  }

  function bootAuth() {
    loadSdk().then(function () {
      auth = ensureApp().auth();
      auth.onAuthStateChanged(function (user) {
        state.user = user || null;
        afterAuth(user);
      });

      var g = $("#authGoogle");
      if (g) g.addEventListener("click", function () {
        authMsg("");
        var provider = new firebase.auth.GoogleAuthProvider();
        provider.setCustomParameters({ prompt: "select_account" });
        var viaRedirect = function () {
          auth.signInWithRedirect(provider).catch(function (e2) {
            authMsg(authErrText(e2));
            var pin = $("#pinPanel");
            if (pin) pin.hidden = true;
          });
        };
        auth.signInWithPopup(provider).catch(function (err) {
          var c = (err && err.code) || "";
          if (c === "auth/popup-blocked" || c === "auth/operation-not-supported-in-this-environment") { viaRedirect(); return; }
          authMsg(authErrText(err));
        });
      });

      var form = $("#authForm");
      if (form) form.addEventListener("submit", function (ev) {
        ev.preventDefault();
        var email = String(($("#authEmail") || {}).value || "").trim();
        var pass = String(($("#authPass") || {}).value || "");
        if (!email || pass.length < 6) { authMsg("이메일과 6자 이상의 비밀번호를 입력해 주세요."); return; }
        auth.signInWithEmailAndPassword(email, pass).catch(function (err) {
          var c = (err && err.code) || "";
          if (c === "auth/user-not-found" || c === "auth/invalid-login-credentials" || c === "auth/invalid-credential" || c === "auth/wrong-password") {
            authMsg(authErrText(err) + " 처음이라면 [비밀번호 만들기]를 눌러 주세요.");
            return;
          }
          authMsg(authErrText(err));
        });
      });

      var su = $("#authSignup");
      if (su) su.addEventListener("click", function () {
        var email = String(($("#authEmail") || {}).value || "").trim();
        var pass = String(($("#authPass") || {}).value || "");
        if (!email || pass.length < 6) { authMsg("이메일과 6자 이상의 비밀번호를 입력해 주세요."); return; }
        auth.createUserWithEmailAndPassword(email, pass).then(function (cred) {
          var u = cred && cred.user;
          if (u && u.sendEmailVerification) u.sendEmailVerification().catch(function () {});
          authMsg("관리자 계정을 만들었습니다. " + email + " 로 보낸 인증 메일의 링크를 누른 뒤 이 화면을 새로고침해 주세요.", "ok");
        }).catch(function (err) { authMsg(authErrText(err)); });
      });

      var resend = $("#authResend");
      if (resend) resend.addEventListener("click", function () {
        var u = auth.currentUser;
        if (!u || !u.sendEmailVerification) return;
        u.sendEmailVerification().then(function () { authMsg("인증 메일을 다시 보냈습니다.", "ok"); },
          function (e) { authMsg(authErrText(e)); });
      });

      var out = $("#authOut");
      if (out) out.addEventListener("click", function () {
        endSession();
        auth.signOut().then(function () {
          authMsg("로그아웃했습니다.");
          showPanel("auth");
        }, function () {});
      });
    }).catch(function () {
      showPanel("auth");
      setSync("off", "연결 실패");
      authMsg("Firebase를 불러오지 못했습니다. 네트워크를 확인해 주세요.");
    });
  }

  /* ---------- boot ---------- */
  bootAuth();

  /* PIN keypad */
  var keypad = $("#keypad");
  if (keypad) {
    keypad.addEventListener("click", function (ev) {
      var btn = ev.target.closest ? ev.target.closest("[data-key]") : null;
      if (!btn) return;
      var k = btn.getAttribute("data-key");
      var msg = $("#lockMsg");
      if (msg) msg.textContent = "";
      if (k === "clear") state.pinInput = "";
      else if (k === "back") state.pinInput = state.pinInput.slice(0, -1);
      else if (/^[0-9]$/.test(k) && state.pinInput.length < 4) state.pinInput += k;
      renderPinDots();
      if (state.pinInput.length === 4) submitPin(state.pinInput);
    });
    document.addEventListener("keydown", function (ev) {
      if (!$("#lock") || $("#lock").hidden) return;
      if (/^[0-9]$/.test(ev.key) && state.pinInput.length < 4) {
        state.pinInput += ev.key;
        renderPinDots();
        if (state.pinInput.length === 4) submitPin(state.pinInput);
      } else if (ev.key === "Backspace") {
        state.pinInput = state.pinInput.slice(0, -1);
        renderPinDots();
      }
    });
  }

  /* tabs */
  var tabs = $("#tabs");
  if (tabs) {
    tabs.addEventListener("click", function (ev) {
      var b = ev.target.closest ? ev.target.closest("[data-tab]") : null;
      if (b) showTab(b.getAttribute("data-tab"));
    });
  }

  /* room + month + filter */
  var roomSeg = $("#roomSeg");
  if (roomSeg) {
    roomSeg.addEventListener("click", function (ev) {
      var b = ev.target.closest ? ev.target.closest("[data-room]") : null;
      if (!b) return;
      state.room = b.getAttribute("data-room");
      $$("[data-room]", roomSeg).forEach(function (x) { x.classList.toggle("is-on", x === b); });
      state.sel = null;
      renderCalendar();
    });
  }
  var prev = $("#prevMonth");
  if (prev) prev.addEventListener("click", function () {
    state.view = new Date(state.view.getFullYear(), state.view.getMonth() - 1, 1);
    renderCalendar();
  });
  var next = $("#nextMonth");
  if (next) next.addEventListener("click", function () {
    state.view = new Date(state.view.getFullYear(), state.view.getMonth() + 1, 1);
    renderCalendar();
  });

  var filterSeg = $("#filterSeg");
  if (filterSeg) {
    filterSeg.addEventListener("click", function (ev) {
      var b = ev.target.closest ? ev.target.closest("[data-filter]") : null;
      if (!b) return;
      state.filter = b.getAttribute("data-filter");
      $$("[data-filter]", filterSeg).forEach(function (x) { x.classList.toggle("is-on", x === b); });
      renderBookings();
    });
  }
  var newManual = $("#newManual");
  if (newManual) newManual.addEventListener("click", function () {
    openManualSheet(ymd(today0()), ymd(today0()));
  });

  var saveRatesBtn = $("#saveRates");
  if (saveRatesBtn) saveRatesBtn.addEventListener("click", saveRates);

  /* reviews tab */
  var reviewRoomSeg = $("#reviewRoomSeg");
  if (reviewRoomSeg) {
    reviewRoomSeg.addEventListener("click", function (ev) {
      var b = ev.target.closest ? ev.target.closest("[data-review-room]") : null;
      if (!b) return;
      state.reviewRoom = b.getAttribute("data-review-room");
      $$("[data-review-room]", reviewRoomSeg).forEach(function (x) { x.classList.toggle("is-on", x === b); });
      renderReviews();
    });
  }
  var newReview = $("#newReview");
  if (newReview) newReview.addEventListener("click", function () { openReviewSheet(state.reviewRoom, null); });

  /* inquiries tab */
  var inqFilterSeg = $("#inqFilterSeg");
  if (inqFilterSeg) {
    inqFilterSeg.addEventListener("click", function (ev) {
      var b = ev.target.closest ? ev.target.closest("[data-inq-filter]") : null;
      if (!b) return;
      state.inqFilter = b.getAttribute("data-inq-filter");
      $$("[data-inq-filter]", inqFilterSeg).forEach(function (x) { x.classList.toggle("is-on", x === b); });
      renderInquiries();
    });
  }

  /* bank + check-in templates */
  var bankForm = $("#bankForm");
  if (bankForm) {
    bankForm.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var msg = $("#bankMsg");
      var payload = {
        bank: bankForm.elements.bank.value.trim(),
        account: bankForm.elements.account.value.trim(),
        holder: bankForm.elements.holder.value.trim(),
        note: bankForm.elements.note.value.trim(),
        updatedAt: Date.now()
      };
      if (!payload.account) {
        if (msg) { msg.textContent = "계좌번호를 입력해 주세요."; msg.className = "msg is-error"; }
        return;
      }
      db.ref(PATH + "/settings/bank").set(payload).then(function () {
        if (msg) { msg.textContent = "입금 계좌를 저장했습니다. 예약 접수 화면에 바로 표시됩니다."; msg.className = "msg is-ok"; }
        toast("입금 계좌를 저장했습니다.");
      }, function () {
        if (msg) { msg.textContent = "저장하지 못했습니다."; msg.className = "msg is-error"; }
      });
    });
  }

  var checkinForm = $("#checkinForm");
  if (checkinForm) {
    checkinForm.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var msg = $("#checkinMsg");
      var payload = {
        heyum: checkinForm.elements.heyum.value,
        orot: checkinForm.elements.orot.value,
        updatedAt: Date.now()
      };
      db.ref(PATH + "/settings/checkinTemplates").set(payload).then(function () {
        if (msg) { msg.textContent = "입실 안내문을 저장했습니다."; msg.className = "msg is-ok"; }
        toast("입실 안내문을 저장했습니다.");
      }, function () {
        if (msg) { msg.textContent = "저장하지 못했습니다."; msg.className = "msg is-error"; }
      });
    });
  }

  /* calendar interaction: tap or drag */
  var calGrid = $("#calGrid");
  if (calGrid) {
    var dragging = false, startDate = null, moved = false;
    var dateFromPoint = function (x, y) {
      var t = document.elementFromPoint(x, y);
      var cell = t && t.closest ? t.closest(".day[data-date]") : null;
      return cell ? cell.getAttribute("data-date") : null;
    };
    calGrid.addEventListener("pointerdown", function (ev) {
      var cell = ev.target.closest ? ev.target.closest(".day[data-date]") : null;
      if (!cell) return;
      dragging = true;
      moved = false;
      startDate = cell.getAttribute("data-date");
      state.sel = { a: startDate, b: startDate };
    });
    calGrid.addEventListener("pointermove", function (ev) {
      if (!dragging) return;
      var d = dateFromPoint(ev.clientX, ev.clientY);
      if (!d || d === state.sel.b) return;
      moved = true;
      state.sel = { a: startDate < d ? startDate : d, b: startDate < d ? d : startDate };
      renderCalendar();
    });
    window.addEventListener("pointerup", function (ev) {
      if (!dragging) return;
      dragging = false;
      var d = dateFromPoint(ev.clientX, ev.clientY) || startDate;
      var a = startDate < d ? startDate : d;
      var b = startDate < d ? d : startDate;
      state.sel = { a: a, b: b };
      openSheet({ a: a, b: b });
    });
  }

  /* sheet close */
  var sheetClose = $("#sheetClose");
  if (sheetClose) sheetClose.addEventListener("click", closeSheet);
  var sheet = $("#sheet");
  if (sheet) sheet.addEventListener("click", function (ev) {
    if (ev.target === sheet) closeSheet();
  });
  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape" && sheet && !sheet.hidden) closeSheet();
  });

  /* logout — 사장님 계정 로그아웃 + PIN 세션 종료 */
  var logout = $("#logout");
  if (logout) logout.addEventListener("click", function () {
    endSession();
    var p = (auth && auth.signOut) ? auth.signOut().catch(function () {}) : Promise.resolve();
    p.then(function () { window.location.reload(); });
  });

  /* PIN change */
  var pinForm = $("#pinForm");
  if (pinForm) {
    pinForm.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var msg = $("#pinMsg");
      var cur = pinForm.elements.cur.value.trim();
      var nx = pinForm.elements.next.value.trim();
      var nx2 = pinForm.elements.next2.value.trim();
      var say = function (text, ok) {
        if (!msg) return;
        msg.textContent = text;
        msg.className = "msg " + (ok ? "is-ok" : "is-error");
      };
      if (!/^\d{4}$/.test(nx)) return say("새 PIN은 숫자 4자리로 정해 주세요.");
      if (nx !== nx2) return say("새 PIN 확인이 일치하지 않습니다.");
      hashPin(cur).then(function (h) {
        if (!state.settings || h !== state.settings.pinHash) return say("현재 PIN이 맞지 않습니다.");
        return hashPin(nx).then(function (nh) {
          return db.ref(PATH + "/settings/pinHash").set(nh).then(function () {
            say("PIN을 변경했습니다. 다음 로그인부터 새 PIN을 사용합니다.", true);
            pinForm.reset();
          });
        });
      }).catch(function () { say("변경하지 못했습니다. 연결을 확인해 주세요."); });
    });
  }

  /* if a session survives a reload, re-open once data arrives */
  var iv = window.setInterval(function () {
    if (state.ready && sessionValid() && $("#app") && $("#app").hidden && !state.pinInput) {
      openApp();
    }
    if (state.ready) window.clearInterval(iv);
  }, 400);
})();
