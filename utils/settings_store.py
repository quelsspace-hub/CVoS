"""
utils/settings_store.py
Persistencia simples de preferencias da aplicacao.

Centraliza a escrita de configuracoes que precisam sobreviver a reinicios:
  - upsert de variaveis no arquivo .env do projeto (preservando comentarios);
  - alternancia do tema no .streamlit/config.toml.

Mantem a camada de UI livre de I/O de arquivo. Sem regra de negocio.
"""

from __future__ import annotations

import re
from pathlib import Path

import config


def caminho_env() -> Path:
    return config.BASE_DIR / ".env"


def salvar_no_env(updates: dict[str, str]) -> None:
    """
    Atualiza (ou insere) as variaveis informadas no arquivo .env e nos
    os.environ em memoria.

    Preserva linhas existentes, comentarios e ordem. Cria o arquivo caso
    ele ainda nao exista. Em ambientes de somente leitura (ex.: Streamlit
    Cloud), a escrita em arquivo falha silenciosamente, mas os valores
    continuam aplicados na sessao via os.environ.
    """
    if not updates:
        return

    # Aplica na sessao atual independente do arquivo.
    import os as _os
    for chave, valor in updates.items():
        _os.environ[chave] = valor

    caminho = caminho_env()
    linhas = caminho.read_text(encoding="utf-8").splitlines() if caminho.exists() else []

    restantes = dict(updates)
    resultado: list[str] = []
    for linha in linhas:
        limpa = linha.strip()
        if limpa and not limpa.startswith("#") and "=" in limpa:
            chave = limpa.split("=", 1)[0].strip()
            if chave in restantes:
                resultado.append(f"{chave}={restantes.pop(chave)}")
                continue
        resultado.append(linha)

    for chave, valor in restantes.items():
        resultado.append(f"{chave}={valor}")

    try:
        caminho.write_text("\n".join(resultado) + "\n", encoding="utf-8")
    except OSError:
        # Filesystem somente-leitura (ex.: Streamlit Cloud).
        # Os valores ja foram aplicados em os.environ acima.
        pass


def definir_tema(base: str) -> None:
    """
    Define o tema base ('light' ou 'dark') no .streamlit/config.toml.

    Atualiza a linha 'base = ...' se existir; caso contrario, adiciona a
    secao/linha necessaria. O efeito visual e aplicado ao reiniciar o app.
    """
    if base not in {"light", "dark"}:
        raise ValueError("Tema inválido. Use 'light' ou 'dark'.")

    caminho = config.BASE_DIR / ".streamlit" / "config.toml"
    caminho.parent.mkdir(parents=True, exist_ok=True)

    try:
        if not caminho.exists():
            caminho.write_text(f'[theme]\nbase = "{base}"\n', encoding="utf-8")
            return

        texto = caminho.read_text(encoding="utf-8")
        if re.search(r'base\s*=\s*".*?"', texto):
            texto = re.sub(r'base\s*=\s*".*?"', f'base = "{base}"', texto, count=1)
        elif "[theme]" in texto:
            texto = texto.replace("[theme]", f'[theme]\nbase = "{base}"', 1)
        else:
            texto = texto + f'\n[theme]\nbase = "{base}"\n'

        caminho.write_text(texto, encoding="utf-8")
    except OSError:
        # Filesystem somente-leitura (ex.: Streamlit Cloud); ignora silenciosamente.
        pass