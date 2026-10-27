"""Páginas públicas: inicio, artículos, artefactos, documentos, sobre mí, archivos, RSS y mapa del sitio."""
from flask import Blueprint, abort, current_app, make_response, render_template, request, send_from_directory
from flask_login import current_user
from sqlalchemy import literal, or_

from .extensions import db
from .models import Articulo, Artefacto, Documento
from .utils import CARPETAS, EXT_AISLADAS, EXT_EN_LINEA, SANDBOX, carpeta_subidas, extension

bp = Blueprint("publico", __name__)


def _visibles(modelo):
    """Lo publicado; con sesión iniciada también los borradores, para revisarlos antes de publicarlos."""
    consulta = db.select(modelo)
    return consulta if current_user.is_authenticated else consulta.filter_by(publicado=True)


def _con_etiqueta(modelo, etiqueta):
    # Las etiquetas se guardan como "a, b, c": se busca ", etiqueta," para no confundir "IA" con "media".
    return (literal(", ") + modelo.etiquetas + literal(",")).icontains(f", {etiqueta},", autoescape=True)


def _buscar(consulta, columnas, q):
    return consulta.where(or_(*[c.icontains(q, autoescape=True) for c in columnas])) if q else consulta


def _paginar(consulta):
    return db.paginate(consulta, page=request.args.get("pagina", 1, type=int),
                       per_page=current_app.config["POR_PAGINA"], error_out=False)


def _uno_o_404(modelo, slug):
    objeto = db.first_or_404(db.select(modelo).filter_by(slug=slug))
    if not objeto.publicado and not current_user.is_authenticated:
        abort(404)
    return objeto


# ---------------------------------------------------------------- inicio y sobre mí
@bp.route("/")
def inicio():
    articulos = db.session.scalars(db.select(Articulo).filter_by(publicado=True)
                                   .order_by(Articulo.fecha_publicacion.desc()).limit(3)).all()
    artefactos = db.session.scalars(db.select(Artefacto).filter_by(publicado=True)
                                    .order_by(Artefacto.destacado.desc(), Artefacto.creado.desc()).limit(3)).all()
    documentos = db.session.scalars(db.select(Documento).filter_by(publicado=True)
                                    .order_by(Documento.creado.desc()).limit(5)).all()
    return render_template("inicio.html", articulos=articulos, artefactos=artefactos, documentos=documentos)


@bp.route("/sobre-mi")
def sobre_mi():
    return render_template("sobre_mi.html")


# ---------------------------------------------------------------- artículos
@bp.route("/articulos/")
def articulos():
    tipo, etiqueta, q = request.args.get("tipo", ""), request.args.get("etiqueta", "").strip(), request.args.get("q", "").strip()
    consulta = _visibles(Articulo)
    if tipo in Articulo.TIPOS:
        consulta = consulta.filter_by(tipo=tipo)
    if etiqueta:
        consulta = consulta.where(_con_etiqueta(Articulo, etiqueta))
    consulta = _buscar(consulta, [Articulo.titulo, Articulo.resumen, Articulo.contenido, Articulo.etiquetas], q)
    orden = (Articulo.fecha_publicacion.is_(None).desc(), Articulo.fecha_publicacion.desc(), Articulo.creado.desc())
    return render_template("articulos/lista.html", pagina=_paginar(consulta.order_by(*orden)),
                           tipo=tipo, etiqueta=etiqueta, q=q)


@bp.route("/articulos/<slug>")
def articulo(slug):
    a = _uno_o_404(Articulo, slug)
    relacionados = db.session.scalars(db.select(Articulo).filter_by(publicado=True, tipo=a.tipo)
                                      .where(Articulo.id != a.id)
                                      .order_by(Articulo.fecha_publicacion.desc()).limit(3)).all()
    return render_template("articulos/detalle.html", a=a, relacionados=relacionados)


@bp.route("/articulos/feed.xml")
def feed():
    articulos = db.session.scalars(db.select(Articulo).filter_by(publicado=True)
                                   .order_by(Articulo.fecha_publicacion.desc()).limit(20)).all()
    resp = make_response(render_template("feed.xml", articulos=articulos))
    resp.mimetype = "application/rss+xml"
    return resp


