@echo off
setlocal
chcp 65001 >nul
title Squelette XML - interface

REM ============================================================
REM  Lance l'interface Streamlit dans le navigateur.
REM  Aucune installation : l'outil "uv" (un seul .exe) est
REM  telecharge dans le dossier "outils", et il y installe
REM  lui-meme Python et Streamlit. Rien n'est ecrit ailleurs.
REM  Premier lancement : quelques minutes (~300 Mo telecharges).
REM  Pour arreter : fermez cette fenetre.
REM ============================================================

set "OUTILS=%~dp0outils"
set "UV=%OUTILS%\uv.exe"
set "UV_ZIP=%OUTILS%\uv.zip"
set "UV_URL=https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip"
set "PORT=8501"

REM Tout reste dans le dossier "outils" (Python, Streamlit, cache)
set "UV_CACHE_DIR=%OUTILS%\cache"
set "UV_PYTHON_INSTALL_DIR=%OUTILS%\python"
set "UV_PYTHON_PREFERENCE=only-managed"

if not exist "%OUTILS%" mkdir "%OUTILS%"
if not exist "%~dp0depot" mkdir "%~dp0depot"

if exist "%UV%" goto :lancer

echo Premier lancement : telechargement de l'outil uv ...
curl.exe -L --fail -o "%UV_ZIP%" "%UV_URL%" 2>nul
if not exist "%UV_ZIP%" powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -Uri '%UV_URL%' -OutFile '%UV_ZIP%'"
if not exist "%UV_ZIP%" (
    echo.
    echo ERREUR : telechargement impossible ^(pas d'acces internet ou proxy^).
    echo Adresse du fichier : %UV_URL%
    pause
    exit /b 1
)
tar -xf "%UV_ZIP%" -C "%OUTILS%" 2>nul
if not exist "%UV%" powershell -NoProfile -Command "Expand-Archive -Path '%UV_ZIP%' -DestinationPath '%OUTILS%' -Force"
del "%UV_ZIP%" 2>nul
if not exist "%UV%" (
    echo ERREUR : la decompression de uv a echoue.
    pause
    exit /b 1
)

:lancer
echo.
echo Demarrage de l'interface (le premier lancement installe Python et Streamlit) ...
echo Le navigateur s'ouvrira tout seul sur http://localhost:%PORT%
echo Pour arreter : fermez cette fenetre.
echo.

REM Ouvre le navigateur des que le serveur repond
start "" /min powershell -NoProfile -WindowStyle Hidden -Command "for($i=0;$i -lt 900;$i++){try{Invoke-WebRequest -UseBasicParsing 'http://localhost:%PORT%/_stcore/health' -TimeoutSec 2 | Out-Null; Start-Process 'http://localhost:%PORT%'; break}catch{Start-Sleep 1}}"

"%UV%" run --no-project --python 3.12 --with "streamlit>=1.45" ^
    streamlit run "%~dp0app_streamlit.py" ^
    --server.headless true --server.port %PORT% --browser.gatherUsageStats false

echo.
echo L'interface s'est arretee.
pause
