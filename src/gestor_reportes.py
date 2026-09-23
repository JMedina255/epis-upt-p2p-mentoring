"""
====================================================================================================
MÓDULO DE GESTIÓN, AUDITORÍA Y PERSISTENCIA DE REPORTES EXPERIMENTALES (EPIS-UPT 2026)
Guarda y administra reportes de recomendaciones en formato JSON y Markdown.
====================================================================================================
"""

import datetime
import json
import math
import os
import re
from typing import Any, Dict, List, Optional, Tuple

DIRECTORIO_REPORTES: str = "reportes"


def obtener_directorio_reportes() -> str:
    """Resuelve la ruta absoluta al directorio reportes/ en la raíz del proyecto."""
    candidatas = [
        os.path.abspath("reportes"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reportes")),
    ]
    for c in candidatas:
        if os.path.isdir(c):
            return c
    ruta_default = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reportes"))
    os.makedirs(ruta_default, exist_ok=True)
    return ruta_default


def asegurar_directorio_reportes() -> str:
    """Garantiza la existencia del directorio de almacenamiento de reportes."""
    directorio = obtener_directorio_reportes()
    os.makedirs(directorio, exist_ok=True)
    return directorio


def generar_markdown_reporte(datos: Dict[str, Any]) -> str:
    """Convierte el diccionario estructurado del reporte en un documento Markdown académico."""
    tut = datos.get("tutorado", {})
    sol = datos.get("solicitud", {})
    cfg = datos.get("configuracion_algoritmo", {})
    pesos = cfg.get("pesos", {})
    fase1 = datos.get("fase1_filtro_sql", {})
    fase2 = datos.get("fase2_espacio_vectorial", {})
    fase4 = datos.get("fase4_reranking_equidad", {})
    topk = datos.get("top_k_recomendados", [])
    telemetria = datos.get("telemetria", {})

    md = []
    md.append("# 📄 Reporte Experimental de Inferencia Algorítmica P2P")
    md.append(f"**Institución:** EPIS - Universidad Privada de Tacna | **Semestre Académico:** 2026-II")
    md.append(f"**ID de Reporte:** `{datos.get('id_reporte', 'N/A')}` | **Fecha y Hora:** `{datos.get('fecha_generacion', 'N/A')}`")
    md.append(f"**Tiempo de Inferencia:** `{telemetria.get('tiempo_inferencia_ms', 0.0):.2f} ms`\n")
    md.append("---\n")

    # 1. Perfil del Estudiante
    md.append("## 1. Perfil del Estudiante Tutorado")
    md.append(f"* **Nombre Completo:** {tut.get('nombre_completo', 'N/A')} (Ciclo {tut.get('ciclo', 'N/A')})")
    md.append(f"* **Código Estudiantil:** `{tut.get('codigo', 'N/A')}` | **Correo:** `{tut.get('correo', 'N/A')}`")
    md.append(f"* **Áreas de Interés Registradas:** `{tut.get('tags', 'N/A')}`")
    md.append(f"* **Horarios Registrados en Intranet:** {', '.join(tut.get('disponibilidad', []))}\n")

    # 2. Solicitud de la Sesión
    md.append("## 2. Requerimientos de la Solicitud de Mentoría")
    md.append(f"* **Curso Objetivo:** `{sol.get('codigo_curso', 'N/A')}` - {sol.get('nombre_curso', 'N/A')}")
    md.append(f"* **Calificación Actual del Alumno:** `{sol.get('nota_tutorado', 0.0):.1f}` (Condición: **{sol.get('condicion_tutorado', 'N/A')}**)")
    md.append(f"* **Día y Franja Horaria Requerida:** `{sol.get('dia', 'N/A')} ({sol.get('franja_horaria', 'N/A')})`")
    md.append(f"* **Tags de Duda / Consulta:** `{sol.get('tags_consulta', 'N/A')}`\n")

    # 3. Parámetros del Algoritmo
    md.append("## 3. Calibración de Parámetros del Modelo")
    md.append(f"* **Afinidad Semántica ($\\alpha$):** `{pesos.get('alpha', 0.70):.2f}`")
    md.append(f"* **Penalización por Saturación ($\\beta$):** `{pesos.get('beta', 0.20):.2f}`")
    md.append(f"* **Bono Mentor Nuevo ($\\gamma$):** `{pesos.get('gamma', 0.10):.2f}`")
    md.append(f"* **Umbral de Nota Mínima:** `$\\ge {cfg.get('nota_minima_mentor', 14.0):.1f}$`")
    md.append(f"* **Top-K Solicitado:** `{cfg.get('top_k', 3)}`\n")

    # 4. Fase 1: SQL
    md.append("## 4. Fase 1: Poda Determinista (SQL Hard Rules)")
    md.append(f"De la cohorte de 40 mentores avanzados, **{fase1.get('total_candidatos_aptos', 0)}** cumplieron simultáneamente las 4 reglas duras (rol MENTOR, nota $\\ge 14.0$, disponibilidad y cupos libres).\n")
    
    mentores_sql = fase1.get("mentores_aptos", [])
    if mentores_sql:
        md.append("| ID | Mentor | Ciclo | Nota en Curso | Sesiones / Cupos | Saturación (%) | Es Nuevo |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for m in mentores_sql:
            sat_pct = round((m.get("sesiones", 0) / m.get("max_cupos", 1)) * 100, 1) if m.get("max_cupos", 1) > 0 else 100.0
            nuevo_str = "Sí (+Bono)" if m.get("es_nuevo") else "No"
            md.append(f"| {m.get('id')} | {m.get('mentor')} | {m.get('ciclo')} | {m.get('nota_en_curso')} | {m.get('sesiones')}/{m.get('max_cupos')} | {sat_pct}% | {nuevo_str} |")
        md.append("")

    # 5. Fase 2: Similitud y Ángulos
    md.append("## 5. Fase 2: Modelado Semántico y Geometría Vectorial (TF-IDF + Coseno)")
    md.append("Cálculo angular en coordenadas polares con el vector del estudiante como referencia ($\\theta = 0^\\circ$):\n")
    
    angulos = fase2.get("mediciones_angulares", [])
    if angulos:
        md.append("| Mentor | Similitud Coseno ($\\cos\\theta$) | Ángulo $\\theta$ (Grados) | Interpretación Geométrica | Tags Coincidentes |")
        md.append("| :--- | :--- | :--- | :--- | :--- |")
        for a in angulos:
            men = a.get("mentor") or a.get("Mentor", "N/A")
            sim_val = a.get("similitud_coseno") if a.get("similitud_coseno") is not None else a.get("Similitud Coseno (cos θ)", 0.0)
            try:
                sim_str = f"{float(sim_val):.4f}"
            except (ValueError, TypeError):
                sim_str = str(sim_val)
            ang = a.get("angulo_grados") or a.get("Ángulo θ (Grados)", "N/A")
            interp = a.get("interpretacion") or a.get("Interpretación Geométrica", "N/A")
            tags_c = a.get("tags_coincidentes") or a.get("Tags Coincidentes", "N/A")
            md.append(f"| {men} | {sim_str} | {ang} | {interp} | {tags_c} |")
        md.append("")

    # 6. Fase 4: Load-Aware Re-ranking
    md.append("## 6. Fase 4: Re-ranking Sensible a la Carga (Load-Aware Re-ranking)")
    md.append("Fórmula aplicada:")
    md.append(f"$$\\text{{ScoreFinal}}(m) = {pesos.get('alpha', 0.70):.2f} \\cdot \\text{{SimCoseno}} - {pesos.get('beta', 0.20):.2f} \\cdot \\text{{Saturacion}} + {pesos.get('gamma', 0.10):.2f} \\cdot \\text{{BonoNuevo}}$$\n")
    
    rerank = fase4.get("desglose_calibracion", [])
    if rerank:
        md.append("| Rank Final | Rank Coseno | Cambio | Mentor | Sim Coseno | Término Semántico | Término Saturación | Término Bono | Score Final |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for r in rerank:
            rf = r.get("rank_final") or r.get("Rank Final", "N/A")
            rc = r.get("rank_coseno") or r.get("Rank Coseno Puro", "N/A")
            chg = r.get("cambio_pos") or r.get("Cambio de Posición", "=")
            men = r.get("mentor") or r.get("Mentor", "N/A")

            sim_val = r.get("similitud_coseno") if r.get("similitud_coseno") is not None else r.get("Sim Coseno (TF-IDF)", 0.0)
            try:
                sim_str = f"{float(sim_val):.4f}"
            except (ValueError, TypeError):
                sim_str = str(sim_val)

            # Términos del score con soporte para claves canónicas y nombres de columnas Streamlit
            tsim = r.get("term_sim")
            if tsim is None:
                for k, v in r.items():
                    if "·sim" in k.lower() or "afinidad" in k.lower():
                        tsim = v
                        break
            try:
                tsim_val = float(tsim or 0.0)
            except (ValueError, TypeError):
                tsim_val = 0.0

            tsat = r.get("term_sat")
            if tsat is None:
                for k, v in r.items():
                    if "·sat" in k.lower() or "penaliz" in k.lower():
                        tsat = v
                        break
            try:
                tsat_val = float(tsat or 0.0)
            except (ValueError, TypeError):
                tsat_val = 0.0

            tbono = r.get("term_bono")
            if tbono is None:
                for k, v in r.items():
                    if "·bono" in k.lower() or "novedad" in k.lower():
                        tbono = v
                        break
            try:
                tbono_val = float(tbono or 0.0)
            except (ValueError, TypeError):
                tbono_val = 0.0

            sc = r.get("puntaje_final") if r.get("puntaje_final") is not None else r.get("Puntaje Final", 0.0)
            try:
                sc_str = f"{float(sc):.4f}"
            except (ValueError, TypeError):
                sc_str = str(sc)

            md.append(
                f"| #{rf} | #{rc} | {chg} | "
                f"{men} | {sim_str} | +{tsim_val:.4f} | "
                f"{tsat_val:.4f} | +{tbono_val:.4f} | **{sc_str}** |"
            )
        md.append("")

    # 7. Selección Final Top-K
    md.append(f"## 7. Selección Final Top-{len(topk)} Entregada")
    for idx, cand in enumerate(topk, start=1):
        md.append(f"### Candidato #{idx}: {cand.get('mentor')} (Ciclo {cand.get('ciclo')})")
        md.append(f"* **Puntaje Final Ponderado:** `{cand.get('puntaje_final'):.4f}`")
        md.append(f"* **Calificación Obtenida en {sol.get('codigo_curso')}:** `{cand.get('nota_en_curso')}` (Brecha: `+{cand.get('nota_en_curso', 0.0) - sol.get('nota_tutorado', 0.0):.1f} pts`)")
        md.append(f"* **Similitud Coseno:** `{cand.get('similitud_coseno'):.4f}` (Ángulo: `{cand.get('angulo_grados', 'N/A')}`)")
        md.append(f"* **Ocupación de Cupos:** `{cand.get('sesiones_activas', 0)} / {cand.get('max_cupos', 0)}`")
        md.append(f"* **Competencias Declaradas:** `{cand.get('tags', 'N/A')}`\n")

    md.append("---\n*Reporte emitido conforme a las directivas del sistema y la Ley N° 29733 de Protección de Datos Personales.*")
    return "\n".join(md)


def guardar_reporte(datos: Dict[str, Any]) -> Tuple[str, str]:
    """Persiste el reporte en disco tanto en JSON estructurado como en Markdown.
    
    Returns:
        Tuple[str, str]: (Ruta archivo JSON, Ruta archivo Markdown)
    """
    directorio = asegurar_directorio_reportes()
    
    tut = datos.get("tutorado", {})
    sol = datos.get("solicitud", {})
    codigo_alumno = tut.get("codigo", "ALUMNO").replace("-", "")
    codigo_curso = sol.get("codigo_curso", "CURSO").replace("-", "")
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    nombre_base = f"reporte_{codigo_alumno}_{codigo_curso}_{timestamp}"
    ruta_json = os.path.join(directorio, f"{nombre_base}.json")
    ruta_md = os.path.join(directorio, f"{nombre_base}.md")

    # 1. Guardar JSON estructurado
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)

    # 2. Guardar Markdown para lectura humana
    contenido_md = generar_markdown_reporte(datos)
    with open(ruta_md, "w", encoding="utf-8") as f:
        f.write(contenido_md)

    return ruta_json, ruta_md


def listar_reportes() -> List[Dict[str, Any]]:
    """Escanea el directorio reportes/ y retorna el inventario ordenado por fecha descendente."""
    directorio = asegurar_directorio_reportes()
    archivos = [f for f in os.listdir(directorio) if f.endswith(".json")]

    lista: List[Dict[str, Any]] = []
    for arch in archivos:
        ruta = os.path.join(directorio, arch)
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                data = json.load(f)
                tut = data.get("tutorado", {})
                sol = data.get("solicitud", {})
                topk = data.get("top_k_recomendados", [])
                top1_nombre = topk[0].get("mentor", "N/A") if topk else "Sin candidatos"
                top1_score = topk[0].get("puntaje_final", 0.0) if topk else 0.0

                lista.append({
                    "archivo_json": arch,
                    "archivo_md": arch.replace(".json", ".md"),
                    "ruta_completa_json": ruta,
                    "ruta_completa_md": os.path.join(directorio, arch.replace(".json", ".md")),
                    "id_reporte": data.get("id_reporte", arch),
                    "fecha": data.get("fecha_generacion", ""),
                    "codigo_alumno": tut.get("codigo", ""),
                    "alumno": tut.get("nombre_completo", ""),
                    "ciclo": tut.get("ciclo", ""),
                    "curso": sol.get("codigo_curso", ""),
                    "nombre_curso": sol.get("nombre_curso", ""),
                    "top1_mentor": top1_nombre,
                    "top1_score": top1_score,
                })
        except Exception:
            continue

    lista.sort(key=lambda x: x["fecha"], reverse=True)
    return lista


def leer_reporte(ruta_archivo: str) -> str:
    """Lee el texto completo de un reporte."""
    if not os.path.exists(ruta_archivo):
        return ""
    with open(ruta_archivo, "r", encoding="utf-8") as f:
        return f.read()
