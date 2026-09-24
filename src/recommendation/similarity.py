"""
Módulo de Similitud Temática y Modelado de Contenido (TF-IDF + Coseno) - EPIS-UPT 2026.
Proporciona funciones para proyectar textos y tags en espacios vectoriales y medir afinidad angular.
"""

from typing import List
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


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
