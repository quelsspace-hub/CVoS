"""
database/crud.py
Funcoes de acesso a dados (Create, Read, Update, Delete).

Esta camada e a unica que fala com a sessao do banco. A UI e os
servicos chamam estas funcoes e recebem/enviam dicionarios simples,
sem lidar com objetos ORM nem com o ciclo de vida da sessao.

Convencoes:
  - Cada funcao gerencia sua propria sessao via session_scope().
  - Cada funcao retorna dicionarios (ou listas de dicionarios), evitando
    erros de instancia desanexada no Streamlit.
  - Validacoes de entrada lancam ValueError com mensagem clara.
  - Operacoes de escrita e excecoes sao registradas em log.
"""

from __future__ import annotations

import functools
from datetime import datetime
from typing import Optional

from sqlalchemy import func, or_, select  

from database.database import session_scope
from database.models import (
    STATUS_PADRAO,
    STATUS_VAGAS,
    TIPOS_DOCUMENTO,
    Documento,
    HistoricoStatus,
    Vaga,
)
from utils.helpers import normalizar_tags
from utils.logger import get_logger

logger = get_logger("database.crud")


# ---------------------------------------------------------------------------
# Decorador de logging de excecoes
# ---------------------------------------------------------------------------


def _logar_excecoes(func_alvo):
    """Registra falhas das funcoes CRUD sem alterar seu comportamento."""

    @functools.wraps(func_alvo)
    def wrapper(*args, **kwargs):
        try:
            return func_alvo(*args, **kwargs)
        except ValueError as exc:
            logger.warning("Validação falhou em %s: %s", func_alvo.__name__, exc)
            raise
        except Exception as exc:  # pragma: no cover - caminho de erro inesperado
            logger.error("Erro inesperado em %s: %s", func_alvo.__name__, exc)
            raise

    return wrapper


# ---------------------------------------------------------------------------
# Helpers de validacao / normalizacao
# ---------------------------------------------------------------------------


def _exigir_texto(valor: Optional[str], campo: str) -> str:
    """Garante que um campo de texto obrigatorio nao esteja vazio."""
    if valor is None or not str(valor).strip():
        raise ValueError(f"O campo '{campo}' é obrigatório.")
    return str(valor).strip()


def _texto_opcional(valor: Optional[str]) -> Optional[str]:
    """Normaliza um texto opcional: string limpa ou None."""
    if valor is None:
        return None
    valor = str(valor).strip()
    return valor or None


def _validar_status(status: Optional[str]) -> str:
    """Valida o status de uma vaga contra a lista de dominio."""
    status = (status or STATUS_PADRAO).strip()
    if status not in STATUS_VAGAS:
        raise ValueError(
            f"Status inválido: '{status}'. "
            f"Valores permitidos: {', '.join(STATUS_VAGAS)}."
        )
    return status


def _validar_tipo_documento(tipo: Optional[str]) -> str:
    """Valida o tipo de um documento contra a lista de dominio."""
    tipo = (tipo or "").strip()
    if tipo not in TIPOS_DOCUMENTO:
        raise ValueError(
            f"Tipo de documento inválido: '{tipo}'. "
            f"Valores permitidos: {', '.join(TIPOS_DOCUMENTO)}."
        )
    return tipo


# ---------------------------------------------------------------------------
# CRUD: Vagas
# ---------------------------------------------------------------------------


@_logar_excecoes
def create_vaga(
    nome: str,
    descricao: Optional[str] = None,
    funcao_principal: Optional[str] = None,
    status: str = STATUS_PADRAO,
    empresa: Optional[str] = None,
    link: Optional[str] = None,
    observacao_status: Optional[str] = None,
) -> dict:
    """Cria uma vaga e registra o status inicial no historico."""
    nome = _exigir_texto(nome, "nome")
    status = _validar_status(status)
    agora = datetime.now()

    with session_scope() as session:
        vaga = Vaga(
            nome=nome,
            descricao=_texto_opcional(descricao),
            funcao_principal=_texto_opcional(funcao_principal),
            status=status,
            data_status=agora,
            empresa=_texto_opcional(empresa),
            link=_texto_opcional(link),
        )
        vaga.historico.append(
            HistoricoStatus(
                status=status,
                data=agora,
                observacao=_texto_opcional(observacao_status),
            )
        )
        session.add(vaga)
        session.flush()
        resultado = vaga.to_dict()

    logger.info("Vaga criada: id=%s nome=%r status=%r", resultado["id"], nome, status)
    return resultado


