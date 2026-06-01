"""Envía el resumen de horarios del fin de semana (job de los jueves).

Variables de entorno necesarias:
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID
"""
from __future__ import annotations

import datetime as dt
import os
import sys

from bot.messages import build_weekend_summary, upcoming_weekend
from bot.sources import MADRID, get_all_sessions
from bot.telegram_client import send_message


def main() -> int:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    now_madrid = dt.datetime.now(MADRID)
    start, end = upcoming_weekend(now_madrid)
    years = sorted({start.year, end.year})

    sessions = get_all_sessions(years)
    message = build_weekend_summary(sessions, start, end)

    if message is None:
        print(f"Sin F1 ni MotoGP entre {start:%Y-%m-%d} y {end:%Y-%m-%d}. No se envía nada.")
        return 0

    send_message(token, chat_id, message)
    print("Resumen del fin de semana enviado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
