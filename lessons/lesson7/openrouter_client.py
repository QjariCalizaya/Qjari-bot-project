from dataclasses import dataclass
import time , os , requests, json, logging
from typing import Dict, List, Tuple

import requests

from config import config
from db import write_service_call
log = logging.getLogger(__name__)


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
        err = OpenRouterError(401, "Отсутствует OPENROUTER_API_KEY (.env).")
        log.error(err)
        raise err


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
    request_str = json.dumps(payload, ensure_ascii=False)
    log.debug(
        "Запрос к OpenRouter: model-%s , temperature= %s, max_tokens=%s",
        model,
        temperature,
        max_tokens
    )



    t0 = time.perf_counter()
    r = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=timeout_s)
    dt_ms = int((time.perf_counter() - t0) * 1000)

    if r.status_code // 100 != 2:
        raise OpenRouterError(r.status_code, _friendly(r.status_code))

    try:
        data = r.json()
        text = data["choices"][0]["message"]["content"]

        write_service_call(
            service = "openrouter",
            request = request_str,
            response = r.text,
            status_code = r.status_code,
            duration_ms = dt_ms,
            error=None if r.status_code // 100 != 2 else _friendly(r.status_code),
        )

    except Exception as e:
        log.error(e)
        write_service_call(
            service = "openrouter",
            request = request_str,
            response = None,
            status_code = None,
            duration_ms = None,
            error = e,
        )
        raise OpenRouterError(500, f"Ошибка при запросе: {e}")

    return text, dt_ms
