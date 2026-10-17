"""Aplicativo PFI: producción anual y diaria de las Reservas 1P de Colombia y regalías esperadas (WTI / Brent).
Uso:  streamlit run app/app.py   →   http://localhost:8501"""
import io, json
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

BASE = Path(__file__).resolve().parent.parent
ART = BASE / "artefactos"
st.set_page_config(page_title="PFI · Reservas 1P y regalías", page_icon="🛢️", layout="wide")

# ---------------------------------------------------------------- identidad visual (paleta de www.rafaelfajardomoreno.com)
NIGHT, NAVY, GOLD, GOLD_LT, CREAM, INK, STONE, BORDE = "#0F1923", "#1F3251", "#C8973A", "#DEB86A", "#F7F5F0", "#1C1C1E", "#6B7785", "#E2DDD6"
SERIE = [NAVY, GOLD, STONE, GOLD_LT, "#9AA7B8", NIGHT]
FUENTE = "'Arial Narrow', 'PFI Narrow', 'Liberation Sans Narrow', sans-serif"
pio.templates["pfi"] = go.layout.Template(layout=dict(
    font=dict(family=FUENTE, color=INK, size=14), colorway=SERIE, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FFFFFF",
    title=dict(font=dict(family=FUENTE, color=NAVY, size=17)), legend=dict(font=dict(family=FUENTE)),
    xaxis=dict(gridcolor=BORDE, linecolor=BORDE), yaxis=dict(gridcolor=BORDE, linecolor=BORDE),
    hoverlabel=dict(font=dict(family=FUENTE))))
pio.templates.default = "plotly_white+pfi"

st.markdown(f"""
<style>
@font-face {{ font-family: 'PFI Narrow'; src: url('app/static/PFINarrow-Regular.ttf') format('truetype'); font-weight: 400; }}
@font-face {{ font-family: 'PFI Narrow'; src: url('app/static/PFINarrow-Bold.ttf') format('truetype'); font-weight: 700; }}
html, body, .stApp, .stApp *:not([data-testid="stIconMaterial"]):not(.material-symbols-rounded):not([class*="material-symbols"]) {{
    font-family: {FUENTE} !important; }}
.stApp h1 {{ color: {NAVY}; font-weight: 700; letter-spacing: .2px; border-bottom: 2px solid {GOLD}; padding-bottom: .35rem; }}
.stApp h2, .stApp h3 {{ color: {NAVY}; }}
[data-testid="stMetric"] {{ background: #FFFFFF; border: 1px solid {BORDE}; border-left: 4px solid {GOLD}; border-radius: 6px; padding: .6rem .8rem; }}
[data-testid="stMetricValue"] {{ color: {NAVY}; }}
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] span {{ color: {CREAM}; }}
[data-testid="stSidebar"] [aria-current="page"] {{ background: {NAVY}; border-left: 3px solid {GOLD}; }}
.stTabs [data-baseweb="tab"] {{ font-size: 1.05rem; font-weight: 700; color: {NAVY}; }}
.stTabs [aria-selected="true"] {{ color: {GOLD}; }}
.pfi-ejemplo {{ background: #FFFFFF; border: 1px solid {BORDE}; border-left: 4px solid {NAVY}; border-radius: 6px; padding: .8rem 1rem; margin: .4rem 0 1rem 0; }}
.pfi-ejemplo b.t {{ color: {GOLD}; text-transform: uppercase; font-size: .85rem; letter-spacing: .6px; }}
.pfi-terminos {{ background: #FFFFFF; border: 1px solid {BORDE}; border-top: 5px solid {GOLD}; border-radius: 8px; padding: 1.4rem 1.6rem; }}
.pfi-terminos h2 {{ margin-top: 0; color: {NAVY}; }}
.pfi-pie {{ color: {STONE}; font-size: .85rem; border-top: 1px solid {BORDE}; margin-top: 2rem; padding-top: .5rem; }}
</style>""", unsafe_allow_html=True)


def ejemplo(texto, titulo="Ejemplo de interpretación"):
    st.markdown(f'<div class="pfi-ejemplo"><b class="t">{titulo}</b><br>{texto}</div>', unsafe_allow_html=True)


def grafico(fig):
    st.plotly_chart(fig, width="stretch", theme=None)


# ---------------------------------------------------------------- términos y condiciones (antes de cualquier página)
TERMINOS = """
1. **Carácter reservado.** Los datos que usa este aplicativo son de carácter reservado.
2. **Uso único académico.** Su único uso es académico, en el marco de la **Especialización en Machine Learning de la Universidad EAN (2026)**.
3. **Prohibiciones.** Está prohibido el **uso, la distribución, la copia o la mejora, total o parcial**, de los datos, los modelos, el código y los resultados.
4. **Alcance del pronóstico.** Solo se tiene en cuenta el **pronóstico de desarrollo de reservas del IRR 2024** (Informe de Recursos y Reservas).
   No se contempla la **migración de reservas probables (2P) y posibles (3P)** a probadas ni la **evolución de los recursos contingentes**.
5. **Naturaleza de los resultados.** Las cifras son estimaciones de modelos de aprendizaje automático con fines académicos; no constituyen cifras
   oficiales ni compromisos de recaudo.
"""
if not st.session_state.get("acepta_terminos"):
    _, centro, _ = st.columns([1, 2.4, 1])
    with centro:
        st.markdown('<div class="pfi-terminos"><h2>Términos y condiciones</h2>'
                    '<p>PFI · Reservas 1P y regalías de petróleo en Colombia · Rafael Fajardo Moreno</p></div>', unsafe_allow_html=True)
        st.markdown(TERMINOS)
        ok = st.checkbox("He leído y **acepto** los términos y condiciones de uso.")
        c1, c2 = st.columns(2)
        if c1.button("Ingresar al aplicativo", type="primary", disabled=not ok, width="stretch"):
            st.session_state.acepta_terminos = True
            st.rerun()
        if c2.button("No acepto", width="stretch"):
            st.session_state.rechazo = True
        if st.session_state.get("rechazo"):
            st.warning("Sin aceptar los términos y condiciones no es posible usar el aplicativo. Puede cerrar esta ventana.")
    st.stop()

# ---------------------------------------------------------------- datos
DIM = {"Total país": None, "Campo": "campo", "Departamento": "departamento", "Municipio": "municipio",
       "Operadora": "operadora", "Tipo de contrato": "tipo_contrato"}
TASAS = ["Escala Ley 756 de 2002 (todos los campos)",
         "Ley 756 para E&P y E&E; 20% fijo para contratos de asociación y convenios (supuesto)",
         "Tasa fija definida por el usuario"]
