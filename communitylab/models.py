from typing import Literal, TypedDict

from pydantic import BaseModel, Field


class AnalisisInteraccion(BaseModel):
    indice: int = Field(
        description="Posición (0-based) de la interacción"
    )
    autor: str
    sentimiento: Literal[
        "positivo",
        "neutro",
        "negativo"
    ]
    tema: str
    categoria: Literal[
        "historia_exito",
        "duda_tecnica",
        "feedback",
        "otro"
    ]
    relevancia: int = Field(
        description="Valor comunicacional de 0 a 10"
    )
    cita_destacada: str


class ListaAnalisis(BaseModel):
    items: list[AnalisisInteraccion]


class PostLinkedIn(BaseModel):
    titulo: str
    texto: str
    potencial_engagement: Literal[
        "Alto",
        "Medio",
        "Bajo"
    ]


class Newsletter(BaseModel):
    seccion: str
    titular: str
    resumen: str


class FAQ(BaseModel):
    tema: str
    explicacion: str


class Estado(TypedDict, total=False):
    origen: str
    periodo: str
    interacciones: list[dict]

    analisis: list[dict]
    resumen: dict

    post_linkedin: dict
    newsletter: dict
    faq: dict

    paquete: dict