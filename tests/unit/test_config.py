"""
Pruebas Unitarias para la Carga y Validación de Configuración (Paso 11).
Valida que parámetros inválidos (alpha negativo, top_k <= 0, JSON corrupto) emitan
errores comprensibles en lugar de propagar comportamientos anómalos en el motor.
"""

import json
import pytest

from src.motor_recomendacion import cargar_reglas_sistema, validar_reglas_sistema


def test_config_valida_correcta(tmp_path):
    """Valida que una configuración bien formada se cargue y valide sin errores."""
    config_valida = {
        "nota_minima_mentor": 14,
        "top_k_recomendados": 3,
        "pesos_algoritmo": {
            "alpha_coseno": 0.70,
            "beta_saturacion": 0.20,
            "gamma_bono_nuevo": 0.10,
        },
    }
    archivo = tmp_path / "valid_rules.json"
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(config_valida, f)

    reglas = cargar_reglas_sistema(str(archivo))
    assert reglas["top_k_recomendados"] == 3
    assert reglas["pesos_algoritmo"]["alpha_coseno"] == 0.70


def test_config_alpha_negativo_lanza_error(tmp_path):
    """Valida que alpha_coseno < 0 emita un ValueError comprensible."""
    config_invalida = {
        "nota_minima_mentor": 14,
        "top_k_recomendados": 3,
        "pesos_algoritmo": {
            "alpha_coseno": -1.0,  # Inválido
            "beta_saturacion": 0.20,
            "gamma_bono_nuevo": 0.10,
        },
    }
    archivo = tmp_path / "bad_alpha.json"
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(config_invalida, f)

    with pytest.raises(ValueError, match="alpha_coseno"):
        cargar_reglas_sistema(str(archivo))


def test_config_top_k_cero_o_negativo_lanza_error(tmp_path):
    """Valida que top_k_recomendados <= 0 emita un ValueError comprensible."""
    config_invalida = {
        "nota_minima_mentor": 14,
        "top_k_recomendados": 0,  # Inválido: debe ser >= 1
        "pesos_algoritmo": {
            "alpha_coseno": 0.70,
            "beta_saturacion": 0.20,
            "gamma_bono_nuevo": 0.10,
        },
    }
    archivo = tmp_path / "bad_top_k.json"
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(config_invalida, f)

    with pytest.raises(ValueError, match="top_k_recomendados"):
        cargar_reglas_sistema(str(archivo))


def test_config_json_corrupto_lanza_error(tmp_path):
    """Valida que un archivo JSON sintácticamente corrupto emita un error claro."""
    archivo_corrupto = tmp_path / "corrupt_rules.json"
    archivo_corrupto.write_text("{ esto no es un json valido: 123 ", encoding="utf-8")

    with pytest.raises(ValueError, match="[Ee]rror.*(JSON|decodificar|sintaxis)"):
        cargar_reglas_sistema(str(archivo_corrupto))
