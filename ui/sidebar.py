"""
ui/sidebar.py
Barra lateral estilizada da Central de Vagas OS.

Mantem a navegacao baseada em st.radio (preservando a logica existente de
key='pagina' e o redirecionamento por atalhos), mas reestiliza tudo via CSS:
  - a sidebar vira um card flutuante claro com cantos arredondados;
  - no topo, um cartao de perfil com avatar e nome/funcao;
  - os circulos do radio sao ocultados e cada item ganha um icone (Lucide,
    SVG inline) a esquerda;
  - o item selecionado recebe fundo azul claro e uma barra azul na borda
    direita, indicando o estado ativo.

Sem regra de negocio: apenas apresentacao. Os icones sao ligados aos itens
pela ordem (nth-of-type), entao a ordem de ORDEM_PAGINAS deve coincidir com
a ordem do menu.
"""

from __future__ import annotations

from urllib.parse import quote

import streamlit as st

# Ordem dos itens do menu (deve casar com a ordem passada ao st.radio).
ORDEM_PAGINAS = ["Início", "Vagas", "Armazenamento", "IA", "Configurações"]

_TRACO = "#475569"  # cor dos icones do menu
_AZUL = "#2F80ED"   # acento azul do estado ativo

# Icones Lucide (SVG inline). stroke fixo para uso como background-image.
_ICONES = {
    "Início": (
        "<svg xmlns='http://www.w3.org/2000/svg' width='18' height='18' "
        "viewBox='0 0 24 24' fill='none' stroke='%s' stroke-width='2' "
        "stroke-linecap='round' stroke-linejoin='round'>"
        "<path d='m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z'/>"
        "<polyline points='9 22 9 12 15 12 15 22'/></svg>"
    ),
    "Vagas": (
        "<svg xmlns='http://www.w3.org/2000/svg' width='18' height='18' "
        "viewBox='0 0 24 24' fill='none' stroke='%s' stroke-width='2' "
        "stroke-linecap='round' stroke-linejoin='round'>"
        "<rect width='20' height='14' x='2' y='7' rx='2'/>"
        "<path d='M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16'/></svg>"
    ),
    "Armazenamento": (
        "<svg xmlns='http://www.w3.org/2000/svg' width='18' height='18' "
        "viewBox='0 0 24 24' fill='none' stroke='%s' stroke-width='2' "
        "stroke-linecap='round' stroke-linejoin='round'>"
        "<rect width='20' height='5' x='2' y='3' rx='1'/>"
        "<path d='M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8'/>"
        "<path d='M10 12h4'/></svg>"
    ),
    "IA": (
        "<svg xmlns='http://www.w3.org/2000/svg' width='18' height='18' "
        "viewBox='0 0 24 24' fill='none' stroke='%s' stroke-width='2' "
        "stroke-linecap='round' stroke-linejoin='round'>"
        "<path d='M12 8V4H8'/><rect width='16' height='12' x='4' y='8' rx='2'/>"
        "<path d='M2 14h2'/><path d='M20 14h2'/>"
        "<path d='M15 13v2'/><path d='M9 13v2'/></svg>"
    ),
    "Configurações": (
        "<svg xmlns='http://www.w3.org/2000/svg' width='18' height='18' "
        "viewBox='0 0 24 24' fill='none' stroke='%s' stroke-width='2' "
        "stroke-linecap='round' stroke-linejoin='round'>"
        "<circle cx='12' cy='12' r='3'/>"
        "<path d='M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83"
        "l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1"
        "-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 "
        "1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3"
        "a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06"
        "-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 "
        "0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82"
        "-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65"
        " 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z'/></svg>"
    ),
}

# Avatar do cartao de perfil (icone de usuario).
_AVATAR_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' width='22' height='22' "
    "viewBox='0 0 24 24' fill='none' stroke='%s' stroke-width='2' "
    "stroke-linecap='round' stroke-linejoin='round'>"
    "<path d='M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2'/>"
    "<circle cx='12' cy='7' r='4'/></svg>" % _AZUL
)


