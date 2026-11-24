/* NEUNGNOL STAY — guest inquiry board with two-way machine translation.
   inquiries/{id} = {name, contact, text, lang, textKo, room, pageLang, createdAt, status,
                     answerKo, answeredAt}
   - 손님이 쓴 글은 한국어 번역본(textKo)과 함께 저장 → 관리자가 바로 읽는다.
   - 관리자 답변은 한국어(answerKo)만 저장하고, 손님 화면에서 화면 언어로 번역해 보여 준다.
   - 연락처(contact)는 화면에 절대 표시하지 않는다. */
(function () {
  "use strict";
  var NNS = window.NNS;
  var root = document.querySelector("[data-inquiry]");
  if (!NNS || !root) return;

  var pageLang = (NNS.cfg || {}).lang || "ko";
  var listEl = root.querySelector("[data-inq-list]");
  var emptyEl = root.querySelector("[data-inq-empty]");
  var form = root.querySelector("[data-inq-form]");
  var msgEl = root.querySelector("[data-inq-msg]");
  var submitBtn = root.querySelector("[data-inq-submit]");

  var S = {};
  var el = document.querySelector("[data-inq-strings]");
  try { S = JSON.parse(el ? el.textContent : "{}") || {}; } catch (e) { S = {}; }
  function txt(key, fb) { return S[key] || fb || ""; }

  var ROOM_LABEL = {
    heyum: txt("heyum", "Heyum"),
    orot: txt("orot", "Orot")
  };
  var LIMIT = 30;
  var sending = false;
  var showAll = false;

  /* ---------- helpers ---------- */
  function fmtDate(ms) {
    var d = new Date(Number(ms) || 0);
    if (!d.getTime()) return "";
    var m = d.getMonth() + 1, day = d.getDate();
    return d.getFullYear() + "." + (m < 10 ? "0" + m : m) + "." + (day < 10 ? "0" + day : day);
  }

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

  function translatedBlock(original, fromLang, toLang, target, cls) {
    if (!original) return;
    if (!fromLang || fromLang === toLang) { target.textContent = original; return; }
    target.textContent = original;
    queue(function (done) {
      NNS.translate(original, toLang, function (err, res) {
        if (!err && res && res.text && res.text !== original) {
          target.textContent = res.text;
          var note = document.createElement("div");
          note.className = cls || "inq__trans";
          var tag = document.createElement("span");
          tag.textContent = txt("translated", "Auto-translated");
          var btn = document.createElement("button");
          btn.type = "button";
          btn.className = "inq__trans-btn";
          btn.textContent = txt("original", "Show original");
          var showingOriginal = false;
          btn.addEventListener("click", function () {
            showingOriginal = !showingOriginal;
            target.textContent = showingOriginal ? original : res.text;
            btn.textContent = showingOriginal ? txt("translated", "Auto-translated") : txt("original", "Show original");
          });
          note.appendChild(tag);
          note.appendChild(btn);
          if (target.parentNode) target.parentNode.insertBefore(note, target.nextSibling);
        }
        done();
      });
    });
  }

  /* ---------- render ---------- */
  function item(raw) {
    var li = document.createElement("li");
    li.className = "inq__item";

    var head = document.createElement("div");
    head.className = "inq__head";
    var who = document.createElement("b");
    who.className = "inq__who";
    who.textContent = String(raw.name || txt("anonymous", "Guest"));
    head.appendChild(who);
    if (raw.room && ROOM_LABEL[raw.room]) {
      var badge = document.createElement("span");
      badge.className = "inq__badge";
      badge.textContent = ROOM_LABEL[raw.room];
      head.appendChild(badge);
    }
    var when = document.createElement("span");
    when.className = "inq__when";
    when.textContent = fmtDate(raw.createdAt);
    head.appendChild(when);
    li.appendChild(head);

    var body = document.createElement("p");
    body.className = "inq__text";
    li.appendChild(body);
    translatedBlock(String(raw.text || ""), String(raw.lang || ""), pageLang, body);

    var ans = String(raw.answerKo || "").trim();
    var box = document.createElement("div");
    box.className = "inq__answer";
    if (ans) {
      var lab = document.createElement("span");
      lab.className = "inq__answer-k";
      lab.textContent = txt("answer_label", "Host's answer");
      box.appendChild(lab);
      var ap = document.createElement("p");
      ap.className = "inq__answer-text";
      box.appendChild(ap);
      /* 관리자 답변은 한국어로 저장된다 → 화면 언어로 번역 */
      translatedBlock(ans, "ko", pageLang, ap, "inq__trans");
    } else {
      var wait = document.createElement("span");
      wait.className = "inq__wait";
      wait.textContent = txt("waiting", "Waiting for the host's answer");
      box.appendChild(wait);
    }
    li.appendChild(box);
    return li;
  }

  function render(items) {
    if (!listEl) return;
    listEl.textContent = "";
    var shown = showAll ? items : items.slice(0, 5);
    shown.forEach(function (it) { listEl.appendChild(item(it)); });
    if (emptyEl) emptyEl.hidden = items.length > 0;
    var moreWrap = root.querySelector("[data-inq-more]");
    if (moreWrap) moreWrap.hidden = items.length <= 5;
  }

  var all = [];
  function normalize(raw) {
    var out = [];
    Object.keys(raw || {}).forEach(function (id) {
      var q = raw[id] || {};
      if (q.deleted) return;
      out.push({
        id: id,
        name: String(q.name || ""),
        text: String(q.text || ""),
        lang: String(q.lang || ""),
        textKo: String(q.textKo || ""),
        room: String(q.room || ""),
        createdAt: Number(q.createdAt) || 0,
        answerKo: String(q.answerKo || "")
      });
    });
    out.sort(function (a, b) { return b.createdAt - a.createdAt; });
    return out;
  }

  /* ---------- form ---------- */
  function setMsg(text, ok) {
    if (!msgEl) return;
    msgEl.textContent = text || "";
    msgEl.className = "inq__msg" + (text ? (ok ? " is-ok" : " is-error") : "");
  }

  if (form) {
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      if (sending) return;
      var data = new FormData(form);
      var name = String(data.get("name") || "").trim();
      var contact = String(data.get("contact") || "").trim();
      var room = String(data.get("room") || "").trim();
      var text = String(data.get("text") || "").trim();
      if (name.length < 1) { setMsg(txt("err_name", "Please enter your name.")); return; }
      if (text.length < 5) { setMsg(txt("err_message", "Please write your question.")); return; }

      sending = true;
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.dataset.label = submitBtn.textContent;
        submitBtn.textContent = txt("submitting", "Sending…");
      }
      setMsg("");

      NNS.withDb("nns-inquiry", function (err, db) {
        if (err || !db) { finish(); setMsg(txt("err_send", "Could not send.")); return; }
        /* 한국어로 번역해 두면 관리자가 바로 읽는다. 번역 실패해도 원문은 저장한다. */
        NNS.translate(text, "ko", function (terr, res) {
          var textKo = (!terr && res && res.text) ? res.text : "";
          var detected = (!terr && res && res.src) ? res.src : pageLang;
          if (detected && detected.indexOf("zh") === 0) detected = pageLang;
          var payload = {
            name: name.slice(0, 40),
            contact: contact.slice(0, 80),
            room: room,
            text: text.slice(0, 1200),
            textKo: textKo,
            lang: detected || pageLang,
            pageLang: pageLang,
            page: (NNS.cfg || {}).page || "",
            status: "open",
            createdAt: Date.now()
          };
          db.ref(NNS.PATH + "/inquiries").push(payload, function (perr) {
            if (perr) { finish(); setMsg(txt("err_send", "Could not send.")); return; }
            finish();
            setMsg(txt("thanks", "Received."), true);
            form.reset();
            NNS.track("inquiry_sent", { room: room || "general" });
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
  render([]);
  NNS.withDb("nns-inquiry", function (err, db) {
    if (err || !db) return;
    db.ref(NNS.PATH + "/inquiries").on("value", function (snap) {
      all = normalize(snap.val());
      render(all);
    }, function () { /* 연결 실패: 빈 보드 유지 */ });
  });

  var moreBtn = root.querySelector("[data-inq-more-btn]");
  if (moreBtn) {
    moreBtn.addEventListener("click", function () {
      showAll = true;
      render(all);
      moreBtn.hidden = true;
    });
  }
})();
