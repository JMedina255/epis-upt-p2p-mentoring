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

import json
import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def resolver_ruta_bd(db_path: str = "epis_mentorias.db") -> str:
    """Resuelve dinámicamente la ruta a la base de datos SQLite soportando ejecuciones desde raíz, src/ o tests/."""
    if os.path.isabs(db_path) and os.path.exists(db_path):
        return db_path
    candidatas = [
        db_path,
        os.path.join("data", db_path),
        os.path.join("data", "epis_mentorias.db"),
        os.path.join(os.path.dirname(__file__), "..", "data", "epis_mentorias.db"),
        os.path.join(os.path.dirname(__file__), "..", "data", os.path.basename(db_path)),
    ]
    for c in candidatas:
        if os.path.exists(c):
            return os.path.abspath(c)
    return db_path


def validar_reglas_sistema(config: Dict[str, Any]) -> Dict[str, Any]:
    """Valida la consistencia lógica y de tipos de las reglas del sistema.
    
    Verifica que:
      - nota_minima_mentor esté en la escala vigesimal [0.0, 20.0].
      - top_k_recomendados sea un entero >= 1.
      - alpha_coseno, beta_saturacion y gamma_bono_nuevo estén en el rango [0.0, 1.0].
      
    Args:
        config: Diccionario con la configuración del sistema.
        
    Returns:
        Dict[str, Any]: El diccionario de configuración validado.
        
    Raises:
        ValueError: Si algún parámetro contiene valores fuera del dominio válido.
    """
    if not isinstance(config, dict):
        raise ValueError("La configuración debe ser un diccionario.")

    # Validación de nota mínima en escala vigesimal [0, 20]
    nota_min = config.get("nota_minima_mentor")
    if nota_min is not None and (not isinstance(nota_min, (int, float)) or not (0 <= nota_min <= 20)):
        raise ValueError(
            f"nota_minima_mentor debe estar en la escala vigesimal [0, 20], recibido: {nota_min}"
        )

    # Validación de top_k
    top_k = config.get("top_k_recomendados")
    if top_k is not None and (not isinstance(top_k, int) or top_k < 1):
        raise ValueError(f"top_k_recomendados debe ser un entero mayor o igual a 1, recibido: {top_k}")

    # Validación de pesos algorítmicos en el rango normalizado [0, 1]
    pesos = config.get("pesos_algoritmo")
    if pesos is not None:
        if not isinstance(pesos, dict):
            raise ValueError("pesos_algoritmo debe ser un diccionario.")

        alpha = pesos.get("alpha_coseno")
        if alpha is not None and (not isinstance(alpha, (int, float)) or not (0 <= alpha <= 1)):
            raise ValueError(f"alpha_coseno debe estar en el rango [0, 1], recibido: {alpha}")

        beta = pesos.get("beta_saturacion")
        if beta is not None and (not isinstance(beta, (int, float)) or not (0 <= beta <= 1)):
            raise ValueError(f"beta_saturacion debe estar en el rango [0, 1], recibido: {beta}")

        gamma = pesos.get("gamma_bono_nuevo")
        if gamma is not None and (not isinstance(gamma, (int, float)) or not (0 <= gamma <= 1)):
            raise ValueError(f"gamma_bono_nuevo debe estar en el rango [0, 1], recibido: {gamma}")

    return config


def cargar_reglas_sistema(ruta_config: Optional[str] = None) -> Dict[str, Any]:
    """Carga y valida los parámetros del algoritmo desde la fuente única de verdad.
    
    Garantiza el desacoplamiento de parámetros algorítmicos (alpha, beta, gamma, top-k,
    nota mínima), evitando valores hardcodeados en el código fuente.
    
    Args:
        ruta_config: Ruta opcional directa al archivo JSON de configuración.
        
    Returns:
        Dict[str, Any]: Diccionario con parámetros globales y pesos del modelo validados.
        
    Raises:
        ValueError: Si el archivo JSON está corrupto o contiene parámetros inválidos.
    """
    if ruta_config is not None:
        if not os.path.exists(ruta_config):
            raise FileNotFoundError(f"No se encontró el archivo de configuración: {ruta_config}")
        try:
            with open(ruta_config, "r", encoding="utf-8") as f:
                datos = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Error al decodificar el archivo JSON de configuración: {e}")
        return validar_reglas_sistema(datos)

    rutas = [
        "system_rules.json",
        os.path.join("config", "system_rules.json"),
        os.path.join(os.path.dirname(__file__), "..", "config", "system_rules.json"),
        os.path.join(os.path.dirname(__file__), "config", "system_rules.json"),
    ]
    for ruta in rutas:
        if os.path.exists(ruta):
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    datos = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Error al decodificar la configuración JSON en {ruta}: {e}")
            return validar_reglas_sistema(datos)

    # Valores de reserva si no se encuentra el archivo de configuración
    fallback = {
        "nota_minima_mentor": 14,
        "top_k_recomendados": 3,
        "pesos_algoritmo": {
            "alpha_coseno": 0.70,
            "beta_saturacion": 0.20,
            "gamma_bono_nuevo": 0.10,
        },
    }
    return validar_reglas_sistema(fallback)


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
      1. Asimetría de roles: Solo estudiantes con rol 'MENTOR' de ciclos avanzados.
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


def calcular_similitud_contenido(
    tags_estudiante: str, tags_mentores: List[str]
) -> np.ndarray:
    """FASE 2: ESPACIO VECTORIAL Y CONTENIDO (TF-IDF + COSENO).
    
    Transforma el lenguaje natural de tags temáticos en un espacio vectorial multidimensional.
    - Se ajusta un TfidfVectorizer sobre el corpus unificado (tutorado + mentores candidatos).
    - Se extrae el vector disperso del estudiante (índice 0) y los vectores de los mentores (índices 1..N).
    - Se calcula el coseno del ángulo entre los vectores:
        cos(theta) = (A · B) / (||A|| * ||B||)
      proporcionando una métrica de afinidad temática normalizada en [0.0, 1.0].
      
    Args:
        tags_estudiante: Cadena de texto con temas de dificultad o interés del alumno.
        tags_mentores: Lista de cadenas de texto con las competencias de cada mentor candidato.
        
    Returns:
        np.ndarray: Arreglo 1D con las similitudes de coseno asociadas a cada mentor.
    """
    if not tags_mentores:
        return np.array([], dtype=float)

    # El corpus unificado permite que el vocabulario y la ponderación IDF consideren
    # tanto las palabras clave del estudiante como las de los mentores presentes.
    textos_totales = [tags_estudiante] + tags_mentores
    tfidf = TfidfVectorizer()
    try:
        matriz_tfidf = tfidf.fit_transform(textos_totales)
    except ValueError:
        # Se captura el caso en que todos los textos están vacíos o solo contienen stop words/espacios
        return np.zeros(len(tags_mentores), dtype=float)

    vector_estudiante = matriz_tfidf[0:1]
    vectores_mentores = matriz_tfidf[1:]

    similitudes = cosine_similarity(vector_estudiante, vectores_mentores)[0]
    return similitudes


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
if __name__ == "__main__":
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