"""
Script para generar el cuaderno Jupyter visualizador_algoritmo.ipynb
conforme a la especificación oficial de nbformat v4.
"""

import json

notebook = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# 🎓 Sistema Web P2P de Mentorías Académicas - EPIS UPT (2026-II)\n",
                "## Cuaderno Interactivo y Visualizador del Algoritmo de Recomendación\n",
                "\n",
                "Este cuaderno documenta e ilustra de manera estructurada y reproducible el funcionamiento del **motor de recomendación híbrido** en sus 5 fases metodológicas, validado sobre la cohorte sintética experimental de **350 estudiantes** (40 mentores avanzados y 310 tutorados) de la EPIS-UPT.\n",
                "\n",
                "---\n",
                "### Formulación Matemática del Modelo:\n",
                "$$\\text{PuntajeFinal}(m) = \\alpha \\cdot \\text{SimCoseno}(u, m) - \\beta \\cdot \\left(\\frac{\\text{SesionesActivas}(m)}{\\text{MaxCupos}(m)}\\right) + \\gamma \\cdot \\text{BonoNuevo}(m)$$\n",
                "\n",
                "Donde los pesos definidos en `system_rules.json` son:\n",
                "* $\\alpha = 0.70$: Afinidad semántica por coseno.\n",
                "* $\\beta = 0.20$: Penalización por saturación de cupos.\n",
                "* $\\gamma = 0.10$: Bono experimental de oportunidad para mentores novatos."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import os\n",
                "import sys\n",
                "import sqlite3\n",
                "import numpy as np\n",
                "import pandas as pd\n",
                "import matplotlib.pyplot as plt\n",
                "\n",
                "# Configurar rutas relativas para importar el motor y conectar a la BD\n",
                "BASE_DIR = os.path.abspath('..') if os.path.basename(os.getcwd()) == 'notebooks' else os.path.abspath('.')\n",
                "SRC_DIR = os.path.join(BASE_DIR, 'src')\n",
                "if SRC_DIR not in sys.path:\n",
                "    sys.path.insert(0, SRC_DIR)\n",
                "\n",
                "from motor_recomendacion import (\n",
                "    cargar_reglas_sistema,\n",
                "    filtrar_mentores_sql,\n",
                "    calcular_similitud_contenido,\n",
                "    aplicar_reranking_equidad,\n",
                "    recomendar_mentores,\n",
                "    resolver_ruta_bd,\n",
                ")\n",
                "\n",
                "DB_PATH = resolver_ruta_bd(os.path.join(BASE_DIR, 'data', 'epis_mentorias.db'))\n",
                "print('✓ Dependencias y motor de recomendación cargados exitosamente.')"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 1. Inspección de la Cohorte Piloto (350 Alumnos)\n",
                "Consultamos la base de datos relacional `epis_mentorias.db` para verificar la distribución de estudiantes entre mentores avanzados (Ciclos VII-X) y tutorados (Ciclos I-VI)."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "conn = sqlite3.connect(DB_PATH)\n",
                "df_alumnos = pd.read_sql_query(\"\"\"\n",
                "    SELECT ciclo_actual, rol, COUNT(*) as cantidad\n",
                "    FROM estudiantes\n",
                "    GROUP BY ciclo_actual, rol\n",
                "    ORDER BY ciclo_actual\n",
                "\"\"\", conn)\n",
                "conn.close()\n",
                "\n",
                "pivot_df = df_alumnos.pivot(index=\"ciclo_actual\", columns=\"rol\", values=\"cantidad\").fillna(0)\n",
                "\n",
                "fig, ax = plt.subplots(figsize=(8, 4))\n",
                "pivot_df.plot(kind=\"bar\", stacked=True, ax=ax, color={\"MENTOR\": \"#1E40AF\", \"TUTORADO\": \"#93C5FD\"})\n",
                "ax.set_title(\"Distribución de la Cohorte EPIS-UPT por Ciclo y Rol (Total: 350)\")\n",
                "ax.set_xlabel(\"Ciclo Académico\")\n",
                "ax.set_ylabel(\"Cantidad de Estudiantes\")\n",
                "ax.grid(axis=\"y\", linestyle=\"--\", alpha=0.5)\n",
                "plt.tight_layout()\n",
                "plt.show()\n",
                "\n",
                "display(df_alumnos.groupby(\"rol\")[\"cantidad\"].sum().to_frame(\"Total por Rol\"))"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 2. FASE 1 - Filtrado Determinista (SQL Hard Rules)\n",
                "Poda relacional directa en SQLite para seleccionar solo mentores que:\n",
                "1. Tengan rol `MENTOR`.\n",
                "2. Hayan aprobado la materia con nota $\\ge 14.0$.\n",
                "3. Coincidan en el día y franja horaria solicitados.\n",
                "4. Tengan cupos operativos libres (`sesiones_activas < max_cupos_mentor`)."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "curso_objetivo = \"INE-186\"  # MATEMÁTICA I (Ciclo 1)\n",
                "dia_objetivo = \"Sabado\"\n",
                "franja_objetivo = \"08:00 - 10:30\"\n",
                "nota_minima = 14.0\n",
                "\n",
                "mentores_aptos = filtrar_mentores_sql(\n",
                "    codigo_curso=curso_objetivo,\n",
                "    dia=dia_objetivo,\n",
                "    franja_horaria=franja_objetivo,\n",
                "    nota_minima=nota_minima,\n",
                "    db_path=DB_PATH\n",
                ")\n",
                "\n",
                "df_fase1 = pd.DataFrame([\n",
                "    {\n",
                "        \"ID\": m[0],\n",
                "        \"Mentor\": f\"{m[1]} {m[2]}\",\n",
                "        \"Ciclo\": m[3],\n",
                "        \"Nota Curso\": m[8],\n",
                "        \"Sesiones\": m[5],\n",
                "        \"Max Cupos\": m[6],\n",
                "        \"Saturación (%)\": round((m[5] / m[6]) * 100, 1),\n",
                "        \"Es Nuevo\": bool(m[7]),\n",
                "        \"Tags\": m[4]\n",
                "    }\n",
                "    for m in mentores_aptos\n",
                "])\n",
                "\n",
                "print(f\"Candidatos que superaron el Filtro Duro SQL: {len(df_fase1)}\")\n",
                "display(df_fase1.head(10))"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 3. FASE 2 - Espacio Vectorial y Similitud de Coseno (TF-IDF)\n",
                "Vectorización de los tags de necesidades del tutorado y cálculo de la proyección angular con respecto a los mentores candidatos."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "tags_tutorado = \"calculo_diferencial algebra logica_proposicional\"\n",
                "textos_mentores = [m[4] for m in mentores_aptos]\n",
                "nombres_mentores = [f\"{m[1]} {m[2]}\" for m in mentores_aptos]\n",
                "\n",
                "similitudes = calcular_similitud_contenido(tags_tutorado, textos_mentores)\n",
                "\n",
                "import math\n",
                "df_fase2 = pd.DataFrame({\n",
                "    \"Mentor\": nombres_mentores,\n",
                "    \"Similitud Coseno (cos θ)\": [round(float(s), 4) for s in similitudes],\n",
                "    \"Ángulo θ (Grados)\": [f\"{math.degrees(math.acos(max(0.0, min(1.0, float(s))))):.1f}°\" for s in similitudes],\n",
                "}).sort_values(by=\"Similitud Coseno (cos θ)\", ascending=False)\n",
                "\n",
                "display(df_fase2)\n",
                "\n",
                "# Diagrama Polar de Vectores Angulares (Tutorado en 0° vs. Mentores)\n",
                "fig_polar, ax_pol = plt.subplots(figsize=(7, 7), subplot_kw={\"projection\": \"polar\"})\n",
                "ax_pol.set_thetamin(0)\n",
                "ax_pol.set_thetamax(90)\n",
                "ax_pol.set_ylim(0, 1.25)\n",
                "ax_pol.annotate('', xy=(0, 1.05), xytext=(0, 0), arrowprops=dict(facecolor='#DC2626', width=2.5, headwidth=9))\n",
                "ax_pol.text(0, 1.15, 'TUTORADO (Vector u | θ=0°)', color='#DC2626', fontweight='bold', ha='center')\n",
                "\n",
                "colores = ['#10B981', '#2563EB', '#8B5CF6', '#F59E0B', '#06B6D4', '#EC4899', '#64748B']\n",
                "for idx, (sim, nom) in enumerate(zip(similitudes, nombres_mentores)):\n",
                "    sim_v = max(0.0, min(1.0, float(sim)))\n",
                "    th_r = math.acos(sim_v)\n",
                "    th_d = math.degrees(th_r)\n",
                "    c = colores[idx % len(colores)]\n",
                "    r = 0.90 + 0.15 * sim_v\n",
                "    ax_pol.annotate('', xy=(th_r, r), xytext=(0, 0), arrowprops=dict(facecolor=c, width=1.8, headwidth=7, alpha=0.85))\n",
                "    nom_c = nom.split()[0] + ' ' + nom.split()[1] if len(nom.split()) > 1 else nom\n",
                "    ax_pol.text(th_r, r + 0.08, f\"{nom_c}\\n(θ={th_d:.1f}°, cos={sim_v:.3f})\", color=c, fontsize=8, ha='center', fontweight='bold')\n",
                "\n",
                "ax_pol.set_title(f\"Espacio Vectorial Angular: Proyección respecto al Tutorado ({curso_objetivo})\", fontsize=11, pad=18, fontweight='bold')\n",
                "ax_pol.grid(True, linestyle='--', alpha=0.6)\n",
                "plt.tight_layout()\n",
                "plt.show()"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 4. FASE 4 - Load-Aware Re-ranking\n",
                "Ajuste del puntaje final aplicando penalización por saturación operativa y bonificación para mentores novatos."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "reglas = cargar_reglas_sistema()\n",
                "pesos = reglas.get(\"pesos_algoritmo\", {})\n",
                "alpha = float(pesos.get(\"alpha_coseno\", 0.70))\n",
                "beta = float(pesos.get(\"beta_saturacion\", 0.20))\n",
                "gamma = float(pesos.get(\"gamma_bono_nuevo\", 0.10))\n",
                "\n",
                "ranking = aplicar_reranking_equidad(\n",
                "    mentores_candidatos=mentores_aptos,\n",
                "    similitudes=similitudes,\n",
                "    alpha=alpha,\n",
                "    beta=beta,\n",
                "    gamma=gamma\n",
                ")\n",
                "\n",
                "df_ranking = pd.DataFrame(ranking)[[\n",
                "    \"id\", \"mentor\", \"ciclo\", \"nota_en_curso\", \"similitud_coseno\",\n",
                "    \"sesiones_activas\", \"max_cupos\", \"es_nuevo\", \"puntaje_final\"\n",
                "]]\n",
                "\n",
                "display(df_ranking)"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 5. FASE 5 - Selección Final Top-K\n",
                "Entrega asistida de los $K=3$ mejores candidatos para su presentación en el frontend web interactivo."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "top_k_final = recomendar_mentores(\n",
                "    codigo_curso_solicitado=curso_objetivo,\n",
                "    tags_estudiante=tags_tutorado,\n",
                "    dia_preferido=dia_objetivo,\n",
                "    franja_preferida=franja_objetivo,\n",
                "    top_k=3,\n",
                "    db_path=DB_PATH\n",
                ")\n",
                "\n",
                "print(\"=\" * 65)\n",
                "print(f\" MENTORES RECOMENDADOS (TOP 3) PARA {curso_objetivo}\")\n",
                "print(\"=\" * 65)\n",
                "for r, m in enumerate(top_k_final, start=1):\n",
                "    print(f\"Rank #{r}: {m['mentor']} (Ciclo {m['ciclo']})\")\n",
                "    print(f\"         Nota en Curso:    {m['nota_en_curso']}\")\n",
                "    print(f\"         Similitud Coseno: {m['similitud_coseno']}\")\n",
                "    print(f\"         Score Final:      {m['puntaje_final']}\")\n",
                "    print(f\"         Competencias:     {m['tags']}\\n\")"
            ]
        }
    ],
    "metadata": {
        "language_info": {
            "name": "python",
            "version": "3.10"
        },
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 4
}

import os
out_dir = os.path.join("notebooks") if os.path.basename(os.getcwd()) != "notebooks" else "."
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "visualizador_algoritmo.ipynb")

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=2, ensure_ascii=False)

print(f"[OK] {out_path} generado con exito.")
