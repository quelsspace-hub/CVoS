"""
tests/test_evaluation.py
Testes da avaliacao por IA, sem chamadas reais a rede.

A funcao ai_service.gerar_conteudo e substituida por um dublê (monkeypatch),
de modo que os testes validam apenas a logica de prompt/parse/normalizacao.

Execucao:
    pytest -q
"""

from __future__ import annotations

import json

import pytest

from services import ai_service, evaluation


def test_extrair_json_simples():
    assert evaluation._extrair_json('{"summary": "ok"}') == {"summary": "ok"}


def test_extrair_json_com_cercas_de_codigo():
    bruto = '```json\n{"summary": "ok", "strengths": ["a"]}\n```'
    assert evaluation._extrair_json(bruto) == {"summary": "ok", "strengths": ["a"]}


def test_extrair_json_com_texto_residual():
    bruto = 'Aqui está:\n{"summary": "ok"}\nObrigado.'
    assert evaluation._extrair_json(bruto) == {"summary": "ok"}


def test_normalizar_preenche_chaves_ausentes():
    resultado = evaluation._normalizar({"summary": "x"})
    for chave in evaluation.CHAVES_AVALIACAO:
        assert chave in resultado
    assert resultado["strengths"] == []
    assert resultado["observations"] == ""


def test_normalizar_converte_tipos():
    bruto = {
        "summary": "resumo",
        "strengths": ["a", "", "b"],
        "gaps": "uma lacuna",  # string vira lista de 1 item
        "recommendations": None,
    }
    resultado = evaluation._normalizar(bruto)
    assert resultado["strengths"] == ["a", "b"]
    assert resultado["gaps"] == ["uma lacuna"]
    assert resultado["recommendations"] == []


def test_avaliar_fluxo_completo(monkeypatch):
    resposta_falsa = json.dumps(
        {
            "summary": "Bom alinhamento",
            "strengths": ["Experiência em Python"],
            "gaps": ["Faltou mencionar testes"],
            "unnecessary_elements": [],
            "recommendations": ["Adicionar métricas"],
            "observations": "Estrutura clara",
        }
    )
    monkeypatch.setattr(ai_service, "gerar_conteudo", lambda *a, **k: resposta_falsa)

    resultado = evaluation.avaliar(
        "Currículo com experiência em Python",
        vaga={"nome": "Dev", "empresa": "ACME"},
        tipo_documento="Currículo",
    )
    assert resultado["summary"] == "Bom alinhamento"
    assert resultado["strengths"] == ["Experiência em Python"]
    assert resultado["recommendations"] == ["Adicionar métricas"]


def test_avaliar_documento_vazio():
    with pytest.raises(ValueError):
        evaluation.avaliar("   ")


def test_avaliar_json_invalido(monkeypatch):
    monkeypatch.setattr(ai_service, "gerar_conteudo", lambda *a, **k: "isto não é json")
    with pytest.raises(ai_service.AIServiceError):
        evaluation.avaliar("conteúdo", vaga={"nome": "Dev"})