"""
ui/vagas.py
Aba de Vagas: cadastro, edicao, listagem, troca de status e historico.

Camada de apresentacao apenas: toda persistencia e validacao ocorre no
crud. Erros de validacao (ValueError) sao exibidos ao usuario; a data e o
historico de status sao atualizados automaticamente pelo crud.
"""

from __future__ import annotations

from typing import Callable, Optional

import streamlit as st

from database import crud
from database.models import STATUS_VAGAS
from utils.helpers import (
    formatar_data_hora,
    normalizar_url,
    tempo_relativo,
    truncar,
)


# ---------------------------------------------------------------------------
# Mensagem flash (sobrevive ao st.rerun)
# ---------------------------------------------------------------------------


def _flash(mensagem: str, tipo: str = "success") -> None:
    st.session_state["_flash_vagas"] = (tipo, mensagem)


def _mostrar_flash() -> None:
    dados = st.session_state.pop("_flash_vagas", None)
    if dados:
        tipo, mensagem = dados
        getattr(st, tipo, st.info)(mensagem)


# ---------------------------------------------------------------------------
# Pagina
# ---------------------------------------------------------------------------


def render(navegar: Optional[Callable[[str], None]] = None) -> None:
    st.header("Vagas")
    _mostrar_flash()

    total = sum(crud.contar_vagas_por_status().values())

    _render_nova_vaga(expandido=(total == 0))

    if total == 0:
        st.info(
            "Você não tem nenhuma vaga cadastrada! Corra atrás dos seus sonhos "
            "e adicione a vaga interessada no sistema."
        )
        return

    st.divider()
    _render_lista()


# ---------------------------------------------------------------------------
# Criacao
# ---------------------------------------------------------------------------


def _render_nova_vaga(expandido: bool) -> None:
    with st.expander("Nova vaga", expanded=expandido):
        with st.form("form_nova_vaga", clear_on_submit=True):
            nome = st.text_input("Nome da vaga *")

            col1, col2 = st.columns(2)
            empresa = col1.text_input("Empresa")
            funcao = col2.text_input("Função principal")

            descricao = st.text_area("Descrição")

            col3, col4 = st.columns(2)
            status = col3.selectbox("Status", STATUS_VAGAS, index=0)
            link = col4.text_input("Link da vaga")

            enviado = st.form_submit_button("Adicionar vaga")

        if enviado:
            try:
                crud.create_vaga(
                    nome=nome,
                    descricao=descricao,
                    funcao_principal=funcao,
                    status=status,
                    empresa=empresa,
                    link=normalizar_url(link),
                )
                _flash("Vaga adicionada.")
                st.rerun()
            except ValueError as erro:
                st.error(str(erro))


# ---------------------------------------------------------------------------
# Listagem + filtros
# ---------------------------------------------------------------------------


def _render_lista() -> None:
    col1, col2 = st.columns([1, 2])
    status_filtro = col1.selectbox(
        "Filtrar por status", ["Todos", *STATUS_VAGAS], index=0
    )
    busca = col2.text_input("Buscar por nome, empresa ou função")

    vagas = crud.list_vagas(
        status=None if status_filtro == "Todos" else status_filtro,
        busca=busca or None,
    )

    if not vagas:
        st.info("Nenhuma vaga encontrada com os filtros atuais.")
        return

    st.caption(f"{len(vagas)} vaga(s) encontrada(s).")
    for vaga in vagas:
        _render_card(vaga)


def _render_card(vaga: dict) -> None:
    with st.container(border=True):
        st.markdown(f"**{vaga['nome']}**")

        detalhes = []
        if vaga.get("empresa"):
            detalhes.append(vaga["empresa"])
        if vaga.get("funcao_principal"):
            detalhes.append(vaga["funcao_principal"])
        detalhes.append(vaga["status"])
        st.caption(" • ".join(detalhes))
        st.caption(f"Atualizada {tempo_relativo(vaga['data_status'])}")

        if vaga.get("descricao"):
            st.write(truncar(vaga["descricao"], 200))
        if vaga.get("link"):
            st.markdown(f"[Abrir vaga]({vaga['link']})")

        with st.expander("Detalhes e ações"):
            _render_troca_status(vaga)
            st.divider()
            _render_edicao(vaga)
            st.divider()
            _render_historico(vaga)
            st.divider()
            _render_remocao(vaga)


# ---------------------------------------------------------------------------
# Acoes do card
# ---------------------------------------------------------------------------


def _render_troca_status(vaga: dict) -> None:
    vaga_id = vaga["id"]
    st.markdown("**Atualizar status**")

    col1, col2 = st.columns([2, 3])
    novo_status = col1.selectbox(
        "Novo status",
        STATUS_VAGAS,
        index=STATUS_VAGAS.index(vaga["status"]),
        key=f"status_{vaga_id}",
    )
    observacao = col2.text_input("Observação (opcional)", key=f"obs_{vaga_id}")

    if st.button("Salvar status", key=f"btn_status_{vaga_id}"):
        try:
            crud.update_status_vaga(vaga_id, novo_status, observacao or None)
            _flash("Status atualizado.")
            st.rerun()
        except ValueError as erro:
            st.error(str(erro))


def _render_edicao(vaga: dict) -> None:
    vaga_id = vaga["id"]
    st.markdown("**Editar dados**")

    with st.form(f"form_edit_{vaga_id}"):
        nome = st.text_input("Nome da vaga *", value=vaga["nome"])

        col1, col2 = st.columns(2)
        empresa = col1.text_input("Empresa", value=vaga.get("empresa") or "")
        funcao = col2.text_input(
            "Função principal", value=vaga.get("funcao_principal") or ""
        )

        descricao = st.text_area("Descrição", value=vaga.get("descricao") or "")
        link = st.text_input("Link da vaga", value=vaga.get("link") or "")

        salvar = st.form_submit_button("Salvar alterações")

    if salvar:
        try:
            crud.update_vaga(
                vaga_id,
                nome=nome,
                empresa=empresa,
                funcao_principal=funcao,
                descricao=descricao,
                link=normalizar_url(link),
            )
            _flash("Vaga atualizada.")
            st.rerun()
        except ValueError as erro:
            st.error(str(erro))


def _render_historico(vaga: dict) -> None:
    vaga_id = vaga["id"]
    if not st.toggle("Ver histórico de status", key=f"hist_{vaga_id}"):
        return

    historico = crud.get_historico_vaga(vaga_id)
    if not historico:
        st.caption("Sem registros de histórico.")
        return

    for registro in reversed(historico):
        linha = f"{formatar_data_hora(registro['data'])} — {registro['status']}"
        if registro.get("observacao"):
            linha += f" ({registro['observacao']})"
        st.caption(linha)


def _render_remocao(vaga: dict) -> None:
    vaga_id = vaga["id"]
    chave = f"confirma_remocao_{vaga_id}"

    if st.session_state.get(chave):
        st.warning(
            f"Remover a vaga '{vaga['nome']}'? Esta ação não pode ser desfeita."
        )
        col1, col2 = st.columns(2)
        if col1.button("Confirmar remoção", key=f"conf_{vaga_id}"):
            crud.delete_vaga(vaga_id)
            st.session_state.pop(chave, None)
            _flash("Vaga removida.")
            st.rerun()
        if col2.button("Cancelar", key=f"canc_{vaga_id}"):
            st.session_state.pop(chave, None)
            st.rerun()
    else:
        if st.button("Remover vaga", key=f"rem_{vaga_id}"):
            st.session_state[chave] = True
            st.rerun()