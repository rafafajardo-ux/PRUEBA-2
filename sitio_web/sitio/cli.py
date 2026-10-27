"""Comandos de consola:  flask --app wsgi crear-admin"""
import click

from .extensions import db
from .models import Usuario


def registrar_comandos(app):
    @app.cli.command("crear-admin")
    @click.option("--usuario", prompt="Usuario del administrador")
    @click.option("--clave", prompt="Contraseña", hide_input=True, confirmation_prompt="Repita la contraseña")
    def crear_admin(usuario, clave):
        """Crea el usuario administrador o, si ya existe, le cambia la contraseña."""
        if len(clave) < 8:
            raise click.BadParameter("La contraseña debe tener al menos 8 caracteres.", param_hint="--clave")
        u = db.session.scalar(db.select(Usuario).filter_by(usuario=usuario))
        nuevo = u is None
        if nuevo:
            u = Usuario(usuario=usuario)
            db.session.add(u)
        u.fijar_clave(clave)
        db.session.commit()
        click.echo(f"Administrador «{usuario}» {'creado' if nuevo else 'actualizado'}. Entre en /panel/entrar")
