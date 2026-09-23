# Directivas y Reglas del Sistema para Desarrolladores y Asistentes AI
## Especificación Técnica: Sistema Web de Mentorías Académicas P2P (EPIS-UPT 2026)

Este documento establece las especificaciones técnicas obligatorias, restricciones de arquitectura, reglas de negocio y directivas de desarrollo que cualquier asistente AI o desarrollador debe acatar estrictamente al modificar código, implementar módulos o refactorizar componentes en este repositorio.

---

### 1. Alcance y Arquitectura
1. **Alcance Exclusivamente Web:** No generar componentes, vistas ni lógica para entornos móviles nativos (React Native, Flutter o Expo). La interfaz oficial de prototipado es web (Streamlit).
2. **Arquitectura Desacoplada (Two-Stage Recommendation Pipeline):**
   * **Etapa 1 (Filtrado duro en SQL):** Restricciones relacionales deterministas ejecutadas en la base de datos (calificación mínima, compatibilidad horaria, cupos disponibles).
   * **Etapa 2 (Afinidad y Calibración en Python):** Vectorización léxica (TF-IDF), cálculo de similitud angular (Coseno), ajuste por balance de carga y oportunidad (*Load-aware re-ranking*) y selección de los mejores candidatos (*Top-K*).

---

### 2. Reglas de Negocio No Negociables
1. **Asimetría de Roles:** Un estudiante de ciclos iniciales (Ciclos I al IV) no puede ser recomendado para tutorías técnicas sobre asignaturas de carrera. El filtro relacional SQL siempre debe restringir los mentores candidatos a estudiantes de ciclos avanzados con condición formal de aprobado en la materia solicitada.
2. **Calificación Mínima Aprobatoria del Mentor:** Todo mentor debe registrar una calificación de $\ge 14.0$ en la escala vigesimal $[0, 20]$ en la asignatura requerida.
3. **Privacidad de Credenciales (Ley N.° 29733):** Queda terminantemente prohibido implementar pantallas, servicios o APIs que capturen contraseñas, tokens de sesión o credenciales institucionales de la intranet universitaria UPT. Toda ingesta futura de notas se concibe mediante plantillas administrativas o lectura de reportes PDF en cliente/servidor.
4. **Modalidad y Quórum de Clases Colectivas:**
   * Quórum para sesión presencial: Exactamente 10 estudiantes.
   * Quórum para sesión virtual: Exactamente 20 estudiantes.

---

### 3. Parámetros y Configuración del Algoritmo
Los siguientes valores corresponden a la **configuración experimental actual** y **deben obtenerse dinámicamente** desde `config/system_rules.json` (Fuente Única de Verdad - SSOT), nunca declararse como constantes fijas o mágicas en el código fuente:

* `alpha_coseno` (Peso de afinidad temática de contenidos): `0.70` (rango permitido: $[0.0, 1.0]$)
* `beta_saturacion` (Penalización por saturación de carga operativa): `0.20` (rango permitido: $[0.0, 1.0]$)
* `gamma_bono_nuevo` (Bono de oportunidad para nuevos mentores): `0.10` (rango permitido: $[0.0, 1.0]$)
* `top_k_recomendados` (Cantidad de mentores presentados en la lista): `3` (entero positivo: $\ge 1$)
* `nota_minima_mentor`: `14.0` (escala vigesimal: $[0.0, 20.0]$)

---

### 4. Estándares y Convenciones Técnicas
* **Entorno y Lenguaje:** Python 3.10+ para el núcleo algorítmico y scripts de soporte.
* **Tipado Estricto:** Es mandatorio el uso de anotaciones de tipo (*type hints*) en todas las firmas de función y clases (ej. `def recomendar_mentores(...) -> List[Dict[str, Any]]:`).
* **Librerías Permitidas para Machine Learning:** Exclusivamente `scikit-learn` (`TfidfVectorizer`, `cosine_similarity`) y `numpy`. No introducir frameworks pesados de deep learning (PyTorch, TensorFlow, Transformers) salvo justificación explícita de tesis.
* **Manejo Defensivo de Excepciones:**
  * En validación de configuración: emitir `ValueError` con mensajes claros y descriptivos ante tipos incorrectos, valores fuera de rango o JSON malformado.
  * En cálculo de similitud: manejar de forma resiliente peticiones con tags vacíos o vocabularios sin términos comunes, evitando excepciones no controladas y retornando ceros vectoriales.
  * En selección Top-K: validar que `k` sea un entero positivo mayor o igual a 1.
* **Separación de Responsabilidades:**
  * Las reglas duras se resuelven en el motor SQL de la base de datos relacional.
  * La vectorización, similitud y el ajuste por carga operativa y oportunidad se resuelven en memoria en Python.

