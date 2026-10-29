import json
import os
from datetime import datetime, timezone
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor, Json
import streamlit as st

# ==============================================================================
# 1. CONFIGURACIÓN DE PÁGINA (Debe ser el primer comando de Streamlit)
# ==============================================================================
st.set_page_config(
    page_title="CommunityLab | Panel de Curaduría",
    layout="wide",
    page_icon="🚀",
    initial_sidebar_state="expanded",
)

# ==============================================================================
# 2. ESTILOS CSS PERSONALIZADOS (UI Ejecutiva + Badges OCI & Temas)
# ==============================================================================
st.markdown(
    """
    <style>
        .main-header {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 60%, #312e81 100%);
            padding: 1.6rem 2rem;
            border-radius: 14px;
            color: #f8fafc;
            margin-bottom: 1.5rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.25);
        }
        .main-header h1 {
            margin: 0;
            font-size: 1.85rem;
            font-weight: 800;
            color: #ffffff;
            letter-spacing: -0.02em;
        }
        .main-header p {
            margin: 0.4rem 0 0 0;
            color: #cbd5e1;
            font-size: 0.98rem;
        }
        .oci-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: linear-gradient(90deg, #c74634 0%, #ea580c 100%);
            color: #ffffff;
            padding: 0.35rem 0.85rem;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 700;
            letter-spacing: 0.03em;
            text-transform: uppercase;
            box-shadow: 0 2px 8px rgba(199, 70, 52, 0.45);
            margin-bottom: 0.6rem;
        }
        .topic-badge {
            display: inline-block;
            background: #1e293b;
            color: #38bdf8;
            border: 1px solid #0284c7;
            padding: 0.35rem 0.85rem;
            border-radius: 999px;
            font-size: 0.85rem;
            font-weight: 600;
            margin: 0.25rem 0.35rem 0.25rem 0;
        }
        .oci-card {
            background: #0f172a;
            border: 1px solid #334155;
            border-left: 5px solid #c74634;
            border-radius: 10px;
            padding: 1.2rem 1.5rem;
            color: #f1f5f9;
            margin-bottom: 1rem;
        }
        .oci-code {
            font-family: 'Courier New', Courier, monospace;
            background: #1e293b;
            color: #38bdf8;
            padding: 0.25rem 0.55rem;
            border-radius: 6px;
            font-size: 0.9rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# 3. CONEXIÓN A POSTGRESQL (SUPABASE)
# ==============================================================================
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "aws-0-us-east-1.pooler.supabase.com"),
    "port": int(os.environ.get("DB_PORT", 5432)),
    "database": os.environ.get("DB_NAME", "postgres"),
    "user": os.environ.get("DB_USER", "postgres.lpcysytybmfcorfybcpv"),
    "password": os.environ.get("DB_PASSWORD", "g43hackaton"),
    "sslmode": os.environ.get("DB_SSLMODE", "require"),
}

DEFAULT_OCI_BUCKET = "communitylab-activos-marketing"


def get_connection():
    """Crea y retorna una nueva conexión a PostgreSQL en Supabase."""
    return psycopg2.connect(**DB_CONFIG, connect_timeout=10)


def check_db_status():
    """
    Verifica conectividad y detecta la versión del esquema en Supabase:
    - v1: sin tabla version_activo
    - v2: con tabla version_activo y almacenamiento_oci.id_lote
    - v3.1: con tabla version_activo y almacenamiento_oci.id_version
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = 'version_activo'
                    );
                    """
                )
                has_v2 = cur.fetchone()[0]

                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'almacenamiento_oci'
                          AND column_name = 'id_version'
                    );
                    """
                )
                has_v31_oci = cur.fetchone()[0]
                schema_label = (
                    "v3.1 (versionado + cola OCI por versión)"
                    if has_v31_oci
                    else ("v2 (con version_activo)" if has_v2 else "v1 (estándar)")
                )
                return True, has_v2, has_v31_oci, schema_label, None
    except Exception as exc:
        return False, False, False, "desconocido", str(exc)


