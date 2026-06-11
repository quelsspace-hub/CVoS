"""
services/ai_service.py
Camada de comunicacao de baixo nivel com a IA Gemini (SDK google-genai).

Responsabilidades:
  - Inicializar o cliente Gemini de forma preguicosa (apenas quando usado).
  - Expor uma funcao unica de geracao de conteudo, com tratamento de erro,
    timeout e suporte a saida em JSON.
  - Garantir que nenhum conteudo enviado a IA seja persistido: este modulo
    nao importa nem chama a camada de banco de dados.

Toda chamada e sob demanda. Em caso de erro, levanta AIServiceError com
mensagem clara para a UI exibir.
"""

from __future__ import annotations

from typing import Optional

import config
from utils.logger import get_logger

logger = get_logger("services.ai_service")


class AIServiceError(Exception):
    """Erro na configuracao ou comunicacao com o servico de IA."""


# Cliente Gemini reutilizavel (criado sob demanda).
_client = None


def is_configured() -> bool:
    """Indica se ha chave de API configurada para uso da IA."""
    return bool(config.GEMINI_API_KEY)


def reset_client() -> None:
    """
    Descarta o cliente em cache, forcando recriacao na proxima chamada.

    Util apos a troca da chave de API pela tela de Configuracoes.
    """
    global _client
    _client = None


def _criar_client(genai):
    """Cria o cliente Gemini, aplicando timeout quando suportado."""
    try:
        from google.genai import types

        opcoes = types.HttpOptions(timeout=config.GEMINI_TIMEOUT_SECONDS * 1000)
        return genai.Client(api_key=config.GEMINI_API_KEY, http_options=opcoes)
    except Exception:
        # Fallback: cliente sem opcoes de http customizadas.
        return genai.Client(api_key=config.GEMINI_API_KEY)


def _get_client():
    """Retorna o cliente Gemini, inicializando-o se necessario."""
    global _client
    if _client is not None:
        return _client

    if not is_configured():
        raise AIServiceError(
            "GEMINI_API_KEY não configurada. Defina-a no arquivo .env ou na "
            "tela de Configurações."
        )

    try:
        from google import genai
    except ImportError as exc:
        raise AIServiceError(
            "Pacote 'google-genai' não instalado. "
            "Execute: pip install google-genai"
        ) from exc

    try:
        _client = _criar_client(genai)
    except Exception as exc:
        raise AIServiceError(f"Falha ao inicializar o cliente Gemini: {exc}") from exc

    logger.info("Cliente Gemini inicializado (modelo padrão: %s).", config.GEMINI_MODEL)
    return _client


def gerar_conteudo(
    prompt: str,
    *,
    instrucao_sistema: Optional[str] = None,
    espera_json: bool = False,
    temperatura: float = 0.4,
) -> str:
    """
    Envia um prompt ao Gemini e retorna o texto da resposta.

    Parametros:
      prompt            : conteudo principal enviado ao modelo.
      instrucao_sistema : instrucao de sistema (papel/tom do modelo).
      espera_json       : se True, solicita saida em JSON (application/json).
      temperatura       : controla a criatividade da resposta.

    Levanta AIServiceError em caso de falha ou resposta vazia.
    O texto enviado NAO e armazenado em lugar algum.
    """
    if not prompt or not prompt.strip():
        raise ValueError("O prompt enviado à IA está vazio.")

    client = _get_client()

    try:
        from google.genai import types
    except ImportError as exc:
        raise AIServiceError(
            "Pacote 'google-genai' não instalado. "
            "Execute: pip install google-genai"
        ) from exc

    parametros = {"temperature": temperatura}
    if instrucao_sistema:
        parametros["system_instruction"] = instrucao_sistema
    if espera_json:
        parametros["response_mime_type"] = "application/json"

    try:
        resposta = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(**parametros),
        )
    except Exception as exc:
        logger.error("Erro na chamada ao Gemini: %s", exc)
        raise AIServiceError(f"Erro ao comunicar com a IA: {exc}") from exc

    texto = getattr(resposta, "text", None)
    if not texto or not texto.strip():
        raise AIServiceError("A IA retornou uma resposta vazia.")

    logger.info("Resposta da IA recebida (%d caracteres).", len(texto))
    return texto.strip()