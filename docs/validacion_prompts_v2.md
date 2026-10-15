# Validación de prompts — LinkedIn (v2.1), Newsletter (v3.1) y FAQs/Tips (v1.1)

**Archivo de casos**: `data/casos_prueba_activos.json` (5 lotes, el caso 1 es el ejemplo enviado por Roxana).
**Última actualización**: 14/10/2026. Los resultados de cada corrida están al final de este documento.

> **Nota**: la columna *Newsletter esperado* de la primera tabla corresponde a la v2.0, que fue reemplazada. La newsletter vigente (salida estructurada, v3.x) se valida con los casos de la sección "Newsletter con salida estructurada".

## Cómo probar en n8n

**Opción rápida**: importar `prompts/pruebas/workflow_prueba_prompts.json`, asignar la credencial de Gemini (Header Auth con `x-goog-api-key`) y ejecutar. Corre los 15 casos (5 por activo) y valida cada salida automáticamente; los resultados se ven en la vista Tabla del nodo *Validar salidas*. Tarda unos 4 minutos por el límite gratuito de 5 solicitudes por minuto.

**Opción manual** (en el flujo principal):

1. En el nodo de LinkedIn, pega el bloque *System message* de `prompts/system_prompt_linkedin.md` y la plantilla del mensaje de usuario. Haz lo mismo en el nodo de Newsletter con `system_prompt_newsletter.md`.
2. Temperatura: 0.5 en LinkedIn, 0.3 en Newsletter. Si el nodo permite formato de respuesta JSON, actívalo.
3. Con *pin data* (o ejecutando el nodo anterior con cada caso), corre los 5 lotes uno por uno por cada nodo.
4. Completa la tabla de abajo con lo que obtengas.

## Revisión general (aplica a todos los casos)

- [ ] La salida es JSON válido y se puede parsear sin limpiar nada.
- [ ] Incluye todos los campos del contrato (LinkedIn: `titulo`, `copy`, `canal_recomendado`, `potencial_engagement`, `hashtags`, `origen_interacciones`; Newsletter: `seccion`, `titular`, `resumen`, `origen_interacciones`).
- [ ] `copy` no trae hashtags dentro del texto y tiene entre 80 y 150 palabras.
- [ ] No aparecen empresas, puestos, cifras ni herramientas que no estén en los datos.
- [ ] Los nombres coinciden exactamente con `autor`.

## Casos

| Caso | Qué prueba | LinkedIn esperado | Newsletter esperado |
|---|---|---|---|
| 1 (Roxana) | Alcance real del logro | `logro_laboral`. Habla de una **entrevista técnica**, nunca de contratación ni de selección. No inventa empresa. | Logro de Laura como entrevista. La duda de Carlos aparece como pregunta (no como problema confirmado). "12" se presenta como total de interacciones, no como cantidad de logros. |
| 2 | Logro laboral concreto | `logro_laboral` con tono cálido. Puede decir que firmó su primer contrato como Analista de Datos Junior. Sin empresa ni salario. | Solo bloques de logro y panorama (el de preguntas se omite porque no hay dudas). |
| 3 | Experiencia de proyecto | `experiencia_proyecto`, tono práctico: Power BI, dashboard de ventas regionales, dificultad al modelar relaciones. Cierra invitando a compartir proyectos. | Incluye la consulta de Andrés sobre permisos del bucket, sin inventar respuesta. Dice "una consulta", no "varias". |
| 4 | Aprendizaje técnico | `aprendizaje_tecnico`, tono didáctico: router y reintentos según lo que dijo Diego, sin código ni detalles inventados. Cierra con pregunta abierta. | La observación de Ricardo sobre ejemplos con OpenAI aparece atribuida a él, no como dato general. |
| 5 | Sin testimonios + feedback crítico | `omitido: true` con `motivo`, campos vacíos. | Sin bloque de logros. Representa las dudas tal cual y atribuidas. "Tercera vez que pregunto" no se cuenta como tres personas. Sin frases como "varios miembros" ni suavizar el reclamo de Carlos. |


---

# FAQs y Tips (`prompts/system_prompt_faq_tips.md`)

Temperatura recomendada: 0.3. Se prueba con los mismos 5 lotes de `data/casos_prueba_activos.json`.

## Revisión general

