@echo off
echo Configurando o ambiente para PyVista/VTK...

REM --- IMPORTANTE: COLOQUE O CAMINHO QUE O 'python find_path.py' IMPRIMIU AQUI ---
SET "VTK_PATH=C:\Users\redno\AppData\Local\Programs\Python\Python310\Lib\site-packages\vtkmodules"

REM Verifica se o caminho definido existe
IF NOT EXIST "%VTK_PATH%" (
    echo.
    echo ERRO: O caminho para as bibliotecas VTK nao foi encontrado!
    echo Verifique o caminho definido na variavel VTK_PATH dentro deste script.
    echo Caminho procurado: %VTK_PATH%
    pause
    exit /b
)

echo Caminho VTK definido como: %VTK_PATH%
REM Adiciona o caminho das DLLs do VTK ao PATH do sistema
SET "PATH=%VTK_PATH%;%PATH%"

echo.
echo Iniciando o Analisador Multifuncional...
python main.py

echo.
echo Programa finalizado. Pressione qualquer tecla para sair.
pause