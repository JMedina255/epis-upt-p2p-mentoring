"""
Pruebas unitarias para el gestor de reportes (src/gestor_reportes.py).
Valida la generación de Markdown, persistencia, listado y lectura resiliente.
"""

import json
import os
import pytest

from src import gestor_reportes
from src.gestor_reportes import (
    asegurar_directorio_reportes,
    generar_markdown_reporte,
    guardar_reporte,
    listar_reportes,
    leer_reporte,
)


@pytest.fixture
def reporte_datos_completos():
    """Fixture con una estructura completa y controlada de reporte de recomendación."""
    return {
        "id_reporte": "REP-2026-001",
        "fecha_generacion": "2026-09-23 12:00:00",
        "tutorado": {
            "nombre_completo": "Juan Perez",
            "ciclo": 2,
            "codigo": "2024-001",
            "correo": "jperez@upt.pe",
            "tags": "calculo, derivadas, limites",
            "disponibilidad": ["Lunes 08:00 - 10:30"],
        },
        "solicitud": {
            "codigo_curso": "INE-186",
            "nombre_curso": "Cálculo I",
            "nota_tutorado": 11.5,
            "condicion_tutorado": "DESAPROBADO",
            "dia": "Lunes",
            "franja_horaria": "08:00 - 10:30",
            "tags_consulta": "limites, derivadas",
        },
        "configuracion_algoritmo": {
            "pesos": {"alpha": 0.70, "beta": 0.20, "gamma": 0.10},
            "nota_minima_mentor": 14.0,
            "top_k": 3,
        },
        "fase1_filtro_sql": {
            "total_candidatos_aptos": 1,
            "mentores_aptos": [
                {
                    "id": 1,
                    "mentor": "Carlos Mentor",
                    "ciclo": 8,
                    "nota_en_curso": 17.0,
                    "sesiones": 1,
                    "max_cupos": 3,
                    "es_nuevo": 1,
                }
            ],
        },
        "fase2_espacio_vectorial": {
            "mediciones_angulares": [
                {
                    "mentor": "Carlos Mentor",
                    "similitud_coseno": 0.8500,
                    "angulo_grados": 31.79,
                    "interpretacion": "Afinidad Alta",
                    "tags_coincidentes": "calculo, derivadas",
                }
            ]
        },
        "fase4_reranking_equidad": {
            "desglose_calibracion": [
                {
                    "rank_final": 1,
                    "rank_coseno": 1,
                    "cambio_pos": "=",
                    "mentor": "Carlos Mentor",
                    "similitud_coseno": 0.8500,
                    "term_sim": 0.5950,
                    "term_sat": 0.0667,
                    "term_bono": 0.1000,
                    "puntaje_final": 0.6283,
                }
            ]
        },
        "top_k_recomendados": [
            {
                "mentor": "Carlos Mentor",
                "ciclo": 8,
                "puntaje_final": 0.6283,
                "nota_en_curso": 17.0,
                "similitud_coseno": 0.8500,
                "angulo_grados": 31.79,
                "sesiones_activas": 1,
                "max_cupos": 3,
                "tags": "calculo, derivadas, algebra",
            }
        ],
        "telemetria": {"tiempo_inferencia_ms": 12.50},
    }


def test_generar_markdown_reporte_completo(reporte_datos_completos):
    """Valida la generación de Markdown con todas las secciones completas."""
    markdown = generar_markdown_reporte(reporte_datos_completos)

    assert "Reporte Experimental" in markdown
    assert "INE-186" in markdown
    assert "Load-Aware Re-ranking" in markdown
    assert "Carlos Mentor" in markdown
    assert "Top-" in markdown
    assert "Sí (+Bono)" in markdown
    assert "12.50 ms" in markdown
    assert "31.79" in markdown


def test_generar_markdown_reporte_minimo_sin_candidatos():
    """Valida que un reporte con listas vacías en todas las fases no lance excepciones y omita tablas."""
    datos_minimos = {
        "id_reporte": "REP-MIN-001",
        "fecha_generacion": "2026-09-23 12:00:00",
        "tutorado": {"nombre_completo": "Ana Alumna"},
        "solicitud": {"codigo_curso": "SI-100"},
        "configuracion_algoritmo": {"pesos": {}},
        "fase1_filtro_sql": {"total_candidatos_aptos": 0, "mentores_aptos": []},
        "fase2_espacio_vectorial": {"mediciones_angulares": []},
        "fase4_reranking_equidad": {"desglose_calibracion": []},
        "top_k_recomendados": [],
        "telemetria": {},
    }

    markdown = generar_markdown_reporte(datos_minimos)

    assert "Reporte Experimental" in markdown
    assert "SI-100" in markdown
    assert "Ana Alumna" in markdown
    # No deben renderizarse encabezados de tablas vacías
    assert "| Saturación (%) |" not in markdown
    assert "| Interpretación Geométrica |" not in markdown
    assert "Candidato #1:" not in markdown


