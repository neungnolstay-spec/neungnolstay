/* NEUNGNOL STAY — shared helpers for the guest-facing modules.
   - NNS.withDb(name, cb): Firebase RTDB (compat SDK) at /neungnol_booking_v1
   - NNS.translate(text, toDir, cb): free translation endpoints, cached in localStorage
   - NNS.track(name, params): GA4 / dataLayer event
   Keep this file dependency-free. */
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
  var LOCALES = { ko: "ko-KR", en: "en-US", ja: "ja-JP", "zh-cn": "zh-CN", "zh-tw": "zh-TW" };
  var API_LANG = { ko: "ko", en: "en", ja: "ja", "zh-cn": "zh-CN", "zh-tw": "zh-TW" };
  var cfg = window.SITE_CONFIG || {};

  function track(name, params) {
    var payload = Object.assign({ page_language: cfg.lang || "ko", page_type: cfg.page || "" }, params || {});
    try {
      if (typeof window.gtag === "function") window.gtag("event", name, payload);
      else if (window.dataLayer) window.dataLayer.push(Object.assign({ event: name }, payload));
    } catch (e) { /* analytics never breaks the page */ }
  }

  /* ---------- firebase ---------- */
  function addScript(src, ok, fail) {
    var s = document.createElement("script");
    s.src = src;
    s.async = false;
    s.onload = ok;
    s.onerror = fail;
    document.head.appendChild(s);
  }

  function withDb(name, cb) {
    var done = false;
    function finish(err) {
      if (done) return;
      done = true;
      if (err) { cb(err, null); return; }
      try {
        var app = null;
        (window.firebase.apps || []).forEach(function (a) { if (a.name === name) app = a; });
        if (!app) app = window.firebase.initializeApp(FB_CONFIG, name);
        cb(null, app.database());
      } catch (e) {
        cb(e, null);
      }
    }
    if (window.firebase && window.firebase.database) { finish(null); return; }
    var base = "https://www.gstatic.com/firebasejs/" + FB_VERSION + "/";
    addScript(base + "firebase-app-compat.js", function () {
      addScript(base + "firebase-database-compat.js", function () { finish(null); },
        function () { finish(new Error("sdk")); });
    }, function () { finish(new Error("sdk")); });
  }

  /* ---------- translation ---------- */
  var cache = {};
  function lsGet(k) { try { return window.localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { window.localStorage.setItem(k, v); } catch (e) {} }
  function hash(s) {
    var h = 5381;
    for (var i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0;
    return (h >>> 0).toString(36);
  }
  function getJson(url, cb) {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", url, true);
    xhr.timeout = 8000;
    xhr.onload = function () {
      if (xhr.status !== 200) { cb(new Error("http" + xhr.status)); return; }
      try { cb(null, JSON.parse(xhr.responseText)); } catch (e) { cb(e); }
    };
    xhr.onerror = function () { cb(new Error("net")); };
    xhr.ontimeout = function () { cb(new Error("timeout")); };
    xhr.send();
  }

  function parseDict(data) {
    /* clients5.google.com/translate_a/t?client=dict-chrome-ex → [["번역","en"]] */
    if (!data) return null;
    if (typeof data === "string") return { text: data, src: "" };
    if (!Array.isArray(data)) return null;
    if (Array.isArray(data[0])) {
      var out = data.map(function (row) { return (row && row[0]) || ""; }).join("");
      return { text: out, src: (data[0] && data[0][1]) || "" };
    }
    if (typeof data[0] === "string") return { text: data[0], src: data[1] || "" };
    return null;
  }

  function parseSingle(data) {
    /* translate.googleapis.com/translate_a/single → [[["번역","원문",…]],null,"en"] */
    if (!Array.isArray(data) || !Array.isArray(data[0])) return null;
    var out = "";
    data[0].forEach(function (seg) { if (seg && seg[0]) out += seg[0]; });
    return out ? { text: out, src: data[2] || "" } : null;
  }

  function parseMemory(data) {
    if (!data || !data.responseData || !data.responseData.translatedText) return null;
    return { text: data.responseData.translatedText, src: "" };
  }

  /**
   * translate(text, toDir, cb) — cb(err, {text, src})
   * toDir: ko | en | ja | zh-cn | zh-tw. Tries three free endpoints in order.
   */
  function translate(text, toDir, cb) {
    var clean = String(text || "").trim();
    if (!clean) { cb(null, { text: "", src: "" }); return; }
    var tgt = API_LANG[toDir] || "en";
    var key = "nns_tr:v1:" + tgt + ":" + hash(clean);
    if (cache[key]) { cb(null, cache[key]); return; }
    var stored = lsGet(key);
    if (stored) {
      try { cache[key] = JSON.parse(stored); cb(null, cache[key]); return; } catch (e) {}
    }
    var q = encodeURIComponent(clean.slice(0, 1800));
    var urls = [
      "https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=auto&tl=" + encodeURIComponent(tgt) + "&q=" + q,
      "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=" + encodeURIComponent(tgt) + "&dt=t&q=" + q,
      "https://api.mymemory.translated.net/get?q=" + q + "&langpair=auto|" + encodeURIComponent(tgt)
    ];
    var parsers = [parseDict, parseSingle, parseMemory];
    var i = 0;
    function next() {
      if (i >= urls.length) { cb(new Error("translate")); return; }
      var idx = i++;
      getJson(urls[idx], function (err, data) {
        if (err) { next(); return; }
        var res = parsers[idx](data);
        if (!res || !res.text) { next(); return; }
        res.src = String(res.src || "").toLowerCase();
        cache[key] = res;
        lsSet(key, JSON.stringify(res));
        cb(null, res);
      });
    }
    next();
  }

  function money(n) { return "₩" + Math.round(Number(n) || 0).toLocaleString("en-US"); }

  window.NNS = {
    PATH: PATH,
    LOCALES: LOCALES,
    API_LANG: API_LANG,
    cfg: cfg,
    withDb: withDb,
    translate: translate,
    track: track,
    money: money,
    lang: cfg.lang || "ko"
  };
})();
