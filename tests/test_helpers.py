"""
tests/test_helpers.py
Testes unitarios das funcoes auxiliares (utils/helpers.py).

Nao dependem de banco nem de rede; usam apenas a biblioteca padrao.

Execucao:
    pytest -q
"""

from __future__ import annotations

from datetime import datetime, timedelta

from utils import helpers


# ---------------------------------------------------------------------------
# Datas
# ---------------------------------------------------------------------------


def test_formatar_data_hora():
    dt = datetime(2025, 3, 7, 14, 30)
    assert helpers.formatar_data_hora(dt) == "07/03/2025 14:30"


def test_formatar_data():
    dt = datetime(2025, 3, 7, 14, 30)
    assert helpers.formatar_data(dt) == "07/03/2025"


def test_formatar_data_invalida_usa_padrao():
    assert helpers.formatar_data(None) == "-"
    assert helpers.formatar_data("texto") == "-"


def test_tempo_relativo_agora():
    assert helpers.tempo_relativo(datetime.now()) == "agora há pouco"


def test_tempo_relativo_minutos_e_horas():
    assert helpers.tempo_relativo(datetime.now() - timedelta(minutes=5)) == "há 5 minutos"
    assert helpers.tempo_relativo(datetime.now() - timedelta(minutes=1, seconds=5)) == "há 1 minuto"
    assert helpers.tempo_relativo(datetime.now() - timedelta(hours=3)) == "há 3 horas"


def test_tempo_relativo_dias():
    assert helpers.tempo_relativo(datetime.now() - timedelta(days=2)) == "há 2 dias"
    assert helpers.tempo_relativo(datetime.now() - timedelta(days=1, hours=1)) == "há 1 dia"


def test_pluralizar():
    assert helpers.pluralizar(1, "dia") == "dia"
    assert helpers.pluralizar(2, "dia") == "dias"
    assert helpers.pluralizar(0, "hora") == "horas"


# ---------------------------------------------------------------------------
# Texto
# ---------------------------------------------------------------------------


def test_truncar():
    assert helpers.truncar("abc", 10) == "abc"
    assert helpers.truncar("a" * 200, 10) == "aaaaaaa..."
    assert helpers.truncar(None) == ""


# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------


def test_validar_url():
    assert helpers.validar_url("https://exemplo.com") is True
    assert helpers.validar_url("http://exemplo.com/x") is True
    assert helpers.validar_url("exemplo.com") is False
    assert helpers.validar_url("") is False
    assert helpers.validar_url(None) is False


def test_normalizar_url():
    assert helpers.normalizar_url("exemplo.com") == "https://exemplo.com"
    assert helpers.normalizar_url("https://x.com") == "https://x.com"
    assert helpers.normalizar_url("  ") is None
    assert helpers.normalizar_url(None) is None


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------


def test_normalizar_tags():
    assert helpers.normalizar_tags(["a", " b ", ""]) == "a, b"
    assert helpers.normalizar_tags("x, y ,, z") == "x, y, z"
    assert helpers.normalizar_tags([]) is None
    assert helpers.normalizar_tags(None) is None


def test_tags_para_lista():
    assert helpers.tags_para_lista("a, b, c") == ["a", "b", "c"]
    assert helpers.tags_para_lista("") == []
    assert helpers.tags_para_lista(None) == []