# ==============================================================================
# 4. FUNCIONES DE ACCESO Y ACTUALIZACIÓN DE DATOS
# ==============================================================================
def fetch_lotes_con_activos():
    """Consulta los IDs de lote disponibles en 'activo_generado' ordenados del más reciente al más antiguo."""
    query = """
        SELECT
            ag.id_lote,
            MAX(lp.periodo_referencia) AS periodo_referencia,
            COUNT(*) AS total_activos
        FROM activo_generado ag
        LEFT JOIN lote_procesamiento lp ON lp.id_lote = ag.id_lote
        GROUP BY ag.id_lote
        ORDER BY ag.id_lote DESC;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            return cur.fetchall()


def fetch_activos(estado_filtro="borrador", id_lote_filtro=None):
    """Consulta activos en 'activo_generado' junto con información de su lote, autor y canal original de Discord."""
    query = """
        SELECT
            ag.id_activo,
            ag.id_lote,
            ag.tipo_activo,
            ag.contenido,
            ag.estado_curaduria,
            ag.comentario_curaduria,
            ag.revisado_en,
            ag.creado_en,
            ag.actualizado_en,
            lp.periodo_referencia,
            lp.sentimiento_predominante,
            f.nombre AS origen_comunidad,
            (
                SELECT string_agg(DISTINCT au.nombre, ', ')
                FROM actividad a
                JOIN autor au ON au.id_autor = a.id_autor
                WHERE a.id_lote = ag.id_lote
            ) AS autor_discord,
            (
                SELECT string_agg(DISTINCT c.nombre, ', ')
                FROM actividad a
                JOIN canal c ON c.id_canal = a.id_canal
                WHERE a.id_lote = ag.id_lote
            ) AS canal_discord
        FROM activo_generado ag
        LEFT JOIN lote_procesamiento lp ON lp.id_lote = ag.id_lote
        LEFT JOIN fuente f ON f.id_fuente = lp.id_fuente
    """
    conditions = []
    params = []
    if estado_filtro != "TODOS":
        conditions.append("ag.estado_curaduria = %s")
        params.append(estado_filtro)
    if id_lote_filtro is not None:
        conditions.append("ag.id_lote = %s")
        params.append(id_lote_filtro)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY ag.id_activo DESC;"

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall()


def extract_titulo_y_copy(tipo_activo: str, contenido: dict) -> tuple[str, str]:
    """
    Extrae de manera resiliente el 'titulo' y 'copy' desde el JSONB `contenido`
    de acuerdo con los contratos de LINKEDIN, NEWSLETTER y FAQ en n8n.
    """
    if not isinstance(contenido, dict):
        return "", str(contenido or "")

    # 1. Extraer título según las llaves posibles del schema
    titulo = (
        contenido.get("titulo")
        or contenido.get("titular")
        or contenido.get("tema")
        or contenido.get("seccion")
        or f"Activo {tipo_activo}"
    )

    # 2. Extraer copy / cuerpo principal según las llaves posibles del schema
    if "copy" in contenido and contenido.get("copy"):
        copy_text = contenido["copy"]
    elif "secciones" in contenido and isinstance(contenido["secciones"], list):
        partes = []
        if contenido.get("introduccion"):
            partes.append(contenido["introduccion"])
        for sec in contenido["secciones"]:
            if isinstance(sec, dict):
                sec_titulo = sec.get("titulo", "Sección")
                sec_cont = sec.get("contenido", "")
                partes.append(f"### {sec_titulo}\n{sec_cont}")
        if contenido.get("cierre"):
            partes.append(contenido["cierre"])
        copy_text = "\n\n".join(partes)
    elif "resumen" in contenido and contenido.get("resumen"):
        copy_text = contenido["resumen"]
    elif "contenido_sugerido" in contenido and contenido.get("contenido_sugerido"):
        copy_text = contenido["contenido_sugerido"]
    elif "texto" in contenido and contenido.get("texto"):
        copy_text = contenido["texto"]
    elif "text" in contenido and contenido.get("text"):
        copy_text = contenido["text"]
    else:
        copy_text = json.dumps(contenido, ensure_ascii=False, indent=2)

    return str(titulo), str(copy_text)


def build_updated_contenido(
    tipo_activo: str, contenido_original: dict, nuevo_titulo: str, nuevo_copy: str
) -> dict:
    """
    Construye el JSONB actualizado preservando metadatos del activo y
    sincronizando las llaves 'titulo' y 'copy' (más equivalentes por tipo).
    """
    nuevo = dict(contenido_original) if isinstance(contenido_original, dict) else {}
    nuevo["titulo"] = nuevo_titulo
    nuevo["copy"] = nuevo_copy

    if tipo_activo == "NEWSLETTER":
        if "titular" in nuevo:
            nuevo["titular"] = nuevo_titulo
        if "resumen" in nuevo:
            nuevo["resumen"] = nuevo_copy
    elif tipo_activo == "FAQ":
        if "tema" in nuevo:
            nuevo["tema"] = nuevo_titulo
        if "contenido_sugerido" in nuevo:
            nuevo["contenido_sugerido"] = nuevo_copy

    return nuevo


def actualizar_estado_activo(
    id_activo: int,
    tipo_activo: str,
    contenido_original: dict,
    nuevo_titulo: str,
    nuevo_copy: str,
    nuevo_estado: str,
    comentario: str = "",
):
    """
    Ejecuta UPDATE en 'activo_generado' guardando el contenido editado (titulo y copy)
    y actualizando 'estado_curaduria' ('aprobado' o 'rechazado') con revisado_en = NOW().
    Registra la versión correspondiente en 'version_activo' y encola en 'almacenamiento_oci'
    mediante verificación previa con SELECT (sin usar ON CONFLICT que pueda fallar).
    """
    contenido_actualizado = build_updated_contenido(
        tipo_activo, contenido_original, nuevo_titulo, nuevo_copy
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'version_activo'
                );
                """
            )
            has_v2 = cur.fetchone()[0]

            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'almacenamiento_oci'
                      AND column_name = 'id_version'
                );
                """
            )
            has_v31_oci = cur.fetchone()[0]

            cur.execute(
                "SELECT id_lote FROM activo_generado WHERE id_activo = %s LIMIT 1;",
                (id_activo,),
            )
            row_activo = cur.fetchone()
            id_lote_activo = row_activo[0] if row_activo else None

            if has_v2:
                cur.execute(
                    "SELECT COALESCE(MAX(numero_version), 0) + 1 FROM version_activo WHERE id_activo = %s;",
                    (id_activo,),
                )
                next_ver = cur.fetchone()[0]
                cur.execute(
                    """
                    INSERT INTO version_activo (
                        id_activo, numero_version, contenido, origen_version, motivo_cambio, creado_por
                    ) VALUES (%s, %s, %s, 'usuario', %s, 'streamlit_curador')
                    RETURNING id_version;
                    """,
                    (
                        id_activo,
                        next_ver,
                        Json(contenido_actualizado),
                        comentario or f"Curaduría ({nuevo_estado}) desde Streamlit",
                    ),
                )
                id_version_nueva = cur.fetchone()[0]

                if nuevo_estado == "aprobado":
                    cur.execute(
                        """
                        UPDATE activo_generado
                        SET contenido = %s,
                            estado_curaduria = %s,
                            comentario_curaduria = %s,
                            id_version_actual = %s,
                            id_version_aprobada = %s,
                            revisado_en = NOW(),
                            actualizado_en = NOW()
                        WHERE id_activo = %s;
                        """,
                        (
                            Json(contenido_actualizado),
                            nuevo_estado,
                            comentario or "Aprobado desde Panel de Curaduría Streamlit",
                            id_version_nueva,
                            id_version_nueva,
                            id_activo,
                        ),
                    )
                    # Encolar en almacenamiento_oci con verificación previa SELECT (sin ON CONFLICT)
                    ruta_obj = f"activos/{id_activo}/versiones/v{next_ver}/activo-{id_activo}-version-{id_version_nueva}.json"
                    if has_v31_oci:
                        cur.execute(
                            "SELECT id_almacenamiento FROM almacenamiento_oci WHERE id_version = %s LIMIT 1;",
                            (id_version_nueva,),
                        )
                        existing_oci = cur.fetchone()
                        if existing_oci:
                            cur.execute(
                                """
                                UPDATE almacenamiento_oci
                                SET bucket = %s,
                                    ruta_objeto = %s,
                                    actualizado_en = NOW()
                                WHERE id_almacenamiento = %s;
                                """,
                                (DEFAULT_OCI_BUCKET, ruta_obj, existing_oci[0]),
                            )
                        else:
                            cur.execute(
                                """
                                INSERT INTO almacenamiento_oci (id_version, bucket, ruta_objeto, status)
                                VALUES (%s, %s, %s, 'pendiente');
                                """,
                                (id_version_nueva, DEFAULT_OCI_BUCKET, ruta_obj),
                            )
                    elif id_lote_activo is not None:
                        cur.execute(
                            "SELECT id_almacenamiento FROM almacenamiento_oci WHERE id_lote = %s LIMIT 1;",
                            (id_lote_activo,),
                        )
                        existing_oci = cur.fetchone()
                        if existing_oci:
                            cur.execute(
                                """
                                UPDATE almacenamiento_oci
                                SET bucket = %s,
                                    ruta_objeto = %s,
                                    actualizado_en = NOW()
                                WHERE id_almacenamiento = %s;
                                """,
                                (DEFAULT_OCI_BUCKET, ruta_obj, existing_oci[0]),
                            )
                        else:
                            cur.execute(
                                """
                                INSERT INTO almacenamiento_oci (id_lote, bucket, ruta_objeto, status)
                                VALUES (%s, %s, %s, 'pendiente');
                                """,
                                (id_lote_activo, DEFAULT_OCI_BUCKET, ruta_obj),
                            )
                else:
                    cur.execute(
                        """
                        UPDATE activo_generado
                        SET contenido = %s,
                            estado_curaduria = %s,
                            comentario_curaduria = %s,
                            id_version_actual = %s,
                            revisado_en = NOW(),
                            actualizado_en = NOW()
                        WHERE id_activo = %s;
                        """,
                        (
                            Json(contenido_actualizado),
                            nuevo_estado,
                            comentario or f"Actualizado ({nuevo_estado}) desde Streamlit",
                            id_version_nueva,
                            id_activo,
                        ),
                    )
            else:
                cur.execute(
                    """
                    UPDATE activo_generado
                    SET contenido = %s,
                        estado_curaduria = %s,
                        comentario_curaduria = %s,
                        revisado_en = NOW(),
                        actualizado_en = NOW()
                    WHERE id_activo = %s;
                    """,
                    (
                        Json(contenido_actualizado),
                        nuevo_estado,
                        comentario or f"Estado {nuevo_estado} desde Panel Streamlit",
                        id_activo,
                    ),
                )
                if nuevo_estado == "aprobado" and id_lote_activo is not None:
                    ruta_obj = f"activos/lote-{id_lote_activo}/activo-{id_activo}-aprobado.json"
                    cur.execute(
                        "SELECT id_almacenamiento FROM almacenamiento_oci WHERE id_lote = %s LIMIT 1;",
                        (id_lote_activo,),
                    )
                    existing_oci = cur.fetchone()
                    if existing_oci:
                        cur.execute(
                            """
                            UPDATE almacenamiento_oci
                            SET bucket = %s,
                                ruta_objeto = %s,
                                actualizado_en = NOW()
                            WHERE id_almacenamiento = %s;
                            """,
                            (DEFAULT_OCI_BUCKET, ruta_obj, existing_oci[0]),
                        )
                    else:
                        cur.execute(
                            """
                            INSERT INTO almacenamiento_oci (id_lote, bucket, ruta_objeto, status)
                            VALUES (%s, %s, %s, 'pendiente');
                            """,
                            (id_lote_activo, DEFAULT_OCI_BUCKET, ruta_obj),
                        )
        conn.commit()


def fetch_lotes_procesamiento():
    """Consulta la tabla 'lote_procesamiento' ordenada del más reciente al más antiguo."""
    query = """
        SELECT
            lp.id_lote,
            f.nombre AS origen_comunidad,
            lp.periodo_referencia,
            lp.estado,
            lp.total_interacciones,
            lp.sentimiento_predominante,
            lp.temas_principales,
            lp.error_resumen,
            lp.workflow_execution_id,
            lp.creado_en,
            lp.actualizado_en,
            lp.finalizado_en
        FROM lote_procesamiento lp
        LEFT JOIN fuente f ON f.id_fuente = lp.id_fuente
        ORDER BY lp.id_lote DESC;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            return cur.fetchall()


