# find_path.py
import os
import vtkmodules

try:
    # A maneira mais confiável é obter o diretório do próprio pacote VTK
    # O arquivo __file__ nos dá o caminho para o __init__.py do vtkmodules
    # E os DLLs geralmente estão no mesmo diretório ou em um subdiretório.
    vtk_path = os.path.dirname(vtkmodules.__file__)
    print(vtk_path)
except Exception as e:
    # Se falhar, imprime o erro para que possamos ver no CMD
    print(f"Erro ao tentar encontrar o caminho do VTK: {e}", file=os.sys.stderr)