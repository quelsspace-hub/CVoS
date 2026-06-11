"""
services/cloud_providers.py
Abstracao de provedores de backup em nuvem.

Como o backup e um unico arquivo (zip do banco SQLite), cada provedor
precisa apenas saber enviar, listar e baixar arquivos. Isso mantem a
abstracao minima e permite adicionar novos provedores sem alterar o
backup_service.

Provedores implementados:
  - LocalFolderProvider: copia para uma pasta sincronizada por um cliente
    de desktop (Google Drive, Dropbox, OneDrive). Sem dependencia externa.
  - S3Provider: envia para um bucket Amazon S3 via boto3.

A escolha do provedor vem de config.BACKUP_PROVIDER.
"""

from __future__ import annotations

import abc
import shutil
from pathlib import Path
from typing import Optional

import config
from utils.logger import get_logger

logger = get_logger("services.cloud_providers")


class BackupError(Exception):
    """Erro durante operacoes de backup/restauracao."""


class CloudProvider(abc.ABC):
    """Contrato comum a todos os provedores de backup em nuvem."""

    nome_provedor: str = "desconhecido"

    @abc.abstractmethod
    def upload(self, caminho_local: Path) -> None:
        """Envia um arquivo de backup para o destino remoto."""

    @abc.abstractmethod
    def listar(self) -> list[str]:
        """Lista os nomes dos backups disponiveis no destino remoto."""

    @abc.abstractmethod
    def download(self, nome: str, destino: Path) -> None:
        """Baixa um backup remoto para o caminho de destino informado."""


class LocalFolderProvider(CloudProvider):
    """Backup para uma pasta sincronizada por um cliente de desktop."""

    nome_provedor = "Pasta sincronizada"

    def __init__(self) -> None:
        self.pasta = Path(config.BACKUP_SYNC_FOLDER)

    def upload(self, caminho_local: Path) -> None:
        self.pasta.mkdir(parents=True, exist_ok=True)
        shutil.copy2(caminho_local, self.pasta / Path(caminho_local).name)
        logger.info("Backup copiado para a pasta sincronizada: %s", self.pasta)

    def listar(self) -> list[str]:
        if not self.pasta.exists():
            return []
        return sorted((p.name for p in self.pasta.glob("*.zip")), reverse=True)

    def download(self, nome: str, destino: Path) -> None:
        origem = self.pasta / nome
        if not origem.exists():
            raise BackupError(f"Backup '{nome}' não encontrado na pasta sincronizada.")
        shutil.copy2(origem, destino)


class S3Provider(CloudProvider):
    """Backup para um bucket Amazon S3 (via boto3)."""

    nome_provedor = "Amazon S3"

    def __init__(self) -> None:
        if not config.S3_BUCKET:
            raise BackupError("S3_BUCKET não configurado.")

        try:
            import boto3
        except ImportError as exc:
            raise BackupError(
                "Pacote 'boto3' não instalado. Execute: pip install boto3"
            ) from exc

        parametros = {}
        if config.S3_REGION:
            parametros["region_name"] = config.S3_REGION

        try:
            self._s3 = boto3.client("s3", **parametros)
        except Exception as exc:
            raise BackupError(f"Falha ao inicializar o cliente S3: {exc}") from exc

        self.bucket = config.S3_BUCKET
        self.prefixo = config.S3_PREFIX or ""

    def _chave(self, nome: str) -> str:
        return f"{self.prefixo}{nome}"

    def upload(self, caminho_local: Path) -> None:
        nome = Path(caminho_local).name
        try:
            self._s3.upload_file(str(caminho_local), self.bucket, self._chave(nome))
        except Exception as exc:
            raise BackupError(f"Falha no upload para o S3: {exc}") from exc
        logger.info("Backup enviado ao S3: s3://%s/%s", self.bucket, self._chave(nome))

    def listar(self) -> list[str]:
        try:
            resposta = self._s3.list_objects_v2(Bucket=self.bucket, Prefix=self.prefixo)
        except Exception as exc:
            raise BackupError(f"Falha ao listar backups no S3: {exc}") from exc

        objetos = resposta.get("Contents", [])
        nomes = [Path(o["Key"]).name for o in objetos if o["Key"].endswith(".zip")]
        return sorted(nomes, reverse=True)

    def download(self, nome: str, destino: Path) -> None:
        try:
            self._s3.download_file(self.bucket, self._chave(nome), str(destino))
        except Exception as exc:
            raise BackupError(f"Falha no download do S3: {exc}") from exc


def obter_provedor() -> Optional[CloudProvider]:
    """
    Retorna a instancia do provedor configurado, ou None quando o backup
    em nuvem esta desativado (BACKUP_PROVIDER='none').
    """
    if config.BACKUP_PROVIDER == "local_folder":
        return LocalFolderProvider()
    if config.BACKUP_PROVIDER == "s3":
        return S3Provider()
    return None