FAMILIA = {"Árbol de decisión": "Árboles de decisión", "Random Forest (ensamble de árboles)": "Árboles de decisión",
           "Gradient Boosting (ensamble de árboles)": "Árboles de decisión", "Regresión lineal (MCO)": "Regresión lineal",
           "Regresión lineal regularizada (Ridge)": "Regresión lineal", "Red neuronal (perceptrón multicapa)": "Redes neuronales"}

if not (ART / "hechos_campo_anio.csv").exists():
    st.error("Faltan los artefactos del modelo. Ejecute primero cuaderno_PFI.ipynb de principio a fin.")
    st.stop()


@st.cache_data
def cargar():
    h = pd.read_csv(ART / "hechos_campo_anio.csv")
    return (h, pd.read_csv(ART / "precios_anuales.csv"), json.loads((ART / "metadatos.json").read_text(encoding="utf-8")),
            pd.read_csv(ART / "comparacion_modelos.csv"))


H, PRECIOS0, META, COMP = cargar()
if "precios" not in st.session_state:
    st.session_state.precios = PRECIOS0[["anio", "brent_usd_bl", "wti_usd_bl", "tipo"]].copy()


def leer(nombre, **kw):
    f = ART / nombre
    return pd.read_csv(f, **kw) if f.exists() else None


def num(v, d=0):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v, d=1, signo=False):
    return (f"{v:+.{d}%}" if signo else f"{v:.{d}%}").replace(".", ",")


def ley756(bpd):
    k = np.asarray(bpd, float) / 1000
    return np.select([k <= 5, k <= 125, k <= 400, k <= 600], [0.08, 0.08 + (k - 5) * 0.001, 0.20, 0.20 + (k - 400) * 0.00025], 0.25)


def tasas(d, opcion, fija):
    if opcion == TASAS[2]:
        return np.full(len(d), fija), np.full(len(d), fija)
    t1, tp = ley756(d["r1p_bl"].fillna(0) / d["dias"]), ley756(d["bpd"].fillna(0))
    if opcion == TASAS[1]:
        antiguo = d["tipo_contrato"].str.contains("ASOCIACI|CONVENIO", case=False, na=False).to_numpy()
        t1, tp = np.where(antiguo, 0.20, t1), np.where(antiguo, 0.20, tp)
    return t1, tp


def estado(a):
    return ("Dato real" if a <= 2025 else "Real enero-junio + pronóstico julio-diciembre" if a == 2026
            else "Pronóstico del modelo con tope en la Reserva 1P del año")


def calcular(anio, dim, sel, precio, opcion, fija):
    d = H[H["anio"] == anio].copy()
    if DIM[dim] and sel:
        d = d[d[DIM[dim]].isin(sel)]
    t1, tp = tasas(d, opcion, fija)
    d["regalias_1p_bl"], d["regalias_prod_bl"] = d["r1p_bl"].fillna(0) * t1, d["prod_total_bl"].fillna(0) * tp
    d["valor_1p_usd"] = d["r1p_bl"].fillna(0) * precio
    d["valor_prod_usd"] = d["prod_total_bl"].fillna(0) * precio
    d["regalias_1p_usd"], d["regalias_prod_usd"] = d["regalias_1p_bl"] * precio, d["regalias_prod_bl"] * precio
    return d


def resumen(d, dim, anio):
    g = d.assign(grupo="Total país" if DIM[dim] is None else d[DIM[dim]].astype(str))
    t = g.groupby("grupo").agg(**{"Producción (bl)": ("prod_total_bl", "sum"), "Reservas 1P (bl)": ("r1p_bl", "sum"),
                                  "Regalías proyectadas 1P (bl)": ("regalias_1p_bl", "sum"), "Regalías por producción (bl)": ("regalias_prod_bl", "sum"),
                                  "Pronosticado = 1P × precio (USD)": ("valor_1p_usd", "sum"), "Producción × precio (USD)": ("valor_prod_usd", "sum"),
                                  "Regalías proyectadas 1P (USD)": ("regalias_1p_usd", "sum"), "Regalías por producción (USD)": ("regalias_prod_usd", "sum"),
                                  "Campos": ("campo", "nunique")}).reset_index().rename(columns={"grupo": dim})
    dias = 366 if anio == 2024 else 365
    t.insert(2, "Barriles por día", t["Producción (bl)"] / dias)
    t.insert(4, "Reservas 1P (bpd)", t["Reservas 1P (bl)"] / dias)
    t = t[(t["Producción (bl)"] > 0) | (t["Reservas 1P (bl)"] > 0)]
    return t.sort_values("Producción (bl)", ascending=False)


def a_excel(hojas):
    b = io.BytesIO()
    with pd.ExcelWriter(b, engine="openpyxl") as w:
        for n, df in hojas.items():
            df.to_excel(w, sheet_name=n[:31], index=False)
    return b.getvalue()


def pie():
    st.markdown('<div class="pfi-pie">Uso exclusivamente académico · Especialización en Machine Learning, Universidad EAN (2026) · Datos de carácter '
                'reservado: prohibido su uso, distribución, copia o mejora total o parcial · Solo pronóstico de desarrollo de reservas del IRR 2024 '
                '(sin migración de reservas 2P y 3P ni evolución de recursos contingentes).</div>', unsafe_allow_html=True)