- [ ] JSON válido con `tema`, `origen`, `status`, `contenido_sugerido` y `formato`.
- [ ] `contenido_sugerido` **no incluye nombres de personas** (el nombre solo va en `origen`).
- [ ] No hay código, comandos, nombres de parámetros, paquetes, versiones ni enlaces.
- [ ] Las causas se presentan como posibles ("una causa habitual..."), no como diagnóstico de la persona.
- [ ] El prefijo de `tema` coincide con `formato` (`FAQ: `, `Tip rápido: ` o `Consulta para mentoría: `).
- [ ] No llama "frecuente" o "recurrente" a una duda sin respaldo en los datos.

## Casos

| Caso | Qué prueba | Esperado |
|---|---|---|
| 1 | Duda que describe una situación (agente con memoria que se vuelve lento) | `TIP` o `derivado_a_mentoria`. Si es TIP: causas como posibles, sin afirmar qué le pasa a Carlos Ruiz y sin llamarla "recurrente" (solo preguntó si alguien más lo notó). |
| 2 | Lote sin dudas | `status: "omitido"`, `omitido: true`, `motivo` presente, campos de texto vacíos. |
| 3 | Pregunta sobre permisos de un bucket en OCI | `FAQ` con orientación general o `derivado_a_mentoria`. **No aceptable**: nombres de permisos, sintaxis de políticas o pasos exactos de consola inventados. |
| 4 | Pregunta sobre usar LangGraph con Gemini | `FAQ` general, sin nombres de paquetes ni código. La observación de Ricardo sobre ejemplos con OpenAI no se presenta como hecho general. |
| 5 | Dos dudas distintas en el mismo lote | Elige una. Lo esperable es la de n8n con Docker (`FAQ`), con `origen` indicando que la persona dijo que ya lo había preguntado antes, sin contarlo como varias personas. Si elige el bug de autenticación, debe ser `derivado_a_mentoria` y sin diagnóstico. |


---

# Newsletter con salida estructurada (`prompts/system_prompt_newsletter.md`)

Temperatura recomendada: 0.3. Casos en `data/casos_prueba_newsletter_estructurado.json` (con `id_actividad`, salvo el N5 que no los trae a propósito).

## Revisión general

- [ ] JSON válido con `status`, `titulo`, `introduccion`, `secciones`, `cierre` y `motivo`.
- [ ] Cada sección tiene `titulo` (uno de los tres permitidos, en orden), `contenido` en texto plano e `ids_actividades`.
- [ ] Todos los `ids_actividades` existen en el lote de entrada (ninguno inventado).
- [ ] Los `ids_actividades` son **números** (no texto), igual que los ids del lote.
- [ ] `contenido` no repite el título de la sección ni trae Markdown.
- [ ] Los números coinciden con el lote (el total de interacciones no se presenta como cantidad de logros o dudas).
- [ ] Sin "muchos", "varios" ni "la mayoría" cuando hay una sola evidencia.
- [ ] El texto entero se puede guardar en PostgreSQL sin limpieza previa (sin bloques de código alrededor del JSON).

## Casos

| Caso | Qué prueba | Esperado |
|---|---|---|
| N1 (Roxana) | Las tres secciones con trazabilidad | `status: "generado"`. Logro de la Semana: Laura como **entrevista técnica** (no contratación), `[3]`. Tema en Tendencia: la pregunta de Carlos como pregunta (no como problema confirmado), `[2]`. Dato de la Comunidad: 12 interacciones en total y los temas, `[]`. |
| N2 | Solo hay un logro, sin dudas | `status: "generado"`. Incluye Logro de la Semana con `[7]`. Tema en Tendencia puede omitirse o apoyarse en la actividad de Camila, pero no inventa preguntas de la comunidad. |
| N3 | Solo dudas, sin logros; feedback crítico | `status: "generado"`, **sin** Logro de la Semana. Las dos dudas atribuidas a cada autor, con ids `5` y `6`. "Tercera vez que pregunto" se atribuye a Javier y no se cuenta como tres personas. No suaviza ni dramatiza el reclamo de Carlos. |
| N4 | Contenido insuficiente | `status: "insuficiente"`, `motivo` con una frase, `titulo`, `introduccion` y `cierre` vacíos, `secciones: []`. No inventa nada. |
| N5 | Actividades sin identificador | `status: "generado"` y todos los `ids_actividades` vacíos (no inventa ids). El contenido de las secciones sigue siendo fiel. |

---

---

# Resultados — corrida 1 (14/10/2026)

**Resumen automático**: 14 OK · 1 con avisos (falso positivo) · 0 fallas · 0 errores de API (de 15).
Todos los casos cumplen la estructura del contrato: JSON válido, campos completos, ids numéricos y existentes en el lote, `omitido`/`insuficiente` en los casos sin material y sin contratación inventada en LinkedIn 1.