def _data_uri(svg: str) -> str:
    return "data:image/svg+xml," + quote(svg)


def _css_icones() -> str:
    regras = []
    for posicao, nome in enumerate(ORDEM_PAGINAS, start=1):
        uri = _data_uri(_ICONES[nome] % _TRACO)
        regras.append(
            f'section[data-testid="stSidebar"] div[role="radiogroup"] '
            f'label:nth-of-type({posicao})::before{{background-image:url("{uri}");}}'
        )
    return "\n".join(regras)


_CSS_BASE = """
/* Sidebar como card flutuante */
section[data-testid="stSidebar"] {
    background: #EDEFEE;
}
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"],
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    background: #FFFFFF;
    border-radius: 18px;
    margin: 10px;
    padding: 16px 14px;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.06);
    border: 1px solid #E7EAE9;
}

/* Marca e cartao de perfil */
.cv-brand {
    font-size: 0.70rem;
    letter-spacing: 0.10em;
    text-transform: uppercase;
    color: #8A938F;
    padding: 2px 4px 12px;
}
.cv-profile {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 0 4px 14px;
    margin-bottom: 10px;
    border-bottom: 1px solid #EEF1F0;
}
.cv-avatar {
    width: 42px;
    height: 42px;
    border-radius: 50%;
    background: #DCEAF7;
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 auto;
}
.cv-profile-text strong {
    display: block;
    font-size: 0.95rem;
    color: #1E2424;
    line-height: 1.2;
}
.cv-profile-text span {
    font-size: 0.78rem;
    color: #6B7775;
}

/* Menu: itens como linhas, sem os circulos do radio */
section[data-testid="stSidebar"] div[role="radiogroup"] {
    gap: 4px;
}
section[data-testid="stSidebar"] div[role="radiogroup"] label {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    margin: 0;
    padding: 10px 12px;
    border-radius: 12px;
    cursor: pointer;
    border-right: 4px solid transparent;
    transition: background 0.15s ease;
}
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
    background: #F3F6F5;
}
/* Oculta o circulo do radio (controle) e o input */
section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-of-type {
    display: none !important;
}
section[data-testid="stSidebar"] div[role="radiogroup"] input {
    display: none !important;
}
/* Espaco do icone (preenchido por nth-of-type) */
section[data-testid="stSidebar"] div[role="radiogroup"] label::before {
    content: "";
    width: 18px;
    height: 18px;
    flex: 0 0 auto;
    background-repeat: no-repeat;
    background-position: center;
    background-size: 18px 18px;
}
/* Estado ativo: fundo azul claro + barra azul a direita */
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
    background: #EAF2FD;
    border-right: 4px solid #2F80ED;
    font-weight: 600;
}
"""


def _html_perfil(nome: str, funcao: str) -> str:
    return (
        '<div class="cv-brand">Central de Vagas OS</div>'
        '<div class="cv-profile">'
        f'<div class="cv-avatar">{_AVATAR_SVG}</div>'
        f'<div class="cv-profile-text"><strong>{nome}</strong>'
        f'<span>{funcao}</span></div>'
        "</div>"
    )


def render(paginas: list[str], avisos: list[str]) -> None:
    """
    Renderiza a sidebar estilizada e o menu de navegacao.

    O st.radio continua usando key='pagina', mantendo intacta a logica de
    navegacao e o redirecionamento por atalhos definidos no app.py.
    """
    with st.sidebar:
        st.markdown(
            f"<style>{_CSS_BASE}{_css_icones()}</style>",
            unsafe_allow_html=True,
        )
        st.markdown(
            _html_perfil("Usuário", "Candidato"),
            unsafe_allow_html=True,
        )
        st.radio(
            "Navegação",
            paginas,
            key="pagina",
            label_visibility="collapsed",
        )
        for aviso in avisos:
            st.warning(aviso)