# ======================================================================= páginas
def pag_ficha():
    st.title("Reservas 1P y regalías de petróleo en Colombia")
    st.markdown("**Pregunta:** ¿cómo se comporta la producción anual y diaria de las Reservas 1P de Colombia y cuánto se espera recibir por regalías "
                "cada año, según los indicadores de referencia WTI y Brent?  \nProyecto Final Integrador · CRISP-DM · Rafael Fajardo Moreno · "
                "Integrantes: *[completar]*")
    c = st.columns([1.3, 1, 1, 1])
    c[0].metric("Modelo final", META["modelo_final"].split(" (")[0])
    c[1].metric("Error por campo en validación cruzada (WAPE)", pct(META["cv_wape"]))
    c[2].metric("Error por campo en la prueba 2026 (WAPE)", pct(META["prueba_wape"]))
    c[3].metric("Sesgo del total país en la prueba", pct(META["prueba_sesgo"], signo=True))
    st.subheader("Fases CRISP-DM")
    st.dataframe(pd.DataFrame([
        ["Comprensión del negocio", "Problema, decisión, métrica de éxito, alcance (IRR 2024) y riesgos"],
        ["Comprensión de los datos", "Ficha de datos y diagnóstico de calidad del Excel (4 hojas)"],
        ["Preparación", "Conjunto campo-año sin fuga; líneas base"],
        ["Modelado", "Árboles de decisión, regresión lineal y redes neuronales con validación cruzada agrupada por campo"],
        ["Evaluación", "Prueba 2026, informe del mejor modelo, curva de aprendizaje, umbral de alerta y segmentos (K-medias)"],
        ["Despliegue y cierre", "Este aplicativo, resumen ejecutivo en inglés, riesgos y plan de seguimiento"]],
        columns=["Fase", "Qué se hizo"]), hide_index=True, width="stretch")
    st.subheader("Cómo usar")
    st.markdown("""
1. En **Consulta** elija el año (2023 a 2060), la desagregación (total país, campo, departamento, municipio, operadora o tipo de contrato) y el indicador de precio (WTI o Brent).
2. Obtendrá la **producción anual**, los **barriles por día**, las **Reservas 1P**, el **pronosticado = Reservas 1P × precio** y las **regalías** (proyectadas con la 1P y a partir de la producción) en barriles y en USD.
3. Para años posteriores a 2026 solo se incluyen campos con Reservas 1P; si un campo no las tiene, se informa **hasta qué año estuvieron proyectadas**. El pronóstico nunca supera la 1P del año.
4. En **Modelos** está el informe del mejor modelo y, por separado, los árboles de decisión, la regresión lineal y las redes neuronales.
""")
    st.info("**Alcance:** solo se tiene en cuenta el pronóstico de desarrollo de reservas del IRR 2024. No se contempla la migración de reservas 2P y 3P "
            "ni la evolución de recursos contingentes, por lo que la senda posterior a 2027 es un piso conservador.")
    pie()


