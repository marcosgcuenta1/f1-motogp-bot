"""Cliente mínimo para enviar mensajes con la Bot API de Telegram."""
from __future__ import annotations

import html

import requests

_API = "https://api.telegram.org/bot{token}/sendMessage"
_TIMEOUT = 30


def escape(text: str) -> str:
    """Escapa texto dinámico para usarlo con parse_mode=HTML."""
    return html.escape(text or "")


def send_message(token: str, chat_id: str, text: str) -> dict:
    resp = requests.post(
        _API.format(token=token),
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()
