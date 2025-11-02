from dataclasses import dataclass
import time
from typing import Dict, List, Tuple

import requests

from config import config

OPENROUTER_API_URL = 'https://openrouter.ai/api/v1/chat/completions'


@dataclass
class OpenRouterError(Exception):
    status: int
    msg: str

    def __str__(self) -> str:
        return f'[{self.status}] {self.msg}'


def _friendly(status: int) -> str:
    dict_friendly = {
        400: 'Неверный формат запроса.',
        401: 'Ключ OpenRouter отклонен.',
        403: 'Нет прав доступа к модели.',
        404: 'Эндпоинт не найден. Проверьте URL api/v1/chat/completions.',
        429: 'Превышены лимиты бесплатной модели. Попробуйте позднее.',
        500: 'Непредвиденная ошибка на стороне OpenRouter. Попробуйте позднее.',
        502: 'Ошибка при пересылке запроса. Попробуйте позднее.',
        503: 'Сервис OpenRouter недоступен. Попробуйте позднее.',
        504: 'Истекло время ожидание ответа. Попробуйте позднее.'
    }

    return dict_friendly.get(status, 'Сервис недоступен. Повторите попытку позже.')


def chat_once(messages: List[Dict],
              *,
              model: str,
              temperature: float = 0.2,
              max_tokens: int = 400,
              timeout_s: int = 30
) -> Tuple[str, int]:
    if not config.openrouter_api_key:
        raise OpenRouterError(401, "Отсутствует OPENROUTER_API_KEY (.env).")

    headers = {
        "Authorization": f"Bearer {config.openrouter_api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    t0 = time.perf_counter()

    request = requests.post(
        OPENROUTER_API_URL,
        json=payload,
        headers=headers,
        timeout=timeout_s
    )

    dt_ms = int((time.perf_counter() - t0) * 1000)

    if request.status_code // 100 != 2:
        raise OpenRouterError(request.status_code, _friendly(request.status_code))

    try:
        data = request.json()
        text = data["choices"][0]["message"]["content"]

    except Exception:
        raise OpenRouterError(500, "Неожиданная структура ответа OpenRouter.")

    return text, dt_ms