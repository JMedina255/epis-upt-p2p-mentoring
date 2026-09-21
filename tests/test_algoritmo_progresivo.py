"""
Suite de Pruebas Progresivas del Motor de Recomendación P2P (EPIS-UPT 2026)
Valida las Fases 1 y 2 según las directivas establecidas en reglas_sistema.md.
"""

import math
import os
import sys
import sqlite3
import numpy as np

# Configuración de ruta para importar el módulo src
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from motor_recomendacion import (
    cargar_reglas_sistema,
    filtrar_mentores_sql,
    calcular_similitud_contenido,
    recomendar_mentores,
    resolver_ruta_bd,
)

DB_PATH = resolver_ruta_bd(os.path.join(BASE_DIR, "data", "epis_mentorias.db"))


# ==============================================================================
# FASE 1: FILTRADO DETERMINISTA (SQL HARD RULES)
# ==============================================================================

def test_fase1_sql_nota_minima_estricta():
    """Valida que NINGÚN mentor devuelto tenga nota menor a 14.0 en el curso."""
    curso = "INE-186"  # Matemática I
    dia = "Sabado"
    franja = "08:00 - 10:30"
    nota_min = 14.0

    candidatos = filtrar_mentores_sql(curso, dia, franja, nota_minima=nota_min, db_path=DB_PATH)
    
    for c in candidatos:
        nota = c[8]  # k.nota
        assert nota >= nota_min, f"Violación de regla dura: mentor {c[0]} tiene nota {nota} < {nota_min}"


def test_fase1_sql_cupos_disponibles():
    """Valida que NINGÚN mentor saturado (sesiones_activas >= max_cupos) sea seleccionado."""
    curso = "INE-186"
    dia = "Sabado"
    franja = "08:00 - 10:30"

    candidatos = filtrar_mentores_sql(curso, dia, franja, nota_minima=14.0, db_path=DB_PATH)

    for c in candidatos:
        sesiones_activas = c[5]
        max_cupos = c[6]
        assert sesiones_activas < max_cupos, (
            f"Violación de regla dura: mentor {c[0]} saturado ({sesiones_activas}/{max_cupos})"
        )


