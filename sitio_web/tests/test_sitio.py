"""Pruebas del sitio:  python -m pytest -q"""
import io
import re

import pytest

from sitio import create_app
from sitio.extensions import db
from sitio.models import Articulo, Artefacto, Documento, Usuario

HTML_INTERACTIVO = b"<!doctype html><title>Demo</title><script>document.title='ok'</script><p>Hola</p>"
PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
       b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")


@pytest.fixture
def app(tmp_path):
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False, "SECRET_KEY": "pruebas",
                      "CARPETA_DATOS": tmp_path, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'p.db'}"})
    with app.app_context():
        u = Usuario(usuario="rafael")
        u.fijar_clave("clave-de-prueba")
        db.session.add(u)
        db.session.commit()
    yield app


@pytest.fixture
def cliente(app):
    return app.test_client()


@pytest.fixture
def admin(cliente):
    r = cliente.post("/panel/entrar", data={"usuario": "rafael", "clave": "clave-de-prueba"})
    assert r.status_code == 302
    return cliente


def archivo(contenido, nombre):
    return (io.BytesIO(contenido), nombre)


@pytest.mark.parametrize("ruta", ["/", "/articulos/", "/artefactos/", "/documentos/", "/sobre-mi",
                                  "/articulos/feed.xml", "/sitemap.xml", "/robots.txt", "/panel/entrar"])
def test_paginas_publicas(cliente, ruta):
    assert cliente.get(ruta).status_code == 200


def test_panel_exige_sesion(cliente):
    for ruta in ["/panel/", "/panel/articulos", "/panel/articulos/nuevo", "/panel/perfil"]:
        r = cliente.get(ruta)
        assert r.status_code == 302 and "/panel/entrar" in r.headers["Location"]
    assert cliente.post("/panel/imagenes").status_code == 302


def test_clave_incorrecta(cliente):
    r = cliente.post("/panel/entrar", data={"usuario": "rafael", "clave": "mala"})
    assert r.status_code == 200 and "incorrectos" in r.get_data(as_text=True)


def test_redireccion_externa_bloqueada(cliente):
    r = cliente.post("/panel/entrar?next=//malicioso.com", data={"usuario": "rafael", "clave": "clave-de-prueba"})
    assert r.headers["Location"] == "/panel/"


def test_borrador_y_publicacion_de_articulo(admin, app):
    datos = {"titulo": "Regalías y precio del Brent", "tipo": "analisis", "resumen": "Un análisis.",
             "contenido": "## Contexto\n\nTexto con **datos**.\n\n| A | B |\n|---|--:|\n| 1 | 2 |",
             "etiquetas": "petróleo, regalías, petróleo", "accion": "borrador",
             "portada": archivo(PNG, "portada.png")}
    r = admin.post("/panel/articulos/nuevo", data=datos, content_type="multipart/form-data")
    assert r.status_code == 302
    with app.app_context():
        a = db.session.scalar(db.select(Articulo))
        assert a.slug == "regalias-y-precio-del-brent" and not a.publicado and a.etiquetas == "petróleo, regalías"
        assert a.portada and a.fecha_publicacion is None
        id_, slug = a.id, a.slug

    anonimo = app.test_client()
    assert anonimo.get(f"/articulos/{slug}").status_code == 404
    assert "Regalías y precio" not in anonimo.get("/articulos/").get_data(as_text=True)

    admin.post(f"/panel/articulos/{id_}/editar", data={**{k: v for k, v in datos.items() if k != "portada"},
                                                      "accion": "publicar"})
    html = anonimo.get(f"/articulos/{slug}").get_data(as_text=True)
    assert "<strong>datos</strong>" in html and 'align="right"' in html
    assert "Regalías y precio" in anonimo.get("/articulos/?tipo=analisis").get_data(as_text=True)
    assert "Regalías y precio" not in anonimo.get("/articulos/?tipo=opinion").get_data(as_text=True)
    assert "Regalías y precio" in anonimo.get("/articulos/?etiqueta=regalías").get_data(as_text=True)
    assert "Regalías y precio" in anonimo.get("/articulos/?q=brent").get_data(as_text=True)
    assert "Regalías y precio" in anonimo.get("/articulos/feed.xml").get_data(as_text=True)
    assert "Regalías y precio" in anonimo.get("/").get_data(as_text=True)


