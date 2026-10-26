# Guía de Ingeniería de Prompts — CommunityLab (n8n)

**Audiencia:** Ingeniero/a de prompts  
**Versión:** 1.5 (compacta)  
**Alineado a:** `contrato-de-datos.md` v1.0 + workflow `communitylab-workflow-v1.0-solo-oci`  
**Última revisión:** 2026-10-02

---

## 1. Propósito

Define el contexto y los criterios para **diseñar, probar y ajustar los prompts** de los nodos LLM (Basic LLM Chain) del workflow de CommunityLab.

Un prompt no se considera terminado hasta validarlo **dentro de n8n** con la estructura de datos real. Que funcione en un script no garantiza que funcione en el workflow (expresiones `{{ $json... }}`, campos disponibles, parser, formato esperado por componentes posteriores).

**Flujo de trabajo recomendado:**
1. Entender la función del LLM  
2. Revisar entrada y salida esperadas  
3. Diseñar / ajustar System + User Prompt  
4. Probar en script/notebook  
5. Evaluar casos de entrada variados  
6. Transferir a n8n y conectar expresiones reales  
7. Ejecutar con datos reales → revisar salida y componentes consumidores → ajustar  

---

## 2. Visión general de los LLM

| # | Nodo | Función principal | Parser actual |
|---|------|-------------------|---------------|
| 1 | **Analista de Contenido** | Analizar y clasificar cada interacción | Sí |
| 2 | **Generador de Post para LinkedIn** | Generar contenido para LinkedIn | No |
| 3 | **Generador de Destaque para Newsletter** | Generar destaque para newsletter | No |
| 4 | **Generador: FAQ & Tip Técnico** | Generar FAQ o tip técnico | No |

**Modelo:** OpenRouter en pruebas. El modelo final aún no está fijado. Mantener estables: entrada, salida, nombres de campos, reglas de comportamiento y compatibilidad con componentes posteriores. Los generadores pueden compartir el mismo perfil; el Analista puede usar otro si las pruebas lo justifican.

---

## 3. Structured Output Parser

**Estado actual:** Solo el Analista usa Structured Output Parser. Los generadores usan instrucciones del tipo `Responde SOLO JSON` (provisional).

**Criterio de decisión:**  
> ¿La salida necesita una estructura controlada para que el siguiente componente la consuma de forma confiable?

- Si **sí** → evaluar Structured Output Parser (y revisar `Require Specific Output Format`, schema, prompt y componente consumidor).  
- **Analista:** mantener y validar el Parser (su salida alimenta decisiones posteriores).

**Schema del Analista:**

```text
status
└── analisis
    ├── sentimiento
    ├── relevancia
    ├── tipo_insight
    ├── temas
    ├── resumen
    └── evidencia_clave
```

**Auto-Fix Format:** útil si el modelo ocasionalmente envuelve el JSON en Markdown. No sustituye un prompt bien definido.

> **Nota para generadores:** actualmente no usan Parser. Evaluar en pruebas si la estructura se mantiene estable con instrucciones del prompt o si conviene incorporarlo.

---

## 4. Alcance del prompt engineer

**Puede modificar:**
- System Message y User Prompt
- Instrucciones de comportamiento, reglas de clasificación y criterios de generación
- Ejemplos, expresiones dinámicas, Temperature y Maximum Number of Tokens
- Schema del parser (coordinado con los consumidores)
- Decisión de usar o no Structured Output Parser en los generadores

**No debe modificar unilateralmente:**
- Nombres de campos ni estructura de datos consumida por otros nodos
- Conexiones, branching, lógica del Evaluador o del Ensamble
- Contrato externo del sistema (`contrato-de-datos.md`)

Los nombres de campos y la estructura de datos son **contrato**. Cambiarlos desde el prompt (ej. `tipo_insight` → `tipo`) puede romper el Evaluador u otros nodos. Si una mejora lo requiere, coordinar con la persona responsable del workflow.

---

## 5. Configuración en n8n

### Basic LLM Chain — Parameters

| Campo | Uso en CommunityLab |
|-------|---------------------|
| Source for Prompt (User Message) | `Define Below` |
| Prompt (User Message) | Instrucciones + datos dinámicos |
| Require Specific Output Format | ON en Analista (necesario con Parser) |
| Chat Messages → Type: System | Rol, reglas y comportamiento |
| Chat Messages → Message | System Prompt |

### Modelo

| Campo | Uso |
|-------|-----|
| Credential / Model | Proveedor y modelo de pruebas |
| Sampling Temperature | Estabilidad vs. creatividad |
| Maximum Number of Tokens | Longitud máxima de respuesta |
| Response Format | Puede ayudar a solicitar JSON |
| Timeout / Max Retries | Ante problemas de ejecución |

### Structured Output Parser (cuando se use)

| Campo | Función |
|-------|---------|
| Schema Type / Input Schema (JSON) | Define la estructura esperada |
| Auto-Fix Format | Corrección de problemas de formato |

### Settings del nodo

