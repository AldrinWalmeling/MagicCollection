@echo off
title MagicCollection - Commit Git

echo ===============================
echo       MAGICCOLLECTION GIT COMMIT
echo ===============================
echo.

set /p msg=Mensagem do commit: 

echo.
echo Adicionando arquivos...
git add .

echo.
echo Criando commit...
git commit -m "%msg%"

echo.
echo Enviando para o GitHub...
git push

echo.
echo ===============================
echo         CONCLUIDO
echo ===============================
pause