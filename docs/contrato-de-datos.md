# Contrato de datos — CommunityLab

**Estado:** Formalizado  
**Versión:** 2.0  
**Última revisión:** 2026-10-15  
**Modo:** Persistencia de dominio + OCI (dual)  
**Fuente de verdad de esquema:** `communitylab_db_v3.1.sql`  
**Documentos de referencia:** `modelo-de-datos-b1-persistencia.md`, workflows n8n de ingesta, procesamiento, curaduría, newsletter y OCI  

---

## 1. Propósito

Este documento define el **contrato de datos** de CommunityLab en su estado actual:

```text
Ingesta (tiempo real / batch)
    → Persistencia (PostgreSQL)
    → Análisis y generación (n8n + LLM)
    → Curaduría (panel)
    → Almacenamiento de versiones aprobadas (OCI Object Storage)
```

El contrato es la frontera del sistema hacia clientes (bot Discord, panel de curaduría, jobs programados y consumidores de OCI).  
Cualquier cambio de campos, códigos HTTP o semántica de estados debe tratarse como evolución explícita de este contrato.

---

## 2. Principios del contrato

1. **PostgreSQL es la fuente de verdad operativa** — lotes, actividades, análisis, activos, versiones y cola OCI viven en la base.
2. **OCI es el artefacto de distribución** — solo se persisten en Object Storage las **versiones aprobadas** (una fila por versión en `almacenamiento_oci`).
3. **Idempotencia donde aplica** — ingesta por `identificador_origen`, newsletter por `clave_idempotencia`, aprobación OCI por `id_version`.
4. **Estados explícitos** — no se infieren; se consultan y se actualizan de forma determinista.
5. **Campos opcionales explícitos** — todo lo no obligatorio se documenta como tal.
6. **Extensible** — nuevos tipos de activo o campos de análisis se agregan sin romper el contrato base.

---

## 3. Catálogo de estados (dominio)

### 3.1. `lote_procesamiento.estado`

| Valor | Significado |
|-------|-------------|
| `recibido` | Lote creado; aún no termina validación/normalización |
| `procesando` | Análisis / generación en curso |
| `completado` | Pipeline OK |
| `parcial` | Algo útil se guardó, pero falló un paso o no hubo contenido suficiente |
| `fallido` | Fallo grave; se puede reprocesar |

### 3.2. `lote_procesamiento.tipo_operacion`

| Valor | Significado |
|-------|-------------|
| `procesamiento` | Job operativo de análisis + generación de activos |
| `newsletter` | Solicitud editorial de newsletter (idempotente) |

### 3.3. `actividad.estado_procesamiento`

| Valor | Significado |
|-------|-------------|
| `pendiente` | Ingresada; aún no asignada a un lote |
| `en_lote` | Asignada a un lote; pendiente de análisis |
| `analizada` | Análisis LLM persistido |
| `omitida` | Descartada de forma consciente |
| `error` | Fallo al procesar |

### 3.4. `activo_generado.estado_curaduria`

| Valor | Significado |
|-------|-------------|
| `borrador` | Generado por el flujo; aún no revisado (o re-editado) |
| `aprobado` | Aceptado por curaduría; versión aprobada registrada para OCI |
| `rechazado` | Rechazado (con comentario opcional) |
| `publicado` | Ya se dio por distribuido fuera del sistema (no editable) |

### 3.5. `almacenamiento_oci.status`

| Valor | Significado |
|-------|-------------|
| `pendiente` | Aún no se intentó subir (o listo para reintento) |
| `procesando` | Intento de subida en curso |
| `guardado_con_exito` | Objeto en el bucket |
| `error` | Falló la subida; reintento programado |
| `omitido` | No se subió (decisión de negocio) |

### 3.6. `version_activo.origen_version`

| Valor | Significado |
|-------|-------------|
| `ia` | Generación inicial del pipeline |
| `usuario` | Edición humana desde el panel |

---

## 4. Endpoints HTTP

Todos los paths se materializan como Webhooks de n8n bajo el prefijo de la instancia.  
En producción se asume base `…/webhook/` (o el path configurado).

---

