@echo off
setlocal
chcp 65001 >nul

REM ============================================================
REM  Extraction de la structure XML (sans le texte)
REM  Aucune installation requise : un Python portable est
REM  telecharge une seule fois dans le dossier "python_portable".
REM
REM  Deposez vos .xml dans "depot", puis double-cliquez ici.
REM  Les resultats arrivent dans "sortie".
REM ============================================================

REM --- Dossiers (modifiables) ---
set "ENTREE=%~dp0depot"
set "SORTIE=%~dp0sortie"

REM --- Options (modifiables), a ajouter dans OPTIONS si besoin ---
REM  --garder-commentaires  conserve les commentaires
REM  --vider-attributs      garde les attributs, efface leurs valeurs
REM  --sans-attributs       supprime les attributs
REM  --chemins              ajoute la liste des chemins (.txt)
REM  --vider-dans A,B      efface les valeurs d'attributs dans les elements A, B
REM                        et tout ce qu'ils contiennent
set "OPTIONS=--vider-dans profileDesc"

REM --- Python portable ---
set "PY_VERSION=3.12.10"
set "PY_DIR=%~dp0python_portable"
set "PY_ZIP=%~dp0python-%PY_VERSION%-embed-amd64.zip"
set "PY_URL=https://www.python.org/ftp/python/%PY_VERSION%/python-%PY_VERSION%-embed-amd64.zip"
set "PY_EXE=%PY_DIR%\python.exe"

if not exist "%ENTREE%" mkdir "%ENTREE%"
if not exist "%SORTIE%" mkdir "%SORTIE%"

if exist "%PY_EXE%" goto :lancer

echo Premier lancement : installation d'un Python portable dans
echo   %PY_DIR%
echo (rien n'est installe sur le systeme)
echo.

if not exist "%PY_ZIP%" (
    echo Telechargement de Python %PY_VERSION% ...
    curl.exe -L --fail -o "%PY_ZIP%" "%PY_URL%" 2>nul
    if not exist "%PY_ZIP%" powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PY_ZIP%'"
)

if not exist "%PY_ZIP%" (
    echo.
    echo ERREUR : telechargement impossible ^(pas d'acces internet ou proxy^).
    echo Telechargez manuellement ce fichier depuis un autre poste :
    echo   %PY_URL%
    echo et placez-le a cote de ce .bat sans le decompresser, puis relancez.
    pause
    exit /b 1
)

echo Decompression ...
mkdir "%PY_DIR%" 2>nul
tar -xf "%PY_ZIP%" -C "%PY_DIR%" 2>nul
if not exist "%PY_EXE%" powershell -NoProfile -Command "Expand-Archive -Path '%PY_ZIP%' -DestinationPath '%PY_DIR%' -Force"

if not exist "%PY_EXE%" (
    echo ERREUR : la decompression a echoue.
    pause
    exit /b 1
)
del "%PY_ZIP%" 2>nul
echo Python portable pret.
echo.

:lancer
"%PY_EXE%" "%~dp0extraire_structure.py" "%ENTREE%" "%SORTIE%" %OPTIONS%

echo.
pause
