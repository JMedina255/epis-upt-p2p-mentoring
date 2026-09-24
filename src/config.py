"""
Módulo de Configuración y Parámetros del Sistema (EPIS-UPT 2026).
Carga y valida los parámetros del motor de recomendación desde system_rules.json (SSOT).
"""

import json
import os
from typing import Any, Dict, Optional


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
        FileNotFoundError: Si la ruta explícita no existe en el sistema.
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
