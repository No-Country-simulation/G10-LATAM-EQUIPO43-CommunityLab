# Backend — CommunityLab

El backend de CommunityLab captura mensajes de una comunidad digital en Discord, los procesa mediante workflows de n8n y genera activos de contenido para su revisión y distribución. Incluye análisis de sentimiento y relevancia, generación de publicaciones y newsletters, y persistencia de versiones aprobadas en Oracle Cloud Infrastructure (OCI) Object Storage.

## Estructura

```text
backend/
├── bot discord n8n/
│   ├── bot.py
│   ├── requirements.txt
│   └── .env                 # configuración local; no subir a Git
├── workflows/
│   ├── Ingesta en Tiempo Real - CommunityLab.json
│   ├── Procesamiento y generación - communityLab.json
│   └── CommunityLab — Persistencia OCI de Versiones Aprobadas.json
└── README.md
```

## Componentes

### 1. Bot de Discord (`bot discord n8n/`)

`bot.py` se conecta a Discord, escucha mensajes en los canales configurados y envía cada mensaje válido al webhook de ingesta de n8n mediante una petición HTTP `POST`.

El bot:
- Ignora sus propios mensajes y los mensajes de otros bots.
- Escucha únicamente los canales incluidos en `CANALES_PERMITIDOS`.
- Envía identificadores del servidor, mensaje, canal y autor, junto con el contenido y la fecha del mensaje.
- Selecciona el webhook de prueba o producción según la configuración de entorno.

`requirements.txt` contiene las dependencias de Python:
- `discord.py`
- `requests`
- `python-dotenv`

### 2. Workflows de n8n (`workflows/`)

| Workflow | Función |
|---|---|
| **Ingesta en Tiempo Real - CommunityLab** | Recibe los mensajes enviados por el bot, valida los campos obligatorios, normaliza los datos y registra la actividad en PostgreSQL con estado pendiente. |
| **Procesamiento y generación - communityLab** | Analiza las interacciones mediante un LLM, identifica sentimiento, temas, relevancia y tipo de insight, y decide qué activos generar según las evidencias disponibles. Puede generar contenido para LinkedIn, newsletter y FAQ/tips. |
| **CommunityLab — Persistencia OCI de Versiones Aprobadas** | Cada cinco minutos revisa la cola de persistencia en PostgreSQL, prepara un JSON por versión aprobada y lo sube a OCI Object Storage mediante una conexión compatible con S3. Registra el éxito o los errores y programa reintentos. |

## Flujo general

```text
Discord
   │
   ▼
bot.py (Python)
   │ POST del mensaje
   ▼
Webhook de n8n
   │
   ▼
1. Ingesta en tiempo real
   │
   ▼
PostgreSQL: actividades pendientes
   │
   ▼
2. Procesamiento y generación
   ├── Análisis de sentimiento, temas y relevancia
   ├── Clasificación de insights
   └── Generación de activos
          │
          ▼
     Curaduría / aprobación
          │
          ▼
PostgreSQL: versión aprobada y cola OCI
          │
          ▼
3. Persistencia OCI de versiones aprobadas
          │
          ▼
OCI Object Storage
```

La revisión y aprobación de activos se realiza desde el frontend del proyecto. La persistencia OCI procesa versiones que ya han sido aprobadas y registradas en la cola correspondiente.

## Requisito imprescindible: bot de Discord en ejecución

**Para que la ingesta ocurra en tiempo real, el bot de Discord debe estar creado, configurado y ejecutándose con `bot.py`.** Importar o activar el workflow de n8n por sí solo no permite escuchar mensajes de Discord: el bot es el componente que recibe los eventos y los envía al webhook.

Antes de iniciar el bot:

