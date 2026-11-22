@echo off
chcp 65001 >nul
title Backup continuo do firmware WBRG1
python -u "%~dp0dump-continuous.py"
echo.
echo Processo encerrado. Consulte a mensagem acima.
pause
