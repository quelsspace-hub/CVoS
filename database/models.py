"""
database/models.py
Definicao das tabelas do sistema (SQLAlchemy 2.0, estilo tipado).

Tabelas:
  - vagas              : vagas de emprego acompanhadas pelo usuario.
  - documentos         : curriculos e cartas de motivacao armazenados.
  - historico_status   : registro de cada mudanca de status de uma vaga.

Decisao de modelagem: o historico de status fica em tabela propria e
normalizada (em vez de empilhar JSON na vaga), pois e mais limpo,
consultavel e atende diretamente a regra de negocio de manter historico.

Os conteudos enviados a IA NAO sao modelados aqui: por regra do projeto,
eles nunca sao persistidos.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base

# ---------------------------------------------------------------------------
# Valores de dominio (fonte unica de verdade para status e tipos)
# ---------------------------------------------------------------------------
STATUS_VAGAS: tuple[str, ...] = (
    "Interessado",
    "Inscrito",
    "A realizar trilhas",
    "Entrevista agendada",
    "Convocado",
    "Não convocado",
)
STATUS_PADRAO: str = "Interessado"

TIPOS_DOCUMENTO: tuple[str, ...] = (
    "Currículo",
    "Carta de Motivação",
)


class Vaga(Base):
    """Vaga de emprego acompanhada pelo usuario."""

    __tablename__ = "vagas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text)
    funcao_principal: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=STATUS_PADRAO
    )
    data_status: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    empresa: Mapped[str | None] = mapped_column(String(200))
    link: Mapped[str | None] = mapped_column(String(500))

    # Documentos podem existir sem vaga; ao apagar a vaga, vira NULL.
    documentos: Mapped[list["Documento"]] = relationship(
        back_populates="vaga",
        passive_deletes=True,
    )
    # Historico pertence a vaga; ao apagar a vaga, e removido junto.
    historico: Mapped[list["HistoricoStatus"]] = relationship(
        back_populates="vaga",
        cascade="all, delete-orphan",
        order_by="HistoricoStatus.data",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nome": self.nome,
            "descricao": self.descricao,
            "funcao_principal": self.funcao_principal,
            "status": self.status,
            "data_status": self.data_status,
            "empresa": self.empresa,
            "link": self.link,
        }


class Documento(Base):
    """Curriculo ou carta de motivacao armazenado pelo usuario."""

    __tablename__ = "documentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    area: Mapped[str | None] = mapped_column(String(120))
    vaga_id: Mapped[int | None] = mapped_column(
        ForeignKey("vagas.id", ondelete="SET NULL")
    )
    descricao_curta: Mapped[str | None] = mapped_column(String(300))
    conteudo: Mapped[str] = mapped_column(Text, nullable=False, default="")
    data_criacao: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    data_atualizacao: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )
    tags: Mapped[str | None] = mapped_column(String(300))

    vaga: Mapped["Vaga | None"] = relationship(back_populates="documentos")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "titulo": self.titulo,
            "tipo": self.tipo,
            "area": self.area,
            "vaga_id": self.vaga_id,
            "descricao_curta": self.descricao_curta,
            "conteudo": self.conteudo,
            "data_criacao": self.data_criacao,
            "data_atualizacao": self.data_atualizacao,
            "tags": self.tags,
        }


class HistoricoStatus(Base):
    """Registro de uma mudanca de status de uma vaga."""

    __tablename__ = "historico_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vaga_id: Mapped[int] = mapped_column(
        ForeignKey("vagas.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    data: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    observacao: Mapped[str | None] = mapped_column(String(300))

    vaga: Mapped["Vaga"] = relationship(back_populates="historico")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "vaga_id": self.vaga_id,
            "status": self.status,
            "data": self.data,
            "observacao": self.observacao,
        }