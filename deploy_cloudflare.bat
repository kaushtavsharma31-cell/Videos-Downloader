@echo off
echo ===================================================
echo      CLOUDFLARE WORKERS DEPLOYMENT HELPER
echo ===================================================
echo.
echo Step 1: Preparing static assets (running prepare_public.py)...
.venv\Scripts\python.exe prepare_public.py
if %ERRORLEVEL% neq 0 (
    echo Error preparing public directory. Make sure .venv is installed.
    pause
    exit /b %ERRORLEVEL%
)
echo.
echo Step 2: Logging in to Cloudflare...
echo A browser window will open. Please authenticate Wrangler in the browser.
call npx wrangler login
echo.
echo Step 3: Deploying Worker and Assets to Cloudflare...
call npx wrangler deploy
echo.
echo ===================================================
echo Cloudflare Workers Deployment Completed!
echo ===================================================
pause
