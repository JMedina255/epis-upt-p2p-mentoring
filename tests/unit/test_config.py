"""
Pruebas Unitarias para la Carga y Validación de Configuración (Paso 11).
Valida que parámetros inválidos (alpha negativo, top_k <= 0, JSON corrupto) emitan
errores comprensibles en lugar de propagar comportamientos anómalos en el motor.
"""

import json
import pytest

from src.config import cargar_reglas_sistema, validar_reglas_sistema
import src.motor_recomendacion as motor_rec


def test_config_retrocompatibilidad_import_desde_motor():
    """Valida que cargar_reglas_sistema y validar_reglas_sistema sigan accesibles desde motor_recomendacion."""
    assert motor_rec.cargar_reglas_sistema is cargar_reglas_sistema
    assert motor_rec.validar_reglas_sistema is validar_reglas_sistema


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


def test_config_alpha_mayor_a_uno_lanza_error(tmp_path):
    """Valida que alpha_coseno > 1.0 (ej. 900) emita un ValueError comprensible."""
    config = {
        "nota_minima_mentor": 14,
        "top_k_recomendados": 3,
        "pesos_algoritmo": {"alpha_coseno": 900.0, "beta_saturacion": 0.20, "gamma_bono_nuevo": 0.10},
    }
    archivo = tmp_path / "bad_alpha_high.json"
    archivo.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(ValueError, match="alpha_coseno.*rango"):
        cargar_reglas_sistema(str(archivo))


def test_config_beta_mayor_a_uno_lanza_error(tmp_path):
    """Valida que beta_saturacion > 1.0 (ej. 450) emita un ValueError comprensible."""
    config = {
        "nota_minima_mentor": 14,
        "top_k_recomendados": 3,
        "pesos_algoritmo": {"alpha_coseno": 0.70, "beta_saturacion": 450.0, "gamma_bono_nuevo": 0.10},
    }
    archivo = tmp_path / "bad_beta_high.json"
    archivo.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(ValueError, match="beta_saturacion.*rango"):
        cargar_reglas_sistema(str(archivo))


def test_config_gamma_mayor_a_uno_lanza_error(tmp_path):
    """Valida que gamma_bono_nuevo > 1.0 (ej. 200) emita un ValueError comprensible."""
    config = {
        "nota_minima_mentor": 14,
        "top_k_recomendados": 3,
        "pesos_algoritmo": {"alpha_coseno": 0.70, "beta_saturacion": 0.20, "gamma_bono_nuevo": 200.0},
    }
    archivo = tmp_path / "bad_gamma_high.json"
    archivo.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(ValueError, match="gamma_bono_nuevo.*rango"):
        cargar_reglas_sistema(str(archivo))


def test_config_nota_minima_fuera_de_escala_vigesimal_lanza_error(tmp_path):
    """Valida que nota_minima_mentor fuera de [0, 20] (ej. 150 o -1) emita un ValueError."""
    config_alta = {
        "nota_minima_mentor": 150,  # Inválido en escala vigesimal
        "top_k_recomendados": 3,
        "pesos_algoritmo": {"alpha_coseno": 0.70, "beta_saturacion": 0.20, "gamma_bono_nuevo": 0.10},
    }
    archivo = tmp_path / "bad_nota_high.json"
    archivo.write_text(json.dumps(config_alta), encoding="utf-8")

    with pytest.raises(ValueError, match="nota_minima_mentor.*vigesimal"):
        cargar_reglas_sistema(str(archivo))


def test_validar_reglas_no_es_diccionario_lanza_error():
    """Valida que pasar un objeto que no es dict a validar_reglas_sistema lance ValueError."""
    with pytest.raises(ValueError, match="La configuración debe ser un diccionario"):
        validar_reglas_sistema(["no", "es", "dict"])


def test_validar_reglas_pesos_no_es_diccionario_lanza_error():
    """Valida que pesos_algoritmo que no sea dict lance ValueError."""
    with pytest.raises(ValueError, match="pesos_algoritmo debe ser un diccionario"):
        validar_reglas_sistema({"pesos_algoritmo": "invalido"})


def test_cargar_reglas_ruta_inexistente_lanza_filenotfound(tmp_path):
    """Valida que pasar una ruta_config explícita inexistente lance FileNotFoundError."""
    ruta_falsa = tmp_path / "archivo_no_existente.json"
    with pytest.raises(FileNotFoundError, match="No se encontró el archivo"):
        cargar_reglas_sistema(str(ruta_falsa))


def test_cargar_reglas_fallback_cuando_no_hay_archivos(monkeypatch):
    """Valida que si no se encuentra ningún archivo de configuración en las rutas por defecto, devuelva el fallback."""
    monkeypatch.setattr("os.path.exists", lambda r: False)
    config = cargar_reglas_sistema()
    assert config["nota_minima_mentor"] == 14
    assert config["top_k_recomendados"] == 3
    assert config["pesos_algoritmo"]["alpha_coseno"] == 0.70


