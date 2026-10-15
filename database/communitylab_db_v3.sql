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
    id_lote             BIGINT       NOT NULL,
    bucket              VARCHAR(200),
    ruta_objeto         TEXT,
    status              VARCHAR(30)  NOT NULL DEFAULT 'pendiente',
    detalle_error       TEXT,
    creado_en           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    actualizado_en      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_oci_lote
        FOREIGN KEY (id_lote) REFERENCES lote_procesamiento (id_lote)
        ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT uq_oci_lote UNIQUE (id_lote),

    CONSTRAINT ck_oci_status CHECK (
        status IN ('pendiente', 'guardado_con_exito', 'error', 'omitido')
    )
);

CREATE INDEX ix_oci_status ON almacenamiento_oci (status);

COMMENT ON TABLE almacenamiento_oci IS 'Referencia al paquete del lote en OCI Object Storage (0..1 por lote).';

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

CREATE OR REPLACE VIEW v_lote_resumen AS
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
    o.status AS oci_status,
    o.bucket AS oci_bucket,
    o.ruta_objeto AS oci_ruta_objeto,
    (SELECT COUNT(*) FROM actividad a WHERE a.id_lote = l.id_lote) AS actividades_count,
    (SELECT COUNT(*) FROM activo_generado ag WHERE ag.id_lote = l.id_lote) AS activos_count,
    (SELECT COUNT(*) FROM activo_generado ag
        WHERE ag.id_lote = l.id_lote AND ag.estado_curaduria = 'borrador') AS activos_borrador_count
FROM lote_procesamiento l
JOIN fuente f ON f.id_fuente = l.id_fuente
LEFT JOIN almacenamiento_oci o ON o.id_lote = l.id_lote;

COMMENT ON VIEW v_lote_resumen IS 'Listado de lotes de análisis para panel y reproceso.';

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
