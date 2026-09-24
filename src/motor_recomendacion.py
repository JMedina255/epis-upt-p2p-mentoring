"""
====================================================================================================
SISTEMA WEB P2P DE MENTORÍAS ACADÉMICAS - EPIS UPT (2026-II)
MOTOR DE RECOMENDACIÓN HÍBRIDO (TWO-STAGE RECOMMENDATION & LOAD-AWARE RE-RANKING)
====================================================================================================

Contexto Metodológico y Arquitectónico:
--------------------------------------
Este módulo implementa el núcleo algorítmico para la personalización de mentorías académicas
entre pares (P2P) en la Escuela Profesional de Ingeniería de Sistemas (EPIS) de la Universidad
Privada de Tacna (UPT), considerando una población de 350 estudiantes matriculados (40 mentores
avanzados y 310 tutorados).

Arquitectura del Pipeline en Etapas (Two-Stage Architecture):
-----------------------------------------------------------
1. ETAPA RELACIONAL (Filtro Duro en SQL):
   - Reduce el espacio de búsqueda eliminando candidatos no aptos directamente en el motor de BD.
   - Restricciones duras: Condición 'APROBADO', nota en la materia >= 14.0, coincidencia horaria
     exacta (día y franja) y cupo disponible (sesiones_activas < max_cupos_mentor).
   - Optimización por cortocircuito (Short-Circuit): Si no hay candidatos aptos, se evita el costo
     computacional de vectorización y álgebra lineal.

2. ETAPA SEMÁNTICA (TF-IDF + Similitud de Coseno):
   - Vectoriza en un espacio disperso los tags de necesidades del tutorado y las competencias
     de los mentores preseleccionados utilizando Scikit-Learn.
   - Computa la similitud de coseno (proyección angular normalizada en el rango [0.0, 1.0]).

3. ETAPA DE RE-RANKING SENSIBLE A LA CARGA (Load-Aware Re-ranking):
   - Mitiga la sobrecarga operativa de mentores con alta demanda y estimula la rotación y activación
     de mentores recién incorporados sin historial previo.
   - Formulación Matemática:
       PuntajeFinal(m) = alpha * SimCoseno(u, m) - beta * (SesionesActivas(m) / MaxCupos(m)) + gamma * BonoNuevo(m)
     donde:
       * alpha (0.70): Ponderación de afinidad temático-semántica.
       * beta  (0.20): Factor de penalización por saturación de carga operativa.
       * gamma (0.10): Bono de oportunidad para mentores sin historial previo de tutorías.

División Modular por Fases de Desarrollo y Verificación:
-------------------------------------------------------
- FASE 1: Filtrado Determinista (SQL Hard Rules) -> Función: filtrar_mentores_sql()
- FASE 2: Espacio Vectorial y Contenido (TF-IDF + Coseno) -> Función: calcular_similitud_contenido()
- FASE 3: Integración Two-Stage + Top-K Ranking -> Función: recomendar_mentores()
- FASE 4: Re-ranking Sensible a la Carga (Load-Aware Re-ranking) -> Función: aplicar_reranking_equidad()
- FASE 5: Auditoría y Experimentación -> Ejecución y telemetría de resultados.

Restricciones No Negociables:
-----------------------------
- Alcance exclusivamente plataforma web (no móviles).
- Protección de datos según Ley N° 29733 (sin captura de credenciales intranet).
- Lectura dinámica de pesos desde system_rules.json (Single Source of Truth).
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

try:
    from src.config import cargar_reglas_sistema, validar_reglas_sistema
except ImportError:
    from config import cargar_reglas_sistema, validar_reglas_sistema

try:
    from src.data.repository import filtrar_mentores_sql, resolver_ruta_bd
except ImportError:
    from data.repository import filtrar_mentores_sql, resolver_ruta_bd

try:
    from src.recommendation.similarity import calcular_similitud_contenido
except ImportError:
    from recommendation.similarity import calcular_similitud_contenido


def aplicar_reranking_equidad(
    mentores_candidatos: List[Tuple[Any, ...]],
    similitudes: np.ndarray,
    alpha: float = 0.70,
    beta: float = 0.20,
    gamma: float = 0.10,
) -> List[Dict[str, Any]]:
    """FASE 4: RE-RANKING SENSIBLE A LA CARGA (LOAD-AWARE RE-RANKING).
    
    Ajusta la puntuación bruta de similitud para mitigar la saturación operativa y otorgar
    oportunidades de activación a nuevos mentores:
    
      PuntajeFinal(m) = alpha * SimCoseno(u, m) - beta * (SesionesActivas / MaxCupos) + gamma * BonoNuevo
      
    Componentes del re-ranking:
      * alpha * SimCoseno: Recompensa la pertinencia y afinidad temática.
      * - beta * (SesionesActivas / MaxCupos): Penalización proporcional a la carga de trabajo.
      * + gamma * BonoNuevo: Bono de oportunidad para mentores sin tutorías previas.
      
    Args:
        mentores_candidatos: Lista de tuplas con información relacional de los mentores aptos.
        similitudes: Arreglo NumPy con las similitudes de coseno calculadas en la Fase 2.
        alpha: Peso de afinidad semántica (leído de system_rules.json).
        beta: Peso de penalización por saturación de cupos.
        gamma: Peso de bonificación para mentores nuevos.
        
    Returns:
        List[Dict[str, Any]]: Lista de diccionarios con la información completa de cada mentor
                              ordenada descendentemente por su puntaje final.
    """
    resultados: List[Dict[str, Any]] = []
    for idx, mentor in enumerate(mentores_candidatos):
        (
            m_id,
            nom,
            ape,
            ciclo,
            tags,
            sesiones,
            max_cupos,
            es_nuevo,
            nota_curso,
        ) = mentor
        sim_coseno = float(similitudes[idx])

        # Fracción de saturación operativa en el rango [0.0, 1.0]
        saturacion = sesiones / max_cupos if max_cupos > 0 else 1.0
        bono_nuevo = gamma if es_nuevo == 1 else 0.0

        # Puntuación final balanceada
        puntaje_final = (alpha * sim_coseno) - (beta * saturacion) + bono_nuevo

        resultados.append({
            "id": m_id,
            "mentor": f"{nom} {ape}",
            "ciclo": ciclo,
            "nota_en_curso": nota_curso,
            "similitud_coseno": round(sim_coseno, 4),
            "puntaje_final": round(puntaje_final, 4),
            "tags": tags,
            "sesiones_activas": sesiones,
            "max_cupos": max_cupos,
            "es_nuevo": bool(es_nuevo),
        })

    # Ordenar candidatos de mayor a menor puntaje final
    resultados.sort(key=lambda x: x["puntaje_final"], reverse=True)
    return resultados


def recomendar_mentores(
    codigo_curso_solicitado: str,
    tags_estudiante: str,
    dia_preferido: str,
    franja_preferida: str,
    top_k: Optional[int] = None,
    db_path: str = "epis_mentorias.db",
) -> List[Dict[str, Any]]:
    """FASE 3 / FASE 5: PIPELINE COMPLETO DE RECOMENDACIÓN TWO-STAGE Y SELECCIÓN TOP-K.
    
    Orquesta el flujo integral de recomendación conectando las fases modulares:
      1. Carga dinámica de parámetros desde la configuración central.
      2. Filtrado duro SQL con descarte inmediato si el conjunto resultante es vacío (Short-circuit).
      3. Vectorización de contenido y similitud de coseno con Scikit-Learn.
      4. Re-ranking sensible a la carga (Load-aware re-ranking).
      5. Selección de los Top-K mejores candidatos para renderizado asistido en el frontend web.
      
    Args:
        codigo_curso_solicitado: Código de asignatura (ej. 'INE-186').
        tags_estudiante: Palabras clave que describen las dudas o intereses del tutorado.
        dia_preferido: Día preferido para la sesión ('Lunes'..'Sabado').
        franja_preferida: Franja horaria requerida (ej. '08:00 - 10:30').
        top_k: Número de candidatos sugeridos (por defecto leído de system_rules.json, ej. 3).
        db_path: Ruta a la base de datos relacional SQLite.
        
    Returns:
        List[Dict[str, Any]]: Lista con los Top-K mentores recomendados listos para interfaz web.
    """
    # Carga de parámetros desde la Fuente Única de Verdad (SSOT)
    reglas = cargar_reglas_sistema()
    k_final = top_k if top_k is not None else reglas.get("top_k_recomendados", 3)
    if not isinstance(k_final, int) or k_final < 1:
        raise ValueError("top_k debe ser un entero mayor o igual a 1")

    nota_min = float(reglas.get("nota_minima_mentor", 14.0))
    pesos = reglas.get("pesos_algoritmo", {})
    alpha = float(pesos.get("alpha_coseno", 0.70))
    beta = float(pesos.get("beta_saturacion", 0.20))
    gamma = float(pesos.get("gamma_bono_nuevo", 0.10))

    # FASE 1: Filtrado Determinista (SQL Hard Rules)
    mentores_candidatos = filtrar_mentores_sql(
        codigo_curso=codigo_curso_solicitado,
        dia=dia_preferido,
        franja_horaria=franja_preferida,
        nota_minima=nota_min,
        db_path=db_path,
    )

    # Cortocircuito: si no hay candidatos aptos, no se ejecuta vectorización ni re-ranking
    if not mentores_candidatos:
        return []

    # FASE 2: Espacio Vectorial y Similitud de Coseno
    textos_mentores = [m[4] for m in mentores_candidatos]
    similitudes = calcular_similitud_contenido(tags_estudiante, textos_mentores)

    # FASE 4: Re-ranking sensible a la carga (Load-aware re-ranking)
    ranking = aplicar_reranking_equidad(
        mentores_candidatos=mentores_candidatos,
        similitudes=similitudes,
        alpha=alpha,
        beta=beta,
        gamma=gamma,
    )

    # FASE 3 / FASE 5: Entrega asistida Top-K
    return ranking[:k_final]


# ==============================================================================
# EJEMPLO DE PRUEBA REAL
# ==============================================================================
if __name__ == "__main__":  # pragma: no cover
    # Alumno novato de Ciclo I necesita ayuda en MATEMÁTICA I (INE-186)
    # Tags del alumno: dificultades en cálculo, álgebra y lógica
    # Disponibilidad deseada: Sábado de 08:00 - 10:30
    curso_test = "INE-186"
    tags_alumno = "calculo_diferencial algebra logica_proposicional"
    dia_test = "Sabado"
    franja_test = "08:00 - 10:30"

    print(
        f"\nBuscando mentores para {curso_test} ({dia_test} {franja_test})...\n"
    )
    top_mentores = recomendar_mentores(
        curso_test, tags_alumno, dia_test, franja_test, top_k=3
    )

    for rank, m in enumerate(top_mentores, start=1):
        print(f"Top {rank}: {m['mentor']} (Ciclo {m['ciclo']})")
        print(f"       Nota en el curso: {m['nota_en_curso']}")
        print(f"       Similitud Coseno: {m['similitud_coseno']}")
        print(f"       Puntaje Final:    {m['puntaje_final']}")
        print(f"       Competencias:     {m['tags']}\n")