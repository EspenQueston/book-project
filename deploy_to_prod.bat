@echo off
REM =============================================================================
REM DEPLOY TO PRODUCTION — DUNO 360 (Windows)
REM =============================================================================
REM This script:
REM   1. Commits all changes locally
REM   2. Pushes to GitHub
REM   3. SSHs into the VPS, pulls, and restarts the service
REM =============================================================================

echo.
echo  ============================================================
echo   DUNO 360 — Deploy to Production
echo  ============================================================
echo.

REM ── STEP 1: Check git status ──────────────────────────────────────────────
echo [1/4] Checking git status...
git status --short

REM ── STEP 2: Add and commit ─────────────────────────────────────────────────
echo.
echo [2/4] Staging all changes...
git add -A

set /p COMMIT_MSG="Enter commit message (press Enter for auto-generated): "
if "%COMMIT_MSG%"=="" (
    for /f "tokens=2 delims==" %%a in ('wmic os get localdatetime /value') do set "dt=%%a"
    set "TIMESTAMP=%dt:~0,4%-%dt:~4,2%-%dt:~6,2% %dt:~8,2%:%dt:~10,2%"
    set COMMIT_MSG=update: mobile UI, checkout, translations (%TIMESTAMP%)
)

git commit -m "%COMMIT_MSG%"
echo [OK] Committed: %COMMIT_MSG%

REM ── STEP 3: Push to GitHub ─────────────────────────────────────────────────
echo.
echo [3/4] Pushing to GitHub...
git push origin main || git push origin master
echo [OK] Pushed to GitHub.

REM ── STEP 4: Deploy to VPS ──────────────────────────────────────────────────
echo.
echo [4/4] Deploying to VPS...

ssh root@ubuntu-s-2vcpu-4gb-120gb-intel-lon1 "bash -s" < deploy_vps_remote.sh

if errorlevel 1 (
    echo [ERROR] VPS deployment failed.
    echo.
    echo Make sure you have SSH access configured.
    echo You may need to run the VPS commands manually.
    pause
    exit /b 1
)

echo.
echo  ============================================================
echo   DEPLOYMENT COMPLETE!
echo  ============================================================
echo.
echo   GitHub:  https://github.com/EspenQueston/book-project
echo   Live:    https://duno360.com
echo.
pause