def fetch_analisis_interacciones(id_lote: int | None = None):
    """
    Consulta las actividades/comentarios evaluados por Gemini ('actividad' + 'analisis')
    mostrando sentimiento, relevancia/puntaje, tipo_insight y evidencia_clave.
    """
    query = """
        SELECT
            a.id_actividad,
            a.id_lote,
            au.nombre AS autor,
            c.nombre AS canal,
            a.contenido AS comentario,
            an.sentimiento,
            an.relevancia,
            an.tipo_insight,
            an.temas,
            an.resumen,
            an.evidencia_clave,
            a.creado_en
        FROM actividad a
        LEFT JOIN autor au ON au.id_autor = a.id_autor
        LEFT JOIN canal c ON c.id_canal = a.id_canal
        LEFT JOIN analisis an ON an.id_actividad = a.id_actividad
    """
    params = []
    if id_lote is not None:
        query += " WHERE a.id_lote = %s"
        params.append(id_lote)
    query += " ORDER BY a.id_actividad DESC LIMIT 50;"

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall()


def fetch_count_guardados_oci() -> int:
    """Retorna el número real de paquetes guardados con éxito en 'almacenamiento_oci'."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM almacenamiento_oci WHERE status = 'guardado_con_exito';"
            )
            row = cur.fetchone()
            return int(row[0]) if row and row[0] is not None else 0


def fetch_almacenamiento_oci():
    """
    Consulta la tabla 'almacenamiento_oci' real adaptándose automáticamente al esquema:
    incluye id_almacenamiento, bucket, ruta_objeto, status y fecha de guardado.
    """
    with get_connection() as conn:
        with conn.cursor() as cur_check:
            cur_check.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'almacenamiento_oci'
                      AND column_name = 'id_version'
                );
                """
            )
            has_id_version = cur_check.fetchone()[0]

            cur_check.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'almacenamiento_oci'
                      AND column_name = 'guardado_en'
                );
                """
            )
            has_guardado_en = cur_check.fetchone()[0]

        expr_fecha = (
            "COALESCE(ao.guardado_en, ao.actualizado_en, ao.creado_en)"
            if has_guardado_en
            else "COALESCE(ao.actualizado_en, ao.creado_en)"
        )

        if has_id_version:
            query = f"""
                SELECT
                    ao.id_almacenamiento,
                    COALESCE(ag.id_lote, ao.id_lote) AS id_lote,
                    ag.id_activo,
                    ag.tipo_activo,
                    va.id_version,
                    va.numero_version,
                    ao.bucket,
                    ao.ruta_objeto,
                    ao.status,
                    {expr_fecha} AS fecha_guardado,
                    ao.detalle_error,
                    ao.creado_en,
                    ao.actualizado_en,
                    lp.periodo_referencia,
                    lp.estado AS estado_lote,
                    lp.total_interacciones,
                    lp.sentimiento_predominante,
                    f.nombre AS origen_comunidad
                FROM almacenamiento_oci ao
                LEFT JOIN version_activo va ON va.id_version = ao.id_version
                LEFT JOIN activo_generado ag ON ag.id_activo = va.id_activo
                LEFT JOIN lote_procesamiento lp ON lp.id_lote = COALESCE(ag.id_lote, ao.id_lote)
                LEFT JOIN fuente f ON f.id_fuente = lp.id_fuente
                ORDER BY ao.id_almacenamiento DESC;
            """
        else:
            query = f"""
                SELECT
                    ao.id_almacenamiento,
                    ao.id_lote,
                    ao.bucket,
                    ao.ruta_objeto,
                    ao.status,
                    {expr_fecha} AS fecha_guardado,
                    ao.detalle_error,
                    ao.creado_en,
                    ao.actualizado_en,
                    lp.periodo_referencia,
                    lp.estado AS estado_lote,
                    lp.total_interacciones,
                    lp.sentimiento_predominante,
                    f.nombre AS origen_comunidad
                FROM almacenamiento_oci ao
                LEFT JOIN lote_procesamiento lp ON lp.id_lote = ao.id_lote
                LEFT JOIN fuente f ON f.id_fuente = lp.id_fuente
                ORDER BY ao.id_almacenamiento DESC;
            """
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            return cur.fetchall()


# ==============================================================================
# 5. UTILIDADES PARA DEMO Y MIGRACIÓN DE ESQUEMA
# ==============================================================================
def seed_datos_demo():
    """
    Inserta un lote de demostración completo (fuente, canales, autores, actividades,
    análisis de Gemini con puntajes/relevancia, lote_procesamiento, 3 activos en borrador
    y respaldo en almacenamiento_oci apuntando a 'communitylab-activos-marketing').
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Fuente
            cur.execute(
                """
                INSERT INTO fuente (nombre)
                VALUES ('Discord_Grupo_ONE_G10')
                ON CONFLICT (nombre) DO UPDATE SET nombre = EXCLUDED.nombre
                RETURNING id_fuente;
                """
            )
            id_fuente = cur.fetchone()[0]

            # 2. Lote de procesamiento
            temas = [
                "Contratación / Logros",
                "LangGraph / Nodos Condicionales",
                "Oracle Cloud Infrastructure (OCI)",
                "Portafolio de IA Generativa",
            ]
            cur.execute(
                """
                INSERT INTO lote_procesamiento (
                    id_fuente,
                    periodo_referencia,
                    estado,
                    total_interacciones,
                    sentimiento_predominante,
                    temas_principales,
                    workflow_execution_id,
                    finalizado_en
                )
                VALUES (%s, %s, 'completado', %s, %s, %s, %s, NOW())
                RETURNING id_lote;
                """,
                (
                    id_fuente,
                    f"Semana_04 ({datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')})",
                    14,
                    "Altamente Positivo",
                    Json(temas),
                    "exec-demo-g43-oci",
                ),
            )
            id_lote = cur.fetchone()[0]

            # 2.1. Canales, Autores, Actividades y Análisis de Gemini (para ver el scoring en vivo)
            interacciones_demo = [
                (
                    "#logros-y-empleos",
                    "Mariana Souza",
                    "testimonio",
                    "¡Comunidad, quedé seleccionada para el puesto de Desarrolladora Junior de IA! El proyecto del curso de LangChain y OCI que construí en mi portfolio marcó toda la diferencia en la entrevista técnica.",
                    "Muy Positivo",
                    "Alta (Score: 9.8/10)",
                    "testimonio",
                    ["Contratación / Logros", "Oracle Cloud Infrastructure (OCI)"],
                    "Estudiante contratada como Dev Jr de IA gracias a su portfolio en OCI y LangChain.",
                    "El proyecto del curso de LangChain y OCI que construí en mi portfolio marcó toda la diferencia",
                ),
                (
                    "#dudas-langgraph",
                    "Lucas Albuquerque",
                    "pregunta_tecnica",
                    "Tengo dudas sobre cómo estructurar los nodos condicionales en LangGraph cuando la respuesta del LLM necesita reintento. ¿Alguien tiene un ejemplo práctico de router?",
                    "Neutral",
                    "Alta (Score: 8.9/10)",
                    "pregunta_tecnica",
                    ["LangGraph / Nodos Condicionales"],
                    "Duda técnica recurrente sobre routers condicionales y reintentos en LangGraph.",
                    "Cómo estructurar los nodos condicionales en LangGraph cuando la respuesta del LLM necesita reintento",
                ),
                (
                    "#proyectos-ia",
                    "Camila Torres",
                    "testimonio",
                    "Acabo de desplegar mi primer flujo automatizado en n8n sobre una VM Always Free de Oracle Cloud conectada con Gemini y Supabase. ¡Increíble lo que aprendimos en esta etapa!",
                    "Positivo",
                    "Media-Alta (Score: 8.5/10)",
                    "logro",
                    ["Oracle Cloud Infrastructure (OCI)", "Portafolio de IA Generativa"],
                    "Despliegue exitoso de flujo n8n + Gemini en VM Always Free de OCI.",
                    "Acabo de desplegar mi primer flujo automatizado en n8n sobre una VM Always Free de Oracle Cloud",
                ),
            ]

            for (
                nombre_canal,
                nombre_autor,
                tipo_decl,
                texto_act,
                sent,
                relev,
                t_insight,
                temas_item,
                resumen_ia,
                evidencia_ia,
            ) in interacciones_demo:
                cur.execute(
                    """
                    INSERT INTO canal (id_fuente, nombre)
                    VALUES (%s, %s)
                    ON CONFLICT (id_fuente, nombre) DO UPDATE SET nombre = EXCLUDED.nombre
                    RETURNING id_canal;
                    """,
                    (id_fuente, nombre_canal),
                )
                id_canal = cur.fetchone()[0]

                cur.execute(
                    """
                    INSERT INTO autor (id_fuente, nombre)
                    VALUES (%s, %s)
                    RETURNING id_autor;
                    """,
                    (id_fuente, nombre_autor),
                )
                id_autor = cur.fetchone()[0]

                cur.execute(
                    """
                    INSERT INTO actividad (id_lote, id_fuente, id_canal, id_autor, contenido, tipo_declarado, momento_origen)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    RETURNING id_actividad;
                    """,
                    (id_lote, id_fuente, id_canal, id_autor, texto_act, tipo_decl),
                )
                id_actividad = cur.fetchone()[0]

                cur.execute(
                    """
                    INSERT INTO analisis (
                        id_actividad, sentimiento, relevancia, tipo_insight, temas, resumen, evidencia_clave, resultado_json
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id_actividad) DO NOTHING;
                    """,
                    (
                        id_actividad,
                        sent,
                        relev,
                        t_insight,
                        Json(temas_item),
                        resumen_ia,
                        evidencia_ia,
                        Json(
                            {
                                "sentimiento": sent,
                                "relevancia": relev,
                                "tipo_insight": t_insight,
                                "temas": temas_item,
                                "resumen": resumen_ia,
                                "cita_extraida": evidencia_ia,
                            }
                        ),
                    ),
                )

            # 3. Activos generados en estado 'borrador'
            activos_demo = [
                (
                    "LINKEDIN",
                    {
                        "titulo": "De la Comunidad al Mercado: El impacto de los proyectos prácticos de IA",
                        "copy": (
                            "¡Nada nos da más orgullo que ver a nuestros talentos conquistando el mercado de tecnología! 🚀\n\n"
                            "Nuestra estudiante Mariana Souza acaba de ser contratada como Desarrolladora Junior de IA "
                            "tras destacar sus proyectos prácticos desarrollados con LangChain y Oracle Cloud Infrastructure.\n\n"
                            "Historias como la de Mariana demuestran que construir soluciones reales es el mejor camino "
                            "para impulsar la carrera tech. ¡Felicitaciones, Mariana! 👏\n\n"
                            "#TalentosTech #InteligenciaArtificial #OracleCloud #CarreraDev"
                        ),
                        "canal_recomendado": "LinkedIn Oficial",
                        "potencial_engagement": "Alto",
                        "hashtags": [
                            "#TalentosTech",
                            "#InteligenciaArtificial",
                            "#OracleCloud",
                            "#CarreraDev",
                        ],
                    },
                ),
                (
                    "NEWSLETTER",
                    {
                        "seccion": "Logro de la Semana",
                        "titulo": "Estudiante consigue empleo Dev Jr de IA con portfolio en Oracle Cloud",
                        "titular": "Estudiante consigue empleo Dev Jr de IA con portfolio en Oracle Cloud",
                        "copy": (
                            "**Logro de la Semana**\n"
                            "Mariana Souza obtuvo su primera oportunidad como Desarrolladora Junior de IA destacando los "
                            "proyectos prácticos de LangChain y OCI construidos durante la formación en ONE.\n\n"
                            "**Tema en Tendencia**\n"
                            "La comunidad estuvo muy activa resolviendo dudas sobre arquitectura de agentes y nodos "
                            "condicionales con reintentos en LangGraph.\n\n"
                            "**Dato de la Comunidad**\n"
                            "Cerramos la semana con 14 interacciones clave y un sentimiento altamente positivo."
                        ),
                        "resumen": (
                            "Mariana Souza obtuvo su primera oportunidad como Dev Jr de IA destacando "
                            "proyectos desarrollados durante la formación."
                        ),
                    },
                ),
                (
                    "FAQ",
                    {
                        "titulo": "Tip Rápido: Cómo estructurar nodos condicionales y reintentos en LangGraph",
                        "tema": "Tip Rápido: Cómo estructurar nodos condicionales y reintentos en LangGraph",
                        "origen": "Duda frecuente planteada por Lucas Albuquerque en #dudas-langgraph",
                        "status": "borrador_para_curaduria",
                        "formato": "TIP",
                        "copy": (
                            "**Pregunta frecuente:** ¿Cómo estructurar un nodo condicional en LangGraph cuando la salida "
                            "del LLM falla la validación y necesita reintento?\n\n"
                            "**Solución recomendada:**\n"
                            "1. Define en el `State` un contador `retry_count: int` y `last_error: str | None`.\n"
                            "2. Crea una función router que evalúe si el JSON es válido; si falla y `retry_count < 3`, "
                            "redirige de vuelta al nodo generador inyectando el error en el prompt.\n"
                            "3. Registra la transición con `graph.add_conditional_edges('validador', router_fn, ...)`."
                        ),
                        "contenido_sugerido": (
                            "Usa `add_conditional_edges` junto con un contador `retry_count` en el estado del grafo "
                            "para reintentar llamadas al LLM hasta un límite seguro."
                        ),
                    },
                ),
            ]

            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'version_activo'
                );
                """
            )
            has_v2 = cur.fetchone()[0]

            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'almacenamiento_oci'
                      AND column_name = 'id_version'
                );
                """
            )
            has_v31_oci = cur.fetchone()[0]

            primer_id_version = None
            for tipo, contenido_json in activos_demo:
                cur.execute(
                    """
                    INSERT INTO activo_generado (id_lote, tipo_activo, contenido, estado_curaduria)
                    VALUES (%s, %s, %s, 'borrador')
                    ON CONFLICT (id_lote, tipo_activo) DO UPDATE SET actualizado_en = NOW()
                    RETURNING id_activo;
                    """,
                    (id_lote, tipo, Json(contenido_json)),
                )
                id_activo_ins = cur.fetchone()[0]

                if has_v2:
                    cur.execute(
                        """
                        INSERT INTO version_activo (
                            id_activo, numero_version, contenido, origen_version, motivo_cambio, creado_por
                        ) VALUES (%s, 1, %s, 'ia', 'Versión inicial generada por Gemini en n8n', 'n8n')
                        ON CONFLICT (id_activo, numero_version) DO UPDATE SET motivo_cambio = EXCLUDED.motivo_cambio
                        RETURNING id_version;
                        """,
                        (id_activo_ins, Json(contenido_json)),
                    )
                    id_ver = cur.fetchone()[0]
                    if primer_id_version is None:
                        primer_id_version = id_ver
                    cur.execute(
                        "UPDATE activo_generado SET id_version_actual = %s WHERE id_activo = %s;",
                        (id_ver, id_activo_ins),
                    )

            # 4. Registro de persistencia en OCI Object Storage (verificación previa SELECT, sin ON CONFLICT)
            ruta_seed = f"activos/2026-semana-04/lote-{id_lote}-paquete-distribucion.json"
            if has_v31_oci and primer_id_version is not None:
                cur.execute(
                    "SELECT id_almacenamiento FROM almacenamiento_oci WHERE id_version = %s LIMIT 1;",
                    (primer_id_version,),
                )
                if not cur.fetchone():
                    cur.execute(
                        """
                        INSERT INTO almacenamiento_oci (id_version, bucket, ruta_objeto, status)
                        VALUES (%s, %s, %s, 'guardado_con_exito');
                        """,
                        (primer_id_version, DEFAULT_OCI_BUCKET, ruta_seed),
                    )
            elif not has_v31_oci:
                cur.execute(
                    "SELECT id_almacenamiento FROM almacenamiento_oci WHERE id_lote = %s LIMIT 1;",
                    (id_lote,),
                )
                if not cur.fetchone():
                    cur.execute(
                        """
                        INSERT INTO almacenamiento_oci (id_lote, bucket, ruta_objeto, status)
                        VALUES (%s, %s, %s, 'guardado_con_exito');
                        """,
                        (id_lote, DEFAULT_OCI_BUCKET, ruta_seed),
                    )
        conn.commit()