### 4.1. Ingesta en tiempo real

**Endpoint:** `POST /communitylab/actividades`  
**Workflow:** Ingesta en Tiempo Real – CommunityLab  
**Propósito:** capturar un mensaje individual de Discord (u origen compatible), resolver Fuente / Canal / Autor (upsert) y persistir la actividad en estado `pendiente` **sin requerir un lote activo**.

#### Request

```json
{
  "server_id": "string",
  "server_name": "string",
  "message_id": "string",          // obligatorio
  "channel_id": "string",          // obligatorio
  "channel_name": "string",
  "user_id": "string",             // obligatorio
  "username": "string",
  "display_name": "string",
  "mention": "string",
  "message": "string",             // obligatorio, no vacío
  "timestamp": "string"            // ISO 8601 recomendado
}
```

| Campo | Obligatorio | Notas |
|-------|-------------|-------|
| `message_id` | Sí | → `actividad.identificador_origen` |
| `channel_id` | Sí | → `canal.identificador_origen` |
| `user_id` | Sí | → `autor.identificador_origen` |
| `message` | Sí | Texto no vacío → `actividad.contenido` |
| Resto | No | Se usan para nombre legible y contexto |

#### Normalización interna (antes de SQL)

```json
{
  "origen_comunidad": "Discord_<server_name_normalizado>",
  "identificador_origen": "<message_id>",
  "contenido": "<message>",
  "timestamp_origen": "<timestamp>",
  "canal": {
    "identificador_origen": "<channel_id>",
    "nombre": "#<channel_name>"
  },
  "autor": {
    "identificador_origen": "<user_id>",
    "nombre": "<display_name | username>"
  }
}
```

#### Persistencia

- Upsert de `fuente` por `nombre`.
- Upsert de `canal` por `(id_fuente, identificador_origen)`.
- Upsert de `autor` por `(id_fuente, identificador_origen)`.
- Upsert de `actividad` por `(id_fuente, identificador_origen)` con:
  - `id_lote = NULL`
  - `estado_procesamiento = 'pendiente'`
  - Si el contenido o el momento cambian respecto a una fila existente → se vuelve a marcar `pendiente`.

#### Responses

| Código | Condición | Cuerpo (resumen) |
|--------|-----------|------------------|
| `200` | Actividad persistida | Datos de la fila insertada/actualizada (id_actividad, estado, …) |
| `400` | Payload inválido | `{ status: "error", errores: [{ codigo, mensaje, detalle }], … }` |

---

### 4.2. Consulta de activos por lote (panel de curaduría)

**Endpoint:** `GET|POST /communitylab/activos?id_lote=<entero positivo>`  
**Workflow:** CommunityLab — Consulta de activos y versiones (rama W*)  
**Propósito:** lectura para la interfaz de curaduría. **No modifica** estados ni crea versiones.

#### Query

| Parámetro | Tipo | Obligatorio | Validación |
|-----------|------|-------------|------------|
| `id_lote` | string/number | Sí | Entero positivo seguro |

#### Response 200

```json
{
  "status": "exito",
  "total": 0,
  "activos": [
    {
      "id_activo": 1,
      "id_lote": 10,
      "tipo_activo": "LINKEDIN",
      "contenido": { },
      "estado_curaduria": "borrador",
      "id_version_actual": 3,
      "numero_version": 1,
      "origen_version": "ia",
      "motivo_cambio": null,
      "creado_por": null,
      "version_creada_en": "…",
      "id_version_aprobada": null,
      "comentario_curaduria": null,
      "revisado_en": null,
      "activo_creado_en": "…",
      "actualizado_en": "…"
    }
  ]
}
```

Si el lote no tiene activos: `activos: []`, `total: 0`.

#### Errores

| Código | Condición |
|--------|-----------|
| `400` | `id_lote` ausente, vacío, no numérico, decimal, ≤ 0 o no safe integer |

---

### 4.3. Historial de versiones de un activo

**Endpoint:** `GET /communitylab/activos/:id_activo/versiones`  
**Workflow:** CommunityLab — Consulta de activos y versiones (rama V*)  
**Propósito:** recuperar el activo y todas sus versiones **sin modificar datos**.

