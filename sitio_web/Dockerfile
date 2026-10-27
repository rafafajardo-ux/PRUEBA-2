FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CARPETA_DATOS=/datos COOKIE_SEGURA=1 DETRAS_DE_PROXY=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home sitio && mkdir -p /datos && chown sitio /datos
USER sitio
VOLUME /datos
EXPOSE 8000
# --preload crea la base de datos una sola vez antes de lanzar los procesos.
CMD ["gunicorn", "--preload", "--workers", "3", "--bind", "0.0.0.0:8000", "wsgi:app"]