def resetear_activos_a_borrador():
    """Devuelve todos los activos existentes al estado 'borrador' para repetir demos."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE activo_generado
                SET estado_curaduria = 'borrador',
                    revisado_en = NULL,
                    actualizado_en = NOW();
                """
            )
        conn.commit()


def migrar_esquema_v2():
    """
    Aplica de forma idempotente las tablas y columnas requeridas por los workflows de n8n
    (`version_activo`, `estado_procesamiento` en `actividad`, `ventana_desde`/`ventana_hasta` en `lote_procesamiento`).
    """
    sql_migration = """
    ALTER TABLE lote_procesamiento ADD COLUMN IF NOT EXISTS ventana_desde TIMESTAMPTZ;
    ALTER TABLE lote_procesamiento ADD COLUMN IF NOT EXISTS ventana_hasta TIMESTAMPTZ;
    ALTER TABLE lote_procesamiento ADD COLUMN IF NOT EXISTS tipo_operacion VARCHAR(30) NOT NULL DEFAULT 'procesamiento';
    ALTER TABLE lote_procesamiento ADD COLUMN IF NOT EXISTS clave_idempotencia TEXT;

    ALTER TABLE actividad ADD COLUMN IF NOT EXISTS estado_procesamiento VARCHAR(30) NOT NULL DEFAULT 'pendiente';

    CREATE TABLE IF NOT EXISTS version_activo (
        id_version       BIGSERIAL PRIMARY KEY,
        id_activo        BIGINT NOT NULL REFERENCES activo_generado (id_activo) ON DELETE CASCADE ON UPDATE CASCADE,
        numero_version   INTEGER NOT NULL CHECK (numero_version >= 1),
        contenido        JSONB NOT NULL,
        origen_version   VARCHAR(20) NOT NULL CHECK (origen_version IN ('ia', 'usuario')),
        motivo_cambio    TEXT,
        creado_por       VARCHAR(150),
        creado_en        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_activo_numero_version UNIQUE (id_activo, numero_version)
    );

    ALTER TABLE activo_generado ADD COLUMN IF NOT EXISTS id_version_actual BIGINT REFERENCES version_activo (id_version) ON DELETE SET NULL ON UPDATE CASCADE;
    ALTER TABLE activo_generado ADD COLUMN IF NOT EXISTS id_version_aprobada BIGINT REFERENCES version_activo (id_version) ON DELETE SET NULL ON UPDATE CASCADE;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_migration)
        conn.commit()


# ==============================================================================
# 6. HEADER PRINCIPAL Y SIDEBAR
# ==============================================================================
st.markdown(
    """
    <div class="main-header">
        <div class="oci-badge">☁️ Oracle Cloud Always Free · OCI Object Storage</div>
        <h1>🚀 CommunityLab: Motor de Curaduría y Distribución de Activos</h1>
        <p>Panel Inteligente Human-in-the-Loop · Transformación de Actividad Orgánica en Activos de Marketing (Grupo 10 · Equipo 43)</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### 🔌 Estado del Sistema")
    db_ok, has_v2_schema, has_v31_oci, schema_label, db_err = check_db_status()
    if db_ok:
        st.success("PostgreSQL (Supabase): Conectado")
        st.caption(
            f"Host: `{DB_CONFIG['host']}`\n\n"
            f"Esquema BD: `{schema_label}`"
        )
    else:
        st.error("Error de conexión a Supabase")
        st.caption(db_err)

    if st.button("🔄 Actualizar Panel", use_container_width=True):
        st.rerun()

    st.divider()
    with st.expander("🛠️ Herramientas de Demo / BD", expanded=True):
        st.caption("Utilidades rápidas para pruebas y demostración en vivo:")
        if st.button("🌱 Poblar Lote Demo (Seed)", use_container_width=True):
            try:
                seed_datos_demo()
                st.toast("Lote, análisis Gemini y activos creados con éxito.", icon="✅")
                st.rerun()
            except Exception as e:
                st.error(f"Error al insertar datos demo: {e}")

        if st.button("♻️ Resetear Activos a Borrador", use_container_width=True):
            try:
                resetear_activos_a_borrador()
                st.toast("Todos los activos volvieron a estado 'borrador'.", icon="🔄")
                st.rerun()
            except Exception as e:
                st.error(f"Error al resetear activos: {e}")

        if not has_v2_schema and db_ok:
            if st.button("⬆️ Habilitar Tablas v2/v3 (n8n)", use_container_width=True):
                try:
                    migrar_esquema_v2()
                    st.toast("Tablas de versionado y columnas para n8n habilitadas.", icon="🚀")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error en migración: {e}")

