"""
Pruebas de Integración del Pipeline Completo de Recomendación (Paso 14).
Valida el flujo integral desacoplado:
  Solicitud del estudiante
    ↓
  Filtrado determinista relacional (SQL)
    ↓
  Vectorización y cálculo de afinidad (TF-IDF + Coseno)
    ↓
  Re-ranking sensible a la carga (Load-aware re-ranking)
    ↓
  Selección Top-K

Escenario de prueba controlado:
  4 candidatos iniciales:
    - 1 descartado por nota (calificación < 14.0)
    - 1 descartado por horario (franja/día no coincidente)
    - 2 evaluados en las fases vectoriales y re-ranking
    → Ranking final esperado con los 2 mejores ordenados por puntaje final.
"""

import sqlite3
import pytest

from src.motor_recomendacion import recomendar_mentores


@pytest.fixture
def pipeline_db(tmp_path):
    """Crea una base de datos temporal con 4 candidatos diseñados para probar

    el flujo completo de poda, vectorización y re-ranking.
    """
    db_file = tmp_path / "pipeline_test.db"
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_estudiante INTEGER,
            codigo_curso TEXT,
            nota REAL,
            condicion TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE disponibilidad (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_estudiante INTEGER,
            dia TEXT,
            franja_horaria TEXT
        )
    """)

    # 4 Candidatos iniciales con rol MENTOR
    # Mentor 1: Aprobado (17.0), Sabado 08:00-10:30, cupos libres (0/4), tags afines a cálculo
    cursor.execute(
        "INSERT INTO estudiantes VALUES (1, 'Carlos', 'Calculista', 8, 'calculo derivadas integrales algebra_lineal', 0, 4, 0, 'MENTOR')"
    )
    cursor.execute("INSERT INTO kardex_notas (id_estudiante, codigo_curso, nota, condicion) VALUES (1, 'INE-186', 17.0, 'APROBADO')")
    cursor.execute("INSERT INTO disponibilidad (id_estudiante, dia, franja_horaria) VALUES (1, 'Sabado', '08:00 - 10:30')")

    # Mentor 2: Aprobado (15.0), Sabado 08:00-10:30, cupos libres (0/3), nuevo mentor (es_nuevo=1), tags de álgebra
    cursor.execute(
        "INSERT INTO estudiantes VALUES (2, 'Beatriz', 'Algebrista', 7, 'algebra matrices geometria logica', 0, 3, 1, 'MENTOR')"
    )
    cursor.execute("INSERT INTO kardex_notas (id_estudiante, codigo_curso, nota, condicion) VALUES (2, 'INE-186', 15.0, 'APROBADO')")
    cursor.execute("INSERT INTO disponibilidad (id_estudiante, dia, franja_horaria) VALUES (2, 'Sabado', '08:00 - 10:30')")

    # Mentor 3: Aprobado (16.0), pero horario incompatible (Viernes por la tarde) -> DESCARTADO POR HORARIO
    cursor.execute(
        "INSERT INTO estudiantes VALUES (3, 'Daniel', 'HorarioDistinto', 9, 'calculo derivadas optimizacion', 0, 4, 0, 'MENTOR')"
    )
    cursor.execute("INSERT INTO kardex_notas (id_estudiante, codigo_curso, nota, condicion) VALUES (3, 'INE-186', 16.0, 'APROBADO')")
    cursor.execute("INSERT INTO disponibilidad (id_estudiante, dia, franja_horaria) VALUES (3, 'Viernes', '15:00 - 17:30')")

    # Mentor 4: Horario compatible (Sabado 08:00-10:30), pero desaprobado (nota 11.0) -> DESCARTADO POR NOTA
    cursor.execute(
        "INSERT INTO estudiantes VALUES (4, 'Elena', 'NotaBaja', 7, 'calculo algebra limites', 0, 3, 1, 'MENTOR')"
    )
    cursor.execute("INSERT INTO kardex_notas (id_estudiante, codigo_curso, nota, condicion) VALUES (4, 'INE-186', 11.0, 'DESAPROBADO')")
    cursor.execute("INSERT INTO disponibilidad (id_estudiante, dia, franja_horaria) VALUES (4, 'Sabado', '08:00 - 10:30')")

    conn.commit()
    conn.close()

    return str(db_file)


def test_pipeline_completo_cuatro_candidatos_dos_descartados_dos_evaluados(pipeline_db):
    """Valida el flujo end-to-end con 4 candidatos iniciales:

      - 1 descartado por nota (Elena, id=4, nota=11.0)
      - 1 descartado por horario (Daniel, id=3, viernes)
      - 2 evaluados en similitud léxica y re-ranking (Carlos id=1, Beatriz id=2)
      - El ranking final devuelve exactamente 2 candidatos con el orden y campos esperados.
    """
    solicitud_curso = "INE-186"
    solicitud_tags = "calculo derivadas"
    solicitud_dia = "Sabado"
    solicitud_franja = "08:00 - 10:30"
    top_k_solicitado = 3

    recomendaciones = recomendar_mentores(
        codigo_curso_solicitado=solicitud_curso,
        tags_estudiante=solicitud_tags,
        dia_preferido=solicitud_dia,
        franja_preferida=solicitud_franja,
        top_k=top_k_solicitado,
        db_path=pipeline_db,
    )

    # 1. Validación de tamaño: de los 4 candidatos iniciales, solo 2 son elegibles
    assert len(recomendaciones) == 2

    ids_recomendados = [m["id"] for m in recomendaciones]

    # 2. Validación de podas deterministas (Fase 1)
    assert 4 not in ids_recomendados, "El mentor 4 debió ser descartado por nota inferior a 14.0"
    assert 3 not in ids_recomendados, "El mentor 3 debió ser descartado por incompatibilidad de horario"

    # 3. Validación de ordenamiento y ranking (Fase 2, 4 y Top-K)
    # Mentor 1 coincide directamente con 'calculo' y 'derivadas' -> alta similitud
    # Mentor 2 tiene tags de álgebra -> menor o nula afinidad temática con la duda
    assert recomendaciones[0]["id"] == 1
    assert recomendaciones[1]["id"] == 2

    assert recomendaciones[0]["similitud_coseno"] > recomendaciones[1]["similitud_coseno"]
    assert recomendaciones[0]["puntaje_final"] > recomendaciones[1]["puntaje_final"]

    # 4. Integridad de los datos devueltos en la interfaz
    for m in recomendaciones:
        assert "mentor" in m
        assert "nota_en_curso" in m
        assert "similitud_coseno" in m
        assert "puntaje_final" in m
        assert "sesiones_activas" in m
        assert "max_cupos" in m
        assert "es_nuevo" in m


def test_pipeline_cortocircuito_sin_mentores(pipeline_db):
    """Valida el cortocircuito (short-circuit): si no hay candidatos aptos en la BD,

    el pipeline retorna inmediatamente una lista vacía sin fallar.
    """
    recomendaciones = recomendar_mentores(
        codigo_curso_solicitado="CURSO-NO-EXISTENTE",
        tags_estudiante="algoritmos",
        dia_preferido="Sabado",
        franja_preferida="08:00 - 10:30",
        db_path=pipeline_db,
    )
    assert recomendaciones == []


def test_pipeline_top_k_uno_restringe_salida(pipeline_db):
    """Valida que si se solicita top_k = 1, el pipeline retorne únicamente

    al candidato mejor posicionado.
    """
    recomendaciones = recomendar_mentores(
        codigo_curso_solicitado="INE-186",
        tags_estudiante="calculo derivadas",
        dia_preferido="Sabado",
        franja_preferida="08:00 - 10:30",
        top_k=1,
        db_path=pipeline_db,
    )
    assert len(recomendaciones) == 1
    assert recomendaciones[0]["id"] == 1


def test_pipeline_top_k_cero_lanza_error(pipeline_db):
    """Valida que pasar top_k = 0 a recomendar_mentores lance ValueError descriptivo."""
    with pytest.raises(ValueError, match="top_k debe ser un entero mayor o igual a 1"):
        recomendar_mentores(
            codigo_curso_solicitado="INE-186",
            tags_estudiante="calculo",
            dia_preferido="Sabado",
            franja_preferida="08:00 - 10:30",
            top_k=0,
            db_path=pipeline_db,
        )


def test_pipeline_top_k_negativo_lanza_error(pipeline_db):
    """Valida que pasar top_k < 0 (ej. -1) a recomendar_mentores lance ValueError en lugar de slicing anómalo."""
    with pytest.raises(ValueError, match="top_k debe ser un entero mayor o igual a 1"):
        recomendar_mentores(
            codigo_curso_solicitado="INE-186",
            tags_estudiante="calculo",
            dia_preferido="Sabado",
            franja_preferida="08:00 - 10:30",
            top_k=-1,
            db_path=pipeline_db,
        )