| Setting | Criterio |
|---------|----------|
| Retry On Fail | Ante errores intermitentes del proveedor |
| On Error | `Stop Workflow` (MVP) |
| Execute Once | OFF en el Analista (una vez por interacción) |
| Notes | Registrar versión del prompt u observaciones |

---

## 6. Reglas generales

- **Formato JSON:** devolver únicamente JSON. Sin bloques Markdown, sin saludos ni texto fuera del objeto. Respetar nombres de campos.
- **Campos estables:** no renombrar; el workflow depende de ellos.
- **Información insuficiente:** definir el comportamiento (ej. FAQ → `"status": "derivado_a_mentoria"`).

---

## 7. Nodo 1 — Analista de Contenido

**Función:** Interpreta cada interacción y genera una clasificación estructurada.  
**Cuándo:** Una vez por cada interacción del lote (después del Split).

### Entrada

| Campo | Origen | Ejemplo | Notas |
|-------|--------|---------|-------|
| `id_temporal` | Normalizador | `INT-1` | Generado por el workflow |
| `autor` | Normalizador | `Mariana Souza` | Opcional |
| `canal` | Normalizador | `#logros-y-empleos` | Opcional |
| `tipo` | Normalizador | `testimonio` | Puede estar ausente |
| `texto` | Normalizador | texto del mensaje | Obligatorio |
| `origen_comunidad` | Normalizador | `Discord_Grupo_ONE_G10` | Del lote |
| `periodo_referencia` | Normalizador | `Semana_04` | Del lote |

Si `tipo` está vacío, ausente o es `desconocido`, inferir `tipo_insight` a partir del contenido.

### Salida

```json
{
  "status": "exito",
  "analisis": {
    "sentimiento": "Positivo",
    "relevancia": "Alta",
    "tipo_insight": "testimonio",
    "temas": ["Contratacion", "OCI"],
    "resumen": "Estudiante consigue empleo destacando proyectos con LangChain y OCI.",
    "evidencia_clave": "quedé seleccionada para el puesto de Desarrolladora Junior de IA"
  }
}
```

| Campo | Valores esperados | Importancia |
|-------|-------------------|-------------|
| `sentimiento` | `Positivo`, `Neutro`, `Negativo` | Usado por el Evaluador |
| `relevancia` | `Alta`, `Media`, `Baja` | Describe relevancia |
| `tipo_insight` | `testimonio`, `pregunta_tecnica`, `duda`, `logro`, `feedback`, `otro` | **Crítico para branching** |
| `temas` | Array de strings cortos | Identifica temas |
| `resumen` | 1–2 frases | Resume la interacción |
| `evidencia_clave` | Cita o fragmento corto | Conserva evidencia concreta |

El Evaluador usa principalmente `tipo_insight + sentimiento`. Una clasificación incorrecta puede desactivar ramas del workflow. Mantener el Parser alineado con el schema.

**Checklist:**  
- [ ] Clasifica correctamente testimonios, logros, preguntas y dudas  
- [ ] Funciona cuando `tipo` viene vacío o ausente  
- [ ] Diferencia casos ambiguos  
- [ ] No inventa información  
- [ ] Produce todos los campos y respeta el schema  
- [ ] Funciona con mensajes de prueba y casos ambiguos/feedback neutro  

---

## 8. Nodo 2 — Generador de Post para LinkedIn

**Cuándo:** Evaluador activa `generar_linkedin` (testimonios/logros positivos o override).

### Entrada

| Campo | Contenido |
|-------|-----------|
| `origen_comunidad` | Comunidad del lote |
| `periodo_referencia` | Periodo del lote |
| `evidencias.testimonios_logros` | Array de interacciones analizadas |

### Salida

```json
{
  "titulo": "De la Comunidad al Mercado: …",
  "copy": "Cuerpo del post con saltos de línea, CTA y tono inspirador…",
  "canal_recomendado": "LinkedIn Oficial",
  "potencial_engagement": "Alto",
  "hashtags": ["#TalentosTech", "#InteligenciaArtificial"]
}
```

| Campo | Obligatorio | Notas |
|-------|-------------|-------|
| `titulo` | Sí | Encabezado |
| `copy` | Sí | Post completo |
| `canal_recomendado` | Sí | Ej. `LinkedIn Oficial` |
| `potencial_engagement` | Sí | `Alto`, `Medio`, `Bajo` |
| `hashtags` | Recomendado | Array |

**Checklist:**  
- [ ] Tono orientado a comunidad tecnológica  
- [ ] Basado solo en evidencias recibidas (no inventa)  
- [ ] JSON válido  
- [ ] Probar con uno y con dos testimonios  
- [ ] Revisar comportamiento con evidencias insuficientes  

---

## 9. Nodo 3 — Generador de Destaque para Newsletter

**Cuándo:** Evaluador activa `generar_newsletter`.

### Entrada

`origen_comunidad`, `periodo_referencia`, `evidencias.testimonios_logros`.

### Salida

