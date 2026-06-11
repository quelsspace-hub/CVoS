"""
tests/test_backup.py
Testes do servico de backup com o provedor local_folder.

Usam apenas o sistema de arquivos (sem rede e sem boto3). Os caminhos do
config sao redirecionados para um diretorio temporario.

Execucao:
    pytest -q
"""

from __future__ import annotations

import pathlib

import pytest

import config
from services import backup_service, cloud_providers


@pytest.fixture()
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(config, "BACKUP_DIR", tmp_path / "backups")
    monkeypatch.setattr(config, "BACKUP_SYNC_FOLDER", tmp_path / "cloud")
    monkeypatch.setattr(config, "DB_FILENAME", "central_de_vagas.db")
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "data" / "central_de_vagas.db")
    monkeypatch.setattr(config, "BACKUP_PROVIDER", "local_folder")
    monkeypatch.setattr(config, "BACKUP_RETENTION", 3)

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.DB_PATH.write_bytes(b"VERSAO_ORIGINAL")
    yield tmp_path


def test_criar_backup_local_e_nuvem(ambiente):
    resultado = backup_service.criar_backup()
    assert resultado["nome"].endswith(".zip")
    assert resultado["nuvem"] == "Pasta sincronizada"
    assert len(backup_service.listar_backups_locais()) == 1
    assert resultado["nome"] in backup_service.listar_backups_nuvem()


def test_restaurar_local(ambiente):
    backup_service.criar_backup(enviar_para_nuvem=False)
    config.DB_PATH.write_bytes(b"ALTERADO")
    backup_service.restaurar(backup_service.listar_backups_locais()[0]["caminho"])
    assert config.DB_PATH.read_bytes() == b"VERSAO_ORIGINAL"
    bak = config.DB_PATH.with_suffix(config.DB_PATH.suffix + ".bak")
    assert bak.exists() and bak.read_bytes() == b"ALTERADO"


def test_restaurar_de_nuvem(ambiente):
    resultado = backup_service.criar_backup()
    config.DB_PATH.write_bytes(b"ALTERADO")
    backup_service.restaurar_de_nuvem(resultado["nome"])
    assert config.DB_PATH.read_bytes() == b"VERSAO_ORIGINAL"


def test_retencao_local(ambiente):
    for _ in range(6):
        backup_service.criar_backup(enviar_para_nuvem=False)
    assert len(backup_service.listar_backups_locais()) == config.BACKUP_RETENTION


def test_provedor_none(ambiente, monkeypatch):
    monkeypatch.setattr(config, "BACKUP_PROVIDER", "none")
    assert cloud_providers.obter_provedor() is None
    assert backup_service.criar_backup()["nuvem"] is None


def test_restaurar_arquivo_inexistente(ambiente):
    with pytest.raises(backup_service.BackupError):
        backup_service.restaurar(pathlib.Path("nao_existe.zip"))