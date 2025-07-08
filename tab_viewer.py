# tab_viewer.py
import sys
from PyQt6.QtWidgets import QApplication
import pyqtgraph.opengl as gl
import numpy as np

try:
    import xyz2graph
    XYZ2GRAPH_AVAILABLE = True
except ImportError:
    XYZ2GRAPH_AVAILABLE = False

ATOM_COLORS = {
    'C': (0.5, 0.5, 0.5, 1.0),   # Cinza
    'H': (0.9, 0.9, 0.9, 1.0),   # Branco
    'O': (1.0, 0.1, 0.1, 1.0),   # Vermelho
    'N': (0.2, 0.2, 1.0, 1.0),   # Azul
    'S': (1.0, 1.0, 0.0, 1.0),   # Amarelo
    'Xx': (1.0, 0.0, 1.0, 1.0)   # Rosa (default)
}
ATOM_RADII = {'C': 0.76, 'H': 0.31, 'O': 0.66, 'N': 0.71, 'S': 1.05, 'Xx': 0.7}

def create_viewer_window(system_data, style):
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    view = gl.GLViewWidget()
    view.setWindowTitle('Visualizador 3D - PyQtGraph')
    view.setCameraPosition(distance=40)
    view.show()

    # Adiciona uma grade de referência
    grid = gl.GLGridItem()
    view.addItem(grid)

    coords = system_data['coords']
    symbols = system_data['symbols']
    
    # Detecção de ligações
    bonds = []
    if XYZ2GRAPH_AVAILABLE and style in ["Bolas e Varetas", "Varetas"]:
        try:
            xyz_data = list(zip(symbols, coords.tolist()))
            graph = xyz2graph.build_graph(xyz_data)
            bonds = list(graph.edges)
        except Exception as e:
            print(f"Aviso: xyz2graph falhou em detectar ligações: {e}")

    # Renderiza a cena de acordo com o estilo
    if style == "Bolas e Varetas":
        # Desenha ligações como cilindros
        if bonds:
            for start_idx, end_idx in bonds:
                p1 = coords[start_idx]
                p2 = coords[end_idx]
                tube = gl.GLLinePlotItem(pos=np.array([p1, p2]), color=(0.7, 0.7, 0.7, 1.0), width=3)
                view.addItem(tube)
        # Desenha átomos como esferas
        atom_colors = np.array([ATOM_COLORS.get(s, ATOM_COLORS['Xx']) for s in symbols])
        atom_sizes = np.array([ATOM_RADII.get(s, 0.7) * 0.6 for s in symbols])
        spheres = gl.GLScatterPlotItem(pos=coords, size=atom_sizes, color=atom_colors, pxMode=False)
        view.addItem(spheres)

    elif style == "Varetas":
        # Desenha apenas as ligações
        if bonds:
            for start_idx, end_idx in bonds:
                p1 = coords[start_idx]
                p2 = coords[end_idx]
                tube = gl.GLLinePlotItem(pos=np.array([p1, p2]), color=(0.7, 0.7, 0.7, 1.0), width=3)
                view.addItem(tube)

    elif style == "Esferas":
        # Desenha esferas com raio de van der Waals
        atom_colors = np.array([ATOM_COLORS.get(s, ATOM_COLORS['Xx']) for s in symbols])
        atom_sizes = np.array([ATOM_RADII.get(s, 0.7) * 1.8 for s in symbols]) # Raio vdW
        spheres = gl.GLScatterPlotItem(pos=coords, size=atom_sizes, color=atom_colors, pxMode=False)
        view.addItem(spheres)
    
    # Inicia o loop de eventos do PyQt
    app.exec()

if __name__ == '__main__':
    # Pequeno teste para rodar o visualizador de forma independente
    # Crie um arquivo 'test.xyz' para ver funcionando
    if os.path.exists('test.xyz'):
        with open('test.xyz', 'r') as f:
            lines = f.readlines()
            num_atoms = int(lines[0])
            atoms = lines[2:2+num_atoms]
            symbols = [line.split()[0] for line in atoms]
            coords = np.array([[float(x) for x in line.split()[1:4]] for line in atoms])
        
        test_data = {'symbols': symbols, 'coords': coords}
        create_viewer_window(test_data, "Bolas e Varetas")