#### Path

| Parámetro | Tipo | Obligatorio |
|-----------|------|-------------|
| `id_activo` | entero positivo | Sí |

#### Response 200

```json
{
  "activo": {
    "id_activo": 2,
    "id_lote": 10,
    "tipo_activo": "NEWSLETTER",
    "estado_curaduria": "borrador",
    "id_version_actual": 5,
    "id_version_aprobada": null,
    "comentario_curaduria": null,
    "revisado_en": null,
    "creado_en": "…",
    "actualizado_en": "…"
  },
  "versiones": [
    {
      "id_version": 5,
      "numero_version": 2,
      "contenido": { },
      "origen_version": "usuario",
      "motivo_cambio": "Ajustes de redacción",
      "creado_por": "usuario_curador",
      "creado_en": "…",
      "es_actual": true,
      "es_aprobada": false
    }
  ],
  "total_versiones": 2
}
```

Las versiones se ordenan de más reciente a más antigua (`numero_version DESC`).

#### Errores

| Código | Condición |
|--------|-----------|
| `400` | `id_activo` inválido |
| `404` | No existe el activo |

---

### 4.4. Editar activo (nueva versión)

**Endpoint:** `PATCH /communitylab/activos/:id_activo`  
**Workflow:** CommunityLab — Curaduría de Activos  
**Propósito:** actualizar el contenido y registrar una **nueva versión** (`origen_version = 'usuario'`). El activo vuelve a `borrador`.

#### Path + Body

```json
{
  "contenido": { "text": "Nuevo contenido del activo" },
  "motivo_cambio": "Corrección editorial",
  "creado_por": "usuario_qa"
}
```

| Campo | Obligatorio | Validación |
|-------|-------------|------------|
| `id_activo` (path) | Sí | Entero positivo |
| `contenido` | Sí | Objeto; `contenido.text` cadena no vacía (si el contrato del frontend lo exige así) |
| `motivo_cambio` | Sí | Cadena no vacía |
| `creado_por` | Sí | Cadena no vacía |

#### Semántica (función `communitylab_editar_activo`)

- Solo si el activo existe y **no** está en estado `publicado`.
- Crea `version_activo` con el siguiente `numero_version`.
- Actualiza `activo_generado.contenido`, `id_version_actual` y fuerza `estado_curaduria = 'borrador'`.

#### Responses

| Código | Condición |
|--------|-----------|
| `200` | Edición OK; devuelve activo + datos de la nueva versión |
| `400` | Validación de path/body |
| `404` | Activo inexistente |
| `409` | Estado incompatible (p. ej. `publicado`) |

---

### 4.5. Aprobar activo

**Endpoint:** `POST /communitylab/activos/:id_activo/aprobar`  
**Workflow:** CommunityLab — Curaduría de Activos  
**Propósito:** aprobar la **versión actual**, marcar el activo como `aprobado` y registrar (o reutilizar) la fila de `almacenamiento_oci` en estado `pendiente` **en la misma transacción**.

#### Body

```json
{
  "comentario_curaduria": "News revisado y aprobado.",
  "revisado_por": "usuario_curador"
}
```

| Campo | Obligatorio | Notas |
|-------|-------------|-------|
| `revisado_por` | Sí | Validado en el workflow; la función SQL actual recibe solo comentario |
| `comentario_curaduria` | No | Texto libre |

#### Semántica (función `communitylab_aprobar_activo`)

- Solo desde `estado_curaduria = 'borrador'` y con `id_version_actual` válido.
- `id_version_aprobada = id_version_actual`.
- `INSERT … ON CONFLICT (id_version) DO NOTHING` en `almacenamiento_oci` (una fila por versión).
- **No** llama a OCI; solo deja la cola lista para el job de subida.

#### Response 200 (éxito)

```json
{
  "success": true,
  "mensaje": "El activo fue aprobado correctamente y quedó registrado para almacenamiento OCI.",
  "activo": {
    "id_activo": 2,
    "id_lote": 10,
    "tipo_activo": "NEWSLETTER",
    "estado_curaduria": "aprobado",
    "id_version_actual": 5,
    "id_version_aprobada": 5,
    "comentario_curaduria": "…",
    "revisado_en": "…"
  },
  "almacenamiento_oci": {
    "id_almacenamiento": 7,
    "status": "pendiente"
  }
}
```

