"""
ui/ia.py
Aba de IA: avaliacao de documentos e geracao de templates (Gemini).

Tres funcoes, em abas:
  1. Avaliar um curriculo/carta em relacao a uma vaga.
  2. Gerar a introducao de um curriculo a partir da vaga.
  3. Gerar uma carta de motivacao a partir da vaga (e de um curriculo
     de referencia opcional).

Regra critica: o conteudo enviado para avaliacao nunca e armazenado.
A camada de UI apenas coleta entradas, chama os servicos e exibe a saida.
"""

from __future__ import annotations

from typing import Callable, Optional

import streamlit as st

from database import crud
from database.models import TIPOS_DOCUMENTO
from services import ai_service, evaluation, template_generator

_TIPO_CURRICULO = "Currículo"


# ---------------------------------------------------------------------------
# Utilitarios
# ---------------------------------------------------------------------------


def _opcoes_vaga(incluir_nenhuma: bool = True) -> dict[str, Optional[int]]:
    opcoes: dict[str, Optional[int]] = {}
    if incluir_nenhuma:
        opcoes["Nenhuma"] = None
    for vaga in crud.list_vagas(ordenar_por_data=False):
        opcoes[f"{vaga['nome']} (#{vaga['id']})"] = vaga["id"]
    return opcoes


def _opcoes_documento(tipo: Optional[str] = None) -> dict[str, Optional[int]]:
    opcoes: dict[str, Optional[int]] = {"Nenhum": None}
    for doc in crud.list_documentos(tipo=tipo):
        opcoes[f"{doc['titulo']} ({doc['tipo']})"] = doc["id"]
    return opcoes


# ---------------------------------------------------------------------------
# Pagina
# ---------------------------------------------------------------------------


def render(navegar: Optional[Callable[[str], None]] = None) -> None:
    st.header("IA")

    if not ai_service.is_configured():
        st.warning(
            "A chave da API Gemini não está configurada. Defina GEMINI_API_KEY "
            "no arquivo .env ou na aba de Configurações para usar os recursos "
            "de IA."
        )

    st.caption(
        "O conteúdo enviado para avaliação ou geração não é armazenado no sistema."
    )

    aba_avaliar, aba_curriculo, aba_carta = st.tabs(
        ["Avaliar", "Template de currículo", "Carta de motivação"]
    )

    with aba_avaliar:
        _render_avaliacao()
    with aba_curriculo:
        _render_template_curriculo()
    with aba_carta:
        _render_carta_motivacao()


# ---------------------------------------------------------------------------
# 1. Avaliacao
# ---------------------------------------------------------------------------


def _render_avaliacao() -> None:
    st.subheader("Avaliar currículo ou carta")

    opcoes_vaga = _opcoes_vaga()
    vaga_rotulo = st.selectbox(
        "Vaga para contexto", list(opcoes_vaga.keys()), key="aval_vaga"
    )

    tipo = st.selectbox("Tipo do documento", TIPOS_DOCUMENTO, key="aval_tipo")

    # Carregar conteudo de um documento salvo (opcional) - apenas preenche o campo.
    opcoes_doc = _opcoes_documento()
    col1, col2 = st.columns([3, 1])
    doc_rotulo = col1.selectbox(
        "Carregar de um documento salvo (opcional)",
        list(opcoes_doc.keys()),
        key="aval_doc",
    )
    if col2.button("Carregar", key="aval_carregar"):
        doc_id = opcoes_doc[doc_rotulo]
        if doc_id is not None:
            documento = crud.get_documento(doc_id)
            st.session_state["aval_texto"] = documento.get("conteudo") if documento else ""
            st.rerun()

    texto = st.text_area(
        "Conteúdo a avaliar",
        height=240,
        key="aval_texto",
        placeholder="Cole aqui o currículo ou a carta a ser avaliada.",
    )

    configurado = ai_service.is_configured()
    if st.button("Avaliar", key="aval_botao", disabled=not configurado):
        if not texto or not texto.strip():
            st.error("Insira o conteúdo a ser avaliado.")
        else:
            _executar_avaliacao(texto, opcoes_vaga[vaga_rotulo], tipo)

    _mostrar_resultado_avaliacao()


