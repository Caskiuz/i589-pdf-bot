"""Cliente de la API de DeepSeek (compatible con OpenAI SDK)."""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"


class DeepSeekConfigError(RuntimeError):
    """No hay API key configurada."""


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not key:
        raise DeepSeekConfigError(
            "Falta DEEPSEEK_API_KEY. Crea el archivo .env con tu key de DeepSeek "
            "(https://platform.deepseek.com) o usa el modo sin IA."
        )
    return OpenAI(api_key=key, base_url=BASE_URL)


def get_model() -> str:
    return os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def ai_available() -> bool:
    return bool(os.getenv("DEEPSEEK_APIKEY", "").strip() or os.getenv("DEEPSEEK_API_KEY", "").strip())
