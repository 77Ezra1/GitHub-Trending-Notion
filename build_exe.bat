@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ====================================
echo   GitHub Trending to Notion
echo   正在打包桌面客户端...
echo ====================================
echo.

REM 删除旧的构建文件
if exist "build" (
    echo 清理旧的构建文件...
    rmdir /s /q "build"
)
if exist "dist\desktop_client.exe" (
    echo 清理旧的 exe 文件...
    del /q "dist\desktop_client.exe"
)

echo.
echo 开始打包...
echo.

pyinstaller --noconfirm ^
    --onefile ^
    --windowed ^
    --name "GitHubTrendingToNotion" ^
    --icon=NONE ^
    --add-data "github_trending_notion.py;." ^
    --hidden-import=tkinter ^
    --hidden-import=customtkinter ^
    --hidden-import=requests ^
    --hidden-import=bs4 ^
    --hidden-import=difflib ^
    --collect-all customtkinter ^
    desktop_client.py

echo.
echo ====================================
if exist "dist\GitHubTrendingToNotion.exe" (
    echo 打包成功！
    echo.
    echo 输出文件: dist\GitHubTrendingToNotion.exe
    echo.
    echo 按任意键打开输出目录...
    pause >nul
    explorer "dist"
) else (
    echo 打包失败，请检查错误信息
    pause
)