def _executar_avaliacao(texto: str, vaga_id: Optional[int], tipo: str) -> None:
    vaga = crud.get_vaga(vaga_id) if vaga_id is not None else None
    try:
        with st.spinner("Avaliando..."):
            resultado = evaluation.avaliar(texto, vaga=vaga, tipo_documento=tipo)
        st.session_state["aval_resultado"] = resultado
    except ValueError as erro:
        st.error(str(erro))
    except ai_service.AIServiceError as erro:
        st.error(str(erro))


def _mostrar_resultado_avaliacao() -> None:
    resultado = st.session_state.get("aval_resultado")
    if not resultado:
        return

    st.divider()
    st.markdown("### Resultado da avaliação")

    if resultado["summary"]:
        st.markdown("**Resumo**")
        st.write(resultado["summary"])

    _render_lista("Pontos fortes", resultado["strengths"])
    _render_lista("Lacunas ou pontos a reforçar", resultado["gaps"])
    _render_lista("Elementos desnecessários", resultado["unnecessary_elements"])
    _render_lista("Recomendações", resultado["recommendations"])

    if resultado["observations"]:
        st.markdown("**Observações**")
        st.write(resultado["observations"])


def _render_lista(titulo: str, itens: list[str]) -> None:
    if not itens:
        return
    st.markdown(f"**{titulo}**")
    for item in itens:
        st.markdown(f"- {item}")


# ---------------------------------------------------------------------------
# 2. Template de curriculo
# ---------------------------------------------------------------------------


def _render_template_curriculo() -> None:
    st.subheader("Gerar introdução de currículo")

    opcoes_vaga = _opcoes_vaga(incluir_nenhuma=False)
    if not opcoes_vaga:
        st.info("Cadastre uma vaga para gerar o template.")
        return

    vaga_rotulo = st.selectbox(
        "Vaga", list(opcoes_vaga.keys()), key="cv_vaga"
    )

    configurado = ai_service.is_configured()
    if st.button("Gerar introdução", key="cv_botao", disabled=not configurado):
        vaga = crud.get_vaga(opcoes_vaga[vaga_rotulo])
        try:
            with st.spinner("Gerando..."):
                st.session_state["cv_template"] = (
                    template_generator.gerar_template_curriculo(vaga)
                )
            st.rerun()
        except (ValueError, ai_service.AIServiceError) as erro:
            st.error(str(erro))

    if st.session_state.get("cv_template"):
        st.text_area(
            "Template gerado (editável)",
            height=240,
            key="cv_template",
        )


# ---------------------------------------------------------------------------
# 3. Carta de motivacao
# ---------------------------------------------------------------------------


def _render_carta_motivacao() -> None:
    st.subheader("Gerar carta de motivação")

    opcoes_vaga = _opcoes_vaga(incluir_nenhuma=False)
    if not opcoes_vaga:
        st.info("Cadastre uma vaga para gerar a carta.")
        return

    vaga_rotulo = st.selectbox("Vaga", list(opcoes_vaga.keys()), key="carta_vaga")

    opcoes_cv = _opcoes_documento(tipo=_TIPO_CURRICULO)
    cv_rotulo = st.selectbox(
        "Currículo de referência (opcional)",
        list(opcoes_cv.keys()),
        key="carta_cv",
    )

    configurado = ai_service.is_configured()
    if st.button("Gerar carta", key="carta_botao", disabled=not configurado):
        vaga = crud.get_vaga(opcoes_vaga[vaga_rotulo])
        cv_id = opcoes_cv[cv_rotulo]
        curriculo_texto = None
        if cv_id is not None:
            documento = crud.get_documento(cv_id)
            curriculo_texto = documento.get("conteudo") if documento else None
        try:
            with st.spinner("Gerando..."):
                st.session_state["carta_template"] = (
                    template_generator.gerar_carta_motivacao(vaga, curriculo_texto)
                )
            st.rerun()
        except (ValueError, ai_service.AIServiceError) as erro:
            st.error(str(erro))

    if st.session_state.get("carta_template"):
        st.text_area(
            "Carta gerada (editável)",
            height=320,
            key="carta_template",
        )