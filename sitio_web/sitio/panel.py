"""Panel privado (/panel): publicar artículos, subir artefactos y documentos, editar el perfil."""
import re
import time
from datetime import datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .extensions import db, login
from .models import PERFIL_POR_DEFECTO, Articulo, Artefacto, Documento, Usuario, ahora, guardar_perfil, perfil
from .utils import (EXT_ARCHIVO, EXT_DOCUMENTO, EXT_HTML, EXT_IMAGEN, borrar_archivo, guardar_archivo,
                    normalizar_etiquetas, render_markdown, slug_unico)

bp = Blueprint("panel", __name__, url_prefix="/panel")

EXT_POR_TIPO = {"html": EXT_HTML, "imagen": EXT_IMAGEN, "archivo": EXT_ARCHIVO}


@bp.before_request
def exigir_sesion():
    if request.endpoint != "panel.entrar" and not current_user.is_authenticated:
        return login.unauthorized()


def _url_valida(url):
    return bool(re.fullmatch(r"https?://\S+", url or ""))


def _destino_seguro(destino):
    if destino and destino.startswith("/") and not destino.startswith("//") and "\\" not in destino:
        return destino
    return url_for(".inicio")


def _subir(campo, carpeta, permitidas, nuevos):
    """Guarda el archivo del campo si se envió; lo anota en `nuevos` para poder deshacerlo si algo falla."""
    archivo = request.files.get(campo)
    if not archivo or not archivo.filename:
        return None
    datos = guardar_archivo(archivo, carpeta, permitidas)
    nuevos.append((carpeta, datos["archivo"]))
    return datos


def _deshacer(nuevos, errores):
    for carpeta, nombre in nuevos:
        borrar_archivo(carpeta, nombre)
    for e in errores:
        flash(e, "error")


# ---------------------------------------------------------------- sesión
@bp.route("/entrar", methods=["GET", "POST"])
def entrar():
    if current_user.is_authenticated:
        return redirect(url_for(".inicio"))
    hay_admin = db.session.scalar(db.select(db.func.count(Usuario.id))) > 0
    if request.method == "POST":
        u = db.session.scalar(db.select(Usuario).filter_by(usuario=request.form.get("usuario", "").strip()))
        if u and u.verificar_clave(request.form.get("clave", "")):
            login_user(u, remember=bool(request.form.get("recordar")))
            return redirect(_destino_seguro(request.args.get("next")))
        time.sleep(1)
        flash("Usuario o contraseña incorrectos.", "error")
    return render_template("panel/entrar.html", hay_admin=hay_admin)


@bp.post("/salir")
@login_required
def salir():
    logout_user()
    flash("Sesión cerrada.", "ok")
    return redirect(url_for("publico.inicio"))


@bp.route("/")
def inicio():
    def contar(modelo, **filtro):
        return db.session.scalar(db.select(db.func.count(modelo.id)).filter_by(**filtro))

    resumen = {
        "articulos": (contar(Articulo, publicado=True), contar(Articulo, publicado=False)),
        "artefactos": (contar(Artefacto, publicado=True), contar(Artefacto, publicado=False)),
        "documentos": (contar(Documento, publicado=True), contar(Documento, publicado=False)),
    }
    recientes = db.session.scalars(db.select(Articulo).order_by(Articulo.actualizado.desc()).limit(5)).all()
    return render_template("panel/inicio.html", resumen=resumen, recientes=recientes)


# ---------------------------------------------------------------- artículos
@bp.route("/articulos")
def articulos():
    lista = db.session.scalars(db.select(Articulo).order_by(Articulo.publicado, Articulo.actualizado.desc())).all()
    return render_template("panel/articulos.html", lista=lista)


