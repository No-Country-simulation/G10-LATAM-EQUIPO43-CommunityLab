BEGIN;

CREATE TABLE fuente (
    id_fuente       BIGSERIAL PRIMARY KEY,
    nombre          VARCHAR(150) NOT NULL,
    creado_en       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_fuente_nombre UNIQUE (nombre)
);

COMMENT ON TABLE fuente IS 'Origen general de actividades (comunidad).';
COMMENT ON COLUMN fuente.nombre IS 'Ej. Discord_Grupo_ONE_G10';

CREATE TABLE canal (
    id_canal              BIGSERIAL PRIMARY KEY,
    id_fuente             BIGINT       NOT NULL,
    nombre                VARCHAR(150) NOT NULL,
    identificador_origen  TEXT,
    creado_en             TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_canal_fuente
        FOREIGN KEY (id_fuente) REFERENCES fuente (id_fuente)
        ON DELETE RESTRICT ON UPDATE CASCADE,

    CONSTRAINT uq_canal_fuente_nombre UNIQUE (id_fuente, nombre)
);

CREATE INDEX ix_canal_id_fuente ON canal (id_fuente);

CREATE UNIQUE INDEX uq_canal_fuente_identificador
    ON canal (id_fuente, identificador_origen)
    WHERE identificador_origen IS NOT NULL;

COMMENT ON TABLE canal IS 'Canal de procedencia dentro de una fuente (ej. #logros-y-empleos).';
COMMENT ON COLUMN canal.identificador_origen IS 'ID del canal en la plataforma de origen (ej. Discord channel id).';

