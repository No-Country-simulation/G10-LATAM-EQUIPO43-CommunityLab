# Contrato de datos — CommunityLab (Hito 1 — Solo OCI)

**Estado:** Vigente para Hito 1
**Versión:** 1.0
**Última revisión:** 2026-10-02
**Hito:** Hito 1 — Flujo base con persistencia en OCI
**Modo:** Solo OCI
**Fuente de verdad de alcance:** PDF oficial del Proyecto – CommunityLab

---

## 1. Propósito

Este documento define el **contrato de datos** del flujo base del MVP en modo Solo OCI:

```text
Cliente HTTP → Webhook n8n → Procesamiento → Paquete OCI → Response HTTP
```

El contrato es la frontera del sistema. El workflow de n8n debe cumplirlo.

Durante este primer hito, el flujo se prueba mediante un cliente HTTP como **Postman**. La integración con el bot de Discord es una etapa posterior que utilizará este mismo contrato.

La persistencia en base de datos **no forma parte de esta versión del contrato**. Su incorporación corresponderá a una evolución posterior del flujo.

Cualquier cambio posterior debe tratarse como evolución del contrato, no como decisión silenciosa de un nodo.

---

## 2. Principios del contrato

1. **Alineado al PDF oficial** — El ejemplo de request/response del documento del proyecto es la base.
2. **Stateless desde el punto de vista del cliente** — El cliente envía un lote y recibe el resultado. No hay sesión ni IDs de dominio obligatorios.
3. **Persistencia mínima del Hito 1** — El flujo contempla la persistencia del paquete de activos en OCI Object Storage.
4. **Campos opcionales explícitos** — Todo lo que no es obligatorio se marca como opcional.
5. **Extensible** — Se pueden agregar tipos de activos o campos de análisis sin romper el contrato base.
6. **Evolutivo** — La incorporación futura de persistencia en BD u otras integraciones deberá documentarse como una nueva evolución del flujo y, cuando corresponda, del contrato.

---

## 3. Entrada (Request)

### 3.1. Endpoint del Hito 1

El workflow se expone mediante un **Webhook HTTP de n8n**.

```text
POST /communitylab/actividades
Content-Type: application/json
```

URL completa de referencia:

```text
https://<host-n8n>/webhook/communitylab/actividades
```

Durante las pruebas puede utilizarse el endpoint de test de n8n:

```text
https://<host-n8n>/webhook-test/communitylab/actividades
```

> `<host-n8n>` depende del entorno donde esté desplegado n8n. No forma parte del contrato de dominio.

> En el Hito 1, Postman se utiliza como cliente de prueba. El bot de Discord utilizará este mismo endpoint cuando se complete su integración.

### 3.2. Schema de entrada

```json
{
  "origen_comunidad": "string",
  "periodo_referencia": "string",
  "interacciones": [
    {
      "autor": "string",
      "canal": "string",
      "tipo": "string",
      "texto": "string",
      "identificador_origen": "string",
      "momento_origen": "string"
    }
  ],
  "opciones": {
    "generar_activos": ["LINKEDIN", "NEWSLETTER", "FAQ"],
    "idioma": "es",
    "tono": "inspirador"
  }
}
```

### 3.3. Campos de la raíz

| Campo                | Tipo   | Obligatorio | Descripción                                                                     |
| -------------------- | ------ | ----------- | ------------------------------------------------------------------------------- |
| `origen_comunidad`   | string | Sí          | Identificador legible de la comunidad de origen (ej. `"Discord_Grupo_ONE_G10"`) |
| `periodo_referencia` | string | Sí          | Periodo o lote que se está procesando                                           |
| `interacciones`      | array  | Sí          | Lista de interacciones a procesar. Debe contener al menos un elemento           |
| `opciones`           | object | No          | Parámetros de control del procesamiento                                         |

### 3.4. Campos de cada interacción

| Campo                  | Tipo   | Obligatorio | Descripción                                            |
| ---------------------- | ------ | ----------- | ------------------------------------------------------ |
| `texto`                | string | Sí          | Contenido textual de la interacción                    |
| `autor`                | string | No          | Nombre o identificador legible del autor               |
| `canal`                | string | No          | Canal de procedencia (ej. `"#logros-y-empleos"`)       |
| `tipo`                 | string | No          | Clasificación inicial de la interacción (ver catálogo) |
| `identificador_origen` | string | No          | ID de la interacción en la plataforma de origen        |
| `momento_origen`       | string | No          | Timestamp de cuando ocurrió (ISO 8601 recomendado)     |

### 3.5. Catálogo inicial de `tipo` (interacción)