@bp.route("/articulos/nuevo", methods=["GET", "POST"], defaults={"id": None})
@bp.route("/articulos/<int:id>/editar", methods=["GET", "POST"])
def articulo_form(id):
    a = db.get_or_404(Articulo, id) if id else Articulo(tipo="analisis", publicado=False)
    if request.method == "GET":
        v = {"titulo": a.titulo or "", "tipo": a.tipo, "resumen": a.resumen or "", "contenido": a.contenido or "",
             "etiquetas": a.etiquetas or "",
             "fecha": a.fecha_publicacion.strftime("%Y-%m-%d") if a.fecha_publicacion else ""}
        return render_template("panel/articulo_form.html", a=a, v=v, tipos=Articulo.TIPOS)

    f = request.form
    v = {k: f.get(k, "").strip() for k in ("titulo", "tipo", "resumen", "contenido", "etiquetas", "fecha")}
    publicar = f.get("accion") == "publicar"
    errores = [] if v["titulo"] else ["El título es obligatorio."]
    if v["tipo"] not in Articulo.TIPOS:
        errores.append("Elija si el artículo es de análisis o de opinión.")
    if publicar and not v["contenido"]:
        errores.append("No se puede publicar un artículo sin contenido.")
    fecha = None
    if v["fecha"]:
        try:
            fecha = datetime.combine(datetime.strptime(v["fecha"], "%Y-%m-%d").date(), ahora().time())
        except ValueError:
            errores.append("La fecha de publicación no es válida.")
    nuevos, portada = [], None
    if not errores:
        try:
            portada = _subir("portada", "imagenes", EXT_IMAGEN, nuevos)
        except ValueError as e:
            errores.append(f"Portada: {e}")
    if errores:
        _deshacer(nuevos, errores)
        return render_template("panel/articulo_form.html", a=a, v=v, tipos=Articulo.TIPOS), 400

    portada_vieja = a.portada if (portada or f.get("quitar_portada")) else None
    if portada:
        a.portada = portada["archivo"]
    elif f.get("quitar_portada"):
        a.portada = None
    a.titulo, a.tipo, a.resumen, a.contenido = v["titulo"], v["tipo"], v["resumen"], v["contenido"]
    a.etiquetas = normalizar_etiquetas(v["etiquetas"])
    a.slug = slug_unico(Articulo, v["titulo"], a.id) if not a.slug or f.get("regenerar_slug") else a.slug
    a.publicado = publicar
    if fecha:
        a.fecha_publicacion = fecha
    elif publicar and not a.fecha_publicacion:
        a.fecha_publicacion = ahora()
    db.session.add(a)
    db.session.commit()
    if portada_vieja:
        borrar_archivo("imagenes", portada_vieja)
    flash("Artículo publicado." if publicar else "Borrador guardado.", "ok")
    return redirect(url_for(".articulo_form", id=a.id))


@bp.post("/articulos/<int:id>/borrar")
def articulo_borrar(id):
    a = db.get_or_404(Articulo, id)
    portada = a.portada
    db.session.delete(a)
    db.session.commit()
    borrar_archivo("imagenes", portada)
    flash(f"Se borró el artículo «{a.titulo}».", "ok")
    return redirect(url_for(".articulos"))


@bp.post("/vista-previa")
def vista_previa():
    return jsonify(html=str(render_markdown(request.form.get("contenido", ""))))


@bp.post("/imagenes")
def subir_imagen():
    try:
        datos = guardar_archivo(request.files.get("imagen"), "imagenes", EXT_IMAGEN)
    except ValueError as e:
        return jsonify(error=str(e)), 400
    return jsonify(url=url_for("publico.archivo", carpeta="imagenes", nombre=datos["archivo"]))


# ---------------------------------------------------------------- artefactos
@bp.route("/artefactos")
def artefactos():
    lista = db.session.scalars(db.select(Artefacto).order_by(Artefacto.creado.desc())).all()
    return render_template("panel/artefactos.html", lista=lista)