1. Crea una aplicación y un bot en el [Discord Developer Portal](https://discord.com/developers/applications).
2. Invita el bot al servidor de Discord y concédele acceso a los canales que quieres escuchar.
3. Habilita **Message Content Intent** en el portal de Discord, ya que `bot.py` lee el contenido de los mensajes.
4. Configura el token, el entorno de n8n y los IDs de los canales en el archivo `.env`.
5. Importa y configura los workflows de n8n, especialmente el webhook de ingesta y las credenciales de PostgreSQL.
6. Ejecuta `bot.py` y comprueba en la consola que aparezca el mensaje de conexión.

## Configuración del bot

### Requisitos

- Python instalado.
- Bot de Discord creado e invitado al servidor.
- Instancia de n8n accesible desde el equipo donde corre el bot.
- Workflow de ingesta importado y configurado.
- Acceso a PostgreSQL y credenciales configuradas en n8n.

### Instalar dependencias

Abre una terminal en `backend/bot discord n8n/`:

```bash
python -m venv .venv
```

Activa el entorno virtual.

**Linux/macOS**
```bash
source .venv/bin/activate
```

**Windows PowerShell**
```powershell
.venv\Scripts\Activate.ps1
```

Instala las dependencias:

```bash
pip install -r requirements.txt
```

### Variables de entorno

Crea un archivo `.env` dentro de `backend/bot discord n8n/`:

```dotenv
DISCORD_TOKEN=tu_token_del_bot
N8N_ENV=test
N8N_HOST=http://localhost:5678
N8N_ENDPOINT_TEST=/webhook-test/communitylab/actividades
N8N_ENDPOINT_PROD=/webhook/communitylab/actividades
CANALES_PERMITIDOS=ID_CANAL_1,ID_CANAL_2
```

| Variable | Descripción |
|---|---|
| `DISCORD_TOKEN` | Token privado del bot de Discord. |
| `N8N_ENV` | Entorno seleccionado: `test` o `prod`. |
| `N8N_HOST` | URL base de la instancia de n8n. |
| `N8N_ENDPOINT_TEST` | Ruta del webhook de prueba. |
| `N8N_ENDPOINT_PROD` | Ruta del webhook de producción. |
| `CANALES_PERMITIDOS` | IDs de los canales que el bot debe escuchar, separados por comas. |

Las variables y rutas deben coincidir con la configuración de n8n. En modo prueba, utiliza el webhook de test y ejecuta el workflow de la forma requerida por n8n. En producción, activa el workflow y usa el endpoint de producción.

### Ejecutar el bot

Desde `backend/bot discord n8n/`, con el entorno virtual activo y `.env` configurado:

```bash
python bot.py
```

Mantén el proceso en ejecución mientras quieras que el bot escuche mensajes. Si se detiene, la ingesta en tiempo real desde Discord deja de funcionar.

## Configuración de n8n

1. Importa los tres archivos JSON de `workflows/` en tu instancia de n8n.
2. Configura las credenciales de PostgreSQL para los workflows que acceden a la base de datos.
3. Configura las credenciales del proveedor LLM utilizadas por el workflow de procesamiento.
4. Configura las credenciales de OCI Object Storage mediante la integración S3 compatible y verifica el bucket esperado.
5. Comprueba las rutas de webhook y la URL que utiliza el bot.
6. Activa los workflows que deban ejecutarse en producción. La persistencia OCI tiene un disparador programado cada cinco minutos.
7. Verifica que el esquema SQL requerido esté instalado desde los scripts de `database/`.

## Seguridad

- No subas el archivo `.env` al repositorio.
- Nunca publiques `DISCORD_TOKEN`, claves de proveedores LLM ni credenciales de PostgreSQL/OCI.
- Añade `.env` y el entorno virtual `.venv/` a `.gitignore`.
- Concede al bot solo los permisos de Discord que necesita.
- No expongas los webhooks de n8n sin controles de acceso adecuados.

## Relación con el resto del proyecto

- `frontend/`: panel Streamlit para consultar, editar y aprobar activos.
- `database/`: esquemas y scripts SQL requeridos por los workflows.
- `data/`: datasets y casos de prueba.
- `docs/`: contrato de datos, diagramas y guías técnicas.