def pag_consulta():
    st.title("Consulta de producción y regalías")
    pr = st.session_state.precios
    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 1.3, 3])
        anio = c1.selectbox("Año", list(range(2023, 2061)), index=3)
        dim = c2.selectbox("Desagregación", list(DIM))
        ops = sorted(H[DIM[dim]].dropna().astype(str).unique()) if DIM[dim] else []
        sel = c3.multiselect(f"{dim}: elija uno o varios (vacío = todos)", ops, disabled=DIM[dim] is None,
                             placeholder="No aplica" if DIM[dim] is None else "Escriba para buscar")
        c4, c5, c6, c7 = st.columns([1, 1, 2.2, 1])
        ind = c4.radio("Indicador", ["WTI", "Brent"], horizontal=True)
        fila = pr[pr["anio"] == anio]
        p0 = float(fila["wti_usd_bl" if ind == "WTI" else "brent_usd_bl"].iloc[0]) if len(fila) else 0.0
        precio = c5.number_input(f"{ind} promedio {anio} (USD/bl)", value=p0, step=0.5, format="%.2f", key=f"p_{ind}_{anio}")
        opcion = c6.selectbox("Tasa de regalías", TASAS)
        fija = c7.number_input("Tasa fija (%)", value=8.0, min_value=0.0, max_value=50.0, step=0.5, disabled=opcion != TASAS[2]) / 100
        if len(fila):
            st.caption(f"Precio {anio}: {fila['tipo'].iloc[0]}. Puede cambiarlo aquí o en la página Datos y precios.")
    d = calcular(anio, dim, sel, precio, opcion, fija)
    st.info(f"**{anio}: {estado(anio)}.**" + (f" Error mediano por campo esperado: ±{META['error_mediano_campo']:.0%}; sesgo del total país en la prueba: "
                                              f"{pct(META['prueba_sesgo'], signo=True)}." if anio >= 2026 else ""))

    if anio > 2026:
        base = H[H["anio"] == anio]
        if DIM[dim] and sel:
            base = base[base[DIM[dim]].isin(sel)]
        sin = base[base["r1p_bl"].fillna(0) <= 0].drop_duplicates("campo")
        if len(sin):
            sin = sin.assign(**{"Situación": np.where(sin["ultimo_anio_1p"].notna(),
                                                      "Reservas 1P proyectadas hasta " + sin["ultimo_anio_1p"].fillna(0).astype(int).astype(str),
                                                      "Sin Reservas 1P en el pronóstico oficial: no se pronostica después de 2026")})
            with st.expander(f"⚠️ {len(sin)} campo(s) sin Reservas 1P en {anio}: no se pronostican", expanded=dim == "Campo" and bool(sel)):
                st.dataframe(sin[["campo", "operadora", "departamento", "Situación"]].rename(columns=str.capitalize), hide_index=True, width="stretch")
    t = resumen(d, dim, anio)
    if t.empty:
        st.warning(f"La selección no tiene producción ni Reservas 1P en {anio}."); return
    tot = t.drop(columns=[dim]).sum(numeric_only=True)
    dias = 366 if anio == 2024 else 365
    k = st.columns(4)
    k[0].metric("Producción anual (bl)", num(tot["Producción (bl)"]))
    k[1].metric("Barriles por día", num(tot["Producción (bl)"] / dias))
    k[2].metric("Reservas 1P del año (bl)", num(tot["Reservas 1P (bl)"]) if anio >= 2024 else "Sin 1P (empieza en 2024)")
    k[3].metric("Producción / Reservas 1P", pct(tot["Producción (bl)"] / tot["Reservas 1P (bl)"]) if tot["Reservas 1P (bl)"] > 0 else "—")
    k = st.columns(4)
    k[0].metric(f"Pronosticado 1P × {ind} (M USD)", num(tot["Pronosticado = 1P × precio (USD)"] / 1e6, 1),
                help="Fórmula del enunciado: Reservas 1P (bl) del año × precio promedio del año seleccionado.")
    k[1].metric(f"Producción × {ind} (M USD)", num(tot["Producción × precio (USD)"] / 1e6, 1))
    k[2].metric("Regalías proyectadas con la 1P", f"{num(tot['Regalías proyectadas 1P (bl)'])} bl")
    k[2].caption(f"= USD {num(tot['Regalías proyectadas 1P (USD)'] / 1e6, 1)} millones a {ind}")
    k[3].metric("Regalías a partir de la producción", f"{num(tot['Regalías por producción (bl)'])} bl")
    k[3].caption(f"= USD {num(tot['Regalías por producción (USD)'] / 1e6, 1)} millones a {ind}")

    st.subheader(f"Detalle por {dim.lower()} — {anio}")
    t_show = t.copy()
    for c in t_show.columns:
        if c not in (dim, "Campos"):
            t_show[c] = t_show[c].round(0)
    st.dataframe(t_show, hide_index=True, width="stretch", height=min(460, 40 + 35 * len(t_show)),
                 column_config={c: st.column_config.NumberColumn(format="localized") for c in t_show.columns if c != dim})

    s = H.copy()
    if DIM[dim] and sel:
        s = s[s[DIM[dim]].isin(sel)]
    s = s.groupby("anio").agg(real=("prod_real_bl", "sum"), pron=("prod_pron_bl", "sum"), r1p=("r1p_bl", "sum")).reset_index()
    s["d"] = np.where(s["anio"] == 2024, 366, 365)
    fig = go.Figure()
    fig.add_bar(x=s["anio"], y=s["real"] / s["d"], name="Real (bpd)", marker_color=NAVY)
    fig.add_bar(x=s["anio"], y=s["pron"] / s["d"], name="Pronóstico (bpd)", marker_color=GOLD)
    fig.add_scatter(x=s.loc[s.anio >= 2024, "anio"], y=s.loc[s.anio >= 2024, "r1p"] / s.loc[s.anio >= 2024, "d"], name="Reservas 1P (bpd)",
                    line=dict(color=NIGHT, dash="dot"))
    fig.add_vline(x=anio, line_dash="dash", line_color=STONE)
    fig.update_layout(barmode="stack", height=390, margin=dict(l=10, r=10, t=50, b=10), legend=dict(orientation="h", y=-0.18),
                      yaxis_title="barriles por día", title="Trayectoria 2023–2060 de la selección")
    grafico(fig)

    det = d[["campo", "departamento", "municipio", "operadora", "tipo_contrato", "estado", "metodo", "prod_real_bl", "prod_pron_bl", "prod_total_bl",
             "bpd", "r1p_bl", "regalias_1p_bl", "regalias_prod_bl", "valor_1p_usd", "regalias_1p_usd", "regalias_prod_usd"]]
    par = pd.DataFrame({"Parámetro": ["Año", "Estado del dato", "Desagregación", "Selección", "Indicador", "Precio (USD/bl)", "Tasa de regalías",
                                      "Modelo", "Alcance", "Uso", "Generado"],
                        "Valor": [anio, estado(anio), dim, ", ".join(sel) or "Todos", ind, precio, opcion if opcion != TASAS[2] else f"Fija {fija:.1%}",
                                  META["modelo_final"], "Pronóstico de desarrollo de reservas del IRR 2024 (sin migración 2P/3P ni recursos contingentes)",
                                  "Académico, Especialización en Machine Learning, Universidad EAN 2026. Datos reservados.",
                                  pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")]})
    st.download_button("⬇️ Descargar informe de la consulta (Excel)", a_excel({"Parámetros": par, "Resumen": t, "Detalle por campo": det}),
                       file_name=f"consulta_{anio}_{dim.replace(' ', '_')}.xlsx")
    with st.expander("Cómo se calcula"):
        st.markdown(f"""
- **Producción:** real hasta junio de 2026; desde julio de 2026, pronóstico de **{META['modelo_final']}**. Desde 2027 el pronóstico de cada campo es
  el mínimo entre el modelo y su **Reserva 1P del año** (IRR 2024); si la 1P es cero el campo no se pronostica.
- **Barriles por día** = producción anual / días del año ({dias} en {anio}).
- **Pronosticado = Reservas 1P (bl) × precio promedio del año** ({ind}).
- **Regalías proyectadas** = Reservas 1P × tasa; **regalías a partir de la producción** = producción × tasa. Tasa por defecto: escala de la
  Ley 756 de 2002 según los barriles por día del campo (8% hasta 5.000 bpd; sube 0,1 puntos por cada 1.000 bpd hasta 20% en 125.000 bpd;
  25% por encima de 600.000 bpd). No incluye el descuento del 25% para crudos pesados (API ≤ 15) porque el archivo no trae la gravedad API.
""")
    pie()


# ---------------------------------------------------------------- Modelos
def tabla_modelos(filtro):
    cols = ["modelo", "hiperparámetros", "CV WAPE", "CV WAPE desv.", "Temporal WAPE", "Prueba WAPE", "Prueba Sesgo total", "Prueba R² (log)"]
    t = COMP[COMP.modelo.isin(filtro)][cols].sort_values("CV WAPE")
    st.dataframe(t.style.format({c: "{:.1%}" for c in cols[2:7]} | {"Prueba R² (log)": "{:.3f}"}), hide_index=True, width="stretch")


def informe_mejor_modelo():
    C = COMP.set_index("modelo"); fin = META["modelo_final"]
    ml = COMP[COMP.modelo.isin(FAMILIA)].assign(familia=lambda d: d.modelo.map(FAMILIA)).sort_values("CV WAPE")
    mf = ml.groupby("familia", sort=False).head(1).set_index("familia")
    b1, bp = C.loc["Línea base: Reservas 1P del año"], C.loc["Línea base: persistencia (año anterior)"]
    r = C.loc[fin]
    st.subheader("Informe: ¿cuál es el mejor modelo?")
    st.markdown(f"#### Veredicto: **{fin}** (familia *{FAMILIA.get(fin, '')}*)")
    k = st.columns(3)
    for col, fam in zip(k, ["Árboles de decisión", "Regresión lineal", "Redes neuronales"]):
        if fam in mf.index:
            f = mf.loc[fam]
            corto = {"Regresión lineal regularizada (Ridge)": "Ridge", "Regresión lineal (MCO)": "MCO", "Red neuronal (perceptrón multicapa)": "Perceptrón"}.get(f["modelo"], f["modelo"].split(" (")[0])
            col.metric(f"Mejor de {fam.lower()}", corto, f"CV {pct(f['CV WAPE'])} · prueba {pct(f['Prueba WAPE'])}",
                       delta_color="off")
    seg = mf.index[1] if len(mf) > 1 else None
    st.markdown(f"""
**Regla de elección (definida antes de ver la prueba):** gana el modelo con menor error ponderado por barriles (WAPE) en la validación cruzada de 5
pliegues agrupados por campo (2024-2025). La prueba 2026 se usó una sola vez, al final, para confirmar.

1. **{fin}** obtuvo el menor error en validación cruzada (**{pct(r['CV WAPE'])} ± {pct(r['CV WAPE desv.'])}**) y confirmó en la prueba 2026
   (**{pct(r['Prueba WAPE'])}**, sesgo del total país **{pct(r['Prueba Sesgo total'], signo=True)}**). Frente a usar la Reserva 1P tal cual
   ({pct(b1['Prueba WAPE'])} en la prueba) reduce el error a cerca de **{r['Prueba WAPE'] / b1['Prueba WAPE']:.0%}** del de la línea base.
2. **Regresión lineal** ({mf.loc['Regresión lineal', 'modelo'] if 'Regresión lineal' in mf.index else '—'}): validación cruzada
   {pct(mf.loc['Regresión lineal', 'CV WAPE']) if 'Regresión lineal' in mf.index else '—'}, pero la mejor validación temporal
   ({pct(mf.loc['Regresión lineal', 'Temporal WAPE']) if 'Regresión lineal' in mf.index else '—'}) y sesgo casi nulo. Es la alternativa más simple y auditable.
3. **Redes neuronales:** validación cruzada {pct(mf.loc['Redes neuronales', 'CV WAPE']) if 'Redes neuronales' in mf.index else '—'}. Con pocos
   campos-año (≈ {sum(int(v) for k_, v in META['filas_entrenamiento'].items() if k_ != '2026')} filas de entrenamiento) la red sobreajusta pronto
   (ver la curva de aprendizaje en *Redes neuronales*).
4. **Persistencia** (repetir el año anterior) logra {pct(bp['Prueba WAPE'])} en un solo semestre de prueba, pero {pct(bp['CV WAPE'])} en validación
   cruzada; el valor del modelo está en seguir el declive de la 1P en los años siguientes.
""")
    rk = COMP.assign(familia=COMP.modelo.map(FAMILIA).fillna("Línea base")).sort_values("CV WAPE")
    rk.insert(0, "puesto", range(1, len(rk) + 1))
    cols = ["puesto", "modelo", "familia", "CV WAPE", "CV WAPE desv.", "Temporal WAPE", "Prueba WAPE", "Prueba Sesgo total"]
    st.dataframe(rk[cols].style.format({c: "{:.1%}" for c in cols[3:]}).apply(
        lambda f: [f"background-color: {GOLD_LT}55; font-weight: 700" if f.modelo == fin else "" for _ in f], axis=1),
        hide_index=True, width="stretch")
    st.caption("WAPE = error absoluto ponderado por barriles. CV = validación cruzada de 5 pliegues agrupados por campo (2024-2025); Temporal = "
               "entrenar con 2024 y evaluar 2025; Prueba = 2026 enero-junio. Resaltado: modelo elegido.")
    tam = leer("error_por_tamano.csv")
    if tam is not None:
        st.markdown("**Error del modelo elegido por tamaño de campo (prueba 2026)**")
        st.dataframe(tam, hide_index=True, width="stretch")
    ejemplo(f"Si el Ministerio programa el recaudo de 2026 con <b>{fin.split(' (')[0]}</b>, por cada 100 barriles producidos el error absoluto "
            f"acumulado entre campos es de unos {r['Prueba WAPE'] * 100:.0f} barriles, y el total país queda {abs(r['Prueba Sesgo total']) * 100:.1f}% "
            f"{'por debajo' if r['Prueba Sesgo total'] < 0 else 'por encima'} del real (estimación conservadora). Con la 1P tal cual el error sería de "
            f"unos {b1['Prueba WAPE'] * 100:.0f} barriles por cada 100.")
    st.download_button("⬇️ Descargar informe del mejor modelo (Excel)",
                       a_excel({"Ranking": rk[cols], "Veredicto": pd.DataFrame({"Concepto": ["Mejor modelo", "Familia", "Regla de elección",
                                                                                          "CV WAPE", "Prueba WAPE", "Prueba sesgo total", "Línea base 1P (prueba)"],
                                                                             "Valor": [fin, FAMILIA.get(fin, ""), "Menor WAPE en validación cruzada agrupada por campo",
                                                                                       pct(r['CV WAPE']), pct(r['Prueba WAPE']), pct(r['Prueba Sesgo total'], signo=True),
                                                                                       pct(b1['Prueba WAPE'])]})}),
                       file_name="informe_mejor_modelo.xlsx")


def sec_arboles():
    st.subheader("Árboles de decisión")
    st.markdown("Familia de modelos que divide los campos con preguntas sí/no sobre sus variables. Incluye el **árbol de decisión** individual "
                "(interpretable) y dos **ensambles de árboles**: Random Forest (promedia 500 árboles) y Gradient Boosting (suma árboles que corrigen errores).")
    tabla_modelos([m for m, f in FAMILIA.items() if f == "Árboles de decisión"])
    st.markdown("**Árbol de decisión (profundidad 3)** — dorado = caída esperada de la producción, azul = crecimiento.")
    st.image(str(ART / "figuras" / "arbol_decision.png"))
    with st.expander("Reglas del árbol en texto"):
        st.code((ART / "arbol_reglas.txt").read_text(encoding="utf-8"), language=None)
    ejemplo("Un campo que produjo <b>2.000 bpd</b> el año anterior (log(1+bpd) = 7,6 &gt; 4,66 → rama «No») y cuya producción estaba cerca de su "
            "Reserva 1P del año, de <b>1.800 bpd</b> (brecha = 7,60 − 7,50 = 0,10 &gt; −0,12 → rama «No»; log 1P = 7,50 ≤ 7,77 → rama «Sí»), cae en la hoja "
            "<b>valor = −0,17</b> (282 campos-año). Significa un cambio esperado de e<sup>−0,17</sup> − 1 ≈ <b>−16%</b>: unos <b>1.690 bpd</b> este año, "
            "por debajo de su 1P. En cambio, un campo con menos de unos 100 bpd y una 1P que cae más de 17% al año siguiente llega a hojas de −0,45 a "
            "−1,06 (caídas de 36% a 65%). El Random Forest final promedia 500 árboles más profundos, por eso sus pronósticos son más suaves.")
    imp = leer("importancia_variables.csv", index_col=0)
    if imp is not None:
        imp = imp["importancia"].sort_values()
        fig = go.Figure(go.Bar(x=imp.values, y=imp.index, orientation="h", marker_color=[GOLD if v == imp.max() else NAVY for v in imp.values]))
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=50, b=10), title=f"Importancia de variables — {META['modelo_final']}",
                          xaxis_title="caída del R² al desordenar la variable (prueba 2026)")
        grafico(fig)
        ejemplo(f"La variable más importante es <b>{imp.index[-1]}</b>: si se desordena al azar, el R² del modelo cae {num(imp.iloc[-1], 2)}. "
                "Es decir, saber cuánto produjo el campo el año anterior es lo que más ayuda a pronosticar el siguiente; la 1P ayuda sobre todo a "
                "anticipar el ritmo de declive.")
    p = leer("prueba_predicciones.csv")
    if p is not None:
        fig = go.Figure()
        fig.add_scatter(x=p.bpd_real, y=p.reservas_1p_bpd, mode="markers", name="Reservas 1P del año (línea base)",
                        marker=dict(color=STONE, size=6, opacity=.55), text=p.campo)
        fig.add_scatter(x=p.bpd_real, y=p.pronostico_final, mode="markers", name=f"{META['modelo_final'].split(' (')[0]}",
                        marker=dict(color=GOLD, size=7, opacity=.8), text=p.campo)
        lim = [10, p.bpd_real.max() * 1.5]
        fig.add_scatter(x=lim, y=lim, mode="lines", name="Pronóstico perfecto", line=dict(color=NIGHT, width=1))
        fig.update_layout(height=430, margin=dict(l=10, r=10, t=50, b=10), title="Prueba 2026: pronóstico frente a producción real por campo",
                          xaxis=dict(type="log", title="real 2026 (bpd)", dtick=1), yaxis=dict(type="log", title="pronóstico (bpd)", dtick=1),
                          legend=dict(orientation="h", y=-0.2))
        grafico(fig)
        top = p.sort_values("bpd_real", ascending=False).iloc[0]
        ejemplo(f"Cada punto es un campo. <b>{top.campo}</b> produjo {num(top.bpd_real)} bpd en el primer semestre de 2026; el modelo pronosticó "
                f"{num(top.pronostico_final)} bpd ({pct(top.pronostico_final / top.bpd_real - 1, signo=True)}) y su Reserva 1P indicaba "
                f"{num(top.reservas_1p_bpd)} bpd ({pct(top.reservas_1p_bpd / top.bpd_real - 1, signo=True)}). Los puntos dorados se pegan a la "
                "diagonal; los grises (1P) se alejan, sobre todo en campos pequeños.")


def sec_lineal():
    st.subheader("Regresión lineal")
    st.markdown("Modelo que suma el efecto de cada variable con un peso fijo (coeficiente). Se probó por **mínimos cuadrados ordinarios (MCO)** y con "
                "**regularización Ridge**, que encoge los coeficientes para evitar sobreajuste. Las variables numéricas están estandarizadas, así que los "
                "coeficientes son comparables entre sí.")
    tabla_modelos([m for m, f in FAMILIA.items() if f == "Regresión lineal"])
    cf = leer("coeficientes_numericos.csv", index_col=0)
    if cf is not None:
        cf = cf.iloc[:, 0].sort_values()
        fig = go.Figure(go.Bar(x=cf.values, y=cf.index, orientation="h", marker_color=[GOLD if v < 0 else NAVY for v in cf.values]))
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=50, b=10), title="Coeficientes de la regresión lineal (variables numéricas estandarizadas)",
                          xaxis_title="efecto en el cambio logarítmico por una desviación estándar")
        grafico(fig)
        pos, neg = cf.idxmax(), cf.idxmin()
        c3 = lambda v: f"{v:+.3f}".replace(".", ",")
        ejemplo(f"El coeficiente de <b>{pos}</b> es {c3(cf[pos])}: si un campo tiene una desviación estándar más en esa variable, y todo lo demás "
                f"igual, el modelo espera que su producción cambie e<sup>{c3(cf[pos])}</sup> − 1 ≈ <b>{pct(np.exp(cf[pos]) - 1, signo=True)}</b> frente "
                f"al año anterior. En sentido contrario, una desviación estándar más en <b>{neg}</b> ({c3(cf[neg])}) cambia la producción en ≈ "
                f"<b>{pct(np.exp(cf[neg]) - 1, signo=True)}</b>. Dorado = efecto negativo, azul = positivo.")
    st.caption("Fortaleza: la mejor validación temporal y un sesgo casi nulo. Limitación: impone efectos constantes y no capta los cortes (umbrales) que "
               "sí capturan los árboles; por eso su error en validación cruzada es mayor.")