```json
{
  "seccion": "Logro de la Semana",
  "titular": "Estudiante consigue empleo dev con portfolio de IA en Oracle Cloud",
  "resumen": "Mariana Souza obtuvo su primera oportunidad como Dev Jr de IA…",
  "llamado_a_accion": "Comparte tu logro en #logros-y-empleos",
  "status": "listo_para_publicar"
}
```

| Campo | Obligatorio |
|-------|-------------|
| `seccion` | Sí |
| `titular` | Sí |
| `resumen` | Sí |
| `llamado_a_accion` | Recomendado |
| `status` | Sí |

**Checklist:**  
- [ ] Más breve que el contenido de LinkedIn  
- [ ] Estilo de destaque de comunidad  
- [ ] Usa las mismas evidencias (no inventa)  
- [ ] JSON válido y campos definidos  

---

## 10. Nodo 4 — Generador FAQ & Tip Técnico

**Cuándo:** Evaluador activa `generar_faq` (preguntas técnicas, dudas o override).

### Entrada

| Campo | Contenido |
|-------|-----------|
| `origen_comunidad` | Lote |
| `periodo_referencia` | Lote |
| `evidencias.preguntas_dudas` | Array de interacciones de tipo pregunta/duda |

### Salida

```json
{
  "tema": "Tip rápido: nodos de reintento en LangGraph",
  "origen": "Duda de Lucas Albuquerque en #dudas-langgraph",
  "status": "listo_para_publicar",
  "contenido_sugerido": "1. …\n2. …\n3. …"
}
```

| Campo | Obligatorio | Notas |
|-------|-------------|-------|
| `tema` | Sí | Título |
| `origen` | Sí | Quién / dónde surgió |
| `status` | Sí | `listo_para_publicar` o `derivado_a_mentoria` |
| `contenido_sugerido` | Sí | Puede contener Markdown |

**Checklist:**  
- [ ] Respuesta útil y accionable (no solo repite la pregunta)  
- [ ] Usa únicamente información disponible  
- [ ] Si no hay suficiente contexto → derivar a mentoría  
- [ ] JSON válido y campos definidos  

---

## 11. Expresiones útiles en User Prompt

```text
{{ $json.autor }}
{{ $json.texto }}
{{ $json.origen_comunidad }}
{{ JSON.stringify($json.evidencias.testimonios_logros) }}
{{ JSON.stringify($json.evidencias.preguntas_dudas) }}
```

No eliminar accidentalmente al editar el prompt. Si una expresión debe cambiar porque la entrada real cambió, comprobar primero el origen del cambio.

---

## 12. Pruebas y Definition of Ready

**Casos básicos:**  
1. Solo Mariana → LinkedIn + Newsletter  
2. Solo Lucas → FAQ  
3. Ambos → los tres tipos de activo  
4. Feedback neutro sin logro ni duda → posible 0 activos  

**Casos adicionales:** interacción ambigua · sin `tipo` · `tipo` que contradice el contenido · contenido insuficiente · varias interacciones (evitar mezcla) · evidencias vacías · información que podría provocar invención de datos.

**Un prompt está listo cuando:**
- [ ] Objetivo, entrada y salida claramente definidos  
- [ ] Nombres de campos compatibles con el workflow  
- [ ] Casos normales y ambiguos/incompletos probados  
- [ ] No inventa información; respeta idioma y tono  
- [ ] Produce JSON válido; el Parser (si existe) lo acepta  
- [ ] Funciona dentro de n8n y no rompe componentes posteriores  

---

## 13. Problemas frecuentes y tabla rápida

| Problema | Revisar primero |
|----------|-----------------|
| JSON inválido | Prompt + Parser |
| Faltan campos | Prompt + schema |
| Clasificación incorrecta | Instrucciones del Analista |
| El modelo inventa información | Reglas de evidencia del prompt |
| Contenido correcto pero rompe el workflow | Schema / estructura de salida |
| Funciona en script pero no en n8n | Entrada real + expresiones |
| El nodo no recibe datos | Conexiones del workflow |
| Un activo no se genera | Analista + Evaluador + branching |
| La respuesta se corta | Maximum Number of Tokens |
| Contenido demasiado variable | Temperature + instrucciones |

| Nodo | Entrada principal | Salida principal |
|------|-------------------|------------------|
| Analista | `autor`, `canal`, `tipo`, `texto` | `analisis.sentimiento`, `tipo_insight`, `temas`, `resumen`, `evidencia_clave` |
| LinkedIn | `evidencias.testimonios_logros` | `titulo`, `copy`, `canal_recomendado`, `potencial_engagement` |
| Newsletter | `evidencias.testimonios_logros` | `seccion`, `titular`, `resumen`, `status` |
| FAQ | `evidencias.preguntas_dudas` | `tema`, `origen`, `status`, `contenido_sugerido` |

---

## 14. Referencias

- `contrato-de-datos.md` — contrato externo de datos  
- `communitylab-workflow-v1.0-solo-oci.json` — workflow de n8n  

---

**Fin — Guía de Ingeniería de Prompts v1.5 (compacta)**
