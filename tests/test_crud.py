"""
tests/test_crud.py
Testes unitarios da camada de acesso a dados (CRUD).

Cada teste roda contra um banco SQLite temporario e isolado, recriado
do zero pela fixture. Nao tocam no banco real da aplicacao.

Execucao:
    pytest -q
"""

from __future__ import annotations

import os
import tempfile

import pytest

from database import crud, database


@pytest.fixture()
def db():
    """Cria um banco temporario, recria as tabelas e limpa ao final."""
    fd, caminho = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database.configure_engine(f"sqlite:///{caminho}")
    database.init_db()
    try:
        yield
    finally:
        database.engine.dispose()
        os.remove(caminho)


# ---------------------------------------------------------------------------
# Vagas
# ---------------------------------------------------------------------------


def test_create_e_get_vaga(db):
    vaga = crud.create_vaga(nome="Dev Python", empresa="ACME")
    assert vaga["id"] is not None
    assert vaga["nome"] == "Dev Python"
    assert vaga["status"] == "Interessado"  # status padrao

    obtida = crud.get_vaga(vaga["id"])
    assert obtida is not None
    assert obtida["empresa"] == "ACME"


def test_create_vaga_registra_historico_inicial(db):
    vaga = crud.create_vaga(nome="Dev", status="Inscrito")
    historico = crud.get_historico_vaga(vaga["id"])
    assert len(historico) == 1
    assert historico[0]["status"] == "Inscrito"


def test_create_vaga_nome_obrigatorio(db):
    with pytest.raises(ValueError):
        crud.create_vaga(nome="   ")


def test_create_vaga_status_invalido(db):
    with pytest.raises(ValueError):
        crud.create_vaga(nome="Dev", status="StatusInexistente")


def test_update_status_atualiza_e_registra_historico(db):
    vaga = crud.create_vaga(nome="Dev")
    crud.update_status_vaga(vaga["id"], "Inscrito")
    crud.update_status_vaga(vaga["id"], "Entrevista agendada")

    atual = crud.get_vaga(vaga["id"])
    assert atual["status"] == "Entrevista agendada"

    historico = crud.get_historico_vaga(vaga["id"])
    assert [h["status"] for h in historico] == [
        "Interessado",
        "Inscrito",
        "Entrevista agendada",
    ]


def test_update_status_igual_e_no_op(db):
    vaga = crud.create_vaga(nome="Dev", status="Inscrito")
    crud.update_status_vaga(vaga["id"], "Inscrito")
    historico = crud.get_historico_vaga(vaga["id"])
    assert len(historico) == 1  # nao duplicou


def test_update_vaga_nao_aceita_status(db):
    vaga = crud.create_vaga(nome="Dev")
    with pytest.raises(ValueError):
        crud.update_vaga(vaga["id"], status="Inscrito")


def test_update_vaga_campos(db):
    vaga = crud.create_vaga(nome="Dev")
    atualizada = crud.update_vaga(vaga["id"], empresa="NovaEmpresa", link="http://x")
    assert atualizada["empresa"] == "NovaEmpresa"
    assert atualizada["link"] == "http://x"


def test_list_vagas_filtro_status_e_busca(db):
    crud.create_vaga(nome="Dev Python", empresa="ACME", status="Inscrito")
    crud.create_vaga(nome="Designer", empresa="Globex", status="Interessado")

    inscritos = crud.list_vagas(status="Inscrito")
    assert len(inscritos) == 1
    assert inscritos[0]["nome"] == "Dev Python"

    busca = crud.list_vagas(busca="globex")
    assert len(busca) == 1
    assert busca[0]["nome"] == "Designer"


def test_contar_vagas_por_status(db):
    crud.create_vaga(nome="A", status="Inscrito")
    crud.create_vaga(nome="B", status="Inscrito")
    crud.create_vaga(nome="C", status="Interessado")

    contagem = crud.contar_vagas_por_status()
    assert contagem["Inscrito"] == 2
    assert contagem["Interessado"] == 1
    assert contagem["Convocado"] == 0  # status sem vagas aparece como zero


def test_delete_vaga_cascata_historico_e_desvincula_documento(db):
    vaga = crud.create_vaga(nome="Dev")
    doc = crud.create_documento(
        titulo="CV", tipo="Currículo", conteudo="...", vaga_id=vaga["id"]
    )

    assert crud.delete_vaga(vaga["id"]) is True
    assert crud.get_vaga(vaga["id"]) is None

    # documento continua existindo, mas sem vinculo com a vaga
    doc_atual = crud.get_documento(doc["id"])
    assert doc_atual is not None
    assert doc_atual["vaga_id"] is None


def test_delete_vaga_inexistente(db):
    assert crud.delete_vaga(9999) is False


# ---------------------------------------------------------------------------
# Documentos
# ---------------------------------------------------------------------------


def test_create_documento(db):
    doc = crud.create_documento(
        titulo="CV Backend",
        tipo="Currículo",
        conteudo="Experiencia em Python",
        area="Tecnologia",
        tags=["python", "backend"],
    )
    assert doc["id"] is not None
    assert doc["tipo"] == "Currículo"
    assert doc["tags"] == "python, backend"


def test_create_documento_tipo_invalido(db):
    with pytest.raises(ValueError):
        crud.create_documento(titulo="X", tipo="Outro")


def test_create_documento_vaga_inexistente(db):
    with pytest.raises(ValueError):
        crud.create_documento(titulo="X", tipo="Currículo", vaga_id=12345)


def test_list_documentos_filtros(db):
    crud.create_documento(titulo="CV A", tipo="Currículo", area="Dados")
    crud.create_documento(
        titulo="Carta B", tipo="Carta de Motivação", area="Marketing"
    )

    curriculos = crud.list_documentos(tipo="Currículo")
    assert len(curriculos) == 1
    assert curriculos[0]["titulo"] == "CV A"

    por_area = crud.list_documentos(area="market")
    assert len(por_area) == 1
    assert por_area[0]["titulo"] == "Carta B"


def test_update_documento(db):
    doc = crud.create_documento(titulo="CV", tipo="Currículo")
    atualizado = crud.update_documento(
        doc["id"], titulo="CV v2", tags="a, b", conteudo="novo"
    )
    assert atualizado["titulo"] == "CV v2"
    assert atualizado["tags"] == "a, b"
    assert atualizado["conteudo"] == "novo"


def test_delete_documento(db):
    doc = crud.create_documento(titulo="CV", tipo="Currículo")
    assert crud.delete_documento(doc["id"]) is True
    assert crud.get_documento(doc["id"]) is None
    assert crud.delete_documento(doc["id"]) is False