"""
ui/armazenamento.py
Aba de Armazenamento: curriculos e cartas de motivacao.

Permite cadastrar, listar (com filtros e busca), editar, remover e
associar documentos a vagas. Inclui uma indicacao simples de combinacoes
CV + carta por vaga (baseada na associacao, sem IA).

Camada de apresentacao: persistencia e validacao ficam no crud.
"""

from __future__ import annotations

from typing import Callable, Optional

import streamlit as st

from database import crud
from database.models import TIPOS_DOCUMENTO
from utils.helpers import formatar_data_hora, tempo_relativo, truncar

_TIPO_CURRICULO = "Currículo"
_TIPO_CARTA = "Carta de Motivação"


# ---------------------------------------------------------------------------
# Flash
# ---------------------------------------------------------------------------


def _flash(mensagem: str, tipo: str = "success") -> None:
    st.session_state["_flash_armazenamento"] = (tipo, mensagem)


def _mostrar_flash() -> None:
    dados = st.session_state.pop("_flash_armazenamento", None)
    if dados:
        tipo, mensagem = dados
        getattr(st, tipo, st.info)(mensagem)


# ---------------------------------------------------------------------------
# Utilitarios de vaga
# ---------------------------------------------------------------------------


def _opcoes_vaga() -> dict[str, Optional[int]]:
    """Mapa rotulo -> id de vaga, com a opcao 'Nenhuma' no inicio."""
    opcoes: dict[str, Optional[int]] = {"Nenhuma": None}
    for vaga in crud.list_vagas(ordenar_por_data=False):
        opcoes[f"{vaga['nome']} (#{vaga['id']})"] = vaga["id"]
    return opcoes


def _nome_vaga(vaga_id: Optional[int]) -> Optional[str]:
    if vaga_id is None:
        return None
    vaga = crud.get_vaga(vaga_id)
    return vaga["nome"] if vaga else None


# ---------------------------------------------------------------------------
# Pagina
# ---------------------------------------------------------------------------


def render(navegar: Optional[Callable[[str], None]] = None) -> None:
    st.header("Armazenamento")
    _mostrar_flash()

    total = len(crud.list_documentos())

    _render_novo_documento(expandido=(total == 0))

    if total == 0:
        st.info(
            "Nenhum documento armazenado ainda. Adicione um currículo ou uma "
            "carta de motivação para reutilizar nas suas candidaturas."
        )
        return

    st.divider()
    _render_combinacoes()
    st.divider()
    _render_lista()


# ---------------------------------------------------------------------------
# Criacao
# ---------------------------------------------------------------------------


def _render_novo_documento(expandido: bool) -> None:
    opcoes_vaga = _opcoes_vaga()

    with st.expander("Novo documento", expanded=expandido):
        with st.form("form_novo_documento", clear_on_submit=True):
            titulo = st.text_input("Título *")

            col1, col2 = st.columns(2)
            tipo = col1.selectbox("Tipo *", TIPOS_DOCUMENTO, index=0)
            area = col2.text_input("Área")

            vaga_rotulo = st.selectbox("Vaga associada", list(opcoes_vaga.keys()))
            descricao_curta = st.text_input("Descrição curta")
            conteudo = st.text_area("Conteúdo", height=200)
            tags = st.text_input("Tags (separadas por vírgula)")

            enviado = st.form_submit_button("Salvar documento")

        if enviado:
            try:
                crud.create_documento(
                    titulo=titulo,
                    tipo=tipo,
                    conteudo=conteudo,
                    area=area,
                    vaga_id=opcoes_vaga[vaga_rotulo],
                    descricao_curta=descricao_curta,
                    tags=tags,
                )
                _flash("Documento salvo.")
                st.rerun()
            except ValueError as erro:
                st.error(str(erro))


# ---------------------------------------------------------------------------
# Combinacoes CV + carta por vaga
# ---------------------------------------------------------------------------


def _render_combinacoes() -> None:
    with st.expander("Combinações por vaga"):
        opcoes_vaga = _opcoes_vaga()
        rotulos = [r for r in opcoes_vaga if opcoes_vaga[r] is not None]

        if not rotulos:
            st.caption("Cadastre vagas e associe documentos a elas para ver sugestões.")
            return

        escolha = st.selectbox("Selecione uma vaga", rotulos, key="combo_vaga")
        vaga_id = opcoes_vaga[escolha]

        curriculos = crud.list_documentos(tipo=_TIPO_CURRICULO, vaga_id=vaga_id)
        cartas = crud.list_documentos(tipo=_TIPO_CARTA, vaga_id=vaga_id)

        col1, col2 = st.columns(2)
        col1.markdown("**Currículos associados**")
        if curriculos:
            for doc in curriculos:
                col1.caption(doc["titulo"])
        else:
            col1.caption("Nenhum.")

        col2.markdown("**Cartas associadas**")
        if cartas:
            for doc in cartas:
                col2.caption(doc["titulo"])
        else:
            col2.caption("Nenhuma.")

        if curriculos and cartas:
            st.success(
                f"Combinação sugerida: '{curriculos[0]['titulo']}' + "
                f"'{cartas[0]['titulo']}'."
            )
        else:
            st.info("Associe ao menos um currículo e uma carta a esta vaga "
                    "para receber uma sugestão de combinação.")


