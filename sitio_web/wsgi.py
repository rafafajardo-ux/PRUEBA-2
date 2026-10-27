"""Punto de entrada.  Desarrollo: flask --app wsgi run --debug   ·   Producción: gunicorn wsgi:app"""
from dotenv import load_dotenv

load_dotenv()

from sitio import create_app  # noqa: E402  (después de cargar .env)

app = create_app()
