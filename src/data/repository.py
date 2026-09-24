"""
Repositorio de Acceso a Datos Relacionales (SQLite) - EPIS-UPT 2026.
Aísla la persistencia y consultas relacionales SQL del motor de recomendación.
"""

import os
import sqlite3
from typing import Any, List, Tuple


def resolver_ruta_bd(db_path: str = "epis_mentorias.db") -> str:
    """Resuelve dinámicamente la ruta a la base de datos SQLite soportando ejecuciones desde raíz, src/ o tests/."""
    if os.path.isabs(db_path) and os.path.exists(db_path):
        return db_path
    candidatas = [
        db_path,
        os.path.join("data", db_path),
        os.path.join("data", "epis_mentorias.db"),
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "epis_mentorias.db"),
        os.path.join(os.path.dirname(__file__), "..", "..", "data", os.path.basename(db_path)),
    ]
    for c in candidatas:
        if os.path.exists(c):
            return os.path.abspath(c)
    return db_path


def filtrar_mentores_sql(
    codigo_curso: str,
    dia: str,
    franja_horaria: str,
    nota_minima: float = 14.0,
    db_path: str = "epis_mentorias.db",
) -> List[Tuple[Any, ...]]:
    """FASE 1: FILTRADO DETERMINISTA (SQL HARD RULES).
    
    Ejecuta la primera etapa del pipeline en el motor de base de datos relacional.
    Aplica una poda estricta basada en reglas de negocio académicas y operativas:
      1. Asimetría de roles: Solo estudiantes con rol 'MENTOR'.
      2. Mérito académico: Curso cursado con condición 'APROBADO' y nota >= nota_minima (14.0).
      3. Capacidad de atención: Mentores con cupos libres (sesiones_activas < max_cupos_mentor).
      4. Factibilidad horaria: Coincidencia simultánea en día y franja horaria requerida.
    
    Args:
        codigo_curso: Código oficial de la materia (ej. 'INE-186' para Matemática I).
        dia: Día de la semana solicitado (ej. 'Sabado').
        franja_horaria: Rango horario solicitado (ej. '08:00 - 10:30').
        nota_minima: Calificación vigesimal mínima exigida (default: 14.0).
        db_path: Ruta al archivo SQLite de persistencia.
        
    Returns:
        List[Tuple]: Lista de tuplas con los atributos de los mentores candidatos aptos.
    """
    ruta_real_bd = resolver_ruta_bd(db_path)
    conn = sqlite3.connect(ruta_real_bd)
    cursor = conn.cursor()

    # Consulta relacional con JOINs optimizados sobre kardex y disponibilidad
    query = """
    SELECT DISTINCT e.id, e.nombres, e.apellidos, e.ciclo_actual, e.tags_interes, 
           e.sesiones_activas, e.max_cupos_mentor, e.es_nuevo_mentor, k.nota
    FROM estudiantes e
    JOIN kardex_notas k ON e.id = k.id_estudiante
    JOIN disponibilidad d ON e.id = d.id_estudiante
    WHERE e.rol = 'MENTOR'
      AND k.codigo_curso = ?
      AND k.condicion = 'APROBADO'
      AND k.nota >= ?
      AND e.sesiones_activas < e.max_cupos_mentor
      AND d.dia = ?
      AND d.franja_horaria = ?
    """

    cursor.execute(query, (codigo_curso, nota_minima, dia, franja_horaria))
    mentores = cursor.fetchall()
    conn.close()
    return mentores
