"""Sitio web personal de Rafael Fajardo Moreno (Flask).

Secciones públicas: inicio, artículos de análisis y opinión, artefactos, documentos de interés y "sobre mí".
Panel privado (/panel): publicar artículos, subir artefactos y documentos, editar el perfil."""
import os
import secrets
from pathlib import Path

from flask import Flask, render_template, request
from flask_login import current_user
from flask_wtf.csrf import CSRFError
from werkzeug.middleware.proxy_fix import ProxyFix

from .extensions import csrf, db, login
from .utils import CARPETAS, fecha_es, fecha_rfc822, render_markdown

BASE = Path(__file__).resolve().parent.parent


def _clave_secreta(instancia: Path) -> str:
    """SECRET_KEY del entorno o, si no existe, una aleatoria guardada en la carpeta de datos (persiste entre reinicios)."""
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    archivo = instancia / "clave_secreta.txt"
    if not archivo.exists():
        archivo.write_text(secrets.token_hex(32), encoding="utf-8")
        archivo.chmod(0o600)
    return archivo.read_text(encoding="utf-8").strip()


def create_app(ajustes: dict | None = None) -> Flask:
    app = Flask(__name__)
    instancia = Path(os.environ.get("CARPETA_DATOS", BASE / "instance")).resolve()
    app.config.update(
        CARPETA_DATOS=instancia,
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL") or f"sqlite:///{instancia / 'sitio.db'}",
        MAX_CONTENT_LENGTH=int(os.environ.get("MAX_MB", "100")) * 1024 * 1024,
        URL_SITIO=os.environ.get("URL_SITIO", "https://www.rafaelfajardomoreno.com").rstrip("/"),
        POR_PAGINA=9,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SEGURA", "0") == "1",
        REMEMBER_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SECURE=os.environ.get("COOKIE_SEGURA", "0") == "1",
        WTF_CSRF_TIME_LIMIT=None,
    )
    app.config.update(ajustes or {})
    instancia = Path(app.config["CARPETA_DATOS"])
    for carpeta in CARPETAS:
        (instancia / "subidas" / carpeta).mkdir(parents=True, exist_ok=True)
    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = _clave_secreta(instancia)

    if os.environ.get("DETRAS_DE_PROXY", "0") == "1":
        # Detrás de Nginx, Render, Railway, etc.: respeta https y el dominio que reporta el proxy.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    csrf.init_app(app)
    login.init_app(app)
    login.login_view = "panel.entrar"
    login.login_message = "Inicie sesión para entrar al panel."
    login.session_protection = "strong"

    from . import models
    from .cli import registrar_comandos
    from .panel import bp as panel_bp
    from .publico import bp as publico_bp

    app.register_blueprint(publico_bp)
    app.register_blueprint(panel_bp)
    registrar_comandos(app)

    app.jinja_env.filters["fecha"] = fecha_es
    app.jinja_env.filters["markdown"] = render_markdown
    app.jinja_env.filters["rfc822"] = fecha_rfc822

    @app.context_processor
    def contexto_global():
        return {"perfil": models.perfil(), "secciones": SECCIONES, "anio_actual": models.ahora().year}

    @app.after_request
    def cabeceras_seguridad(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if current_user.is_authenticated or request.blueprint == "panel":
            resp.headers.setdefault("Cache-Control", "no-store")
        return resp

    @app.errorhandler(404)
    def no_encontrado(_):
        return render_template("errores/error.html", codigo=404, mensaje="La página que busca no existe o fue retirada."), 404

    @app.errorhandler(CSRFError)
    def formulario_vencido(_):
        return render_template("errores/error.html", codigo=400,
                               mensaje="El formulario venció o no es válido. Vuelva atrás, recargue la página e intente de nuevo."), 400

    @app.errorhandler(413)
    def muy_grande(_):
        limite = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
        return render_template("errores/error.html", codigo=413, mensaje=f"El archivo supera el límite de {limite} MB."), 413

    with app.app_context():
        db.create_all()
        models.crear_admin_desde_entorno()
    return app


# Menú principal: (endpoint, etiqueta, páginas en las que el enlace queda resaltado)
SECCIONES = [
    ("publico.inicio", "Inicio", {"publico.inicio"}),
    ("publico.articulos", "Artículos", {"publico.articulos", "publico.articulo"}),
    ("publico.artefactos", "Artefactos", {"publico.artefactos", "publico.artefacto"}),
    ("publico.documentos", "Documentos", {"publico.documentos", "publico.documento"}),
    ("publico.sobre_mi", "Sobre mí", {"publico.sobre_mi"}),
]
