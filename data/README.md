# Data — CommunityLab

Esta carpeta contiene datasets de ejemplo, resultados de análisis y casos de prueba utilizados para validar el flujo de CommunityLab: desde las interacciones de la comunidad hasta la generación de activos de contenido.

## Contenido

| Archivo | Descripción |
|---|---|
| `dataset_prueba_interacciones.json` | Dataset de ejemplo con mensajes de la comunidad, autores, canales y tipos de interacción. Sirve como entrada para probar el análisis de conversaciones. |
| `resultados_analisis.json` | Ejemplo de resultados del análisis de interacciones: sentimiento, categoría temática, relevancia, tipo de insight, citas y justificación. |
| `activos_generados.json` | Ejemplo de activos derivados del análisis, incluyendo una publicación para LinkedIn y un resumen para newsletter. |
| `casos_prueba_activos.json` | Casos de prueba para la generación de activos a partir de distintos lotes, con evidencias de testimonios/logros y preguntas/dudas. |
| `casos_prueba_newsletter_estructurado.json` | Casos de prueba específicos para la generación de newsletters, con opciones de generación, resumen de comunidad y evidencias asociadas a cada lote. |

## Cómo encajan en el proyecto

```text
Interacciones de ejemplo
(dataset_prueba_interacciones.json)
            │
            ▼
Análisis de mensajes
(resultados_analisis.json)
            │
            ▼
Generación de contenido
(activos_generados.json)

Casos de prueba:
├── casos_prueba_activos.json
└── casos_prueba_newsletter_estructurado.json
```

Los archivos representan ejemplos y escenarios de validación. No deben interpretarse como datos en tiempo real de Discord ni como garantía de que el contenido generado haya sido aprobado o publicado.

## Estructura de los datos

### `dataset_prueba_interacciones.json`

Contiene información de interacciones de ejemplo, incluyendo:

- Origen de la comunidad y período de referencia.
- Autor y canal de cada mensaje.
- Tipo de interacción.
- Texto original del mensaje.

### `resultados_analisis.json`

Incluye un resumen agregado y las interacciones analizadas individualmente. Cada análisis puede contener:

- `sentimiento`
- `tema_categoria`
- `tema_libre`
- `score_relevancia`
- `tipo_insight`
- `cita_extraida`
- `razon_relevancia`

### `activos_generados.json`

Contiene ejemplos de contenido generado para distribución, como:

- `post_linkedin`: autor destacado y copy de la publicación.
- `resumen_newsletter`: texto organizado en secciones editoriales.

### `casos_prueba_activos.json`

Agrupa lotes de prueba con opciones de generación, resúmenes de comunidad, temas principales y evidencias que pueden incluir testimonios/logros y preguntas/dudas.

### `casos_prueba_newsletter_estructurado.json`

Agrupa escenarios orientados a newsletters. Cada caso incluye un identificador de lote, origen de comunidad, opciones, resumen de interacciones y evidencias relevantes. También contempla casos con pocas o ninguna evidencia, útiles para comprobar cómo responde el flujo ante entradas distintas.

## Uso

1. Utiliza `dataset_prueba_interacciones.json` como conjunto de entrada de ejemplo.
2. Compara los resultados del análisis con la estructura de `resultados_analisis.json`.
3. Revisa `activos_generados.json` como ejemplo de salida de generación de contenido.
4. Usa los archivos `casos_prueba_*.json` para probar escenarios con diferentes tipos de evidencia y opciones de generación.
5. Verifica las salidas de n8n y la revisión posterior desde el frontend antes de considerar un activo aprobado.

Los archivos son JSON; pueden inspeccionarse con cualquier editor de texto o procesarse desde Python, n8n u otras herramientas compatibles con JSON.

## Consideraciones

- Estos archivos contienen datos de prueba y ejemplos ilustrativos.
- Las personas, mensajes y resultados que aparecen en ellos forman parte de los ejemplos incluidos en los propios archivos; no deben tratarse automáticamente como información real o vigente.
- Si actualizas la estructura esperada por los workflows, revisa también estos datasets y casos de prueba para mantenerlos compatibles.
- Evita guardar tokens, contraseñas, claves API u otras credenciales en esta carpeta.
