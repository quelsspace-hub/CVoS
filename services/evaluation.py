"""
services/evaluation.py
Avaliacao de curriculos e cartas de motivacao pela IA.

Fluxo:
  1. Monta um prompt com o documento e o contexto da vaga.
  2. Chama o ai_service solicitando saida em JSON.
  3. Interpreta e normaliza a resposta para uma estrutura previsivel,
     pronta para exibicao na UI.

Regra de negocio critica: o conteudo avaliado NUNCA e persistido.
Este modulo apenas processa a resposta em memoria.
"""

from __future__ import annotations

import json
from typing import Optional

from services import ai_service
from utils.helpers import formatar_vaga_para_prompt
from utils.logger import get_logger

logger = get_logger("services.evaluation")

# Chaves garantidas na estrutura de retorno.
CHAVES_AVALIACAO = (
    "summary",
    "strengths",
    "gaps",
    "unnecessary_elements",
    "recommendations",
    "observations",
)

_INSTRUCAO_SISTEMA = (
    "Você é um avaliador especialista em currículos e cartas de motivação. "
    "Responda em português, de forma objetiva e acionável. "
    "Baseie-se apenas no conteúdo fornecido; não invente informações. "
    "Não use emojis. Responda exclusivamente em JSON válido, "
    "sem nenhum texto fora do JSON."
)


def _montar_prompt(documento_texto: str, vaga: Optional[dict], tipo_documento: Optional[str]) -> str:
    rotulo = (tipo_documento or "documento").strip()
    contexto = formatar_vaga_para_prompt(vaga)
    return (
        f"Avalie o {rotulo} a seguir em relação à vaga.\n\n"
        f"VAGA:\n{contexto}\n\n"
        f"{rotulo.upper()}:\n"
        f'"""\n{documento_texto}\n"""\n\n'
        "Retorne um objeto JSON com exatamente estas chaves:\n"
        '- "summary": resumo geral da avaliação (string)\n'
        '- "strengths": pontos do documento alinhados à vaga (lista de strings)\n'
        '- "gaps": lacunas ou pontos a reforçar (lista de strings)\n'
        '- "unnecessary_elements": elementos desnecessários ou irrelevantes (lista de strings)\n'
        '- "recommendations": recomendações práticas (lista de strings)\n'
        '- "observations": observações sobre clareza, relevância e estrutura (string)\n'
    )


def _extrair_json(texto: str) -> dict:
    """Interpreta o JSON da IA, tolerando cercas de codigo e texto residual."""
    conteudo = texto.strip()

    if conteudo.startswith("```"):
        conteudo = conteudo.strip("`").strip()
        if conteudo.lower().startswith("json"):
            conteudo = conteudo[4:].strip()

    try:
        return json.loads(conteudo)
    except json.JSONDecodeError:
        inicio = conteudo.find("{")
        fim = conteudo.rfind("}")
        if inicio != -1 and fim != -1 and fim > inicio:
            return json.loads(conteudo[inicio : fim + 1])
        raise


def _normalizar(bruto: dict) -> dict:
    """Garante tipos e chaves consistentes na estrutura de avaliacao."""

    def como_lista(valor) -> list[str]:
        if isinstance(valor, list):
            return [str(item).strip() for item in valor if str(item).strip()]
        if valor is None:
            return []
        texto = str(valor).strip()
        return [texto] if texto else []

    def como_texto(valor) -> str:
        return str(valor).strip() if valor is not None else ""

    return {
        "summary": como_texto(bruto.get("summary")),
        "strengths": como_lista(bruto.get("strengths")),
        "gaps": como_lista(bruto.get("gaps")),
        "unnecessary_elements": como_lista(bruto.get("unnecessary_elements")),
        "recommendations": como_lista(bruto.get("recommendations")),
        "observations": como_texto(bruto.get("observations")),
    }


def avaliar(
    documento_texto: str,
    vaga: Optional[dict] = None,
    tipo_documento: Optional[str] = None,
) -> dict:
    """
    Avalia um documento em relacao a uma vaga e retorna a analise
    normalizada. O texto avaliado nao e armazenado.
    """
    if not documento_texto or not documento_texto.strip():
        raise ValueError("O conteúdo do documento para avaliação está vazio.")

    prompt = _montar_prompt(documento_texto.strip(), vaga, tipo_documento)
    resposta = ai_service.gerar_conteudo(
        prompt,
        instrucao_sistema=_INSTRUCAO_SISTEMA,
        espera_json=True,
    )

    try:
        bruto = _extrair_json(resposta)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("Falha ao interpretar JSON da IA: %s", exc)
        raise ai_service.AIServiceError(
            "A IA retornou um JSON inválido. Tente novamente."
        ) from exc

    if not isinstance(bruto, dict):
        raise ai_service.AIServiceError("A IA não retornou um objeto JSON válido.")

    resultado = _normalizar(bruto)
    logger.info("Avaliação concluída (conteúdo não armazenado).")
    return resultado