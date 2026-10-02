from langchain_openai import ChatOpenAI

from .config import LLM_BASE_URL, LLM_MODEL


def get_llm(temperature: float = 0.4):
    """Crea una conexión con el modelo local."""

    return ChatOpenAI(
        model=LLM_MODEL,
        temperature=temperature,
        base_url=LLM_BASE_URL,
        api_key="lm-studio",
    )