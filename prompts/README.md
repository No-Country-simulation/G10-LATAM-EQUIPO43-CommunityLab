# Prompts de CommunityLab (IA/Prompts)

Esta carpeta contiene los prompts que usa el flujo de n8n para analizar la actividad de la comunidad y generar los activos de distribución. **Los archivos de esta carpeta son la versión vigente.** Los scripts de `scripts/` son el prototipo inicial en Python y llevan prompts embebidos de versiones anteriores.

## Versiones vigentes

| Archivo | Versión | Qué hace | Temperatura | Esquema de salida |
|---|---|---|---|---|
| `system_prompt_analisis.md` | v1.0 | Clasifica sentimiento, tema y relevancia de cada interacción | 0.2 | `response_schema_analisis.json` |
| `system_prompt_linkedin.md` | v2.1 | Genera el post de LinkedIn a partir de un testimonio o logro | 0.5 | `response_schema_linkedin.json` |
| `system_prompt_newsletter.md` | v3.1 | Genera la newsletter semanal con salida estructurada | 0.3 | `response_schema_newsletter.json` |
| `system_prompt_faq_tips.md` | v1.1 | Genera un borrador de FAQ o Tip a partir de una duda | 0.3 | `response_schema_faq_tips.json` |

Modelo usado en las pruebas: `gemini-3.8-flash`, con respuesta en formato JSON.

## Cómo usarlos en n8n

Cada archivo `system_prompt_*.md` tiene dos bloques de texto:

1. **Mensaje de usuario (plantilla)**: va en el campo del mensaje del usuario. Usa `{{ JSON.stringify($json, null, 2) }}` para enviar el lote completo.
2. **System message**: va en el campo de instrucciones del sistema.

Configura la temperatura de la tabla y activa la salida JSON si el nodo lo permite. El historial de cambios está al final de cada archivo.

## Entrada que esperan los prompts

El lote de la comunidad con esta forma (los campos entre corchetes son opcionales):

```json
{
  "id_lote": "1",
  "origen_comunidad": "Discord_Grupo_ONE_G10",
  "opciones": { "generar_activos": ["LINKEDIN", "NEWSLETTER", "FAQ"] },
  "resumen_comunidad": {
    "total_interacciones_procesadas": 12,
    "temas_principales": ["..."]
  },
  "evidencias": {
    "testimonios_logros": [{ "id_actividad": 3, "autor": "...", "texto_original": "..." }],
    "preguntas_dudas": [{ "id_actividad": 2, "autor": "...", "texto_original": "..." }]
  }
}
```

El nombre `id_actividad` y su tipo numérico son un supuesto basado en el ejemplo del equipo de orquestación; si el lote real usa otro nombre, hay que cambiarlo en el system message de la newsletter.

## Salida de cada prompt

- **LinkedIn**: `titulo`, `copy`, `canal_recomendado`, `potencial_engagement`, `hashtags`, `origen_interacciones`. Campos extra: `tipo_experiencia`, `omitido`, `motivo`. Los hashtags van en su propio campo, no dentro del `copy`.
- **Newsletter**: `status` (`generado` o `insuficiente`), `titulo`, `introduccion`, `secciones` (cada una con `titulo`, `contenido`, `ids_actividades`), `cierre` y `motivo`. Las secciones son "Logro de la Semana", "Tema en Tendencia" y "Dato de la Comunidad". Este formato reemplaza al de la sección 4.4.2 del contrato de datos v1.0.
- **FAQs y Tips**: `tema`, `origen`, `status` (`borrador_para_curaduria`, `derivado_a_mentoria` u `omitido`), `contenido_sugerido`, `formato` (`FAQ`, `TIP` o `NINGUNO`). Campos extra: `omitido`, `motivo`.

Cuando no hay material para generar un activo, LinkedIn y FAQ devuelven `omitido: true` con un `motivo`, y la newsletter devuelve `status: "insuficiente"`.

## Criterios comunes de fidelidad

- Solo se usa información presente en el lote: no se inventan empresas, puestos, cifras, ids ni herramientas.
- Se respeta el alcance real de cada logro (una entrevista no es una contratación).
- El feedback se refleja con las palabras y la intensidad con que lo expresó cada persona, atribuido a su autor.
- Una sola evidencia no se presenta como tendencia.
- El contenido técnico de FAQs y Tips es un borrador: debe revisarse en curaduría antes de publicarse.

## Pruebas

- Casos de prueba: `data/casos_prueba_activos.json` (LinkedIn y FAQ) y `data/casos_prueba_newsletter_estructurado.json` (newsletter).
- Workflow de n8n que ejecuta los 15 casos y valida cada salida: `prompts/pruebas/workflow_prueba_prompts.json`.
- Criterios y resultados de cada corrida: `docs/validacion_prompts_v2.md`.
