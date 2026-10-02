from .models import Estado


def decidir_contenido(state: Estado) -> list[str]:
    categorias = {
        analisis["categoria"]
        for analisis in state["analisis"]
    }

    destinos = []

    if "historia_exito" in categorias:
        destinos.append("caso_exito")

    if "duda_tecnica" in categorias:
        destinos.append("faq")

    if not destinos:
        destinos.append("consolidar")

    return destinos
