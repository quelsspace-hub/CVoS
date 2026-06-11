"""
database/database.py
Configuracao da conexao SQLite e gerenciamento de sessao (SQLAlchemy 2.0).

Responsabilidades:
  - Construir o engine SQLite a partir de config.DATABASE_URL.
  - Habilitar o enforcement de chaves estrangeiras no SQLite (PRAGMA).
  - Fornecer a Base declarativa para os models.
  - Expor um gerenciador de contexto (session_scope) que cuida de
    commit, rollback e fechamento de forma segura.
  - Permitir reconfiguracao do engine (usado pelos testes).

Sem logica de negocio aqui: apenas infraestrutura de persistencia.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

import config


class Base(DeclarativeBase):
    """Base declarativa compartilhada por todos os models."""


@event.listens_for(Engine, "connect")
def _habilitar_foreign_keys(dbapi_connection, connection_record) -> None:
    """
    Habilita o suporte a chaves estrangeiras no SQLite.

    O SQLite vem com FK desabilitada por padrao; sem isto, as acoes
    ON DELETE (CASCADE / SET NULL) nao seriam aplicadas.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _build_engine(database_url: str) -> Engine:
    """Cria um engine SQLite adequado para uso com Streamlit."""
    return create_engine(
        database_url,
        # check_same_thread=False: o Streamlit executa em multiplas threads.
        connect_args={"check_same_thread": False},
        future=True,
    )


# Engine e fabrica de sessao padrao (a partir da configuracao da aplicacao).
engine: Engine = _build_engine(config.DATABASE_URL)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
    future=True,
)


def configure_engine(database_url: str) -> Engine:
    """
    Reconfigura o engine e a fabrica de sessao para outra URL.

    Util principalmente em testes, que apontam para um banco temporario.
    """
    global engine, SessionLocal
    engine = _build_engine(database_url)
    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )
    return engine


def init_db() -> None:
    """
    Cria todas as tabelas declaradas nos models (idempotente).

    O import dos models e feito aqui dentro para registrar as tabelas
    no metadata sem criar import circular em tempo de carga do modulo.
    """
    from database import models  # noqa: F401  (registra as tabelas)

    Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    """
    Fornece uma sessao transacional.

    Faz commit ao final em caso de sucesso, rollback em caso de erro e
    sempre fecha a sessao. Le SessionLocal dinamicamente para respeitar
    eventual reconfiguracao via configure_engine.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()