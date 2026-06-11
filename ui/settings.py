"""
ui/settings.py
Aba de Configuracoes.

Secoes:
  - IA (Gemini): chave/modelo, aplicacao na sessao e persistencia no .env.
  - Interface: tema e idioma.
  - Backup e exportacao: download do banco, backup/restauracao (local e
    nuvem) e configuracao do provedor de nuvem.
  - Manutencao: limpeza de cache e dados temporarios.

A persistencia em arquivo fica no settings_store; a logica de backup no
backup_service. A UI apenas coleta entradas e dispara acoes.
"""

from __future__ import annotations

import os
from typing import Callable, Optional

import streamlit as st

import config
from services import ai_service, backup_service
from utils import settings_store


# ---------------------------------------------------------------------------
# Flash
# ---------------------------------------------------------------------------


def _flash(mensagem: str, tipo: str = "success") -> None:
    st.session_state["_flash_settings"] = (tipo, mensagem)


def _mostrar_flash() -> None:
    dados = st.session_state.pop("_flash_settings", None)
    if dados:
        tipo, mensagem = dados
        getattr(st, tipo, st.info)(mensagem)


# ---------------------------------------------------------------------------
# Pagina
# ---------------------------------------------------------------------------


def render(navegar: Optional[Callable[[str], None]] = None) -> None:
    st.header("Configurações")
    _mostrar_flash()

    _render_gemini()
    st.divider()
    _render_interface()
    st.divider()
    _render_backup()
    st.divider()
    _render_manutencao()


# ---------------------------------------------------------------------------
# IA (Gemini)
# ---------------------------------------------------------------------------


def _render_gemini() -> None:
    st.subheader("IA (Gemini)")

    status = "configurada" if ai_service.is_configured() else "não configurada"
    st.caption(f"Chave atual: {status}. Modelo atual: {config.GEMINI_MODEL}.")

    with st.form("form_gemini"):
        chave = st.text_input(
            "Chave da API Gemini",
            type="password",
            placeholder="Deixe em branco para manter a chave atual",
        )
        modelo = st.text_input("Modelo", value=config.GEMINI_MODEL)
        persistir = st.checkbox("Salvar no arquivo .env (persistente)", value=True)
        salvar = st.form_submit_button("Salvar e aplicar")

    if salvar:
        _aplicar_gemini(chave.strip(), modelo.strip(), persistir)

    if st.button("Testar conexão", disabled=not ai_service.is_configured()):
        _testar_conexao()


def _aplicar_gemini(chave: str, modelo: str, persistir: bool) -> None:
    updates: dict[str, str] = {}

    if chave:
        os.environ["GEMINI_API_KEY"] = chave
        config.GEMINI_API_KEY = chave
        updates["GEMINI_API_KEY"] = chave

    if modelo:
        os.environ["GEMINI_MODEL"] = modelo
        config.GEMINI_MODEL = modelo
        updates["GEMINI_MODEL"] = modelo

    ai_service.reset_client()

    if persistir and updates:
        try:
            settings_store.salvar_no_env(updates)
        except OSError as erro:
            st.error(f"Não foi possível salvar no .env: {erro}")
            return

    _flash("Configurações da IA aplicadas.")
    st.rerun()


def _testar_conexao() -> None:
    try:
        with st.spinner("Testando..."):
            ai_service.gerar_conteudo("Responda apenas: ok", temperatura=0.0)
        st.success("Conexão com o Gemini bem-sucedida.")
    except ai_service.AIServiceError as erro:
        st.error(str(erro))


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------


def _render_interface() -> None:
    st.subheader("Interface")

    temas = {"Claro": "light", "Escuro": "dark"}
    rotulo_atual = "Escuro" if config.DEFAULT_THEME == "dark" else "Claro"
    tema_rotulo = st.selectbox(
        "Tema", list(temas.keys()), index=list(temas).index(rotulo_atual)
    )

    idiomas = ["pt-BR", "en"]
    idioma_atual = config.DEFAULT_LANGUAGE if config.DEFAULT_LANGUAGE in idiomas else "pt-BR"
    idioma = st.selectbox("Idioma padrão", idiomas, index=idiomas.index(idioma_atual))

    if st.button("Salvar preferências de interface"):
        base = temas[tema_rotulo]
        try:
            settings_store.definir_tema(base)
            settings_store.salvar_no_env(
                {"DEFAULT_THEME": base, "DEFAULT_LANGUAGE": idioma}
            )
            config.DEFAULT_THEME = base
            config.DEFAULT_LANGUAGE = idioma
        except OSError as erro:
            st.error(f"Não foi possível salvar as preferências: {erro}")
            return
        _flash("Preferências salvas. Reinicie o app para aplicar o tema.")
        st.rerun()


# ---------------------------------------------------------------------------
# Backup e exportacao
# ---------------------------------------------------------------------------


def _render_backup() -> None:
    st.subheader("Backup e exportação")

    _render_exportacao()
    _render_backup_agora()
    _render_restauracao()
    _render_config_nuvem()


