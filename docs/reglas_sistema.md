
# Directivas y Reglas del Sistema para Asistentes AI y Copiloto
## Contexto: Sistema Web de Mentorías Académicas P2P (EPIS-UPT 2026)

Este archivo define las reglas de negocio estrictas, el alcance técnico y las directivas que GitHub Copilot y los desarrolladores deben acatar al modificar código o sugerir implementaciones.

---

### 1. Reglas de Negocio No Negociables
1. **Alcance Exclusivamente Web:** No generar componentes, vistas ni lógica para entornos móviles (React Native, Expo o Flutter). El sistema es estrictamente una aplicación web[cite: 7].
2. **Asimetría de Roles:** Un estudiante novato (Ciclos I a IV) no puede recomendar a otro novato para tutoría técnica. El filtro SQL siempre debe restringir el conjunto de mentores a estudiantes de ciclos avanzados con condición `APROBADO` en la materia requerida[cite: 4].
3. **Calificación Mínima del Mentor:** Todo mentor debe registrar una calificación de $\ge 14.0$ en el curso objetivo.
4. **Privacidad de Credenciales (Ley N° 29733):** Queda terminantemente prohibido implementar pantallas o APIs que capturen contraseñas o tokens personales de la intranet universitaria UPT[cite: 5]. El procesamiento de datos se hace vía Excel administrativo o lectura de PDF en cliente/servidor[cite: 5].
5. **Doble Modalidad de Clases Colectivas:**
   * Quórum Presencial: Exactamente 10 estudiantes.
   * Quórum Virtual: Exactamente 20 estudiantes.

---

### 2. Parámetros del Motor de Recomendación
Al escribir o modificar funciones en Python, los siguientes valores actúan como constantes globales (definidos en `config/system_rules.json`):
* `ALPHA` (Peso afinidad temática / Coseno): `0.70`[cite: 6]
* `BETA` (Penalización por saturación de sesiones): `0.20`
* `GAMMA` (Bono a mentores nuevos sin mentorías): `0.10`
* `TOP_K` (Mentores presentados en la lista web): `3`[cite: 6]
* `MIN_NOTA_MENTOR`: `14`

---

### 3. Estándares Técnicos para Copilot
* **Lenguaje:** Python 3.10+ para el motor algorítmico[cite: 7].
* **Tipado:** Usar *type hinting* obligatorio en todas las funciones (`def recomendar(id_alumno: int) -> list[dict]:`).
* **Librerías Permitidas para ML:** `scikit-learn` (`TfidfVectorizer`, `cosine_similarity`) y `numpy`[cite: 6]. No introducir frameworks pesados como PyTorch o TensorFlow sin justificación de tesis.
* **Separación de Responsabilidades:**
  * Las reglas duras (horario, curso aprobado, cupos disponibles) se resuelven en **SQL**[cite: 4, 7].
  * La vectorización, similitud de coseno y ponderación de equidad se resuelven en **Python** en memoria[cite: 6].

---

## Directiva de Desarrollo: Fases de Prueba y Verificación Progresiva del Algoritmo

Al implementar, refactorizar o ejecutar pruebas sobre el motor de recomendación, el asistente debe ceñirse al siguiente orden estricto de validación modular:

1. FASE 1 - FILTRADO DETERMINISTA (SQL HARD RULES):
   - Probar de forma aislada la función/query de preselección.
   - Restricciones obligatorias: Curso aprobado con nota >= 14.0, coincidencia de franja horaria y cupos activos < cupos máximos.
   - No ejecutar vectorización ni cálculo de distancias si el conjunto de candidatos aptos está vacío.

2. FASE 2 - ESPACIO VECTORIAL Y CONTENIDO (TF-IDF + COSENO):
   - Probar la matriz de características generada por Scikit-Learn.
   - Asegurar que vocablos idénticos produzcan similitud = 1.0 y vocabularios disjuntos produzcan similitud = 0.0.
   - El vector de entrada debe ser la combinación de tags de intereses y necesidades del alumno tutorado.

3. FASE 3 - INTEGRACIÓN TWO-STAGE + K-NN:
   - Acoplar la Etapa 1 (SQL) con la Etapa 2 (Coseno).
   - Extraer el Top-K (K=3) preliminar sin factores de ponderación.
   - Verificar tiempos de ejecución: el pipeline completo sobre la cohorte de 350 alumnos debe responder en milisegundos.

4. FASE 4 - RE-RANKING POR EQUIDAD (FAIRNESS CALIBRATION):
   - Aplicar el ajuste de puntuación final: Score = (alpha * Coseno) - (beta * Saturacion) + (gamma * BonoNuevo).
   - Los pesos alpha, beta y gamma NO deben estar fijos en el código; deben leerse dinámicamente desde `config/system_rules.json`.
   - Simular casos límite: un mentor con similitud perfecta (1.0) pero con cupos llenos debe ser penalizado frente a un mentor nuevo con similitud moderada.

5. FASE 5 - AUDITORÍA DE DISTRIBUCIÓN Y EXPERIMENTACIÓN:
   - Generar scripts de prueba que simulen lotes de solicitudes y calculen la cobertura de mentores y la varianza de carga.
   - Toda salida de prueba debe generar métricas exportables en JSON o consola para el registro experimental de la tesis.

Cualquier cambio propuesto en una fase debe mantener la compatibilidad hacia atrás con las pruebas unitarias de las fases anteriores.