@bp.route("/artefactos/nuevo", methods=["GET", "POST"], defaults={"id": None})
@bp.route("/artefactos/<int:id>/editar", methods=["GET", "POST"])
def artefacto_form(id):
    a = db.get_or_404(Artefacto, id) if id else Artefacto(tipo="html", publicado=True, destacado=False)
    contexto = {"a": a, "tipos": Artefacto.TIPOS, "ext": {t: ", ".join(sorted(e)) for t, e in EXT_POR_TIPO.items()}}
    if request.method == "GET":
        contexto["v"] = {"titulo": a.titulo or "", "tipo": a.tipo, "descripcion": a.descripcion or "",
                         "enlace": a.enlace or "", "etiquetas": a.etiquetas or "",
                         "destacado": a.destacado, "publicado": a.publicado}
        return render_template("panel/artefacto_form.html", **contexto)

    f = request.form
    v = {k: f.get(k, "").strip() for k in ("titulo", "tipo", "descripcion", "enlace", "etiquetas")}
    v.update(destacado=bool(f.get("destacado")), publicado=bool(f.get("publicado")))
    contexto["v"] = v
    errores = [] if v["titulo"] else ["El título es obligatorio."]
    if v["tipo"] not in Artefacto.TIPOS:
        errores.append("Elija el tipo de artefacto.")
    elif v["tipo"] == "enlace" and not _url_valida(v["enlace"]):
        errores.append("Escriba un enlace completo que empiece por https://")
    elif v["tipo"] != "enlace" and v["enlace"] and not _url_valida(v["enlace"]):
        errores.append("El enlace complementario debe empezar por https://")
    nuevos, archivo, miniatura = [], None, None
    if not errores:
        try:
            if v["tipo"] != "enlace":
                archivo = _subir("archivo", "artefactos", EXT_POR_TIPO[v["tipo"]], nuevos)
                misma_familia = a.archivo and a.tipo == v["tipo"]
                if not archivo and not misma_familia:
                    errores.append("Suba el archivo del artefacto.")
            miniatura = _subir("miniatura", "imagenes", EXT_IMAGEN, nuevos)
        except ValueError as e:
            errores.append(str(e))
    if errores:
        _deshacer(nuevos, errores)
        return render_template("panel/artefacto_form.html", **contexto), 400

    viejos = []
    if archivo or (v["tipo"] == "enlace" and a.archivo):
        viejos.append(("artefactos", a.archivo))
        a.archivo, a.nombre_original, a.tamano = (archivo["archivo"], archivo["nombre_original"], archivo["tamano"]) \
            if archivo else (None, None, None)
    if miniatura or f.get("quitar_miniatura"):
        viejos.append(("imagenes", a.miniatura))
        a.miniatura = miniatura["archivo"] if miniatura else None
    a.titulo, a.tipo, a.descripcion, a.enlace = v["titulo"], v["tipo"], v["descripcion"], v["enlace"] or None
    a.etiquetas = normalizar_etiquetas(v["etiquetas"])
    a.destacado, a.publicado = v["destacado"], v["publicado"]
    a.slug = slug_unico(Artefacto, v["titulo"], a.id) if not a.slug or f.get("regenerar_slug") else a.slug
    db.session.add(a)
    db.session.commit()
    for carpeta, nombre in viejos:
        borrar_archivo(carpeta, nombre)
    flash("Artefacto guardado.", "ok")
    return redirect(url_for(".artefacto_form", id=a.id))


@bp.post("/artefactos/<int:id>/borrar")
def artefacto_borrar(id):
    a = db.get_or_404(Artefacto, id)
    archivos = [("artefactos", a.archivo), ("imagenes", a.miniatura)]
    db.session.delete(a)
    db.session.commit()
    for carpeta, nombre in archivos:
        borrar_archivo(carpeta, nombre)
    flash(f"Se borró el artefacto «{a.titulo}».", "ok")
    return redirect(url_for(".artefactos"))


# ---------------------------------------------------------------- documentos
@bp.route("/documentos")
def documentos():
    lista = db.session.scalars(db.select(Documento).order_by(Documento.creado.desc())).all()
    return render_template("panel/documentos.html", lista=lista)