# ==============================================================================
# 7. PESTAÑAS PRINCIPALES
# ==============================================================================
tab_curaduria, tab_metricas, tab_oci = st.tabs(
    [
        "📋 Panel de Curaduría (Human-in-the-Loop)",
        "📊 Métricas y Salud de la Comunidad",
        "🪣 Persistencia en OCI Object Storage",
    ]
)

# ------------------------------------------------------------------------------
# PESTAÑA 1: PANEL DE CURADURÍA (HUMAN-IN-THE-LOOP)
# ------------------------------------------------------------------------------
with tab_curaduria:
    st.subheader("📋 Bandeja de Curaduría de Activos Generados por IA")
    st.caption(
        "Revisa, edita el título y copy persuasivo de cada activo en estado `borrador`, "
        "y aprueba su publicación o recházalo."
    )

    try:
        lotes_activos_rows = fetch_lotes_con_activos()
    except Exception:
        lotes_activos_rows = []

    lote_mas_reciente_id = (
        lotes_activos_rows[0]["id_lote"] if lotes_activos_rows else 30
    )
    opcion_lote_reciente = f"Lote más reciente (Lote #{lote_mas_reciente_id})"
    opcion_todos_lotes = "Mostrar todos los lotes (Histórico)"

    mapa_opciones_lote = {
        opcion_lote_reciente: lote_mas_reciente_id,
        opcion_todos_lotes: None,
    }
    for row_l in lotes_activos_rows:
        lid = row_l["id_lote"]
        if lid != lote_mas_reciente_id:
            per = row_l.get("periodo_referencia") or "Sin período"
            label_lote = f"Lote #{lid} · {per}"
            mapa_opciones_lote[label_lote] = lid

    col_filter_lote, col_filter_estado = st.columns([2, 1])
    with col_filter_lote:
        seleccion_lote_label = st.selectbox(
            "Filtrar activos por Lote de Procesamiento:",
            options=list(mapa_opciones_lote.keys()),
            index=0,
        )
    with col_filter_estado:
        filtro_estado = st.selectbox(
            "Filtrar por estado de curaduría:",
            options=["borrador", "aprobado", "rechazado", "TODOS"],
            index=0,
        )

    id_lote_seleccionado = mapa_opciones_lote.get(seleccion_lote_label)

    try:
        activos = fetch_activos(
            estado_filtro=filtro_estado,
            id_lote_filtro=id_lote_seleccionado,
        )
    except Exception as exc:
        st.error(f"No se pudo consultar la tabla `activo_generado`: {exc}")
        activos = []

    if not activos:
        lote_msg = (
            f"en el **Lote #{id_lote_seleccionado}**"
            if id_lote_seleccionado is not None
            else "en el **histórico de lotes**"
        )
        st.info(
            f"No hay activos en estado **'{filtro_estado}'** {lote_msg}. "
            "Puedes cambiar el filtro de lote a **'Mostrar todos los lotes (Histórico)'**, "
            "cambiar el estado a **'aprobado' / 'TODOS'**, o pulsar **'🌱 Poblar Lote Demo (Seed)'** en el panel lateral."
        )
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Activos Mostrados", len(activos))
        c2.metric(
            "💼 LinkedIn",
            sum(1 for a in activos if a.get("tipo_activo") == "LINKEDIN"),
        )
        c3.metric(
            "📰 Newsletter",
            sum(1 for a in activos if a.get("tipo_activo") == "NEWSLETTER"),
        )
        c4.metric(
            "💡 FAQ / Tips",
            sum(1 for a in activos if a.get("tipo_activo") == "FAQ"),
        )

        st.markdown("---")

        iconos_tipo = {
            "LINKEDIN": "💼 LINKEDIN",
            "NEWSLETTER": "📰 NEWSLETTER",
            "FAQ": "💡 FAQ",
        }

        for activo in activos:
            id_activo = activo["id_activo"]
            id_lote = activo["id_lote"]
            tipo = activo["tipo_activo"]
            estado = activo["estado_curaduria"]
            periodo = activo.get("periodo_referencia") or f"Lote #{id_lote}"
            comunidad = activo.get("origen_comunidad") or "Discord_Grupo_ONE_G10"
            contenido_raw = activo["contenido"] or {}
            if isinstance(contenido_raw, str):
                try:
                    contenido_raw = json.loads(contenido_raw)
                except Exception:
                    contenido_raw = {"copy": contenido_raw}

            # Extraer datos de contexto disponibles: Autor original de Discord, Canal y Lote asociado
            origen_inter = (
                contenido_raw.get("origen_interacciones")
                if isinstance(contenido_raw, dict)
                else None
            )
            autor_fallback = (
                ", ".join(str(x) for x in origen_inter if x)
                if isinstance(origen_inter, list) and origen_inter
                else (str(origen_inter) if origen_inter else None)
            )
            autor_original = (
                activo.get("autor_discord")
                or autor_fallback
                or (contenido_raw.get("autor") if isinstance(contenido_raw, dict) else None)
                or "Miembro de la Comunidad"
            )
            canal_original = (
                activo.get("canal_discord")
                or (contenido_raw.get("canal_origen") if isinstance(contenido_raw, dict) else None)
                or "#general"
            )

            titulo_actual, copy_actual = extract_titulo_y_copy(tipo, contenido_raw)

            header_expander = (
                f"{iconos_tipo.get(tipo, tipo)}  |  {titulo_actual}  "
                f"·  [{estado.upper()}]  ·  (Activo #{id_activo} · Lote #{id_lote})"
            )

            with st.expander(header_expander, expanded=(estado == "borrador")):
                meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)
                meta_col1.markdown(f"**👤 Autor original (Discord):** `{autor_original}`")
                meta_col2.markdown(f"**💬 Canal Discord:** `{canal_original}`")
                meta_col3.markdown(f"**📦 Lote asociado:** `Lote #{id_lote}` (`{periodo}`)")
                meta_col4.markdown(f"**🎯 Tipo / Comunidad:** `{tipo}` · `{comunidad}`")

                extras = []
                if isinstance(contenido_raw, dict):
                    if contenido_raw.get("canal_recomendado"):
                        extras.append(
                            f"📢 **Canal de Distribución:** {contenido_raw['canal_recomendado']}"
                        )
                    if contenido_raw.get("potencial_engagement"):
                        extras.append(
                            f"🔥 **Engagement estimado:** {contenido_raw['potencial_engagement']}"
                        )
                    if contenido_raw.get("origen"):
                        extras.append(f"💬 **Detalle Origen:** {contenido_raw['origen']}")
                    if contenido_raw.get("hashtags") and isinstance(
                        contenido_raw["hashtags"], list
                    ):
                        extras.append(
                            "🏷️ **Hashtags:** " + " ".join(contenido_raw["hashtags"])
                        )
                if extras:
                    st.markdown(" · ".join(extras))

                nuevo_titulo = st.text_area(
                    "✏️ Título / Titular del Activo",
                    value=titulo_actual,
                    height=68,
                    key=f"titulo_{id_activo}",
                )

                nuevo_copy = st.text_area(
                    "📝 Copy / Contenido para Distribución",
                    value=copy_actual,
                    height=220,
                    key=f"copy_{id_activo}",
                )

                comentario_curador = st.text_input(
                    "💬 Nota de curaduría (opcional)",
                    value=activo.get("comentario_curaduria") or "",
                    placeholder="Ej.: Ajustado tono de marca y llamado a la acción...",
                    key=f"comentario_{id_activo}",
                )

                btn_col1, btn_col2, btn_col3 = st.columns([2, 2, 4])

                with btn_col1:
                    if st.button(
                        "✅ Aprobar para Publicación",
                        key=f"aprobar_{id_activo}",
                        type="primary",
                        use_container_width=True,
                    ):
                        try:
                            actualizar_estado_activo(
                                id_activo=id_activo,
                                tipo_activo=tipo,
                                contenido_original=contenido_raw,
                                nuevo_titulo=nuevo_titulo.strip(),
                                nuevo_copy=nuevo_copy.strip(),
                                nuevo_estado="aprobado",
                                comentario=comentario_curador.strip(),
                            )
                            st.toast(
                                f"Activo #{id_activo} ({tipo}) aprobado y registrado para OCI.",
                                icon="✅",
                            )
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Error al aprobar el activo #{id_activo}: {exc}")

                with btn_col2:
                    if st.button(
                        "❌ Rechazar",
                        key=f"rechazar_{id_activo}",
                        use_container_width=True,
                    ):
                        try:
                            actualizar_estado_activo(
                                id_activo=id_activo,
                                tipo_activo=tipo,
                                contenido_original=contenido_raw,
                                nuevo_titulo=nuevo_titulo.strip(),
                                nuevo_copy=nuevo_copy.strip(),
                                nuevo_estado="rechazado",
                                comentario=comentario_curador.strip(),
                            )
                            st.toast(
                                f"Activo #{id_activo} ({tipo}) marcado como rechazado.",
                                icon="❌",
                            )
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Error al rechazar el activo #{id_activo}: {exc}")

                with btn_col3:
                    with st.popover("🔍 Ver JSONB completo del activo"):
                        st.json(
                            build_updated_contenido(
                                tipo,
                                contenido_raw,
                                nuevo_titulo.strip(),
                                nuevo_copy.strip(),
                            )
                        )