**Revisión manual** (lectura de la columna `salida`; conviene confirmarla leyendo las salidas):

| Caso | Qué salió bien | Observación → ajuste |
|---|---|---|
| LinkedIn 1 | La entrevista no se convirtió en contratación. | El título decía "el dominio del grafo de estados"; Laura solo dijo que pudo explicarlo → v2.1 |
| LinkedIn 2 | Contrato, dos años en atención al cliente y portafolio, todo fiel. | Sin observaciones. |
| LinkedIn 3 | Cita literal correcta. | "Lo más difícil" intensifica el "me costó" original → v2.1 (respetar la intensidad) |
| LinkedIn 4 | Aprendizaje fiel a lo que dijo Diego. | El título "Cómo usar nodos condicionales..." promete un tutorial que el post no es → v2.1 |
| LinkedIn 5 | `omitido: true` con motivo. | Sin observaciones. |
| Newsletter N1 | Entrevista, duda como pregunta, ids `[3]` y `[2]`, total 12. | La introducción habla de "rendimiento de la memoria" (reformula la duda) → v3.1 |
| Newsletter N2 | Solo logro y dato; no inventa preguntas. | Omite "Tema en Tendencia" (aceptable). |
| Newsletter N3 | "Tercera vez" atribuida a Javier, no contada como tres personas; ids `[5, 6]`. | Cambia "bug" por "inconveniente" y pierde "en soporte" (suaviza el reclamo) → v3.1 |
| Newsletter N4 | `status: "insuficiente"` con motivo. | Sin observaciones. |
| Newsletter N5 | `ids_actividades` vacíos (no inventa ids). | Sin observaciones. |
| FAQ 1 | TIP con la causa como posible, sin diagnóstico ni código. | Sin observaciones. |
| FAQ 2 | `status: "omitido"`. | Sin observaciones. |
| FAQ 3 | Sin sintaxis ni permisos inventados. | Tan genérica que no nombra OCI aunque la duda lo menciona → v1.1 |
| FAQ 4 | Sin paquetes ni código. | Presenta la observación de Ricardo ("muchos ejemplos usan OpenAI") como hecho general → v1.1 |
| FAQ 5 | Elige la duda de Javier y registra que ya la había preguntado. | El aviso "parece incluir comandos" fue falso positivo (la palabra "Docker"); regla del validador corregida. |

## Ajustes aplicados tras la corrida 1

- LinkedIn v2.1, Newsletter v3.1 y FAQ/Tips v1.1 (ver el historial de cambios de cada prompt).
- El validador ahora marca como aviso: título que empieza con "Cómo", textos que hablan de "dominio" o "experto", y "inconveniente" en la newsletter.
- Pendiente: volver a correr los 15 casos para confirmar que los ajustes no introducen regresiones.

---

# Resultados — corrida 2 (prompts LinkedIn v2.1, Newsletter v3.1, FAQ/Tips v1.1)

**Resumen automático**: 15 OK · 0 con avisos · 0 fallas · 0 errores de API (de 15).

**Ajustes de la corrida 1 confirmados al leer las salidas**:

- LinkedIn 1: el título ya no habla de "dominio"; solo dice que Laura pasó de aprender agentes a su primera entrevista técnica.
- LinkedIn 3: el texto de Valeria se cita literal ("Me costó modelar las relaciones entre tablas...") en vez de intensificarlo.
- LinkedIn 4: el título ya no empieza con "Cómo".
- Newsletter N1: la introducción habla de "la velocidad de los agentes", más cercano a lo que preguntó Carlos.
- Newsletter N3: conserva "bug de autenticación" y "nadie le ha respondido en soporte", y la "tercera vez" sigue atribuida a Javier.
- FAQ 3: nombra OCI Object Storage.
- FAQ 4: ya no presenta la observación de Ricardo como hecho general.
- FAQ 5: sin avisos de comandos.

**Observaciones menores (no bloquean)**:

- Newsletter N1: el título y la introducción dicen "consultas" en plural, aunque hay una sola duda.
- LinkedIn 3: agrega la generalización "modelar los datos suele ser el paso más retador", que no sale de los datos.
- FAQ 3 y FAQ 5 son borradores técnicos: deben verificarlos en curaduría personas que conozcan OCI y n8n antes de publicarlos (por ejemplo, "listado del directorio" en la FAQ 3 es impreciso para Object Storage).
