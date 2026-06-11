"""
services/template_generator.py
Geracao de templates de introducao de curriculo e de carta de motivacao.

Monta prompts organizados a partir do contexto da vaga (e do curriculo,
quando aplicavel), chama o ai_service e devolve o texto gerado, pronto
para ser exibido e editado na UI.

Nada e persistido por este modulo.
"""

from __future__ import annotations

from typing import Optional

from services import ai_service
from utils.helpers import formatar_vaga_para_prompt
from utils.logger import get_logger

logger = get_logger("services.template_generator")

_INSTRUCAO_SISTEMA = (
    "Você é um assistente de redação profissional para candidaturas de emprego. "
    "Escreva em português, com tom profissional, claro e direto. "
    "Não use emojis. Gere apenas o texto solicitado, sem comentários ou "
    "explicações adicionais."
)


def gerar_template_curriculo(vaga: Optional[dict]) -> str:
    """
    Gera a parte inicial (apresentacao/resumo) de um curriculo, adequada
    a vaga informada.
    """
    if not vaga:
        raise ValueError("Selecione uma vaga para gerar o template de currículo.")

    contexto = formatar_vaga_para_prompt(vaga)
    prompt = (
        "Gere a seção inicial (resumo/apresentação) de um currículo para a "
        "vaga abaixo.\n"
        "A seção deve conter: uma apresentação concisa do candidato, seus "
        "objetivos profissionais e a aderência do perfil à vaga.\n"
        "Escreva em primeira pessoa, com 3 a 5 frases. Não invente dados "
        "pessoais específicos; use marcadores como [SEU NOME] ou "
        "[ANOS DE EXPERIÊNCIA] quando necessário.\n\n"
        f"VAGA:\n{contexto}\n"
    )

    texto = ai_service.gerar_conteudo(
        prompt,
        instrucao_sistema=_INSTRUCAO_SISTEMA,
        temperatura=0.6,
    )
    logger.info("Template de currículo gerado (conteúdo não armazenado).")
    return texto


def gerar_carta_motivacao(
    vaga: Optional[dict],
    curriculo_texto: Optional[str] = None,
) -> str:
    """
    Gera uma carta de motivacao para a vaga, opcionalmente baseada no
    conteudo de um curriculo de referencia.
    """
    if not vaga:
        raise ValueError("Selecione uma vaga para gerar a carta de motivação.")

    contexto = formatar_vaga_para_prompt(vaga)

    bloco_curriculo = ""
    if curriculo_texto and curriculo_texto.strip():
        bloco_curriculo = (
            "\nCURRÍCULO DE REFERÊNCIA (use para personalizar a carta):\n"
            f'"""\n{curriculo_texto.strip()}\n"""\n'
        )

    prompt = (
        "Gere uma carta de motivação profissional para a vaga abaixo.\n"
        "A carta deve: abrir com uma apresentação, demonstrar interesse e "
        "aderência à vaga, destacar pontos relevantes do perfil e encerrar "
        "com um fechamento cordial.\n"
        "Escreva em primeira pessoa, com 3 a 4 parágrafos curtos. Use "
        "marcadores como [SEU NOME] quando precisar de dados pessoais.\n\n"
        f"VAGA:\n{contexto}\n"
        f"{bloco_curriculo}"
    )

    texto = ai_service.gerar_conteudo(
        prompt,
        instrucao_sistema=_INSTRUCAO_SISTEMA,
        temperatura=0.6,
    )
    logger.info("Carta de motivação gerada (conteúdo não armazenado).")
    return texto