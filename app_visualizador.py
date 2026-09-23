"""
====================================================================================================
VISUALIZADOR Y SIMULADOR INTERACTIVO DEL MOTOR DE RECOMENDACIÓN P2P (EPIS-UPT 2026)
Aplicación Web desarrollada con Streamlit
====================================================================================================
"""

import datetime
import json
import math
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
import streamlit as st

import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import gestor_reportes as gr

from motor_recomendacion import (
    cargar_reglas_sistema,
    filtrar_mentores_sql,
    calcular_similitud_contenido,
    aplicar_reranking_equidad,
    recomendar_mentores,
    resolver_ruta_bd,
)

DB_PATH = resolver_ruta_bd(os.path.join(BASE_DIR, "data", "epis_mentorias.db"))

# --------------------------------------------------------------------------------------------------
# Configuración general de la página Streamlit
# --------------------------------------------------------------------------------------------------
st.set_page_config(
    page_title="Visualizador Algoritmo P2P - EPIS UPT",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilos CSS personalizados para presentación académica
st.markdown("""
<style>
    .main-title {
        font-size: 2.1rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.2rem;
    }
    .metric-badge {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 0.4rem;
        margin-bottom: 0.3rem;
    }
    .badge-blue { background-color: #DBEAFE; color: #1E40AF; }
    .badge-green { background-color: #D1FAE5; color: #065F46; }
    .badge-amber { background-color: #FEF3C7; color: #92400E; }
    .badge-purple { background-color: #EDE9FE; color: #5B21B6; }
    .badge-gray { background-color: #F3F4F6; color: #374151; }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------------------------------
# Funciones auxiliares de carga de datos y renderizado
# --------------------------------------------------------------------------------------------------
def renderizar_tarjeta_mentor(m: Dict[str, Any], rank: Optional[int] = None) -> None:
    """Renderiza una tarjeta de mentor con componentes nativos de Streamlit para evitar bugs de markdown."""
    icono = "🥇" if rank == 1 else ("🥈" if rank == 2 else ("🥉" if rank == 3 else (f"#{rank}" if rank else "👤")))
    bono_badge = '<span class="metric-badge badge-green">✨ Mentor Nuevo (+Bono)</span>' if m.get("es_nuevo") else ""
    
    with st.container(border=True):
        col_c1, col_c2 = st.columns([3, 1])
        with col_c1:
            st.markdown(f"#### {icono} {m['mentor']} <span style='color:#6B7280; font-size:0.95rem;'>(Ciclo {m['ciclo']})</span>", unsafe_allow_html=True)
        with col_c2:
            st.markdown(f"<div style='text-align:right;'><b>Score Final: <code>{m['puntaje_final']}</code></b></div>", unsafe_allow_html=True)
        
        # Badges en una sola línea HTML limpia sin saltos ni indentación
        badges_line = (
            f'<div style="margin-bottom:0.4rem;">'
            f'<span class="metric-badge badge-blue">Puntaje: <b>{m["puntaje_final"]}</b></span>'
            f'<span class="metric-badge badge-green">Similitud Coseno: <b>{m["similitud_coseno"]}</b></span>'
            f'<span class="metric-badge badge-amber">Nota en Curso: <b>{m["nota_en_curso"]}</b></span>'
            f'<span class="metric-badge badge-purple">Sesiones: <b>{m.get("sesiones_activas", 0)} / {m.get("max_cupos", 0)}</b></span>'
            f'{bono_badge}'
            f'</div>'
        )
        st.markdown(badges_line, unsafe_allow_html=True)
        st.markdown(f"**Competencias del Mentor:** `{m['tags']}`")


def generar_grafico_vectores_angulares(
    similitudes: List[float],
    nombres: List[str],
    titulo: str = "Espacio Vectorial Angular: Proyección respecto al Tutorado",
) -> plt.Figure:
    """Genera un diagrama vectorial en coordenadas polares que muestra el ángulo theta real
    entre el vector del estudiante tutorado (referencia en 0°) y cada mentor candidato."""
    fig, ax = plt.subplots(figsize=(8, 7), subplot_kw={"projection": "polar"})
    ax.set_thetamin(0)
    ax.set_thetamax(90)
    ax.set_ylim(0, 1.25)
    
    # Vector de referencia del tutorado en theta = 0 rad
    ax.annotate(
        "", xy=(0, 1.05), xytext=(0, 0),
        arrowprops=dict(facecolor="#DC2626", edgecolor="#B91C1C", width=3, headwidth=10)
    )
    ax.text(0, 1.16, "TUTORADO\n(Vector u | θ = 0°)", color="#DC2626", fontweight="bold", fontsize=9.5, ha="center", va="bottom")
    
    # Paleta de colores para los mentores
    paleta = ["#10B981", "#2563EB", "#8B5CF6", "#F59E0B", "#06B6D4", "#EC4899", "#64748B"]
    
    for idx, (sim, nom) in enumerate(zip(similitudes, nombres)):
        sim_val = max(0.0, min(1.0, float(sim)))
        theta_rad = math.acos(sim_val)  # rango [0, pi/2]
        theta_deg = math.degrees(theta_rad)
        color = paleta[idx % len(paleta)]
        
        radio = 0.90 + 0.15 * sim_val
        ax.annotate(
            "", xy=(theta_rad, radio), xytext=(0, 0),
            arrowprops=dict(facecolor=color, edgecolor=color, width=2, headwidth=8, alpha=0.85)
        )
        
        nom_corto = nom.split()[0] + " " + nom.split()[1] if len(nom.split()) > 1 else nom
        ax.text(
            theta_rad, radio + 0.08,
            f"{nom_corto}\n(θ = {theta_deg:.1f}°, cos = {sim_val:.3f})",
            color=color, fontsize=8.5, ha="center", va="center", fontweight="bold"
        )
        
    ax.set_title(titulo, fontsize=12, pad=20, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.6)
    return fig


def obtener_matriz_tfidf_df(tags_estudiante: str, tags_mentores: List[str], nombres_mentores: List[str]) -> pd.DataFrame:
    """Extrae las dimensiones léxicas y ponderaciones TF-IDF para comparar los vectores numéricamente."""
    textos = [tags_estudiante] + tags_mentores
    tfidf = TfidfVectorizer()
    matriz = tfidf.fit_transform(textos).toarray()
    vocabulario = tfidf.get_feature_names_out()
    
    filas = ["TUTORADO (Vector u)"] + [f"Mentor: {n}" for n in nombres_mentores]
    df = pd.DataFrame(matriz, index=filas, columns=vocabulario)
    
    # Seleccionar columnas prioritarias (donde el tutorado o algún mentor tenga peso significativo)
    cols_tutorado = df.columns[df.loc["TUTORADO (Vector u)"] > 0].tolist()
    otras_cols = [c for c in df.columns if c not in cols_tutorado]
    cols_mostrar = cols_tutorado + otras_cols[:max(0, 10 - len(cols_tutorado))]
    return df[cols_mostrar].round(3)


@st.cache_data
def obtener_catalogo_cursos() -> List[Dict[str, Any]]:
    """Consulta la lista de cursos ordenados por ciclo."""
    if not os.path.exists(DB_PATH):
        return []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT codigo, nombre, ciclo, area FROM cursos ORDER BY ciclo, codigo")
    rows = cursor.fetchall()
    conn.close()
    return [{"codigo": r[0], "nombre": r[1], "ciclo": r[2], "area": r[3]} for r in rows]


@st.cache_data
def obtener_resumen_cohorte() -> Dict[str, Any]:
    """Obtiene estadísticas de la cohorte de 350 estudiantes."""
    if not os.path.exists(DB_PATH):
        return {}
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM estudiantes")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM estudiantes WHERE rol = 'MENTOR'")
    mentores = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM estudiantes WHERE rol = 'TUTORADO'")
    tutorados = cursor.fetchone()[0]
    conn.close()
    return {"total": total, "mentores": mentores, "tutorados": tutorados}


@st.cache_data
def obtener_estudiantes_por_rol(rol: str) -> pd.DataFrame:
    """Extrae la lista completa de estudiantes según su rol (MENTOR o TUTORADO)."""
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    query = """
    SELECT id, codigo_estudiante, nombres || ' ' || apellidos AS nombre_completo,
           nombres, apellidos, ciclo_actual, correo_institucional, rol,
           max_cupos_mentor, sesiones_activas, es_nuevo_mentor, tags_interes
    FROM estudiantes
    WHERE rol = ?
    ORDER BY ciclo_actual, apellidos, nombres
    """
    df = pd.read_sql_query(query, conn, params=(rol,))
    conn.close()
    return df


@st.cache_data
def obtener_kardex_alumno(id_estudiante: int) -> pd.DataFrame:
    """Extrae el historial académico oficial de notas de un estudiante."""
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    query = """
    SELECT codigo_curso, nombre_curso, nota, condicion
    FROM kardex_notas
    WHERE id_estudiante = ?
    ORDER BY codigo_curso
    """
    df = pd.read_sql_query(query, conn, params=(id_estudiante,))
    conn.close()
    return df


@st.cache_data
def obtener_disponibilidad_alumno(id_estudiante: int) -> List[Tuple[str, str]]:
    """Extrae los días y franjas horarias registradas para un estudiante."""
    if not os.path.exists(DB_PATH):
        return []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT dia, franja_horaria FROM disponibilidad WHERE id_estudiante = ? ORDER BY dia, franja_horaria",
        (id_estudiante,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


# --------------------------------------------------------------------------------------------------
# Barra Lateral (Sidebar): Controles Paramétricos Globales
# --------------------------------------------------------------------------------------------------
reglas_base = cargar_reglas_sistema()
pesos_base = reglas_base.get("pesos_algoritmo", {})

st.sidebar.header("⚙️ Calibración del Algoritmo")
st.sidebar.markdown("Hiperparámetros de la fórmula de puntuación:")

alpha = st.sidebar.slider(
    "α (Afinidad Temática Coseno)",
    min_value=0.0,
    max_value=1.0,
    value=float(pesos_base.get("alpha_coseno", 0.70)),
    step=0.05,
    help="Ponderación de la similitud angular entre los tags del alumno y del mentor.",
)

beta = st.sidebar.slider(
    "β (Penalización por Saturación)",
    min_value=0.0,
    max_value=1.0,
    value=float(pesos_base.get("beta_saturacion", 0.20)),
    step=0.05,
    help="Deducción de puntaje proporcional a la carga de trabajo (sesiones_activas / max_cupos).",
)

gamma = st.sidebar.slider(
    "γ (Bono para Mentor Nuevo)",
    min_value=0.0,
    max_value=1.0,
    value=float(pesos_base.get("gamma_bono_nuevo", 0.10)),
    step=0.05,
    help="Incentivo de oportunidad para mentores sin tutorías previas.",
)

top_k = st.sidebar.number_input(
    "K (Top-K Recomendaciones)",
    min_value=1,
    max_value=10,
    value=int(reglas_base.get("top_k_recomendados", 3)),
    step=1,
    help="Cantidad de candidatos finales sugeridos al estudiante.",
)

nota_minima = st.sidebar.slider(
    "Nota Mínima del Mentor",
    min_value=11.0,
    max_value=20.0,
    value=float(reglas_base.get("nota_minima_mentor", 14.0)),
    step=0.5,
    help="Umbral del filtro duro relacional en SQL.",
)

st.sidebar.markdown("---")
st.sidebar.markdown(f"""
**Resumen de Pesos Actuales:**
* **α:** `{alpha:.2f}` | **β:** `{beta:.2f}` | **γ:** `{gamma:.2f}`
* **Suma Pesos:** `{alpha + beta + gamma:.2f}`
""")


# --------------------------------------------------------------------------------------------------
# Encabezado Principal
# --------------------------------------------------------------------------------------------------
st.markdown('<div class="main-title">🎓 Plataforma de Visualización y Análisis Algorítmico P2P</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">'
    'EPIS-UPT 2026-II | Inferencia Two-Stage con Filtro Relacional SQL, TF-IDF + Coseno y Load-Aware Re-ranking'
    '</div>',
    unsafe_allow_html=True,
)

# Pestañas principales
tab_guiado, tab_directorio, tab_simulador, tab_fase1, tab_fase2, tab_fase4, tab_cohorte, tab_reportes = st.tabs([
    "🎯 1. Emparejamiento por Estudiante",
    "👥 2. Directorio EPIS (Mentores / Tutorados)",
    "⚡ 3. Simulador Rápido por Curso",
    "🔍 4. Fase 1: Filtro Determinista (SQL)",
    "📐 5. Fase 2: Similitud Coseno (TF-IDF)",
    "⚖️ 6. Fase 4: Load-Aware Re-ranking",
    "📊 7. Cohorte Completa (350)",
    "📁 8. Repositorio de Reportes",
])


# ==================================================================================================
# TAB 1: Emparejamiento Guiado por Estudiante (Tutorado)
# ==================================================================================================
with tab_guiado:
    st.subheader("🎯 Emparejamiento Centrado en el Estudiante Tutorado")
    st.markdown("""
    Selecciona un alumno tutorado de la cohorte sintética experimental para precargar automáticamente su perfil,
    su historial de calificaciones (Kardex) y sus horarios libres registrados.
    """)

    df_tutorados = obtener_estudiantes_por_rol("TUTORADO")

    if df_tutorados.empty:
        st.error("No se encontraron registros de tutorados en la base de datos.")
    else:
        # Selector de estudiante
        opciones_estudiantes = {
            f"{row['codigo_estudiante']} - {row['nombre_completo']} (Ciclo {row['ciclo_actual']})": row
            for _, row in df_tutorados.iterrows()
        }
        
        col_sel1, col_sel2 = st.columns([3, 1])
        with col_sel1:
            estudiante_sel_str = st.selectbox(
                "Seleccionar Estudiante Tutorado:",
                options=list(opciones_estudiantes.keys()),
                index=0,
            )
        alumno_sel = opciones_estudiantes[estudiante_sel_str]

        # Cargar kardex y disponibilidad del estudiante
        kardex_alumno = obtener_kardex_alumno(alumno_sel["id"])
        disp_alumno = obtener_disponibilidad_alumno(alumno_sel["id"])

        # Ficha del Alumno con Container Nativo
        with st.container(border=True):
            col_a1, col_a2 = st.columns([3, 1])
            with col_a1:
                st.markdown(f"#### 👤 {alumno_sel['nombre_completo']} <span style='font-size:0.9rem; color:#4B5563;'>(Código: `{alumno_sel['codigo_estudiante']}` | Ciclo {alumno_sel['ciclo_actual']})</span>", unsafe_allow_html=True)
                st.markdown(f"**📧 Correo Institucional:** `{alumno_sel['correo_institucional']}`")
            with col_a2:
                st.metric("Ciclo Actual", f"Ciclo {alumno_sel['ciclo_actual']}")
            
            horarios_str = " ".join([f"`🕒 {d} ({f})`" for d, f in disp_alumno]) if disp_alumno else "_Sin horarios registrados_"
            tags_str = " ".join([f"`🏷️ {t}`" for t in alumno_sel["tags_interes"].split()])
            st.markdown(f"**Disponibilidad Semanal:** {horarios_str}")
            st.markdown(f"**Áreas de Interés / Dificultades:** {tags_str}")

        # Configuración de la Solicitud del Alumno
        st.markdown("#### ⚙️ Configurar Preferencias de la Sesión")
        col_pref1, col_pref2, col_pref3 = st.columns([2, 1, 1])

        # Cursos en los que está matriculado o cursando
        cursos_kardex = []
        for _, row in kardex_alumno.iterrows():
            cursos_kardex.append(f"{row['codigo_curso']} - {row['nombre_curso']} (Nota: {row['nota']} | {row['condicion']})")

        catalogo_total = obtener_catalogo_cursos()
        todos_cursos_str = [f"{c['codigo']} - {c['nombre']} (Ciclo {c['ciclo']})" for c in catalogo_total]

        lista_cursos_disponibles = cursos_kardex if cursos_kardex else todos_cursos_str

        with col_pref1:
            curso_elegido_str = st.selectbox("Curso en el que necesita apoyo:", options=lista_cursos_disponibles, index=0)
            codigo_curso_objetivo = curso_elegido_str.split(" - ")[0]

            # Buscar nota del tutorado en este curso
            nota_tutorado_match = kardex_alumno[kardex_alumno["codigo_curso"] == codigo_curso_objetivo]
            if not nota_tutorado_match.empty:
                nota_tutorado_val = float(nota_tutorado_match.iloc[0]["nota"])
                condicion_tutorado_val = str(nota_tutorado_match.iloc[0]["condicion"])
            else:
                nota_tutorado_val = 11.0
                condicion_tutorado_val = "CURSANDO"

        # Horarios compatibles (precargando la disponibilidad del propio alumno)
        opciones_horario = [f"{d} | {f}" for d, f in disp_alumno]
        if not opciones_horario:
            opciones_horario = ["Sabado | 08:00 - 10:30", "Sabado | 10:30 - 13:00", "Lunes | 15:00 - 16:40"]

        with col_pref2:
            horario_elegido_str = st.selectbox("Horario preferido para la mentoría:", options=opciones_horario, index=0)
            dia_objetivo = horario_elegido_str.split(" | ")[0]
            franja_objetiva = horario_elegido_str.split(" | ")[1]

        with col_pref3:
            st.metric("Nota del Alumno en Curso", f"{nota_tutorado_val:.1f}", delta=condicion_tutorado_val, delta_color="off")

        # Tags de consulta (precargados con los del alumno pero editables)
        tags_consulta = st.text_input(
            "Temas específicos de consulta / dudas:",
            value=alumno_sel["tags_interes"],
            help="Puedes editar o agregar dudas específicas para esta sesión de mentoría.",
        )

        st.markdown("---")

        # EJECUTAR RECOMENDACIÓN REACTIVA
        tiempo_ini_guiado = time.perf_counter()

        mentores_sql_guiado = filtrar_mentores_sql(
            codigo_curso=codigo_curso_objetivo,
            dia=dia_objetivo,
            franja_horaria=franja_objetiva,
            nota_minima=nota_minima,
            db_path=DB_PATH,
        )

        if not mentores_sql_guiado:
            st.warning(
                f"⚠️ No hay mentores disponibles para **{codigo_curso_objetivo}** el día **{dia_objetivo} ({franja_objetiva})** con nota >= {nota_minima}."
            )
            st.info("💡 Intenta seleccionar otro horario de disponibilidad del alumno o ajusta la nota mínima en la barra lateral.")
        else:
            textos_mentores_g = [m[4] for m in mentores_sql_guiado]
            nombres_mentores_g = [f"{m[1]} {m[2]}" for m in mentores_sql_guiado]
            similitudes_g = calcular_similitud_contenido(tags_consulta, textos_mentores_g)
            
            ranking_guiado = aplicar_reranking_equidad(
                mentores_candidatos=mentores_sql_guiado,
                similitudes=similitudes_g,
                alpha=alpha,
                beta=beta,
                gamma=gamma,
            )
            top_k_guiado = ranking_guiado[:top_k]
            tiempo_ms_guiado = (time.perf_counter() - tiempo_ini_guiado) * 1000.0

            st.markdown(f"### 🏆 Mentores Ideales para {alumno_sel['nombres']} ({len(top_k_guiado)} seleccionados en {tiempo_ms_guiado:.2f} ms)")

            # Renderizar tarjetas con función corregida
            for r, m in enumerate(top_k_guiado, start=1):
                renderizar_tarjeta_mentor(m, rank=r)

            # --------------------------------------------------------------------------------------
            # SECCIÓN VECTORIAL: Proyección Angular y Vectores de Mentor y Tutorado
            # --------------------------------------------------------------------------------------
            st.markdown("#### 📐 Proyección de Vectores y Relación Angular (TF-IDF + Coseno)")
            st.markdown("""
            > **Fundamento Trigonométrico:** La compatibilidad semántica se basa en el **ángulo $\\theta$** entre el vector del alumno ($\\vec{u}$) y el vector del mentor ($\\vec{m}$):
            > $$\\cos(\\theta) = \\frac{\\vec{u} \\cdot \\vec{m}}{\\|\\vec{u}\\| \\|\\vec{m}\\|} \\implies \\theta = \\arccos(\\text{SimilitudCoseno})$$
            > * **$\\theta \\approx 0^\\circ$ (Alineación máxima, $\\cos\\theta \\approx 1.0$):** Máxima afinidad temática (lenguaje y competencias casi idénticos).
            > * **$\\theta = 90^\\circ$ (Ortogonales, $\\cos\\theta = 0.0$):** Sin ninguna palabra ni competencia en común.
            """)

            col_vec1, col_vec2 = st.columns([1, 1])

            with col_vec1:
                # Diagrama Polar de Vectores
                fig_polar = generar_grafico_vectores_angulares(
                    similitudes=[m["similitud_coseno"] for m in ranking_guiado],
                    nombres=[m["mentor"] for m in ranking_guiado],
                    titulo=f"Proyección Angular respecto a {alumno_sel['nombres']}",
                )
                st.pyplot(fig_polar)
                plt.close()

            with col_vec2:
                # Tabla de Ángulos y Distancias
                df_angulos = []
                for m in ranking_guiado:
                    sim_val = max(0.0, min(1.0, float(m["similitud_coseno"])))
                    th_rad = math.acos(sim_val)
                    th_deg = math.degrees(th_rad)
                    
                    if th_deg < 50.0:
                        interp = "🟢 Ángulo Estrecho (Alta afinidad)"
                    elif th_deg < 75.0:
                        interp = "🟡 Ángulo Moderado"
                    elif th_deg < 89.0:
                        interp = "🟠 Ángulo Amplio (Baja afinidad)"
                    else:
                        interp = "🔴 Ortogonal (Sin coincidencia)"

                    # Buscar palabras coincidentes
                    set_tutorado = set(tags_consulta.lower().split())
                    set_mentor = set(m["tags"].lower().split())
                    coincidentes = set_tutorado.intersection(set_mentor)
                    coinc_str = ", ".join(coincidentes) if coincidentes else "_Ninguna_"

                    df_angulos.append({
                        "Mentor": m["mentor"],
                        "Similitud Coseno (cos θ)": m["similitud_coseno"],
                        "Ángulo θ (Grados)": f"{th_deg:.1f}°",
                        "Interpretación Geométrica": interp,
                        "Tags Coincidentes": coinc_str,
                    })

                st.markdown("**Tabla Geométrica de Ángulos y Coincidencias:**")
                st.dataframe(pd.DataFrame(df_angulos), use_container_width=True)

            # Matriz de Componentes Vectoriales (Pesos TF-IDF)
            st.markdown("##### 🔠 Matriz de Pesos en el Espacio Vectorial (TF-IDF por Término)")
            st.caption("Muestra las dimensiones (palabras clave) que componen cada vector y activan el producto punto:")
            df_matriz_tfidf = obtener_matriz_tfidf_df(tags_consulta, textos_mentores_g, nombres_mentores_g)
            st.dataframe(df_matriz_tfidf, use_container_width=True)

            st.markdown("---")

            # --------------------------------------------------------------------------------------
            # CUADRO 1: Comparativa de Calificaciones (Tutorado vs. Mentor)
            # --------------------------------------------------------------------------------------
            st.markdown("#### 📊 Cuadro Comparativo de Rendimiento Académico en la Materia")
            st.markdown(f"""
            Enfrenta la calificación del estudiante solicitante (**{nota_tutorado_val:.1f}** en `{codigo_curso_objetivo}`)
            frente a las notas de excelencia ($\\ge 14.0$) obtenidas por los mentores candidatos recomendados:
            """)

            df_comp_notas = []
            for m in ranking_guiado:
                brecha = m["nota_en_curso"] - nota_tutorado_val
                df_comp_notas.append({
                    "Mentor": m["mentor"],
                    "Ciclo Mentor": m["ciclo"],
                    "Nota Mentor (APROBADO)": m["nota_en_curso"],
                    "Nota Tutorado": nota_tutorado_val,
                    "Brecha Académica (+Puntos)": round(brecha, 1),
                    "Similitud Coseno": m["similitud_coseno"],
                    "Score Final": m["puntaje_final"],
                })
            df_notas_tab = pd.DataFrame(df_comp_notas)
            st.dataframe(df_notas_tab, use_container_width=True)

            # Gráfico de barras comparando notas
            fig_notas, ax_notas = plt.subplots(figsize=(10, max(3.5, len(df_notas_tab) * 0.45)))
            y_pos = np.arange(len(df_notas_tab))
            alto = 0.35

            df_plot_notas = df_notas_tab.iloc[::-1]  # Invertir para mostrar el mejor arriba
            ax_notas.barh(y_pos - alto/2, df_plot_notas["Nota Mentor (APROBADO)"], height=alto, label="Nota Mentor", color="#2563EB")
            ax_notas.barh(y_pos + alto/2, df_plot_notas["Nota Tutorado"], height=alto, label=f"Nota Tutorado ({alumno_sel['nombres']})", color="#F59E0B")
            ax_notas.axvline(x=14.0, color="#DC2626", linestyle="--", alpha=0.7, label="Umbral Mínimo Mentor (14.0)")

            ax_notas.set_yticks(y_pos)
            ax_notas.set_yticklabels(df_plot_notas["Mentor"])
            ax_notas.set_xlim(0, 21)
            ax_notas.set_xlabel("Calificación Vigesimal (0 - 20)")
            ax_notas.set_title(f"Contraste Académico en {codigo_curso_objetivo}: Tutorado vs. Mentores Candidatos", fontsize=11)
            ax_notas.legend(loc="lower right")
            ax_notas.grid(axis="x", linestyle="--", alpha=0.5)

            plt.tight_layout()
            st.pyplot(fig_notas)
            plt.close()

            # --------------------------------------------------------------------------------------
            # CUADRO 2: Relación entre los Algoritmos y Componentes del Sistema
            # --------------------------------------------------------------------------------------
            st.markdown("#### ⚖️ Cuadro Analítico de Interacción entre Algoritmos")
            st.markdown(f"""
            Desglose paso a paso de cómo cada componente matemático influye en la decisión final:
            $$\\text{{Score}} = ({alpha:.2f} \\cdot \\text{{Coseno}}) - ({beta:.2f} \\cdot \\text{{Saturación}}) + ({gamma:.2f} \\cdot \\text{{BonoNuevo}})$$
            """)

            df_analisis_alg = []
            # Calcular posiciones preliminares solo por coseno
            ranking_solo_coseno = sorted(ranking_guiado, key=lambda x: x["similitud_coseno"], reverse=True)
            orden_coseno_dict = {m["id"]: pos + 1 for pos, m in enumerate(ranking_solo_coseno)}

            for pos_final, m in enumerate(ranking_guiado, start=1):
                pos_inicial = orden_coseno_dict[m["id"]]
                cambio_pos = pos_inicial - pos_final
                cambio_str = f"⬆️ +{cambio_pos}" if cambio_pos > 0 else (f"⬇️ {cambio_pos}" if cambio_pos < 0 else "⏺️ 0")

                sat = m["sesiones_activas"] / m["max_cupos"] if m["max_cupos"] > 0 else 1.0
                bono = gamma if m["es_nuevo"] else 0.0

                df_analisis_alg.append({
                    "Rank Final": pos_final,
                    "Rank Coseno Puro": pos_inicial,
                    "Cambio de Posición": cambio_str,
                    "Mentor": m["mentor"],
                    "Sim Coseno (TF-IDF)": m["similitud_coseno"],
                    f"Afinidad ({alpha}·Sim)": round(alpha * m["similitud_coseno"], 4),
                    "Saturación (%)": f"{round(sat * 100, 0)}%",
                    f"Penalización (-{beta}·Sat)": round(-beta * sat, 4),
                    f"Bono Novedad (+{gamma}·Bono)": round(bono, 4),
                    "Puntaje Final": m["puntaje_final"],
                })

            df_analisis_tab = pd.DataFrame(df_analisis_alg)
            st.dataframe(df_analisis_tab, use_container_width=True)

            # Gráfico de dispersión/relación: Similitud Coseno vs Puntaje Final
            fig_rel, ax_rel = plt.subplots(figsize=(9, 4.5))
            sims = [m["similitud_coseno"] for m in ranking_guiado]
            scores = [m["puntaje_final"] for m in ranking_guiado]
            nombres = [m["mentor"].split()[0] + " " + m["mentor"].split()[1][:1] + "." for m in ranking_guiado]

            colores = ["#10B981" if m["es_nuevo"] else "#3B82F6" for m in ranking_guiado]
            sizes = [(1.0 - (m["sesiones_activas"] / m["max_cupos"])) * 250 + 100 for m in ranking_guiado]

            scatter = ax_rel.scatter(sims, scores, c=colores, s=sizes, alpha=0.8, edgecolors="black")

            for i, nom in enumerate(nombres):
                ax_rel.annotate(nom, (sims[i], scores[i] + 0.015), fontsize=8.5, ha="center")

            ax_rel.set_xlabel("Similitud de Coseno Bruta (TF-IDF)")
            ax_rel.set_ylabel("Puntaje Final Calibrado (Re-ranking)")
            ax_rel.set_title("Relación entre Afinidad Semántica y Score Final (Tamaño = Capacidad Disponible, Verde = Mentor Nuevo)")
            ax_rel.grid(True, linestyle="--", alpha=0.5)

            plt.tight_layout()
            st.pyplot(fig_rel)
            plt.close()

            # --------------------------------------------------------------------------------------
            # SECCIÓN DE AUDITORÍA Y GENERACIÓN DE REPORTE EXPERIMENTAL
            # --------------------------------------------------------------------------------------
            st.markdown("---")
            st.markdown("#### 📄 Generación y Registro de Reporte de Inferencia")
            st.markdown(
                "Guarda un informe formal de esta recomendación en el repositorio institucional `reportes/` para trazabilidad y sustento de la tesis."
            )

            col_btn_rep, _ = st.columns([1, 2])
            with col_btn_rep:
                btn_generar = st.button("💾 Generar y Guardar Reporte en Repositorio", type="primary", use_container_width=True)

            if btn_generar:
                datos_rep = {
                    "id_reporte": f"REP-{codigo_curso_objetivo}-{alumno_sel['codigo_estudiante']}-{int(time.time())}",
                    "fecha_generacion": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "tutorado": {
                        "id": int(alumno_sel["id"]),
                        "codigo": str(alumno_sel["codigo_estudiante"]),
                        "nombre_completo": str(alumno_sel["nombre_completo"]),
                        "ciclo": int(alumno_sel["ciclo_actual"]),
                        "correo": str(alumno_sel["correo_institucional"]),
                        "tags": str(alumno_sel["tags_interes"]),
                        "disponibilidad": [f"{d} ({f})" for d, f in disp_alumno],
                    },
                    "solicitud": {
                        "codigo_curso": str(codigo_curso_objetivo),
                        "nombre_curso": str(curso_elegido_str),
                        "nota_tutorado": float(nota_tutorado_val),
                        "condicion_tutorado": str(condicion_tutorado_val),
                        "dia": str(dia_objetivo),
                        "franja_horaria": str(franja_objetiva),
                        "tags_consulta": str(tags_consulta),
                    },
                    "configuracion_algoritmo": {
                        "pesos": {"alpha": float(alpha), "beta": float(beta), "gamma": float(gamma)},
                        "top_k": int(top_k),
                        "nota_minima_mentor": float(nota_minima),
                    },
                    "fase1_filtro_sql": {
                        "total_candidatos_aptos": len(mentores_sql_guiado),
                        "mentores_aptos": [
                            {
                                "id": int(m[0]),
                                "mentor": f"{m[1]} {m[2]}",
                                "ciclo": int(m[3]),
                                "nota_en_curso": float(m[8]),
                                "sesiones": int(m[5]),
                                "max_cupos": int(m[6]),
                                "es_nuevo": bool(m[7]),
                            }
                            for m in mentores_sql_guiado
                        ],
                    },
                    "fase2_espacio_vectorial": {
                        "mediciones_angulares": df_angulos,
                    },
                    "fase4_reranking_equidad": {
                        "desglose_calibracion": df_analisis_alg,
                    },
                    "top_k_recomendados": top_k_guiado,
                    "telemetria": {
                        "tiempo_inferencia_ms": round(float(tiempo_ms_guiado), 2),
                    },
                }

                ruta_json, ruta_md = gr.guardar_reporte(datos_rep)
                st.success(f"✓ Reporte generado y almacenado con éxito en `{gr.DIRECTORIO_REPORTES}/`!")
                st.caption(f"Archivos: `{os.path.basename(ruta_md)}` y `{os.path.basename(ruta_json)}`")

                # Botones de descarga directa
                col_dl1, col_dl2 = st.columns(2)
                with col_dl1:
                    st.download_button(
                        label="📥 Descargar Reporte en Markdown (.md)",
                        data=gr.generar_markdown_reporte(datos_rep),
                        file_name=os.path.basename(ruta_md),
                        mime="text/markdown",
                        use_container_width=True,
                    )
                with col_dl2:
                    st.download_button(
                        label="📥 Descargar Reporte en JSON (.json)",
                        data=json.dumps(datos_rep, indent=2, ensure_ascii=False),
                        file_name=os.path.basename(ruta_json),
                        mime="application/json",
                        use_container_width=True,
                    )


# ==================================================================================================
# TAB 2: Directorio EPIS (Mentores y Tutorados)
# ==================================================================================================
with tab_directorio:
    st.subheader("👥 Directorio Oficial de la Cohorte Piloto (350 Estudiantes)")
    st.markdown("Consulta y filtra los perfiles completos de mentores avanzados y estudiantes tutorados.")

    subtab_mentores, subtab_tutorados = st.tabs(["🎓 Mentores Avanzados (40)", "🎒 Estudiantes Tutorados (310)"])

    with subtab_mentores:
        df_m = obtener_estudiantes_por_rol("MENTOR")
        if not df_m.empty:
            col_fm1, col_fm2 = st.columns(2)
            with col_fm1:
                ciclos_sel_m = st.multiselect("Filtrar por Ciclo:", options=[7, 8, 9, 10], default=[7, 8, 9, 10], key="filtro_ciclo_m")
            with col_fm2:
                buscar_m = st.text_input("Buscar Mentor por Nombre o Tag:", key="busc_m")

            df_m_filtrado = df_m[df_m["ciclo_actual"].isin(ciclos_sel_m)]
            if buscar_m:
                df_m_filtrado = df_m_filtrado[
                    df_m_filtrado["nombre_completo"].str.contains(buscar_m, case=False) |
                    df_m_filtrado["tags_interes"].str.contains(buscar_m, case=False)
                ]

            st.markdown(f"Mostrando **{len(df_m_filtrado)}** mentores:")
            df_m_display = df_m_filtrado[[
                "id", "codigo_estudiante", "nombre_completo", "ciclo_actual",
                "sesiones_activas", "max_cupos_mentor", "es_nuevo_mentor", "tags_interes"
            ]].copy()
            df_m_display.rename(columns={
                "id": "ID", "codigo_estudiante": "Código", "nombre_completo": "Nombre Completo",
                "ciclo_actual": "Ciclo", "sesiones_activas": "Sesiones Activas", "max_cupos_mentor": "Cupos Max",
                "es_nuevo_mentor": "Es Nuevo", "tags_interes": "Tags de Competencia"
            }, inplace=True)
            df_m_display["Es Nuevo"] = df_m_display["Es Nuevo"].apply(lambda x: "Sí" if x == 1 else "No")
            st.dataframe(df_m_display, use_container_width=True)

    with subtab_tutorados:
        df_t = obtener_estudiantes_por_rol("TUTORADO")
        if not df_t.empty:
            col_ft1, col_ft2 = st.columns(2)
            with col_ft1:
                ciclos_sel_t = st.multiselect("Filtrar por Ciclo:", options=[1, 2, 3, 4, 5, 6], default=[1, 2, 3, 4, 5, 6], key="filtro_ciclo_t")
            with col_ft2:
                buscar_t = st.text_input("Buscar Tutorado por Nombre o Tag:", key="busc_t")

            df_t_filtrado = df_t[df_t["ciclo_actual"].isin(ciclos_sel_t)]
            if buscar_t:
                df_t_filtrado = df_t_filtrado[
                    df_t_filtrado["nombre_completo"].str.contains(buscar_t, case=False) |
                    df_t_filtrado["tags_interes"].str.contains(buscar_t, case=False)
                ]

            st.markdown(f"Mostrando **{len(df_t_filtrado)}** tutorados:")
            df_t_display = df_t_filtrado[[
                "id", "codigo_estudiante", "nombre_completo", "ciclo_actual",
                "correo_institucional", "tags_interes"
            ]].copy()
            df_t_display.rename(columns={
                "id": "ID", "codigo_estudiante": "Código", "nombre_completo": "Nombre Completo",
                "ciclo_actual": "Ciclo", "correo_institucional": "Correo", "tags_interes": "Tags Registrados"
            }, inplace=True)
            st.dataframe(df_t_display, use_container_width=True)


# ==================================================================================================
# TAB 3: Simulador Rápido por Curso
# ==================================================================================================
with tab_simulador:
    st.subheader("⚡ Simulación Rápida de Solicitudes Libres")
    
    col_sim_c1, col_sim_c2, col_sim_c3 = st.columns([2, 1, 1])
    
    catalogo = obtener_catalogo_cursos()
    opciones_cursos_sim = [f"{c['codigo']} - {c['nombre']} (Ciclo {c['ciclo']})" for c in catalogo]
    idx_default_sim = 0
    for idx, c in enumerate(catalogo):
        if c["codigo"] == "INE-186":
            idx_default_sim = idx
            break

    with col_sim_c1:
        curso_sim_str = st.selectbox("Curso a consultar:", opciones_cursos_sim, index=idx_default_sim, key="sim_curso")
        codigo_sim = curso_sim_str.split(" - ")[0]
    with col_sim_c2:
        dia_sim = st.selectbox("Día:", ["Sabado", "Lunes", "Martes", "Miercoles", "Jueves", "Viernes"], index=0, key="sim_dia")
    with col_sim_c3:
        franja_sim = st.selectbox(
            "Franja:",
            ["08:00 - 10:30", "10:30 - 12:10", "10:30 - 13:00", "15:00 - 16:40", "16:40 - 18:20", "18:20 - 20:00", "20:00 - 21:40"],
            index=0,
            key="sim_franja",
        )

    tags_sim = st.text_input(
        "Tags de consulta rápida:",
        value="calculo_diferencial algebra logica_proposicional",
        key="sim_tags",
    )

    t_ini = time.perf_counter()
    mentores_sql_sim = filtrar_mentores_sql(codigo_sim, dia_sim, franja_sim, nota_minima=nota_minima, db_path=DB_PATH)
    
    if mentores_sql_sim:
        similitudes_sim = calcular_similitud_contenido(tags_sim, [m[4] for m in mentores_sql_sim])
        ranking_sim = aplicar_reranking_equidad(mentores_sql_sim, similitudes_sim, alpha=alpha, beta=beta, gamma=gamma)
        top_k_sim = ranking_sim[:top_k]
        t_total_ms = (time.perf_counter() - t_ini) * 1000.0

        st.success(f"✓ {len(mentores_sql_sim)} candidatos evaluados en {t_total_ms:.2f} ms. Mostrando Top {len(top_k_sim)}:")
        for r, m in enumerate(top_k_sim, start=1):
            renderizar_tarjeta_mentor(m, rank=r)
    else:
        st.warning(f"No hay mentores que cumplan los filtros para {codigo_sim} en {dia_sim} {franja_sim}.")


# ==================================================================================================
# TAB 4: Fase 1 (SQL Hard Rules)
# ==================================================================================================
with tab_fase1:
    st.subheader("🔍 Poda Relacional Determinista en SQLite")
    st.markdown(f"""
    En esta etapa, el motor ejecuta la consulta relacional con **Filtros Duros** sobre `epis_mentorias.db`.
    - **Criterio 1:** Rol = `'MENTOR'` (Ciclos VII a X).
    - **Criterio 2:** Materia aprobada con calificación vigesimal $\\ge {nota_minima}$.
    - **Criterio 3:** Disponibilidad exacta en día y franja solicitados.
    - **Criterio 4:** Cupo operativo disponible (`sesiones_activas < max_cupos_mentor`).
    """)

    if mentores_sql_sim:
        df_sql = pd.DataFrame([
            {
                "ID": m[0],
                "Nombres": f"{m[1]} {m[2]}",
                "Ciclo": m[3],
                "Nota en Curso": m[8],
                "Sesiones Activas": m[5],
                "Cupos Máximos": m[6],
                "Saturación (%)": round((m[5] / m[6]) * 100, 1) if m[6] > 0 else 100.0,
                "Es Nuevo": "Sí" if m[7] == 1 else "No",
                "Tags de Competencia": m[4],
            }
            for m in mentores_sql_sim
        ])
        st.dataframe(df_sql, use_container_width=True)
    else:
        st.info("Sin datos de candidatos aptos en esta combinación.")


# ==================================================================================================
# TAB 5: Fase 2 (TF-IDF + Coseno)
# ==================================================================================================
with tab_fase2:
    st.subheader("📐 Modelamiento Semántico en Espacio Vectorial y Diagrama Polar")
    st.markdown("""
    Visualización geométrica del vector del tutorado vs. los vectores de los mentores en el cuadrante angular $[0^\\circ, 90^\\circ]$.
    """)

    if mentores_sql_sim and len(similitudes_sim) > 0:
        nombres_sim = [f"{m[1]} {m[2]}" for m in mentores_sql_sim]
        
        col_f2_1, col_f2_2 = st.columns([1, 1])
        with col_f2_1:
            fig_pol_f2 = generar_grafico_vectores_angulares(
                similitudes=list(similitudes_sim),
                nombres=nombres_sim,
                titulo=f"Proyección Angular Polar ({codigo_sim})",
            )
            st.pyplot(fig_pol_f2)
            plt.close()

        with col_f2_2:
            df_sim_tabla = pd.DataFrame({
                "Mentor": nombres_sim,
                "Similitud Coseno": [round(float(s), 4) for s in similitudes_sim],
                "Ángulo θ": [f"{math.degrees(math.acos(max(0.0, min(1.0, float(s))))):.1f}°" for s in similitudes_sim],
                "Tags": [m[4] for m in mentores_sql_sim],
            }).sort_values(by="Similitud Coseno", ascending=False)
            st.dataframe(df_sim_tabla, use_container_width=True)

        st.markdown("##### 🔠 Matriz de Pesos en el Espacio Vectorial (TF-IDF)")
        df_tfidf_f2 = obtener_matriz_tfidf_df(tags_sim, [m[4] for m in mentores_sql_sim], nombres_sim)
        st.dataframe(df_tfidf_f2, use_container_width=True)
    else:
        st.info("Sin datos para graficar espacio vectorial.")


# ==================================================================================================
# TAB 6: Fase 4 (Load-Aware Re-ranking)
# ==================================================================================================
with tab_fase4:
    st.subheader("⚖️ Balance de Carga y Oportunidad (Load-Aware Re-ranking)")
    st.latex(
        rf"\text{{PuntajeFinal}}(m) = {alpha:.2f} \cdot \text{{SimCoseno}} - {beta:.2f} \cdot \text{{Saturacion}} + {gamma:.2f} \cdot \text{{BonoNuevo}}"
    )

    if mentores_sql_sim and ranking_sim:
        df_desglose = []
        for r in ranking_sim:
            sat = r["sesiones_activas"] / r["max_cupos"] if r["max_cupos"] > 0 else 1.0
            bono = gamma if r["es_nuevo"] else 0.0
            term_sim = alpha * r["similitud_coseno"]
            term_sat = beta * sat
            df_desglose.append({
                "Mentor": r["mentor"],
                "Sim Coseno": r["similitud_coseno"],
                f"α·Sim ({alpha})": round(term_sim, 4),
                f"-β·Sat ({beta})": round(-term_sat, 4),
                f"+γ·Bono ({gamma})": round(bono, 4),
                "Score Final": r["puntaje_final"],
                "Saturación": f"{round(sat * 100, 0)}%",
                "Es Nuevo": "Sí" if r["es_nuevo"] else "No",
            })

        df_rank = pd.DataFrame(df_desglose)
        st.dataframe(df_rank, use_container_width=True)

        fig_comp, ax_comp = plt.subplots(figsize=(10, max(4, len(df_rank) * 0.45)))
        y_pos = np.arange(len(df_rank))
        h = 0.35

        df_rank_plot = df_rank.iloc[::-1]
        ax_comp.barh(y_pos - h/2, df_rank_plot["Sim Coseno"], height=h, label="Similitud Coseno Bruta", color="#93C5FD")
        ax_comp.barh(y_pos + h/2, df_rank_plot["Score Final"], height=h, label="Puntaje Final Equitativo", color="#1D4ED8")

        ax_comp.set_yticks(y_pos)
        ax_comp.set_yticklabels(df_rank_plot["Mentor"])
        ax_comp.set_xlabel("Puntaje")
        ax_comp.set_title("Efecto del Re-ranking: Coseno Puro vs. Puntaje Final Calibrado", fontsize=11)
        ax_comp.legend()
        ax_comp.grid(axis="x", linestyle="--", alpha=0.5)

        plt.tight_layout()
        st.pyplot(fig_comp)
        plt.close()
    else:
        st.info("Sin datos para graficar la etapa de re-ranking.")


# ==================================================================================================
# TAB 7: Cohorte Completa (350 Alumnos)
# ==================================================================================================
with tab_cohorte:
    st.subheader("📊 Distribución de la Muestra Piloto (EPIS-UPT)")
    resumen = obtener_resumen_cohorte()
    col_c1, col_c2, col_c3 = st.columns(3)
    col_c1.metric("Población Total", f"{resumen.get('total', 350)} estudiantes")
    col_c2.metric("Mentores Avanzados (VII - X)", f"{resumen.get('mentores', 40)} estudiantes")
    col_c3.metric("Tutorados (I - VI)", f"{resumen.get('tutorados', 310)} estudiantes")

    st.markdown("---")
    
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        df_dist_ciclos = pd.read_sql_query(
            "SELECT ciclo_actual as Ciclo, rol as Rol, COUNT(*) as Total FROM estudiantes GROUP BY ciclo_actual, rol ORDER BY ciclo_actual",
            conn,
        )
        conn.close()

        fig_dist, ax_dist = plt.subplots(figsize=(9, 4))
        pivot_df = df_dist_ciclos.pivot(index="Ciclo", columns="Rol", values="Total").fillna(0)
        pivot_df.plot(kind="bar", stacked=True, ax=ax_dist, color={"MENTOR": "#2563EB", "TUTORADO": "#93C5FD"})
        ax_dist.set_ylabel("Cantidad de Estudiantes")
        ax_dist.set_title("Distribución de Estudiantes por Ciclo Académico y Rol (2026-II)")
        ax_dist.grid(axis="y", linestyle="--", alpha=0.5)
        plt.tight_layout()
        st.pyplot(fig_dist)
        plt.close()


# ==================================================================================================
# TAB 8: Repositorio de Reportes
# ==================================================================================================
with tab_reportes:
    st.subheader("📁 Repositorio Institucional de Reportes de Inferencia")
    st.markdown("""
    Historial y repositorio de las evaluaciones algorítmicas generadas para cada estudiante tutorado.
    Los reportes se persisten automáticamente en la carpeta `reportes/` tanto en formato legible Markdown (`.md`)
    como en formato de datos estructurados (`.json`) para fines de trazabilidad y sustentación de tesis.
    """)

    reportes_existentes = gr.listar_reportes()

    col_rep_m1, col_rep_m2, col_rep_m3 = st.columns(3)
    col_rep_m1.metric("Total Reportes Guardados", len(reportes_existentes))
    col_rep_m2.metric("Directorio Local", gr.DIRECTORIO_REPORTES)
    ultimo_rep = reportes_existentes[0]["fecha"] if reportes_existentes else "Ninguno"
    col_rep_m3.metric("Última Generación", ultimo_rep)

    st.markdown("---")

    if not reportes_existentes:
        st.info("El repositorio está listo y a la espera de evaluaciones. Para registrar el primer reporte, ve a la pestaña **🎯 1. Emparejamiento por Estudiante** y haz clic en el botón **💾 Generar y Guardar Reporte en Repositorio**.")
    else:
        # Tabla resumen del inventario de reportes
        df_reps = pd.DataFrame([
            {
                "Archivo Markdown": r["archivo_md"],
                "Fecha de Generación": r["fecha"],
                "Código Alumno": r["codigo_alumno"],
                "Estudiante Tutorado": r["alumno"],
                "Ciclo": r["ciclo"],
                "Curso Solicitado": r["curso"],
                "Top 1 Recomendado": r["top1_mentor"],
                "Puntaje Final": r["top1_score"],
            }
            for r in reportes_existentes
        ])
        st.dataframe(df_reps, use_container_width=True)

        st.markdown("#### 🔍 Visor e Inspector de Reporte Seleccionado")
        opciones_rep = {f"{r['fecha']} | {r['alumno']} ({r['curso']})": r for r in reportes_existentes}
        rep_seleccionado_str = st.selectbox("Seleccionar reporte para examinar:", list(opciones_rep.keys()))
        rep_elegido = opciones_rep[rep_seleccionado_str]

        subtab_vista_md, subtab_vista_json = st.tabs(["📄 Vista Documental (Markdown)", "🧩 Datos Estructurados (JSON)"])

        with subtab_vista_md:
            contenido_md = gr.leer_reporte(rep_elegido["ruta_completa_md"])
            st.markdown(contenido_md)
            st.download_button(
                label="📥 Descargar este Reporte en Markdown (.md)",
                data=contenido_md,
                file_name=rep_elegido["archivo_md"],
                mime="text/markdown",
                key=f"dl_md_{rep_elegido['archivo_md']}",
            )

        with subtab_vista_json:
            contenido_json = gr.leer_reporte(rep_elegido["ruta_completa_json"])
            try:
                st.json(json.loads(contenido_json))
            except Exception:
                st.code(contenido_json, language="json")
            st.download_button(
                label="📥 Descargar este Reporte en JSON (.json)",
                data=contenido_json,
                file_name=rep_elegido["archivo_json"],
                mime="application/json",
                key=f"dl_json_{rep_elegido['archivo_json']}",
            )
