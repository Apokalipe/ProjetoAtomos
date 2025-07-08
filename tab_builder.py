# tab_builder.py
# (As importações permanecem as mesmas da versão anterior)
import os
import threading
import multiprocessing
import numpy as np
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QPushButton, QListWidget,
                             QFileDialog, QMessageBox, QLineEdit, QLabel, QInputDialog,
                             QFrame, QPlainTextEdit, QSplitter, QSizePolicy, QCheckBox) # Adicionar QCheckBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QVector3D
from scipy.spatial.transform import Rotation as R
from scipy.spatial import cKDTree

import pyqtgraph as pg 
import pyqtgraph.opengl as gl
import qtawesome as qta

try:
    import xyz2graph
    XYZ2GRAPH_AVAILABLE = True
except ImportError:
    XYZ2GRAPH_AVAILABLE = False

from tab_viewer import ATOM_COLORS, ATOM_RADII

class SystemBuilderTab(QWidget):
    # __init__ e outras funções permanecem iguais...
    def __init__(self, parent=None):
        super().__init__(parent)
        self.molecules_to_pack = []
        self.generated_system = None
        self.atomic_masses = {'C': 12.011, 'H': 1.008, 'O': 15.999, 'N': 14.007, 'S': 32.06, 'Xx': 0.0}
        self.AVOGADRO = 6.02214076e23
        self.A3_to_L = 1e-27
        self._create_widgets()

    def _create_widgets(self):
        main_layout = QHBoxLayout(self)
        left_panel = QFrame(); left_panel.setObjectName("Card"); left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("<b>Moléculas (Clique Duplo para Editar)</b>"))
        self.mol_listbox = QListWidget(); self.mol_listbox.itemDoubleClicked.connect(self._edit_molecule_count); left_layout.addWidget(self.mol_listbox)
        
        mol_buttons_layout = QHBoxLayout()
        btn_from_file = QPushButton("De Arquivo...")
        btn_from_file.clicked.connect(self._add_molecule_from_file)
        btn_remove = QPushButton("Remover")
        btn_remove.clicked.connect(self._remove_molecule)
        
        mol_buttons_layout.addWidget(btn_from_file)
        mol_buttons_layout.addWidget(btn_remove)
        left_layout.addLayout(mol_buttons_layout)
        
        pack_frame = QFrame(); pack_layout = QVBoxLayout(pack_frame); pack_layout.setContentsMargins(0, 0, 0, 0)
        pack_layout.addWidget(QLabel("<b>Parâmetros de Empacotamento</b>")); box_grid = QGridLayout()
        self.box_x_edit = QLineEdit("50.0"); self.box_y_edit = QLineEdit("50.0"); self.box_z_edit = QLineEdit("50.0"); self.tolerance_edit = QLineEdit("2.0")
        box_grid.addWidget(QLabel("X (Å):"), 0, 0); box_grid.addWidget(self.box_x_edit, 0, 1); box_grid.addWidget(QLabel("Y (Å):"), 0, 2); box_grid.addWidget(self.box_y_edit, 0, 3)
        box_grid.addWidget(QLabel("Z (Å):"), 0, 4); box_grid.addWidget(self.box_z_edit, 0, 5); box_grid.addWidget(QLabel("Tolerância (Å):"), 1, 0); box_grid.addWidget(self.tolerance_edit, 1, 1, 1, 5)
        box_grid.setColumnStretch(1, 1); box_grid.setColumnStretch(3, 1); box_grid.setColumnStretch(5, 1); pack_layout.addLayout(box_grid); left_layout.addWidget(pack_frame)
        btn_generate = QPushButton("Gerar Sistema"); btn_generate.setObjectName("AccentButton"); btn_generate.clicked.connect(self._generate_system); left_layout.addWidget(btn_generate)
        
        save_buttons_layout = QHBoxLayout()
        self.save_xyz_button = QPushButton("Salvar .xyz")
        self.save_xyz_button.clicked.connect(self._save_xyz)
        self.save_data_button = QPushButton("Salvar .data")
        self.save_data_button.clicked.connect(self._save_data)
        
        save_buttons_layout.addWidget(self.save_xyz_button)
        save_buttons_layout.addWidget(self.save_data_button)
        left_layout.addLayout(save_buttons_layout)
        
        left_layout.addStretch()
        
        right_panel = QFrame(); right_panel.setObjectName("Card"); right_layout = QVBoxLayout(right_panel)
        splitter = QSplitter(Qt.Orientation.Vertical); viewer_container = QWidget(); viewer_container_layout = QHBoxLayout(viewer_container)
        viewer_container_layout.setContentsMargins(0, 0, 0, 0); viewer_container_layout.setSpacing(5)
        
        # --- CORREÇÃO: Layout de controles do visualizador ---
        controls_layout = QVBoxLayout()
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        btn_zoom_in = QPushButton(qta.icon('fa5s.search-plus'), "")
        btn_zoom_out = QPushButton(qta.icon('fa5s.search-minus'), "")
        btn_reset_view = QPushButton(qta.icon('fa5s.expand-arrows-alt'), "")
        
        btn_zoom_in.setToolTip("Aproximar")
        btn_zoom_out.setToolTip("Afastar")
        btn_reset_view.setToolTip("Resetar Câmera")
        
        btn_zoom_in.clicked.connect(lambda: self._zoom_camera(0.9))
        btn_zoom_out.clicked.connect(lambda: self._zoom_camera(1.1))
        btn_reset_view.clicked.connect(self._reset_camera)

        # --- NOVO: Checkbox para alternar a projeção ---
        self.projection_check = QCheckBox("Perspectiva")
        self.projection_check.setChecked(True) # Começa em modo perspectiva
        self.projection_check.stateChanged.connect(self._toggle_projection)
        self.projection_check.setToolTip("Alternar entre projeção em perspectiva e ortográfica")
        
        controls_layout.addWidget(btn_zoom_in)
        controls_layout.addWidget(btn_zoom_out)
        controls_layout.addWidget(btn_reset_view)
        controls_layout.addWidget(self.projection_check) # Adiciona o checkbox ao layout
        
        viewer_layout = QVBoxLayout(); self.viewer = gl.GLViewWidget(); self.viewer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.viewer.setMinimumSize(400, 400); self._reset_camera(); viewer_layout.addWidget(self.viewer)
        legend_caption_layout = QHBoxLayout(); self.legend_layout = QVBoxLayout(); self.system_caption = QLabel("Gere um sistema para visualizar"); self.system_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.system_caption.setStyleSheet("color: #A0A0A0; padding: 5px;"); legend_caption_layout.addLayout(self.legend_layout); legend_caption_layout.addWidget(self.system_caption, 1, Qt.AlignmentFlag.AlignCenter)
        viewer_layout.addLayout(legend_caption_layout); viewer_container_layout.addLayout(controls_layout); viewer_container_layout.addLayout(viewer_layout, 1)
        log_widget = QWidget(); log_layout = QVBoxLayout(log_widget); log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.addWidget(QLabel("<b>Status do Empacotamento</b>")); self.log_text = QPlainTextEdit(); self.log_text.setReadOnly(True); log_layout.addWidget(self.log_text)
        splitter.addWidget(viewer_container); splitter.addWidget(log_widget); splitter.setStretchFactor(0, 3); splitter.setStretchFactor(1, 1)
        right_layout.addWidget(splitter); main_layout.addWidget(left_panel, 1); main_layout.addWidget(right_panel, 2)
        self._update_button_states()
        self._toggle_projection() # Chama uma vez para definir o estado inicial

    # --- NOVO: Método para alternar a projeção da câmera ---
    def _toggle_projection(self):
        """Alterna a câmera entre perspectiva e ortográfica."""
        if self.projection_check.isChecked():
            # Modo Perspectiva: 'fov' > 0
            self.viewer.opts['fov'] = 60
        else:
            # Modo Ortográfico: 'fov' = 0
            self.viewer.opts['fov'] = 0
        self.viewer.update() # Aplica a mudança

    def _reset_camera(self):
        self.viewer.setCameraPosition(distance=40, elevation=20, azimuth=45)
        # Garante que a projeção seja resetada junto com a posição
        self._toggle_projection() 
        if self.generated_system and 'coords' in self.generated_system and len(self.generated_system['coords']) > 0:
            center_point = np.mean(self.generated_system['coords'], axis=0)
            self.viewer.opts['center'] = pg.Vector(center_point)
        else:
            self.viewer.opts['center'] = pg.Vector(0, 0, 0)
        self.viewer.update()

    # O resto da classe (zoom, find_bonds, draw_system, generate_system, etc.) permanece exatamente igual à versão anterior.
    # ...
    # ... (Cole aqui o restante dos métodos da classe SystemBuilderTab da resposta anterior)
    # ...
    def _zoom_camera(self, factor):
        self.viewer.setCameraPosition(distance=self.viewer.opts['distance'] * factor)

    def _find_bonds(self, coords, symbols):
        bonds = []; kdtree = cKDTree(coords); pairs = kdtree.query_pairs(r=2.2)
        for i, j in pairs:
            r_i = ATOM_RADII.get(symbols[i], 0.7); r_j = ATOM_RADII.get(symbols[j], 0.7); max_dist = (r_i + r_j) * 1.2
            if np.linalg.norm(coords[i] - coords[j]) <= max_dist: bonds.append((i, j))
        return bonds

    def _draw_generated_system(self, style='avogadro'):
        if not self.generated_system: return
        self.viewer.items.clear(); coords = self.generated_system['coords']; center_point = np.mean(coords, axis=0); self.viewer.opts['center'] = pg.Vector(center_point)
        if style == 'avogadro': self._draw_style_avogadro()
        else: self._log(f"Estilo '{style}' desconhecido.")
        self._draw_simulation_box(self.generated_system['box']); self._update_legend_and_caption(); QTimer.singleShot(50, self._reset_camera)

    def _draw_style_avogadro(self):
        coords = self.generated_system['coords']
        symbols = self.generated_system['symbols']
        atom_colors = np.array([ATOM_COLORS.get(s, ATOM_COLORS['Xx']) for s in symbols])
        atom_diameters = np.array([ATOM_RADII.get(s, 0.7) * 1.5 for s in symbols])

        # --- CORREÇÃO: Suprimir avisos de divisão por zero durante a renderização ---
        # O RuntimeWarning ocorre dentro do pyqtgraph quando o tamanho do pixel é 0
        # durante a inicialização. Este contexto ignora o aviso de forma segura.
        with np.errstate(divide='ignore'):
            spheres = gl.GLScatterPlotItem(pos=coords, size=atom_diameters, color=atom_colors, pxMode=False, glOptions='translucent')
            self.viewer.addItem(spheres)

        try:
            bonds = self._find_bonds(coords, symbols)
            if bonds:
                bond_positions = []
                [bond_positions.extend([coords[s], coords[e]]) for s, e in bonds]
                if bond_positions:
                    bond_lines = gl.GLLinePlotItem(pos=np.array(bond_positions), color=(0.7, 0.7, 0.7, 1.0), width=3, mode='lines', glOptions='opaque')
                    self.viewer.addItem(bond_lines)
        except Exception as e:
            self._log(f"Aviso: Falha na detecção de ligações: {e}")

    def _draw_simulation_box(self, box_dims):
        x, y, z = box_dims
        # Desenha a caixa na origem [0,0,0] para [x,y,z]
        verts = np.array([[0,0,0], [x,0,0], [x,y,0], [0,y,0], [0,0,z], [x,0,z], [x,y,z], [0,y,z]])
        edges = np.array([[0,1], [1,2], [2,3], [3,0], [4,5], [5,6], [6,7], [7,4], [0,4], [1,5], [2,6], [3,7]])
        box_lines_pos = []; [box_lines_pos.extend([verts[s], verts[e]]) for s, e in edges]
        box_item = gl.GLLinePlotItem(pos=np.array(box_lines_pos), color=(1,1,1,0.3), width=2, mode='lines', glOptions='translucent'); self.viewer.addItem(box_item)

    def _update_button_states(self):
        is_generated = self.generated_system is not None
        self.save_xyz_button.setEnabled(is_generated)
        self.save_data_button.setEnabled(is_generated)

    def _log(self, message):
        self.log_text.appendPlainText(message)
    
    def _generate_system(self):
        self.viewer.items.clear()
        try:
            box = np.array([float(self.box_x_edit.text()), float(self.box_y_edit.text()), float(self.box_z_edit.text())])
            tolerance = float(self.tolerance_edit.text())
        except ValueError:
            QMessageBox.critical(self, "Erro", "Dimensões da caixa e tolerância devem ser números válidos.")
            return
        if not self.molecules_to_pack:
            QMessageBox.warning(self, "Aviso", "Nenhuma molécula foi adicionada para empacotar.")
            return

        self._log("\nIniciando empacotamento...")
        
        unwrapped_coords_list = []
        wrapped_coords_list = []
        
        final_symbols = []
        final_mol_ids = []
        final_atom_types = []
        
        element_to_type_map = {}
        current_type_id = 1
        max_tries_per_mol = 1000
        mol_id_counter = 1

        for mol_data in self.molecules_to_pack:
            mol_name = mol_data['name']
            self._log(f"Empacotando {mol_data['count']}x {mol_name}...")
            
            for i in range(mol_data['count']):
                placed = False
                for attempt in range(max_tries_per_mol):
                    random_rotation = R.random()
                    rotated_coords = random_rotation.apply(mol_data['coords'])
                    offset = np.random.uniform(low=0.0, high=box)
                    candidate_coords_unwrapped = rotated_coords + offset

                    if not unwrapped_coords_list:
                        placed = True
                        break

                    candidate_coords_wrapped = candidate_coords_unwrapped % box

                    existing_coords_wrapped = np.array(wrapped_coords_list)
                    tree = cKDTree(existing_coords_wrapped, boxsize=box)
                    
                    clashing_indices = tree.query_ball_point(candidate_coords_wrapped, r=tolerance)
                    
                    if not any(clashing_indices):
                        placed = True
                        break
                
                if not placed:
                    self._log(f"ERRO: Falha ao posicionar a molécula {i+1} de {mol_name} após {max_tries_per_mol} tentativas.")
                    QMessageBox.critical(self, "Erro de Empacotamento", f"Não foi possível encontrar uma posição para a molécula {i+1} de {mol_name}. Tente aumentar o tamanho da caixa.")
                    return

                unwrapped_coords_list.extend(candidate_coords_unwrapped.tolist())
                wrapped_coords_list.extend((candidate_coords_unwrapped % box).tolist())
                
                final_symbols.extend(mol_data['symbols'])
                final_mol_ids.extend([mol_id_counter] * len(mol_data['symbols']))
                
                for symbol in mol_data['symbols']:
                    if symbol not in element_to_type_map:
                        element_to_type_map[symbol] = current_type_id
                        current_type_id += 1
                    final_atom_types.append(element_to_type_map[symbol])
                
                mol_id_counter += 1

        self.generated_system = {
            'symbols': np.array(final_symbols),
            'coords': np.array(unwrapped_coords_list),
            'mol_ids': np.array(final_mol_ids),
            'atom_types': np.array(final_atom_types),
            'element_map': element_to_type_map,
            'box': box
        }
        
        self._update_button_states()
        self._log(f"Sistema gerado com sucesso com {len(final_symbols)} átomos.")
        self._calculate_and_log_properties()
        self._draw_generated_system(style='avogadro')
    
    def _update_legend_and_caption(self):
        for i in reversed(range(self.legend_layout.count())):
            layout_item = self.legend_layout.itemAt(i)
            if layout_item.widget(): layout_item.widget().setParent(None)
            else:
                while layout_item.count():
                    child = layout_item.takeAt(0)
                    if child.widget(): child.widget().setParent(None)
        if not self.generated_system: return
        symbols = self.generated_system['symbols']; unique_symbols = sorted(list(set(symbols)))
        for symbol in unique_symbols:
            color = ATOM_COLORS.get(symbol, ATOM_COLORS['Xx']); rgba = f"rgba({int(color[0]*255)}, {int(color[1]*255)}, {int(color[2]*255)}, {color[3]})"
            legend_item_layout = QHBoxLayout(); color_label = QLabel(); color_label.setFixedSize(15, 15); color_label.setStyleSheet(f"background-color: {rgba}; border-radius: 7px;")
            symbol_label = QLabel(symbol); legend_item_layout.addWidget(color_label); legend_item_layout.addWidget(symbol_label); legend_item_layout.addStretch(); self.legend_layout.addLayout(legend_item_layout)
        total_atoms = len(symbols); caption = f"{total_atoms} átomos ({', '.join(unique_symbols)})"; self.system_caption.setText(caption)
        
    def _save_xyz(self):
        if not self.generated_system: return
        filepath, _ = QFileDialog.getSaveFileName(self, "Salvar sistema como XYZ", "", "XYZ files (*.xyz)")
        if not filepath: return
        symbols = self.generated_system['symbols']; coords = self.generated_system['coords']
        try:
            with open(filepath, 'w') as f: f.write(f"{len(symbols)}\n"); f.write("Sistema gerado pelo Analisador LAMMPS\n"); [f.write(f"{s: <4} {c[0]:>12.6f} {c[1]:>12.6f} {c[2]:>12.6f}\n") for s, c in zip(symbols, coords)]
            self._log(f"Sistema salvo em: {filepath}")
        except Exception as e: QMessageBox.critical(self, "Erro ao Salvar", f"Não foi possível salvar o arquivo:\n{e}")

    def _add_molecule_from_file(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Selecione o arquivo XYZ", "", "XYZ files (*.xyz);;All files (*.*)")
        if not filepath: return
        symbols, coords = self._read_xyz(filepath)
        if symbols is not None:
            new_molecule = {'path': filepath, 'name': os.path.basename(filepath), 'count': 1, 'symbols': symbols, 'coords': coords}
            self.molecules_to_pack.append(new_molecule); self._update_molecule_listbox(); self._log(f"Adicionado de arquivo: {os.path.basename(filepath)}")

    def _read_xyz(self, filepath):
        try:
            with open(filepath, 'r') as f: lines = f.readlines()
            num_atoms = int(lines[0].strip()); atom_lines = lines[2:2+num_atoms]; symbols, coords = [], []
            for line in atom_lines: parts = line.strip().split(); symbols.append(parts[0]); coords.append([float(p) for p in parts[1:4]])
            coords = np.array(coords); coords -= coords.mean(axis=0); return np.array(symbols), coords
        except Exception as e: QMessageBox.critical(self, "Erro de Leitura", f"Não foi possível ler o arquivo XYZ:\n{e}"); return None, None

    def _edit_molecule_count(self, item):
        index = self.mol_listbox.row(item)
        if index < 0 or index >= len(self.molecules_to_pack): return
        molecule_data = self.molecules_to_pack[index]
        new_count, ok = QInputDialog.getInt(self, "Editar Contagem", f"Nova quantidade para '{molecule_data['name']}':", value=molecule_data['count'], min=1)
        if ok: self.molecules_to_pack[index]['count'] = new_count; self._update_molecule_listbox(); self._log(f"Contagem de '{molecule_data['name']}' atualizada para {new_count}.")

    def _update_molecule_listbox(self):
        self.mol_listbox.clear();
        for mol in self.molecules_to_pack: self.mol_listbox.addItem(f"{mol['count']}x {mol['name']}")

    def _remove_molecule(self):
        selected_rows = [self.mol_listbox.row(item) for item in self.mol_listbox.selectedItems()]
        if not selected_rows: return
        for index in sorted(selected_rows, reverse=True): removed = self.molecules_to_pack.pop(index); self._log(f"Removido: {removed['name']}")
        self._update_molecule_listbox()

    def _calculate_and_log_properties(self):
        if not self.generated_system: return
        symbols = self.generated_system['symbols']; box = self.generated_system['box']; total_mass_amu = sum(self.atomic_masses.get(s, 0) for s in symbols); box_volume_a3 = box[0] * box[1] * box[2]
        if box_volume_a3 > 0:
            conversion_factor = 1.660539; density_g_cm3 = (total_mass_amu / box_volume_a3) * conversion_factor
            self._log("-" * 20); self._log(f"Volume da caixa: {box_volume_a3:.2f} Å³"); self._log(f"Massa total: {total_mass_amu:.2f} amu"); self._log(f"DENSIDADE TOTAL: {density_g_cm3:.4f} g/cm³"); self._log("-" * 20)
            self._log("Concentrações Molares:"); volume_L = box_volume_a3 * self.A3_to_L
            for mol_data in self.molecules_to_pack: num_molecules = mol_data['count']; mols = num_molecules / self.AVOGADRO; concentration_mol_L = mols / volume_L; mol_name = mol_data['name']; self._log(f"- {mol_name}: {concentration_mol_L:.4f} mol/L")
            self._log("-" * 20)
        self._log("Pronto para salvar ou visualizar.")

    def _save_data(self):
        if not self.generated_system: return
        filepath, _ = QFileDialog.getSaveFileName(self, "Salvar como arquivo de dados LAMMPS", "", "LAMMPS Data (*.data);;All files (*.*)")
        if not filepath: return
        sys_data = self.generated_system; num_atoms = len(sys_data['symbols']); num_atom_types = len(sys_data['element_map']); box = sys_data['box']
        try:
            with open(filepath, 'w') as f:
                f.write("LAMMPS data file from Analisador\n\n"); f.write(f"{num_atoms} atoms\n"); f.write(f"{num_atom_types} atom types\n\n"); f.write(f"0.0 {box[0]:.6f} xlo xhi\n"); f.write(f"0.0 {box[1]:.6f} ylo yhi\n"); f.write(f"0.0 {box[2]:.6f} zlo zhi\n\n"); f.write("Masses\n\n"); type_to_element_map = {v: k for k, v in sys_data['element_map'].items()}
                for type_id in sorted(type_to_element_map.keys()): element = type_to_element_map[type_id]; mass = self.atomic_masses.get(element, 0.0); f.write(f" {type_id} {mass:.4f} # {element}\n")
                f.write("\n"); f.write("Atoms # full\n\n")
                for i in range(num_atoms): atom_id = i + 1; mol_id = sys_data['mol_ids'][i]; atom_type = sys_data['atom_types'][i]; charge = 0.0; x, y, z = sys_data['coords'][i]; f.write(f"{atom_id} {mol_id} {atom_type} {charge:.4f} {x:.6f} {y:.6f} {z:.6f}\n")
            self._log(f"Arquivo de dados LAMMPS salvo em: {filepath}")
        except Exception as e: QMessageBox.critical(self, "Erro ao Salvar", f"Não foi possível salvar o arquivo .data:\n{e}")