def test_fase1_sql_coincidencia_horaria():
    """Valida que todos los mentores preseleccionados tengan disponibilidad registrada en día y franja."""
    curso = "INE-186"
    dia = "Sabado"
    franja = "08:00 - 10:30"

    candidatos = filtrar_mentores_sql(curso, dia, franja, nota_minima=14.0, db_path=DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for c in candidatos:
        mentor_id = c[0]
        cursor.execute(
            "SELECT COUNT(*) FROM disponibilidad WHERE id_estudiante = ? AND dia = ? AND franja_horaria = ?",
            (mentor_id, dia, franja),
        )
        count = cursor.fetchone()[0]
        assert count > 0, f"Mentor {mentor_id} no tiene registrado el horario {dia} {franja}"
    conn.close()


def test_fase1_sql_cortocircuito_conjunto_vacio():
    """Valida el cortocircuito: si no hay candidatos aptos, retorna lista vacía sin error."""
    # Curso inexistente
    resultado_inexistente = filtrar_mentores_sql("CURSO-INEXISTENTE-999", "Sabado", "08:00 - 10:30", db_path=DB_PATH)
    assert resultado_inexistente == []

    # Horario con día no registrado
    resultado_dia_invalido = filtrar_mentores_sql("INE-186", "Domingo", "03:00 - 05:00", db_path=DB_PATH)
    assert resultado_dia_invalido == []

    # El pipeline completo también debe retornar lista vacía
    rec_vacio = recomendar_mentores("CURSO-INEXISTENTE-999", "tags_test", "Sabado", "08:00 - 10:30", db_path=DB_PATH)
    assert rec_vacio == []


# ==============================================================================
# FASE 2: ESPACIO VECTORIAL Y CONTENIDO (TF-IDF + COSENO)
# ==============================================================================

def test_fase2_tfidf_similitud_identica():
    """Asegura que vocablos idénticos produzcan similitud de coseno = 1.0."""
    tags_estudiante = "python postgresql react algoritmos"
    tags_mentores = ["python postgresql react algoritmos"]

    similitudes = calcular_similitud_contenido(tags_estudiante, tags_mentores)
    assert len(similitudes) == 1
    assert math.isclose(similitudes[0], 1.0, rel_tol=1e-5), f"Esperado 1.0, obtenido {similitudes[0]}"


def test_fase2_tfidf_vocabularios_disjuntos():
    """Asegura que vocabularios completamente disjuntos produzcan similitud de coseno = 0.0."""
    tags_estudiante = "calculo_diferencial algebra geometria"
    tags_mentores = ["ciberseguridad redes_tcp_ip linux"]

    similitudes = calcular_similitud_contenido(tags_estudiante, tags_mentores)
    assert len(similitudes) == 1
    assert math.isclose(similitudes[0], 0.0, abs_tol=1e-5), f"Esperado 0.0, obtenido {similitudes[0]}"


def test_fase2_tfidf_gradiente_afinidad():
    """Asegura que un mentor con mayor solapamiento léxico obtenga mayor similitud."""
    tags_estudiante = "python sql machine_learning"
    tags_mentores = [
        "python sql machine_learning deep_learning",  # Alta afinidad
        "python scrum git",                           # Media-baja afinidad
        "redaccion_academica filosofia etica",        # Nula afinidad
    ]

    similitudes = calcular_similitud_contenido(tags_estudiante, tags_mentores)
    assert similitudes[0] > similitudes[1] > similitudes[2]
    assert math.isclose(similitudes[2], 0.0, abs_tol=1e-5)


def test_fase2_tfidf_candidatos_vacios():
    """Valida que si no se pasan mentores, retorne un array vacío."""
    similitudes = calcular_similitud_contenido("python sql", [])
    assert isinstance(similitudes, np.ndarray)
    assert len(similitudes) == 0


# ==============================================================================
# EJECUCIÓN COMO SCRIPT DIRECTO
# ==============================================================================

if __name__ == "__main__":
    print("=================================================================")
    print(" INICIANDO PRUEBAS PROGRESIVAS (FASE 1 Y FASE 2) - EPIS-UPT 2026")
    print("=================================================================")

    # Fase 1
    print("\n[FASE 1] Ejecutando pruebas de filtrado determinista SQL...")
    test_fase1_sql_nota_minima_estricta()
    print("  -> test_fase1_sql_nota_minima_estricta: PASSED")
    test_fase1_sql_cupos_disponibles()
    print("  -> test_fase1_sql_cupos_disponibles: PASSED")
    test_fase1_sql_coincidencia_horaria()
    print("  -> test_fase1_sql_coincidencia_horaria: PASSED")
    test_fase1_sql_cortocircuito_conjunto_vacio()
    print("  -> test_fase1_sql_cortocircuito_conjunto_vacio: PASSED")

    # Fase 2
    print("\n[FASE 2] Ejecutando pruebas de espacio vectorial TF-IDF y Coseno...")
    test_fase2_tfidf_similitud_identica()
    print("  -> test_fase2_tfidf_similitud_identica: PASSED")
    test_fase2_tfidf_vocabularios_disjuntos()
    print("  -> test_fase2_tfidf_vocabularios_disjuntos: PASSED")
    test_fase2_tfidf_gradiente_afinidad()
    print("  -> test_fase2_tfidf_gradiente_afinidad: PASSED")
    test_fase2_tfidf_candidatos_vacios()
    print("  -> test_fase2_tfidf_candidatos_vacios: PASSED")

    print("\n=================================================================")
    print(" TODAS LAS PRUEBAS DE FASE 1 Y FASE 2 PASARON EXITOSAMENTE (8/8)")
    print("=================================================================\n")
