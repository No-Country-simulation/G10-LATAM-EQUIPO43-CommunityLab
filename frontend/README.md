# CommunityLab — Frontend de Curaduría y Distribución de Activos

Frontend de **CommunityLab**, una plataforma que transforma interacciones de comunidades digitales en activos de contenido mediante análisis y generación asistidos por inteligencia artificial.

Esta aplicación está desarrollada con **Streamlit** y permite consultar, editar, aprobar o rechazar activos generados, revisar métricas de procesamiento de la comunidad y visualizar el estado de los registros asociados a Oracle Cloud Infrastructure (OCI) Object Storage.

Este módulo forma parte del proyecto desarrollado para el hackatón de **ALURA y NoCountry**, Grupo 10 — Equipo 43.

## Arquitectura general

```text
Workflows de n8n
      │
      ▼
PostgreSQL (Supabase)
      │
      ├── Actividades y análisis
      ├── Lotes de procesamiento
      ├── Activos generados y versiones
      └── Registros de almacenamiento OCI
      │
      ▼
Frontend Streamlit (app.py)
      │
      ├── Panel de curaduría
      ├── Métricas y salud de la comunidad
      └── Persistencia en OCI Object Storage
```

La aplicación consulta y actualiza los datos almacenados en PostgreSQL. La ejecución de los workflows de n8n y la configuración de los servicios externos se gestionan fuera del frontend.

## Funcionalidades

### 1. Panel de curaduría de activos

Permite revisar los activos almacenados en `activo_generado`, filtrarlos por estado y editar su título y contenido antes de registrar una decisión de curaduría.

Tipos de activos contemplados:

- **LINKEDIN:** publicaciones para redes profesionales.
- **NEWSLETTER:** contenido organizado para boletines.
- **FAQ:** preguntas frecuentes y consejos.

Acciones disponibles:

- Filtrar por estado: `borrador`, `aprobado`, `rechazado` o `TODOS`.
- Consultar el tipo de activo, lote de procesamiento, período y comunidad de origen.
- Editar el título y el contenido.
- Añadir una nota o motivo de curaduría.
- Aprobar o rechazar un activo.
- Inspeccionar el contenido JSONB del activo.

Cuando el esquema de base de datos incluye la tabla `version_activo`, la aplicación registra nuevas versiones. En el esquema compatible con OCI por versión, la aprobación también puede crear un registro pendiente en `almacenamiento_oci`.

**Nota:** aprobar un activo registra su estado de curaduría; no significa que se publique automáticamente en LinkedIn ni en otra plataforma externa.

### 2. Métricas y salud de la comunidad

Presenta información de los lotes registrados en `lote_procesamiento` y permite inspeccionar un lote específico.

Incluye:

- Total de interacciones del lote seleccionado y acumulado de los lotes consultados.
- Sentimiento predominante.
- Estado del procesamiento.
- Comunidad de origen.
- Temas principales detectados.
- Tabla de interacciones analizadas, con campos como autor, canal, tipo de insight, sentimiento, relevancia, resumen y comentario.
- Historial de lotes procesados.

Los datos se consultan desde las tablas `lote_procesamiento`, `actividad`, `analisis`, `autor`, `canal` y `fuente`.

### 3. Persistencia en OCI Object Storage

Permite inspeccionar los registros de `almacenamiento_oci` asociados a los paquetes de distribución.

Muestra información como:

- Bucket configurado.
- Ruta del objeto.
- Estado del registro.
- Fecha de creación o actualización.
- Detalles de error, cuando existen.
- Información del lote y, según el esquema, del activo y su versión.

La pestaña consulta los registros de la base de datos; no constituye por sí sola una verificación directa de disponibilidad del objeto en OCI.

### 4. Herramientas de demostración y esquema

La barra lateral incluye utilidades para:

- Actualizar la interfaz.
- Insertar datos de demostración.
- Devolver los activos al estado `borrador`.
- Aplicar una migración de esquema cuando corresponde.

**Precaución:** las opciones de demostración y migración realizan escrituras en la base de datos. Utilízalas únicamente en un entorno controlado y después de verificar el destino de la conexión.

## Estructura del directorio

```text
frontend/
├── app.py
├── requirements.txt
└── README.md
```

- `app.py`: interfaz Streamlit, consultas a PostgreSQL, actualización de activos, métricas y visualización de registros OCI.
- `requirements.txt`: dependencias Python necesarias para la aplicación.
- `README.md`: documentación del frontend.

## Tecnologías

- **Python:** lenguaje de implementación.
- **Streamlit:** interfaz web interactiva.
- **pandas:** organización y presentación tabular de los datos.
- **psycopg2-binary:** conexión con PostgreSQL.
- **PostgreSQL / Supabase:** almacenamiento consultado y actualizado por la aplicación.
- **n8n:** workflows externos que procesan interacciones y generan activos.
- **Oracle Cloud Infrastructure (OCI) Object Storage:** servicio de almacenamiento reflejado en los registros consultados por la interfaz.

## Requisitos previos

