"""
ui/home.py
Pagina inicial: resumo das vagas, atalhos e ultimas atualizacoes.

So lida com apresentacao: le dados via crud e formata via helpers. Sem
regra de negocio aqui.
"""

from __future__ import annotations

from typing import Callable, Optional

import streamlit as st

from database import crud
from utils.helpers import tempo_relativo, truncar

_LIMITE_ULTIMAS = 6


def render(navegar: Optional[Callable[[str], None]] = None) -> None:
    st.header("Início")

    contagem = crud.contar_vagas_por_status()
    total = sum(contagem.values())

    if total == 0:
        _render_estado_vazio(navegar)
        return

    _render_resumo(contagem, total)
    _render_atalhos(navegar)
    _render_ultimas_vagas()


def _render_estado_vazio(navegar: Optional[Callable[[str], None]]) -> None:
    st.info(
        "Você não tem nenhuma vaga cadastrada! Corra atrás dos seus sonhos "
        "e adicione a vaga interessada no sistema."
    )
    if navegar and st.button("Adicionar vaga"):
        navegar("Vagas")


def _render_resumo(contagem: dict[str, int], total: int) -> None:
    st.subheader("Resumo")
    st.caption(f"Total de vagas acompanhadas: {total}")

    colunas = st.columns(len(contagem))
    for coluna, (status, quantidade) in zip(colunas, contagem.items()):
        coluna.metric(status, quantidade)


def _render_atalhos(navegar: Optional[Callable[[str], None]]) -> None:
    if not navegar:
        return

    st.subheader("Atalhos")
    col1, col2, col3 = st.columns(3)
    if col1.button("Adicionar vaga", use_container_width=True):
        navegar("Vagas")
    if col2.button("Abrir armazenamento", use_container_width=True):
        navegar("Armazenamento")
    if col3.button("Avaliar com IA", use_container_width=True):
        navegar("IA")


def _render_ultimas_vagas() -> None:
    st.subheader("Últimas vagas atualizadas")

    vagas = crud.list_vagas(ordenar_por_data=True)[:_LIMITE_ULTIMAS]
    for vaga in vagas:
        with st.container(border=True):
            st.markdown(f"**{vaga['nome']}**")

            detalhes = []
            if vaga.get("empresa"):
                detalhes.append(vaga["empresa"])
            detalhes.append(vaga["status"])
            st.caption(" • ".join(detalhes))
            st.caption(f"Atualizada {tempo_relativo(vaga['data_status'])}")

            if vaga.get("descricao"):
                st.write(truncar(vaga["descricao"], 160))

            if vaga.get("link"):
                st.markdown(f"[Abrir vaga]({vaga['link']})")