Valores orientativos (no cerrados):

```text
testimonio
pregunta_tecnica
duda
logro
feedback
comentario
otro
```

El workflow puede reclasificar o enriquecer el tipo durante el análisis.

### 3.6. Ejemplo de entrada

```json
{
  "origen_comunidad": "Discord_Grupo_ONE_G10",
  "periodo_referencia": "Semana_04",
  "interacciones": [
    {
      "autor": "Mariana Souza",
      "canal": "#logros-y-empleos",
      "tipo": "testimonio",
      "texto": "Comunidad, quede seleccionada para el puesto de Desarrolladora Junior de IA! El proyecto del curso de LangChain y OCI que construi en mi portfolio marco toda la diferencia en la entrevista tecnica. Muy agradecida con la comunidad por todo el apoyo!"
    },
    {
      "autor": "Lucas Albuquerque",
      "canal": "#dudas-langgraph",
      "tipo": "pregunta_tecnica",
      "texto": "Tengo dudas sobre como estructurar los nodos condicionales en LangGraph cuando la respuesta del LLM necesita reintento. Alguien tiene un ejemplo practico de router?"
    }
  ]
}
```

### 3.7. Validaciones mínimas de entrada

* `origen_comunidad` y `periodo_referencia` no vacíos.
* `interacciones` es un array con longitud ≥ 1.
* Cada elemento de `interacciones` tiene `texto` no vacío.
* Si `opciones.generar_activos` viene informado, solo se generan esos tipos.
* Si `opciones.generar_activos` no viene informado, el workflow decide mediante branching según el análisis.

---

## 4. Salida (Response)

### 4.1. Schema de salida

```json
{
  "status": "exito" | "parcial" | "error",
  "resumen_comunidad": {
    "total_interacciones_procesadas": 0,
    "sentimiento_predominante": "string",
    "temas_principales": ["string"],
    "insights_destacados": []
  },
  "activos_distribucion_generados": {
    "post_linkedin": {},
    "destaque_newsletter_semanal": {},
    "sugerencia_contenido_faq": {}
  },
  "almacenamiento_oci": {
    "bucket": "string",
    "ruta_objeto": "string",
    "status": "guardado_con_exito" | "error" | "omitido"
  },
  "errores": [
    {
      "codigo": "string",
      "mensaje": "string",
      "detalle": "string"
    }
  ],
  "meta": {
    "procesado_en": "string",
    "modo": "solo_oci",
    "workflow_execution_id": "string"
  }
}
```

### 4.2. Campos de la raíz de la respuesta

| Campo                            | Tipo   | Obligatorio                  | Descripción                                     |
| -------------------------------- | ------ | ---------------------------- | ----------------------------------------------- |
| `status`                         | string | Sí                           | `"exito"`, `"parcial"` o `"error"`              |
| `resumen_comunidad`              | object | Sí (si existe procesamiento) | Resumen consolidado del lote                    |
| `activos_distribucion_generados` | object | Sí (puede estar vacío)       | Activos generados según el branching            |
| `almacenamiento_oci`             | object | Sí                           | Resultado del intento de guardado en OCI        |
| `errores`                        | array  | No                           | Presente cuando hubo fallos parciales o totales |
| `meta`                           | object | No                           | Metadatos de ejecución                          |

### 4.3. `resumen_comunidad`

| Campo                            | Tipo            | Obligatorio | Descripción                                          |
| -------------------------------- | --------------- | ----------- | ---------------------------------------------------- |
| `total_interacciones_procesadas` | integer         | Sí          | Cantidad de interacciones del lote que se procesaron |
| `sentimiento_predominante`       | string          | Sí          | Clasificación agregada                               |
| `temas_principales`              | array de string | Sí          | Lista de temas detectados                            |
| `insights_destacados`            | array de string | No          | Frases o hallazgos relevantes extraídos              |

### 4.4. Estructura de los activos generados

El objeto `activos_distribucion_generados` es un mapa cuya clave es el tipo de activo.

Los tipos mínimos esperados por el PDF / ejemplos son:

| Clave                         | Descripción                                          |
| ----------------------------- | ---------------------------------------------------- |
| `post_linkedin`               | Publicación orientada a LinkedIn                     |
| `destaque_newsletter_semanal` | Bloque para newsletter / Community Highlights        |
| `sugerencia_contenido_faq`    | Tip / FAQ / contenido educativo derivado de una duda |

#### 4.4.1. `post_linkedin`

