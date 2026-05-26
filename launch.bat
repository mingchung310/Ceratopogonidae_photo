@echo off
cd /d "%~dp0"
echo 啟動本地伺服器 http://localhost:8080
echo 關閉此視窗即停止伺服器
start "" "http://localhost:8080"
python -m http.server 8080