def sec_red():
    st.subheader("Redes neuronales")
    hp = COMP.set_index("modelo").loc["Red neuronal (perceptrón multicapa)", "hiperparámetros"] if "Red neuronal (perceptrón multicapa)" in set(COMP.modelo) else "—"
    st.markdown(f"**Perceptrón multicapa** (capas ocultas con activación ReLU, optimizador Adam y regularización L2). Hiperparámetros elegidos: {hp}. "
                "Aprende combinaciones no lineales de las variables, pero necesita muchos datos.")
    tabla_modelos(["Red neuronal (perceptrón multicapa)"])
    cu = leer("curva_aprendizaje_red.csv")
    if cu is not None:
        ep = int(META.get("red_mejor_epoca", cu.loc[cu.validacion.idxmin(), "epoca"]))
        fig = go.Figure()
        fig.add_scatter(x=cu.epoca, y=cu.entrenamiento, name="Entrenamiento (80 % de los campos, 2024-2025)", line=dict(color=NAVY, width=2.5))
        fig.add_scatter(x=cu.epoca, y=cu.validacion, name="Validación (20 % de campos no vistos)", line=dict(color=STONE, width=2, dash="dash"))
        fig.add_scatter(x=cu.epoca, y=cu.prueba_2026, name="Prueba 2026 (solo se muestra)", line=dict(color=GOLD, width=2.5))
        fig.add_vline(x=ep, line_dash="dot", line_color=NIGHT, annotation_text=f"mejor época: {ep}", annotation_position="top right")
        fig.update_layout(height=430, margin=dict(l=10, r=10, t=50, b=10), title="Curva de aprendizaje: entrenamiento frente a prueba",
                          xaxis_title="época (pasada completa por los datos de entrenamiento)",
                          yaxis=dict(title="error cuadrático medio ponderado (cambio logarítmico)", rangemode="tozero"), legend=dict(orientation="h", y=-0.22))
        grafico(fig)
        f1, fe, fu = cu.iloc[0], cu[cu.epoca == ep].iloc[0], cu.iloc[-1]
        ejemplo(f"En la época 1 los tres errores son altos (entrenamiento {f1.entrenamiento:.3f}, prueba {f1.prueba_2026:.3f}): la red aún no aprende. "
                f"Hacia la <b>época {ep}</b> el error de validación es el más bajo ({fe.validacion:.3f}) y la prueba 2026 también está cerca de su mínimo "
                f"({fe.prueba_2026:.3f}). Después el error de entrenamiento sigue bajando hasta {fu.entrenamiento:.3f} en la época {int(fu.epoca)}, mientras "
                f"validación y prueba suben a {fu.validacion:.3f} y {fu.prueba_2026:.3f}: la red <b>memoriza</b> los campos de entrenamiento y pierde "
                "capacidad de generalizar (sobreajuste). Por eso se entrena con <b>parada temprana</b> y, aun así, queda detrás de los árboles.")
        st.caption("La línea de prueba se muestra solo para ilustrar; la mejor época se fija con la validación, nunca con la prueba.")


