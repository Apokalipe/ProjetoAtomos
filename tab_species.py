# tab_species.py
import os
from itertools import cycle
import numpy as np
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, 
                             QSlider, QLineEdit, QFileDialog, QMessageBox, QFrame,
                             QLabel, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView,
                             QSplitter)
from PyQt6.QtCore import Qt

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class SpeciesAnalysisTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.log_data = {}
        self.available_timesteps = []
        self.slider_marker = None
        
        self.PLOT_COLORS = cycle(["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"])
        
        self._create_widgets()

    def _create_widgets(self):
        # O layout principal agora é um QHBoxLayout para conter o splitter diretamente
        main_layout = QHBoxLayout(self)
        #main_layout.setContentsMargins(0,0,0,0)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- PAINEL ESQUERDO (CONTROLES) ---
        left_panel = QFrame()
        left_panel.setObjectName("Card")
        left_layout = QVBoxLayout(left_panel)
        
        # Botão de carregar arquivo e label (agora no topo do painel esquerdo)
        load_layout = QHBoxLayout()
        btn_load = QPushButton("Carregar o log de espécies...")
        btn_load.clicked.connect(self._load_file)
        load_layout.addWidget(btn_load)
        self.label_arquivo = QLabel("Nenhum arquivo carregado.")
        load_layout.addWidget(self.label_arquivo)
        load_layout.addStretch()
        left_layout.addLayout(load_layout)
        
        # Separador visual
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        left_layout.addWidget(separator)
        
        # Controles do Timestep
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("Timestep:"))
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.valueChanged.connect(self._update_table_from_slider)
        slider_layout.addWidget(self.slider)
        self.label_timestep = QLabel("N/A")
        slider_layout.addWidget(self.label_timestep)
        left_layout.addLayout(slider_layout)

        left_layout.addWidget(QLabel("<b>Espécies para o Gráfico (Ctrl+Click):</b>"))
        self.listbox = QListWidget()
        self.listbox.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.listbox.itemSelectionChanged.connect(self._update_graph)
        left_layout.addWidget(self.listbox)
        
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filtrar contagem >")); self.filter_entry = QLineEdit("0")
        self.filter_entry.returnPressed.connect(self._apply_filter); filter_layout.addWidget(self.filter_entry)
        btn_apply = QPushButton("Aplicar"); btn_apply.clicked.connect(self._apply_filter); filter_layout.addWidget(btn_apply)
        left_layout.addLayout(filter_layout)
        
        left_layout.addWidget(QLabel("<b>Composição no Timestep:</b>"))
        self.tree = QTableWidget(); self.tree.setColumnCount(3); self.tree.setHorizontalHeaderLabels(['Molécula', 'Contagem', '%'])
        self.tree.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tree.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers); left_layout.addWidget(self.tree)
        
        # --- PAINEL DIREITO (GRÁFICO) ---
        right_panel = QFrame(); right_panel.setObjectName("Card"); right_layout = QVBoxLayout(right_panel)
        graph_controls_layout = QHBoxLayout(); graph_controls_layout.addStretch()
        self.marker_check = QCheckBox("Mostrar Marcador"); self.marker_check.setChecked(True); self.marker_check.stateChanged.connect(self._update_marker)
        graph_controls_layout.addWidget(self.marker_check)
        self.canvas = FigureCanvas(Figure(figsize=(5, 4), facecolor="#2c2e3a")); self.ax = self.canvas.figure.subplots()
        right_layout.addLayout(graph_controls_layout); right_layout.addWidget(self.canvas)
        
        # Adiciona os painéis ao splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 600])
        
        main_layout.addWidget(splitter)
        self._plot_graph_data({}, "Selecione uma espécie para visualizar sua evolução")

    # (O resto das funções da classe permanecem inalteradas)
    def _load_file(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Selecionar Arquivo de Log de Espécies", "", "Log Files (*.log);;All Files (*.*)")
        if not filepath: return
        status, result = self._preprocess_log_file(filepath)
        if status == 'error': QMessageBox.critical(self, "Erro", result); return
        self.log_data = result; self.available_timesteps = sorted(self.log_data.keys())
        self.label_arquivo.setText(f"Log: {os.path.basename(filepath)}")
        self.slider.setRange(0, len(self.available_timesteps) - 1); self.slider.setValue(0)
        self.listbox.clear()
        all_species = set(key for data in self.log_data.values() for key in data.keys())
        self.listbox.addItems(sorted(list(all_species)))
        self._update_table_from_slider(); self._update_graph()
    def _preprocess_log_file(self, log_file):
        if not os.path.exists(log_file): return ('error', f"Arquivo não encontrado: {log_file}")
        all_data = {}; i = 0
        try:
            with open(log_file, 'r') as f: lines = f.readlines()
        except Exception as e: return ('error', f"Não foi possível ler o arquivo: {e}")
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('#'):
                if i + 1 < len(lines):
                    data_line = lines[i+1].strip(); data_parts = data_line.split()
                    if data_parts and data_parts[0].isdigit():
                        current_timestep = int(data_parts[0]); header_parts = line.lstrip('# ').split()
                        species_names = header_parts[3:]; species_counts = [int(count) for count in data_parts[3:]]
                        all_data[current_timestep] = dict(zip(species_names, species_counts))
                i += 2
            else: i += 1
        if not all_data: return ('error', "Nenhum dado de espécies válido encontrado no arquivo.")
        return ('success', all_data)
    def _apply_filter(self): self._update_table_from_slider()
    def _update_table_from_slider(self):
        slider_index = self.slider.value()
        if not self.available_timesteps: return
        timestep = self.available_timesteps[slider_index]; self.label_timestep.setText(str(timestep)); data = self.log_data.get(timestep, {})
        try: filter_value = int(self.filter_entry.text())
        except ValueError: filter_value = 0
        filtered_data = {formula: count for formula, count in data.items() if count > filter_value}
        self.tree.setRowCount(0); total = sum(filtered_data.values())
        sorted_data = sorted(filtered_data.items(), key=lambda item: item[1], reverse=True)
        for row, (formula, count) in enumerate(sorted_data):
            self.tree.insertRow(row); percent = (count / total * 100) if total > 0 else 0
            self.tree.setItem(row, 0, QTableWidgetItem(formula)); self.tree.setItem(row, 1, QTableWidgetItem(str(count))); self.tree.setItem(row, 2, QTableWidgetItem(f"{percent:.2f}%"))
        if total > 0:
            row_count = self.tree.rowCount(); self.tree.insertRow(row_count)
            self.tree.setItem(row_count, 0, QTableWidgetItem("TOTAL (Filtrado)")); self.tree.setItem(row_count, 1, QTableWidgetItem(str(total))); self.tree.setItem(row_count, 2, QTableWidgetItem("100.00%"))
        self._update_marker()
    def _update_graph(self):
        if not self.log_data: return
        selected_items = self.listbox.selectedItems()
        if not selected_items: self._plot_graph_data({}, "Selecione uma ou mais espécies na lista"); return
        data_to_plot = {}
        for item in selected_items:
            species = item.text(); y_vals = [self.log_data[ts].get(species, 0) for ts in self.available_timesteps]
            data_to_plot[species] = y_vals
        self._plot_graph_data(data_to_plot, "Evolução das Espécies")
    def _plot_graph_data(self, data_dict, title):
        self.ax.clear(); self.slider_marker = None; self.ax.set_facecolor("#2c2e3a")
        for spine in self.ax.spines.values(): spine.set_color("#555")
        self.ax.tick_params(axis='x', colors="#e0e0e0"); self.ax.tick_params(axis='y', colors="#e0e0e0")
        if data_dict:
            for label, y_data in data_dict.items(): self.ax.plot(self.available_timesteps, y_data, marker='.', linestyle='-', markersize=4, label=label, color=next(self.PLOT_COLORS))
            legend = self.ax.legend(); legend.get_frame().set_facecolor("#2c2e3a"); legend.get_frame().set_edgecolor("#555")
            for text in legend.get_texts(): text.set_color("white")
        self.ax.set_title(title, color="#e0e0e0", weight='bold'); self.ax.set_xlabel("Passo de Tempo (Timestep)", color="#b0b0b0"); self.ax.set_ylabel("Número de Moléculas", color="#b0b0b0")
        self.ax.grid(True, linestyle='--', alpha=0.2, color="#777"); self.canvas.figure.tight_layout(); self._update_marker(); self.canvas.draw_idle()
    def _update_marker(self):
        if self.slider_marker: self.slider_marker.remove(); self.slider_marker = None
        if self.marker_check.isChecked() and self.available_timesteps:
            slider_index = self.slider.value(); current_timestep = self.available_timesteps[slider_index]
            self.slider_marker = self.ax.axvline(x=current_timestep, color="#e0218a", linestyle='--', linewidth=1.5, alpha=0.8)
        self.canvas.draw_idle()