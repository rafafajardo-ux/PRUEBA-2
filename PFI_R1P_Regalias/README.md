# PFI — Producción anual y diaria de las Reservas 1P de Colombia y regalías esperadas (WTI y Brent)

Proyecto Final Integrador con metodología **CRISP-DM**. Modelos supervisados (árbol de decisión, regresión lineal, red neuronal y ensambles de árboles)
entrenados con la producción real por campo 2023-2026 y el perfil de Reservas 1P/2P/3P; aprendizaje no supervisado (segmentos de campos); aplicativo local.

Autor: Rafael Fajardo Moreno · Integrantes: *[completar]*

| Archivo | Qué es |
|---|---|
| `cuaderno_PFI.ipynb` | Análisis completo y reproducible (semilla 42). Genera `artefactos/` y `ficha_datos.md`. |
| `app/app.py` | Aplicativo Streamlit (consulta por año, desagregación, WTI/Brent, regalías). |
| `iniciar_app.command` | Doble clic en macOS: prepara el entorno y abre http://localhost:8501. |
| `informe_PFI`, `resumen_ejecutivo_EN`, `guia_PFI` | Documentos en Word y PDF. |
| `datos_crudos/` | Excel original y precios mensuales EIA. |

## Uso

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
jupyter nbconvert --to notebook --execute cuaderno_PFI.ipynb --inplace   # opcional: regenera artefactos
streamlit run app/app.py
```

## Términos y condiciones

Los datos son de **carácter reservado** y tienen un **único uso académico**, en el marco de la Especialización en Machine Learning de la
Universidad EAN (2026). **Está prohibido el uso, la distribución, la copia o la mejora, total o parcial.** Solo se tiene en cuenta el pronóstico de
desarrollo de reservas del IRR 2024, sin contemplar la migración de reservas 2P y 3P ni la evolución de recursos contingentes. El aplicativo pide
aceptar estos términos antes de ingresar.

Identidad visual: paleta de www.rafaelfajardomoreno.com y letra Arial Narrow (con la equivalente libre `app/static/PFINarrow-*.ttf`, derivada de
Liberation Sans bajo licencia SIL OFL, si Arial Narrow no está instalada).
