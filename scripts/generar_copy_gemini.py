"""
CommunityLab — Generación de activos de marketing (LinkedIn + Newsletter) con Gemini
---------------------------------------------------------------------------------------
Lee data/resultados_analisis.json (generado por analisis_gemini.py) y produce:
  - Un post de LinkedIn, basado en el insight de mayor score_relevancia.
  - Un Resumen Semanal / Newsletter, basado en el resumen agregado del lote.
Guarda ambos en data/activos_generados.json

Requiere:
    pip install google-generativeai
    export GEMINI_API_KEY="tu-api-key-aqui"
"""

import os
import json
import time
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTADOS_PATH = os.path.join(BASE_DIR, "data", "resultados_analisis.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "activos_generados.json")

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

SYSTEM_PROMPT_LINKEDIN = """Eres el copywriter de una comunidad tech que celebra los
logros de sus estudiantes. A partir del insight que te entrego, escribe un post
para LinkedIn con tono inspirador y profesional, que celebre el logro y motive a
otros miembros de la comunidad a seguir esforzándose.

Reglas:
- Máximo 150 palabras.
- Incluye 2-3 hashtags relevantes al final.
- Usa el nombre del autor tal como viene en el dato.
- Si hay una cita textual extraída, intégrala naturalmente en el post.
- No inventes datos que no estén en el insight.

Responde solo con el texto del post, sin explicaciones adicionales."""

SYSTEM_PROMPT_NEWSLETTER = """Eres el editor de la newsletter semanal de una
comunidad educativa de tecnología. A partir del resumen consolidado del período,
escribe un Resumen Semanal con tono cercano y motivador, en 3 secciones cortas:
"Logro de la Semana", "Tema en Tendencia" y "Dato de la Comunidad".

Reglas:
- Máximo 200 palabras en total.
- No menciones quejas o frustraciones de forma negativa; reformúlalas como
  "temas en los que la comunidad está trabajando".
- No inventes cifras ni nombres que no vengan en los datos de entrada.

Responde solo con el texto del resumen, sin explicaciones adicionales."""

model_linkedin = genai.GenerativeModel(
    model_name="gemini-3.8-flash",
    system_instruction=SYSTEM_PROMPT_LINKEDIN,
    generation_config={"temperature": 0.7},
)

model_newsletter = genai.GenerativeModel(
    model_name="gemini-3.8-flash",
    system_instruction=SYSTEM_PROMPT_NEWSLETTER,
    generation_config={"temperature": 0.6},
)


def _generar_con_reintento(model_obj, entrada: str, intentos: int = 3) -> str:
    for intento in range(1, intentos + 1):
        try:
            response = model_obj.generate_content(entrada)
            return response.text.strip()
        except ResourceExhausted:
            espera = 20 * intento
            print(f"  ⚠ Límite de cuota alcanzado, esperando {espera}s antes de reintentar ({intento}/{intentos})...")
            time.sleep(espera)
    raise RuntimeError("No se pudo generar el copy tras varios reintentos por límite de cuota.")


def generar_post_linkedin(insight: dict) -> str:
    entrada = (
        f"Autor: {insight['autor']}\n"
        f"Insight (tema libre): {insight['analisis']['tema_libre']}\n"
        f"Cita destacada: {insight['analisis']['cita_extraida']}\n"
        f"Texto original: {insight['texto']}"
    )
    return _generar_con_reintento(model_linkedin, entrada)


def generar_newsletter(resumen_comunidad: dict, highlights: list) -> str:
    lista_highlights = "\n".join(
        f"- {h['autor']}: {h['analisis']['tema_libre']} (score {h['analisis']['score_relevancia']})"
        for h in highlights
    )
    entrada = (
        f"Sentimiento predominante del período: {resumen_comunidad['sentimiento_predominante']}\n"
        f"Temas principales: {', '.join(resumen_comunidad['temas_principales'])}\n"
        f"Highlights seleccionados:\n{lista_highlights}"
    )
    return _generar_con_reintento(model_newsletter, entrada)


def main():
    with open(RESULTADOS_PATH, "r", encoding="utf-8") as f:
        datos = json.load(f)

    interacciones = datos["interacciones_analizadas"]

    # El insight con mayor score, de tipo testimonio o logro, es el candidato a LinkedIn
    candidatos = [
        i for i in interacciones
        if i["analisis"]["tipo_insight"] in ("testimonio", "logro")
    ]
    mejor_insight = max(candidatos, key=lambda i: i["analisis"]["score_relevancia"])

    # Los 3 insights de mayor score (de cualquier tipo relevante) alimentan la newsletter
    relevantes = sorted(
        [i for i in interacciones if i["analisis"]["tipo_insight"] != "ninguno"],
        key=lambda i: i["analisis"]["score_relevancia"],
        reverse=True,
    )[:3]

    print(f"→ Generando post de LinkedIn para: {mejor_insight['autor']}")
    post_linkedin = generar_post_linkedin(mejor_insight)

    print("→ Generando Resumen Semanal / Newsletter...")
    newsletter = generar_newsletter(datos["resumen_comunidad"], relevantes)

    salida = {
        "periodo_referencia": datos["periodo_referencia"],
        "activos_distribucion_generados": {
            "post_linkedin": {
                "autor_destacado": mejor_insight["autor"],
                "copy": post_linkedin,
            },
            "resumen_newsletter": {
                "texto": newsletter,
            },
        },
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)

    print("\n--- POST LINKEDIN ---\n")
    print(post_linkedin)
    print("\n--- NEWSLETTER ---\n")
    print(newsletter)
    print(f"\nActivos guardados en: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