def test_generar_markdown_reporte_mentor_con_max_cupos_cero():
    """Valida el cálculo de saturación porcentual cuando max_cupos es 0 (evitando ZeroDivisionError)."""
    datos = {
        "id_reporte": "REP-CUPOS-0",
        "fase1_filtro_sql": {
            "total_candidatos_aptos": 1,
            "mentores_aptos": [
                {
                    "id": 2,
                    "mentor": "Mentor Sin Cupos",
                    "ciclo": 7,
                    "nota_en_curso": 15.0,
                    "sesiones": 0,
                    "max_cupos": 0,
                    "es_nuevo": 0,
                }
            ],
        },
    }
    markdown = generar_markdown_reporte(datos)
    assert "100.0%" in markdown
    assert "No" in markdown  # es_nuevo = 0 produce "No"


def test_guardar_reporte_crea_json_y_markdown(tmp_path, monkeypatch, reporte_datos_completos):
    """Valida que guardar_reporte persista los archivos JSON y Markdown en disco."""
    monkeypatch.setattr(gestor_reportes, "obtener_directorio_reportes", lambda: str(tmp_path))

    ruta_json, ruta_md = guardar_reporte(reporte_datos_completos)

    assert os.path.exists(ruta_json)
    assert os.path.exists(ruta_md)
    assert ruta_json.endswith(".json")
    assert ruta_md.endswith(".md")

    # Validar persistencia estructurada del JSON
    with open(ruta_json, "r", encoding="utf-8") as f:
        guardado = json.load(f)
    assert guardado["id_reporte"] == reporte_datos_completos["id_reporte"]
    assert guardado["solicitud"]["codigo_curso"] == "INE-186"

    # Validar que el archivo Markdown contiene el reporte generado
    contenido_md = leer_reporte(ruta_md)
    assert "Reporte Experimental" in contenido_md
    assert "Carlos Mentor" in contenido_md


def test_listar_reportes_orden_descendente_e_ignora_corruptos(tmp_path, monkeypatch):
    """Valida que listar_reportes ordene descendentemente por fecha e ignore JSONs corruptos."""
    monkeypatch.setattr(gestor_reportes, "obtener_directorio_reportes", lambda: str(tmp_path))

    # 1. Reporte antiguo válido
    rep_antiguo = {
        "id_reporte": "REP-001",
        "fecha_generacion": "2026-09-20 10:00:00",
        "tutorado": {"codigo": "2024-001", "nombre_completo": "Alumno Uno", "ciclo": 2},
        "solicitud": {"codigo_curso": "INE-186", "nombre_curso": "Cálculo I"},
        "top_k_recomendados": [{"mentor": "Mentor A", "puntaje_final": 0.85}],
    }
    (tmp_path / "reporte_001.json").write_text(json.dumps(rep_antiguo), encoding="utf-8")

    # 2. Reporte reciente válido sin candidatos recomendados
    rep_reciente = {
        "id_reporte": "REP-002",
        "fecha_generacion": "2026-09-23 15:00:00",
        "tutorado": {"codigo": "2024-002", "nombre_completo": "Alumno Dos", "ciclo": 3},
        "solicitud": {"codigo_curso": "SI-100", "nombre_curso": "Algoritmos"},
        "top_k_recomendados": [],
    }
    (tmp_path / "reporte_002.json").write_text(json.dumps(rep_reciente), encoding="utf-8")

    # 3. Archivo JSON corrupto que debe ser ignorado sin romper el listado
    (tmp_path / "reporte_corrupto.json").write_text("{ ESTO NO ES UN JSON VALIDO ...", encoding="utf-8")

    # 4. Archivo que no es JSON (ej. .txt o .md) que no debe procesarse
    (tmp_path / "reporte_001.md").write_text("# Contenido markdown", encoding="utf-8")

    lista = listar_reportes()

    assert len(lista) == 2
    # El más reciente debe aparecer primero
    assert lista[0]["id_reporte"] == "REP-002"
    assert lista[0]["fecha"] == "2026-09-23 15:00:00"
    assert lista[0]["top1_mentor"] == "Sin candidatos"
    assert lista[0]["top1_score"] == 0.0

    # El más antiguo debe aparecer segundo
    assert lista[1]["id_reporte"] == "REP-001"
    assert lista[1]["fecha"] == "2026-09-20 10:00:00"
    assert lista[1]["top1_mentor"] == "Mentor A"
    assert lista[1]["top1_score"] == 0.85


