/* NEUNGNOL STAY — guest booking lookup + 1:1 chat with the host.
   bookings/{id}          : 접수 번호 = NN-<체크인YYMMDD>-<id 뒤 4자리>
   bookingChats/{id}/{n}  : {from: 'guest'|'host', text, textKo, lang, kind?, createdAt}
   - 게스트가 쓴 글은 한국어 번역본(textKo)과 함께 저장 → 호스트가 바로 읽는다.
   - 호스트 메시지(한국어)는 화면 언어로 번역해 보여 준다. */
(function () {
  "use strict";
  var NNS = window.NNS;
  var root = document.querySelector("[data-mybook]");
  if (!NNS || !root) return;

  var pageLang = (NNS.cfg || {}).lang || "ko";
  var S = {};
  var elS = document.querySelector("[data-mybk-strings]");
  try { S = JSON.parse(elS ? elS.textContent : "{}") || {}; } catch (e) { S = {}; }
  function txt(k, fb) { return S[k] || fb || ""; }

  var form = root.querySelector("[data-mybk-form]");
  var msg = root.querySelector("[data-mybk-msg]");
  var view = root.querySelector("[data-mybk-view]");
  var refEl = root.querySelector("[data-mybk-ref]");
  var stateEl = root.querySelector("[data-mybk-state]");
  var stayEl = root.querySelector("[data-mybk-stay]");
  var bankEl = root.querySelector("[data-mybk-bank]");
  var noteEl = root.querySelector("[data-mybk-note]");
  var listEl = root.querySelector("[data-chat-list]");
  var emptyEl = root.querySelector("[data-chat-empty]");
  var chatForm = root.querySelector("[data-chat-form]");
  var chatMsg = root.querySelector("[data-chat-msg]");
  var sendBtn = root.querySelector("[data-chat-send]");

  var booking = null;
  var bookingId = null;
  var chatRef = null;
  var sending = false;

  function setMsg(text, ok) {
    if (!msg) return;
    msg.textContent = text || "";
    msg.className = "mybk__msg" + (text ? (ok ? " is-ok" : " is-error") : "");
  }
  function setChatMsg(text) {
    if (!chatMsg) return;
    chatMsg.textContent = text || "";
  }
  function money(n) { return "₩" + Math.round(Number(n) || 0).toLocaleString("en-US"); }
  function refOf(id, booking) {
    var ci = String((booking && booking.checkin) || "").replace(/-/g, "");
    return "NN-" + ci.slice(2) + "-" + String(id).slice(-4).toUpperCase();
  }
  function digits(s) { return String(s || "").replace(/[^0-9]/g, ""); }

  function queueListOf() {
    var q = [], busy = false;
    return function (fn) {
      q.push(fn);
      if (busy) return;
      busy = true;
      (function run() {
        var next = q.shift();
        if (!next) { busy = false; return; }
        next(function () { window.setTimeout(run, 120); });
      })();
    };
  }
  var queue = queueListOf();

  function when(ms) {
    var d = new Date(Number(ms) || 0);
    if (!d.getTime()) return "";
    var p = function (n) { return (n < 10 ? "0" : "") + n; };
    return d.getFullYear() + "." + p(d.getMonth() + 1) + "." + p(d.getDate()) + " " + p(d.getHours()) + ":" + p(d.getMinutes());
  }

  /* ---------- chat ---------- */
  function bubble(m) {
    var mine = m.from === "guest";
    var li = document.createElement("li");
    li.className = "chat__item " + (mine ? "is-me" : "is-host");
    if (m.kind === "checkin") li.classList.add("is-checkin");
    var head = document.createElement("div");
    head.className = "chat__head";
    head.appendChild(document.createTextNode(mine ? txt("me", "Me") : txt("host", "Host")));
    var t = document.createElement("span");
    t.className = "chat__when";
    t.textContent = when(m.createdAt);
    head.appendChild(t);
    if (m.kind === "checkin") {
      var k = document.createElement("span");
      k.className = "chat__kind";
      k.textContent = "CHECK-IN";
      head.appendChild(k);
    }
    li.appendChild(head);

    var p = document.createElement("p");
    p.className = "chat__text";
    p.textContent = String(m.text || "");
    li.appendChild(p);

    /* 상대(호스트)의 한국어 메시지는 화면 언어로 번역 */
    if (!mine) {
      var src = String(m.lang || "ko").toLowerCase();
      if (src && src !== pageLang) {
        queue(function (done) {
          NNS.translate(String(m.text || ""), pageLang, function (err, res) {
            if (!err && res && res.text && res.text !== m.text) {
              p.textContent = res.text;
              var note = document.createElement("div");
              note.className = "chat__trans";
              var tag = document.createElement("span");
              tag.textContent = txt("chat_translated", "Auto-translated");
              var btn = document.createElement("button");
              btn.type = "button";
              btn.className = "chat__trans-btn";
              btn.textContent = txt("chat_original", "Original");
              var orig = false;
              btn.addEventListener("click", function () {
                orig = !orig;
                p.textContent = orig ? m.text : res.text;
                btn.textContent = orig ? txt("chat_translated", "Auto-translated") : txt("chat_original", "Original");
              });
              note.appendChild(tag);
              note.appendChild(btn);
              li.appendChild(note);
            }
            done();
          });
        });
      }
    }
    return li;
  }

  function renderChat(raw) {
    if (!listEl) return;
    var items = Object.keys(raw || {}).map(function (k) {
      var m = raw[k] || {};
      m._k = k;
      return m;
    }).sort(function (a, b) { return (a.createdAt || 0) - (b.createdAt || 0); });
    listEl.textContent = "";
    items.forEach(function (m) { listEl.appendChild(bubble(m)); });
    if (emptyEl) emptyEl.hidden = items.length > 0;
  }

  function openChat(id) {
    bookingId = id;
    if (chatRef) chatRef.off();
    NNS.withDb("nns-mybooking", function (err, db) {
      if (err || !db) return;
      chatRef = db.ref(NNS.PATH + "/bookingChats/" + id);
      chatRef.on("value", function (snap) { renderChat(snap.val()); }, function () {});
    });
  }

  if (chatForm) {
    chatForm.addEventListener("submit", function (ev) {
      ev.preventDefault();
      if (sending || !bookingId) return;
      var ta = chatForm.querySelector('textarea[name="text"]');
      var text = String((ta && ta.value) || "").trim();
      if (text.length < 1) return;
      sending = true;
      if (sendBtn) { sendBtn.disabled = true; sendBtn.dataset.label = sendBtn.textContent; sendBtn.textContent = txt("chat_sending", "Sending…"); }
      setChatMsg("");
      NNS.withDb("nns-mybooking", function (err, db) {
        if (err || !db) { done(); setChatMsg(txt("chat_err", "Could not send.")); return; }
        NNS.translate(text, "ko", function (terr, res) {
          var payload = {
            from: "guest",
            text: text.slice(0, 800),
            textKo: (!terr && res && res.text) ? res.text : "",
            lang: (!terr && res && res.src) ? res.src : pageLang,
            pageLang: pageLang,
            createdAt: Date.now()
          };
          db.ref(NNS.PATH + "/bookingChats/" + bookingId).push(payload, function (perr) {
            done();
            if (perr) { setChatMsg(txt("chat_err", "Could not send.")); return; }
            if (ta) ta.value = "";
            NNS.track("booking_chat_sent", { booking: bookingId.slice(-4) });
          });
        });
      });
      function done() {
        sending = false;
        if (sendBtn) { sendBtn.disabled = false; sendBtn.textContent = sendBtn.dataset.label || txt("chat_send", "Send"); }
      }
    });
  }

  /* ---------- lookup ---------- */
  function showBooking(id, b) {
    booking = b;
    if (view) view.hidden = false;
    if (refEl) refEl.textContent = refOf(id, b);
    var st = String(b.status || "pending");
    if (stateEl) {
      stateEl.textContent = { pending: txt("status_pending", "Awaiting approval"), confirmed: txt("status_confirmed", "Confirmed"), cancelled: txt("status_cancelled", "Cancelled") }[st] || st;
      stateEl.className = "mybk__state is-" + st;
    }
    if (stayEl) {
      stayEl.textContent = (b.checkin || "") + " → " + (b.checkout || "") +
        " · " + (b.nights || "") + txt("nights_unit", "박") + " · " + money(b.total);
    }
    var bank = b.bank || null;
    if (!bank) {
      var s = (window.__mybkSettings && window.__mybkSettings.bank) || null;
      bank = s;
    }
    if (bankEl) {
      bankEl.textContent = bank && (bank.account || bank.bank)
        ? [bank.bank, bank.account, bank.holder].filter(Boolean).join(" ")
        : txt("bank_empty", "Bank details are sent with your confirmation.");
    }
    if (noteEl) {
      noteEl.hidden = st !== "pending";
      noteEl.textContent = st === "pending" ? txt("status_pending_note", "") : "";
    }
    openChat(id);
    KST_scroll();
  }

  function KST_scroll() {
    var sec = document.getElementById("my-booking");
    if (!sec) return;
    var top = sec.getBoundingClientRect().top + window.pageYOffset - 70;
    window.scrollTo({ top: top, behavior: "smooth" });
  }

  function lookup(refInput, phone4) {
    var ref = String(refInput || "").trim().toUpperCase().replace(/\s+/g, "");
    var p4 = digits(phone4).slice(-4);
    if (!ref || p4.length !== 4) { setMsg(txt("lookup_err", "Please check the details.")); return; }
    setMsg(txt("lookup_loading", "Searching…"), true);
    var done = function (bookings) {
      var hit = null;
      Object.keys(bookings || {}).forEach(function (id) {
        var b = bookings[id] || {};
        if (refOf(id, b) !== ref) return;
        if (digits(b.phone).slice(-4) !== p4) return;
        hit = { id: id, b: b };
      });
      if (!hit) { setMsg(txt("lookup_err", "Please check the details.")); return; }
      setMsg("");
      showBooking(hit.id, hit.b);
      NNS.track("booking_lookup", { status: hit.b.status || "" });
    };
    NNS.withDb("nns-mybooking", function (err, db) {
      if (err || !db) { setMsg(txt("lookup_err", "Please check the details.")); return; }
      db.ref(NNS.PATH + "/bookings").once("value", function (snap) { done(snap.val()); },
        function () { setMsg(txt("lookup_err", "Please check the details.")); });
    });
  }

  if (form) {
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      lookup(form.elements.ref.value, form.elements.phone4.value);
    });
  }

  /* 번역·계좌 안내용 설정은 한 번만 읽어 둔다 */
  NNS.withDb("nns-mybooking", function (err, db) {
    if (err || !db) return;
    db.ref(NNS.PATH + "/settings").once("value", function (snap) {
      var v = snap.val() || {};
      window.__mybkSettings = v;
      window.__mybkBankEmpty = (v && v.bank && v.bank.account) ? "" : txt("bank_empty", "");
    }, function () {});
  });

  /* 예약 완료 화면의 "내 예약 확인" 버튼 → 접수 번호 채우고 이동 */
  document.addEventListener("click", function (ev) {
    var btn = ev.target.closest ? ev.target.closest("[data-bk-open-my]") : null;
    if (!btn) return;
    var ref = document.querySelector("[data-bk-ref]");
    if (ref && form) {
      form.elements.ref.value = String(ref.textContent || "").trim();
      window.setTimeout(function () {
        var f = form.elements.phone4;
        if (f) f.focus();
      }, 500);
    }
  });

  /* ?booking=NN-... 로 들어오면 접수 번호를 채워 둔다 */
  try {
    var m = /[?&]booking=([^&#]+)/.exec(window.location.search);
    if (m && form) {
      form.elements.ref.value = decodeURIComponent(m[1]);
      setMsg(txt("lookup_hint", txt("my_lede", "")), true);
    }
  } catch (e) { /* noop */ }
})();