#### Errores

| Código | Condición |
|--------|-----------|
| `400` | Validación |
| `404` | Activo inexistente |
| `409` | Estado incompatible / versión actual inválida |

---

### 4.6. Rechazar activo

**Endpoint:** `POST /communitylab/activos/:id_activo/rechazar`  
**Workflow:** CommunityLab — Curaduría de Activos  
**Propósito:** marcar el activo como `rechazado`.

#### Body

```json
{
  "comentario_curaduria": "News fuera de tono.",
  "revisado_por": "usuario_curador"
}
```

| Campo | Obligatorio |
|-------|-------------|
| `revisado_por` | Sí |
| `comentario_curaduria` | No |

#### Semántica

- Permitido desde `borrador` o `aprobado`.
- No limpia automáticamente `id_version_aprobada` si ya existía (comportamiento actual del SQL del workflow).
- `revisado_por` se valida en el workflow; la consulta de rechazo actual **no lo persiste** (pendiente técnico si se requiere trazabilidad).

#### Responses

| Código | Condición |
|--------|-----------|
| `200` | Rechazo OK |
| `400` | Validación |
| `404` | Activo inexistente |
| `409` | Estado incompatible |

---

### 4.7. Generación de newsletter (editorial, idempotente)

**Endpoint:** `POST /communitylab/generar-newsletter`  
**Workflow:** Generador Newsletter  
**Propósito:** generar (o recuperar) un activo `NEWSLETTER` a partir de actividades ya **analizadas** en una ventana temporal, con reserva idempotente de lote editorial.

#### Request

```json
{
  "origen_comunidad": "Discord_Servidor_G10_Pruebas",
  "ventana_desde": "2026-10-01T00:00:00.000Z",
  "ventana_hasta": "2026-10-08T00:00:00.000Z",
  "opciones": {
    "idioma": "es",
    "tono": "inspirador",
    "min_actividades_utiles": 3,
    "max_actividades": 30
  }
}
```

| Campo | Obligatorio | Validación |
|-------|-------------|------------|
| `origen_comunidad` | Sí | No vacío; debe resolver a `fuente.nombre` |
| `ventana_desde` | Sí | Fecha válida |
| `ventana_hasta` | Sí | Fecha válida y **estrictamente mayor** que `ventana_desde` |
| `opciones.*` | No | Defaults: idioma=`es`, tono=`inspirador`, min=3, max=30 (acotado 1–100) |

#### Clave de idempotencia

```text
newsletter:v1:{origen_comunidad, ventana_desde, ventana_hasta, opciones_normalizadas}
```

Se almacena en `lote_procesamiento.clave_idempotencia` con `tipo_operacion = 'newsletter'`.  
Índice único parcial: evita solicitudes equivalentes duplicadas.

#### Flujo de reserva

| Resultado de reserva | HTTP | Comportamiento |
|----------------------|------|----------------|
| Reserva nueva | continúa | Consulta actividades → genera → persiste |
| Newsletter ya completado | `200` | Devuelve el activo existente (idempotente) |
| Solicitud en proceso | `202` | No inicia una segunda generación |
| Estado que requiere revisión | `409` | No regenera automáticamente |

#### Contenido insuficiente

Si no hay suficientes actividades útiles (umbral `min_actividades_utiles`):

- El lote editorial se marca `parcial`.
- Response `200` con `status: "sin_contenido_suficiente"`, `newsletter_generado: false`.

#### Response 200 (generado o idempotente)