---

### 5. Reglas del Pipeline y Orden de Ejecución

Al implementar, refactorizar o extender el motor de recomendación, el flujo debe respetar estrictamente las siguientes fases:

1. **FASE 1 - FILTRADO DETERMINISTA (SQL HARD RULES):**
   * Preselección relacional con tres condiciones simultáneas: Nota $\ge 14.0$, disponibilidad en el día y franja horaria solicitados, y sesiones activas estrictamente menores al cupo máximo asignado (`sesiones_activas < max_cupos` y `max_cupos > 0`).
   * **Cortocircuito obligatorio:** Si la consulta SQL devuelve 0 candidatos aptos, el pipeline debe retornar inmediatamente una lista vacía `[]`, sin invocar la vectorización ni el re-ranking.

2. **FASE 2 - ESPACIO VECTORIAL Y CONTENIDO (TF-IDF + COSENO):**
   * Ajustar la matriz término-documento sobre los tags de intereses y temas requeridos.
   * Manejo seguro ante vocabularios disjuntos (similitud = 0.0) o textos vacíos.

3. **FASE 3 - INTEGRACIÓN TWO-STAGE + TOP-K RANKING:**
   * Acoplar la preselección de la Fase 1 con las puntuaciones de similitud de la Fase 2.
   * Ordenar candidatos por similitud y seleccionar las K mejores alternativas según el experimento definido.
   * Registrar el tiempo de ejecución del pipeline para establecer una línea base de rendimiento experimental.

4. **FASE 4 - LOAD-AWARE RE-RANKING:**
   * Aplicar la ecuación de re-ranking sensible a la carga:
     $$\text{score}(m) = \alpha \cdot \text{SimCoseno}(u, m) - \beta \cdot \left(\frac{\text{SesionesActivas}(m)}{\text{MaxCupos}(m)}\right) + \gamma \cdot \text{BonoNuevo}(m)$$
   * Los coeficientes $\alpha$, $\beta$ y $\gamma$ deben inyectarse dinámicamente desde la configuración.
   * Manejo seguro ante `max_cupos = 0` para evitar divisiones por cero.

5. **FASE 5 - AUDITORÍA DE DISTRIBUCIÓN Y EXPERIMENTACIÓN:**
   * Permitir la evaluación de baselines comparativos (B0: Similitud pura, B1: Similitud + Carga, B2: Modelo propuesto completo).
   * Producir métricas cuantitativas exportables (similitud promedio, varianza de carga, tasa de saturación, tasa de activación de nuevos talentos).

---

### 6. Estrategia de Pruebas Automatizadas (Pytest)

Las pruebas deben ser completamente herméticas e independientes de la base de datos de producción `data/epis_mentorias.db`, utilizando la fixture `test_db` definida en `tests/conftest.py` sobre bases SQLite temporales en memoria o `tmp_path`.

La suite se organiza en:
* **`tests/unit/test_config.py`:** Validación de parámetros en `system_rules.json`, rangos $[0, 1]$, escala vigesimal $[0, 20]$, enteros positivos para `top_k` y manejo de JSON corrupto.
* **`tests/unit/test_filtering.py`:** Restricciones deterministas en SQL (nota mínima, disponibilidad horaria, cupo disponible, descarte si `max_cupos = 0` y cortocircuito ante cero candidatos).
* **`tests/unit/test_similarity.py`:** Espacio vectorial TF-IDF, similitud idéntica (1.0), ortogonal/disjunta (0.0), gradiente de coincidencia y resiliencia ante vocabulario vacío.
* **`tests/unit/test_reranking.py`:** Penalización por carga ($\beta$), bono a novatos ($\gamma$), aislamiento con $\gamma = 0$, prevención de división por cero, orden descendente estricto y dimensionamiento Top-K.
* **`tests/integration/test_recommendation_pipeline.py`:** Integración integral del pipeline (*end-to-end*) con datos controlados (4 candidatos: 1 descartado por nota, 1 por horario, 2 evaluados y ordenados por score final) y validación de `top_k \ge 1`.

---

### 7. Restricciones y Reglas para Cambios Futuros
1. **Preservación de Compatibilidad de API:** No alterar firmas de funciones existentes (como `aplicar_reranking_equidad` o `recomendar_mentores`) sin actualizar coordinadamente los consumidores (visualizador Streamlit, suites de pruebas y documentación).
2. **Sincronización Mandatoria:** Ante cualquier modificación de parámetros en `config/system_rules.json`, es obligatorio ejecutar `python scripts/sync_docs.py` y verificar que las pruebas sigan pasando con `pytest`.
3. **Convención de Commits:** Todos los mensajes de commit deben redactarse en **español** siguiendo la convención Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `perf:`).