# ------------------------------------------------------------------------------
# PESTAÑA 2: MÉTRICAS Y SALUD DE LA COMUNIDAD
# ------------------------------------------------------------------------------
with tab_metricas:
    st.subheader("📊 Métricas y Salud de la Comunidad")
    st.caption(
        "Monitoreo continuo de lotes procesados (`lote_procesamiento`), volumen de interacciones, "
        "sentimiento predominante y evaluación de relevancia/puntaje realizada por Gemini."
    )

    try:
        lotes = fetch_lotes_procesamiento()
    except Exception as exc:
        st.error(f"No se pudo consultar la tabla `lote_procesamiento`: {exc}")
        lotes = []

    if not lotes:
        st.info(
            "Aún no hay registros en `lote_procesamiento`. "
            "Usa el botón **'🌱 Poblar Lote Demo (Seed)'** en la barra lateral o ejecuta el pipeline en n8n."
        )
    else:
        opciones_lote = {
            f"Lote #{l['id_lote']} · {l.get('periodo_referencia', 'Sin período')} ({l.get('estado', '')})": l
            for l in lotes
        }
        lote_seleccionado_label = st.selectbox(
            "Seleccionar lote de procesamiento para inspeccionar:",
            options=list(opciones_lote.keys()),
            index=0,
        )
        lote_actual = opciones_lote[lote_seleccionado_label]

        total_interacciones_lote = lote_actual.get("total_interacciones") or 0
        sentimiento_lote = (
            lote_actual.get("sentimiento_predominante") or "No determinado"
        )
        estado_lote = (lote_actual.get("estado") or "recibido").upper()
        total_interacciones_global = sum(
            (l.get("total_interacciones") or 0) for l in lotes
        )

        # KPIs con st.metric
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric(
            label="💬 Total de Interacciones (Lote)",
            value=total_interacciones_lote,
            delta=f"{total_interacciones_global} acumuladas en {len(lotes)} lote(s)",
        )
        kpi2.metric(
            label="❤️ Sentimiento Predominante",
            value=sentimiento_lote,
        )
        kpi3.metric(
            label="⚙️ Estado del Lote",
            value=estado_lote,
        )
        kpi4.metric(
            label="🏘️ Comunidad Origen",
            value=lote_actual.get("origen_comunidad") or "Discord_Grupo_ONE_G10",
        )

        st.markdown("#### 🏷️ Temas Principales Detectados en el Lote")
        temas_raw = lote_actual.get("temas_principales") or []
        if isinstance(temas_raw, str):
            try:
                temas_raw = json.loads(temas_raw)
            except Exception:
                temas_raw = [temas_raw]

        if temas_raw and isinstance(temas_raw, list):
            badges_html = "".join(
                f'<span class="topic-badge"># {tema}</span>' for tema in temas_raw
            )
            st.markdown(badges_html, unsafe_allow_html=True)

            with st.expander("📋 Ver lista detallada de temas del lote"):
                for idx, tema in enumerate(temas_raw, start=1):
                    st.markdown(f"{idx}. **{tema}**")
        else:
            st.caption("Este lote no registra temas principales consolidados aún.")

        # Sección de comentarios/interacciones evaluadas y puntuadas por Gemini
        st.markdown("---")
        st.markdown(
            "#### 🤖 Evaluación de Interacciones y Puntaje de Relevancia (Gemini LLM)"
        )
        try:
            interacciones_evaluadas = fetch_analisis_interacciones(
                id_lote=lote_actual["id_lote"]
            )
            if not interacciones_evaluadas:
                interacciones_evaluadas = fetch_analisis_interacciones(id_lote=None)
        except Exception:
            interacciones_evaluadas = []

        if interacciones_evaluadas:
            df_inter = pd.DataFrame(interacciones_evaluadas)
            cols_inter = [
                c
                for c in [
                    "id_actividad",
                    "autor",
                    "canal",
                    "tipo_insight",
                    "sentimiento",
                    "relevancia",
                    "resumen",
                    "comentario",
                ]
                if c in df_inter.columns
            ]
            st.dataframe(
                df_inter[cols_inter],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption(
                "Aún no hay interacciones analizadas en las tablas `actividad` / `analisis`."
            )

        st.markdown("---")
        st.markdown("#### 🗂️ Historial de Lotes Procesados (`lote_procesamiento`)")
        df_lotes = pd.DataFrame(lotes)
        if not df_lotes.empty:
            columnas_visibles = [
                col
                for col in [
                    "id_lote",
                    "origen_comunidad",
                    "periodo_referencia",
                    "estado",
                    "total_interacciones",
                    "sentimiento_predominante",
                    "temas_principales",
                    "creado_en",
                    "finalizado_en",
                ]
                if col in df_lotes.columns
            ]
            st.dataframe(
                df_lotes[columnas_visibles],
                use_container_width=True,
                hide_index=True,
            )

# ------------------------------------------------------------------------------
# PESTAÑA 3: PERSISTENCIA EN OCI OBJECT STORAGE
# ------------------------------------------------------------------------------
with tab_oci:
    st.subheader("🪣 Persistencia en OCI Object Storage (Capa Always Free)")
    st.caption(
        "Verificación y trazabilidad en vivo de los paquetes JSON de distribución respaldados en "
        "Oracle Cloud Infrastructure Object Storage (`almacenamiento_oci`)."
    )

    # Datos oficiales verificados en OCI Console
    DEFAULT_OCI_BUCKET = "communitylab-activos-marketing"
    OCI_NAMESPACE = "grhxfjzkgrnw"
    OCI_REGION = "sa-saopaulo-1"

    try:
        registros_oci = fetch_almacenamiento_oci() or []
    except Exception:
        registros_oci = []

    try:
        paquetes_guardados_count = fetch_count_guardados_oci()
    except Exception:
        paquetes_guardados_count = len(
            [r for r in registros_oci if r.get("status") == "guardado_con_exito"]
        )

    ultimo_path = (
        registros_oci[0].get("ruta_objeto")
        if registros_oci
        and isinstance(registros_oci[0], dict)
        and registros_oci[0].get("ruta_objeto")
        else "Sin paquetes registrados aún"
    )
    ultimo_status = (
        registros_oci[0].get("status")
        if registros_oci
        and isinstance(registros_oci[0], dict)
        and registros_oci[0].get("status")
        else "sin_registros"
    )

    oci_col1, oci_col2, oci_col3 = st.columns(3)
    oci_col1.metric("🪣 Bucket OCI Configurado", DEFAULT_OCI_BUCKET)
    oci_col2.metric("📦 Paquetes Guardados con Éxito", paquetes_guardados_count)
    oci_col3.metric("☁️ Último Estado OCI", ultimo_status)

    st.markdown(
        f"""
        <div class="oci-card">
            <div style="font-size:0.85rem; color:#94a3b8; text-transform:uppercase; font-weight:700;">
                Oracle Cloud Infrastructure · Object Storage (Always Free)
            </div>
            <div style="margin-top:0.5rem;">
                <strong>Bucket Principal:</strong> <span class="oci-code">{DEFAULT_OCI_BUCKET}</span>
            </div>
            <div style="margin-top:0.4rem;">
                <strong>Namespace OCI:</strong> <span class="oci-code">{OCI_NAMESPACE}</span>
            </div>
            <div style="margin-top:0.4rem;">
                <strong>Región:</strong> <span class="oci-code">{OCI_REGION}</span>
            </div>
            <div style="margin-top:0.4rem;">
                <strong>Último Path del Paquete JSON:</strong> <span class="oci-code">{ultimo_path}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not registros_oci:
        st.info(
            f"ℹ️ Aún no hay paquetes registrados en la tabla `almacenamiento_oci`. "
            f"Cuando apruebes un activo en el Panel de Curaduría, el flujo de persistencia en n8n "
            f"lo respaldará automáticamente en el bucket `{DEFAULT_OCI_BUCKET}` (`{OCI_REGION}`)."
        )
    else:
        st.markdown("#### 📊 Tabla de Paquetes Respaldados en `almacenamiento_oci`")
        filas_tabla_oci = [
            {
                "id_almacenamiento": reg.get("id_almacenamiento"),
                "bucket": reg.get("bucket") or DEFAULT_OCI_BUCKET,
                "ruta_objeto": reg.get("ruta_objeto"),
                "status": reg.get("status"),
                "fecha_guardado": reg.get("fecha_guardado")
                or reg.get("actualizado_en")
                or reg.get("creado_en"),
            }
            for reg in registros_oci
        ]
        df_oci_resumen = pd.DataFrame(filas_tabla_oci)
        st.dataframe(df_oci_resumen, use_container_width=True, hide_index=True)

        st.markdown("#### 📦 Detalle Expandible de Paquetes Respaldados")
        for idx, reg in enumerate(registros_oci):
            id_alm = reg.get("id_almacenamiento", 1)
            bucket_db = reg.get("bucket") or DEFAULT_OCI_BUCKET
            ruta_db = reg.get("ruta_objeto") or "N/A"
            status_db = reg.get("status") or "pendiente"
            fecha_guardado = (
                reg.get("fecha_guardado")
                or reg.get("actualizado_en")
                or reg.get("creado_en")
                or "Reciente"
            )

            icono_status = (
                "🟢"
                if status_db == "guardado_con_exito"
                else ("🟡" if status_db in ("pendiente", "procesando") else "🔴")
            )

            with st.expander(
                f"{icono_status} Paquete #{id_alm} · Bucket: {bucket_db} · Status: {status_db} · Path: {ruta_db}",
                expanded=(idx < 3),
            ):
                c_b1, c_b2, c_b3 = st.columns(3)
                c_b1.markdown(
                    f"**🆔 ID Almacenamiento:** `#{id_alm}`\n\n"
                    f"**🪣 Bucket:** `{bucket_db}`"
                )
                c_b2.markdown(
                    f"**📂 Ruta del Objeto (`ruta_objeto`):**\n`{ruta_db}`"
                )
                c_b3.markdown(
                    f"**📌 Status:** `{status_db}`\n\n"
                    f"**🕒 Fecha de Guardado:** `{fecha_guardado}`"
                )

                if reg.get("detalle_error"):
                    st.warning(f"Detalle registrado: {reg['detalle_error']}")

                st.code(
                    f"oci://{bucket_db}@{OCI_NAMESPACE}/{ruta_db}",
                    language="bash",
                )
