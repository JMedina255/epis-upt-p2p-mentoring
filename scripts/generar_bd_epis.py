import json
import os
import random
import sqlite3

# Fijar semilla para que los resultados sean reproducibles en tus pruebas
random.seed(2026)

# ==============================================================================
# 1. CATÁLOGO OFICIAL DE CURSOS EPIS-UPT (2026-II)
# ==============================================================================
CURSOS_EPIS = [
    # Ciclo 1
    {
        "codigo": "EG-181",
        "nombre": "COMUNICACIÓN I",
        "ciclo": 1,
        "area": "GENERAL",
    },
    {
        "codigo": "EG-182",
        "nombre": "MATEMÁTICA BÁSICA",
        "ciclo": 1,
        "area": "MATEMATICA",
    },
    {
        "codigo": "EG-183",
        "nombre": "ESTRATEGIAS PARA EL APRENDIZAJE AUTÓNOMO",
        "ciclo": 1,
        "area": "GENERAL",
    },
    {
        "codigo": "EG-184",
        "nombre": "DESARROLLO PERSONAL Y LIDERAZGO",
        "ciclo": 1,
        "area": "HUMANIDADES",
    },
    {
        "codigo": "EG-185",
        "nombre": "DESARROLLO DE COMPETENCIAS DIGITALES",
        "ciclo": 1,
        "area": "TECNOLOGIA",
    },
    {"codigo": "INE-186", "nombre": "MATEMÁTICA I", "ciclo": 1, "area": "CIENCIAS"},
    # Ciclo 2
    {
        "codigo": "EG-281",
        "nombre": "COMUNICACIÓN II",
        "ciclo": 2,
        "area": "GENERAL",
    },
    {
        "codigo": "EG-282",
        "nombre": "TERRITORIO PERUANO Y SEGURIDAD NACIONAL",
        "ciclo": 2,
        "area": "GENERAL",
    },
    {"codigo": "EG-283", "nombre": "FILOSOFÍA", "ciclo": 2, "area": "HUMANIDADES"},
    {
        "codigo": "INE-284",
        "nombre": "TÉCNICAS DE PROGRAMACIÓN",
        "ciclo": 2,
        "area": "PROGRAMACION",
    },
    {"codigo": "INE-285", "nombre": "FÍSICA I", "ciclo": 2, "area": "CIENCIAS"},
    {
        "codigo": "INE-286",
        "nombre": "MATEMÁTICA II",
        "ciclo": 2,
        "area": "MATEMATICA",
    },
    # Ciclo 3
    {"codigo": "INE-381", "nombre": "ECONOMÍA", "ciclo": 3, "area": "GESTION"},
    {"codigo": "EG-382", "nombre": "ÉTICA", "ciclo": 3, "area": "HUMANIDADES"},
    {
        "codigo": "INE-383",
        "nombre": "ESTADÍSTICA Y PROBABILIDADES",
        "ciclo": 3,
        "area": "CIENCIAS",
    },
    {
        "codigo": "SI-384",
        "nombre": "ESTRUCTURA DE DATOS",
        "ciclo": 3,
        "area": "PROGRAMACION",
    },
    {
        "codigo": "SI-385",
        "nombre": "SISTEMAS DE INFORMACIÓN",
        "ciclo": 3,
        "area": "SOFTWARE",
    },
    {
        "codigo": "SI-386",
        "nombre": "MATEMÁTICA DISCRETA",
        "ciclo": 3,
        "area": "MATEMATICA",
    },
    # Ciclo 4
    {
        "codigo": "SI-481",
        "nombre": "MODELAMIENTO DE PROCESOS",
        "ciclo": 4,
        "area": "GESTION",
    },
    {
        "codigo": "SI-482",
        "nombre": "INGENIERÍA ECONÓMICA Y FINANCIERA",
        "ciclo": 4,
        "area": "GESTION",
    },
    {
        "codigo": "SI-483",
        "nombre": "INTERACCIÓN Y DISEÑO DE INTERFACES",
        "ciclo": 4,
        "area": "SOFTWARE",
    },
    {
        "codigo": "INE-484",
        "nombre": "DISEÑO EN INGENIERÍA",
        "ciclo": 4,
        "area": "INGENIERIA",
    },
    {
        "codigo": "SI-485",
        "nombre": "SISTEMAS ELECTRÓNICOS DIGITALES",
        "ciclo": 4,
        "area": "HARDWARE",
    },
    {
        "codigo": "SI-486",
        "nombre": "PROGRAMACIÓN I",
        "ciclo": 4,
        "area": "PROGRAMACION",
    },
    # Ciclo 5
    {
        "codigo": "SI-581",
        "nombre": "ARQUITECTURA DE COMPUTADORAS",
        "ciclo": 5,
        "area": "HARDWARE",
    },
    {
        "codigo": "SI-582",
        "nombre": "DISEÑO DE BASE DE DATOS",
        "ciclo": 5,
        "area": "BD",
    },
    {
        "codigo": "SI-583",
        "nombre": "DISEÑO Y MODELAMIENTO VIRTUAL",
        "ciclo": 5,
        "area": "SOFTWARE",
    },
    {
        "codigo": "SI-584",
        "nombre": "INGENIERÍA DE REQUERIMIENTOS",
        "ciclo": 5,
        "area": "SOFTWARE",
    },
    {
        "codigo": "SI-585",
        "nombre": "INGENIERÍA DE SOFTWARE",
        "ciclo": 5,
        "area": "SOFTWARE",
    },
    {
        "codigo": "SI-586",
        "nombre": "PROGRAMACIÓN II",
        "ciclo": 5,
        "area": "PROGRAMACION",
    },
    # Ciclo 6
    {
        "codigo": "EG-681",
        "nombre": "ECOLOGÍA Y DESARROLLO SOSTENIBLE",
        "ciclo": 6,
        "area": "GENERAL",
    },
    {
        "codigo": "SI-682",
        "nombre": "SISTEMAS OPERATIVOS I",
        "ciclo": 6,
        "area": "TI",
    },
    {"codigo": "SI-683", "nombre": "BASE DE DATOS I", "ciclo": 6, "area": "BD"},
    {
        "codigo": "SI-684",
        "nombre": "INVESTIGACIÓN DE OPERACIONES",
        "ciclo": 6,
        "area": "CIENCIAS",
    },
    {
        "codigo": "SI-685",
        "nombre": "DISEÑO Y ARQUITECTURA DE SOFTWARE",
        "ciclo": 6,
        "area": "SOFTWARE",
    },
    {
        "codigo": "SI-686",
        "nombre": "PROGRAMACIÓN III",
        "ciclo": 6,
        "area": "PROGRAMACION",
    },
    # Ciclo 7
    {
        "codigo": "EG-781",
        "nombre": "PROBLEMAS Y DESAFÍOS DEL PERÚ",
        "ciclo": 7,
        "area": "GENERAL",
    },
    {
        "codigo": "SI-782",
        "nombre": "SISTEMAS OPERATIVOS II",
        "ciclo": 7,
        "area": "TI",
    },
    {"codigo": "SI-783", "nombre": "BASE DE DATOS II", "ciclo": 7, "area": "BD"},
    {
        "codigo": "SI-784",
        "nombre": "CALIDAD Y PRUEBAS DE SOFTWARE",
        "ciclo": 7,
        "area": "SOFTWARE",
    },
    {
        "codigo": "SI-785",
        "nombre": "GESTIÓN DE PROYECTOS DE TI",
        "ciclo": 7,
        "area": "GESTION",
    },
    {
        "codigo": "SI-786",
        "nombre": "PROGRAMACIÓN WEB I",
        "ciclo": 7,
        "area": "PROGRAMACION",
    },
    # Ciclo 8
    {
        "codigo": "SI-881",
        "nombre": "INTELIGENCIA ARTIFICIAL",
        "ciclo": 8,
        "area": "IA",
    },
    {
        "codigo": "SI-882",
        "nombre": "REDES Y COMUNICACIÓN DE DATOS I",
        "ciclo": 8,
        "area": "REDES",
    },
    {
        "codigo": "SI-883",
        "nombre": "SOLUCIONES MÓVILES I",
        "ciclo": 8,
        "area": "SOFTWARE",
    },
    {
        "codigo": "SI-884",
        "nombre": "ESTADÍSTICA INFERENCIAL Y ANÁLISIS DE DATOS",
        "ciclo": 8,
        "area": "CIENCIAS",
    },
    {
        "codigo": "SI-885",
        "nombre": "INTELIGENCIA DE NEGOCIOS",
        "ciclo": 8,
        "area": "TI",
    },
    {
        "codigo": "SI-886",
        "nombre": "PLANEAMIENTO ESTRATÉGICO DE TI",
        "ciclo": 8,
        "area": "GESTION",
    },
    # Ciclo 9
    {
        "codigo": "SI-981",
        "nombre": "TALLER DE TESIS I",
        "ciclo": 9,
        "area": "INVESTIGACION",
    },
    {
        "codigo": "SI-982",
        "nombre": "PROGRAMACIÓN WEB II",
        "ciclo": 9,
        "area": "PROGRAMACION",
    },
    {
        "codigo": "SI-983",
        "nombre": "CONSTRUCCIÓN DE SOFTWARE I",
        "ciclo": 9,
        "area": "SOFTWARE",
    },
    {
        "codigo": "SI-984",
        "nombre": "REDES Y COMUNICACIÓN DE DATOS II",
        "ciclo": 9,
        "area": "REDES",
    },
    {
        "codigo": "SI-985",
        "nombre": "GESTIÓN DE CONFIGURACIÓN DE SOFTWARE",
        "ciclo": 9,
        "area": "SOFTWARE",
    },
    {
        "codigo": "SI-989",
        "nombre": "MACHINE LEARNING",
        "ciclo": 9,
        "area": "IA",
    },
    # Ciclo 10
    {
        "codigo": "SI-080",
        "nombre": "TALLER DE TESIS II / TRABAJO DE INVESTIGACIÓN",
        "ciclo": 10,
        "area": "INVESTIGACION",
    },
    {
        "codigo": "SI-082",
        "nombre": "SEGURIDAD DE TECNOLOGÍA DE INFORMACIÓN",
        "ciclo": 10,
        "area": "SEGURIDAD",
    },
    {
        "codigo": "SI-083",
        "nombre": "CONSTRUCCIÓN DE SOFTWARE II",
        "ciclo": 10,
        "area": "SOFTWARE",
    },
    {
        "codigo": "SI-084",
        "nombre": "AUDITORÍA DE SISTEMAS",
        "ciclo": 10,
        "area": "TI",
    },
    {
        "codigo": "SI-085",
        "nombre": "TALLER DE EMPRENDIMIENTO Y LIDERAZGO",
        "ciclo": 10,
        "area": "GESTION",
    },
    {
        "codigo": "SI-086",
        "nombre": "GERENCIA DE TECNOLOGÍAS DE INFORMACIÓN",
        "ciclo": 10,
        "area": "GESTION",
    },
]

