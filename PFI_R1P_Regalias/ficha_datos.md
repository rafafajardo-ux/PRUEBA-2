# Ficha de datos — PFI: producción, Reservas 1P y regalías de petróleo en Colombia

Generada por `cuaderno_PFI.ipynb` el 2026-10-16.

## 1. Archivo principal: `datos_crudos/1_ML_OIL_produccion_reservas.xlsx`

- **Fuente o portal:** Agencia Nacional de Hidrocarburos (ANH) y Ministerio de Minas y Energía (MME). Producción fiscalizada de petróleo por campo
  (2023 a junio de 2026) y pronóstico de Reservas Probadas (1P), Probables y Posibles por campo con base en el Informe de Recursos y Reservas (IRR) 2024
  (corte al 31 de diciembre de 2023); consolidado por el equipo en un solo libro. Portal: https://www.anh.gov.co/
- **Licencia o autorización:** datos de carácter reservado, con un único uso académico en el marco de la Especialización en Machine Learning
  de la Universidad EAN (2026). Está prohibido el uso, la distribución, la copia o la mejora, total o parcial, de los datos y de sus resultados.
- **Alcance:** solo se tiene en cuenta el pronóstico de desarrollo de reservas del IRR 2024; no se contempla la migración de reservas probables (2P)
  y posibles (3P) a probadas ni la evolución de los recursos contingentes.
- **Fecha de acceso:** 2026-10-16.
- **Hojas:** `1P_Oil_final_val_col_abr29 2024` (390 filas × 120 columnas), `Petróleo_1P Pronóstico` (320 filas),
  `Petróleo_Prb` (275 filas), `Petróleo_Ps` (262 filas). Las columnas de 2027 a 2060 de "Producción Bls" son fórmulas iguales a la 1P y
  no se usan como dato observado.
- **Unidad:** barriles (bl) por año; barriles por día (bpd). La producción 2026 cubre enero a junio (181 días).
- **Población:** 320 campos con Reservas 1P y 70 campos con producción sin 1P.
- **Cita (APA 7):** Agencia Nacional de Hidrocarburos & Ministerio de Minas y Energía. (2026). *Producción fiscalizada y pronóstico de reservas 1P,
  2P y 3P de petróleo por campo, 2023–2060* [Conjunto de datos]. https://www.anh.gov.co/

### Faltantes por columna (hoja principal, columnas observadas)

| Columna | Tipo | Faltantes | % faltantes |
|---|---|---|---|
| Cod. Dane Departamento | float64 | 75 | 19.2 |
| Departamento | str | 75 | 19.2 |
| Cod. Dane Municipio | float64 | 75 | 19.2 |
| Municipio | str | 75 | 19.2 |
| Operadora | str | 75 | 19.2 |
| Tipo Contrato | str | 75 | 19.2 |
| CAMPO | str | 0 | 0.0 |
| Producción Bls 2023 | float64 | 36 | 9.2 |
| Producción Dia Bls 2023 | float64 | 36 | 9.2 |
| Reservas 1P (bl) 2024 | float64 | 70 | 17.9 |
| Producción Bls 2024 | float64 | 37 | 9.5 |
| Producción Dia Bls 2024 | float64 | 37 | 9.5 |
| Reservas 1P (bl) 2025 | float64 | 70 | 17.9 |
| Producción Bls 2025 | float64 | 45 | 11.5 |
| Producción Dia Bls 2025 | float64 | 45 | 11.5 |
| Reservas 1P (bl) 2026 | float64 | 70 | 17.9 |
| Producción Bls 2026 | float64 | 78 | 20.0 |
| Producción Dia Bls 2026 | float64 | 78 | 20.0 |

### Hojas de reservas (columnas de identificación y años 2024-2030)

| Columna | Tipo | Faltantes | % faltantes |
|---|---|---|---|
| 1P · OPERADOR | str | 0 | 0.0 |
| 1P · CONTRATO | str | 0 | 0.0 |
| 1P · CAMPO | str | 0 | 0.0 |
| 1P · ACTIVIDAD | str | 0 | 0.0 |
| 1P · 2024 | float64 | 0 | 0.0 |
| 1P · 2025 | float64 | 0 | 0.0 |
| 1P · 2026 | float64 | 0 | 0.0 |
| 1P · 2027 | float64 | 0 | 0.0 |
| 1P · 2028 | float64 | 0 | 0.0 |
| 1P · 2029 | float64 | 0 | 0.0 |
| 1P · 2030 | float64 | 0 | 0.0 |
| Prb · CAMPO | str | 45 | 14.1 |
| Prb · 2024 | float64 | 49 | 15.3 |
| Prb · 2025 | float64 | 49 | 15.3 |
| Prb · 2026 | float64 | 48 | 15.0 |
| Prb · 2027 | float64 | 48 | 15.0 |
| Prb · 2028 | float64 | 50 | 15.6 |
| Prb · 2029 | float64 | 55 | 17.2 |
| Prb · 2030 | float64 | 56 | 17.5 |
| Ps · CAMPO | str | 58 | 18.1 |
| Ps · 2024 | float64 | 62 | 19.4 |
| Ps · 2025 | float64 | 59 | 18.4 |
| Ps · 2026 | float64 | 61 | 19.1 |
| Ps · 2027 | float64 | 61 | 19.1 |
| Ps · 2028 | float64 | 62 | 19.4 |
| Ps · 2029 | float64 | 67 | 20.9 |
| Ps · 2030 | float64 | 68 | 21.2 |

## 2. Precios: `datos_crudos/precios_brent_wti_mensual_EIA.csv`

- **Fuente o portal:** U.S. Energy Information Administration (EIA), precios spot mensuales Europe Brent (RBRTE) y WTI Cushing (RWTC); para 2027,
  Short-Term Energy Outlook del 6 de octubre de 2026. Son las mismas referencias que publica investing.com (que no permite descargar promedios anuales).
- **Licencia:** dominio público (datos del Gobierno de EE. UU.).
- **Fecha de acceso:** 2026-10-16. **Filas:** 45 · **Columnas:** 5 (anio, mes, brent_usd_bl, wti_usd_bl, fuente) · sin faltantes.
- **Cita (APA 7):** U.S. Energy Information Administration. (2026). *Europe Brent spot price FOB; Cushing, OK WTI spot price FOB* [Conjunto de datos].
  https://www.eia.gov/dnav/pet/pet_pri_spt_s1_m.htm
