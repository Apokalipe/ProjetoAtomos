# tab_analysis.py
import numpy as np
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, 
                             QCheckBox, QLabel, QFileDialog, QMessageBox, QFrame,
                             QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt

import matplotlib
matplotlib.use('Qt5Agg') # Matplotlib backend para PyQt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from scipy.stats import linregress
from scipy.spatial import cKDTree
from scipy.signal import find_peaks

class MplCanvas(FigureCanvas):
    """Widget de canvas do Matplotlib para integrar com PyQt."""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor="#2c2e3a")
        self.axes = self.fig.add_subplot(111)
        self._style_plot("Gráfico", "X", "Y") # Estilo inicial
        super().__init__(self.fig)

    def _style_plot(self, title, xlabel, ylabel):
        self.axes.clear()
        self.axes.set_facecolor("#2c2e3a")
        self.axes.set_title(title, color="#e0e0e0", fontsize=12, weight='bold')
        self.axes.set_xlabel(xlabel, color="#b0b0b0")
        self.axes.set_ylabel(ylabel, color="#b0b0b0")
        for spine in self.axes.spines.values():
            spine.set_color("#555")
        self.axes.tick_params(axis='x', colors="#e0e0e0")
        self.axes.tick_params(axis='y', colors="#e0e0e0")
        self.axes.grid(True, linestyle='--', alpha=0.2, color="#777")
        self.fig.tight_layout()


class AnalysisTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.frames = []
        self.box_dims = None
        self.unique_elements = []
        self.rdf_data = {}
        
        self._create_widgets()

    def _create_widgets(self):
        main_layout = QVBoxLayout(self)

        # Barra de ferramentas superior
        top_toolbar = QHBoxLayout()
        btn_load = QPushButton("Carregar Trajetória (dump.lammpstrj)")
        btn_load.clicked.connect(self._load_trajectory)
        top_toolbar.addWidget(btn_load)
        top_toolbar.addStretch()
        main_layout.addLayout(top_toolbar)

        # --- CORREÇÃO APLICADA AQUI: Widgets são criados antes de serem usados ---
        self.rdf_canvas = MplCanvas(self, width=5, height=4, dpi=100)
        self.msd_canvas = MplCanvas(self, width=5, height=4, dpi=100)
        self.peak_table = QTableWidget(4, 2)
        # --- FIM DA CORREÇÃO ---
        
        # Sistema de abas para RDF e MSD
        analysis_frame = QFrame()
        analysis_frame.setObjectName("Card")
        analysis_layout = QHBoxLayout(analysis_frame)
        
        rdf_panel = self._create_rdf_panel()
        msd_panel = self._create_msd_panel()

        analysis_layout.addWidget(rdf_panel)
        analysis_layout.addWidget(msd_panel)

        main_layout.addWidget(analysis_frame)

        # Desenha os placeholders iniciais DEPOIS que tudo foi criado
        self._draw_rdf_plot()
        self._draw_msd_plot()


    def _create_rdf_panel(self):
        panel = QFrame()
        layout = QHBoxLayout(panel)
        
        plot_frame = QFrame()
        plot_layout = QVBoxLayout(plot_frame)
        plot_layout.addWidget(QLabel("<b>Função de Distribuição Radial (RDF)</b>"))
        
        rdf_controls_layout = QHBoxLayout()
        rdf_controls_layout.addWidget(QLabel("Par 1:"))
        self.rdf_el1_combo = QComboBox()
        self.rdf_el1_combo.setEnabled(False)
        rdf_controls_layout.addWidget(self.rdf_el1_combo)
        
        rdf_controls_layout.addWidget(QLabel("Par 2:"))
        self.rdf_el2_combo = QComboBox()
        self.rdf_el2_combo.setEnabled(False)
        rdf_controls_layout.addWidget(self.rdf_el2_combo)
        
        btn_calc_rdf = QPushButton("Calcular RDF")
        btn_calc_rdf.clicked.connect(self._calculate_rdf)
        rdf_controls_layout.addWidget(btn_calc_rdf)
        
        self.show_rdf_markers_check = QCheckBox("Mostrar Marcadores")
        self.show_rdf_markers_check.setChecked(True)
        self.show_rdf_markers_check.stateChanged.connect(self._draw_rdf_plot)
        rdf_controls_layout.addWidget(self.show_rdf_markers_check)
        rdf_controls_layout.addStretch()
        
        plot_layout.addLayout(rdf_controls_layout)
        plot_layout.addWidget(self.rdf_canvas)
        
        results_frame = QFrame()
        results_layout = QVBoxLayout(results_frame)
        results_layout.addWidget(QLabel("<b>Quantificação dos Picos</b>"))
        
        # Usa a tabela já criada em _create_widgets
        self.peak_table.setHorizontalHeaderLabels(["Propriedade", "Valor"])
        self.peak_table.setItem(0, 0, QTableWidgetItem("Posição 1º Pico"))
        self.peak_table.setItem(1, 0, QTableWidgetItem("Nº Coord. (1º Mínimo)"))
        self.peak_table.setItem(2, 0, QTableWidgetItem("Posição 2º Pico"))
        self.peak_table.setItem(3, 0, QTableWidgetItem("Nº Coord. (2º Mínimo)"))
        self.peak_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.peak_table.verticalHeader().setVisible(False)
        self.peak_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        results_layout.addWidget(self.peak_table)
        results_layout.addStretch()
        
        layout.addWidget(plot_frame, 2)
        layout.addWidget(results_frame, 1)
        return panel

    def _create_msd_panel(self):
        panel = QFrame()
        layout = QVBoxLayout(panel)
        layout.addWidget(QLabel("<b>Coeficiente de Difusão (MSD)</b>"))

        msd_controls_layout = QHBoxLayout()
        msd_controls_layout.addWidget(QLabel("Elemento:"))
        self.msd_el_combo = QComboBox()
        self.msd_el_combo.setEnabled(False)
        msd_controls_layout.addWidget(self.msd_el_combo)
        
        btn_calc_msd = QPushButton("Calcular Difusão")
        btn_calc_msd.clicked.connect(self._calculate_msd)
        msd_controls_layout.addWidget(btn_calc_msd)
        msd_controls_layout.addStretch()
        self.msd_result_label = QLabel("<b>D = N/A</b>")
        msd_controls_layout.addWidget(self.msd_result_label)
        
        layout.addLayout(msd_controls_layout)
        layout.addWidget(self.msd_canvas)
        return panel

    # --- O resto do arquivo (lógica de backend) permanece o mesmo ---
    def _load_trajectory(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Selecionar arquivo de trajetória", "", "LAMMPS Trajectory (*.lammpstrj);;All files (*.*)")
        if not filepath: return
        try:
            self.frames, self.box_dims = self._parse_dump_file(filepath)
            if not self.frames:
                QMessageBox.critical(self, "Erro", "Nenhum frame válido encontrado no arquivo dump.")
                return
            first_frame_elements = [atom[1] for atom in self.frames[0]['atoms']]
            self.unique_elements = sorted(list(set(first_frame_elements)))
            
            self.rdf_el1_combo.clear()
            self.rdf_el1_combo.addItems(self.unique_elements)
            self.rdf_el1_combo.setEnabled(True)
            self.rdf_el2_combo.clear()
            self.rdf_el2_combo.addItems(self.unique_elements)
            self.rdf_el2_combo.setEnabled(True)
            self.msd_el_combo.clear()
            self.msd_el_combo.addItems(self.unique_elements)
            self.msd_el_combo.setEnabled(True)
            
            QMessageBox.information(self, "Sucesso", f"{len(self.frames)} frames carregados com sucesso.")
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Carregar Trajetória", f"Ocorreu um erro: {e}")

    def _parse_dump_file(self, filepath):
        frames = []; box_dims = []
        with open(filepath, 'r') as f: lines = f.readlines()
        i = 0
        num_atoms = 0
        while i < len(lines):
            if lines[i].strip() == "ITEM: TIMESTEP":
                frame_data = {'timestep': int(lines[i+1])}
                i += 2
            elif lines[i].strip() == "ITEM: NUMBER OF ATOMS":
                num_atoms = int(lines[i+1])
                i += 2
            elif lines[i].strip() == "ITEM: BOX BOUNDS pp pp pp":
                x_bounds = list(map(float, lines[i+1].split())); y_bounds = list(map(float, lines[i+2].split())); z_bounds = list(map(float, lines[i+3].split()))
                box_dims.append([x_bounds[1]-x_bounds[0], y_bounds[1]-y_bounds[0], z_bounds[1]-z_bounds[0]])
                i += 4
            elif lines[i].strip().startswith("ITEM: ATOMS"):
                headers = lines[i].strip().split()[2:]
                id_idx, el_idx = headers.index('id'), headers.index('element')
                x_idx, y_idx, z_idx = headers.index('x'), headers.index('y'), headers.index('z')
                atoms = []
                for j in range(num_atoms):
                    parts = lines[i+1+j].strip().split()
                    atoms.append([int(parts[id_idx]), parts[el_idx], float(parts[x_idx]), float(parts[y_idx]), float(parts[z_idx])])
                atoms.sort(key=lambda x: x[0])
                frame_data['atoms'] = atoms
                frames.append(frame_data)
                i += 1 + num_atoms
            else:
                i += 1
        return frames, np.array(box_dims[0]) if box_dims else None

    def _calculate_rdf(self):
        if not self.frames:
            QMessageBox.critical(self, "Erro", "Carregue uma trajetória primeiro.")
            return
        el1, el2 = self.rdf_el1_combo.currentText(), self.rdf_el2_combo.currentText()
        if not el1 or not el2:
            QMessageBox.warning(self, "Aviso", "Selecione os dois elementos para o par.")
            return
        rmax, nbins = min(self.box_dims) / 2.0, 200
        dr = rmax / nbins
        rdf_hist = np.zeros(nbins)
        n_el1_total, n_el2_total, num_frames_processed = 0, 0, 0
        
        num_frames_to_process = min(len(self.frames), 100)
        frame_step = len(self.frames) // num_frames_to_process if num_frames_to_process > 0 else 1
        
        for frame in self.frames[::frame_step]:
            coords = np.array([atom[2:] for atom in frame['atoms']])
            elements = np.array([atom[1] for atom in frame['atoms']])
            indices1 = np.where(elements == el1)[0]
            indices2 = np.where(elements == el2)[0]

            if len(indices1) == 0 or len(indices2) == 0: continue
            
            tree = cKDTree(coords[indices2])
            dist_matrix = tree.query_ball_point(coords[indices1], r=rmax)

            for i, neighbors_indices in enumerate(dist_matrix):
                if not neighbors_indices: continue
                ref_pos = coords[indices1[i]]
                dists = np.linalg.norm(coords[indices2[neighbors_indices]] - ref_pos, axis=1)
                if el1 == el2:
                    dists = dists[dists > 1e-6] 
                if dists.size > 0:
                    hist, _ = np.histogram(dists, bins=nbins, range=(0, rmax))
                    rdf_hist += hist
            
            n_el1_total += len(indices1)
            n_el2_total += len(indices2)
            num_frames_processed += 1

        if num_frames_processed == 0:
            QMessageBox.critical(self, "Erro", "Nenhum par de elementos encontrado.")
            return
        
        r = np.linspace(0, rmax, nbins)
        shell_volume = 4.0 * np.pi * (r + dr/2)**2 * dr
        volume = self.box_dims[0] * self.box_dims[1] * self.box_dims[2]
        avg_n_el1 = n_el1_total / num_frames_processed
        avg_n_el2 = n_el2_total / num_frames_processed
        bulk_density = avg_n_el2 / volume
        if el1 == el2:
            bulk_density = (avg_n_el1 - 1) / volume
        
        norm_factor = bulk_density * avg_n_el1 * num_frames_processed
        g_r = rdf_hist / (shell_volume + 1e-9) / (norm_factor + 1e-9)
        
        self.rdf_data = {'r': r, 'g_r': g_r, 'rdf_hist': rdf_hist, 'avg_n_el1': avg_n_el1, 'num_frames': num_frames_processed, 'pair': f"{el1}-{el2}"}
        self._draw_rdf_plot()

    def _draw_rdf_plot(self):
        self.rdf_canvas._style_plot("Função de Distribuição Radial (RDF)", "Distância, r (Å)", "g(r)")
        
        for row in range(self.peak_table.rowCount()):
            self.peak_table.setItem(row, 1, QTableWidgetItem("N/A"))

        if self.rdf_data:
            r, g_r = self.rdf_data['r'], self.rdf_data['g_r']
            self.rdf_canvas.axes.set_title(f"RDF: {self.rdf_data['pair']}", color="#e0e0e0", weight='bold')
            self.rdf_canvas.axes.plot(r, g_r, color="#3498DB")
            
            if self.show_rdf_markers_check.isChecked():
                rdf_hist, avg_n_el1, num_frames = self.rdf_data['rdf_hist'], self.rdf_data['avg_n_el1'], self.rdf_data['num_frames']
                peaks, _ = find_peaks(g_r, height=1.1, distance=5)
                minima, _ = find_peaks(-g_r, distance=5)

                if len(peaks) > 0:
                    peak1_r = r[peaks[0]]
                    self.peak_table.setItem(0, 1, QTableWidgetItem(f"{peak1_r:.2f} Å"))
                    self.rdf_canvas.axes.axvline(peak1_r, color='yellow', linestyle='--', alpha=0.7)
                    minima_after_peak1 = minima[minima > peaks[0]]
                    if len(minima_after_peak1) > 0:
                        min1_idx = minima_after_peak1[0]
                        cn1 = np.sum(rdf_hist[:min1_idx]) / (avg_n_el1 * num_frames)
                        self.peak_table.setItem(1, 1, QTableWidgetItem(f"{cn1:.2f}"))

                if len(peaks) > 1:
                    peak2_r = r[peaks[1]]
                    self.peak_table.setItem(2, 1, QTableWidgetItem(f"{peak2_r:.2f} Å"))
                    self.rdf_canvas.axes.axvline(peak2_r, color='yellow', linestyle='--', alpha=0.7)
                    minima_after_peak2 = minima[minima > peaks[1]]
                    if len(minima_after_peak2) > 0:
                        min2_idx = minima_after_peak2[0]
                        cn2 = np.sum(rdf_hist[:min2_idx]) / (avg_n_el1 * num_frames)
                        self.peak_table.setItem(3, 1, QTableWidgetItem(f"{cn2:.2f}"))
        else:
            self.rdf_canvas.axes.text(0.5, 0.5, 'Calcule o RDF para visualizar', ha='center', va='center', transform=self.rdf_canvas.axes.transAxes, color='gray')
        
        self.rdf_canvas.draw()
        
    def _calculate_msd(self):
        if not self.frames:
            QMessageBox.critical(self, "Erro", "Carregue uma trajetória primeiro.")
            return
        element = self.msd_el_combo.currentText()
        if not element:
            QMessageBox.warning(self, "Aviso", "Selecione um elemento para o cálculo do MSD.")
            return

        initial_ids = {atom[0] for atom in self.frames[0]['atoms'] if atom[1] == element}
        if not initial_ids:
            QMessageBox.critical(self, "Erro", f"Nenhum átomo do elemento '{element}' encontrado no primeiro frame.")
            return
        
        id_list = sorted(list(initial_ids))
        id_map = {p_id: i for i, p_id in enumerate(id_list)}
        
        positions = np.zeros((len(self.frames), len(id_list), 3))
        timesteps = np.zeros(len(self.frames))
        
        for i, frame in enumerate(self.frames):
            timesteps[i] = frame['timestep']
            frame_atoms = {atom[0]: np.array(atom[2:]) for atom in frame['atoms'] if atom[0] in initial_ids}
            for p_id, pos in frame_atoms.items():
                positions[i, id_map[p_id]] = pos
        
        for t in range(1, len(positions)):
            displacement = positions[t] - positions[t - 1]
            displacement -= self.box_dims * np.round(displacement / self.box_dims)
            positions[t] = positions[t - 1] + displacement

        msd = np.zeros(len(self.frames))
        for t in range(1, len(self.frames)):
            diff = positions[t:] - positions[:-t]
            msd[t] = np.mean(np.sum(diff**2, axis=2))

        dt = 0.25 # ASSUMIDO! O ideal é pegar isso do script de input
        time_ps = (timesteps - timesteps[0]) * dt * 1e-3

        fit_start_index = len(time_ps) // 2
        if fit_start_index < 2:
            QMessageBox.critical(self, "Erro", "Não há pontos suficientes para o ajuste linear do MSD.")
            return

        slope, intercept, r_value, _, _ = linregress(time_ps[fit_start_index:], msd[fit_start_index:])
        
        diffusion_coeff_A2_ps = slope / 6.0
        diffusion_coeff_cm2_s = diffusion_coeff_A2_ps * 1e-16 / 1e-12 

        self.msd_result_label.setText(f"<b>D = {diffusion_coeff_cm2_s:.3e} cm²/s</b>")
        self._draw_msd_plot(time_ps, msd, time_ps[fit_start_index:], intercept + slope * time_ps[fit_start_index:], element, r_value**2)
        
    def _draw_msd_plot(self, time_data=None, msd_data=None, fit_time=None, fit_msd=None, element=None, r2=None):
        self.msd_canvas._style_plot("Deslocamento Quadrático Médio (MSD)", "Tempo (ps)", "MSD (Å²)")
        
        if msd_data is not None:
            self.msd_canvas.axes.set_title(f"MSD para {element}", color="#e0e0e0", weight='bold')
            self.msd_canvas.axes.plot(time_data, msd_data, color="#2ecc71", label="MSD Calculado")
            self.msd_canvas.axes.plot(fit_time, fit_msd, '--', color="#e74c3c", label=f"Ajuste Linear (R²={r2:.4f})")
            legend = self.msd_canvas.axes.legend()
            legend.get_frame().set_facecolor("#2c2e3a")
            legend.get_frame().set_edgecolor("#555")
            for text in legend.get_texts(): text.set_color("white")
        else:
            self.msd_canvas.axes.text(0.5, 0.5, 'Calcule a Difusão para visualizar', ha='center', va='center', transform=self.msd_canvas.axes.transAxes, color='gray')
        
        self.msd_canvas.draw()