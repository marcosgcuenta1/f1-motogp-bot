"""Utilidad para averiguar tu TELEGRAM_CHAT_ID.

Uso:
  1) Abre Telegram y envía cualquier mensaje (p. ej. "hola") a tu bot.
  2) Ejecuta:  python get_chat_id.py <TOKEN>
     (o define TELEGRAM_BOT_TOKEN en el entorno y ejecútalo sin argumentos)
  3) Copia el "chat id" que imprime y guárdalo como secreto TELEGRAM_CHAT_ID.
"""
from __future__ import annotations

import os
import sys

import requests


def main() -> int:
    token = (sys.argv[1] if len(sys.argv) > 1 else None) or os.environ.get(
        "TELEGRAM_BOT_TOKEN"
    )
    if not token:
        print("Falta el token. Uso: python get_chat_id.py <TOKEN>")
        return 1

    resp = requests.get(
        f"https://api.telegram.org/bot{token}/getUpdates", timeout=30
    )
    resp.raise_for_status()
    updates = resp.json().get("result", [])

    if not updates:
        print(
            "No hay mensajes recientes. Envía un mensaje a tu bot desde "
            "Telegram y vuelve a ejecutar este script."
        )
        return 0

    seen: set[str] = set()
    for update in updates:
        chat = (update.get("message") or update.get("channel_post") or {}).get("chat")
        if not chat:
            continue
        chat_id = str(chat.get("id"))
        if chat_id in seen:
            continue
        seen.add(chat_id)
        nombre = chat.get("title") or chat.get("username") or chat.get("first_name", "")
        print(f"chat id: {chat_id}   ({chat.get('type')}: {nombre})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
