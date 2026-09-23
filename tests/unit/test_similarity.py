"""
Pruebas Unitarias del Espacio Vectorial y Similitud de Coseno (Paso 12).
Valida el comportamiento defensivo ante vocabularios vacíos, tags en blanco y gradiente de afinidad.
"""

import math
import numpy as np
import pytest

from src.motor_recomendacion import calcular_similitud_contenido


def test_similarity_empty_student_tags():
    """Valida que si el estudiante no ingresa tags (cadena vacía o solo espacios),

    el cálculo no falle y devuelva un arreglo de similitudes en 0.0 para todos los mentores.
    """
    tags_estudiante = "   "
    tags_mentores = ["python algoritmos", "react frontend", "sql bases_datos"]

    similitudes = calcular_similitud_contenido(tags_estudiante, tags_mentores)

    assert isinstance(similitudes, np.ndarray)
    assert len(similitudes) == 3
    assert np.allclose(similitudes, 0.0), f"Esperado todo en 0.0, obtenido {similitudes}"


def test_similarity_empty_vocabulary():
    """Valida que si tanto el estudiante como todos los mentores tienen tags vacíos

    (vocabulario global completamente vacío), TfidfVectorizer no lance
    ValueError ('empty vocabulary') y retorne ceros de forma segura.
    """
    tags_estudiante = ""
    tags_mentores = ["", "   ", "\t\n"]

    similitudes = calcular_similitud_contenido(tags_estudiante, tags_mentores)

    assert isinstance(similitudes, np.ndarray)
    assert len(similitudes) == 3
    assert np.allclose(similitudes, 0.0), f"Esperado todo en 0.0, obtenido {similitudes}"


def test_similarity_candidatos_vacios():
    """Valida que si la lista de mentores está vacía, retorne un array NumPy vacío."""
    similitudes = calcular_similitud_contenido("python machine_learning", [])
    assert isinstance(similitudes, np.ndarray)
    assert len(similitudes) == 0


def test_similarity_identica():
    """Asegura que vocablos idénticos produzcan similitud de coseno = 1.0."""
    tags_estudiante = "python postgresql react algoritmos"
    tags_mentores = ["python postgresql react algoritmos"]

    similitudes = calcular_similitud_contenido(tags_estudiante, tags_mentores)
    assert len(similitudes) == 1
    assert math.isclose(similitudes[0], 1.0, rel_tol=1e-5)


def test_similarity_ortogonal_disjunta():
    """Asegura que vocabularios completamente disjuntos produzcan similitud de coseno = 0.0."""
    tags_estudiante = "calculo_diferencial algebra geometria"
    tags_mentores = ["ciberseguridad redes_tcp_ip linux"]

    similitudes = calcular_similitud_contenido(tags_estudiante, tags_mentores)
    assert len(similitudes) == 1
    assert math.isclose(similitudes[0], 0.0, abs_tol=1e-5)
