@echo off
echo 启动生产服务器（需要SSL证书）...
echo 请确保SSL证书文件存在：
echo   - cert.pem
echo   - key.pem
echo.
python main.py --env server --port 8989 --host 0.0.0.0 --certfile cert.pem --keyfile key.pem
pause 