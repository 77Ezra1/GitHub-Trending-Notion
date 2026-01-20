@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ====================================
echo   GitHub Trending to Notion
echo   桌面客户端启动中...
echo ====================================
echo.

python desktop_client.py

if errorlevel 1 (
    echo.
    echo 启动失败，请检查 Python 是否已安装
    pause
)
