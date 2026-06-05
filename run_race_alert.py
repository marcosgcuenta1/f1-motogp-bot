"""Aviso '10 minutos antes' de cada CARRERA (job frecuente del fin de semana).

Recorre las sesiones de tipo 'race' (y 'sprint') y avisa cuando faltan ~10
minutos. Como GitHub Actions ejecuta el cron cada 5 minutos y puede tener
algo de retraso, se considera 'inminente' cualquier carrera que empiece
dentro de los próximos WINDOW_MIN minutos, y se deduplica con el estado en
disco para enviar el aviso una sola vez.

Variables de entorno necesarias:
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID
Opcional:
  STATE_PATH        (por defecto data/alerted.json)
  ALERT_SPRINTS=1   para avisar también de las carreras al sprint
"""
from __future__ import annotations

import datetime as dt
import os
import sys

from bot import state
from bot.messages import build_race_alert
from bot.sources import UTC, get_all_sessions
from bot.telegram_client import send_message

WINDOW_MIN = 12  # margen para absorber el jitter del cron de GitHub Actions


def main() -> int:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    state_path = os.environ.get("STATE_PATH", os.path.join("data", "alerted.json"))
    kinds = {"race"}
    if os.environ.get("ALERT_SPRINTS") == "1":
        kinds.add("sprint")

    now_utc = dt.datetime.now(UTC)
    years = sorted({now_utc.year, (now_utc + dt.timedelta(days=14)).year})

    sessions, failed = get_all_sessions(years)
    if failed:
        print(f"Aviso: no se pudieron cargar estos deportes: {', '.join(failed)}.")
    alerted = state.load(state_path)

    sent = 0
    for session in sessions:
        if session.kind not in kinds:
            continue
        if session.uid in alerted:
            continue
        minutes_left = (session.start_utc - now_utc).total_seconds() / 60.0
        if 0 < minutes_left <= WINDOW_MIN:
            send_message(token, chat_id, build_race_alert(session))
            alerted[session.uid] = session.start_utc.isoformat()
            sent += 1
            print(f"Aviso enviado: {session.sport} — {session.event} ({session.name})")

    if sent:
        state.save(state_path, state.prune(alerted, now_utc))
    else:
        print("Ninguna carrera inminente.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
