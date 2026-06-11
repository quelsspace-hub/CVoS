"""
app.py
Ponto de entrada da Central de Vagas OS (Streamlit).

Responsabilidades:
  - Configurar a pagina e inicializar o banco de dados.
  - Executar backup automatico na inicializacao, quando habilitado.
  - Renderizar a sidebar estilizada (ui/sidebar.py) com o menu de navegacao.
  - Exibir avisos de configuracao (ex.: chave Gemini ausente).
  - Oferecer redirecionamento seguro usado pelos atalhos da pagina inicial.

Nao contem regra de negocio: apenas orquestra as paginas da pasta ui/.

Execucao:
    streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

import config
from database.database import init_db
from services import backup_service
from ui import armazenamento, home, ia, settings, sidebar, vagas
from utils.logger import get_logger

logger = get_logger("app")

# Mapeia o nome exibido no menu para a funcao de renderizacao da pagina.
PAGINAS = {
    "Início": home.render,
    "Vagas": vagas.render,
    "Armazenamento": armazenamento.render,
    "IA": ia.render,
    "Configurações": settings.render,
}


def _inicializar() -> None:
    """Inicializa o banco e executa o backup automatico uma vez por sessao."""
    if st.session_state.get("_inicializado"):
        return
    init_db()
    _backup_automatico()
    st.session_state["_inicializado"] = True
    logger.info("Aplicação inicializada.")


def _backup_automatico() -> None:
    """
    Cria um backup na inicializacao quando BACKUP_AUTO_ENABLED estiver ativo.

    Falhas nunca interrompem a abertura do app: sao apenas registradas em log.
    """
    if not config.BACKUP_AUTO_ENABLED or not config.DB_PATH.exists():
        return
    try:
        resultado = backup_service.criar_backup()
        logger.info("Backup automático na inicialização: %s", resultado["nome"])
    except backup_service.BackupError as erro:
        logger.warning("Backup automático falhou: %s", erro)


def navegar_para(pagina: str) -> None:
    """
    Solicita a troca de pagina de forma segura.

    Guarda o destino em uma chave auxiliar e reinicia o run; o destino e
    aplicado no inicio do proximo run, antes do menu ser criado, evitando
    o erro de alterar a chave de um widget ja instanciado.
    """
    st.session_state["_redirect"] = pagina
    st.rerun()


def main() -> None:
    st.set_page_config(page_title=config.APP_TITLE, layout="wide")
    _inicializar()

    # Aplica redirecionamento solicitado por atalhos antes de criar o menu.
    if "_redirect" in st.session_state:
        st.session_state["pagina"] = st.session_state.pop("_redirect")
    st.session_state.setdefault("pagina", "Início")

    avisos = config.validate_config()
    sidebar.render(list(PAGINAS.keys()), avisos)

    pagina_atual = st.session_state["pagina"]
    PAGINAS[pagina_atual](navegar_para)


main()