- Python instalado en el entorno de ejecución.
- Acceso de red a la instancia PostgreSQL/Supabase.
- Credenciales válidas de base de datos configuradas mediante variables de entorno.
- Esquema y tablas requeridos por la aplicación creados en la base de datos.
- Workflows de n8n configurados si se desea visualizar datos generados por el pipeline.

## Instalación y ejecución local

### 1. Obtener el código

Clona el repositorio y entra en el directorio del frontend:

```bash
git clone <URL_DEL_REPOSITORIO>
cd G10-LATAM-EQUIPO43-CommunityLab/frontend
```

Si ya tienes el repositorio clonado, basta con entrar en su directorio `frontend`.

### 2. Crear y activar un entorno virtual

```bash
python -m venv .venv
```

**Linux/macOS:**

```bash
source .venv/bin/activate
```

**Windows PowerShell:**

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar la conexión a la base de datos

La aplicación utiliza las siguientes variables de entorno:

| Variable | Descripción |
|---|---|
| `DB_HOST` | Host del servidor PostgreSQL. |
| `DB_PORT` | Puerto de PostgreSQL; por defecto, `5432`. |
| `DB_NAME` | Nombre de la base de datos. |
| `DB_USER` | Usuario de conexión. |
| `DB_PASSWORD` | Contraseña de conexión. |
| `DB_SSLMODE` | Modo SSL de la conexión; el código utiliza `require` como valor predeterminado. |

Configura estas variables en el entorno donde se ejecutará Streamlit. Por ejemplo, en Linux/macOS:

```bash
export DB_HOST="tu-host-postgres"
export DB_PORT="5432"
export DB_NAME="tu-base-de-datos"
export DB_USER="tu-usuario"
export DB_PASSWORD="tu-contraseña"
export DB_SSLMODE="require"
```

En Windows PowerShell, puedes establecerlas para la sesión actual con `$env:DB_HOST="tu-host-postgres"` y el equivalente para cada variable.

**Seguridad:** no incluyas contraseñas reales en el repositorio ni en archivos compartidos. Antes de desplegar, elimina del código los valores sensibles usados como predeterminados y configura las credenciales mediante el entorno o el gestor de secretos de la plataforma.

### 5. Ejecutar la aplicación

Desde el directorio `frontend/`:

```bash
streamlit run app.py
```

Streamlit mostrará en la terminal la dirección local para abrir la aplicación en el navegador.

## Base de datos y compatibilidad de esquema

La aplicación consulta tablas como:

- `activo_generado`
- `version_activo`
- `lote_procesamiento`
- `actividad`
- `analisis`
- `autor`
- `canal`
- `fuente`
- `almacenamiento_oci`

El código detecta algunas diferencias entre versiones del esquema, en particular la presencia de `version_activo` y de la columna `almacenamiento_oci.id_version`. También incorpora una utilidad de migración para añadir columnas y estructuras de versionado.

Antes de ejecutar migraciones, revisa el esquema actual, realiza un respaldo y confirma que la cuenta de base de datos tenga los permisos necesarios. No ejecutes las herramientas de migración o de demostración contra una base de datos de producción sin una revisión previa.

## Flujo de uso

1. Los workflows de n8n procesan las interacciones y almacenan los resultados en PostgreSQL.
2. El frontend consulta los activos, análisis, lotes y registros de almacenamiento.
3. El usuario revisa y edita el contenido de cada activo.
4. El usuario aprueba o rechaza el activo y puede registrar un comentario.
5. Si el esquema admite versionado, se registra la versión correspondiente.
6. La pestaña de OCI permite consultar el estado registrado para los objetos asociados.

## Solución de problemas

- **Error de conexión a PostgreSQL:** comprueba las variables `DB_*`, el acceso de red, el host, el puerto y las credenciales.
- **No aparecen activos:** verifica el filtro de estado y confirma que existan registros en `activo_generado`.
- **No aparecen métricas:** revisa que `lote_procesamiento` y las tablas relacionadas contengan datos.
- **Error al aprobar o rechazar:** comprueba las restricciones, permisos y compatibilidad del esquema, especialmente si se utiliza `version_activo`.
- **No hay registros OCI:** verifica si los workflows o las acciones de curaduría han creado registros en `almacenamiento_oci`.

## Seguridad y buenas prácticas

- No subir tokens, contraseñas ni credenciales al repositorio.
- Evitar credenciales predeterminadas en el código fuente.
- Utilizar variables de entorno o un gestor de secretos.
- Restringir los permisos de la cuenta de base de datos al mínimo necesario.
- Probar las operaciones de escritura, migración y demostración en un entorno de desarrollo.
- No asumir que un registro de base de datos confirma que un objeto está disponible en OCI.

## Alcance

Este directorio contiene la interfaz Streamlit de CommunityLab para curaduría de activos, consulta de métricas comunitarias y seguimiento de registros de almacenamiento OCI. La ingesta, el análisis y la generación automatizada dependen de los componentes externos —como n8n, PostgreSQL y los servicios de IA— configurados para el proyecto.

