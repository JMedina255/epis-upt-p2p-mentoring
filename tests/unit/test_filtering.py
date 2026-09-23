"""
Pruebas Unitarias del Filtrado Determinista Relacional SQL (Fase 1).
Utiliza la fixture aislada 'test_db' (Paso 13) para garantizar pruebas reproducibles,
herméticas y sin acoplamiento a data/epis_mentorias.db.
"""

import os
import pytest
from src.motor_recomendacion import filtrar_mentores_sql, resolver_ruta_bd


def test_filtrado_sql_excluye_nota_menor_al_umbral(test_db):
    """Valida que un mentor con nota inferior al umbral (ej. Elena con 11.0)

    sea estrictamente excluido de los candidatos elegibles.
    """
    candidatos = filtrar_mentores_sql(
        codigo_curso="INE-186",
        dia="Sabado",
        franja_horaria="08:00 - 10:30",
        nota_minima=14.0,
        db_path=test_db,
    )
    ids_encontrados = [c[0] for c in candidatos]

    # Mentor 4 (Elena, nota 11.0) debe quedar fuera
    assert 4 not in ids_encontrados
    for c in candidatos:
        assert c[8] >= 14.0, f"Mentor {c[0]} tiene nota {c[8]} menor a 14.0"


def test_filtrado_sql_excluye_mentor_saturado(test_db):
    """Valida que mentores con cupos agotados (ej. David con 3/3 sesiones)

    no sean preseleccionados aunque cumplan con la nota y el horario.
    """
    candidatos = filtrar_mentores_sql(
        codigo_curso="INE-186",
        dia="Sabado",
        franja_horaria="08:00 - 10:30",
        nota_minima=14.0,
        db_path=test_db,
    )
    ids_encontrados = [c[0] for c in candidatos]

    # Mentor 3 (David, 3 sesiones activas de 3 cupos máximos) debe quedar excluido
    assert 3 not in ids_encontrados


def test_filtrado_sql_candidatos_aptos(test_db):
    """Valida que los mentores que cumplen todas las reglas duras (nota >= 14,

    horario coincidente y cupos libres) sean devueltos exitosamente.
    """
    candidatos = filtrar_mentores_sql(
        codigo_curso="INE-186",
        dia="Sabado",
        franja_horaria="08:00 - 10:30",
        nota_minima=14.0,
        db_path=test_db,
    )
    ids_encontrados = [c[0] for c in candidatos]

    # Deben clasificar Mentor 1 (Carlos, 18.0, 0/4) y Mentor 2 (Beatriz, 15.0, 0/3)
    assert set(ids_encontrados) == {1, 2}


def test_filtrado_sql_cortocircuito_curso_inexistente(test_db):
    """Valida que si se consulta un curso no registrado, retorne lista vacía sin errores."""
    candidatos = filtrar_mentores_sql(
        codigo_curso="CURSO-INEXISTENTE-999",
        dia="Sabado",
        franja_horaria="08:00 - 10:30",
        nota_minima=14.0,
        db_path=test_db,
    )
    assert candidatos == []


def test_filtrado_sql_cortocircuito_horario_incompatible(test_db):
    """Valida que si no hay mentores disponibles en la franja requerida, retorne lista vacía."""
    candidatos = filtrar_mentores_sql(
        codigo_curso="INE-186",
        dia="Domingo",
        franja_horaria="03:00 - 05:00",
        nota_minima=14.0,
        db_path=test_db,
    )
    assert candidatos == []


def test_filtrado_sql_coincidencia_horaria(test_db):
    """Valida que todos los mentores devueltos tengan disponibilidad efectiva en día y franja."""
    import sqlite3
    dia = "Sabado"
    franja = "08:00 - 10:30"
    candidatos = filtrar_mentores_sql(
        codigo_curso="INE-186",
        dia=dia,
        franja_horaria=franja,
        nota_minima=14.0,
        db_path=test_db,
    )
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    for c in candidatos:
        mentor_id = c[0]
        cursor.execute(
            "SELECT COUNT(*) FROM disponibilidad WHERE id_estudiante = ? AND dia = ? AND franja_horaria = ?",
            (mentor_id, dia, franja),
        )
        count = cursor.fetchone()[0]
        assert count > 0, f"Mentor {mentor_id} no registra disponibilidad en {dia} {franja}"
    conn.close()


def test_filtrado_sql_max_cupos_cero(tmp_path):
    """Valida que un mentor con max_cupos_mentor = 0 sea estrictamente ignorado por SQL."""
    import sqlite3
    db_file = tmp_path / "sql_cupos_cero.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE estudiantes (
            id INTEGER PRIMARY KEY, nombres TEXT, apellidos TEXT, ciclo_actual INTEGER,
            tags_interes TEXT, sesiones_activas INTEGER, max_cupos_mentor INTEGER,
            es_nuevo_mentor INTEGER, rol TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE kardex_notas (
            id_estudiante INTEGER, codigo_curso TEXT, nota REAL, condicion TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE disponibilidad (
            id_estudiante INTEGER, dia TEXT, franja_horaria TEXT
        )
    """)
    cursor.execute("INSERT INTO estudiantes VALUES (1, 'SinCupo', 'Test', 8, 'python', 0, 0, 0, 'MENTOR')")
    cursor.execute("INSERT INTO kardex_notas VALUES (1, 'INE-186', 18.0, 'APROBADO')")
    cursor.execute("INSERT INTO disponibilidad VALUES (1, 'Sabado', '08:00 - 10:30')")
    conn.commit()
    conn.close()

    candidatos = filtrar_mentores_sql("INE-186", "Sabado", "08:00 - 10:30", db_path=str(db_file))
    assert candidatos == [], "Un mentor con max_cupos_mentor = 0 nunca debe superar el filtro SQL"


def test_resolver_ruta_absoluta_existente(tmp_path):
    """Valida que resolver_ruta_bd devuelva la misma ruta absoluta si el archivo existe."""
    archivo_db = tmp_path / "prueba.db"
    archivo_db.write_text("dummy", encoding="utf-8")
    assert resolver_ruta_bd(str(archivo_db)) == str(archivo_db)


def test_resolver_ruta_inexistente_devuelve_original(monkeypatch):
    """Valida que resolver_ruta_bd devuelva la cadena original si ninguna ruta candidata existe."""
    monkeypatch.setattr(os.path, "exists", lambda p: False)
    ruta_falsa = "base_inexistente_99999.db"
    assert resolver_ruta_bd(ruta_falsa) == ruta_falsa


def test_resolver_ruta_candidata_relativa_resuelve_correctamente():
    """Valida que pasar 'epis_mentorias.db' resuelva la ruta absoluta existente en data/."""
    ruta = resolver_ruta_bd("epis_mentorias.db")
    assert os.path.isabs(ruta)
    assert os.path.exists(ruta)
    assert "data" in ruta


