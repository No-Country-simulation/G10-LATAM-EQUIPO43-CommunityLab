# CommunityLab — Backend de Ingesta y Automatización

Backend de **CommunityLab**, plataforma de curaduría de interacciones comunitarias y generación de activos de contenido mediante Discord, n8n, modelos de lenguaje y PostgreSQL.

Este módulo recibe mensajes de Discord, los procesa mediante workflows de n8n y permite generar activos —como publicaciones para LinkedIn, secciones de newsletter y contenido FAQ— para su posterior revisión, edición y aprobación desde la interfaz de Streamlit ubicada en `Frontend/`.

## Arquitectura general

```text
Discord
   │
   ▼
bot.py (Python)
   │
   ▼
Webhook de ingesta en n8n
   │
   ▼
Validación y normalización
   │
   ▼
PostgreSQL
   │
   ▼
Análisis de interacciones mediante LLM
   │
   ▼
Generación de activos de contenido
   │
   ▼
Persistencia y versionado
   │
   ▼
Frontend (Streamlit)
   │
   ▼
Edición, aprobación o rechazo
```

## Estructura del directorio

```text
backend/
├── bot discord n8n/
│   └── bot.py
│
├── workflows/
│   ├── Ingesta en Tiempo Real - CommunityLab.json
│   ├── Procesamiento y generación - communityLab.json
│   ├── CommunityLab — Curaduría de Activos.json
│   ├── Generador Newsletter - respuesta persistida.json
│   └── communitylab-workflow-v1.0-solo-oci.json
│
└── README.md
```

## Componentes

### 1. Bot de Discord

**Archivo:** `bot discord n8n/bot.py`

Implementa un cliente de Discord con Python que escucha mensajes en los canales configurados y envía las interacciones a n8n mediante solicitudes HTTP POST.

Responsabilidades principales:

- Escuchar mensajes nuevos en Discord.
- Ignorar los mensajes enviados por el propio bot y por otros bots.
- Filtrar los mensajes según los identificadores de los canales permitidos.
- Enviar el contenido y los metadatos de cada mensaje al webhook de n8n.
- Seleccionar el endpoint de n8n según el entorno configurado.

El payload enviado incluye identificadores del servidor, canal, mensaje y autor, además del contenido y la marca temporal.

### 2. Workflows de n8n

Los archivos JSON contienen workflows exportados de n8n. Deben importarse en la instancia correspondiente y configurarse con las credenciales y los servicios externos necesarios.

| Workflow | Responsabilidad |
|---|---|
| `Ingesta en Tiempo Real - CommunityLab.json` | Recibe mensajes de Discord, valida el payload, normaliza los datos y persiste las actividades en PostgreSQL con estado pendiente. |
| `Procesamiento y generación - communityLab.json` | Analiza las interacciones mediante un LLM, clasifica sentimientos, temas y relevancia, y determina qué activos generar. |
| `CommunityLab — Curaduría de Activos.json` | Gestiona la edición, el versionado, la aprobación y el rechazo de activos mediante webhooks y operaciones en PostgreSQL. |
| `Generador Newsletter - respuesta persistida.json` | Recupera actividades analizadas en un periodo determinado, valida si existe contenido suficiente y genera y persiste el newsletter. |
| `communitylab-workflow-v1.0-solo-oci.json` | Implementa un flujo de análisis y generación de activos con lógica de selección para LinkedIn, newsletter y FAQ, además de componentes relacionados con OCI. |

### 3. Integración con Streamlit

El frontend, ubicado en `frontend/`, proporciona la interfaz de curaduría para que los usuarios revisen los activos generados.

El proceso contempla:

- Consultar los activos almacenados.
- Editar el contenido y registrar el motivo del cambio.
- Mantener un historial de versiones.
- Aprobar o rechazar activos.
- Gestionar el estado de curaduría.

La edición, aprobación y rechazo se integran con los endpoints HTTP expuestos por los workflows de n8n.

## Tecnologías

- **Python:** ejecución del bot de Discord.
- **discord.py:** conexión y recepción de eventos de Discord.
- **Requests:** comunicación HTTP con n8n.
- **python-dotenv:** carga de variables de entorno.
- **n8n:** orquestación de workflows y automatización.
- **PostgreSQL:** persistencia de actividades, análisis, activos y versiones.
- **LLM:** análisis de interacciones y generación de contenido.
- **Streamlit:** interfaz de curaduría de activos.
- **OCI:** integración contemplada en el workflow específico de procesamiento.

## Configuración del bot

### Requisitos previos