def pag_modelos():
    st.title("Modelos")
    st.markdown(f"**Modelo final:** {META['modelo_final']} · hiperparámetros: {META['hiperparametros']}.")
    t0, t1, t2, t3 = st.tabs(["📋 Informe: mejor modelo", "🌳 Árboles de decisión", "📈 Regresión lineal", "🧠 Redes neuronales"])
    with t0:
        informe_mejor_modelo()
    with t1:
        sec_arboles()
    with t2:
        sec_lineal()
    with t3:
        sec_red()
    pie()


def pag_alertas():
    st.title("Umbral recomendado y alertas de cumplimiento")
    U = META["umbral_alerta"]
    st.markdown(f"Un campo **incumple** si produce menos del **{META['meta_cumplimiento']:.0%}** de su Reserva 1P del año. Se emite **alerta** si el "
                f"cumplimiento pronosticado (producción pronosticada / Reserva 1P) es menor a **{U:.2f}**. El umbral se eligió en la validación 2025 "
                "minimizando un costo en el que no detectar un incumplimiento (regalías sobreestimadas) cuesta 3 veces una falsa alarma.")
    u = pd.read_csv(ART / "umbral_alerta.csv")
    st.dataframe(u.style.format({"AUC": "{:.2f}", "sensibilidad": "{:.2f}", "precisión": "{:.2f}", "costo medio": "{:.3f}", "umbral": "{:.2f}"}),
                 hide_index=True, width="stretch")
    c = leer("umbral_costos.csv")
    if c is not None:
        fig = go.Figure(go.Scatter(x=c.umbral, y=c.costo_medio, line=dict(color=NAVY, width=2.5), name="costo medio"))
        fig.add_vline(x=U, line_dash="dash", line_color=GOLD, annotation_text=f"umbral elegido {U:.2f}")
        fig.update_layout(height=330, margin=dict(l=10, r=10, t=50, b=10), title="Elección del umbral de alerta (validación 2025)",
                          xaxis_title="umbral de cumplimiento pronosticado", yaxis_title="costo medio por campo")
        grafico(fig)
    p = u.iloc[1]
    ejemplo(f"En la prueba 2026 hubo <b>{int(p['incumplimientos reales'])}</b> campos que realmente produjeron menos del "
            f"{META['meta_cumplimiento']:.0%} de su 1P. La alerta se encendió en <b>{int(p['alertas'])}</b> campos. Sensibilidad "
            f"{p['sensibilidad']:.2f}: de cada 100 campos que incumplieron, la alerta detectó unos {p['sensibilidad'] * 100:.0f}. Precisión "
            f"{p['precisión']:.2f}: de cada 100 alertas, unas {p['precisión'] * 100:.0f} fueron incumplimientos reales y el resto falsas alarmas, que "
            "son baratas (una revisión con el operador) frente a presupuestar regalías que no llegarán.", "Cómo leer la tabla")
    anio = st.selectbox("Año para revisar alertas", list(range(2026, 2036)), index=1)
    d = H[(H.anio == anio) & (H.r1p_bl > 0)].copy()
    d["cumplimiento"] = d["prod_total_bl"] / d["r1p_bl"]
    d = d[d["cumplimiento"] < U].sort_values("r1p_bl", ascending=False)
    d[["prod_total_bl", "r1p_bl"]] = d[["prod_total_bl", "r1p_bl"]].round(0)
    st.write(f"**{len(d)}** campos con cumplimiento pronosticado menor a {U:.2f} en {anio}.")
    st.dataframe(d[["campo", "operadora", "departamento", "prod_total_bl", "r1p_bl", "cumplimiento", "metodo"]], hide_index=True, width="stretch",
                 column_config={"cumplimiento": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.2f"),
                                "prod_total_bl": st.column_config.NumberColumn("producción pronosticada (bl)", format="localized"),
                                "r1p_bl": st.column_config.NumberColumn("Reserva 1P (bl)", format="localized")})
    if len(d):
        f = d.iloc[0]; brecha = f.r1p_bl - f.prod_total_bl
        tasa = float(ley756(f.r1p_bl / (366 if anio == 2024 else 365)))
        ejemplo(f"En {anio}, <b>{f.campo}</b> ({f.operadora}) tiene una Reserva 1P de {num(f.r1p_bl)} bl, pero el modelo pronostica {num(f.prod_total_bl)} bl: "
                f"cumplimiento <b>{f.cumplimiento:.2f}</b> &lt; {U:.2f} → <b>alerta</b>. Si las regalías se presupuestan con la 1P, se esperarían "
                f"{num(brecha)} bl de producción que probablemente no llegarán, unos {num(brecha * tasa)} bl de regalías (tasa {pct(tasa)}). "
                "Acción sugerida: revisar con el operador el plan de desarrollo del campo antes de cerrar el presupuesto.")
    pie()


