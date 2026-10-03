# Guía para el Bot de Discord — CommunityLab

**Audiencia:** quien implementa el bot / integrador de Discord
**Versión:** 1.0
**Estado:** Integración pendiente — preparada para el Hito 1
**Alineado a:** `contrato-de-datos.md` v1.0
**Última revisión:** 2026-10-02

---

## 1. Qué hace el bot en el sistema

El bot de Discord será el cliente que recolectará las interacciones de la comunidad y las enviará al workflow de CommunityLab.

Sus responsabilidades serán:

1. Recolectar mensajes / interacciones de Discord (o un lote manual).
2. Armar un JSON según el contrato de **entrada**.
3. Hacer `POST` al webhook de n8n.
4. (Opcional) Mostrar al usuario un resumen de la **respuesta** o un error legible.

```text
Discord
   ↓
Bot
   ↓
POST webhook n8n
   ↓
CommunityLab
   ↓
Response JSON
```

### Estado actual

El webhook y el flujo de automatización se encuentran en desarrollo como **Hito 1 — Solo OCI**.

Actualmente el flujo se prueba mediante **Postman**. El bot de Discord todavía no está integrado y utilizará este mismo endpoint y contrato cuando se implemente.

---

## 2. Endpoint a llamar

| Campo            | Valor                                                      |
| ---------------- | ---------------------------------------------------------- |
| Método           | `POST`                                                     |
| Path del webhook | `/communitylab/actividades`                                |
| Content-Type     | `application/json`                                         |
| URL completa     | `https://<host-n8n>/webhook/communitylab/actividades`      |
| URL de test      | `https://<host-n8n>/webhook-test/communitylab/actividades` |

> La URL base depende de dónde esté desplegado n8n (local, OCI, n8n Cloud u otro entorno).

> `<host-n8n>` es una configuración del entorno y no debe incorporarse como un valor fijo en el código del bot.

---

## 3. Body que debes enviar (Request)

El body debe cumplir el contrato definido en `contrato-de-datos.md` v1.0.

### Campos obligatorios

| Campo                   | Tipo   | Regla                                   |
| ----------------------- | ------ | --------------------------------------- |
| `origen_comunidad`      | string | No vacío. Ej. `"Discord_Grupo_ONE_G10"` |
| `periodo_referencia`    | string | No vacío                                |
| `interacciones`         | array  | Mínimo **1** elemento                   |
| `interacciones[].texto` | string | No vacío en **cada** ítem               |

### Campos opcionales por interacción

| Campo                  | Tipo   | Uso recomendado desde Discord                                                                                   |
| ---------------------- | ------ | --------------------------------------------------------------------------------------------------------------- |
| `autor`                | string | Display name o username del autor                                                                               |
| `canal`                | string | Nombre del canal (`#logros-y-empleos`)                                                                          |
| `tipo`                 | string | Si el bot puede clasificar: `testimonio`, `pregunta_tecnica`, `duda`, `logro`, `feedback`, `comentario`, `otro` |
| `identificador_origen` | string | ID del mensaje en Discord                                                                                       |
| `momento_origen`       | string | ISO 8601 del mensaje                                                                                            |

### Opcional a nivel de lote

```json
{
  "opciones": {
    "generar_activos": ["LINKEDIN", "NEWSLETTER", "FAQ"],
    "idioma": "es",
    "tono": "inspirador"
  }
}
```

* Si **no** envías `generar_activos`, n8n decide mediante branching.
* Si **sí** lo envías, se respeta esa lista como override.

---

## 4. Convención de `periodo_referencia`

El campo `periodo_referencia` identifica el lote que se está procesando.

Para mantener consistencia entre clientes, se recomienda utilizar una única convención en cada implementación.

Ejemplo utilizado en la documentación del Hito 1:

```text
Semana_04
```

También puede utilizarse una representación temporal como:

```text
2026-W40
```

Si el bot genera este valor automáticamente, deberá utilizar la convención que el equipo establezca para el lote que está enviando.

---

## 5. Ejemplo mínimo válido

```json
{
  "origen_comunidad": "Discord_Grupo_ONE_G10",
  "periodo_referencia": "Semana_04",
  "interacciones": [
    {
      "autor": "Mariana Souza",
      "canal": "#logros-y-empleos",
      "tipo": "testimonio",
      "texto": "Quedé seleccionada como Dev Junior de IA gracias al proyecto con LangChain y OCI.",
      "identificador_origen": "1234567890123456789",
      "momento_origen": "2026-10-01T18:22:00Z"
    }
  ]
}
```

---

## 6. Ejemplo con varias interacciones

