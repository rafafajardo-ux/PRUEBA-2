// Panel: confirmación al borrar, editor Markdown con vista previa e inserción de imágenes, campos según el tipo de artefacto.
(function () {
  var token = document.querySelector('meta[name="csrf-token"]').content;

  function enviar(url, datos) {
    return fetch(url, { method: "POST", body: datos, headers: { "X-CSRFToken": token }, credentials: "same-origin" })
      .then(function (r) {
        return r.json().catch(function () { return { error: "Respuesta inesperada del servidor (" + r.status + ")." }; })
          .then(function (j) { if (!r.ok && !j.error) { j.error = "Error " + r.status; } return j; });
      });
  }

  document.querySelectorAll("form[data-confirmar]").forEach(function (f) {
    f.addEventListener("submit", function (e) { if (!window.confirm(f.dataset.confirmar)) { e.preventDefault(); } });
  });

  document.querySelectorAll("[data-editor]").forEach(function (ed) {
    var texto = ed.querySelector("[data-editor-texto]");
    var previa = ed.querySelector("[data-editor-previa]");
    var pestanas = ed.querySelectorAll("[data-modo]");

    pestanas.forEach(function (p) {
      p.addEventListener("click", function () {
        var verPrevia = p.dataset.modo === "previa";
        pestanas.forEach(function (o) { o.setAttribute("aria-selected", String(o === p)); });
        texto.hidden = verPrevia;
        previa.hidden = !verPrevia;
        if (verPrevia) {
          previa.innerHTML = "<p class='ayuda'>Generando vista previa…</p>";
          var datos = new FormData();
          datos.append("contenido", texto.value);
          enviar(ed.dataset.urlPrevia, datos).then(function (j) {
            if (j.error) { previa.textContent = j.error; return; }
            previa.innerHTML = j.html || "<p class='ayuda'>(Sin contenido)</p>";
          });
        }
      });
    });

    var botonImagen = ed.querySelector("[data-insertar-imagen]");
    var archivo = ed.querySelector("[data-archivo-imagen]");
    var estado = ed.querySelector("[data-estado-imagen]");
    if (botonImagen && archivo) {
      botonImagen.addEventListener("click", function () { archivo.click(); });
      archivo.addEventListener("change", function () {
        if (!archivo.files.length) { return; }
        var f = archivo.files[0];
        var datos = new FormData();
        datos.append("imagen", f);
        estado.textContent = "Subiendo " + f.name + "…";
        enviar(ed.dataset.urlImagenes, datos).then(function (j) {
          archivo.value = "";
          if (j.error) { estado.textContent = j.error; return; }
          var alt = f.name.replace(/\.[^.]+$/, "").replace(/[-_]+/g, " ");
          var md = "\n![" + alt + "](" + j.url + ")\n";
          var i = texto.selectionStart || texto.value.length;
          texto.value = texto.value.slice(0, i) + md + texto.value.slice(texto.selectionEnd || i);
          texto.focus();
          texto.selectionStart = texto.selectionEnd = i + md.length;
          estado.textContent = "Imagen insertada. Puede cambiar el texto entre corchetes por una descripción.";
        }).catch(function () { estado.textContent = "No se pudo subir la imagen."; });
      });
    }
  });

  var formArtefacto = document.querySelector("[data-form-artefacto]");
  if (formArtefacto) {
    var actualizar = function () {
      var marcado = formArtefacto.querySelector('input[name="tipo"]:checked');
      var tipo = marcado ? marcado.value : "";
      formArtefacto.querySelectorAll("[data-solo-tipos]").forEach(function (el) {
        el.hidden = tipo && el.dataset.soloTipos.split(" ").indexOf(tipo) === -1;
      });
      var entrada = formArtefacto.querySelector("#archivo");
      if (entrada) { entrada.accept = { html: ".html,.htm", imagen: "image/*" }[tipo] || ""; }
      var enlace = formArtefacto.querySelector("#enlace");
      if (enlace) { enlace.required = tipo === "enlace"; }
    };
    formArtefacto.querySelectorAll('input[name="tipo"]').forEach(function (r) { r.addEventListener("change", actualizar); });
    actualizar();
  }
})();