def pag_segmentos():
    st.title("Segmentos de campos (no supervisado)")
    seg = pd.read_csv(ART / "segmentos_campos.csv"); per = pd.read_csv(ART / "perfil_segmentos.csv")
    car = leer("componentes_pca.csv", index_col=0)
    var = META.get("pca_varianza", [np.nan, np.nan])
    st.markdown(f"K-medias con k = {META['segmentos_k']} (elegido por silueta y comparado con agrupamiento jerárquico) sobre seis variables "
                "estandarizadas de cada campo. Para dibujarlos en un plano se resumen las seis variables en dos **componentes principales**.")
    fig = px.scatter(seg, x="pc1", y="pc2", color="nombre_segmento", hover_name="campo", height=480, color_discrete_sequence=SERIE,
                     labels={"pc1": f"Componente 1 ({var[0]:.0%}): tamaño y desempeño frente a la 1P",
                             "pc2": f"Componente 2 ({var[1]:.0%}): horizonte de la 1P", "nombre_segmento": "Segmento"})
    fig.update_traces(marker=dict(size=8, opacity=.8, line=dict(width=.5, color="#FFFFFF")))
    fig.update_layout(margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=-0.2))
    grafico(fig)
    st.subheader("¿Qué significan el componente 1 y el componente 2?")
    c1, c2 = st.columns(2)
    c1.markdown(f"""
**Componente 1 — tamaño y desempeño frente a la 1P** ({var[0]:.0%} de la variación)

Crece con el **tamaño** del campo, su **cambio 2025 frente a 2024** y su **cumplimiento de la 1P**, y en menor medida con una 1P de declive suave y
larga vida; baja cuando el campo depende más de reservas **probables**.
- **Derecha:** campos grandes, estables o en crecimiento, que producen lo que dice su 1P.
- **Izquierda:** campos pequeños, en caída y muy por debajo de su 1P.
""")
    c2.markdown(f"""
**Componente 2 — horizonte de la 1P** ({var[1]:.0%} de la variación)

Crece con los **años restantes de 1P** y con un **declive 1P 2026-2030 suave**, y baja con el **cumplimiento 2025**.
- **Arriba:** campos con reservas probadas para muchos años y perfil estable, aunque hoy produzcan algo por debajo de su 1P.
- **Abajo:** campos que hoy cumplen o superan su 1P pero cuya 1P se agota pronto o cae rápido.
""")
    if car is not None:
        cc = car.drop(index="varianza explicada", errors="ignore").rename(columns={"componente_1": "Componente 1", "componente_2": "Componente 2"})
        fig = go.Figure()
        fig.add_bar(y=cc.index, x=cc["Componente 1"], name="Componente 1", orientation="h", marker_color=NAVY)
        fig.add_bar(y=cc.index, x=cc["Componente 2"], name="Componente 2", orientation="h", marker_color=GOLD)
        fig.update_layout(barmode="group", height=360, margin=dict(l=10, r=10, t=50, b=10), legend=dict(orientation="h", y=-0.2),
                          title="Cargas: peso de cada variable en cada componente", xaxis_title="carga (−1 a 1)")
        grafico(fig)
    ej = seg.set_index("campo")
    a = "CASTILLA" if "CASTILLA" in ej.index else ej.pc1.idxmax()
    b = ej.pc1.idxmin()
    fa, fb = ej.loc[a], ej.loc[b]
    ejemplo(f"<b>{a}</b> está en ({num(fa.pc1, 1)}; {num(fa.pc2, 1)}): a la derecha porque es grande ({num(10 ** fa.iloc[0])} bpd en 2025), "
            f"estable ({pct(np.exp(fa.iloc[1]) - 1, signo=True)} frente a 2024) y cumple su 1P ({num(fa.iloc[2], 2)}); arriba porque le quedan "
            f"{fa.iloc[4]:.0f} años de 1P con declive suave. Pertenece a «{fa.nombre_segmento}». En el otro extremo, <b>{b}</b> está en "
            f"({num(fb.pc1, 1)}; {num(fb.pc2, 1)}): muy a la izquierda porque es pequeño y su cumplimiento de la 1P fue {num(fb.iloc[2], 2)}; "
            f"pertenece a «{fb.nombre_segmento}». <b>Lectura práctica:</b> cuanto más a la izquierda, más riesgo de que las regalías calculadas con "
            "la 1P no se materialicen; cuanto más abajo, más pronto se agota la 1P.")
    st.subheader("Perfil de los segmentos (medianas)")
    st.dataframe(per.round(2), hide_index=True, width="stretch")
    pie()


