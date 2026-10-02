import os
from dotenv import load_dotenv

load_dotenv()

LLM_BASE_URL = "http://localhost:1234/v1"
LLM_MODEL = os.getenv(
    "LM_STUDIO_MODEL",
    "google/gemma-4-e4b"
)