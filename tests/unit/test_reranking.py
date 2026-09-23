"""
Pruebas Unitarias del Subsistema de Re-ranking Sensible a la Carga (Load-Aware Re-ranking)
Valida los términos de la función de puntuación:
  score(m) = alpha * similarity(u, m) - beta * (sesiones / max_cupos) + gamma * newcomer
"""

import math
import sqlite3
import numpy as np
import pytest

from src.motor_recomendacion import aplicar_reranking_equidad, filtrar_mentores_sql, resolver_ruta_bd


# ==============================================================================
# FIXTURES Y DATOS DE PRUEBA SINTÉTICOS
# ==============================================================================

def crear_mentor_sintetico(
    mentor_id: int,
    nombre: str,
    apellido: str,
    sesiones: int = 0,
    max_cupos: int = 4,
    es_nuevo: int = 0,
    ciclo: int = 8,
    nota_curso: float = 16.0,
    tags: str = "python algoritmos",
):
    """Genera una tupla con la estructura requerida por aplicar_reranking_equidad."""
    return (
        mentor_id,
        nombre,
        apellido,
        ciclo,
        tags,
        sesiones,
        max_cupos,
        es_nuevo,
        nota_curso,
    )


# ==============================================================================
# PASO 5: VALIDACIÓN DE PENALIZACIÓN POR SATURACIÓN (TÉRMINO BETA)
# ==============================================================================

def test_reranking_penaliza_saturacion():
    """Valida que un mentor con mayor similitud pero alta saturación

    pueda ser superado en el ranking por un mentor con similitud ligeramente
    menor pero con baja carga operativa (efecto directo de beta).
    """
    # Mentor A: alta similitud pero saturación al 100% (3/3)
    mentor_a = crear_mentor_sintetico(1, "Mentor", "Saturado", sesiones=3, max_cupos=3, es_nuevo=0)
    # Mentor B: similitud ligeramente inferior pero totalmente disponible (0/3)
    mentor_b = crear_mentor_sintetico(2, "Mentor", "Disponible", sesiones=0, max_cupos=3, es_nuevo=0)

    mentores = [mentor_a, mentor_b]
    similitudes = np.array([0.90, 0.80])  # Similitud pura: A (0.90) > B (0.80)

    # Parámetros: alpha=0.70, beta=0.20, gamma=0.10
    # Score A: 0.70 * 0.90 - 0.20 * (3/3) + 0 = 0.63 - 0.20 = 0.43
    # Score B: 0.70 * 0.80 - 0.20 * (0/3) + 0 = 0.56 - 0.00 = 0.56
    ranking = aplicar_reranking_equidad(
        mentores,
        similitudes,
        alpha=0.70,
        beta=0.20,
        gamma=0.10,
    )

    assert len(ranking) == 2
    # Mentor B debe encabezar el ranking a pesar de tener menor similitud léxica
    assert ranking[0]["id"] == 2
    assert ranking[0]["puntaje_final"] == 0.56
    assert ranking[1]["id"] == 1
    assert ranking[1]["puntaje_final"] == 0.43
    assert ranking[0]["puntaje_final"] > ranking[1]["puntaje_final"]


# ==============================================================================
# PASO 6: VALIDACIÓN DEL BONO DE OPORTUNIDAD PARA MENTOR NUEVO (TÉRMINO GAMMA)
# ==============================================================================

