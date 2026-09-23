# Contexto Arquitectónico y Metodológico del Sistema
## Sistema Web P2P con Algoritmo de Recomendación para la Personalización de Mentorías Académicas (EPIS-UPT 2026)

---

### 1. Justificación y Alcance del Proyecto
El sistema aborda la problemática de retención y rendimiento estudiantil en la Escuela Profesional de Ingeniería de Sistemas de la Universidad Privada de Tacna (EPIS-UPT), orientándose a una población estudiantil de aproximadamente 350 matriculados. El propósito central no es diseñar un algoritmo de aprendizaje profundo complejo desde cero, sino **implementar un pipeline de recomendación en dos etapas (Two-Stage Recommendation Pipeline)** que optimice el emparejamiento bidireccional entre estudiantes de ciclos avanzados (mentores) y estudiantes de ciclos iniciales (tutorados).

El alcance del proyecto es **exclusivamente una plataforma web**, centralizando su lógica de inferencia en un motor modular en Python conectado a la infraestructura de persistencia relacional.

---

### 2. Decisiones Técnicas Fundamentales

#### 2.1. Estrategia Prevista de Ingesta de Datos Académicos (Kardex)
Frente al dilema entre *Web Scraping de credenciales* y mecanismos institucionales seguros:
* **Riesgo del Scraping Directo:** Requerir el usuario y contraseña institucional del estudiante en una aplicación transgrede los principios de seguridad de la información y el principio de consentimiento informado de la Ley N.° 29733 (Ley de Protección de Datos Personales de Perú). Asimismo, la dependencia de la interfaz web de la intranet universitaria genera una alta fragilidad operativa.
* **Diseño Propuesto para Ingesta Institucional (Fase Posterior):**
  1. **Vía Primaria (Administrativa):** Carga masiva estructurada por el Administrador de Tutoría de la EPIS mediante plantillas disociadas en Excel (`.xlsx` o `.csv`).
  2. **Vía Secundaria (Autoservicio Seguro):** Procesamiento en cliente/servidor del reporte oficial de notas en PDF descargado voluntariamente por el estudiante de la intranet, extrayendo las asignaturas aprobadas sin solicitar ni almacenar contraseñas.

> **Estado actual del prototipo:** La fase analítica actual opera sobre un **dataset sintético reproducible** de 350 estudiantes modelado en SQLite (`data/epis_mentorias.db`), diseñado para validar la lógica del pipeline sin comprometer datos personales.

#### 2.2. Análisis de Horarios Oficiales (Semestre Académico EPIS)
Del análisis curricular y de la distribución horaria oficial de la EPIS:
* **Ciclos Iniciales (I al III):** Cursan asignaturas generales y ciencias (*EG-181, EG-182, INE-186, INE-284, SI-384*). Sus horarios lectivos se concentran en el **turno mañana** (08:00 a 13:00).
* **Ciclos Superiores (VII al X):** Cursan asignaturas de especialidad e ingeniería (*SI-783, SI-881, SI-983, SI-083*). Sus horarios lectivos se concentran preferentemente en el **turno tarde/noche** (15:00 a 21:40).
* **Compatibilidad Horaria:** La disponibilidad temporal de ambos grupos se complementa: los estudiantes de ciclos iniciales disponen de tardes libres, mientras que los mentores de ciclos superiores disponen de mañanas y fines de semana libres para brindar asesorías.

---

### 3. Modelo Matemático del Algoritmo Híbrido

El sistema descarta el uso de similitud aislada y adopta un **Pipeline de Recomendación en Dos Etapas (Two-Stage Pipeline)**:

```text
[Entrada: Petición de Mentoría (Curso, Tags, Horario)]
  │
  ▼
┌───────────────────────────┐
│  ETAPA 1: SQL Filter      │  --> Restricciones duras: Nota >= 14.0, Horario, Cupos disponibles
└─────────────┬─────────────┘
  │ Mentores preseleccionados (Candidatos elegibles)
  ▼
┌───────────────────────────┐
│  ETAPA 2: TF-IDF          │  --> Vectorización de necesidades de tutorado y tags de mentores
└─────────────┬─────────────┘
  │ Representación vectorial dispersa
  ▼
┌───────────────────────────┐
│  ETAPA 3: Similitud Coseno│  --> Medición de afinidad angular temático-léxica sim(u, m)
└─────────────┬─────────────┘
  │ Puntuación preliminar en [0, 1]
  ▼
┌───────────────────────────┐
│  ETAPA 4: Load-aware      │  --> Ajuste por saturación de carga operativa y bono de oportunidad
│           re-ranking      │      para mentores nuevos
└─────────────┬─────────────┘
  │ Puntuación calibrada final
  ▼
┌───────────────────────────┐
│  ETAPA 5: Selección Top-K │  --> Selección y ordenamiento de los K mejores candidatos
└───────────────────────────┘
```

