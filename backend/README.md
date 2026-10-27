# CommunityLab — Backend

Backend de CommunityLab para capturar interacciones de Discord, analizarlas con workflows de n8n y generar activos de contenido que pueden revisarse, editarse y aprobarse desde la interfaz de Streamlit ubicada en `frontend/`.

## Arquitectura general

```text
Discord
  │
  ▼
Bot de Discord (Python / bot.py)
  │ HTTP POST
  ▼
1. Ingesta en Tiempo Real
  │
  ▼
PostgreSQL: actividades pendientes
  │
  ▼
2. Procesamiento y generación
  │
  ├── Análisis de mensajes mediante LLM
  ├── Clasificación de sentimiento, tema y relevancia
  └── Generación de activos
        │
        ▼
   PostgreSQL: activos y versiones
        │
        ├── 3. Consulta de activos y versiones
        ├── 4. Curaduría de Activos
        ├── 5. Persistencia OCI de Versiones Aprobadas
        └── 6. Generador Newsletter
                 │
                 ▼
          Frontend (Streamlit)
          Edición y aprobación
```

## Estructura del directorio

```text
backend/
├── bot discord n8n/
│   └── bot.py
├── workflows/
│   ├── Communitylab — Ingesta en Tiempo Real.json
│   ├── Communitylab — Procesamiento y generación.json
│   ├── CommunityLab — Consulta de activos y versiones.json
│   ├── CommunityLab — Curaduría de Activos.json
│   ├── CommunityLab — Persistencia OCI de Versiones Aprobadas.json
│   └── Communitylab — Generador Newsletter.json
└── README.md
```

Los nombres de los archivos pueden variar ligeramente según cómo se hayan exportado desde n8n. La numeración funcional corresponde a la lista documentada a continuación.

## Workflows de n8n

Importa los seis archivos JSON en tu instancia de n8n y configura sus credenciales, variables y conexiones antes de ejecutarlos.

### 1. Ingesta en Tiempo Real - CommunityLab

Recibe los mensajes enviados por el bot de Discord mediante un webhook (`communitylab/actividades`). Valida los campos requeridos, normaliza la información de la fuente, canal y autor, y guarda la actividad en PostgreSQL con estado `pendiente`.

### 2. Procesamiento y generación - communityLab

Analiza las actividades almacenadas mediante un modelo de lenguaje (LLM). Clasifica cada interacción por sentimiento, tema, relevancia y tipo de insight; después decide qué activos generar, por ejemplo publicaciones de LinkedIn, contenido para newsletter o FAQ, según las evidencias y opciones de la solicitud.

### 3. CommunityLab — Consulta de activos y versiones

Expone endpoints para consultar activos y su historial de versiones. Permite recuperar el contenido actual y revisar qué versión está marcada como actual o aprobada. Es un workflow de consulta: no crea ni modifica versiones.

### 4. CommunityLab — Curaduría de Activos

Expone endpoints para las operaciones de curaduría, como editar un activo, registrar una nueva versión, aprobarlo o rechazarlo. Las operaciones validan la solicitud y el estado del activo, y devuelven respuestas HTTP con el resultado.

### 5. CommunityLab — Persistencia OCI de Versiones Aprobadas

Se ejecuta de forma programada para procesar registros pendientes de almacenamiento. Prepara un archivo JSON por versión, lo sube a un bucket compatible con S3 en Oracle Cloud Infrastructure (OCI) y registra el resultado en PostgreSQL. Contempla errores y reintentos.

### 6. Generador Newsletter

Recibe una solicitud HTTP para generar un newsletter a partir de actividades analizadas dentro de un intervalo temporal. Valida el origen, las fechas y las opciones; consulta las actividades relevantes y persiste el activo generado. Incluye validación de la solicitud y respuestas de éxito o error.

## Requisito previo: crear el bot de Discord

