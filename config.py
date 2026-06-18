"""
config.py
Configuracoes globais da Central de Vagas OS.

Centraliza, em um unico ponto, todos os parametros de ambiente: caminhos de
arquivos, chave da IA e ajustes de backup em nuvem. Nenhum valor sensivel e
escrito diretamente no codigo; tudo e lido de variaveis de ambiente (.env),
mantendo chaves e credenciais fora do repositorio.

Premissas do projeto: uso pessoal, execucao local, baixa manutencao.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Carregamento de configuracoes: .env local e, como fallback, st.secrets
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _load_streamlit_secrets() -> None:
    """
    Injeta os segredos do Streamlit Cloud nas variaveis de ambiente.

    No Streamlit Cloud nao ha arquivo .env; as chaves sao configuradas na
    interface da plataforma (Settings > Secrets) e ficam disponiveis via
    st.secrets. Esta funcao as copia para os.environ antes que os valores
    de configuracao sejam lidos, de modo que o restante do codigo nao
    precisa saber de onde o segredo veio.

    Valores ja presentes no ambiente (vindos do .env local) nao sao
    sobrescritos, garantindo que o ambiente local tenha precedencia.
    """
    try:
        import streamlit as st

        for chave, valor in st.secrets.items():
            if isinstance(valor, str) and not os.environ.get(chave):
                os.environ[chave] = valor
    except Exception:
        pass


_load_streamlit_secrets()


def _get_bool(name: str, default: bool = False) -> bool:
    """Le uma variavel de ambiente como booleano de forma tolerante."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "sim"}


def _get_int(name: str, default: int) -> int:
    """Le uma variavel de ambiente como inteiro, com fallback seguro."""
    value = os.getenv(name)
    if value is None or not value.strip().isdigit():
        return default
    return int(value)


def _get_path(name: str, default: Path) -> Path:
    """Le uma variavel de ambiente como caminho absoluto, com fallback."""
    value = os.getenv(name)
    return Path(value).expanduser().resolve() if value else default


# ---------------------------------------------------------------------------
# Diretorios base
# ---------------------------------------------------------------------------
DATA_DIR = _get_path("DATA_DIR", BASE_DIR / "data")
BACKUP_DIR = _get_path("BACKUP_DIR", BASE_DIR / "backups")
LOG_DIR = _get_path("LOG_DIR", BASE_DIR / "logs")

# ---------------------------------------------------------------------------
# Banco de dados (SQLite)
# ---------------------------------------------------------------------------
DB_FILENAME = os.getenv("DB_FILENAME", "central_de_vagas.db")
DB_PATH = DATA_DIR / DB_FILENAME
DATABASE_URL = f"sqlite:///{DB_PATH}"

# ---------------------------------------------------------------------------
# Integracao com IA (Gemini)
# O nome exato do pacote/modelo do Gemini sera confirmado na etapa de
# integracao de IA. Mantido configuravel para nao exigir alteracao de codigo.
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_TIMEOUT_SECONDS = _get_int("GEMINI_TIMEOUT_SECONDS", 60)

# ---------------------------------------------------------------------------
# Backup em nuvem
# Provedores suportados:
#   "none"          -> backup em nuvem desativado (apenas backup local manual)
#   "local_folder"  -> copia o backup para uma pasta sincronizada por um
#                      cliente de desktop (Google Drive, Dropbox, OneDrive)
#   "s3"            -> envio direto para Amazon S3 via boto3
# ---------------------------------------------------------------------------
BACKUP_PROVIDER = os.getenv("BACKUP_PROVIDER", "none").strip().lower()
BACKUP_AUTO_ENABLED = _get_bool("BACKUP_AUTO_ENABLED", False)
BACKUP_RETENTION = _get_int("BACKUP_RETENTION", 10)  # quantos backups manter

# Provedor local_folder
BACKUP_SYNC_FOLDER = _get_path("BACKUP_SYNC_FOLDER", BACKUP_DIR / "cloud")

# Provedor s3 (credenciais AWS vem do ambiente padrao do boto3:
# AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_REGION)
S3_BUCKET = os.getenv("S3_BUCKET", "")
S3_PREFIX = os.getenv("S3_PREFIX", "central_de_vagas/")
S3_REGION = os.getenv("AWS_REGION", "")

# ---------------------------------------------------------------------------
# Aplicacao / interface
# ---------------------------------------------------------------------------
APP_TITLE = os.getenv("APP_TITLE", "Central de Vagas OS")
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "pt-BR")
DEFAULT_THEME = os.getenv("DEFAULT_THEME", "light")

# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip().upper()
LOG_FILENAME = os.getenv("LOG_FILENAME", "central_de_vagas.log")
LOG_PATH = LOG_DIR / LOG_FILENAME


# ---------------------------------------------------------------------------
# Funcoes utilitarias de configuracao
# ---------------------------------------------------------------------------
def ensure_directories() -> None:
    """Garante a existencia dos diretorios essenciais da aplicacao."""
    for path in (DATA_DIR, BACKUP_DIR, LOG_DIR):
        path.mkdir(parents=True, exist_ok=True)
    if BACKUP_PROVIDER == "local_folder":
        BACKUP_SYNC_FOLDER.mkdir(parents=True, exist_ok=True)


def validate_config() -> list[str]:
    """
    Verifica a configuracao e retorna uma lista de avisos legiveis.

    Nao lanca excecao: o app deve abrir mesmo sem IA configurada, apenas
    sinalizando os recursos indisponiveis. A UI exibe esses avisos ao usuario.
    """
    warnings: list[str] = []

    if not GEMINI_API_KEY:
        warnings.append(
            "GEMINI_API_KEY nao definida; os recursos de IA ficarao indisponiveis."
        )

    if BACKUP_PROVIDER not in {"none", "local_folder", "s3"}:
        warnings.append(
            f"BACKUP_PROVIDER invalido: '{BACKUP_PROVIDER}'. "
            "Use 'none', 'local_folder' ou 's3'."
        )

    if BACKUP_PROVIDER == "s3" and not S3_BUCKET:
        warnings.append("BACKUP_PROVIDER=s3 mas S3_BUCKET nao foi definido.")

    return warnings


# Garante os diretorios assim que o modulo e importado.
ensure_directories()