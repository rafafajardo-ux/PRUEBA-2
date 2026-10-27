"""Utilidades: fechas en español, Markdown seguro, slugs y manejo de archivos subidos."""
import re
import unicodedata
import uuid
from datetime import timezone
from email.utils import format_datetime
from pathlib import Path

import markdown as md
import nh3
from flask import current_app
from markupsafe import Markup

CARPETAS = ("imagenes", "documentos", "artefactos")

EXT_IMAGEN = {"png", "jpg", "jpeg", "gif", "webp", "svg"}
EXT_HTML = {"html", "htm"}
EXT_DOCUMENTO = {"pdf", "doc", "docx", "odt", "rtf", "txt", "md", "epub", "xls", "xlsx", "ods", "csv",
                 "ppt", "pptx", "odp", "zip"}
EXT_ARCHIVO = {"ipynb", "py", "r", "sql", "csv", "json", "parquet", "xlsx", "xls", "zip", "txt", "md", "pdf",
               "docx", "pptx", "joblib", "pbix", "twbx", "kml", "geojson"}
# Lo que se puede mostrar dentro del sitio; el resto se entrega como descarga.
EXT_EN_LINEA = EXT_IMAGEN | EXT_HTML | {"pdf"}
# Contenido activo: se sirve con CSP "sandbox" para que su JavaScript corra en un origen aislado, sin acceso a la sesión.
EXT_AISLADAS = EXT_HTML | {"svg", "xml", "xhtml"}
SANDBOX = "allow-scripts allow-popups allow-popups-to-escape-sandbox allow-forms allow-modals allow-downloads"

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]


def fecha_es(fecha, corto=False):
    if not fecha:
        return ""
    if corto:
        return f"{fecha.day} {MESES[fecha.month - 1][:3]} {fecha.year}"
    return f"{fecha.day} de {MESES[fecha.month - 1]} de {fecha.year}"


def fecha_rfc822(fecha):
    return format_datetime(fecha.replace(tzinfo=timezone.utc)) if fecha else ""


# ---------------------------------------------------------------- Markdown → HTML saneado
_ATRIBUTOS = {etiqueta: set(attrs) for etiqueta, attrs in nh3.ALLOWED_ATTRIBUTES.items()}
_ATRIBUTOS["*"] = _ATRIBUTOS.get("*", set()) | {"id", "class", "title"}
_ATRIBUTOS["a"] = _ATRIBUTOS.get("a", set()) | {"href", "title"}
_ATRIBUTOS["img"] = _ATRIBUTOS.get("img", set()) | {"title", "loading"}


def render_markdown(texto: str | None) -> Markup:
    html = md.markdown(texto or "", extensions=["abbr", "def_list", "fenced_code", "footnotes", "tables",
                                                "sane_lists", "toc", "smarty"],
                       extension_configs={"tables": {"use_align_attribute": True}})
    return Markup(nh3.clean(html, attributes=_ATRIBUTOS, url_schemes={"http", "https", "mailto"}))


def texto_plano(texto: str | None) -> str:
    return re.sub(r"\s+", " ", nh3.clean(str(render_markdown(texto)), tags=set())).strip()


# ---------------------------------------------------------------- slugs y etiquetas
def slugificar(texto: str, largo: int = 80) -> str:
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return t[:largo].strip("-") or "sin-titulo"


def slug_unico(modelo, texto: str, id_actual: int | None = None) -> str:
    from .extensions import db
    base = slugificar(texto)
    slug, n = base, 2
    while True:
        existente = db.session.scalar(db.select(modelo).filter_by(slug=slug))
        if existente is None or existente.id == id_actual:
            return slug
        slug, n = f"{base}-{n}", n + 1


def normalizar_etiquetas(texto: str | None) -> str:
    vistas, salida = set(), []
    for e in (texto or "").split(","):
        e = e.strip()
        if e and e.lower() not in vistas:
            vistas.add(e.lower())
            salida.append(e)
    return ", ".join(salida)


# ---------------------------------------------------------------- archivos
def extension(nombre: str | None) -> str:
    return Path(nombre or "").suffix.lower().lstrip(".")


def carpeta_subidas(carpeta: str) -> Path:
    if carpeta not in CARPETAS:
        raise ValueError(f"Carpeta desconocida: {carpeta}")
    return Path(current_app.config["CARPETA_DATOS"]) / "subidas" / carpeta


def guardar_archivo(archivo, carpeta: str, permitidas: set[str]) -> dict:
    """Guarda un FileStorage con nombre aleatorio. Devuelve archivo, nombre_original y tamano."""
    if archivo is None or not archivo.filename:
        raise ValueError("No se recibió ningún archivo.")
    original = Path(archivo.filename.replace("\\", "/")).name
    ext = extension(original)
    if ext not in permitidas:
        raise ValueError(f"Tipo de archivo no permitido (.{ext or '?'}). Se aceptan: {', '.join(sorted(permitidas))}.")
    nombre = f"{uuid.uuid4().hex}.{ext}"
    destino = carpeta_subidas(carpeta) / nombre
    archivo.save(destino)
    return {"archivo": nombre, "nombre_original": original[:255], "tamano": destino.stat().st_size}


def borrar_archivo(carpeta: str, nombre: str | None) -> None:
    if nombre:
        (carpeta_subidas(carpeta) / Path(nombre).name).unlink(missing_ok=True)


def tamano_legible(n: int | None) -> str:
    if not n:
        return ""
    for unidad in ("B", "KB", "MB", "GB"):
        if n < 1024 or unidad == "GB":
            return f"{n:.0f} {unidad}" if unidad == "B" else f"{n:.1f} {unidad}".replace(".", ",")
        n /= 1024