Antes de ejecutar `bot.py`, crea y configura una aplicación con bot en el [Discord Developer Portal](https://discord.com/developers/applications). El token se obtiene desde la configuración del bot y se utiliza para autenticar la conexión de Python con Discord.

1. Crea una aplicación en el portal de desarrolladores de Discord.
2. En la sección **Bot**, añade/configura el bot y copia su token.
3. Habilita **Message Content Intent** si el bot necesita leer el contenido de los mensajes.
4. Invita el bot al servidor de Discord que se utilizará, concediéndole acceso al servidor y permisos de lectura de los canales correspondientes.
5. Asegúrate de que el bot tenga acceso al canal o canales que quieres escuchar.
6. Guarda el token como variable de entorno. **No lo publiques ni lo subas al repositorio.**

Crear el bot no basta por sí solo: también debe estar invitado al servidor y tener permisos para ver los canales y leer los mensajes necesarios.

## Configuración del bot de Python

### Requisitos

- Python instalado.
- Token de un bot de Discord con acceso al servidor y a los canales.
- Instancia de n8n accesible desde el entorno donde corre el bot.
- Workflow **1. Ingesta en Tiempo Real - CommunityLab** importado y configurado.

### Instalar dependencias

Desde el directorio que contiene `bot.py`, crea y activa un entorno virtual:

```bash
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Instala las dependencias usadas por el bot:

```bash
pip install discord.py requests python-dotenv
```

### Variables de entorno

Crea un archivo `.env` junto a `bot.py` y adapta los valores a la configuración real del proyecto:

```dotenv
DISCORD_TOKEN=pega_aqui_el_token_del_bot
N8N_ENV=test
N8N_HOST=http://localhost:5678
N8N_ENDPOINT_TEST=/webhook-test/communitylab/actividades
N8N_ENDPOINT_PROD=/webhook/communitylab/actividades
CANALES_PERMITIDOS=ID_CANAL_1,ID_CANAL_2
```

- `DISCORD_TOKEN`: token privado del bot.
- `N8N_ENV`: entorno de n8n que utilizará el bot (`test` o `prod`).
- `N8N_HOST`: dirección base de la instancia de n8n.
- `N8N_ENDPOINT_TEST`: ruta del webhook de prueba.
- `N8N_ENDPOINT_PROD`: ruta del webhook de producción.
- `CANALES_PERMITIDOS`: IDs de los canales de Discord que se escucharán, separados por comas.

Comprueba los nombres exactos de las variables que lee `bot.py` y las rutas configuradas en n8n. Los valores anteriores son una plantilla: deben coincidir con la implementación y la instancia desplegada. En n8n, las URLs de prueba y producción pueden ser distintas; el webhook de producción requiere que el workflow esté activo.

### Ejecutar el bot

```bash
python bot.py
```

Comprueba en la consola que el bot se conecte a Discord y revisa las ejecuciones del workflow de ingesta en n8n para verificar que los mensajes llegan correctamente.

## Dependencias e infraestructura

- **Discord:** origen de las interacciones comunitarias.
- **Python / discord.py:** cliente que escucha los mensajes.
- **Requests:** envío HTTP desde el bot hacia n8n.
- **python-dotenv:** lectura de variables de entorno.
- **n8n:** orquestación de ingesta, análisis, generación, curaduría y persistencia.
- **PostgreSQL:** almacenamiento de actividades, análisis, activos, versiones y estados de procesamiento.
- **LLM:** análisis semántico y generación de contenido en el workflow de procesamiento.
- **Streamlit:** interfaz de revisión, edición y aprobación en `Frontend/`.
- **Oracle Cloud Infrastructure (OCI):** almacenamiento de versiones aprobadas mediante la integración compatible con S3.

## Puesta en marcha de n8n

1. Importa los seis workflows JSON.
2. Configura las credenciales de PostgreSQL utilizadas por los nodos correspondientes.
3. Configura las credenciales del proveedor LLM requerido por el workflow 2.
4. Configura las credenciales de OCI/S3 y verifica el bucket utilizado por el workflow 5.
5. Comprueba los paths de los webhooks y las URLs que utiliza el frontend y el bot.
6. Activa los workflows que deban atender solicitudes en producción. El workflow 5 necesita además su disparador programado.
7. Verifica que el esquema y las funciones de PostgreSQL requeridas por los workflows existan en la base de datos de destino.
8. Prueba primero la ingesta y consulta los registros en PostgreSQL antes de comprobar el ciclo de generación y curaduría desde Streamlit.

## Seguridad

- Añade `.env` a `.gitignore`.
- No incluyas tokens de Discord, contraseñas, claves API ni credenciales de OCI en Git.
- Limita los permisos del bot a los servidores y canales necesarios.
- No expongas públicamente los webhooks de n8n sin controles de acceso apropiados.
- Separa los endpoints de prueba y producción.
- Revisa las credenciales y los permisos de la base de datos y del bucket de OCI antes del despliegue.

## Alcance

Este directorio contiene el bot de ingesta y los workflows de n8n. La interfaz para revisar, editar y aprobar activos se encuentra en `frontend/`. La generación de contenido no implica que las publicaciones se publiquen automáticamente en LinkedIn: los activos se preparan para el proceso de revisión y aprobación definido por la aplicación.
