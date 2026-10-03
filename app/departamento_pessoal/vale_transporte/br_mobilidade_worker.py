import time

import click
from flask.cli import with_appcontext

from app.departamento_pessoal.vale_transporte.br_mobilidade_integracao import (
    buscar_integracoes_pendentes,
    processar_integracao_br_mobilidade,
)


@click.command("br-mobilidade-worker")
@click.option("--once", is_flag=True, help="Processa um ciclo e encerra.")
@click.option("--intervalo", default=15, show_default=True, type=int)
@with_appcontext
def br_mobilidade_worker(once, intervalo):
    """Processa a fila persistente da integração BR Mobilidade."""
    while True:
        pendentes = buscar_integracoes_pendentes()
        for integracao in pendentes:
            processar_integracao_br_mobilidade(integracao.id)
        if once:
            return
        time.sleep(max(5, intervalo))


def registrar_comandos_br_mobilidade(app):
    app.cli.add_command(br_mobilidade_worker)
