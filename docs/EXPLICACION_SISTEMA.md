# Contexto Arquitectónico y Metodológico del Sistema
## Sistema Web P2P con Algoritmo de Recomendación para la Personalización de Mentorías Académicas (EPIS-UPT 2026)

---

### 1. Justificación y Alcance del Proyecto
El sistema aborda la problemática de retención y rendimiento estudiantil en la Escuela Profesional de Ingeniería de Sistemas de la Universidad Privada de Tacna (EPIS-UPT), donde coexisten aproximadamente 350 estudiantes matriculados. El propósito central no es diseñar un algoritmo matemático desde cero, sino **implementar un motor de recomendación híbrido** que optimice el emparejamiento bidireccional entre estudiantes de ciclos avanzados (mentores) y estudiantes de ciclos iniciales (tutorados)[cite: 6, 8, 10].

El alcance del proyecto es **exclusivamente una plataforma web**, centralizando su lógica de inferencia en un microservicio/script en Python conectado a la infraestructura de persistencia[cite: 5, 7].

---

### 2. Decisiones Técnicas Fundamentales

#### 2.1. Estrategia de Ingesta de Datos Académicos (Kardex)
Frente al dilema entre *Web Scraping de credenciales* y *Carga Institucional*:
* **Riesgo del Scraping Directo:** Requerir el usuario y contraseña institucional del estudiante en una aplicación de terceros transgrede los principios de seguridad de la información y el principio de consentimiento informado de la Ley N° 29733 (Ley de Protección de Datos Personales de Perú)[cite: 5]. Asimismo, la fragilidad ante cambios en la intranet universitaria vuelve inestable el sistema.
* **Solución Implementada:**
  1. **Vía Primaria (Piloto):** Carga masiva por el Administrador de Tutoría de la EPIS mediante plantillas estructuradas en Excel (`.xlsx` o `.csv`).
  2. **Vía Secundaria (Autoservicio Seguro):** Parser en backend para que el estudiante suba directamente su reporte de notas oficial en PDF descargado de la intranet, extrayendo las calificaciones sin almacenar contraseñas[cite: 5].

#### 2.2. Análisis de Horarios Oficiales (Semestre 2026-II)
Del análisis del documento de horarios de la EPIS:
* **Ciclos Iniciales (I al III):** Cursan asignaturas generales y ciencias (*EG-181, EG-182, INE-186, INE-284, SI-384*)[cite: 4]. Sus horarios se concentran en el **turno mañana** (08:00 a 13:00)[cite: 4].
* **Ciclos Superiores (VII al X):** Cursan asignaturas de especialidad (*SI-783, SI-881, SI-983, SI-083*)[cite: 4]. Sus horarios se concentran en el **turno tarde/noche** (15:00 a 21:40)[cite: 4].
* **Compatibilidad:** La disponibilidad libre de ambos grupos se complementa naturalmente: los tutorados tienen libres las tardes/noches y los mentores tienen libres las mañanas y sábados[cite: 4].

---

### 3. Modelo Matemático del Algoritmo Híbrido

El sistema descarta el uso del coseno aislado y adopta un **Pipeline en Dos Etapas (Two-Stage Pipeline)**[cite: 10]:

[Entrada: Petición de Mentoría]
│
▼
┌──────────────────────┐
│  ETAPA 1: SQL Filter │  --> Restricciones duras: Kardex >= 14, Horario, Cupo
└──────────┬───────────┘
│ Mentores preseleccionados
▼
┌──────────────────────┐
│  ETAPA 2: TF-IDF     │  --> Vectorización de intereses y áreas de dominio
└──────────┬───────────┘
│ Vectores dispersos
▼
┌──────────────────────┐
│  ETAPA 3: Coseno     │  --> Cálculo de afinidad angular sim(u, m)
└──────────┬───────────┘
│ Puntaje [0, 1]
▼
┌──────────────────────┐
│  ETAPA 4: Re-ranking │  --> Ajuste por saturación y equidad a nuevos mentores
└──────────┬───────────┘
│ Score Final
▼
┌──────────────────────┐
│  ETAPA 5: KNN Top-K  │  --> Selección de los K=3 mejores mentores
└──────────────────────┘

#### 3.1. Fórmula de Puntuación de Equidad (Fairness Re-ranking)
Para evitar la saturación de los mentores más populares y promover la equidad con mentores novatos:

$$\text{PuntajeFinal}(m) = \alpha \cdot \text{SimCoseno}(u, m) - \beta \cdot \left(\frac{\text{SesionesActivas}(m)}{\text{MaxCupos}(m)}\right) + \gamma \cdot \text{BonoNuevo}(m)$$

* **$\alpha = 0.70$**: Ponderación de afinidad temática de contenidos[cite: 6].
* **$\beta = 0.20$**: Factor de penalización por saturación de carga operativa.
* **$\gamma = 0.10$**: Bono de oportunidad para mentores sin historial previo de tutorías.

---

### 4. Doble Mecánica de Mentorías
1. **Mentoría Individual (1 a 1):** Búsqueda asistida en catálogo Top-K; el estudiante elige su mentor tras la recomendación[cite: 6].
2. **Clases por Demanda (Quórum Colectivo):** Solicitudes colectivas creadas por estudiantes. Al alcanzar el quórum mínimo (**10 inscritos en presencial / 20 en virtual**), la clase se habilita para que cualquier mentor apto tome la sesión.

---

### 5. Metodología de Validación Experimental
La efectividad del algoritmo no se mide exclusivamente por métricas fuera de línea, sino mediante **evaluación en línea de percepción y satisfacción (Escala Likert)** aplicada a los estudiantes de la muestra durante la fase piloto[cite: 6], analizando:
* Pertinencia de los mentores recomendados[cite: 6].
* Reducción del tiempo de búsqueda y coordinación[cite: 6].
* Claridad y utilidad de las sesiones recibidas[cite: 6].