```json
{
  "titulo": "string",
  "copy": "string",
  "canal_recomendado": "string",
  "potencial_engagement": "Alto" | "Medio" | "Bajo",
  "hashtags": [],
  "origen_interacciones": []
}
```

#### 4.4.2. `destaque_newsletter_semanal`

```json
{
  "seccion": "string",
  "titular": "string",
  "resumen": "string",
  "origen_interacciones": []
}
```

#### 4.4.3. `sugerencia_contenido_faq`

```json
{
  "tema": "string",
  "origen": "string",
  "status": "string",
  "contenido_sugerido": "string"
}
```

> Se pueden agregar más tipos de activos sin romper el contrato, siempre que se documenten.

### 4.5. `almacenamiento_oci`

| Campo         | Tipo   | Obligatorio | Descripción                                     |
| ------------- | ------ | ----------- | ----------------------------------------------- |
| `bucket`      | string | Sí          | Nombre del bucket utilizado                     |
| `ruta_objeto` | string | Sí          | Clave / path del objeto dentro del bucket       |
| `status`      | string | Sí          | `"guardado_con_exito"`, `"error"` u `"omitido"` |

### 4.6. Ejemplo de salida

```json
{
  "status": "exito",
  "resumen_comunidad": {
    "total_interacciones_procesadas": 2,
    "sentimiento_predominante": "Altamente Positivo",
    "temas_principales": [
      "Contratacion / Logros",
      "LangGraph / Nodos Condicionales"
    ]
  },
  "activos_distribucion_generados": {
    "post_linkedin": {
      "titulo": "De la Comunidad al Mercado: El impacto de los proyectos practicos de IA",
      "copy": "Nada nos da mas orgullo que ver a nuestros talentos conquistando el mercado de tecnologia!",
      "canal_recomendado": "LinkedIn Oficial",
      "potencial_engagement": "Alto"
    },
    "destaque_newsletter_semanal": {
      "seccion": "Logro de la Semana",
      "titular": "Estudiante consigue empleo dev con portfolio de IA en Oracle Cloud",
      "resumen": "Mariana Souza obtuvo su primera oportunidad como Dev Jr de IA destacando proyectos desarrollados durante la formacion."
    },
    "sugerencia_contenido_faq": {
      "tema": "Tip Rapido: Como crear nodos de reintento en LangGraph",
      "origen": "Duda frecuente planteada por Lucas Albuquerque en el canal de soporte",
      "status": "derivado_a_mentoria"
    }
  },
  "almacenamiento_oci": {
    "bucket": "communitylab-activos-marketing",
    "ruta_objeto": "activos/Semana_04/paquete-20261001T221500Z.json",
    "status": "guardado_con_exito"
  },
  "meta": {
    "procesado_en": "2026-10-01T22:15:00Z",
    "modo": "solo_oci"
  }
}
```

---

## 5. Paquete que se sube a OCI Object Storage

### 5.1. Contenido del paquete

En el **Hito 1 — Solo OCI**, el paquete que se persiste es un JSON que contiene:

* Metadatos del lote.
* El resumen de la comunidad.
* Los activos generados.
* Información opcional de la ejecución.

El contenido del objeto en OCI puede corresponder al mismo JSON de la respuesta o a una versión ligeramente enriquecida con contexto interno.

### 5.2. Estructura recomendada del objeto en OCI

```json
{
  "meta": {
    "origen_comunidad": "Discord_Grupo_ONE_G10",
    "periodo_referencia": "Semana_04",
    "procesado_en": "2026-10-01T22:15:00Z",
    "modo": "solo_oci",
    "workflow_execution_id": "opcional"
  },
  "resumen_comunidad": {},
  "activos_distribucion_generados": {},
  "almacenamiento_oci": {
    "bucket": "communitylab-activos-marketing",
    "ruta_objeto": "activos/Semana_04/paquete-20261001T221500Z.json",
    "status": "guardado_con_exito"
  }
}
```

### 5.3. Convención de ruta del objeto

La convención adoptada para este hito es:

```text
activos/{periodo_referencia}/paquete-{timestamp}.json
```

Ejemplo:

```text
activos/Semana_04/paquete-20261001T221500Z.json
```

Esta convención podrá evolucionar junto con el diseño de persistencia futuro, pero constituye la referencia para el Hito 1.

### 5.4. Bucket

* Nombre orientativo: `communitylab-activos-marketing` (o el que se cree en la cuenta Always Free).
* Región y namespace: configuración técnica de n8n / OCI, **fuera del contrato de dominio**.
* La disponibilidad efectiva del servicio OCI depende de la infraestructura asignada al equipo.