# ---------------------------------------------------------------- artefactos
@bp.route("/artefactos/")
def artefactos():
    tipo, etiqueta, q = request.args.get("tipo", ""), request.args.get("etiqueta", "").strip(), request.args.get("q", "").strip()
    consulta = _visibles(Artefacto)
    if tipo in Artefacto.TIPOS:
        consulta = consulta.filter_by(tipo=tipo)
    if etiqueta:
        consulta = consulta.where(_con_etiqueta(Artefacto, etiqueta))
    consulta = _buscar(consulta, [Artefacto.titulo, Artefacto.descripcion, Artefacto.etiquetas], q)
    consulta = consulta.order_by(Artefacto.destacado.desc(), Artefacto.creado.desc())
    return render_template("artefactos/lista.html", pagina=_paginar(consulta), tipo=tipo, etiqueta=etiqueta, q=q)


@bp.route("/artefactos/<slug>")
def artefacto(slug):
    return render_template("artefactos/detalle.html", a=_uno_o_404(Artefacto, slug))


@bp.route("/artefactos/<slug>/descargar")
def descargar_artefacto(slug):
    a = _uno_o_404(Artefacto, slug)
    if not a.archivo:
        abort(404)
    return send_from_directory(carpeta_subidas("artefactos"), a.archivo, as_attachment=True,
                               download_name=a.nombre_original or a.archivo)


# ---------------------------------------------------------------- documentos
@bp.route("/documentos/")
def documentos():
    categoria, q = request.args.get("categoria", "").strip(), request.args.get("q", "").strip()
    consulta = _visibles(Documento)
    if categoria:
        consulta = consulta.filter_by(categoria=categoria)
    consulta = _buscar(consulta, [Documento.titulo, Documento.descripcion, Documento.autor, Documento.etiquetas], q)
    categorias = db.session.scalars(db.select(Documento.categoria).filter_by(publicado=True)
                                    .distinct().order_by(Documento.categoria)).all()
    return render_template("documentos/lista.html", pagina=_paginar(consulta.order_by(Documento.creado.desc())),
                           categoria=categoria, categorias=[c for c in categorias if c], q=q)


@bp.route("/documentos/<slug>")
def documento(slug):
    return render_template("documentos/detalle.html", d=_uno_o_404(Documento, slug))


@bp.route("/documentos/<slug>/descargar")
def descargar_documento(slug):
    d = _uno_o_404(Documento, slug)
    if not d.archivo:
        abort(404)
    return send_from_directory(carpeta_subidas("documentos"), d.archivo, as_attachment=True,
                               download_name=d.nombre_original or d.archivo)


# ---------------------------------------------------------------- archivos subidos
@bp.route("/archivos/<carpeta>/<nombre>")
def archivo(carpeta, nombre):
    if carpeta not in CARPETAS:
        abort(404)
    # Los archivos de artefactos y documentos solo se sirven mientras su ficha esté publicada.
    dueno = {"artefactos": Artefacto, "documentos": Documento}.get(carpeta)
    if dueno is not None and not current_user.is_authenticated:
        if db.session.scalar(db.select(dueno.id).filter_by(archivo=nombre, publicado=True)) is None:
            abort(404)
    ext = extension(nombre)
    resp = send_from_directory(carpeta_subidas(carpeta), nombre, as_attachment=ext not in EXT_EN_LINEA,
                               max_age=0 if current_user.is_authenticated else 3600)
    if ext in EXT_AISLADAS:
        resp.headers["Content-Security-Policy"] = f"sandbox {SANDBOX}"
    return resp


# ---------------------------------------------------------------- buscadores
@bp.route("/robots.txt")
def robots():
    resp = make_response(render_template("robots.txt"))
    resp.mimetype = "text/plain"
    return resp


@bp.route("/sitemap.xml")
def sitemap():
    publicados = {m: db.session.scalars(db.select(m).filter_by(publicado=True)).all()
                  for m in (Articulo, Artefacto, Documento)}
    resp = make_response(render_template("sitemap.xml", articulos=publicados[Articulo],
                                         artefactos=publicados[Artefacto], documentos=publicados[Documento]))
    resp.mimetype = "application/xml"
    return resp