def test_slug_unico(admin, app):
    for _ in range(2):
        admin.post("/panel/articulos/nuevo", data={"titulo": "Opinión", "tipo": "opinion", "contenido": "x",
                                                   "accion": "publicar"})
    with app.app_context():
        assert sorted(db.session.scalars(db.select(Articulo.slug))) == ["opinion", "opinion-2"]


def test_markdown_saneado(admin, app):
    admin.post("/panel/articulos/nuevo", data={"titulo": "XSS", "tipo": "opinion", "accion": "publicar",
                                               "contenido": "<script>alert(1)</script>\n\n[x](javascript:alert(1))"
                                                            "\n\n<img src=x onerror=alert(1)>"})
    html = app.test_client().get("/articulos/xss").get_data(as_text=True)
    cuerpo = html.split('class="prosa"')[1]
    assert "<script>alert" not in cuerpo and "javascript:" not in cuerpo and "onerror" not in cuerpo


def test_artefacto_html_aislado(admin, app):
    r = admin.post("/panel/artefactos/nuevo", content_type="multipart/form-data",
                   data={"titulo": "Guía interactiva", "tipo": "html", "publicado": "1", "destacado": "1",
                         "descripcion": "Guía de estudio.", "archivo": archivo(HTML_INTERACTIVO, "guia.html")})
    assert r.status_code == 302
    with app.app_context():
        a = db.session.scalar(db.select(Artefacto))
        assert a.nombre_original == "guia.html" and a.tamano == len(HTML_INTERACTIVO)
        nombre = a.archivo
    anonimo = app.test_client()
    pagina = anonimo.get("/artefactos/guia-interactiva").get_data(as_text=True)
    assert f"/archivos/artefactos/{nombre}" in pagina and 'sandbox="allow-scripts' in pagina
    r = anonimo.get(f"/archivos/artefactos/{nombre}")
    assert r.status_code == 200 and r.headers["Content-Security-Policy"].startswith("sandbox ")
    assert "allow-same-origin" not in r.headers["Content-Security-Policy"]
    r = anonimo.get("/artefactos/guia-interactiva/descargar")
    assert "attachment" in r.headers["Content-Disposition"] and "guia.html" in r.headers["Content-Disposition"]


def test_artefacto_rechaza_extension(admin, app):
    r = admin.post("/panel/artefactos/nuevo", content_type="multipart/form-data",
                   data={"titulo": "Malo", "tipo": "imagen", "archivo": archivo(b"MZ", "virus.exe")})
    assert r.status_code == 400 and "no permitido" in r.get_data(as_text=True)
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(Artefacto.id))) == 0


def test_artefacto_enlace(admin, app):
    r = admin.post("/panel/artefactos/nuevo", data={"titulo": "App", "tipo": "enlace", "enlace": "javascript:alert(1)"})
    assert r.status_code == 400
    admin.post("/panel/artefactos/nuevo", data={"titulo": "App", "tipo": "enlace", "publicado": "1",
                                                "enlace": "https://ejemplo.streamlit.app"})
    assert "https://ejemplo.streamlit.app" in app.test_client().get("/artefactos/app").get_data(as_text=True)


def test_artefacto_oculto_no_sirve_archivo(admin, app):
    admin.post("/panel/artefactos/nuevo", content_type="multipart/form-data",
               data={"titulo": "Privado", "tipo": "html", "archivo": archivo(HTML_INTERACTIVO, "p.html")})
    with app.app_context():
        nombre = db.session.scalar(db.select(Artefacto.archivo))
    anonimo = app.test_client()
    assert anonimo.get("/artefactos/privado").status_code == 404
    assert anonimo.get(f"/archivos/artefactos/{nombre}").status_code == 404
    assert admin.get(f"/archivos/artefactos/{nombre}").status_code == 200