```json
{
  "status": "exito",
  "newsletter_generado": true,
  "idempotente": false,
  "newsletter": {
    "id_activo": 12,
    "id_lote": 45,
    "tipo_activo": "NEWSLETTER",
    "estado_curaduria": "borrador",
    "id_version_actual": 20,
    "numero_version": 1,
    "estado_lote": "completado",
    "contenido": {
      "titulo": "…",
      "introduccion": "…",
      "secciones": [
        {
          "titulo": "Logro de la Semana",
          "contenido": "…",
          "ids_actividades": [1, 2]
        }
      ],
      "cierre": "…",
      "status": "generado",
      "motivo": ""
    }
  },
  "meta": {
    "origen_comunidad": "…",
    "ventana_desde": "…",
    "ventana_hasta": "…"
  }
}
```

#### Estructura editorial del contenido (salida del LLM)

| Campo | Tipo | Notas |
|-------|------|-------|
| `status` | `"generado"` \| `"insuficiente"` | |
| `titulo` | string | Máx. ~12 palabras |
| `introduccion` | string | 1–2 frases |
| `secciones` | array | Títulos fijos: `"Logro de la Semana"`, `"Tema en Tendencia"`, `"Dato de la Comunidad"` |
| `secciones[].ids_actividades` | array de integer | IDs reales usados como evidencia |
| `cierre` | string | |
| `motivo` | string | Vacío si generado; explicación si insuficiente |

#### Códigos HTTP

| Código | Significado |
|--------|-------------|
| `400` | Validación de request |
| `200` | Generado, idempotente o sin contenido suficiente |
| `202` | Solicitud equivalente en curso |
| `409` | Reserva en estado que requiere revisión |

---

### 4.8. Persistencia OCI de versiones aprobadas (job)

**Trigger:** Schedule cada 5 minutos  
**Workflow:** CommunityLab — Persistencia OCI de Versiones Aprobadas  
**Propósito:** reclamar filas de `almacenamiento_oci` pendientes/error/estancadas, subir el JSON de la versión a Object Storage y actualizar el estado.

#### Selección (cola)

- `status IN ('pendiente', 'error')` y `proximo_intento_en <= NOW()`, o
- `status = 'procesando'` y `procesando_desde < NOW() - 15 minutes` (estancado)
- `intentos < 8`
- `FOR UPDATE SKIP LOCKED`, límite 10

#### Paquete subido

```json
{
  "meta": {
    "sistema": "CommunityLab",
    "id_activo": 2,
    "id_version": 5,
    "numero_version": 2,
    "generado_en": "2026-10-15T…"
  },
  "contenido": { }
}
```

Ruta por defecto (si no venía informada):

```text
activos/{id_activo}/versiones/v{numero_version}/activo-{id_activo}-version-{id_version}.json
```

Bucket por defecto: `communitylab-activos-marketing`.

#### Actualización de estado

| Resultado | Acción |
|-----------|--------|
| Éxito | `status = 'guardado_con_exito'`, `guardado_en = NOW()` |
| Fallo | `status = 'error'`, `detalle_error`, backoff exponencial en `proximo_intento_en` |

Este job **no** es un endpoint HTTP de negocio; es un worker interno.

---

## 5. Modelo de datos (resumen alineado a v3.1)

### 5.1. Entidades principales

| Entidad | Rol |
|---------|-----|
| `fuente` | Comunidad de origen (`nombre` único) |
| `canal` | Canal dentro de la fuente; unique parcial por `identificador_origen` |
| `autor` | Autor dentro de la fuente; unique parcial por `identificador_origen` |
| `lote_procesamiento` | Corrida operativa o editorial (`tipo_operacion`, `clave_idempotencia`) |
| `actividad` | Hecho de comunidad; puede existir **sin lote** (`pendiente`) |
| `analisis` | Interpretación 1:1 de una actividad |
| `activo_generado` | Activo lógico (`LINKEDIN` \| `NEWSLETTER` \| `FAQ`) con estado de curaduría |
| `version_activo` | Historial de contenido (`ia` / `usuario`) |
| `almacenamiento_oci` | Cola/estado de persistencia **por versión** (máx. 1 fila por `id_version`) |

### 5.2. Tipos de activo

```text
LINKEDIN | NEWSLETTER | FAQ
```

### 5.3. Vistas de apoyo

| Vista | Uso |
|-------|-----|
| `v_lote_resumen` | Panel de lotes + conteos OCI agregados |
| `v_activos_versiones_oci` | Activos, versiones, si es aprobada y estado OCI |
| `v_actividades_pendientes` | Cola para el job batch de análisis |