# Vocabulario controlado para el TF-IDF
POOL_TAGS = [
    "python",
    "c_sharp",
    "java",
    "javascript",
    "react",
    "sql",
    "postgresql",
    "algebra",
    "geometria_analitica",
    "calculo_diferencial",
    "calculo_integral",
    "logica_proposicional",
    "algoritmos",
    "estructuras_datos",
    "grafos",
    "poo",
    "patrones_diseno",
    "arquitectura_limpia",
    "scrum",
    "git",
    "redes_tcp_ip",
    "ciberseguridad",
    "machine_learning",
    "deep_learning",
    "redaccion_academica",
    "diagramas_uml",
    "gestion_proyectos",
]

FRANJAS_HORARIAS = [
    "08:00 - 10:30",
    "10:30 - 12:10",
    "10:30 - 13:00",
    "15:00 - 16:40",
    "16:40 - 18:20",
    "18:20 - 20:00",
    "20:00 - 21:40",
]
DIAS_SEMANA = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado"]

# Nombres y Apellidos peruanos para realismo
NOMBRES = [
    "Carlos",
    "Juan",
    "Brayan",
    "Luis",
    "Jorge",
    "Diego",
    "Kevin",
    "Jhon",
    "Renzo",
    "Rodrigo",
    "Maria",
    "Ana",
    "Lucia",
    "Valeria",
    "Fiorella",
    "Diana",
    "Gabriela",
    "Camila",
    "Andrea",
    "Deysy",
]
APELLIDOS = [
    "Mamani",
    "Quispe",
    "Condori",
    "Flores",
    "Chura",
    "Calizaya",
    "Vargas",
    "Ramos",
    "Ticona",
    "Vilca",
    "Perez",
    "Rodriguez",
    "Huanca",
    "Rivera",
    "Mendoza",
    "Garcia",
    "Castro",
    "Cruz",
    "Gomez",
    "Silva",
]


