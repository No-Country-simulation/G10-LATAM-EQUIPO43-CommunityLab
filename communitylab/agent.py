import json
import sys

from .graph import construir_grafo


def procesar(payload: dict) -> dict:

    grafo = construir_grafo()

    resultado = grafo.invoke({
        "origen": payload["origen_comunidad"],
        "periodo": payload["periodo_referencia"],
        "interacciones": payload["interacciones"],
    })

    return resultado["paquete"]


if __name__ == "__main__":

    ruta = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "data/sample_input.json"
    )

    with open(ruta, encoding="utf-8") as archivo:
        payload = json.load(archivo)

    resultado = procesar(payload)

    print(
        json.dumps(
            resultado,
            ensure_ascii=False,
            indent=2
        )
    )