def pag_datos():
    st.title("Datos y precios")
    st.subheader("Precios promedio anuales (USD/bl), editables")
    st.caption("Fuente por defecto: EIA (spot Brent y WTI, promedio de los meses del año; 2026 = enero-septiembre; 2027 = EIA STEO de octubre de "
               "2026; 2028 en adelante = supuesto constante). Equivalen a las referencias de investing.com.")
    st.session_state.precios = st.data_editor(st.session_state.precios, hide_index=True, width="stretch", disabled=["anio", "tipo"])
    if st.button("Actualizar 2023-2026 con futuros Brent (BZ=F) y WTI (CL=F) de Yahoo Finance (requiere internet)"):
        try:
            import yfinance as yf
            p = st.session_state.precios.copy()
            for col, tick in (("brent_usd_bl", "BZ=F"), ("wti_usd_bl", "CL=F")):
                s = yf.download(tick, start="2023-01-01", progress=False, auto_adjust=False)["Close"].squeeze()
                for a, v in s.groupby(s.index.year).mean().items():
                    if 2023 <= a <= 2026:
                        p.loc[p.anio == a, col] = round(float(v), 2)
            st.session_state.precios = p; st.success("Precios actualizados."); st.rerun()
        except Exception as e:
            st.warning(f"No se pudo actualizar ({e}). Se mantienen los valores cargados.")
    st.subheader("Diagnóstico de calidad")
    st.dataframe(pd.read_csv(ART / "calidad_hallazgos.csv").rename(columns={"Unnamed: 0": "indicador"}), hide_index=True, width="stretch")
    n = H.groupby("anio").agg(real=("prod_real_bl", "sum"), r1p=("r1p_bl", "sum")).loc[2023:2026]
    dd = pd.Series({2023: 365, 2024: 366, 2025: 365, 2026: 181})
    fig = go.Figure()
    fig.add_bar(x=n.index, y=n.real / dd / 1e3, name="Producción real (kbpd; 2026 = ene-jun)", marker_color=NAVY)
    fig.add_scatter(x=n.index[n.r1p > 0], y=(n.r1p / np.where(n.index == 2024, 366, 365) / 1e3)[n.r1p > 0], name="Reservas 1P del año (kbpd)",
                    line=dict(color=GOLD, width=3), mode="lines+markers")
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=50, b=10), title="Producción real frente a Reservas 1P (total país)",
                      yaxis_title="miles de barriles por día", legend=dict(orientation="h", y=-0.2))
    grafico(fig)
    f = BASE / "ficha_datos.md"
    if f.exists():
        with st.expander("Ficha de datos"):
            st.markdown(f.read_text(encoding="utf-8"))
    pie()


def salir():
    st.session_state.acepta_terminos = False
    st.rerun()


st.navigation([st.Page(pag_ficha, title="Ficha del proyecto", icon="🛢️", default=True),
               st.Page(pag_consulta, title="Consulta", icon="📊", url_path="consulta"),
               st.Page(pag_modelos, title="Modelos", icon="🧩", url_path="modelos"),
               st.Page(pag_alertas, title="Umbral y alertas", icon="🚦", url_path="alertas"),
               st.Page(pag_segmentos, title="Segmentos", icon="🧭", url_path="segmentos"),
               st.Page(pag_datos, title="Datos y precios", icon="🗂️", url_path="datos")]).run()
with st.sidebar:
    st.caption("Uso académico · Universidad EAN 2026")
    if st.button("Ver términos y condiciones"):
        salir()
