from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def carregar_timezone(chave, fallback):
    try:
        return ZoneInfo(chave)
    except ZoneInfoNotFoundError:
        return fallback


UTC_TZ = carregar_timezone("UTC", timezone.utc)
BR_TZ = carregar_timezone("America/Sao_Paulo", timezone(timedelta(hours=-3)))


def agora_brasil():
    return datetime.now(BR_TZ).replace(tzinfo=None)


def formatar_data_hora_brasil(data):
    if not data:
        return "-"

    if data.tzinfo is None:
        data = data.replace(tzinfo=BR_TZ)

    return data.astimezone(BR_TZ).strftime("%d/%m/%Y %H:%M")