def _render_exportacao() -> None:
    st.markdown("**Exportar banco de dados**")
    if config.DB_PATH.exists():
        st.download_button(
            "Baixar banco de dados",
            data=config.DB_PATH.read_bytes(),
            file_name=config.DB_FILENAME,
            mime="application/octet-stream",
        )
    else:
        st.caption("O banco de dados ainda não foi criado.")


def _render_backup_agora() -> None:
    st.markdown("**Backup**")
    st.caption(f"Provedor de nuvem atual: {config.BACKUP_PROVIDER}.")

    if st.button("Fazer backup agora"):
        try:
            with st.spinner("Criando backup..."):
                resultado = backup_service.criar_backup()
            mensagem = f"Backup criado: {resultado['nome']}."
            if resultado["nuvem"]:
                mensagem += f" Enviado para: {resultado['nuvem']}."
            _flash(mensagem)
            st.rerun()
        except backup_service.BackupError as erro:
            st.error(str(erro))


def _render_restauracao() -> None:
    st.markdown("**Restaurar**")

    opcoes: dict[str, tuple[str, str]] = {}
    for backup in backup_service.listar_backups_locais():
        tamanho_kb = max(1, backup["tamanho"] // 1024)
        rotulo = f"{backup['nome']} — local ({tamanho_kb} KB)"
        opcoes[rotulo] = ("local", backup["caminho"])

    if config.BACKUP_PROVIDER != "none":
        if st.button("Listar backups da nuvem"):
            try:
                st.session_state["_backups_nuvem"] = backup_service.listar_backups_nuvem()
            except backup_service.BackupError as erro:
                st.error(str(erro))
        for nome in st.session_state.get("_backups_nuvem", []):
            opcoes[f"{nome} — nuvem"] = ("nuvem", nome)

    if not opcoes:
        st.caption("Nenhum backup disponível para restauração.")
        return

    escolha = st.selectbox("Backup para restaurar", list(opcoes.keys()), key="restore_sel")
    _render_confirmacao_restauracao(opcoes[escolha])


def _render_confirmacao_restauracao(origem: tuple[str, str]) -> None:
    tipo, referencia = origem
    chave = "_confirma_restore"

    if st.session_state.get(chave):
        st.warning(
            "Restaurar substitui o banco de dados atual. Uma cópia de "
            "segurança (.bak) será criada automaticamente. Confirmar?"
        )
        col1, col2 = st.columns(2)
        if col1.button("Confirmar restauração", key="conf_restore"):
            _executar_restauracao(tipo, referencia)
        if col2.button("Cancelar", key="canc_restore"):
            st.session_state.pop(chave, None)
            st.rerun()
    else:
        if st.button("Restaurar selecionado", key="btn_restore"):
            st.session_state[chave] = True
            st.rerun()


def _executar_restauracao(tipo: str, referencia: str) -> None:
    try:
        with st.spinner("Restaurando..."):
            if tipo == "local":
                backup_service.restaurar(referencia)
            else:
                backup_service.restaurar_de_nuvem(referencia)
        st.session_state.pop("_confirma_restore", None)
        st.session_state["_inicializado"] = False
        _flash("Backup restaurado.")
        st.rerun()
    except backup_service.BackupError as erro:
        st.session_state.pop("_confirma_restore", None)
        st.error(str(erro))


def _render_config_nuvem() -> None:
    st.markdown("**Configuração do backup em nuvem**")

    provedores = ["none", "local_folder", "s3"]
    indice = provedores.index(config.BACKUP_PROVIDER) if config.BACKUP_PROVIDER in provedores else 0

    provedor = st.selectbox("Provedor", provedores, index=indice)
    auto = st.checkbox("Backup automático", value=config.BACKUP_AUTO_ENABLED)
    sync_folder = st.text_input(
        "Pasta sincronizada (provedor local_folder)",
        value=str(config.BACKUP_SYNC_FOLDER),
    )
    s3_bucket = st.text_input("Bucket S3 (provedor s3)", value=config.S3_BUCKET)

    if st.button("Salvar configuração de backup"):
        try:
            settings_store.salvar_no_env(
                {
                    "BACKUP_PROVIDER": provedor,
                    "BACKUP_AUTO_ENABLED": "true" if auto else "false",
                    "BACKUP_SYNC_FOLDER": sync_folder.strip(),
                    "S3_BUCKET": s3_bucket.strip(),
                }
            )
        except OSError as erro:
            st.error(f"Não foi possível salvar a configuração: {erro}")
            return
        _flash("Configuração de backup salva. Reinicie o app para aplicar.")
        st.rerun()


# ---------------------------------------------------------------------------
# Manutencao
# ---------------------------------------------------------------------------


def _render_manutencao() -> None:
    st.subheader("Manutenção")
    st.caption(
        "Limpa o cache do Streamlit e os dados temporários da sessão (como "
        "avaliações e templates gerados, que nunca são armazenados)."
    )

    if st.button("Limpar cache e dados temporários"):
        st.cache_data.clear()
        st.cache_resource.clear()
        for chave in (
            "aval_resultado",
            "aval_texto",
            "cv_template",
            "carta_template",
            "_backups_nuvem",
        ):
            st.session_state.pop(chave, None)
        _flash("Cache e dados temporários limpos.")
        st.rerun()