# ---------------------------------------------------------------------------
# Listagem + filtros
# ---------------------------------------------------------------------------


def _render_lista() -> None:
    col1, col2, col3 = st.columns([1, 1, 2])
    tipo_filtro = col1.selectbox("Tipo", ["Todos", *TIPOS_DOCUMENTO], index=0)
    area_filtro = col2.text_input("Área")
    busca = col3.text_input("Buscar por título, descrição ou tags")

    documentos = crud.list_documentos(
        tipo=None if tipo_filtro == "Todos" else tipo_filtro,
        area=area_filtro or None,
        busca=busca or None,
    )

    if not documentos:
        st.info("Nenhum documento encontrado com os filtros atuais.")
        return

    st.caption(f"{len(documentos)} documento(s) encontrado(s).")
    for documento in documentos:
        _render_card(documento)


def _render_card(documento: dict) -> None:
    with st.container(border=True):
        st.markdown(f"**{documento['titulo']}**")

        detalhes = [documento["tipo"]]
        if documento.get("area"):
            detalhes.append(documento["area"])
        nome_vaga = _nome_vaga(documento.get("vaga_id"))
        if nome_vaga:
            detalhes.append(f"Vaga: {nome_vaga}")
        st.caption(" • ".join(detalhes))
        st.caption(f"Atualizado {tempo_relativo(documento['data_atualizacao'])}")

        if documento.get("descricao_curta"):
            st.write(documento["descricao_curta"])
        if documento.get("tags"):
            st.caption(f"Tags: {documento['tags']}")

        with st.expander("Detalhes e ações"):
            _render_conteudo(documento)
            st.divider()
            _render_edicao(documento)
            st.divider()
            _render_remocao(documento)


# ---------------------------------------------------------------------------
# Acoes do card
# ---------------------------------------------------------------------------


def _render_conteudo(documento: dict) -> None:
    if st.toggle("Ver conteúdo", key=f"conteudo_{documento['id']}"):
        st.text_area(
            "Conteúdo",
            value=documento.get("conteudo") or "",
            height=200,
            disabled=True,
            key=f"view_conteudo_{documento['id']}",
        )


def _render_edicao(documento: dict) -> None:
    doc_id = documento["id"]
    st.markdown("**Editar documento**")

    opcoes_vaga = _opcoes_vaga()
    rotulos = list(opcoes_vaga.keys())
    indice_vaga = next(
        (i for i, r in enumerate(rotulos) if opcoes_vaga[r] == documento.get("vaga_id")),
        0,
    )
    indice_tipo = (
        TIPOS_DOCUMENTO.index(documento["tipo"])
        if documento["tipo"] in TIPOS_DOCUMENTO
        else 0
    )

    with st.form(f"form_edit_doc_{doc_id}"):
        titulo = st.text_input("Título *", value=documento["titulo"])

        col1, col2 = st.columns(2)
        tipo = col1.selectbox("Tipo *", TIPOS_DOCUMENTO, index=indice_tipo)
        area = col2.text_input("Área", value=documento.get("area") or "")

        vaga_rotulo = st.selectbox("Vaga associada", rotulos, index=indice_vaga)
        descricao_curta = st.text_input(
            "Descrição curta", value=documento.get("descricao_curta") or ""
        )
        conteudo = st.text_area(
            "Conteúdo", value=documento.get("conteudo") or "", height=200
        )
        tags = st.text_input("Tags", value=documento.get("tags") or "")

        salvar = st.form_submit_button("Salvar alterações")

    if salvar:
        try:
            crud.update_documento(
                doc_id,
                titulo=titulo,
                tipo=tipo,
                area=area,
                vaga_id=opcoes_vaga[vaga_rotulo],
                descricao_curta=descricao_curta,
                conteudo=conteudo,
                tags=tags,
            )
            _flash("Documento atualizado.")
            st.rerun()
        except ValueError as erro:
            st.error(str(erro))


def _render_remocao(documento: dict) -> None:
    doc_id = documento["id"]
    chave = f"confirma_remocao_doc_{doc_id}"

    if st.session_state.get(chave):
        st.warning(
            f"Remover o documento '{documento['titulo']}'? "
            "Esta ação não pode ser desfeita."
        )
        col1, col2 = st.columns(2)
        if col1.button("Confirmar remoção", key=f"conf_doc_{doc_id}"):
            crud.delete_documento(doc_id)
            st.session_state.pop(chave, None)
            _flash("Documento removido.")
            st.rerun()
        if col2.button("Cancelar", key=f"canc_doc_{doc_id}"):
            st.session_state.pop(chave, None)
            st.rerun()
    else:
        if st.button("Remover documento", key=f"rem_doc_{doc_id}"):
            st.session_state[chave] = True
            st.rerun()