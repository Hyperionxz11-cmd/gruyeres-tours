/* Gruyères Tours : interactions sobres (diaporama, récit des étapes, apparitions, parallaxe légère) */
(function () {
  var root = document.documentElement;
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var finePointer = window.matchMedia("(pointer: fine)").matches;

  /* En-tête : opaque après le haut de page */
  var header = document.querySelector(".site-header");
  function onScrollHeader() { header.classList.toggle("is-solid", window.scrollY > 40); }
  onScrollHeader();
  window.addEventListener("scroll", onScrollHeader, { passive: true });

  /* Menu mobile et choix de langue */
  var menuBtn = document.querySelector(".menu-btn");
  var lang = document.querySelector(".lang");
  function setMenu(open) {
    root.classList.toggle("menu-open", open);
    menuBtn.setAttribute("aria-expanded", String(open));
    document.body.style.overflow = open ? "hidden" : "";
  }
  menuBtn.addEventListener("click", function () { setMenu(!root.classList.contains("menu-open")); });
  document.querySelectorAll(".mobile-panel a").forEach(function (a) { a.addEventListener("click", function () { setMenu(false); }); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") { setMenu(false); lang.open = false; } });
  document.addEventListener("click", function (e) { if (lang.open && !lang.contains(e.target)) lang.open = false; });

  /* Images différées du diaporama : chargées après la page */
  function loadDeferred() {
    document.querySelectorAll("img[data-srcset]").forEach(function (img) {
      img.srcset = img.dataset.srcset;
      img.src = img.dataset.src;
      img.removeAttribute("data-srcset");
    });
  }
  if (document.readyState === "complete") setTimeout(loadDeferred, 300);
  else window.addEventListener("load", function () { setTimeout(loadDeferred, 300); });

  /* Diaporama d'ouverture */
  var slides = Array.prototype.slice.call(document.querySelectorAll(".slide"));
  var dots = Array.prototype.slice.call(document.querySelectorAll(".slide-dots button"));
  var capNum = document.querySelector(".slide-num");
  var capName = document.querySelector(".slide-name");
  var current = 0, timer = null, DURATION = 7000;
  function show(i) {
    slides[current].classList.remove("is-active");
    dots[current].setAttribute("aria-selected", "false");
    current = (i + slides.length) % slides.length;
    slides[current].classList.add("is-active");
    dots[current].setAttribute("aria-selected", "true");
    capNum.textContent = String(current + 1).padStart(2, "0");
    capName.textContent = slides[current].dataset.cap;
  }
  function play() {
    clearInterval(timer);
    if (reduce) return;
    root.style.setProperty("--slide-ms", DURATION + "ms");
    timer = setInterval(function () { show(current + 1); }, DURATION);
  }
  dots.forEach(function (d, i) { d.addEventListener("click", function () { show(i); play(); }); });
  document.addEventListener("visibilitychange", function () { if (document.hidden) clearInterval(timer); else play(); });
  if (slides.length) play();

  /* Apparitions au défilement */
  var revealables = document.querySelectorAll("[data-reveal], [data-unveil]");
  if ("IntersectionObserver" in window && !reduce) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add("is-in"); io.unobserve(en.target); } });
    }, { rootMargin: "0px 0px -10% 0px", threshold: 0.05 });
    revealables.forEach(function (el) { io.observe(el); });
  } else {
    revealables.forEach(function (el) { el.classList.add("is-in"); });
  }
  requestAnimationFrame(function () { root.classList.add("is-loaded"); });

  /* Récit des étapes : l'image suit le texte */
  var steps = Array.prototype.slice.call(document.querySelectorAll(".story-step"));
  var storyImgs = Array.prototype.slice.call(document.querySelectorAll(".story-img"));
  var storyCount = document.querySelector(".story-count b");
  if (steps.length && "IntersectionObserver" in window) {
    var so = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        var i = steps.indexOf(en.target);
        steps.forEach(function (s, k) { s.classList.toggle("is-active", k === i); });
        storyImgs.forEach(function (m, k) { m.classList.toggle("is-active", k === i); });
        if (storyCount) storyCount.textContent = String(i + 1).padStart(2, "0");
      });
    }, { rootMargin: "-45% 0px -45% 0px" });
    steps.forEach(function (s) { so.observe(s); });
  }

  /* Parallaxe légère des grandes images */
  var layers = Array.prototype.slice.call(document.querySelectorAll("[data-parallax]"));
  if (layers.length && !reduce) {
    var ticking = false;
    function update() {
      var vh = window.innerHeight;
      layers.forEach(function (el) {
        var box = el.getBoundingClientRect();
        if (box.bottom < 0 || box.top > vh) return;
        var progress = (box.top + box.height / 2 - vh / 2) / vh; // de -1 à 1 environ
        var shift = Math.max(-7.5, Math.min(7.5, progress * parseFloat(el.dataset.parallax) * -60));
        var img = el.querySelector("img");
        if (img) img.style.transform = "translate3d(0," + shift.toFixed(2) + "%,0)";
      });
      ticking = false;
    }
    window.addEventListener("scroll", function () { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
    window.addEventListener("resize", update);
    update();
  }

  /* Boutons aimantés : suivent doucement le pointeur */
  if (finePointer && !reduce) {
    document.querySelectorAll("[data-magnet]").forEach(function (btn) {
      btn.addEventListener("pointermove", function (e) {
        var r = btn.getBoundingClientRect();
        var x = (e.clientX - r.left - r.width / 2) * 0.18;
        var y = (e.clientY - r.top - r.height / 2) * 0.28;
        btn.style.transform = "translate(" + x.toFixed(1) + "px," + y.toFixed(1) + "px)";
      });
      btn.addEventListener("pointerleave", function () { btn.style.transform = ""; });
    });
  }
})();
