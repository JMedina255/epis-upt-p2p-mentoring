import datetime
import json
import os
import re

BASE_DIR = (
    os.path.abspath(os.path.join(os.getcwd(), ".."))
    if os.path.basename(os.getcwd()) == "scripts"
    else os.path.abspath(os.getcwd())
)
CONFIG_FILE = os.path.join(BASE_DIR, "config", "system_rules.json")
README_FILE = os.path.join(BASE_DIR, "README.md")
EXPLICACION_FILE = os.path.join(BASE_DIR, "docs", "EXPLICACION_SISTEMA.md")


def cargar_configuracion():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    rutas = ["system_rules.json", os.path.join("config", "system_rules.json")]
    for r in rutas:
        if os.path.exists(r):
            with open(r, "r", encoding="utf-8") as f:
                return json.load(f)
    print(f"Error: No se encontró system_rules.json en {CONFIG_FILE}")
    return None


def actualizar_readme(config):
    if not os.path.exists(README_FILE):
        return
    with open(README_FILE, "r", encoding="utf-8") as f:
        contenido = f.read()

    # Reemplazo de parámetros en tabla Markdown
    contenido = re.sub(
        r"(\|\s*\*\*Población Objetivo\*\*\s*\|\s*)\d+(\s*\|)",
        rf"\g<1>{config['poblacion_estudiantes']}\g<2>",
        contenido,
    )
    contenido = re.sub(
        r"(\|\s*\*\*Nota Mínima Aprobatoria\*\*\s*\|\s*\\ge )\d+\.?\d*(\s*\|)",
        rf"\g<1>{config['nota_minima_mentor']}.0\g<2>",
        contenido,
    )
    contenido = re.sub(
        r"(\|\s*\*\*Ponderación Coseno \(\\alpha\)\*\*\s*\|\s*)\d+\.\d+(\s*\|)",
        rf"\g<1>{config['pesos_algoritmo']['alpha_coseno']:.2f}\g<2>",
        contenido,
    )
    contenido = re.sub(
        r"(\|\s*\*\*Penalización Sobrecarga \(\\beta\)\*\*\s*\|\s*)\d+\.\d+(\s*\|)",
        rf"\g<1>{config['pesos_algoritmo']['beta_saturacion']:.2f}\g<2>",
        contenido,
    )
    contenido = re.sub(
        r"(\|\s*\*\*Bono Nuevo Mentor \(\\gamma\)\*\*\s*\|\s*)\d+\.\d+(\s*\|)",
        rf"\g<1>{config['pesos_algoritmo']['gamma_bono_nuevo']:.2f}\g<2>",
        contenido,
    )
    contenido = re.sub(
        r"(\|\s*\*\*Quórum Clase Presencial\*\*\s*\|\s*)\d+(\s*alumnos\s*\|)",
        rf"\g<1>{config['quorum_presencial']}\g<2>",
        contenido,
    )
    contenido = re.sub(
        r"(\|\s*\*\*Quórum Clase Virtual\*\*\s*\|\s*)\d+(\s*alumnos\s*\|)",
        rf"\g<1>{config['quorum_virtual']}\g<2>",
        contenido,
    )

    with open(README_FILE, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"-> {README_FILE} sincronizado con éxito.")


def actualizar_explicacion(config):
    if not os.path.exists(EXPLICACION_FILE):
        return
    with open(EXPLICACION_FILE, "r", encoding="utf-8") as f:
        contenido = f.read()

    # Actualizar constantes en la explicación matemática
    contenido = re.sub(
        r"(\*\*\$\\alpha = )\d+\.\d+(\$\*\*:)",
        rf"\g<1>{config['pesos_algoritmo']['alpha_coseno']:.2f}\g<2>",
        contenido,
    )
    contenido = re.sub(
        r"(\*\*\$\\beta = )\d+\.\d+(\$\*\*:)",
        rf"\g<1>{config['pesos_algoritmo']['beta_saturacion']:.2f}\g<2>",
        contenido,
    )
    contenido = re.sub(
        r"(\*\*\$\\gamma = )\d+\.\d+(\$\*\*:)",
        rf"\g<1>{config['pesos_algoritmo']['gamma_bono_nuevo']:.2f}\g<2>",
        contenido,
    )

    # Actualizar quórum en texto
    contenido = re.sub(
        r"(\*\*)\d+(\s*inscritos en presencial\s*/\s*)\d+(\s*en virtual\*\*)",
        rf"\g<1>{config['quorum_presencial']}\g<2>{config['quorum_virtual']}\g<3>",
        contenido,
    )

    with open(EXPLICACION_FILE, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"-> {EXPLICACION_FILE} sincronizado con éxito.")


def main():
    print(
        f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iniciando sincronización de documentación..."
    )
    config = cargar_configuracion()
    if config:
        actualizar_readme(config)
        actualizar_explicacion(config)
        print("Todos los archivos Markdown han sido actualizados y validados.")


if __name__ == "__main__":
    main()