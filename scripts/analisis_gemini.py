"""
CommunityLab — Análisis de sentimiento, tema y relevancia con Google Gemini
----------------------------------------------------------------------------
Lee el dataset completo de prueba, analiza cada interacción, y guarda:
  - data/resultados_analisis.json   (análisis por interacción)
  - imprime en consola el resumen de comunidad (sentimiento predominante,
    temas principales) que se usará luego para la Newsletter.

Requiere:
    pip install google-generativeai

Configura tu API key (Google AI Studio -> aistudio.google.com) antes de correr:
    export GEMINI_API_KEY="tu-api-key-aqui"
"""

import os
import json
import time
import collections
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH = os.path.join(BASE_DIR, "data", "dataset_prueba_interacciones.json")
SCHEMA_PATH = os.path.join(BASE_DIR, "prompts", "response_schema_analisis.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "resultados_analisis.json")

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
    RESPONSE_SCHEMA = json.load(f)

SYSTEM_PROMPT = """Eres un analista de comunidad digital para una plataforma
educativa de tecnología. Tu tarea es analizar mensajes de estudiantes
(testimonios, dudas técnicas, feedback) y clasificarlos según sentimiento,
tema y relevancia para marketing/contenido educativo.

Reglas importantes:
- Una pregunta técnica NO es negativa solo por tratar un problema; solo es
  "Frustración" si el tono expresa bloqueo, cansancio o queja explícita.
- El score_relevancia mide qué tan apto es el mensaje para convertirse en
  contenido (especificidad, carga emocional, valor educativo), no qué tan
  "importante" es el tema en sí.
- Si el mensaje es un saludo, pregunta administrativa o no aporta contenido
  analizable, usa tema_categoria "Otro" y tipo_insight "ninguno".

Ejemplos de referencia (few-shot):

Mensaje: "Conseguí trabajo como Dev Jr gracias al proyecto que hice en el curso!"
Salida: {"sentimiento": "Muy Positivo", "tema_categoria": "Logro Laboral",
"score_relevancia": 9, "tipo_insight": "testimonio",
"cita_extraida": "Conseguí trabajo como Dev Jr gracias al proyecto que hice en el curso",
"razon_relevancia": "Logro concreto, alta carga emocional, ideal para LinkedIn"}

Mensaje: "¿Alguien sabe por qué me da error 404 en el endpoint?"
Salida: {"sentimiento": "Neutral", "tema_categoria": "Duda Técnica",
"score_relevancia": 4, "tipo_insight": "duda_recurrente",
"cita_extraida": "", "razon_relevancia": "Pregunta puntual, poco valor de contenido por sí sola"}

Mensaje: "Ya llevo 3 días atascado con este bug y nadie responde, muy frustrante."
Salida: {"sentimiento": "Frustración", "tema_categoria": "Duda Técnica",
"score_relevancia": 3, "tipo_insight": "ninguno",
"cita_extraida": "", "razon_relevancia": "Frustración legítima, no apta para marketing, sí para seguimiento de soporte"}

Mensaje: "Buenos días a todos, ¿alguien sabe a qué hora es la reunión de hoy?"
Salida: {"sentimiento": "Neutral", "tema_categoria": "Otro",
"score_relevancia": 1, "tipo_insight": "ninguno",
"cita_extraida": "", "razon_relevancia": "Mensaje administrativo sin valor de contenido"}
"""

model = genai.GenerativeModel(
    model_name="gemini-3.8-flash",
    system_instruction=SYSTEM_PROMPT,
    generation_config={
        "temperature": 0.2,
        "response_mime_type": "application/json",
        "response_schema": RESPONSE_SCHEMA,
    },
)


def analizar_mensaje(texto: str, canal: str = "", intentos: int = 3) -> dict:
    prompt = f'Mensaje: "{texto}"\nCanal de origen: "{canal}"'
    for intento in range(1, intentos + 1):
        try:
            response = model.generate_content(prompt)
            return json.loads(response.text)
        except ResourceExhausted as e:
            espera = 20 * intento  # espera creciente: 20s, 40s, 60s
            print(f"  ⚠ Límite de cuota alcanzado, esperando {espera}s antes de reintentar ({intento}/{intentos})...")
            time.sleep(espera)
    raise RuntimeError("No se pudo completar el análisis tras varios reintentos por límite de cuota.")


def main():
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    resultados = []
    for i, interaccion in enumerate(dataset["interacciones"]):
        analisis = analizar_mensaje(interaccion["texto"], interaccion["canal"])
        resultado = {**interaccion, "analisis": analisis}
        resultados.append(resultado)
        print(f"✔ Analizado: {interaccion['autor']} — {analisis['sentimiento']} / {analisis['tema_categoria']} (score {analisis['score_relevancia']})")

        # Pausa preventiva: la capa gratuita permite 5 solicitudes/minuto.
        # Esperamos 13s entre llamadas (salvo la última) para no toparla.
        if i < len(dataset["interacciones"]) - 1:
            time.sleep(13)

    # --- Resumen agregado del lote (para la Newsletter) ---
    sentimientos = collections.Counter(r["analisis"]["sentimiento"] for r in resultados)
    temas = collections.Counter(r["analisis"]["tema_categoria"] for r in resultados)

    resumen_comunidad = {
        "total_interacciones_procesadas": len(resultados),
        "sentimiento_predominante": sentimientos.most_common(1)[0][0],
        "distribucion_sentimiento": dict(sentimientos),
        "temas_principales": [tema for tema, _ in temas.most_common(3)],
    }

    salida = {
        "origen_comunidad": dataset["origen_comunidad"],
        "periodo_referencia": dataset["periodo_referencia"],
        "resumen_comunidad": resumen_comunidad,
        "interacciones_analizadas": resultados,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)

    print("\n--- Resumen de comunidad ---")
    print(json.dumps(resumen_comunidad, indent=2, ensure_ascii=False))
    print(f"\nResultados guardados en: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