@bp.route("/documentos/nuevo", methods=["GET", "POST"], defaults={"id": None})
@bp.route("/documentos/<int:id>/editar", methods=["GET", "POST"])
def documento_form(id):
    d = db.get_or_404(Documento, id) if id else Documento(categoria="Informe", publicado=True)
    contexto = {"d": d, "categorias": Documento.CATEGORIAS, "ext": ", ".join(sorted(EXT_DOCUMENTO))}
    if request.method == "GET":
        contexto["v"] = {"titulo": d.titulo or "", "descripcion": d.descripcion or "", "categoria": d.categoria or "",
                         "autor": d.autor or "", "anio": d.anio or "", "enlace": d.enlace or "",
                         "etiquetas": d.etiquetas or "", "publicado": d.publicado}
        return render_template("panel/documento_form.html", **contexto)

    f = request.form
    v = {k: f.get(k, "").strip() for k in ("titulo", "descripcion", "categoria", "autor", "anio", "enlace", "etiquetas")}
    v["publicado"] = bool(f.get("publicado"))
    contexto["v"] = v
    errores = [] if v["titulo"] else ["El título es obligatorio."]
    if v["anio"] and not (v["anio"].isdigit() and 1800 <= int(v["anio"]) <= 2200):
        errores.append("El año debe ser un número de cuatro cifras.")
    if v["enlace"] and not _url_valida(v["enlace"]):
        errores.append("El enlace debe empezar por https://")
    nuevos, archivo = [], None
    if not errores:
        try:
            archivo = _subir("archivo", "documentos", EXT_DOCUMENTO, nuevos)
        except ValueError as e:
            errores.append(str(e))
        quitar = f.get("quitar_archivo")
        if not archivo and not v["enlace"] and (not d.archivo or quitar):
            errores.append("Suba el documento o escriba un enlace a él.")
    if errores:
        _deshacer(nuevos, errores)
        return render_template("panel/documento_form.html", **contexto), 400

    viejo = d.archivo if (archivo or f.get("quitar_archivo")) else None
    if archivo:
        d.archivo, d.nombre_original, d.tamano = archivo["archivo"], archivo["nombre_original"], archivo["tamano"]
    elif f.get("quitar_archivo"):
        d.archivo = d.nombre_original = d.tamano = None
    d.titulo, d.descripcion, d.autor, d.enlace = v["titulo"], v["descripcion"], v["autor"], v["enlace"] or None
    d.categoria = v["categoria"] or "Otro"
    d.anio = int(v["anio"]) if v["anio"] else None
    d.etiquetas = normalizar_etiquetas(v["etiquetas"])
    d.publicado = v["publicado"]
    d.slug = slug_unico(Documento, v["titulo"], d.id) if not d.slug or f.get("regenerar_slug") else d.slug
    db.session.add(d)
    db.session.commit()
    borrar_archivo("documentos", viejo)
    flash("Documento guardado.", "ok")
    return redirect(url_for(".documento_form", id=d.id))


@bp.post("/documentos/<int:id>/borrar")
def documento_borrar(id):
    d = db.get_or_404(Documento, id)
    archivo = d.archivo
    db.session.delete(d)
    db.session.commit()
    borrar_archivo("documentos", archivo)
    flash(f"Se borró el documento «{d.titulo}».", "ok")
    return redirect(url_for(".documentos"))


# ---------------------------------------------------------------- perfil y contraseña
@bp.route("/perfil", methods=["GET", "POST"])
def perfil_form():
    if request.method == "GET":
        return render_template("panel/perfil.html", v=perfil())
    v = {k: request.form.get(k, "").strip() for k in PERFIL_POR_DEFECTO if k != "foto"}
    errores = [f"El enlace de {k} debe empezar por https://" for k in ("linkedin", "x", "github")
               if v[k] and not _url_valida(v[k])]
    if not v["nombre"]:
        errores.append("El nombre es obligatorio.")
    nuevos, foto = [], None
    if not errores:
        try:
            foto = _subir("foto", "imagenes", EXT_IMAGEN, nuevos)
        except ValueError as e:
            errores.append(f"Foto: {e}")
    if errores:
        _deshacer(nuevos, errores)
        return render_template("panel/perfil.html", v={**perfil(), **v}), 400
    vieja = perfil()["foto"] if (foto or request.form.get("quitar_foto")) else None
    if foto:
        v["foto"] = foto["archivo"]
    elif request.form.get("quitar_foto"):
        v["foto"] = ""
    guardar_perfil(v)
    borrar_archivo("imagenes", vieja)
    flash("Perfil actualizado.", "ok")
    return redirect(url_for(".perfil_form"))


@bp.post("/clave")
def cambiar_clave():
    actual, nueva = request.form.get("clave_actual", ""), request.form.get("clave_nueva", "")
    if not current_user.verificar_clave(actual):
        flash("La contraseña actual no es correcta.", "error")
    elif len(nueva) < 8:
        flash("La nueva contraseña debe tener al menos 8 caracteres.", "error")
    elif nueva != request.form.get("clave_confirmacion", ""):
        flash("La confirmación no coincide con la nueva contraseña.", "error")
    else:
        current_user.fijar_clave(nueva)
        db.session.commit()
        flash("Contraseña cambiada.", "ok")
    return redirect(url_for(".perfil_form"))
