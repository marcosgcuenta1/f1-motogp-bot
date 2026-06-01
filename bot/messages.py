"""Construcción de los textos que se envían a Telegram."""
from __future__ import annotations

import datetime as dt
from collections import OrderedDict

from .sources import MADRID, Session
from .telegram_client import escape

_DAYS_ES = [
    "lunes", "martes", "miércoles", "jueves",
    "viernes", "sábado", "domingo",
]
_SPORT_ICON = {"F1": "🏎️", "MotoGP": "🏍️"}


def _fmt_day_time(when: dt.datetime) -> str:
    """'Sábado 14:30' (la fecha debe venir ya en hora de Madrid)."""
    return f"{_DAYS_ES[when.weekday()].capitalize()} {when:%H:%M}"


def upcoming_weekend(now_madrid: dt.datetime) -> tuple[dt.datetime, dt.datetime]:
    """Ventana [viernes 00:00, domingo 23:59] del fin de semana más próximo."""
    days_to_friday = (4 - now_madrid.weekday()) % 7  # lunes=0 ... viernes=4
    friday = (now_madrid + dt.timedelta(days=days_to_friday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    sunday_end = (friday + dt.timedelta(days=2)).replace(
        hour=23, minute=59, second=59, microsecond=0
    )
    return friday, sunday_end


def build_weekend_summary(
    sessions: list[Session],
    start_madrid: dt.datetime,
    end_madrid: dt.datetime,
) -> str | None:
    """Resumen del finde, o ``None`` si no hay ninguna sesión en la ventana."""
    in_window = [
        s for s in sessions if start_madrid <= s.start_madrid <= end_madrid
    ]
    if not in_window:
        return None

    in_window.sort(key=lambda s: s.start_utc)

    groups: "OrderedDict[tuple[str, str], list[Session]]" = OrderedDict()
    for session in in_window:
        groups.setdefault((session.sport, session.event), []).append(session)

    lines = ["🏁 <b>Carreras de este fin de semana</b> 🏁", ""]
    for (sport, event), group in groups.items():
        icon = _SPORT_ICON.get(sport, "")
        lines.append(f"{icon} <b>{escape(sport)} — {escape(event)}</b>")
        for session in group:
            lines.append(
                f"   • {escape(session.name)}: "
                f"{_fmt_day_time(session.start_madrid)}"
            )
        lines.append("")

    lines.append("<i>Horarios en hora de Madrid 🇪🇸</i>")
    return "\n".join(lines)


def build_race_alert(session: Session) -> str:
    icon = _SPORT_ICON.get(session.sport, "🏁")
    hora = f"{session.start_madrid:%H:%M}"
    return (
        f"⏰ <b>¡Quedan 10 minutos para que empiece!</b>\n\n"
        f"{icon} {escape(session.sport)} — <b>{escape(session.event)}</b>\n"
        f"🏁 {escape(session.name)} · empieza a las {hora} (hora de Madrid)"
    )