def inicializar_bd(cursor):
    """Crea el esquema relacional en SQLite."""
    cursor.execute("DROP TABLE IF EXISTS disponibilidad")
    cursor.execute("DROP TABLE IF EXISTS kardex_notas")
    cursor.execute("DROP TABLE IF EXISTS estudiantes")
    cursor.execute("DROP TABLE IF EXISTS cursos")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cursos (
        codigo TEXT PRIMARY KEY,
        nombre TEXT NOT NULL,
        ciclo INTEGER NOT NULL,
        area TEXT NOT NULL
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estudiantes (
        id INTEGER PRIMARY KEY,
        codigo_estudiante TEXT UNIQUE NOT NULL,
        nombres TEXT NOT NULL,
        apellidos TEXT NOT NULL,
        correo_institucional TEXT NOT NULL,
        ciclo_actual INTEGER NOT NULL,
        rol TEXT NOT NULL,
        max_cupos_mentor INTEGER DEFAULT 0,
        sesiones_activas INTEGER DEFAULT 0,
        es_nuevo_mentor INTEGER DEFAULT 0,
        tags_interes TEXT NOT NULL
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS kardex_notas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_estudiante INTEGER NOT NULL,
        codigo_curso TEXT NOT NULL,
        nombre_curso TEXT NOT NULL,
        nota REAL NOT NULL,
        condicion TEXT NOT NULL,
        FOREIGN KEY (id_estudiante) REFERENCES estudiantes(id),
        FOREIGN KEY (codigo_curso) REFERENCES cursos(codigo)
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS disponibilidad (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_estudiante INTEGER NOT NULL,
        dia TEXT NOT NULL,
        franja_horaria TEXT NOT NULL,
        FOREIGN KEY (id_estudiante) REFERENCES estudiantes(id)
    )""")


def poblar_datos(cursor, total_estudiantes=350):
    """Genera 350 estudiantes con kardex, roles y disponibilidad coherentes."""
    # 1. Insertar Catálogo de Cursos
    for c in CURSOS_EPIS:
        cursor.execute(
            "INSERT OR REPLACE INTO cursos VALUES (?, ?, ?, ?)",
            (c["codigo"], c["nombre"], c["ciclo"], c["area"]),
        )

    estudiantes_json = []

    # Cohorte exacta para entorno real piloto EPIS-UPT:
    # 40 Mentores (10 por cada ciclo avanzado: VII, VIII, IX, X)
    # 310 Tutorados (60 en Ciclo 1, 60 en Ciclo 2, 60 en Ciclo 3, 60 en Ciclo 4, 35 en Ciclo 5, 35 en Ciclo 6)
    perfiles = []
    for c_mentor in [7, 8, 9, 10]:
        for _ in range(10):
            perfiles.append(("MENTOR", c_mentor))

    for _ in range(60):
        perfiles.append(("TUTORADO", 1))
    for _ in range(60):
        perfiles.append(("TUTORADO", 2))
    for _ in range(60):
        perfiles.append(("TUTORADO", 3))
    for _ in range(60):
        perfiles.append(("TUTORADO", 4))
    for _ in range(35):
        perfiles.append(("TUTORADO", 5))
    for _ in range(35):
        perfiles.append(("TUTORADO", 6))

    random.shuffle(perfiles)

    for i, (rol, ciclo) in enumerate(perfiles, start=1):

        # Año de ingreso estimado según ciclo (2026-II)
        ano_ingreso = 2026 - (ciclo // 2)
        codigo_est = f"{ano_ingreso}-{10000 + i}"
        nombres = random.choice(NOMBRES)
        apellidos = f"{random.choice(APELLIDOS)} {random.choice(APELLIDOS)}"
        correo = f"{codigo_est}@virtual.upt.pe"

        # Variables de mentor
        max_cupos = random.randint(2, 4) if rol == "MENTOR" else 0
        sesiones_activas = (
            random.randint(0, max_cupos - 1) if rol == "MENTOR" else 0
        )
        es_nuevo = (
            1
            if (rol == "MENTOR" and random.random() < 0.35)
            else (0 if rol == "MENTOR" else 0)
        )

        # Tags de especialidad/interés (TF-IDF input)
        k_tags = random.randint(4, 7)
        tags_seleccionados = random.sample(POOL_TAGS, k_tags)
        tags_str = " ".join(tags_seleccionados)

        cursor.execute(
            """
            INSERT INTO estudiantes (
                id, codigo_estudiante, nombres, apellidos, correo_institucional,
                ciclo_actual, rol, max_cupos_mentor, sesiones_activas, es_nuevo_mentor, tags_interes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                i,
                codigo_est,
                nombres,
                apellidos,
                correo,
                ciclo,
                rol,
                max_cupos,
                sesiones_activas,
                es_nuevo,
                tags_str,
            ),
        )

        # 2. Generar Kardex de Notas histórico
        kardex_list = []
        # Cursos de ciclos ya completados
        cursos_previos = [c for c in CURSOS_EPIS if c["ciclo"] < ciclo]
        for c in cursos_previos:
            # Los mentores tienen notas altas (14 a 20) en cursos clave
            if rol == "MENTOR":
                nota = random.randint(14, 20)
                condicion = "APROBADO"
            else:
                # Tutorados y estudiantes regulares tienen variación normal
                prob_aprobado = random.random()
                if prob_aprobado > 0.15:
                    nota = random.randint(11, 18)
                    condicion = "APROBADO"
                else:
                    nota = random.randint(5, 10)
                    condicion = "DESAPROBADO"

            cursor.execute(
                """
                INSERT INTO kardex_notas (id_estudiante, codigo_curso, nombre_curso, nota, condicion)
                VALUES (?, ?, ?, ?, ?)
            """,
                (i, c["codigo"], c["nombre"], nota, condicion),
            )

            kardex_list.append({
                "codigo_curso": c["codigo"],
                "nombre_curso": c["nombre"],
                "nota": nota,
                "condicion": condicion,
            })

        # Cursos del ciclo actual (en curso)
        cursos_actuales = [c for c in CURSOS_EPIS if c["ciclo"] == ciclo]
        for c in cursos_actuales:
            nota_parcial = round(random.uniform(08.0, 16.0), 1)
            cursor.execute(
                """
                INSERT INTO kardex_notas (id_estudiante, codigo_curso, nombre_curso, nota, condicion)
                VALUES (?, ?, ?, ?, ?)
            """,
                (i, c["codigo"], c["nombre"], nota_parcial, "CURSANDO"),
            )

            kardex_list.append({
                "codigo_curso": c["codigo"],
                "nombre_curso": c["nombre"],
                "nota": nota_parcial,
                "condicion": "CURSANDO",
            })

        # 3. Generar Disponibilidad Horaria según ciclo/turno
        disp_list = []
        if rol == "TUTORADO":
            pool_franjas = [
                "15:00 - 16:40",
                "16:40 - 18:20",
                "18:20 - 20:00",
                "20:00 - 21:40",
                "08:00 - 10:30",
                "10:30 - 13:00",
            ]
        else:
            pool_franjas = [
                "08:00 - 10:30",
                "10:30 - 12:10",
                "10:30 - 13:00",
                "15:00 - 16:40",
            ]

        # Seleccionar 3 días con 1 o 2 franjas
        dias_disponibles = random.sample(DIAS_SEMANA, 3)
        for dia in dias_disponibles:
            franja = random.choice(pool_franjas)
            cursor.execute(
                """
                INSERT INTO disponibilidad (id_estudiante, dia, franja_horaria)
                VALUES (?, ?, ?)
            """,
                (i, dia, franja),
            )
            disp_list.append({"dia": dia, "franja_horaria": franja})

        # Estructura JSON para respaldo directo
        estudiantes_json.append({
            "id": i,
            "codigo_estudiante": codigo_est,
            "nombres": nombres,
            "apellidos": apellidos,
            "correo_institucional": correo,
            "ciclo_actual": ciclo,
            "rol": rol,
            "max_cupos_mentor": max_cupos,
            "sesiones_activas": sesiones_activas,
            "es_nuevo_mentor": bool(es_nuevo),
            "tags_interes": tags_seleccionados,
            "disponibilidad": disp_list,
            "kardex": kardex_list,
        })

    return estudiantes_json


def main():
    # Resolver la carpeta data/ de forma independiente del directorio de ejecución
    if os.path.basename(os.getcwd()) == "scripts":
        data_dir = os.path.abspath(os.path.join(os.getcwd(), "..", "data"))
    else:
        data_dir = os.path.abspath(os.path.join(os.getcwd(), "data"))
    os.makedirs(data_dir, exist_ok=True)

    db_filename = os.path.join(data_dir, "epis_mentorias.db")
    json_filename = os.path.join(data_dir, "epis_mentorias.json")

    conn = sqlite3.connect(db_filename)
    cursor = conn.cursor()

    inicializar_bd(cursor)
    dataset = poblar_datos(cursor, total_estudiantes=350)

    conn.commit()
    conn.close()

    # Guardar en archivo JSON estructurado
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    print("=========================================================")
    print(" BASE DE DATOS SINTÉTICA EPIS-UPT GENERADA CON ÉXITO")
    print("=========================================================")
    print(f"-> Base de datos SQLite creada: {db_filename}")
    print(f"-> Archivo JSON exportado:       {json_filename}")
    print(f"-> Total de estudiantes:        {len(dataset)}")
    print(
        f"-> Total mentores (VII - X):    {sum(1 for e in dataset if e['rol'] == 'MENTOR')}"
    )
    print(
        f"-> Total tutorados (I - VI):    {sum(1 for e in dataset if e['rol'] == 'TUTORADO')}"
    )


if __name__ == "__main__":
    main()