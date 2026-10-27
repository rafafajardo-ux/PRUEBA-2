// Menú en móvil y botón «Copiar enlace».
(function () {
  var boton = document.querySelector(".menu-boton");
  var menu = document.getElementById("menu");
  if (boton && menu) {
    boton.addEventListener("click", function () {
      var abierto = boton.getAttribute("aria-expanded") === "true";
      boton.setAttribute("aria-expanded", String(!abierto));
      menu.classList.toggle("abierto", !abierto);
    });
  }
  document.querySelectorAll("[data-copiar]").forEach(function (b) {
    b.addEventListener("click", function () {
      var original = b.textContent;
      var listo = function () { b.textContent = "¡Copiado!"; setTimeout(function () { b.textContent = original; }, 1800); };
      if (navigator.clipboard) {
        navigator.clipboard.writeText(b.dataset.copiar).then(listo, function () { window.prompt("Copie el enlace:", b.dataset.copiar); });
      } else {
        window.prompt("Copie el enlace:", b.dataset.copiar);
      }
    });
  });
})();
