from decimal import Decimal, InvalidOperation


def formatar_leitura_horimetro(valor):
    """Exibe somente os quatro primeiros dígitos da parte inteira."""
    if valor is None:
        return "-"
    try:
        numero = Decimal(str(valor))
        sinal = "-" if numero < 0 else ""
        inteiro, _, decimais = format(abs(numero), "f").partition(".")
        inteiro = inteiro[:4] if len(inteiro) > 4 else inteiro
        decimais = (decimais + "00")[:2]
        return f"{sinal}{inteiro},{decimais}"
    except (InvalidOperation, TypeError, ValueError):
        return "-"
