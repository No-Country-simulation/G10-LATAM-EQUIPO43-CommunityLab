from langgraph.graph import END, START, StateGraph

from .models import Estado
from .nodes import (
    analizar_interacciones,
    generar_caso_exito,
    generar_faq,
    consolidar,
)
from .router import decidir_contenido


def construir_grafo():

    grafo = StateGraph(Estado)

    grafo.add_node(
        "analizar",
        analizar_interacciones
    )

    grafo.add_node(
        "caso_exito",
        generar_caso_exito
    )

    grafo.add_node(
        "faq",
        generar_faq
    )

    grafo.add_node(
        "consolidar",
        consolidar
    )

    grafo.add_edge(
        START,
        "analizar"
    )

    grafo.add_conditional_edges(
        "analizar",
        decidir_contenido,
        [
            "caso_exito",
            "faq",
            "consolidar",
        ],
    )

    grafo.add_edge(
        "caso_exito",
        "consolidar"
    )

    grafo.add_edge(
        "faq",
        "consolidar"
    )

    grafo.add_edge(
        "consolidar",
        END
    )

    return grafo.compile()