#### 3.1. Fórmula de puntuación del Load-Aware Re-ranking
Para penalizar la saturación operativa de mentores con alta carga y otorgar un incentivo experimental a mentores nuevos:

$$\text{PuntajeFinal}(m) = \alpha \cdot \text{SimCoseno}(u, m) - \beta \cdot \left(\frac{\text{SesionesActivas}(m)}{\text{MaxCupos}(m)}\right) + \gamma \cdot \text{BonoNuevo}(m)$$

Donde:
* **$\alpha = 0.70$**: Ponderación de afinidad temática de contenidos (similitud de coseno).
* **$\beta = 0.20$**: Factor de penalización por saturación de carga operativa.
* **$\gamma = 0.10$**: Bono de oportunidad para mentores sin historial previo de tutorías.

> [!NOTE]
> Los valores $\alpha=0.70$, $\beta=0.20$ y $\gamma=0.10$ corresponden a la configuración experimental actual. No constituyen parámetros óptimos ni validados definitivamente; serán evaluados mediante experimentos comparativos y análisis de sensibilidad.

---

### 4. Doble Mecánica de Mentorías
1. **Mentoría Individual (1 a 1):** Búsqueda asistida en catálogo Top-K; el estudiante recibe la lista clasificada y selecciona al mentor de su preferencia tras revisar su perfil.
2. **Clases por Demanda (Quórum Colectivo):** Solicitudes colectivas creadas por estudiantes sobre un tema específico. Al alcanzar el quórum mínimo (**10 inscritos en presencial / 20 en virtual**), la clase se habilita formalmente para que cualquier mentor elegible asuma la sesión.

---

### 5. Metodología de Validación Experimental

La evaluación formal del sistema se divide metodológicamente en dos etapas complementarias:

#### 5.1. Evaluación experimental offline (Estudio de ablación)
Se evalúa la capacidad de optimización del algoritmo comparando tres líneas base (*baselines*) sobre el dataset de evaluación:
* **B0 (Similitud pura):** $\text{score}(m) = \text{sim}(u, m)$ con $\alpha=1.0, \beta=0.0, \gamma=0.0$.
* **B1 (Similitud + Carga):** $\text{score}(m) = \alpha \cdot \text{sim}(u, m) - \beta \cdot \text{load}(m)$ con $\alpha=0.70, \beta=0.20, \gamma=0.0$.
* **B2 (Modelo propuesto completo):** $\alpha=0.70, \beta=0.20, \gamma=0.10$.

**Métricas algorítmicas cuantitativas:**
1. **Preservación de afinidad temática:** Similitud de coseno promedio del Top-K recomendado.
2. **Balance y dispersión de carga:** Desviación estándar y coeficiente de variación de sesiones asignadas por mentor.
3. **Tasa de saturación operativa:** Porcentaje de mentores que alcanzan el 100% de su capacidad.
4. **Tasa de activación de nuevos talentos:** Proporción de mentores novatos recomendados en el Top-K y asignados con éxito.
5. **Rendimiento computacional:** Registro de tiempos de respuesta del pipeline para establecer la línea base de latencia experimental.

#### 5.2. Evaluación posterior con usuarios (Fase piloto en campo)
Diferenciando rigurosamente las métricas matemáticas del algoritmo de la experiencia humana, se contempla una prueba piloto con usuarios evaluada mediante encuestas en Escala Likert:
* **Pertinencia percibida:** Adecuación del perfil y dominio temático del mentor sugerido.
* **Eficiencia en la coordinación:** Reducción subjetiva del tiempo dedicado a encontrar un tutor disponible.
* **Satisfacción pedagógica:** Utilidad de las sesiones recibidas y percepción de progreso académico.

---

### 6. Limitaciones del Alcance Actual
1. **Dataset Sintético:** Los experimentos actuales se fundamentan en distribuciones probabilísticas simuladas, no en trazas reales de interacción.
2. **Representación Léxica TF-IDF:** El emparejamiento depende de coincidencia de n-gramas y vocabulario explícito; no resuelve polisemia ni sinonimia semántica profunda.
3. **Parámetros Heurísticos:** Los coeficientes $\alpha, \beta, \gamma$ requieren calibración formal mediante barridos experimentales multiobjetivo.