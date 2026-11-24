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
  var SESSION_KEY = "nns_admin_session";
  var SESSION_MS = 12 * 3600 * 1000;
  var ROOM_NAME = { heyum: "헤윰 · 3층", orot: "오롯 · 6층" };
  var DEFAULT_RATES = {
    heyum: { wd: 500000, fri: 600000, sat: 1100000 },
    orot: { wd: 500000, fri: 600000, sat: 1100000 }
  };
  var DEFAULT_EXTRA = 30000;

  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  var db = null;
  var state = {
    ready: false,
    settings: null,
    blocks: {},
    bookings: {},
    room: "heyum",
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
      if (window.firebase && window.firebase.database) return resolve();
      var base = "https://www.gstatic.com/firebasejs/" + FB_VERSION + "/";
      var addScript = function (src, ok, fail) {
        var s = document.createElement("script");
        s.src = src;
        s.async = false;
        s.onload = ok;
        s.onerror = fail;
        document.head.appendChild(s);
      };
      /* app-compat → database-compat 순서 보장 */
      addScript(base + "firebase-app-compat.js", function () {
        addScript(base + "firebase-database-compat.js", function () { resolve(); },
          function () { reject(new Error("sdk")); });
      }, function () { reject(new Error("sdk")); });
    });
  }

  function setSync(kind, text) {
    var elx = $("#syncState");
    if (!elx) return;
    elx.className = "sync" + (kind ? " is-" + kind : "");
    elx.textContent = text;
  }

  function connect() {
    loadSdk().then(function () {
      var app = null;
      (firebase.apps || []).forEach(function (a) { if (a.name === "nns-admin") app = a; });
      if (!app) app = firebase.initializeApp(FB_CONFIG, "nns-admin");
      db = app.database();
      db.ref(PATH).on("value", function (snap) {
        var v = snap.val() || {};
        state.settings = v.settings || null;
        state.blocks = v.blocks || {};
        state.bookings = v.bookings || {};
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
    var blocked = !!(state.blocks[room] && state.blocks[room][date]);
    if (conf.length) return { kind: "confirmed", items: conf.concat(pend), blocked: blocked };
    if (pend.length) return { kind: "pending", items: pend, blocked: blocked };
    if (blocked) return { kind: "blocked", items: [], blocked: true };
    return { kind: "open", items: [], blocked: false };
  }
  function rateOf(room, date) {
    var ov = state.settings && state.settings.overrides && state.settings.overrides[room];
    if (ov && Number(ov[date]) > 0) return Number(ov[date]);
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
      cell.appendChild(el("span", "day__n", d));
      cell.appendChild(el("span", "day__p", Math.round(rateOf(state.room, key) / 10000) + "만" + (isOverride(state.room, key) ? " *" : "")));
      if (st.kind !== "open") {
        var label = { blocked: "차단", pending: "대기", confirmed: "확정" }[st.kind];
        var cls = "day__s day__s--" + st.kind;
        cell.appendChild(el("span", cls, label));
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
        row.appendChild(el("b", null, dateKo(b.checkin).replace(/ \(.\)/, "") + " → " + dateKo(b.checkout).replace(/ \(.\)/, "")));
        row.appendChild(el("span", null, (b.name || "이름 없음") + " · " + (b.nights || daysBetween(b.checkin, b.checkout)) + "박 · " +
          (b.status === "confirmed" ? "확정" : "대기")));
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
      top.appendChild(el("span", "bk__state bk__state--" + bk.status, bk.status === "confirmed" ? "확정" : "대기"));
      box.appendChild(top);
      box.appendChild(el("p", "bk__msg", dateKo(bk.checkin) + " → " + dateKo(bk.checkout) + " · " +
        (bk.phone || "연락처 없음") + " · " + money(bk.total)));
      var acts = el("div", "bk__acts");
      if (bk.status === "pending") {
        var ok = el("button", "btn btn--ok btn--sm", "예약 확정");
        ok.addEventListener("click", function () { setStatus(bk.id, "confirmed"); closeSheet(); });
        acts.appendChild(ok);
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

    /* 차단 / 해제 */
    var btnBlock = el("button", "btn", "외부예약 차단 (에어비앤비·네이버 등)");
    btnBlock.addEventListener("click", function () {
      var updates = {};
      dateRange(a, b).forEach(function (d) {
        updates[PATH + "/blocks/" + state.room + "/" + d] = { reason: "external", createdAt: Date.now() };
      });
      db.ref().update(updates).then(function () { toast(n + "일 차단했습니다."); closeSheet(); },
        function () { toast("차단하지 못했습니다. 연결을 확인해 주세요."); });
    });
    var btnUnblock = el("button", "btn btn--line", "차단 해제");
    btnUnblock.addEventListener("click", function () {
      var updates = {};
      dateRange(a, b).forEach(function (d) { updates[PATH + "/blocks/" + state.room + "/" + d] = null; });
      db.ref().update(updates).then(function () { toast("차단을 해제했습니다."); closeSheet(); },
        function () { toast("해제하지 못했습니다."); });
    });
    body.appendChild(el("div", "sheet__divider"));
    body.appendChild(btnBlock);
    body.appendChild(btnUnblock);

    /* 요금 */
    body.appendChild(el("div", "sheet__divider"));
    var priceWrap = el("div", "sheet__field");
    priceWrap.appendChild(el("span", null, "특정일 1박 요금 (원)"));
    var input = document.createElement("input");
    input.type = "number";
    input.step = "10000";
    input.min = "0";
    input.value = String(rateOf(state.room, a));
    priceWrap.appendChild(input);
    body.appendChild(priceWrap);
    var row = el("div", "sheet__row");
    var savePrice = el("button", "btn btn--line", "요금 적용");
    savePrice.addEventListener("click", function () {
      var val = parseInt(input.value, 10);
      if (!val || val < 0) return toast("요금을 입력해 주세요.");
      var updates = {};
      dateRange(a, b).forEach(function (d) { updates[PATH + "/settings/overrides/" + state.room + "/" + d] = val; });
      db.ref().update(updates).then(function () { toast(n + "일 요금을 " + money(val) + "로 저장했습니다."); closeSheet(); },
        function () { toast("요금을 저장하지 못했습니다."); });
    });
    var resetPrice = el("button", "btn btn--line", "기본 요금으로");
    resetPrice.addEventListener("click", function () {
      var updates = {};
      dateRange(a, b).forEach(function (d) { updates[PATH + "/settings/overrides/" + state.room + "/" + d] = null; });
      db.ref().update(updates).then(function () { toast("기본 요금으로 되돌렸습니다."); closeSheet(); },
        function () { toast("변경하지 못했습니다."); });
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
    stWrap.appendChild(el("span", null, "상태"));
    var select = document.createElement("select");
    [["confirmed", "확정 (날짜 마감)"], ["pending", "대기"]].forEach(function (opt) {
      var o = document.createElement("option");
      o.value = opt[0];
      o.textContent = opt[1];
      select.appendChild(o);
    });
    stWrap.appendChild(select);
    body.appendChild(stWrap);

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
        source: "manual",
        createdAt: Date.now()
      };
      db.ref(PATH + "/bookings").push(payload, function (err) {
        if (err) return toast("등록하지 못했습니다.");
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

  function setStatus(id, status) {
    if (!db) return;
    db.ref(PATH + "/bookings/" + id + "/status").set(status).then(function () {
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
      var stateLabel = { pending: "확인 대기", confirmed: "확정", cancelled: "취소" }[b.status] || b.status;
      top.appendChild(el("span", "bk__state bk__state--" + b.status, stateLabel));
      if (b.source === "manual") top.appendChild(el("span", "bk__state", "수동"));
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
    var ms = $("#metaSync");
    if (ms) ms.textContent = state.lastSync ? ts(state.lastSync) : "—";
  }

  /* ---------- render ---------- */
  function renderAll() {
    if (!state.ready && !state.settings) {
      /* 데이터 오기 전에도 잠금 화면 PIN 검증은 가능해야 한다 */
    }
    if (!$("#app") || $("#app").hidden) return;
    renderCalendar();
    renderBookings();
    renderRates();
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

  /* ---------- boot ---------- */
  connect();

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

  /* logout */
  var logout = $("#logout");
  if (logout) logout.addEventListener("click", function () {
    endSession();
    window.location.reload();
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
