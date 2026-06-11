"""
utils/logger.py
Configuracao central de logging da aplicacao.

Cria um logger nomeado ("central_de_vagas") com dois destinos:
  - arquivo rotativo em config.LOG_PATH (evita crescimento ilimitado);
  - console (stderr), util durante a execucao do Streamlit.

A configuracao e idempotente: chamar get_logger varias vezes nao
duplica handlers. Sem logica de negocio aqui.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

import config

_FORMATO = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_NOME_BASE = "central_de_vagas"
_MAX_BYTES = 1_000_000  # ~1 MB por arquivo de log
_BACKUP_COUNT = 3

_configurado = False


def _nivel() -> int:
    """Converte config.LOG_LEVEL em constante do logging, com fallback."""
    return getattr(logging, config.LOG_LEVEL, logging.INFO)


def _configurar_base() -> None:
    """Configura o logger base uma unica vez."""
    global _configurado
    if _configurado:
        return

    logger_base = logging.getLogger(_NOME_BASE)
    logger_base.setLevel(_nivel())
    # Nao propaga para o root do Python para nao duplicar com o Streamlit.
    logger_base.propagate = False

    if not logger_base.handlers:
        formatter = logging.Formatter(_FORMATO)

        try:
            file_handler = RotatingFileHandler(
                config.LOG_PATH,
                maxBytes=_MAX_BYTES,
                backupCount=_BACKUP_COUNT,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            logger_base.addHandler(file_handler)
        except OSError:
            # Se nao for possivel escrever em arquivo, segue apenas com console.
            pass

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger_base.addHandler(console_handler)

    _configurado = True


def get_logger(nome: str) -> logging.Logger:
    """
    Retorna um logger filho namespaced sob "central_de_vagas".

    Exemplo: get_logger("database.crud") -> "central_de_vagas.database.crud".
    """
    _configurar_base()
    return logging.getLogger(f"{_NOME_BASE}.{nome}")