@_logar_excecoes
def get_vaga(vaga_id: int) -> Optional[dict]:
    """Retorna uma vaga por id, ou None se nao existir."""
    with session_scope() as session:
        vaga = session.get(Vaga, vaga_id)
        return vaga.to_dict() if vaga else None


@_logar_excecoes
def list_vagas(
    status: Optional[str] = None,
    busca: Optional[str] = None,
    ordenar_por_data: bool = True,
) -> list[dict]:
    """Lista vagas, com filtros opcionais por status e busca textual."""
    with session_scope() as session:
        stmt = select(Vaga)

        if status:
            stmt = stmt.where(Vaga.status == status)

        if busca and busca.strip():
            termo = f"%{busca.strip()}%"
            stmt = stmt.where(
                or_(
                    Vaga.nome.ilike(termo),
                    Vaga.empresa.ilike(termo),
                    Vaga.funcao_principal.ilike(termo),
                )
            )

        if ordenar_por_data:
            stmt = stmt.order_by(Vaga.data_status.desc())
        else:
            stmt = stmt.order_by(Vaga.nome.asc())

        return [v.to_dict() for v in session.scalars(stmt).all()]


@_logar_excecoes
def update_vaga(vaga_id: int, **campos) -> dict:
    """
    Atualiza campos de uma vaga (exceto status).

    O status nao e alterado aqui para garantir o registro de historico:
    use update_status_vaga().
    """
    permitidos = {"nome", "descricao", "funcao_principal", "empresa", "link"}

    with session_scope() as session:
        vaga = session.get(Vaga, vaga_id)
        if not vaga:
            raise ValueError(f"Vaga {vaga_id} não encontrada.")

        for campo, valor in campos.items():
            if campo not in permitidos:
                raise ValueError(
                    f"Campo não atualizável por esta função: '{campo}'. "
                    "Use update_status_vaga para alterar o status."
                )
            if campo == "nome":
                setattr(vaga, campo, _exigir_texto(valor, "nome"))
            else:
                setattr(vaga, campo, _texto_opcional(valor))

        session.flush()
        resultado = vaga.to_dict()

    logger.info("Vaga atualizada: id=%s campos=%s", vaga_id, list(campos.keys()))
    return resultado


@_logar_excecoes
def update_status_vaga(
    vaga_id: int,
    novo_status: str,
    observacao: Optional[str] = None,
) -> dict:
    """
    Altera o status de uma vaga, atualiza a data e registra o historico.

    Se o status enviado for igual ao atual, e tratado como no-op (nao
    duplica historico nem altera a data).
    """
    novo_status = _validar_status(novo_status)
    agora = datetime.now()

    with session_scope() as session:
        vaga = session.get(Vaga, vaga_id)
        if not vaga:
            raise ValueError(f"Vaga {vaga_id} não encontrada.")

        if vaga.status == novo_status:
            return vaga.to_dict()

        anterior = vaga.status
        vaga.status = novo_status
        vaga.data_status = agora
        vaga.historico.append(
            HistoricoStatus(
                status=novo_status,
                data=agora,
                observacao=_texto_opcional(observacao),
            )
        )
        session.flush()
        resultado = vaga.to_dict()

    logger.info(
        "Status da vaga %s alterado: %r -> %r", vaga_id, anterior, novo_status
    )
    return resultado


@_logar_excecoes
def delete_vaga(vaga_id: int) -> bool:
    """
    Remove uma vaga. O historico e removido em cascata; documentos
    associados tem o vinculo (vaga_id) definido como NULL.
    Retorna True se removeu, False se a vaga nao existia.
    """
    with session_scope() as session:
        vaga = session.get(Vaga, vaga_id)
        if not vaga:
            return False
        session.delete(vaga)

    logger.info("Vaga removida: id=%s", vaga_id)
    return True


@_logar_excecoes
def get_historico_vaga(vaga_id: int) -> list[dict]:
    """Retorna o historico de status de uma vaga (ordem cronologica)."""
    with session_scope() as session:
        vaga = session.get(Vaga, vaga_id)
        if not vaga:
            raise ValueError(f"Vaga {vaga_id} não encontrada.")
        return [h.to_dict() for h in vaga.historico]


@_logar_excecoes
def contar_vagas_por_status() -> dict[str, int]:
    """
    Retorna a contagem de vagas por status, incluindo zeros para os
    status sem vagas. Util para os contadores da pagina inicial.
    """
    with session_scope() as session:
        stmt = select(Vaga.status, func.count(Vaga.id)).group_by(Vaga.status)
        contagem = {status: 0 for status in STATUS_VAGAS}
        for status, total in session.execute(stmt).all():
            contagem[status] = total
        return contagem


