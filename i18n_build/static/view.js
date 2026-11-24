/* NEUNGNOL STAY — PC / 모바일 버전 전환
   - 기본값은 기기 화면에 맞춘 자동(반응형)
   - 버튼을 누르면 localStorage("nns_view")에 저장되어 페이지를 옮겨도 유지된다.
   - PC 버전: 폰에서도 <meta viewport>를 width=1280 으로 바꿔 데스크톱 레이아웃 그대로 본다.
   - 모바일 버전: PC에서도 html.view-mo 로 420px 모바일 레이아웃을 강제한다.
   - 선택된 버튼을 한 번 더 누르면 자동으로 돌아간다. */
(function () {
  "use strict";

  var KEY = "nns_view";
  var root = document.documentElement;
  var META_DEVICE = "width=device-width, initial-scale=1";
  var META_PC = "width=1280";

  function viewMeta() {
    return document.querySelector('meta[name="viewport"]');
  }

  function syncButtons(v) {
    var btns = document.querySelectorAll("[data-view]");
    for (var i = 0; i < btns.length; i++) {
      btns[i].setAttribute("aria-pressed", btns[i].getAttribute("data-view") === v ? "true" : "false");
    }
  }

  function apply(v) {
    if (root.classList) {
      root.classList.toggle("view-pc", v === "pc");
      root.classList.toggle("view-mo", v === "mo");
    }
    var m = viewMeta();
    if (m) m.setAttribute("content", v === "pc" ? META_PC : META_DEVICE);
    syncButtons(v);
  }

  function stored() {
    try {
      var v = localStorage.getItem(KEY);
      return v === "pc" || v === "mo" ? v : "";
    } catch (e) {
      return "";
    }
  }

  function onClick(ev) {
    var t = ev.target;
    var btn = t && t.closest ? t.closest("[data-view]") : null;
    if (!btn) return;
    var want = btn.getAttribute("data-view");
    var next = stored() === want ? "" : want; /* 같은 버튼을 다시 누르면 자동(반응형) */
    try {
      if (next) localStorage.setItem(KEY, next);
      else localStorage.removeItem(KEY);
    } catch (e) { /* 저장이 막혀도 이번 화면에는 적용 */ }
    apply(next);
    try {
      if (window.NNS && window.NNS.track) window.NNS.track("view_switch", { view: next || "auto" });
    } catch (e) { /* 분석 실패는 무시 */ }
  }

  document.addEventListener("click", onClick);
  apply(stored());
})();
