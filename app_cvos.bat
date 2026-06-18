@echo off
setlocal
REM ============================================================
REM  CVOS  -  Launcher padronizado (porta 8502, modo servico)
REM  Mesmo padrao do CaOS: venv isolado + guardas de robustez.
REM ============================================================
cd /d "%~dp0"
set "PORT=8502"
set "LOG=streamlit_%PORT%.log"

REM --- 1. Bootstrap do ambiente virtual (auto-cura se .venv sumir) ---
if not exist ".venv\Scripts\python.exe" (
    echo [CVOS] Ambiente virtual nao encontrado. Criando .venv...
    py -3.14 -m venv .venv
    if errorlevel 1 (
        echo [CVOS] ERRO ao criar o ambiente virtual. Instale o Python 3.14.
        pause
        exit /b 1
    )
    .venv\Scripts\python.exe -m pip install --upgrade pip
    .venv\Scripts\python.exe -m pip install -r requirements.txt
)

REM --- 2. Evita abrir uma segunda instancia na mesma porta ---
netstat -ano | findstr ":%PORT%" | findstr "LISTENING" >nul
if %errorlevel%==0 (
    echo [CVOS] Ja existe um servidor ativo na porta %PORT%. Abrindo no navegador...
    start "" "http://localhost:%PORT%"
    exit /b 0
)

REM --- 3. Sobe o Streamlit pelo Python do venv (modo servico: headless + log) ---
echo [CVOS] Iniciando em http://localhost:%PORT%  (log: %LOG%)
.venv\Scripts\python.exe -m streamlit run app.py --server.port=%PORT% --server.headless true > "%LOG%" 2>&1

REM --- 4. So chega aqui se o servidor encerrou/falhou: mantem o motivo visivel ---
echo.
echo [CVOS] O servidor foi encerrado. Verifique o log: %LOG%
pause