- Python 3.10 o superior.
- Un bot de Discord configurado en el portal de desarrolladores.
- Una instancia de n8n accesible desde el entorno donde se ejecuta Python.
- Los workflows de n8n importados y configurados.

### 1. Instalar dependencias

Desde el directorio del bot:

```bash
python -m venv .venv
```

Activar el entorno virtual:

**Linux/macOS**

```bash
source .venv/bin/activate
```

**Windows**

```powershell
.venv\Scripts\Activate.ps1
```

Instalar las dependencias:

```bash
pip install discord.py requests python-dotenv
```

### 2. Configurar variables de entorno

Crear un archivo `.env` en el directorio desde el que se ejecutará `bot.py`:

```dotenv
DISCORD_TOKEN=tu_token_de_discord

N8N_ENV=test
N8N_HOST=http://localhost:5678

N8N_ENDPOINT_TEST=/webhook-test/communitylab/actividades
N8N_ENDPOINT_PROD=/webhook/communitylab/actividades

CANALES_PERMITIDOS=123456789012345678,234567890123456789
```

**Descripción de las variables**

| Variable | Descripción |
|---|---|
| `DISCORD_TOKEN` | Token del bot de Discord. |
| `N8N_ENV` | Entorno seleccionado: `test` o `prod`. |
| `N8N_HOST` | Host base de la instancia de n8n. |
| `N8N_ENDPOINT_TEST` | Endpoint utilizado en modo de prueba. |
| `N8N_ENDPOINT_PROD` | Endpoint utilizado en producción. |
| `CANALES_PERMITIDOS` | IDs de los canales cuyos mensajes se procesarán, separados por comas. |

Los endpoints del ejemplo corresponden a la ruta de ingesta definida en el workflow. Ajustarlos si la configuración de n8n utiliza rutas diferentes.

El bot requiere el intent de contenido de mensajes (`Message Content Intent`) habilitado en el portal de desarrolladores de Discord y en su configuración de permisos, cuando corresponda.

### 3. Ejecutar el bot

```bash
python bot.py
```

Cuando la conexión se establece correctamente, el bot informa su identidad en la consola. Los mensajes de los canales permitidos se envían al webhook configurado.

## Configuración de n8n

1. Importar los archivos JSON desde la interfaz de n8n.
2. Configurar las credenciales de PostgreSQL.
3. Configurar las credenciales y conexiones necesarias para los nodos de LLM y los servicios externos utilizados por cada workflow.
4. Revisar las rutas de los webhooks y sus modos de ejecución.
5. Activar los workflows que deban operar en producción.
6. Configurar `N8N_HOST` y los endpoints del bot para que apunten a la instancia correcta.
7. Verificar la comunicación entre n8n, PostgreSQL y el frontend de Streamlit.

Los archivos exportados contienen definiciones de workflows, pero no sustituyen la configuración de credenciales, variables de entorno ni dependencias de la instancia.

## Flujo de procesamiento

1. **Ingesta:** el bot captura una interacción de Discord y la envía a n8n.
2. **Normalización:** n8n valida los campos obligatorios y adapta los datos al esquema interno.
3. **Persistencia:** la actividad se registra en PostgreSQL.
4. **Análisis:** el LLM identifica sentimiento, temática, relevancia y tipo de insight.
5. **Generación:** según las evidencias disponibles y las opciones solicitadas, se generan los activos correspondientes.
6. **Curaduría:** los activos se almacenan y quedan disponibles para su revisión.
7. **Aprobación:** el usuario edita, aprueba o rechaza el contenido desde Streamlit.

La generación de publicaciones para LinkedIn no implica por sí misma su publicación automática en la plataforma: los activos se preparan para su revisión y aprobación.

## Seguridad y buenas prácticas

- No subir archivos `.env`, tokens de Discord ni credenciales al repositorio.
- Añadir `.env` a `.gitignore`.
- No utilizar credenciales reales en los ejemplos de configuración.
- Restringir el acceso a los webhooks y servicios internos según el entorno de despliegue.
- Verificar las credenciales de PostgreSQL y las integraciones de LLM antes de activar los workflows.
- Mantener diferenciados los endpoints de prueba y producción.

## Alcance

Este directorio contiene los componentes del backend responsables de la ingesta, el procesamiento, la generación y la curaduría de activos. La interfaz de usuario y sus funcionalidades se encuentran en `Frontend/`.

Para ejecutar el sistema completo, deben estar disponibles y correctamente conectados el bot de Discord, n8n, PostgreSQL y el frontend.
