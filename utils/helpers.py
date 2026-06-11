"""
utils/helpers.py
Funcoes auxiliares puras, reutilizaveis por toda a aplicacao.

Sem efeitos colaterais e sem dependencia de banco ou de servicos:
apenas formatacao, validacao e normalizacao de dados.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional
from urllib.parse import urlparse

_FMT_DATA_HORA = "%d/%m/%Y %H:%M"
_FMT_DATA = "%d/%m/%Y"


# ---------------------------------------------------------------------------
# Datas
# ---------------------------------------------------------------------------


def formatar_data_hora(dt: Optional[datetime], padrao: str = "-") -> str:
    """Formata um datetime como 'dd/mm/aaaa HH:MM' (pt-BR)."""
    if not isinstance(dt, datetime):
        return padrao
    return dt.strftime(_FMT_DATA_HORA)


def formatar_data(dt: Optional[datetime], padrao: str = "-") -> str:
    """Formata um datetime como 'dd/mm/aaaa' (pt-BR)."""
    if not isinstance(dt, datetime):
        return padrao
    return dt.strftime(_FMT_DATA)


def tempo_relativo(dt: Optional[datetime], padrao: str = "-") -> str:
    """
    Descreve, em pt-BR, ha quanto tempo um datetime ocorreu.

    Ex.: 'agora há pouco', 'há 5 minutos', 'há 3 horas', 'há 2 dias'.
    Para datas com mais de 30 dias, devolve a data formatada.
    """
    if not isinstance(dt, datetime):
        return padrao

    segundos = int((datetime.now() - dt).total_seconds())
    if segundos < 0:
        return formatar_data_hora(dt)
    if segundos < 60:
        return "agora há pouco"

    minutos = segundos // 60
    if minutos < 60:
        return f"há {minutos} {pluralizar(minutos, 'minuto')}"

    horas = minutos // 60
    if horas < 24:
        return f"há {horas} {pluralizar(horas, 'hora')}"

    dias = horas // 24
    if dias < 30:
        return f"há {dias} {pluralizar(dias, 'dia')}"

    return formatar_data(dt)


def pluralizar(quantidade: int, singular: str, plural: Optional[str] = None) -> str:
    """Devolve a forma singular ou plural conforme a quantidade."""
    plural = plural or f"{singular}s"
    return singular if quantidade == 1 else plural


# ---------------------------------------------------------------------------
# Texto
# ---------------------------------------------------------------------------


def truncar(texto: Optional[str], limite: int = 120, sufixo: str = "...") -> str:
    """Trunca um texto longo, anexando um sufixo quando cortado."""
    if texto is None:
        return ""
    texto = str(texto).strip()
    if len(texto) <= limite:
        return texto
    corte = max(0, limite - len(sufixo))
    return texto[:corte].rstrip() + sufixo


# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------


def validar_url(url: Optional[str]) -> bool:
    """Valida se a string e uma URL http(s) com dominio."""
    if not url or not str(url).strip():
        return False
    analisada = urlparse(str(url).strip())
    return analisada.scheme in {"http", "https"} and bool(analisada.netloc)


def normalizar_url(url: Optional[str]) -> Optional[str]:
    """Normaliza uma URL, prefixando 'https://' quando faltar esquema."""
    if not url or not str(url).strip():
        return None
    url = str(url).strip()
    if not urlparse(url).scheme:
        url = f"https://{url}"
    return url


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------


def normalizar_tags(tags) -> Optional[str]:
    """
    Normaliza tags para o formato de armazenamento 'a, b, c'.

    Aceita lista/tupla ou string separada por virgulas. Remove vazios e
    espacos extras. Devolve None se nao restar nenhuma tag.
    """
    if tags is None:
        return None
    if isinstance(tags, (list, tuple)):
        itens = [str(t).strip() for t in tags if str(t).strip()]
    else:
        itens = [t.strip() for t in str(tags).split(",") if t.strip()]
    return ", ".join(itens) if itens else None


def tags_para_lista(tags: Optional[str]) -> list[str]:
    """Converte a string de tags armazenada em uma lista de strings."""
    if not tags:
        return []
    return [t.strip() for t in str(tags).split(",") if t.strip()]


# ---------------------------------------------------------------------------
# Formatacao de contexto para prompts de IA
# ---------------------------------------------------------------------------


def formatar_vaga_para_prompt(vaga: Optional[dict]) -> str:
    """
    Converte um dicionario de vaga em um bloco de texto legivel para
    ser inserido em prompts de IA. Funcao pura, reutilizada pelos
    servicos de avaliacao e de geracao de templates.
    """
    if not vaga:
        return "(sem vaga selecionada)"

    campos = (
        ("Nome", vaga.get("nome")),
        ("Empresa", vaga.get("empresa")),
        ("Função principal", vaga.get("funcao_principal")),
        ("Status", vaga.get("status")),
        ("Descrição", vaga.get("descricao")),
    )
    partes = [f"{rotulo}: {valor}" for rotulo, valor in campos if valor]
    return "\n".join(partes) if partes else "(dados da vaga incompletos)"