# ---------------------------------------------------------------------------
# CRUD: Documentos
# ---------------------------------------------------------------------------


@_logar_excecoes
def create_documento(
    titulo: str,
    tipo: str,
    conteudo: str = "",
    area: Optional[str] = None,
    vaga_id: Optional[int] = None,
    descricao_curta: Optional[str] = None,
    tags=None,
) -> dict:
    """Cria um documento (curriculo ou carta)."""
    titulo = _exigir_texto(titulo, "titulo")
    tipo = _validar_tipo_documento(tipo)

    with session_scope() as session:
        if vaga_id is not None and session.get(Vaga, vaga_id) is None:
            raise ValueError(
                f"Vaga {vaga_id} não encontrada para associação ao documento."
            )

        documento = Documento(
            titulo=titulo,
            tipo=tipo,
            conteudo=conteudo or "",
            area=_texto_opcional(area),
            vaga_id=vaga_id,
            descricao_curta=_texto_opcional(descricao_curta),
            tags=normalizar_tags(tags),
        )
        session.add(documento)
        session.flush()
        resultado = documento.to_dict()

    logger.info(
        "Documento criado: id=%s titulo=%r tipo=%r", resultado["id"], titulo, tipo
    )
    return resultado


@_logar_excecoes
def get_documento(documento_id: int) -> Optional[dict]:
    """Retorna um documento por id, ou None se nao existir."""
    with session_scope() as session:
        documento = session.get(Documento, documento_id)
        return documento.to_dict() if documento else None


@_logar_excecoes
def list_documentos(
    area: Optional[str] = None,
    tipo: Optional[str] = None,
    vaga_id: Optional[int] = None,
    busca: Optional[str] = None,
) -> list[dict]:
    """Lista documentos com filtros opcionais (area, tipo, vaga, busca)."""
    with session_scope() as session:
        stmt = select(Documento)

        if area and area.strip():
            stmt = stmt.where(Documento.area.ilike(f"%{area.strip()}%"))
        if tipo:
            stmt = stmt.where(Documento.tipo == tipo)
        if vaga_id is not None:
            stmt = stmt.where(Documento.vaga_id == vaga_id)
        if busca and busca.strip():
            termo = f"%{busca.strip()}%"
            stmt = stmt.where(
                or_(
                    Documento.titulo.ilike(termo),
                    Documento.descricao_curta.ilike(termo),
                    Documento.tags.ilike(termo),
                )
            )

        stmt = stmt.order_by(Documento.data_atualizacao.desc())
        return [d.to_dict() for d in session.scalars(stmt).all()]


@_logar_excecoes
def update_documento(documento_id: int, **campos) -> dict:
    """Atualiza campos de um documento, com validacao por campo."""
    permitidos = {
        "titulo",
        "tipo",
        "area",
        "vaga_id",
        "descricao_curta",
        "conteudo",
        "tags",
    }

    with session_scope() as session:
        documento = session.get(Documento, documento_id)
        if not documento:
            raise ValueError(f"Documento {documento_id} não encontrado.")

        for campo, valor in campos.items():
            if campo not in permitidos:
                raise ValueError(f"Campo não atualizável: '{campo}'.")

            if campo == "titulo":
                documento.titulo = _exigir_texto(valor, "titulo")
            elif campo == "tipo":
                documento.tipo = _validar_tipo_documento(valor)
            elif campo == "vaga_id":
                if valor is not None and session.get(Vaga, valor) is None:
                    raise ValueError(f"Vaga {valor} não encontrada.")
                documento.vaga_id = valor
            elif campo == "conteudo":
                documento.conteudo = valor or ""
            elif campo == "tags":
                documento.tags = normalizar_tags(valor)
            else:  # area, descricao_curta
                setattr(documento, campo, _texto_opcional(valor))

        session.flush()
        resultado = documento.to_dict()

    logger.info(
        "Documento atualizado: id=%s campos=%s", documento_id, list(campos.keys())
    )
    return resultado


@_logar_excecoes
def delete_documento(documento_id: int) -> bool:
    """Remove um documento. Retorna True se removeu, False se nao existia."""
    with session_scope() as session:
        documento = session.get(Documento, documento_id)
        if not documento:
            return False
        session.delete(documento)

    logger.info("Documento removido: id=%s", documento_id)
    return True