def test_documento_pdf_y_borrado(admin, app):
    r = admin.post("/panel/documentos/nuevo", content_type="multipart/form-data",
                   data={"titulo": "Informe de reservas 2024", "categoria": "Informe", "autor": "ANH", "anio": "2024",
                         "publicado": "1", "archivo": archivo(b"%PDF-1.4 prueba", "IRR 2024.pdf")})
    assert r.status_code == 302
    anonimo = app.test_client()
    lista = anonimo.get("/documentos/?categoria=Informe").get_data(as_text=True)
    assert "Informe de reservas 2024" in lista and "ANH" in lista
    pagina = anonimo.get("/documentos/informe-de-reservas-2024").get_data(as_text=True)
    assert "<iframe" in pagina
    r = anonimo.get("/documentos/informe-de-reservas-2024/descargar")
    assert r.data.startswith(b"%PDF") and "IRR" in r.headers["Content-Disposition"]
    with app.app_context():
        d = db.session.scalar(db.select(Documento))
        ruta = app.config["CARPETA_DATOS"] / "subidas" / "documentos" / d.archivo
        assert ruta.exists()
        id_ = d.id
    admin.post(f"/panel/documentos/{id_}/borrar")
    assert not ruta.exists()
    assert anonimo.get("/documentos/informe-de-reservas-2024").status_code == 404


def test_documento_requiere_archivo_o_enlace(admin):
    r = admin.post("/panel/documentos/nuevo", data={"titulo": "Vacío"})
    assert r.status_code == 400 and "Suba el documento" in r.get_data(as_text=True)


def test_perfil_y_clave(admin, app):
    r = admin.post("/panel/perfil", content_type="multipart/form-data",
                   data={"nombre": "Rafael Fajardo Moreno", "titular": "Energía y datos",
                         "presentacion": "Presentación de prueba.", "biografia": "Primer párrafo.\n\nSegundo.",
                         "correo": "contacto@ejemplo.com", "linkedin": "https://www.linkedin.com/in/ejemplo",
                         "foto": archivo(PNG, "yo.png")})
    assert r.status_code == 302
    inicio = app.test_client().get("/").get_data(as_text=True)
    assert "Energía y datos" in inicio and "Primer párrafo" in inicio and "Segundo" not in inicio
    assert "Segundo" in app.test_client().get("/sobre-mi").get_data(as_text=True)

    admin.post("/panel/clave", data={"clave_actual": "clave-de-prueba", "clave_nueva": "otra-clave-larga",
                                     "clave_confirmacion": "otra-clave-larga"})
    nuevo = app.test_client()
    assert nuevo.post("/panel/entrar", data={"usuario": "rafael", "clave": "otra-clave-larga"}).status_code == 302


def test_subir_imagen_y_vista_previa(admin):
    r = admin.post("/panel/imagenes", data={"imagen": archivo(PNG, "fig.png")}, content_type="multipart/form-data")
    assert r.status_code == 200 and re.fullmatch(r"/archivos/imagenes/[0-9a-f]{32}\.png", r.json["url"])
    assert admin.post("/panel/imagenes", data={"imagen": archivo(b"x", "a.exe")},
                      content_type="multipart/form-data").status_code == 400
    assert "<em>hola</em>" in admin.post("/panel/vista-previa", data={"contenido": "*hola*"}).json["html"]


def test_csrf_activo(tmp_path):
    app = create_app({"TESTING": True, "SECRET_KEY": "x", "CARPETA_DATOS": tmp_path,
                      "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'c.db'}"})
    r = app.test_client().post("/panel/entrar", data={"usuario": "a", "clave": "b"})
    assert r.status_code == 400


def test_ruta_de_archivo_no_escapa(cliente):
    assert cliente.get("/archivos/imagenes/..%2F..%2Fsitio.db").status_code == 404
    assert cliente.get("/archivos/otra/archivo.png").status_code == 404
