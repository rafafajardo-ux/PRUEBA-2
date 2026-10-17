#!/bin/bash
# Doble clic en macOS: prepara un entorno local (solo la primera vez) y abre el aplicativo en http://localhost:8501
cd "$(dirname "$0")"
sirve() { "$1" -c 'import sys, venv; sys.exit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; }

if [ ! -x .venv/bin/python ]; then
  PY=""
  for c in "$HOME"/.conda/envs/*/bin/python3 "$HOME"/.anaconda-desktop/micromamba/envs/*/bin/python3 \
           "$HOME"/anaconda3/bin/python3 "$HOME"/opt/anaconda3/bin/python3 /opt/anaconda3/bin/python3 \
           "$HOME"/miniconda3/bin/python3 /opt/miniconda3/bin/python3 "$HOME"/miniforge3/bin/python3 \
           /opt/homebrew/bin/python3 /usr/local/bin/python3 /Library/Frameworks/Python.framework/Versions/3.1*/bin/python3 \
           "$HOME"/.local/share/uv/python/*/bin/python3 "$(command -v python3)"; do
    if [ -x "$c" ] && sirve "$c"; then PY="$c"; break; fi
  done
  if [ -n "$PY" ]; then
    echo "Usando $PY"; "$PY" -m venv .venv || { echo "No se pudo crear el entorno."; read -p "Enter para salir"; exit 1; }
  else
    echo "No se encontró Python 3.10 o superior; se instalará uno local con 'uv' (sin permisos de administrador)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    uv venv --seed --python 3.12 .venv || { echo "No fue posible instalar Python."; read -p "Enter para salir"; exit 1; }
  fi
fi
source .venv/bin/activate
echo "Verificando dependencias (la primera vez tarda unos minutos)..."
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt || { echo "Falló la instalación de dependencias."; read -p "Enter para salir"; exit 1; }
if [ ! -f artefactos/hechos_campo_anio.csv ]; then
  echo "Generando los resultados del modelo (ejecuta el cuaderno, 3-5 minutos)..."
  jupyter nbconvert --to notebook --execute cuaderno_PFI.ipynb --inplace --ExecutePreprocessor.timeout=1800
fi
(sleep 6; open "http://localhost:8501") &
echo "Aplicativo en http://localhost:8501 — deje esta ventana abierta mientras lo usa."
python -m streamlit run app/app.py --server.port 8501 --server.headless true