```json
{
  "origen_comunidad": "Discord_Grupo_ONE_G10",
  "periodo_referencia": "Semana_04",
  "interacciones": [
    {
      "autor": "Mariana Souza",
      "canal": "#logros-y-empleos",
      "tipo": "testimonio",
      "texto": "Comunidad, quede seleccionada para el puesto de Desarrolladora Junior de IA! El proyecto del curso de LangChain y OCI que construi en mi portfolio marco toda la diferencia en la entrevista tecnica."
    },
    {
      "autor": "Lucas Albuquerque",
      "canal": "#dudas-langgraph",
      "tipo": "pregunta_tecnica",
      "texto": "Tengo dudas sobre como estructurar los nodos condicionales en LangGraph cuando la respuesta del LLM necesita reintento."
    }
  ]
}
```

---

## 7. Qué vas a recibir (Response)

La respuesta sigue el contrato de datos del Hito 1.

### Éxito — HTTP 200

```json
{
  "status": "exito",
  "resumen_comunidad": {
    "total_interacciones_procesadas": 2,
    "sentimiento_predominante": "Positivo",
    "temas_principales": ["..."]
  },
  "activos_distribucion_generados": {
    "post_linkedin": {},
    "destaque_newsletter_semanal": {},
    "sugerencia_contenido_faq": {}
  },
  "almacenamiento_oci": {
    "bucket": "communitylab-activos-marketing",
    "ruta_objeto": "activos/Semana_04/paquete-20261001T221500Z.json",
    "status": "guardado_con_exito"
  },
  "meta": {
    "procesado_en": "2026-10-02T...",
    "modo": "solo_oci"
  }
}
```

Algunos activos pueden venir con información que indique que no fueron requeridos por el branching.

### Procesamiento parcial — HTTP 200

Si el workflow logra procesar la solicitud pero se produce un fallo parcial:

```json
{
  "status": "parcial",
  "resumen_comunidad": {},
  "activos_distribucion_generados": {},
  "almacenamiento_oci": {
    "status": "error"
  },
  "errores": [
    {
      "codigo": "OCI_001",
      "mensaje": "No fue posible guardar el paquete en OCI.",
      "detalle": null
    }
  ],
  "meta": {
    "modo": "solo_oci"
  }
}
```

### Error de validación — HTTP 400

```json
{
  "status": "error",
  "errores": [
    {
      "codigo": "VALIDACION_1",
      "mensaje": "El campo 'interacciones' debe ser un array con al menos 1 elemento.",
      "detalle": null
    }
  ],
  "almacenamiento_oci": {
    "status": "omitido"
  },
  "meta": {
    "modo": "solo_oci"
  }
}
```

### Error crítico — HTTP 500

Un HTTP `500` indica un fallo crítico no controlado durante la ejecución del workflow.

El bot debería informar al usuario que ocurrió un error durante el procesamiento sin exponer detalles internos del workflow.

---

## 8. Cómo mostrar la respuesta en Discord

La respuesta completa del workflow no necesita mostrarse en el canal público.

Se recomienda presentar únicamente un resumen legible:

| `status`  | Mensaje al canal                                                   |
| --------- | ------------------------------------------------------------------ |
| `exito`   | “Procesadas N interacciones. Sentimiento: X. Activos generados: …” |
| `parcial` | “Procesado con advertencias. Revisar errores / OCI.”               |
| `error`   | Mostrar los mensajes de `errores[].mensaje` de forma legible       |

No se recomienda reenviar el JSON completo al canal público.

---

## 9. Relación con el Hito 1

El bot de Discord **no forma parte todavía de la ejecución del Hito 1**.

El flujo actualmente validado mediante Postman es:

```text
Postman
   ↓
Webhook HTTP n8n
   ↓
Validación
   ↓
Procesamiento
   ↓
Generación de activos
   ↓
OCI
   ↓
Response HTTP
```

Cuando se implemente el bot, este reemplazará a Postman como cliente:

```text
Discord
   ↓
Bot
   ↓
Webhook HTTP n8n
   ↓
Validación
   ↓
Procesamiento
   ↓
Generación de activos
   ↓
OCI
   ↓
Response HTTP
   ↓
Bot
   ↓
Resumen en Discord
```

El contrato de datos no depende de que el cliente sea Postman o Discord.

---

## 10. Consideraciones futuras

La futura incorporación de persistencia en base de datos corresponde a una evolución posterior del flujo.

El bot deberá continuar enviando el mismo contrato de entrada salvo que una nueva versión del contrato establezca cambios.

La integración con BD tampoco modifica las responsabilidades principales del bot: recolectar las interacciones, construir el request y enviar/interpretar la respuesta.

---

**Fin — Guía Bot Discord v1.0**
