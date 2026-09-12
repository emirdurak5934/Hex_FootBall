@echo off
setlocal
cd /d "%~dp0"

set "CODEX_GIT_ROOT=C:\Users\Emir\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git"
if exist "%CODEX_GIT_ROOT%\cmd\git.exe" (
    set "PATH=%CODEX_GIT_ROOT%\cmd;%CODEX_GIT_ROOT%\mingw64\bin;%PATH%"
    set "GIT_EXEC_PATH=%CODEX_GIT_ROOT%\mingw64\bin"
)

rem Bu depo Codex tarafindan olusturuldu. Yalniz bu script boyunca guvenli say.
set "SAFE_REPOSITORY=%CD:\=/%"
set "GIT_CONFIG_COUNT=1"
set "GIT_CONFIG_KEY_0=safe.directory"
set "GIT_CONFIG_VALUE_0=%SAFE_REPOSITORY%"

where git >nul 2>&1
if errorlevel 1 (
    echo GIT BULUNAMADI.
    echo Git for Windows kurulduktan sonra bu dosyayi tekrar calistirin:
    echo https://git-scm.com/download/win
    pause
    exit /b 1
)

echo EDYN Football GitHub ilk yukleme islemi
git --version
echo.

if not exist ".git" git init -b main
git branch -M main
git config user.name "Emir Durak"
git config user.email "emirdurak5934@users.noreply.github.com"
git config http.sslBackend openssl

git remote get-url origin >nul 2>&1
if errorlevel 1 (
    git remote add origin https://github.com/emirdurak5934/Hex_FootBall.git
) else (
    git remote set-url origin https://github.com/emirdurak5934/Hex_FootBall.git
)

git add --all
git diff --cached --quiet
if errorlevel 1 git commit -m "Initial EDYN Football mobile and server setup"

echo.
echo GitHub giris ekrani acilirsa emirdurak5934 hesabi ile giris yapin.
git push -u origin main

echo.
if errorlevel 1 (
    echo YUKLEME TAMAMLANAMADI. Yukaridaki hata metnini paylasin.
) else (
    echo YUKLEME BASARILI.
)
pause
