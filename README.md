# Central de Vagas OS

Sistema pessoal para organizar candidaturas de emprego: cadastro e
acompanhamento de vagas, armazenamento de currículos e cartas de motivação,
e uso de IA (Gemini) sob demanda para avaliar documentos e gerar templates.

Projeto monousuário, de execução local. Sem autenticação, sem multiusuário,
sem servidor web separado. O conteúdo enviado para a IA nunca é armazenado.

## Stack

- Python
- Streamlit (interface)
- SQLite (banco de dados)
- SQLAlchemy (ORM)
- Gemini via SDK google-genai (IA)
- Arquitetura monolítica modular

## Estrutura de pastas

```
central_de_vagas_os/
├── app.py                      Ponto de entrada Streamlit (roteamento, init, backup automático)
├── config.py                   Configurações globais (env, paths, IA, backup)
├── requirements.txt
├── .env.example                Modelo de variáveis de ambiente
├── .streamlit/config.toml      Tema da interface
│
├── database/
│   ├── database.py             Engine e sessão SQLite
│   ├── models.py               Tabelas: vagas, documentos, historico_status
│   └── crud.py                 Operações de dados (com logging)
│
├── services/
│   ├── ai_service.py           Comunicação com o Gemini
│   ├── evaluation.py           Avaliação de CV/carta (saída estruturada)
│   ├── template_generator.py   Geração de templates de CV e carta
│   ├── backup_service.py       Backup e restauração
│   └── cloud_providers.py      Provedores de nuvem (local_folder, s3)
│
├── ui/
│   ├── home.py                 Página inicial
│   ├── vagas.py                Aba de vagas
│   ├── armazenamento.py        Aba de armazenamento
│   ├── ia.py                   Aba de IA
│   └── settings.py             Configurações
│
├── utils/
│   ├── helpers.py              Funções auxiliares (datas, URLs, tags, prompts)
│   ├── logger.py               Logging com rotação
│   └── settings_store.py       Persistência de preferências (.env, tema)
│
└── tests/                      Testes unitários (pytest)
```

## Instalação

No Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
copy .env.example .env
```

No Linux/Mac:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Depois, edite o arquivo `.env`.

## Configuração

Principais variáveis do `.env`:

- `GEMINI_API_KEY`: chave da API Gemini (obrigatória para recursos de IA).
- `GEMINI_MODEL`: modelo usado (padrão `gemini-2.5-flash`).
- `BACKUP_PROVIDER`: `none`, `local_folder` ou `s3`.
- `BACKUP_AUTO_ENABLED`: `true` para backup automático na inicialização.

A chave e o modelo também podem ser definidos pela aba de Configurações, que
salva no `.env`. O app abre normalmente mesmo sem `GEMINI_API_KEY`; apenas os
recursos de IA ficam indisponíveis até a chave ser configurada.

## Execução

```bash
streamlit run app.py
```

Rode sempre a partir da raiz do projeto (a pasta `central_de_vagas_os`).

## Backup e restauração

O backup é um arquivo zip contendo o banco SQLite. Tudo funciona localmente;
a nuvem é apenas um destino de backup seguro.

Provedores de nuvem:

- `local_folder`: aponte `BACKUP_SYNC_FOLDER` para uma pasta sincronizada pelo
  cliente de desktop do Google Drive, Dropbox ou OneDrive. O backup é copiado
  para lá e o cliente faz a sincronização. Não exige credenciais no app.
- `s3`: defina `S3_BUCKET` e as credenciais AWS padrão (`AWS_ACCESS_KEY_ID`,
  `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`). Requer o pacote `boto3`.

Pela aba de Configurações é possível:

- exportar (baixar) o banco de dados diretamente;
- fazer backup manual a qualquer momento;
- listar e restaurar backups locais ou da nuvem;
- configurar o provedor e o backup automático.

Ao restaurar, o banco atual é preservado em um arquivo `.bak` antes de ser
substituído. Os backups locais são mantidos até o limite de `BACKUP_RETENTION`.

## Testes

```bash
pytest -q
```

Os testes cobrem o CRUD, as funções auxiliares, a avaliação por IA (com dublê,
sem chamadas de rede) e o ciclo de backup/restauração com o provedor
`local_folder`.

## Privacidade

- A chave da API fica em variável de ambiente, fora do versionamento.
- O conteúdo enviado para avaliação ou geração pela IA não é armazenado.
- O banco é local; o backup em nuvem é controlado pelo usuário.