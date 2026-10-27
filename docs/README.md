# Documentación — CommunityLab

Esta carpeta reúne la documentación técnica y funcional de CommunityLab: contrato de datos, integración con Discord, diseño de prompts, validación de salidas y diagramas de arquitectura.

## Contenido

| Archivo | Propósito |
|---|---|
| `contrato-de-datos.md` | Define el contrato de datos del sistema: flujo general, estados de dominio, endpoints HTTP, estructuras de request/response y reglas de persistencia. Es la referencia principal para mantener compatibles el bot, n8n, el panel de curaduría y los procesos de OCI. |
| `guia-bot-discord.md` | Describe cómo debe integrarse el bot de Discord con los webhooks de n8n, incluyendo payloads, campos obligatorios, respuestas esperadas y recomendaciones para mostrar resultados. Revisar su estado y versión antes de usarlo como guía de implementación. |
| `guia-prompt-engineering.md` | Explica cómo diseñar, configurar y validar los prompts de los nodos LLM en n8n: analista de contenido, generador de LinkedIn, destaque para newsletter y FAQ/tip técnico. Incluye schemas, reglas de formato y criterios de calidad. |
| `validacion_prompts_v2.md` | Documenta los casos y criterios de validación para LinkedIn, newsletter estructurado y FAQ/tips. Incluye resultados de corridas, observaciones y ajustes recomendados. |
| `diagrama_proyecto.png` | Diagramas visuales de alto nivel del sistema y de la integración de automatización con n8n. Facilita entender las etapas desde la ingesta hasta la curaduría y distribución. |

## Cómo se relacionan los documentos

```text
contrato-de-datos.md
        │ define campos, endpoints y estados
        ▼
guia-bot-discord.md ───────► Integración de origen
        │
        ▼
guia-prompt-engineering.md ─► Diseño de análisis y generación
        │
        ▼
validacion_prompts_v2.md ───► Pruebas de calidad de las salidas

diagrama_proyecto.png ───────► Vista visual de arquitectura
```

## Orden recomendado de lectura

1. **`diagrama_proyecto.png`** — comprender el flujo general y sus componentes.
2. **`contrato-de-datos.md`** — conocer el contrato operativo vigente y las reglas de integración.
3. **`guia-bot-discord.md`** — revisar la integración de Discord con n8n.
4. **`guia-prompt-engineering.md`** — entender el diseño de prompts y los formatos que consumen los workflows.
5. **`validacion_prompts_v2.md`** — ejecutar o revisar pruebas para comprobar la calidad y consistencia de las salidas.

## Recomendaciones de mantenimiento

- Antes de cambiar un endpoint, un campo, un código HTTP o un estado, actualizar el contrato de datos y revisar los consumidores afectados.
- Mantener alineados los prompts, los schemas de salida, los nodos de n8n y los casos de prueba.
- Probar los prompts dentro de n8n con la estructura de datos real; una prueba aislada no garantiza compatibilidad con el workflow.
- Registrar la fecha, la versión del prompt y los resultados de cada nueva corrida de validación.
- Revisar las versiones y el estado indicados dentro de cada documento: algunos materiales describen hitos anteriores o pueden no reflejar la implementación actual.
- Mantener actualizadas las rutas relativas cuando se muevan archivos o carpetas.

## Nota sobre versiones

Los documentos incluidos tienen versiones y fechas de revisión diferentes. Para integración, toma como referencia el contrato de datos formalizado y contrasta las guías con los workflows desplegados antes de realizar cambios. No asumas que una guía antigua describe automáticamente el estado actual de todos los componentes.