### 5.4. Funciones de dominio

| Función | Uso |
|---------|-----|
| `communitylab_aprobar_activo(id, comentario)` | Aprobación atómica + registro OCI pendiente |
| `communitylab_editar_activo(id, contenido, motivo, creado_por)` | Nueva versión de usuario + vuelve a borrador |

---

## 6. Análisis LLM (contrato de salida del analista)

El nodo **Analista de Contenido (LLM)** produce un objeto con al menos:

```json
{
  "sentimiento": "Muy Positivo | Positivo | Neutral | Frustración | …",
  "tema_categoria": "Logro Laboral | Duda Técnica | Feedback de Curso | Otro | …",
  "tema_libre": "string corto",
  "score_relevancia": 1,
  "tipo_insight": "testimonio | duda_recurrente | feedback | ninguno | …",
  "resumen": "string",
  "cita_extraida": "string",
  "razon_relevancia": "string"
}
```

Se persiste en `analisis` (campos tipados + `resultado_json` completo).  
`tipo_insight` y sentimiento alimentan el **branching** de generación de activos (LINKEDIN / NEWSLETTER / FAQ).

---

## 7. Activos generados — estructuras de contenido

### 7.1. LINKEDIN (post)

```json
{
  "titulo": "string",
  "copy": "string",
  "canal_recomendado": "LinkedIn Oficial",
  "potencial_engagement": "Alto | Medio | Bajo",
  "hashtags": ["#…"],
  "origen_interacciones": ["autor…"],
  "tipo_experiencia": "logro_laboral | experiencia_proyecto | aprendizaje_tecnico | testimonio_formacion"
}
```

### 7.2. NEWSLETTER

Ver sección 4.7 (estructura editorial con `titulo`, `introduccion`, `secciones[]`, `cierre`, `status`, `motivo`).

### 7.3. FAQ

Estructura extensible (tema, origen, contenido sugerido, status). Se documentará con mayor detalle cuando el generador FAQ quede estabilizado en el mismo nivel que LinkedIn/Newsletter.

---

## 8. Relación con el modo Solo OCI (histórico)

El contrato **v1.0** describía un único endpoint batch `POST /procesar-actividad` sin IDs de dominio obligatorios y con persistencia mínima solo en OCI.

En **v2.0**:

- La ingesta y el procesamiento se separan (tiempo real + jobs).
- El panel de curaduría y las consultas por `id_lote` / `id_activo` son contratos de primer nivel.
- OCI se limita a **versiones aprobadas**, no al paquete completo de la corrida en un solo objeto obligatorio del response síncrono.
- El response de generación puede incluir `id_lote` / `estado_lote` cuando el flujo los produce.

El modo Solo OCI puede seguir existiendo como ruta de demo o fallback, pero **ya no es el contrato principal** del sistema con persistencia.

---

## 9. Validaciones transversales

1. IDs de path/query: enteros positivos safe.
2. Textos no vacíos en campos obligatorios de texto.
3. Ventanas temporales: `desde < hasta`.
4. Upserts de dominio siempre por identificadores de origen cuando existen.
5. Parámetros SQL con placeholders (`$1`, …) / `queryReplacement`; no interpolar entrada cruda.
6. Respuestas de error con `status`/`codigo`/`mensaje` (y lista `errores` cuando aplica validación).

---

## 10. Evolución del contrato

Cualquier cambio en:

- paths o métodos HTTP,
- campos obligatorios,
- catálogos de estado,
- semántica de idempotencia,
- forma de `contenido` de un tipo de activo,

debe incrementar la versión de este documento y actualizar los workflows y el SQL de forma coordinada.

**Próximas mejoras candidatas (no bloqueantes):**

- Persistir `revisado_por` en aprobación/rechazo.
- Política explícita de regeneración de newsletter distinta del reintento idempotente.
- Contrato formal del generador FAQ al mismo nivel que LinkedIn/Newsletter.
- Endpoint de reproceso de lote por `id_lote` si se expone al panel.