def test_reranking_bonus_mentor_nuevo():
    """Valida que el bono de mentor nuevo (gamma) permita a un mentor novato

    competitivo adelantar a un mentor con mayor similitud pero sin bono.
    """
    # Mentor A: similitud 0.80, no es nuevo (es_nuevo=0), sin carga
    mentor_a = crear_mentor_sintetico(1, "Mentor", "Experimentado", sesiones=0, max_cupos=4, es_nuevo=0)
    # Mentor B: similitud 0.75, es nuevo (es_nuevo=1), sin carga
    mentor_b = crear_mentor_sintetico(2, "Mentor", "Nuevo", sesiones=0, max_cupos=4, es_nuevo=1)

    mentores = [mentor_a, mentor_b]
    similitudes = np.array([0.80, 0.75])

    # Score A: 0.70 * 0.80 - 0.20 * 0.0 + 0.00 = 0.560
    # Score B: 0.70 * 0.75 - 0.20 * 0.0 + 0.10 = 0.525 + 0.10 = 0.625
    ranking = aplicar_reranking_equidad(
        mentores,
        similitudes,
        alpha=0.70,
        beta=0.20,
        gamma=0.10,
    )

    assert len(ranking) == 2
    assert ranking[0]["id"] == 2  # Mentor B queda en primer lugar gracias al bono
    assert ranking[0]["es_nuevo"] is True
    assert ranking[0]["puntaje_final"] == 0.625
    assert ranking[1]["id"] == 1
    assert ranking[1]["es_nuevo"] is False
    assert ranking[1]["puntaje_final"] == 0.56


# ==============================================================================
# PASO 7: VALIDACIÓN DE GAMMA = 0 (AISLAMIENTO PARA ESTUDIO DE ABLACIÓN B1)
# ==============================================================================

def test_reranking_gamma_cero_elimina_bono_nuevo():
    """Valida que configurar gamma = 0 elimine totalmente el incentivo a nuevos

    mentores, preservando el orden basado únicamente en similitud y carga (Baseline B1).
    """
    mentor_a = crear_mentor_sintetico(1, "Mentor", "Experimentado", sesiones=0, max_cupos=4, es_nuevo=0)
    mentor_b = crear_mentor_sintetico(2, "Mentor", "Nuevo", sesiones=0, max_cupos=4, es_nuevo=1)

    mentores = [mentor_a, mentor_b]
    similitudes = np.array([0.80, 0.75])

    # Con gamma = 0.0:
    # Score A: 0.70 * 0.80 = 0.560
    # Score B: 0.70 * 0.75 = 0.525
    ranking = aplicar_reranking_equidad(
        mentores,
        similitudes,
        alpha=0.70,
        beta=0.20,
        gamma=0.0,
    )

    assert len(ranking) == 2
    # Al ser gamma=0, Mentor A debe mantenerse primero por su superioridad en similitud
    assert ranking[0]["id"] == 1
    assert ranking[0]["puntaje_final"] == 0.56
    assert ranking[1]["id"] == 2
    assert ranking[1]["puntaje_final"] == 0.525
    assert ranking[0]["puntaje_final"] > ranking[1]["puntaje_final"]


# ==============================================================================
# PASO 8: ROBUSTEZ Y CASOS BORDE: MAX_CUPOS = 0 (DOS NIVELES)
# ==============================================================================

def test_reranking_max_cupos_cero_evita_zero_division():
    """Valida que si un candidato llega con max_cupos = 0 al re-ranking,

    el algoritmo no lance ZeroDivisionError y le asigne saturación máxima (1.0).
    """
    mentor_anomalo = crear_mentor_sintetico(99, "Mentor", "SinCupos", sesiones=0, max_cupos=0, es_nuevo=0)
    similitudes = np.array([0.80])

    # No debe lanzar ZeroDivisionError
    ranking = aplicar_reranking_equidad(
        [mentor_anomalo],
        similitudes,
        alpha=0.70,
        beta=0.20,
        gamma=0.10,
    )

    # Con max_cupos=0, la saturación se fija en 1.0:
    # Score esperado: 0.70 * 0.80 - 0.20 * 1.0 + 0.0 = 0.56 - 0.20 = 0.36
    assert len(ranking) == 1
    assert ranking[0]["id"] == 99
    assert ranking[0]["max_cupos"] == 0
    assert math.isclose(ranking[0]["puntaje_final"], 0.36, abs_tol=1e-4)


