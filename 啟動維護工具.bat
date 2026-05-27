@echo off
cd /d "%~dp0"
python maintenance_tool.py
if errorlevel 1 (
    echo.
    echo [錯誤] 請確認已安裝 Python 與 Pillow
    echo        pip install pillow
    pause
)