> **Estado de OCI:** la integración se encuentra parcialmente configurada. La finalización de la infraestructura de OCI está pendiente de la disponibilidad de la capa de servicios utilizada por el equipo. Esto no modifica el contrato de datos del Hito 1.

---

## 6. Códigos HTTP, status y manejo de errores

Los códigos HTTP indican el resultado de la comunicación con el endpoint, mientras que `status` describe el resultado del procesamiento.

| HTTP                        | `status`  | Significado                                                              |
| --------------------------- | --------- | ------------------------------------------------------------------------ |
| `200 OK`                    | `exito`   | Lote procesado correctamente y paquete generado para persistencia en OCI |
| `200 OK`                    | `parcial` | El procesamiento terminó, pero se produjeron uno o más fallos parciales  |
| `400 Bad Request`           | `error`   | La entrada no cumple las validaciones mínimas del contrato               |
| `500 Internal Server Error` | `error`   | Fallo crítico no controlado durante la ejecución del workflow            |

Cuando `status` sea `parcial` o `error`, se recomienda incluir el array `errores`.

En errores de validación (`400`), la persistencia en OCI debe omitirse.

---

## 7. Qué NO forma parte del contrato (Hito 1 — Solo OCI)

En este hito no se exponen ni se exigen:

* IDs de entidades de dominio (`id_actividad`, `id_analisis`, `id_hallazgo`, …).
* Referencias a tablas PostgreSQL.
* Historial de versiones o revisiones.
* Credenciales.
* Nombres de nodos de n8n.
* IDs internos de ejecución, excepto el opcional `workflow_execution_id` en `meta`.

La **persistencia en base de datos** queda fuera del alcance de esta versión y podrá incorporarse en una evolución posterior del contrato.

---

## 8. Relación con el flujo n8n

```text
1. Cliente HTTP envía Request
   └── Durante el Hito 1: Postman
2. Webhook recibe Request
3. Validación de entrada
4. Normalización
5. Análisis LLM + branching
6. Generación de activos
7. Construcción del Response + Paquete OCI
8. Intento de subida del paquete a OCI Object Storage
9. Respuesta HTTP al cliente
```

El bot de Discord no forma parte todavía de la ejecución del Hito 1.

Cuando se complete su integración, reemplazará al cliente de prueba:

```text
                 Hito 1
Postman ───────→ Webhook n8n
                     │
                     ↓
                 Workflow


              Integración futura
Bot Discord ─→ Webhook n8n
                     │
                     ↓
                 Workflow
```

El contrato se cierra antes de detallar los nodos. Los nodos se diseñan para producir las estructuras definidas en este documento.

---

## 9. Evolución prevista

El Hito 1 establece el flujo base con persistencia en OCI.

Una evolución posterior contempla la incorporación de **persistencia en base de datos**:

```text
Hito 1
Cliente HTTP
    ↓
Webhook
    ↓
Procesamiento
    ↓
Activos
    ↓
OCI
    ↓
Response


Evolución posterior
Cliente HTTP / Discord
    ↓
Webhook
    ↓
Procesamiento
    ↓
Activos
    ├──→ Base de datos
    └──→ OCI
    ↓
Response
```

La incorporación de la BD deberá documentarse como una nueva etapa del diseño y podrá requerir una nueva versión del contrato.

---

## 10. Criterio de cierre del contrato del Hito 1

El contrato se considera listo para el Hito 1 cuando el equipo confirma:

* [x] Schema de entrada.
* [x] Schema de salida.
* [x] Estructura mínima de cada tipo de activo del MVP.
* [x] Convención de ruta del paquete en OCI.
* [x] Comportamiento de `status` / `errores`.
* [x] Códigos HTTP principales.

La integración efectiva con la infraestructura OCI y la futura persistencia en BD son tareas de implementación/evolución, no cambios necesarios para cerrar la estructura del contrato del Hito 1.

---

## 11. Estado actual

```text
PDF oficial
    ↓
MODELO DE DATOS v3.0 (dual-mode)
    ↓
CONTRATO DE DATOS v1.0
    ↓
HITO 1 — FLUJO BASE SOLO OCI
    ├── Webhook HTTP
    ├── Procesamiento
    ├── Generación de activos
    ├── Integración OCI parcialmente configurada
    └── Respuesta HTTP
    ↓
SIGUIENTE EVOLUCIÓN
    └── Persistencia en BD
```

**Nota:** Postman se utiliza actualmente como cliente de prueba. La integración con el bot de Discord corresponde a una etapa posterior.

---

**Fin del documento — Contrato de datos v1.0 (Hito 1 — Solo OCI)**