def test_sql_filtrado_ignora_mentor_con_max_cupos_cero(tmp_path):
    """Valida que la consulta SQL de filtrado determinista descarte

    a cualquier mentor cuyo max_cupos_mentor sea 0 (regla dura relacional).
    """
    # Creamos una base de datos SQLite temporal aislada para probar la regla SQL
    db_file = tmp_path / "test_cupos_cero.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE estudiantes (
            id INTEGER PRIMARY KEY,
            nombres TEXT,
            apellidos TEXT,
            ciclo_actual INTEGER,
            tags_interes TEXT,
            sesiones_activas INTEGER,
            max_cupos_mentor INTEGER,
            es_nuevo_mentor INTEGER,
            rol TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE kardex_notas (
            id_estudiante INTEGER,
            codigo_curso TEXT,
            nota REAL,
            condicion TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE disponibilidad (
            id_estudiante INTEGER,
            dia TEXT,
            franja_horaria TEXT
        )
    """)

    # Mentor 1: cumple nota y horario, pero max_cupos_mentor = 0
    cursor.execute(
        "INSERT INTO estudiantes VALUES (1, 'Ana', 'Rios', 8, 'python', 0, 0, 0, 'MENTOR')"
    )
    cursor.execute(
        "INSERT INTO kardex_notas VALUES (1, 'INE-186', 17.0, 'APROBADO')"
    )
    cursor.execute(
        "INSERT INTO disponibilidad VALUES (1, 'Sabado', '08:00 - 10:30')"
    )

    # Mentor 2: cumple todo y tiene cupos disponibles (0 < 3)
    cursor.execute(
        "INSERT INTO estudiantes VALUES (2, 'Luis', 'Gomez', 9, 'python', 0, 3, 0, 'MENTOR')"
    )
    cursor.execute(
        "INSERT INTO kardex_notas VALUES (2, 'INE-186', 16.0, 'APROBADO')"
    )
    cursor.execute(
        "INSERT INTO disponibilidad VALUES (2, 'Sabado', '08:00 - 10:30')"
    )

    conn.commit()
    conn.close()

    candidatos = filtrar_mentores_sql("INE-186", "Sabado", "08:00 - 10:30", nota_minima=14.0, db_path=str(db_file))
    
    # Solo el Mentor 2 debe superar el filtro SQL; el Mentor 1 debe ser descartado
    ids_candidatos = [c[0] for c in candidatos]
    assert 1 not in ids_candidatos, "El mentor con max_cupos_mentor = 0 no debió ser preseleccionado por SQL"
    assert 2 in ids_candidatos


# ==============================================================================
# PASO 9: VALIDACIÓN DEL ORDEN DESCENDENTE DEL RANKING FINAL
# ==============================================================================

def test_ranking_ordenado_descendentemente():
    """Garantiza que la lista devuelta por el re-ranking esté estrictamente

    ordenada de mayor a menor puntaje final (scores == sorted(scores, reverse=True)).
    """
    mentores = [
        crear_mentor_sintetico(1, "A", "Uno", sesiones=2, max_cupos=4, es_nuevo=0),
        crear_mentor_sintetico(2, "B", "Dos", sesiones=0, max_cupos=3, es_nuevo=1),
        crear_mentor_sintetico(3, "C", "Tres", sesiones=3, max_cupos=3, es_nuevo=0),
        crear_mentor_sintetico(4, "D", "Cuatro", sesiones=1, max_cupos=5, es_nuevo=0),
        crear_mentor_sintetico(5, "E", "Cinco", sesiones=0, max_cupos=2, es_nuevo=0),
    ]
    similitudes = np.array([0.45, 0.72, 0.88, 0.60, 0.95])

    ranking = aplicar_reranking_equidad(
        mentores,
        similitudes,
        alpha=0.70,
        beta=0.20,
        gamma=0.10,
    )

    assert len(ranking) == 5
    scores = [r["puntaje_final"] for r in ranking]

    # Validación de la propiedad de ordenamiento monótono no decreciente
    assert scores == sorted(scores, reverse=True), f"El ranking no está ordenado descendentemente: {scores}"
    for i in range(len(scores) - 1):
        assert scores[i] >= scores[i + 1]


# ==============================================================================
# PASO 10: VALIDACIÓN DE SELECCIÓN Y DIMENSIONAMIENTO TOP-K
# ==============================================================================

def test_top_k_diez_candidatos_retorna_exactamente_tres():
    """Valida que ante 10 candidatos elegibles y top_k = 3,

    se seleccionen exactamente los 3 mejores mentores.
    """
    # Creamos 10 candidatos con puntajes crecientes
    mentores = [
        crear_mentor_sintetico(i, f"Mentor_{i}", "Test", sesiones=0, max_cupos=4, es_nuevo=0)
        for i in range(1, 11)
    ]
    similitudes = np.linspace(0.10, 0.95, 10)  # Similitudes de 0.10 a 0.95

    ranking_completo = aplicar_reranking_equidad(
        mentores,
        similitudes,
        alpha=0.70,
        beta=0.20,
        gamma=0.10,
    )
    assert len(ranking_completo) == 10

    # Selección Top-K con K=3
    top_k = 3
    seleccion = ranking_completo[:top_k]

    assert len(seleccion) == 3
    # Deben ser los 3 con mayor puntaje final
    assert seleccion[0]["id"] == 10  # mayor similitud (0.95)
    assert seleccion[1]["id"] == 9   # segunda mayor
    assert seleccion[2]["id"] == 8   # tercera mayor
    assert seleccion[0]["puntaje_final"] >= seleccion[1]["puntaje_final"] >= seleccion[2]["puntaje_final"]


def test_top_k_dos_candidatos_retorna_exactamente_dos():
    """Valida que ante solo 2 candidatos elegibles y top_k = 3,

    se devuelvan exactamente 2 candidatos sin errores de indexación o desbordamiento.
    """
    mentores = [
        crear_mentor_sintetico(1, "Uno", "Test", sesiones=0, max_cupos=4, es_nuevo=0),
        crear_mentor_sintetico(2, "Dos", "Test", sesiones=0, max_cupos=4, es_nuevo=0),
    ]
    similitudes = np.array([0.60, 0.85])

    ranking_completo = aplicar_reranking_equidad(
        mentores,
        similitudes,
        alpha=0.70,
        beta=0.20,
        gamma=0.10,
    )
    assert len(ranking_completo) == 2

    # Solicitamos top_k = 3, pero solo hay 2 candidatos
    top_k = 3
    seleccion = ranking_completo[:top_k]

    assert len(seleccion) == 2
    assert seleccion[0]["id"] == 2
    assert seleccion[1]["id"] == 1


def test_top_k_uno_retorna_exactamente_un_candidato():
    """Valida que cuando top_k = 1, se devuelva exactamente el mejor candidato único."""
    mentores = [
        crear_mentor_sintetico(1, "Bajo", "Test", sesiones=2, max_cupos=3, es_nuevo=0),
        crear_mentor_sintetico(2, "Lider", "Test", sesiones=0, max_cupos=4, es_nuevo=1),
        crear_mentor_sintetico(3, "Medio", "Test", sesiones=1, max_cupos=4, es_nuevo=0),
    ]
    similitudes = np.array([0.40, 0.80, 0.60])

    ranking_completo = aplicar_reranking_equidad(
        mentores,
        similitudes,
        alpha=0.70,
        beta=0.20,
        gamma=0.10,
    )

    # Selección Top-1
    top_k = 1
    seleccion = ranking_completo[:top_k]

    assert len(seleccion) == 1
    assert seleccion[0]["id"] == 2
    assert seleccion[0]["puntaje_final"] == ranking_completo[0]["puntaje_final"]

