# Sitio web · www.rafaelfajardomoreno.com (Python / Flask)

Sitio personal con la identidad visual de www.rafaelfajardomoreno.com (noche `#0F1923`, azul marino `#1F3251`, dorado `#C8973A`,
crema `#F7F5F0`; títulos en Cormorant Garamond y texto en Arial Narrow) y un **panel privado** para publicar sin tocar código.

| Menú público | Qué muestra | Qué se sube desde el panel |
|---|---|---|
| **Artículos** | Análisis y opinión, con filtros por tipo, etiquetas, buscador, RSS y botones para compartir | Texto en Markdown con vista previa, imágenes dentro del texto, portada, etiquetas, borrador o publicado, fecha original |
| **Artefactos** | Páginas interactivas (HTML) incrustadas, figuras, archivos descargables y enlaces a aplicativos | Archivo `.html`, imagen, cuaderno/datos/código/modelo, o un enlace (Streamlit, Power BI, GitHub, artefactos de Claude…) |
| **Documentos** | Biblioteca de documentos de interés por categoría; los PDF se leen dentro del sitio | PDF, Word, Excel, PowerPoint, CSV, ZIP… o un enlace a la fuente, con autor, año y categoría |
| **Sobre mí** | Biografía, foto y contacto | Panel → Perfil (también cambia los textos de la portada y del pie) |

## Probarlo en su computador

**macOS:** doble clic en `iniciar_sitio.command`. La primera vez instala lo necesario y le pide el usuario y la contraseña del panel.
Abre http://localhost:5050 (el panel está en http://localhost:5050/panel).

**Cualquier sistema:**

```bash
cd sitio_web
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
flask --app wsgi crear-admin                             # usuario y contraseña del panel (también sirve para cambiarla)
flask --app wsgi run --port 5050 --debug
```

La base de datos (SQLite) y los archivos subidos quedan en `sitio_web/instance/`. **Esa carpeta es todo el contenido del sitio:**
cópiela para hacer respaldos o para llevar el contenido a otro servidor. No se sube a Git.

## Cómo publicar

1. Entre en `/panel` (o en «Acceso», al pie de cualquier página).
2. **Artículo:** Panel → Artículos → *Escribir artículo*. Elija *Análisis* u *Opinión*, escriba en Markdown (la guía rápida está debajo
   del editor) y use *Vista previa*. *Guardar borrador* lo deja oculto; *Publicar* lo pone en línea. Si trae artículos del sitio anterior,
   ponga su fecha original en *Fecha de publicación*.
3. **Artefacto:** Panel → Artefactos → *Subir artefacto*. Para una guía o tablero interactivo suba el `.html` autocontenido
   (por ejemplo, un artefacto de Claude descargado); para una aplicación publicada en otro lugar, elija *Enlace externo*.
   *Destacar* lo pone primero en la portada.
4. **Documento:** Panel → Documentos → *Subir documento*, o pegue el enlace a la fuente original si prefiere no alojar el archivo.
5. **Perfil:** nombre, titular, presentación, biografía, foto y redes.

Mientras tenga la sesión iniciada verá también los borradores en el sitio, marcados como «Sin publicar».

## Seguridad

- Solo el administrador puede subir o publicar; los formularios llevan protección CSRF y la contraseña se guarda cifrada (hash).
- El texto en Markdown se limpia (nh3): no admite `<script>`, atributos `on…` ni enlaces `javascript:`.
- Los `.html` y `.svg` subidos se sirven con `Content-Security-Policy: sandbox` y dentro de un `iframe` aislado: su JavaScript corre
  en un origen propio, sin acceso a la sesión del panel. Por eso no pueden usar `localStorage` ni cookies, y deben ser **un solo archivo**
  (si cargan bibliotecas, que sea desde un CDN).
- Los archivos de un artefacto o documento oculto dejan de servirse al público. Los archivos se guardan con nombres aleatorios.
- Solo se aceptan las extensiones de la lista de cada sección (ver `sitio/utils.py`). Límite por archivo: 100 MB (`MAX_MB`).

## Ponerlo en internet con su dominio

Cualquier servicio que ejecute Python sirve. Lo importante es que la carpeta de datos sea **persistente** (que no se borre en cada
despliegue). Tres caminos, de más simple a más flexible:

- **PythonAnywhere** (plan pagado para dominio propio): suba la carpeta `sitio_web`, cree una *web app* Flask manual apuntando a
  `wsgi.py` (`from wsgi import app as application`), instale `requirements.txt` en un virtualenv y ejecute `flask --app wsgi crear-admin`
  en su consola. El disco es persistente.
- **Render / Railway / Fly.io** con el `Dockerfile` incluido: añada un **disco persistente montado en `/datos`** y las variables
  `ADMIN_USUARIO` y `ADMIN_CLAVE` para el primer arranque (bórrelas después). Sin disco persistente, cada despliegue borra el contenido.
- **Servidor propio (VPS)**: `docker build -t sitio . && docker run -d -p 8000:8000 -v /srv/sitio:/datos --restart unless-stopped sitio`
  detrás de Nginx o Caddy con HTTPS.

Después, en el proveedor del dominio, apunte `www.rafaelfajardomoreno.com` (registro CNAME) y el dominio raíz (A/ALIAS) al servicio
elegido, según sus instrucciones. En producción defina `COOKIE_SEGURA=1` y, si hay un proxy delante, `DETRAS_DE_PROXY=1`
(el `Dockerfile` ya los trae). Todas las variables están en `.env.example`.

## Estructura

```
sitio_web/
├── wsgi.py                 punto de entrada (flask --app wsgi …  /  gunicorn wsgi:app)
├── sitio/
│   ├── __init__.py         configuración y creación de la aplicación
│   ├── models.py           Articulo, Artefacto, Documento, Ajuste (perfil), Usuario
│   ├── publico.py          páginas públicas, archivos, RSS (/articulos/feed.xml) y sitemap.xml
│   ├── panel.py            panel de administración (/panel)
│   ├── utils.py            Markdown seguro, fechas en español, slugs y archivos permitidos
│   ├── cli.py              comando crear-admin
│   ├── templates/          páginas (Jinja2)
│   └── static/             estilos, JavaScript y fuente PFI Narrow (SIL OFL)
├── tests/test_sitio.py     pruebas (pip install pytest && python -m pytest -q)
├── Dockerfile · .env.example · iniciar_sitio.command
```