def test_leer_reporte_inexistente_retorna_vacio(tmp_path):
    """Valida que leer_reporte sobre un archivo inexistente retorne una cadena vacía de forma segura."""
    ruta_inexistente = tmp_path / "archivo_que_no_existe.md"
    assert leer_reporte(str(ruta_inexistente)) == ""


def test_asegurar_directorio_reportes_crea_directorio(tmp_path, monkeypatch):
    """Valida que asegurar_directorio_reportes cree la carpeta si no existía previamente."""
    dir_objetivo = tmp_path / "subcarpeta_reportes"
    assert not dir_objetivo.exists()

    monkeypatch.setattr(gestor_reportes, "obtener_directorio_reportes", lambda: str(dir_objetivo))

    resultado = asegurar_directorio_reportes()
    assert resultado == str(dir_objetivo)
    assert dir_objetivo.is_dir()


def test_obtener_directorio_reportes_resuelve_ruta_existente():
    """Valida que obtener_directorio_reportes resuelva la ruta canónica del proyecto."""
    ruta = gestor_reportes.obtener_directorio_reportes()
    assert os.path.isabs(ruta)
    assert os.path.exists(ruta)
    assert os.path.basename(ruta) == "reportes"


def test_directorio_reportes_constante_definida():
    """Valida que la constante DIRECTORIO_REPORTES requerida por app_visualizador esté disponible."""
    assert hasattr(gestor_reportes, "DIRECTORIO_REPORTES")
    assert gestor_reportes.DIRECTORIO_REPORTES == "reportes"


def test_generar_markdown_soporta_esquema_visualizador_streamlit():
    """Valida que generar_markdown_reporte maneje de forma resiliente tanto el esquema canónico

    como diccionarios con nombres de columnas de visualización provenientes de DataFrames de Streamlit.
    """
    datos_estilo_streamlit = {
        "id_reporte": "REP-STREAMLIT-001",
        "fecha_generacion": "2026-09-23 15:30:00",
        "tutorado": {"nombre_completo": "Estudiante Streamlit"},
        "solicitud": {"codigo_curso": "INE-186", "nombre_curso": "Cálculo I"},
        "configuracion_algoritmo": {"pesos": {"alpha": 0.70, "beta": 0.20, "gamma": 0.10}},
        "fase1_filtro_sql": {"total_candidatos_aptos": 1, "mentores_aptos": []},
        "fase2_espacio_vectorial": {
            "mediciones_angulares": [
                {
                    "Mentor": "Prof. Mentor",
                    "Similitud Coseno (cos θ)": 0.9123,
                    "Ángulo θ (Grados)": "24.2°",
                    "Interpretación Geométrica": "🟢 Ángulo Estrecho",
                    "Tags Coincidentes": "calculo, derivadas",
                }
            ]
        },
        "fase4_reranking_equidad": {
            "desglose_calibracion": [
                {
                    "Rank Final": 1,
                    "Rank Coseno Puro": 1,
                    "Cambio de Posición": "⏺️ 0",
                    "Mentor": "Prof. Mentor",
                    "Sim Coseno (TF-IDF)": 0.9123,
                    "Afinidad (0.7·Sim)": 0.6386,
                    "Saturación (%)": "33%",
                    "Penalización (-0.2·Sat)": -0.0667,
                    "Bono Novedad (+0.1·Bono)": 0.0,
                    "Puntaje Final": 0.5719,
                }
            ]
        },
        "top_k_recomendados": [
            {
                "mentor": "Prof. Mentor",
                "ciclo": 9,
                "puntaje_final": 0.5719,
                "nota_en_curso": 18.0,
                "similitud_coseno": 0.9123,
                "angulo_grados": "24.2°",
                "sesiones_activas": 1,
                "max_cupos": 3,
                "tags": "calculo",
            }
        ],
        "telemetria": {"tiempo_inferencia_ms": 15.2},
    }

    markdown = generar_markdown_reporte(datos_estilo_streamlit)

    assert "Reporte Experimental" in markdown
    assert "Prof. Mentor" in markdown
    assert "0.9123" in markdown
    assert "0.5719" in markdown
    assert "🟢 Ángulo Estrecho" in markdown