CREATE TABLE autor (
    id_autor              BIGSERIAL PRIMARY KEY,
    id_fuente             BIGINT       NOT NULL,
    nombre                VARCHAR(200) NOT NULL,
    identificador_origen  TEXT,
    creado_en             TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_autor_fuente
        FOREIGN KEY (id_fuente) REFERENCES fuente (id_fuente)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE UNIQUE INDEX uq_autor_fuente_identificador
    ON autor (id_fuente, identificador_origen)
    WHERE identificador_origen IS NOT NULL;

CREATE INDEX ix_autor_id_fuente ON autor (id_fuente);

COMMENT ON TABLE autor IS 'Autor de una actividad; opcional. Identidad dependiente de la fuente.';
COMMENT ON COLUMN autor.identificador_origen IS 'ID en la plataforma de origen (ej. Discord user id).';

CREATE TABLE lote_procesamiento (
    id_lote                   BIGSERIAL PRIMARY KEY,
    id_fuente                 BIGINT       NOT NULL,
    periodo_referencia        VARCHAR(100) NOT NULL,
    estado                    VARCHAR(30)  NOT NULL DEFAULT 'recibido',
    opciones                  JSONB,
    total_interacciones       INTEGER,
    sentimiento_predominante  VARCHAR(50),
    temas_principales         JSONB,
    error_resumen             TEXT,
    workflow_execution_id     VARCHAR(100),
    ventana_desde             TIMESTAMPTZ,
    ventana_hasta             TIMESTAMPTZ,
    tipo_operacion            VARCHAR(30) NOT NULL DEFAULT 'procesamiento',
    clave_idempotencia        TEXT,
    creado_en                 TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    actualizado_en            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    finalizado_en             TIMESTAMPTZ,

    CONSTRAINT fk_lote_fuente
        FOREIGN KEY (id_fuente) REFERENCES fuente (id_fuente)
        ON DELETE RESTRICT ON UPDATE CASCADE,

    CONSTRAINT ck_lote_estado CHECK (
        estado IN ('recibido', 'procesando', 'completado', 'parcial', 'fallido')
    ),

    CONSTRAINT ck_lote_tipo_operacion CHECK (
        tipo_operacion IN ('procesamiento', 'newsletter')
    ),

    CONSTRAINT ck_lote_ventana CHECK (
        ventana_desde IS NULL
        OR ventana_hasta IS NULL
        OR ventana_desde <= ventana_hasta
    )
);

CREATE INDEX ix_lote_fuente_periodo
    ON lote_procesamiento (id_fuente, periodo_referencia);

CREATE INDEX ix_lote_estado
    ON lote_procesamiento (estado);

CREATE INDEX ix_lote_creado_en
    ON lote_procesamiento (creado_en DESC);

CREATE UNIQUE INDEX uq_lote_newsletter_idempotencia
    ON lote_procesamiento (clave_idempotencia)
    WHERE tipo_operacion = 'newsletter'
      AND clave_idempotencia IS NOT NULL;

COMMENT ON COLUMN lote_procesamiento.tipo_operacion IS
    'Clasifica el lote como procesamiento operativo o solicitud editorial de newsletter.';

COMMENT ON COLUMN lote_procesamiento.clave_idempotencia IS
    'Clave canónica de una solicitud editorial calculada por el workflow.';

COMMENT ON INDEX uq_lote_newsletter_idempotencia IS
    'Evita solicitudes editoriales equivalentes duplicadas sin bloquear lotes operativos.';

CREATE INDEX ix_lote_ventana
    ON lote_procesamiento (ventana_desde, ventana_hasta)
    WHERE ventana_desde IS NOT NULL;

COMMENT ON TABLE lote_procesamiento IS 'Corrida de análisis/generación. Se crea en schedule o proceso manual.';
COMMENT ON COLUMN lote_procesamiento.estado IS 'recibido | procesando | completado | parcial | fallido';
COMMENT ON COLUMN lote_procesamiento.opciones IS 'Opciones del job (generar_activos, idioma, tono, límites, ...)';
COMMENT ON COLUMN lote_procesamiento.temas_principales IS 'Array JSON de strings del consolidado del lote';
COMMENT ON COLUMN lote_procesamiento.ventana_desde IS 'Inicio del rango de actividades incluidas en el job';
COMMENT ON COLUMN lote_procesamiento.ventana_hasta IS 'Fin del rango de actividades incluidas en el job';

CREATE TABLE actividad (
    id_actividad            BIGSERIAL PRIMARY KEY,
    id_lote                 BIGINT,
    id_fuente               BIGINT       NOT NULL,
    id_canal                BIGINT       NOT NULL,
    id_autor                BIGINT,
    contenido               TEXT         NOT NULL,
    tipo_declarado          VARCHAR(50),
    identificador_origen    TEXT,
    momento_origen          TIMESTAMPTZ,
    contexto                JSONB,
    estado_procesamiento    VARCHAR(30)  NOT NULL DEFAULT 'pendiente',
    creado_en               TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_actividad_lote
        FOREIGN KEY (id_lote) REFERENCES lote_procesamiento (id_lote)
        ON DELETE SET NULL ON UPDATE CASCADE,

    CONSTRAINT fk_actividad_fuente
        FOREIGN KEY (id_fuente) REFERENCES fuente (id_fuente)
        ON DELETE RESTRICT ON UPDATE CASCADE,

    CONSTRAINT fk_actividad_canal
        FOREIGN KEY (id_canal) REFERENCES canal (id_canal)
        ON DELETE RESTRICT ON UPDATE CASCADE,

    CONSTRAINT fk_actividad_autor
        FOREIGN KEY (id_autor) REFERENCES autor (id_autor)
        ON DELETE SET NULL ON UPDATE CASCADE,

    CONSTRAINT ck_actividad_contenido_no_vacio CHECK (length(trim(contenido)) > 0),

    CONSTRAINT ck_actividad_estado_procesamiento CHECK (
        estado_procesamiento IN (
            'pendiente',
            'en_lote',
            'analizada',
            'omitida',
            'error'
        )
    )
);

CREATE INDEX ix_actividad_id_lote
    ON actividad (id_lote)
    WHERE id_lote IS NOT NULL;

CREATE INDEX ix_actividad_id_canal ON actividad (id_canal);
CREATE INDEX ix_actividad_id_autor ON actividad (id_autor) WHERE id_autor IS NOT NULL;

CREATE INDEX ix_actividad_pendiente
    ON actividad (id_fuente, estado_procesamiento, creado_en)
    WHERE estado_procesamiento = 'pendiente';

CREATE UNIQUE INDEX uq_actividad_fuente_identificador
    ON actividad (id_fuente, identificador_origen)
    WHERE identificador_origen IS NOT NULL;

CREATE UNIQUE INDEX uq_actividad_lote_identificador
    ON actividad (id_lote, identificador_origen)
    WHERE id_lote IS NOT NULL AND identificador_origen IS NOT NULL;

COMMENT ON TABLE actividad IS 'Hecho de comunidad. Puede existir sin lote (ingesta en tiempo real).';
COMMENT ON COLUMN actividad.id_lote IS 'NULL mientras estado_procesamiento = pendiente';
COMMENT ON COLUMN actividad.estado_procesamiento IS 'pendiente | en_lote | analizada | omitida | error';
COMMENT ON COLUMN actividad.tipo_declarado IS 'Tipo opcional de ingesta; el análisis infiere tipo_insight';
COMMENT ON COLUMN actividad.identificador_origen IS 'Message ID Discord u otro ID de origen (idempotencia)';

CREATE TABLE analisis (
    id_analisis       BIGSERIAL PRIMARY KEY,
    id_actividad      BIGINT       NOT NULL,
    sentimiento       VARCHAR(50),
    relevancia        VARCHAR(50),
    tipo_insight      VARCHAR(100),
    temas             JSONB,
    resumen           TEXT,
    evidencia_clave   TEXT,
    resultado_json    JSONB,
    creado_en         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    actualizado_en    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_analisis_actividad
        FOREIGN KEY (id_actividad) REFERENCES actividad (id_actividad)
        ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT uq_analisis_actividad UNIQUE (id_actividad)
);

CREATE INDEX ix_analisis_tipo_insight ON analisis (tipo_insight);
CREATE INDEX ix_analisis_sentimiento ON analisis (sentimiento);

COMMENT ON TABLE analisis IS 'Interpretación de una actividad. Temas en JSONB.';
COMMENT ON COLUMN analisis.temas IS 'Ej. ["OCI", "LangGraph"]';
COMMENT ON COLUMN analisis.resultado_json IS 'Salida completa del Analista LLM (auditoría).';
COMMENT ON COLUMN analisis.tipo_insight IS 'Crítico para branching: testimonio, pregunta_tecnica, duda, ...';

CREATE TABLE activo_generado (
    id_activo              BIGSERIAL PRIMARY KEY,
    id_lote                BIGINT NOT NULL,
    tipo_activo            VARCHAR(50) NOT NULL,
    contenido              JSONB NOT NULL,
    estado_curaduria       VARCHAR(30) NOT NULL DEFAULT 'borrador',
    id_version_actual      BIGINT,
    id_version_aprobada    BIGINT,
    comentario_curaduria   TEXT,
    revisado_en            TIMESTAMPTZ,
    creado_en              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en         TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_activo_lote
        FOREIGN KEY (id_lote)
        REFERENCES lote_procesamiento (id_lote)
        ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT uq_activo_lote_tipo
        UNIQUE (id_lote, tipo_activo),

    CONSTRAINT ck_activo_tipo
        CHECK (tipo_activo IN ('LINKEDIN', 'NEWSLETTER', 'FAQ')),

    CONSTRAINT ck_activo_estado_curaduria
        CHECK (
            estado_curaduria IN (
                'borrador', 'aprobado', 'rechazado', 'publicado'
            )
        )
);

CREATE INDEX ix_activo_id_lote
    ON activo_generado (id_lote);

CREATE INDEX ix_activo_estado_curaduria
    ON activo_generado (estado_curaduria);

COMMENT ON TABLE activo_generado IS
    'Activo lógico de distribución con estado de curaduría y referencias a versiones.';

COMMENT ON COLUMN activo_generado.contenido IS
    'Copia del contenido correspondiente a la versión actual.';

CREATE TABLE version_activo (
    id_version       BIGSERIAL PRIMARY KEY,
    id_activo        BIGINT NOT NULL,
    numero_version   INTEGER NOT NULL,
    contenido        JSONB NOT NULL,
    origen_version   VARCHAR(20) NOT NULL,
    motivo_cambio    TEXT,
    creado_por       VARCHAR(150),
    creado_en        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_version_activo
        FOREIGN KEY (id_activo)
        REFERENCES activo_generado (id_activo)
        ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT uq_activo_numero_version
        UNIQUE (id_activo, numero_version),

    CONSTRAINT ck_version_numero_positivo
        CHECK (numero_version >= 1),

    CONSTRAINT ck_version_origen
        CHECK (origen_version IN ('ia', 'usuario'))
);

CREATE INDEX ix_version_activo_id
    ON version_activo (id_activo);

CREATE INDEX ix_version_activo_creado_en
    ON version_activo (id_activo, creado_en DESC);

ALTER TABLE activo_generado
    ADD CONSTRAINT fk_activo_version_actual
    FOREIGN KEY (id_version_actual)
    REFERENCES version_activo (id_version)
    ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE activo_generado
    ADD CONSTRAINT fk_activo_version_aprobada
    FOREIGN KEY (id_version_aprobada)
    REFERENCES version_activo (id_version)
    ON DELETE SET NULL ON UPDATE CASCADE;

COMMENT ON TABLE version_activo IS
    'Historial de versiones del contenido generado y editado durante la curaduría.';

COMMENT ON COLUMN version_activo.origen_version IS
    'ia para la generación inicial; usuario para las ediciones humanas.';

COMMENT ON COLUMN activo_generado.id_version_actual IS
    'Versión vigente del contenido del activo.';

COMMENT ON COLUMN activo_generado.id_version_aprobada IS
    'Última versión aprobada del activo; NULL si aún no se aprobó.';

CREATE TABLE almacenamiento_oci (
    id_almacenamiento   BIGSERIAL PRIMARY KEY,
    id_version          BIGINT       NOT NULL,
    bucket              VARCHAR(200),
    ruta_objeto         TEXT,
    status              VARCHAR(30)  NOT NULL DEFAULT 'pendiente',
    checksum_sha256     CHAR(64),
    intentos            INTEGER      NOT NULL DEFAULT 0,
    proximo_intento_en  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    ultimo_intento_en   TIMESTAMPTZ,
    procesando_desde    TIMESTAMPTZ,
    detalle_error       TEXT,
    guardado_en         TIMESTAMPTZ,
    creado_en           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    actualizado_en      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_oci_version
        FOREIGN KEY (id_version) REFERENCES version_activo (id_version)
        ON DELETE CASCADE ON UPDATE CASCADE,

    -- Una versión tiene como máximo un registro de almacenamiento OCI.
    -- Los reintentos actualizan este registro, no crean uno nuevo.
    CONSTRAINT uq_oci_version UNIQUE (id_version),

    CONSTRAINT ck_oci_status CHECK (
        status IN ('pendiente', 'procesando', 'guardado_con_exito', 'error', 'omitido')
    ),
    CONSTRAINT ck_oci_intentos_no_negativos CHECK (intentos >= 0),
    CONSTRAINT ck_oci_checksum_sha256 CHECK (
        checksum_sha256 IS NULL OR checksum_sha256 ~ '^[0-9a-fA-F]{64}$'
    )
);

CREATE INDEX ix_oci_status ON almacenamiento_oci (status);
CREATE INDEX ix_oci_guardado_en ON almacenamiento_oci (guardado_en DESC);
CREATE INDEX ix_oci_reintentos_programados
    ON almacenamiento_oci (status, proximo_intento_en)
    WHERE status IN ('pendiente', 'error');
CREATE INDEX ix_oci_procesos_estancados
    ON almacenamiento_oci (procesando_desde)
    WHERE status = 'procesando';

COMMENT ON TABLE almacenamiento_oci IS
    'Referencia al objeto de OCI asociado a una versión concreta de un activo; máximo un registro por versión.';
COMMENT ON COLUMN almacenamiento_oci.id_version IS
    'Versión exacta almacenada. El flujo de aprobación debe registrar únicamente la versión aprobada.';
COMMENT ON COLUMN almacenamiento_oci.ruta_objeto IS
    'Ruta del objeto JSON en OCI Object Storage.';
COMMENT ON COLUMN almacenamiento_oci.checksum_sha256 IS
    'Hash SHA-256 del contenido serializado enviado a OCI, cuando esté disponible.';
COMMENT ON COLUMN almacenamiento_oci.intentos IS
    'Cantidad de intentos de persistencia realizados para esta versión.';
COMMENT ON COLUMN almacenamiento_oci.proximo_intento_en IS
    'Momento a partir del cual el registro puede ser procesado o reintentado.';
COMMENT ON COLUMN almacenamiento_oci.ultimo_intento_en IS
    'Fecha y hora del último intento de persistencia iniciado.';
COMMENT ON COLUMN almacenamiento_oci.procesando_desde IS
    'Inicio del intento actualmente en curso; permite detectar ejecuciones estancadas.';
COMMENT ON COLUMN almacenamiento_oci.guardado_en IS
    'Fecha y hora de confirmación de almacenamiento exitoso en OCI.';

CREATE OR REPLACE FUNCTION set_actualizado_en()
RETURNS TRIGGER AS $$
BEGIN
    NEW.actualizado_en = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_lote_actualizado
    BEFORE UPDATE ON lote_procesamiento
    FOR EACH ROW EXECUTE PROCEDURE set_actualizado_en();

CREATE TRIGGER trg_analisis_actualizado
    BEFORE UPDATE ON analisis
    FOR EACH ROW EXECUTE PROCEDURE set_actualizado_en();

CREATE TRIGGER trg_activo_actualizado
    BEFORE UPDATE ON activo_generado
    FOR EACH ROW EXECUTE PROCEDURE set_actualizado_en();

CREATE TRIGGER trg_oci_actualizado
    BEFORE UPDATE ON almacenamiento_oci
    FOR EACH ROW EXECUTE PROCEDURE set_actualizado_en();

DROP VIEW IF EXISTS v_lote_resumen;

CREATE VIEW v_lote_resumen AS
SELECT
    l.id_lote,
    f.nombre AS origen_comunidad,
    l.periodo_referencia,
    l.estado,
    l.ventana_desde,
    l.ventana_hasta,
    l.total_interacciones,
    l.sentimiento_predominante,
    l.temas_principales,
    l.error_resumen,
    l.creado_en,
    l.finalizado_en,
    (SELECT COUNT(*)
        FROM actividad a
        WHERE a.id_lote = l.id_lote) AS actividades_count,
    (SELECT COUNT(*)
        FROM activo_generado ag
        WHERE ag.id_lote = l.id_lote) AS activos_count,
    (SELECT COUNT(*)
        FROM activo_generado ag
        WHERE ag.id_lote = l.id_lote
          AND ag.estado_curaduria = 'borrador') AS activos_borrador_count,
    (SELECT COUNT(*)
        FROM almacenamiento_oci o
        JOIN version_activo v ON v.id_version = o.id_version
        JOIN activo_generado ag ON ag.id_activo = v.id_activo
        WHERE ag.id_lote = l.id_lote) AS oci_objetos_count,
    (SELECT COUNT(*)
        FROM almacenamiento_oci o
        JOIN version_activo v ON v.id_version = o.id_version
        JOIN activo_generado ag ON ag.id_activo = v.id_activo
        WHERE ag.id_lote = l.id_lote
          AND o.status = 'pendiente') AS oci_pendientes_count,
    (SELECT COUNT(*)
        FROM almacenamiento_oci o
        JOIN version_activo v ON v.id_version = o.id_version
        JOIN activo_generado ag ON ag.id_activo = v.id_activo
        WHERE ag.id_lote = l.id_lote
          AND o.status = 'guardado_con_exito') AS oci_guardados_count,
    (SELECT COUNT(*)
        FROM almacenamiento_oci o
        JOIN version_activo v ON v.id_version = o.id_version
        JOIN activo_generado ag ON ag.id_activo = v.id_activo
        WHERE ag.id_lote = l.id_lote
          AND o.status = 'error') AS oci_errores_count,
    (SELECT COUNT(*)
        FROM almacenamiento_oci o
        JOIN version_activo v ON v.id_version = o.id_version
        JOIN activo_generado ag ON ag.id_activo = v.id_activo
        WHERE ag.id_lote = l.id_lote
          AND o.status = 'omitido') AS oci_omitidos_count,
    CASE
        WHEN NOT EXISTS (
            SELECT 1
            FROM almacenamiento_oci o
            JOIN version_activo v ON v.id_version = o.id_version
            JOIN activo_generado ag ON ag.id_activo = v.id_activo
            WHERE ag.id_lote = l.id_lote
        ) THEN 'sin_registros'
        WHEN NOT EXISTS (
            SELECT 1
            FROM almacenamiento_oci o
            JOIN version_activo v ON v.id_version = o.id_version
            JOIN activo_generado ag ON ag.id_activo = v.id_activo
            WHERE ag.id_lote = l.id_lote
              AND o.status <> 'omitido'
        ) THEN 'omitido'
        WHEN EXISTS (
            SELECT 1
            FROM almacenamiento_oci o
            JOIN version_activo v ON v.id_version = o.id_version
            JOIN activo_generado ag ON ag.id_activo = v.id_activo
            WHERE ag.id_lote = l.id_lote
              AND o.status = 'guardado_con_exito'
        ) AND EXISTS (
            SELECT 1
            FROM almacenamiento_oci o
            JOIN version_activo v ON v.id_version = o.id_version
            JOIN activo_generado ag ON ag.id_activo = v.id_activo
            WHERE ag.id_lote = l.id_lote
              AND o.status <> 'guardado_con_exito'
        ) THEN 'parcial'
        WHEN EXISTS (
            SELECT 1
            FROM almacenamiento_oci o
            JOIN version_activo v ON v.id_version = o.id_version
            JOIN activo_generado ag ON ag.id_activo = v.id_activo
            WHERE ag.id_lote = l.id_lote
              AND o.status = 'error'
        ) THEN 'error'
        WHEN EXISTS (
            SELECT 1
            FROM almacenamiento_oci o
            JOIN version_activo v ON v.id_version = o.id_version
            JOIN activo_generado ag ON ag.id_activo = v.id_activo
            WHERE ag.id_lote = l.id_lote
              AND o.status = 'pendiente'
        ) THEN 'pendiente'
        WHEN EXISTS (
            SELECT 1
            FROM almacenamiento_oci o
            JOIN version_activo v ON v.id_version = o.id_version
            JOIN activo_generado ag ON ag.id_activo = v.id_activo
            WHERE ag.id_lote = l.id_lote
              AND o.status = 'procesando'
        ) THEN 'procesando'
        ELSE 'guardado_con_exito'
    END AS oci_status
FROM lote_procesamiento l
JOIN fuente f ON f.id_fuente = l.id_fuente;

COMMENT ON VIEW v_lote_resumen IS
    'Listado de lotes para panel y reproceso, con conteos y estado agregado de almacenamiento OCI.';

CREATE OR REPLACE VIEW v_activos_versiones_oci AS
SELECT
    l.id_lote,
    ag.id_activo,
    ag.tipo_activo,
    ag.estado_curaduria,
    v.id_version,
    v.numero_version,
    v.origen_version,
    v.creado_en AS version_creada_en,
    (ag.id_version_aprobada = v.id_version) AS es_version_aprobada,
    o.id_almacenamiento,
    o.status AS oci_status,
    o.bucket AS oci_bucket,
    o.ruta_objeto AS oci_ruta_objeto,
    o.checksum_sha256 AS oci_checksum_sha256,
    o.intentos AS oci_intentos,
    o.detalle_error AS oci_detalle_error,
    o.guardado_en AS oci_guardado_en,
    o.creado_en AS oci_registro_creado_en,
    o.actualizado_en AS oci_actualizado_en
FROM activo_generado ag
JOIN lote_procesamiento l ON l.id_lote = ag.id_lote
JOIN version_activo v ON v.id_activo = ag.id_activo
LEFT JOIN almacenamiento_oci o ON o.id_version = v.id_version;

COMMENT ON VIEW v_activos_versiones_oci IS
    'Consulta de activos y versiones, indicando cuál está aprobada y su estado de almacenamiento OCI.';

CREATE OR REPLACE VIEW v_actividades_pendientes AS
SELECT
    a.id_actividad,
    f.nombre AS origen_comunidad,
    c.nombre AS canal,
    au.nombre AS autor,
    a.contenido,
    a.tipo_declarado,
    a.identificador_origen,
    a.momento_origen,
    a.creado_en,
    a.id_fuente,
    a.id_canal,
    a.id_autor
FROM actividad a
JOIN fuente f ON f.id_fuente = a.id_fuente
JOIN canal c ON c.id_canal = a.id_canal
LEFT JOIN autor au ON au.id_autor = a.id_autor
WHERE a.estado_procesamiento = 'pendiente'
ORDER BY a.creado_en;

COMMENT ON VIEW v_actividades_pendientes IS 'Cola para el job batch: actividades pendientes de análisis.';



-- Aprueba la versión actual y registra su almacenamiento OCI pendiente
-- dentro de la misma transacción de la llamada a esta función.
CREATE OR REPLACE FUNCTION public.communitylab_aprobar_activo(
    p_id_activo BIGINT,
    p_comentario_curaduria TEXT DEFAULT NULL
)
RETURNS TABLE (
    id_activo BIGINT,
    id_lote BIGINT,
    tipo_activo VARCHAR(50),
    estado_curaduria VARCHAR(30),
    id_version_actual BIGINT,
    id_version_aprobada BIGINT,
    comentario_curaduria TEXT,
    revisado_en TIMESTAMPTZ,
    actualizado_en TIMESTAMPTZ,
    id_almacenamiento BIGINT,
    oci_status VARCHAR(30),
    status_http INTEGER,
    resultado TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_activo activo_generado%ROWTYPE;
    v_id_almacenamiento BIGINT;
    v_oci_status VARCHAR(30);
BEGIN
    -- Serializa solicitudes concurrentes de aprobación para el mismo activo.
    SELECT ag.*
      INTO v_activo
      FROM activo_generado AS ag
     WHERE ag.id_activo = p_id_activo
     FOR UPDATE;

    IF NOT FOUND THEN
        RETURN QUERY
        SELECT
            NULL::BIGINT,
            NULL::BIGINT,
            NULL::VARCHAR(50),
            NULL::VARCHAR(30),
            NULL::BIGINT,
            NULL::BIGINT,
            NULL::TEXT,
            NULL::TIMESTAMPTZ,
            NULL::TIMESTAMPTZ,
            NULL::BIGINT,
            NULL::VARCHAR(30),
            404::INTEGER,
            'not_found'::TEXT;
        RETURN;
    END IF;

    IF v_activo.estado_curaduria <> 'borrador'
       OR v_activo.id_version_actual IS NULL THEN
        RETURN QUERY
        SELECT
            v_activo.id_activo,
            v_activo.id_lote,
            v_activo.tipo_activo,
            v_activo.estado_curaduria,
            v_activo.id_version_actual,
            v_activo.id_version_aprobada,
            v_activo.comentario_curaduria,
            v_activo.revisado_en,
            v_activo.actualizado_en,
            NULL::BIGINT,
            NULL::VARCHAR(30),
            409::INTEGER,
            'state_conflict'::TEXT;
        RETURN;
    END IF;

    -- La FK verifica que exista la versión, pero esta comprobación adicional
    -- garantiza que la versión actual pertenezca al activo que se aprueba.
    IF NOT EXISTS (
        SELECT 1
          FROM version_activo AS va
         WHERE va.id_version = v_activo.id_version_actual
           AND va.id_activo = v_activo.id_activo
    ) THEN
        RETURN QUERY
        SELECT
            v_activo.id_activo,
            v_activo.id_lote,
            v_activo.tipo_activo,
            v_activo.estado_curaduria,
            v_activo.id_version_actual,
            v_activo.id_version_aprobada,
            v_activo.comentario_curaduria,
            v_activo.revisado_en,
            v_activo.actualizado_en,
            NULL::BIGINT,
            NULL::VARCHAR(30),
            409::INTEGER,
            'invalid_current_version'::TEXT;
        RETURN;
    END IF;

    UPDATE activo_generado AS ag
       SET estado_curaduria = 'aprobado',
           id_version_aprobada = v_activo.id_version_actual,
           comentario_curaduria = p_comentario_curaduria,
           revisado_en = NOW(),
           actualizado_en = NOW()
     WHERE ag.id_activo = v_activo.id_activo
    RETURNING ag.* INTO v_activo;

    -- Una fila por versión. Si ya existe, no se reinicia ni se duplica:
    -- esto conserva el estado de una carga previa de esa misma versión.
    INSERT INTO almacenamiento_oci (id_version, status)
    VALUES (v_activo.id_version_aprobada, 'pendiente')
    ON CONFLICT (id_version) DO NOTHING
    RETURNING almacenamiento_oci.id_almacenamiento INTO v_id_almacenamiento;

    IF v_id_almacenamiento IS NULL THEN
        SELECT o.id_almacenamiento, o.status
          INTO v_id_almacenamiento, v_oci_status
          FROM almacenamiento_oci AS o
         WHERE o.id_version = v_activo.id_version_aprobada;
    ELSE
        v_oci_status := 'pendiente';
    END IF;

    RETURN QUERY
    SELECT
        v_activo.id_activo,
        v_activo.id_lote,
        v_activo.tipo_activo,
        v_activo.estado_curaduria,
        v_activo.id_version_actual,
        v_activo.id_version_aprobada,
        v_activo.comentario_curaduria,
        v_activo.revisado_en,
        v_activo.actualizado_en,
        v_id_almacenamiento,
        v_oci_status,
        200::INTEGER,
        'ok'::TEXT;
END;
$$;

COMMENT ON FUNCTION public.communitylab_aprobar_activo(BIGINT, TEXT) IS
    'Aprueba la versión actual de un activo y crea su registro OCI pendiente atómicamente; no realiza llamadas a OCI.';


CREATE OR REPLACE FUNCTION public.communitylab_editar_activo(
    p_id_activo BIGINT,
    p_contenido JSONB,
    p_motivo_cambio TEXT,
    p_creado_por VARCHAR(150)
)
RETURNS TABLE (
    id_activo BIGINT,
    id_lote BIGINT,
    tipo_activo VARCHAR(50),
    estado_curaduria VARCHAR(30),
    id_version_actual BIGINT,
    id_version_aprobada BIGINT,
    actualizado_en TIMESTAMPTZ,
    numero_version INTEGER,
    origen_version VARCHAR(20),
    contenido JSONB,
    motivo_cambio TEXT,
    creado_por VARCHAR(150),
    creado_en TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_activo activo_generado%ROWTYPE;
    v_numero_version INTEGER;
    v_id_version BIGINT;
BEGIN
    SELECT ag.*
      INTO v_activo
      FROM activo_generado AS ag
     WHERE ag.id_activo = p_id_activo
     FOR UPDATE;

    IF NOT FOUND THEN
        RETURN;
    END IF;

    IF v_activo.estado_curaduria = 'publicado' THEN
        RETURN;
    END IF;

    SELECT COALESCE(MAX(va.numero_version), 0) + 1
      INTO v_numero_version
      FROM version_activo AS va
     WHERE va.id_activo = p_id_activo;

    INSERT INTO version_activo (
        id_activo,
        numero_version,
        contenido,
        origen_version,
        motivo_cambio,
        creado_por
    )
    VALUES (
        p_id_activo,
        v_numero_version,
        p_contenido,
        'usuario',
        p_motivo_cambio,
        p_creado_por
    )
    RETURNING version_activo.id_version INTO v_id_version;

    UPDATE activo_generado AS ag
       SET contenido = p_contenido,
           id_version_actual = v_id_version,
           actualizado_en = NOW(),
           estado_curaduria = 'borrador'
     WHERE ag.id_activo = p_id_activo;

    RETURN QUERY
    SELECT
        ag.id_activo,
        ag.id_lote,
        ag.tipo_activo,
        ag.estado_curaduria,
        ag.id_version_actual,
        ag.id_version_aprobada,
        ag.actualizado_en,
        va.numero_version,
        va.origen_version,
        va.contenido,
        va.motivo_cambio,
        va.creado_por,
        va.creado_en
    FROM activo_generado AS ag
    JOIN version_activo AS va ON va.id_version = v_id_version
    WHERE ag.id_activo = p_id_activo;
END;
$$;

COMMIT;
