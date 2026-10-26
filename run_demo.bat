@echo off
rem ============================================================
rem  I-589 PDF Bot — arranque de un clic
rem  1. Crea el entorno virtual (la primera vez)
rem  2. Instala dependencias
rem  3. Verifica pdftk y el formulario
rem  4. Abre el navegador y levanta el servidor
rem ============================================================
cd /d "%~dp0"

if not exist .venv (
    echo Creando entorno virtual...
    python -m venv .venv
    .venv\Scripts\python -m pip install --upgrade pip
    .venv\Scripts\python -m pip install -r requirements.txt
) else (
    .venv\Scripts\python -m pip install -q -r requirements.txt
)

echo.
echo Verificando entorno...
.venv\Scripts\python scripts\setup.py
if errorlevel 1 (
    echo.
    pause
    exit /b 1
)

echo.
echo Abriendo http://127.0.0.1:8000 ...
start "" http://127.0.0.1:8000
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

pause
