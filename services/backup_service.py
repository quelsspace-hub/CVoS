"""
services/backup_service.py
Orquestracao de backup e restauracao do sistema.

O "backup" e um arquivo zip contendo o banco SQLite. O fluxo cobre:
  - criar backup local (com retencao dos N mais recentes);
  - enviar o backup ao provedor de nuvem configurado (se houver);
  - listar backups locais e da nuvem;
  - restaurar um backup local ou da nuvem, com copia de seguranca do
    banco atual antes de sobrescrever.

A aplicacao continua 100% funcional localmente; a nuvem e apenas um
destino de backup/restauracao seguro.
"""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

import config
from services import cloud_providers
from services.cloud_providers import BackupError
from utils.logger import get_logger

logger = get_logger("services.backup_service")

_PREFIXO = "central_de_vagas_backup_"
_PADRAO = f"{_PREFIXO}*.zip"


def _timestamp() -> str:
    # Inclui microssegundos para garantir nomes unicos mesmo em backups
    # criados dentro do mesmo segundo (ex.: backup automatico).
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def _descartar_conexoes() -> None:
    """
    Fecha as conexoes do banco antes de sobrescrever o arquivo.

    Necessario principalmente no Windows, que nao permite substituir um
    arquivo em uso. Feito de forma tolerante: se o engine ainda nao existir
    ou nao puder ser importado, segue sem erro.
    """
    try:
        from database.database import engine

        engine.dispose()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Criacao
# ---------------------------------------------------------------------------


def criar_backup(enviar_para_nuvem: bool = True) -> dict:
    """
    Cria um backup local do banco e, opcionalmente, o envia para a nuvem.

    Retorna um dicionario com 'nome', 'caminho_local' e 'nuvem' (nome do
    provedor para o qual foi enviado, ou None).
    """
    if not config.DB_PATH.exists():
        raise BackupError("Banco de dados não encontrado para backup.")

    config.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    nome = f"{_PREFIXO}{_timestamp()}.zip"
    destino = config.BACKUP_DIR / nome

    try:
        with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as arquivo_zip:
            arquivo_zip.write(config.DB_PATH, arcname=config.DB_FILENAME)
    except OSError as exc:
        raise BackupError(f"Falha ao criar o arquivo de backup: {exc}") from exc

    _aplicar_retencao_local()

    resultado = {"nome": nome, "caminho_local": str(destino), "nuvem": None}

    if enviar_para_nuvem:
        provedor = cloud_providers.obter_provedor()
        if provedor is not None:
            provedor.upload(destino)
            resultado["nuvem"] = provedor.nome_provedor

    logger.info("Backup criado: %s (nuvem=%s)", nome, resultado["nuvem"])
    return resultado


def _aplicar_retencao_local() -> None:
    """Mantem apenas os BACKUP_RETENTION backups locais mais recentes."""
    arquivos = sorted(
        config.BACKUP_DIR.glob(_PADRAO),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for antigo in arquivos[config.BACKUP_RETENTION :]:
        try:
            antigo.unlink()
        except OSError:
            logger.warning("Não foi possível remover backup antigo: %s", antigo)


# ---------------------------------------------------------------------------
# Listagem
# ---------------------------------------------------------------------------


def listar_backups_locais() -> list[dict]:
    """Lista os backups locais, do mais recente ao mais antigo."""
    if not config.BACKUP_DIR.exists():
        return []

    arquivos = sorted(
        config.BACKUP_DIR.glob(_PADRAO),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return [
        {
            "nome": arquivo.name,
            "caminho": str(arquivo),
            "tamanho": arquivo.stat().st_size,
            "data": datetime.fromtimestamp(arquivo.stat().st_mtime),
        }
        for arquivo in arquivos
    ]


def listar_backups_nuvem() -> list[str]:
    """Lista os backups disponiveis no provedor de nuvem configurado."""
    provedor = cloud_providers.obter_provedor()
    if provedor is None:
        raise BackupError("Nenhum provedor de nuvem configurado.")
    return provedor.listar()


# ---------------------------------------------------------------------------
# Restauracao
# ---------------------------------------------------------------------------


def restaurar(caminho_zip) -> None:
    """
    Restaura o banco a partir de um arquivo de backup local.

    Antes de sobrescrever, faz uma copia de seguranca do banco atual
    (arquivo .bak ao lado do banco).
    """
    caminho_zip = Path(caminho_zip)
    if not caminho_zip.exists():
        raise BackupError("Arquivo de backup não encontrado.")

    try:
        with zipfile.ZipFile(caminho_zip) as arquivo_zip:
            candidatos = [n for n in arquivo_zip.namelist() if n.endswith(".db")]
            if not candidatos:
                raise BackupError(
                    "Backup inválido: nenhum banco de dados encontrado no arquivo."
                )
            with tempfile.TemporaryDirectory() as temporario:
                extraido = Path(arquivo_zip.extract(candidatos[0], temporario))
                _substituir_banco(extraido)
    except zipfile.BadZipFile as exc:
        raise BackupError("Arquivo de backup corrompido ou inválido.") from exc

    logger.info("Backup restaurado de: %s", caminho_zip.name)


def restaurar_de_nuvem(nome: str) -> None:
    """Baixa um backup da nuvem e o restaura."""
    provedor = cloud_providers.obter_provedor()
    if provedor is None:
        raise BackupError("Nenhum provedor de nuvem configurado.")

    with tempfile.TemporaryDirectory() as temporario:
        destino = Path(temporario) / nome
        provedor.download(nome, destino)
        restaurar(destino)


def _substituir_banco(novo_db: Path) -> None:
    """Substitui o banco atual pelo conteudo restaurado, com seguranca."""
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)

    if config.DB_PATH.exists():
        seguranca = config.DB_PATH.with_suffix(config.DB_PATH.suffix + ".bak")
        try:
            shutil.copy2(config.DB_PATH, seguranca)
        except OSError:
            logger.warning("Não foi possível criar cópia de segurança do banco atual.")

    _descartar_conexoes()

    try:
        shutil.copy2(novo_db, config.DB_PATH)
    except OSError as exc:
        raise BackupError(f"Falha ao restaurar o banco de dados: {exc}") from exc