"""
Fixtures globales de Pytest para la suite de pruebas del motor de recomendación P2P.
Proporciona entornos SQLite aislados y configuraciones reproducibles sin depender de data/epis_mentorias.db.
"""

import sqlite3
import pytest


@pytest.fixture
def test_db(tmp_path):
    """Crea una base de datos SQLite mínima en memoria/archivo temporal (Paso 13).

    Estructura controlada:
      - 1 curso oficial: INE-186 (Matemática I)
      - 1 estudiante tutorado (Ciclo I)
      - 4 mentores con perfiles diferenciados:
          * Mentor 1: Excelente nota (18.0), compatible, cupos libres (0/4), con experiencia.
          * Mentor 2: Buena nota (15.0), compatible, nuevo mentor (es_nuevo=1), cupos libres (0/3).
          * Mentor 3: Nota suficiente (14.0), compatible, saturado (3/3 cupos).
          * Mentor 4: Desaprobado en el curso (11.0), compatible (debe ser podado por regla dura).
      - Disponibilidad horaria en 'Sabado', '08:00 - 10:30' para evaluar cruces exactos.
    """
    db_path = tmp_path / "test_epis_minima.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Esquema relacional esencial
    cursor.execute("""
        CREATE TABLE cursos (
            codigo TEXT PRIMARY KEY,
            nombre TEXT,
            ciclo INTEGER,
            area TEXT
        )
    """)

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

    # Inserción de catálogo de cursos
    cursor.execute("INSERT INTO cursos VALUES ('INE-186', 'MATEMÁTICA I', 1, 'CIENCIAS')")

    # Inserción de perfiles de prueba
    # Tutorado (id=100)
    cursor.execute("""
        INSERT INTO estudiantes VALUES 
        (100, 'Tutorado', 'Prueba', 1, 'algebra geometria limites calculo', 0, 0, 0, 'TUTORADO')
    """)

    # Mentores (ids 1..4)
    # Mentor 1: Alto rendimiento, experimentado, cupos libres (0/4)
    cursor.execute("""
        INSERT INTO estudiantes VALUES 
        (1, 'Carlos', 'Avanzado', 8, 'calculo derivadas integrales algebra_lineal', 0, 4, 0, 'MENTOR')
    """)
    # Mentor 2: Buen rendimiento, mentor nuevo (es_nuevo=1), cupos libres (0/3)
    cursor.execute("""
        INSERT INTO estudiantes VALUES 
        (2, 'Beatriz', 'Nueva', 7, 'algebra limites geometria funciones', 0, 3, 1, 'MENTOR')
    """)
    # Mentor 3: Rendimiento regular, saturado (3/3 cupos)
    cursor.execute("""
        INSERT INTO estudiantes VALUES 
        (3, 'David', 'Saturado', 9, 'calculo algebra geometria', 3, 3, 0, 'MENTOR')
    """)
    # Mentor 4: Desaprobado en INE-186 (no apto por regla dura)
    cursor.execute("""
        INSERT INTO estudiantes VALUES 
        (4, 'Elena', 'NoApta', 7, 'algebra matematica basica', 0, 3, 1, 'MENTOR')
    """)

    # Historial académico (Kardex)
    cursor.execute("INSERT INTO kardex_notas (id_estudiante, codigo_curso, nota, condicion) VALUES (1, 'INE-186', 18.0, 'APROBADO')")
    cursor.execute("INSERT INTO kardex_notas (id_estudiante, codigo_curso, nota, condicion) VALUES (2, 'INE-186', 15.0, 'APROBADO')")
    cursor.execute("INSERT INTO kardex_notas (id_estudiante, codigo_curso, nota, condicion) VALUES (3, 'INE-186', 14.0, 'APROBADO')")
    cursor.execute("INSERT INTO kardex_notas (id_estudiante, codigo_curso, nota, condicion) VALUES (4, 'INE-186', 11.0, 'DESAPROBADO')")

    # Disponibilidad horaria común
    dia_test = "Sabado"
    franja_test = "08:00 - 10:30"
    for est_id in [100, 1, 2, 3, 4]:
        cursor.execute(
            "INSERT INTO disponibilidad (id_estudiante, dia, franja_horaria) VALUES (?, ?, ?)",
            (est_id, dia_test, franja_test)
        )

    conn.commit()
    conn.close()

    return str(db_path)
