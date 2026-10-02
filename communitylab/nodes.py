from collections import Counter

from .llm import get_llm
from .models import (
    Estado,
    ListaAnalisis,
    PostLinkedIn,
    Newsletter,
    FAQ,
)
from .prompts import (
    SYS_ANALISIS,
    SYS_LINKEDIN,
    SYS_FAQ,
)


def preparar_interacciones(interacciones: list[dict]) -> str:
    mensajes = []

    for indice, interaccion in enumerate(interacciones):
        mensajes.append(
            f"[{indice}] "
            f"autor={interaccion['autor']} "
            f"canal={interaccion['canal']} "
            f"tipo={interaccion.get('tipo', '')}: "
            f"{interaccion['texto']}"
        )

    return "\n".join(mensajes)


def obtener_interaccion_mas_relevante(
    state: Estado,
    categoria: str
):
    candidatos = [
        analisis
        for analisis in state["analisis"]
        if analisis["categoria"] == categoria
    ]

    seleccionado = max(
        candidatos,
        key=lambda item: item["relevancia"]
    )

    interaccion = state["interacciones"][
        seleccionado["indice"]
    ]

    return seleccionado, interaccion


def analizar_interacciones(state: Estado) -> Estado:
    texto = preparar_interacciones(
        state["interacciones"]
    )

    resultado = get_llm(0).with_structured_output(
        ListaAnalisis
    ).invoke([
        ("system", SYS_ANALISIS),
        ("human", texto),
    ])

    analisis = [
        item.model_dump()
        for item in resultado.items
    ]

    conteo = Counter(
        item["sentimiento"]
        for item in analisis
    )

    total = max(len(analisis), 1)

    positivos = conteo["positivo"] / total
    negativos = conteo["negativo"] / total

    if positivos >= 0.7:
        sentimiento = "Altamente Positivo"
    elif positivos > negativos:
        sentimiento = "Positivo"
    elif negativos > positivos:
        sentimiento = "Con Dificultades"
    else:
        sentimiento = "Neutro"

    temas = [
        item["tema"]
        for item in sorted(
            analisis,
            key=lambda item: -item["relevancia"]
        )
    ][:5]

    return {
        "analisis": analisis,
        "resumen": {
            "total_interacciones_procesadas": len(
                state["interacciones"]
            ),
            "sentimiento_predominante": sentimiento,
            "temas_principales": temas,
        },
    }

def generar_caso_exito(state: Estado) -> Estado:
    """Genera contenido para una historia de éxito."""

    _, interaccion = obtener_interaccion_mas_relevante(
        state,
        "historia_exito"
    )

    prompt = (
        f"Autor: {interaccion['autor']}\n"
        f"Mensaje original: {interaccion['texto']}"
    )

    llm = get_llm(0.7)

    # Generamos publicación para LinkedIn.
    post = llm.with_structured_output(
        PostLinkedIn
    ).invoke(
        [
            ("system", SYS_LINKEDIN),
            ("human", prompt),
        ]
    )

    # Generamos destaque para el newsletter.
    newsletter = llm.with_structured_output(
        Newsletter
    ).invoke(
        [
            (
                "system",
                """
                Redacta un destaque breve para el newsletter semanal.

                Sección:
                'Logro de la Semana'

                Escribe en español.
                No inventes información.
                """
            ),
            ("human", prompt),
        ]
    )

    return {
        "post_linkedin": post.model_dump(),
        "newsletter": newsletter.model_dump(),
    }


def generar_faq(state: Estado) -> Estado:
    """Genera una FAQ a partir de una duda técnica."""

    _, interaccion = obtener_interaccion_mas_relevante(
        state,
        "duda_tecnica"
    )

    prompt = (
        f"Duda de {interaccion['autor']} "
        f"en el canal {interaccion['canal']}:\n"
        f"{interaccion['texto']}"
    )

    resultado = get_llm(0.4).with_structured_output(
        FAQ
    ).invoke(
        [
            ("system", SYS_FAQ),
            ("human", prompt),
        ]
    )

    faq = resultado.model_dump()

    faq["origen"] = (
        f"Duda planteada por {interaccion['autor']} "
        f"en el canal {interaccion['canal']}"
    )

    faq["status"] = "derivado_a_mentoria"

    return {
        "faq": faq
    }

def consolidar(state: Estado) -> Estado:
    """Construye el resultado final del agente."""

    activos = {}

    # Publicación de LinkedIn.
    if state.get("post_linkedin"):
        post = state["post_linkedin"]

        activos["post_linkedin"] = {
            "titulo": post["titulo"],
            "copy": post["texto"],
            "canal_recomendado": "LinkedIn Oficial",
            "potencial_engagement": post[
                "potencial_engagement"
            ],
        }

    # Newsletter.
    if state.get("newsletter"):
        activos[
            "destaque_newsletter_semanal"
        ] = state["newsletter"]

    # FAQ.
    if state.get("faq"):
        faq = state["faq"]

        activos["sugerencia_contenido_faq"] = {
            "tema": faq["tema"],
            "explicacion": faq["explicacion"],
            "origen": faq["origen"],
            "status": faq["status"],
        }

    return {
        "paquete": {
            "status": "exito",
            "resumen_comunidad": state["resumen"],
            "analisis_detallado": state["analisis"],
            "activos_distribucion_generados": activos,
        }
    }
