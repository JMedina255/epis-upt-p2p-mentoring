"""
Pruebas Unitarias del Filtrado Determinista Relacional SQL (Fase 1).
Utiliza la fixture aislada 'test_db' (Paso 13) para garantizar pruebas reproducibles,
herméticas y sin acoplamiento a data/epis_mentorias.db.
"""

import pytest
from src.motor_recomendacion import filtrar_mentores_sql


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
