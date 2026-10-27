"""Modelos: usuario administrador, artículos, artefactos, documentos y ajustes del perfil."""
import os
from datetime import datetime, timezone

from flask import g
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login
from .utils import extension, render_markdown, tamano_legible, texto_plano


def ahora():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _lista(etiquetas):
    return [e.strip() for e in (etiquetas or "").split(",") if e.strip()]


class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(80), unique=True, nullable=False)
    clave_hash = db.Column(db.String(255), nullable=False)

    def fijar_clave(self, clave):
        self.clave_hash = generate_password_hash(clave)

    def verificar_clave(self, clave):
        return check_password_hash(self.clave_hash, clave)


@login.user_loader
def cargar_usuario(id_usuario):
    return db.session.get(Usuario, int(id_usuario))


class Articulo(db.Model):
    TIPOS = {"analisis": "Análisis", "opinion": "Opinión"}

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False, index=True)
    tipo = db.Column(db.String(20), nullable=False, default="analisis")
    resumen = db.Column(db.Text, default="")
    contenido = db.Column(db.Text, default="")
    portada = db.Column(db.String(255))
    etiquetas = db.Column(db.String(300), default="")
    publicado = db.Column(db.Boolean, default=False, nullable=False)
    fecha_publicacion = db.Column(db.DateTime)
    creado = db.Column(db.DateTime, default=ahora)
    actualizado = db.Column(db.DateTime, default=ahora, onupdate=ahora)

    @property
    def tipo_nombre(self):
        return self.TIPOS.get(self.tipo, self.tipo)

    @property
    def html(self):
        return render_markdown(self.contenido)

    @property
    def lista_etiquetas(self):
        return _lista(self.etiquetas)

    @property
    def minutos_lectura(self):
        return max(1, round(len(texto_plano(self.contenido).split()) / 200))

    @property
    def extracto(self):
        if self.resumen:
            return self.resumen
        texto = texto_plano(self.contenido)
        return texto[:220].rsplit(" ", 1)[0] + "…" if len(texto) > 220 else texto


class Artefacto(db.Model):
    TIPOS = {"html": "Página interactiva", "imagen": "Imagen o figura", "archivo": "Archivo descargable",
             "enlace": "Enlace externo"}

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False, index=True)
    tipo = db.Column(db.String(20), nullable=False, default="html")
    descripcion = db.Column(db.Text, default="")
    archivo = db.Column(db.String(255))
    nombre_original = db.Column(db.String(255))
    tamano = db.Column(db.Integer)
    enlace = db.Column(db.String(500))
    miniatura = db.Column(db.String(255))
    etiquetas = db.Column(db.String(300), default="")
    destacado = db.Column(db.Boolean, default=False, nullable=False)
    publicado = db.Column(db.Boolean, default=True, nullable=False)
    creado = db.Column(db.DateTime, default=ahora)
    actualizado = db.Column(db.DateTime, default=ahora, onupdate=ahora)

    @property
    def tipo_nombre(self):
        return self.TIPOS.get(self.tipo, self.tipo)

    @property
    def lista_etiquetas(self):
        return _lista(self.etiquetas)

    @property
    def extension(self):
        return extension(self.nombre_original or self.archivo)

    @property
    def tamano_legible(self):
        return tamano_legible(self.tamano)

    @property
    def imagen_tarjeta(self):
        """Imagen para la tarjeta del listado: la miniatura o, si es una figura, la propia imagen."""
        if self.miniatura:
            return ("imagenes", self.miniatura)
        if self.tipo == "imagen" and self.archivo:
            return ("artefactos", self.archivo)
        return None


class Documento(db.Model):
    CATEGORIAS = ["Informe", "Estudio o investigación", "Normativa", "Presentación", "Datos", "Artículo académico",
                  "Libro o capítulo", "Otro"]

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False, index=True)
    descripcion = db.Column(db.Text, default="")
    categoria = db.Column(db.String(80), default="Otro")
    autor = db.Column(db.String(200), default="")
    anio = db.Column(db.Integer)
    archivo = db.Column(db.String(255))
    nombre_original = db.Column(db.String(255))
    tamano = db.Column(db.Integer)
    enlace = db.Column(db.String(500))
    etiquetas = db.Column(db.String(300), default="")
    publicado = db.Column(db.Boolean, default=True, nullable=False)
    creado = db.Column(db.DateTime, default=ahora)
    actualizado = db.Column(db.DateTime, default=ahora, onupdate=ahora)

    @property
    def lista_etiquetas(self):
        return _lista(self.etiquetas)

    @property
    def extension(self):
        return extension(self.nombre_original or self.archivo)

    @property
    def tamano_legible(self):
        return tamano_legible(self.tamano)

    @property
    def es_pdf(self):
        return self.extension == "pdf"


class Ajuste(db.Model):
    clave = db.Column(db.String(50), primary_key=True)
    valor = db.Column(db.Text, default="")


PERFIL_POR_DEFECTO = {
    "nombre": "Rafael Fajardo Moreno",
    "titular": "Análisis, datos y opinión",
    "presentacion": "Artículos de análisis y de opinión, artefactos interactivos y documentos de interés.",
    "biografia": "",
    "foto": "",
    "correo": "",
    "linkedin": "",
    "x": "",
    "github": "",
    "ubicacion": "",
}


def perfil() -> dict:
    if "perfil" not in g:
        datos = dict(PERFIL_POR_DEFECTO)
        datos.update({a.clave: a.valor or "" for a in db.session.scalars(db.select(Ajuste))})
        g.perfil = datos
    return g.perfil


def guardar_perfil(valores: dict) -> None:
    for clave, valor in valores.items():
        if clave in PERFIL_POR_DEFECTO:
            db.session.merge(Ajuste(clave=clave, valor=valor))
    db.session.commit()
    g.pop("perfil", None)


def crear_admin_desde_entorno() -> None:
    """Primer arranque en un servidor: crea el administrador con ADMIN_USUARIO y ADMIN_CLAVE si aún no hay ninguno."""
    usuario, clave = os.environ.get("ADMIN_USUARIO"), os.environ.get("ADMIN_CLAVE")
    if usuario and clave and db.session.scalar(db.select(db.func.count(Usuario.id))) == 0:
        admin = Usuario(usuario=usuario)
        admin.fijar_clave(clave)
        db.session.add(admin)
        db.session.commit()
