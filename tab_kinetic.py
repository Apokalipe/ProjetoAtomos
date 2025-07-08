# tab_kinetic.py
import os
import numpy as np
from scipy.stats import linregress
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, 
                             QRadioButton, QFileDialog, QMessageBox, QFrame,
                             QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
                             QSplitter, QInputDialog)
from PyQt6.QtCore import Qt

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

def _preprocess_log_file(log_file):
    # Lógica idêntica à original
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
                    current_timestep = int(data_parts[0])
                    header_parts = line.lstrip('# ').split()
                    species_names = header_parts[3:]
                    species_counts = [int(count) for count in data_parts[3:]]
                    all_data[current_timestep] = dict(zip(species_names, species_counts))
            i += 2
        else: i += 1
    if not all_data: return ('error', "Nenhum dado de espécies válido encontrado no arquivo.")
    return ('success', all_data)


class KineticAnalysisTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.experiments = {}
        self.k_results = {}
        self.GAS_CONSTANT_J_MOL_K = 8.31446
        
        self._create_widgets()

    def _create_widgets(self):
        main_layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Painel Esquerdo (Configuração)
        left_panel = QFrame()
        left_panel.setObjectName("Card")
        left_layout = QVBoxLayout(left_panel)
        
        left_layout.addWidget(QLabel("<b>Dados Experimentais (species.log)</b>"))
        btn_add = QPushButton("Adicionar Experimento...")
        btn_add.clicked.connect(self._add_experiment)
        btn_remove = QPushButton("Remover Selecionado")
        btn_remove.clicked.connect(self._remove_experiment)
        left_layout.addWidget(btn_add)
        left_layout.addWidget(btn_remove)

        self.exp_table = QTableWidget()
        self.exp_table.setColumnCount(2)
        self.exp_table.setHorizontalHeaderLabels(['Arquivo', 'Temperatura (K)'])
        self.exp_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.exp_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        left_layout.addWidget(self.exp_table)
        
        left_layout.addWidget(QLabel("<b>Análise de Ordem de Reação</b>"))
        left_layout.addWidget(QLabel("Reagente de Interesse:"))
        self.reagent_combo = QComboBox()
        self.reagent_combo.setEnabled(False)
        left_layout.addWidget(self.reagent_combo)
        
        btn_calc_k = QPushButton("1. Calcular Constantes de Velocidade (k)")
        btn_calc_k.clicked.connect(self._calculate_rate_constants)
        left_layout.addWidget(btn_calc_k)
        
        left_layout.addWidget(QLabel("<b>Resultados Cinéticos</b>"))
        self.results_table = QTableWidget()
        cols = ('T (K)', 'k₀', 'R²₀', 'k₁', 'R²₁', 'k₂', 'R²₂')
        self.results_table.setColumnCount(len(cols))
        self.results_table.setHorizontalHeaderLabels(cols)
        left_layout.addWidget(self.results_table)
        
        left_layout.addWidget(QLabel("<b>Ordem para Ajuste de Arrhenius</b>"))
        order_radio_layout = QHBoxLayout()
        self.order_radio_0 = QRadioButton("Ordem 0")
        self.order_radio_1 = QRadioButton("Ordem 1")
        self.order_radio_1.setChecked(True)
        self.order_radio_2 = QRadioButton("Ordem 2")
        order_radio_layout.addWidget(self.order_radio_0)
        order_radio_layout.addWidget(self.order_radio_1)
        order_radio_layout.addWidget(self.order_radio_2)
        left_layout.addLayout(order_radio_layout)
        
        btn_arrhenius = QPushButton("2. Ajustar Arrhenius e Calcular Parâmetros")
        btn_arrhenius.clicked.connect(self._perform_arrhenius_fit)
        left_layout.addWidget(btn_arrhenius)
        
        left_panel.setLayout(left_layout)
        
        # Painel Direito (Gráfico e Resultados Finais)
        right_panel = QFrame()
        right_panel.setObjectName("Card")
        right_layout = QVBoxLayout(right_panel)
        
        right_layout.addWidget(QLabel("<b>Gráfico de Arrhenius (ln(k) vs 1/T)</b>"))
        self.canvas = FigureCanvas(Figure(figsize=(5, 4), facecolor="#2c2e3a"))
        self.ax = self.canvas.figure.subplots()
        right_layout.addWidget(self.canvas)
        
        self.ea_label = QLabel("Energia de Ativação (Ea): N/A")
        self.a_label = QLabel("Fator Pré-exponencial (A): N/A")
        right_layout.addWidget(self.ea_label)
        right_layout.addWidget(self.a_label)
        
        right_panel.setLayout(right_layout)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([600, 400])
        main_layout.addWidget(splitter)
        
        self._update_plot_style()

    def _add_experiment(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Selecionar species.log", "", "Log Files (*.log);;All files (*.*)")
        if not filepath: return
        
        temp, ok = QInputDialog.getDouble(self, "Temperatura", "Digite a temperatura (K) para este experimento:", 298.15, 0, 10000, 2)
        if not ok: return
        
        row = self.exp_table.rowCount()
        self.exp_table.insertRow(row)
        item_id = str(row) # Usar o índice da linha como ID
        self.exp_table.setItem(row, 0, QTableWidgetItem(os.path.basename(filepath)))
        self.exp_table.setItem(row, 1, QTableWidgetItem(f"{temp:.2f}"))
        
        self.experiments[item_id] = {'path': filepath, 'temp': temp, 'log_data': None}
        self._update_reagent_list()

    def _remove_experiment(self):
        selected_rows = sorted([item.row() for item in self.exp_table.selectedItems()], reverse=True)
        if not selected_rows: return
        
        for row in set(selected_rows): # set para evitar remoção duplicada
            item_id = str(row)
            if item_id in self.experiments:
                del self.experiments[item_id]
            self.exp_table.removeRow(row)
        
        self._update_reagent_list()

    def _update_reagent_list(self):
        all_species = set()
        for exp in self.experiments.values():
            if exp['log_data'] is None:
                status, log_data = _preprocess_log_file(exp['path'])
                if status == 'success':
                    exp['log_data'] = log_data
            if exp['log_data']:
                all_species.update(key for data in exp['log_data'].values() for key in data.keys())
        
        self.reagent_combo.clear()
        if all_species:
            self.reagent_combo.addItems(sorted(list(all_species)))
            self.reagent_combo.setEnabled(True)
        else:
            self.reagent_combo.setEnabled(False)

    def _calculate_rate_constants(self):
        reagent = self.reagent_combo.currentText()
        if not reagent:
            QMessageBox.critical(self, "Erro", "Por favor, selecione um reagente de interesse.")
            return
        if not self.experiments:
            QMessageBox.critical(self, "Erro", "Por favor, adicione pelo menos um experimento.")
            return
            
        self.results_table.setRowCount(0)
        self.k_results.clear()
        
        for item_id, exp_data in self.experiments.items():
            log_data = exp_data['log_data']
            if not log_data: continue
            
            timesteps = sorted(log_data.keys())
            concentrations = [log_data[ts].get(reagent, 0) for ts in timesteps]
            valid_indices = [i for i, c in enumerate(concentrations) if c > 0]
            if len(valid_indices) < 3: continue
            
            t = np.array([timesteps[i] for i in valid_indices])
            conc = np.array([concentrations[i] for i in valid_indices])
            
            res0 = linregress(t, conc); k0, r2_0 = -res0.slope, res0.rvalue**2
            res1 = linregress(t, np.log(conc)); k1, r2_1 = -res1.slope, res1.rvalue**2
            res2 = linregress(t, 1/conc); k2, r2_2 = res2.slope, res2.rvalue**2
            
            self.k_results[item_id] = {'k0': k0, 'r2_0': r2_0, 'k1': k1, 'r2_1': r2_1, 'k2': k2, 'r2_2': r2_2}
            values = (f"{exp_data['temp']:.2f}", f"{k0:.3e}", f"{r2_0:.4f}", f"{k1:.3e}", f"{r2_1:.4f}", f"{k2:.3e}", f"{r2_2:.4f}")
            
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            for col, val in enumerate(values):
                self.results_table.setItem(row, col, QTableWidgetItem(val))

    def _perform_arrhenius_fit(self):
        if len(self.k_results) < 2:
            QMessageBox.critical(self, "Erro de Análise", "São necessários pelo menos 2 experimentos com temperaturas diferentes.")
            return
            
        selected_order = 1
        if self.order_radio_0.isChecked(): selected_order = 0
        elif self.order_radio_2.isChecked(): selected_order = 2
        
        temps, k_values = [], []
        for item_id, results in self.k_results.items():
            k = results.get(f'k{selected_order}')
            if k is not None and k > 0:
                temps.append(self.experiments[item_id]['temp'])
                k_values.append(k)
            else:
                QMessageBox.warning(self, "Dado Inválido", f"A constante k (ordem {selected_order}) para T={self.experiments[item_id]['temp']}K é inválida e será ignorada.")
        
        if len(temps) < 2:
            QMessageBox.critical(self, "Erro de Análise", "São necessários pelo menos 2 pontos de dados válidos (k > 0) para o ajuste.")
            return
            
        inv_T = 1 / np.array(temps)
        ln_k = np.log(np.array(k_values))
        slope, intercept, r_value, _, _ = linregress(inv_T, ln_k)
        
        Ea_J_mol = -slope * self.GAS_CONSTANT_J_MOL_K
        Ea_kJ_mol = Ea_J_mol / 1000
        A = np.exp(intercept)
        
        order_units = {0: "mol·L⁻¹·s⁻¹", 1: "s⁻¹", 2: "L·mol⁻¹·s⁻¹"}
        unit_str = order_units.get(selected_order, "(unidades mistas)")

        self.ea_label.setText(f"<b>Energia de Ativação (Ea): {Ea_kJ_mol:.2f} kJ/mol</b>")
        self.a_label.setText(f"<b>Fator Pré-exponencial (A): {A:.3e} {unit_str}</b>")
        
        self._update_plot_style()
        fit_line = intercept + slope * inv_T
        self.ax.scatter(inv_T, ln_k, color='#e0218a', label=f'Dados (k de ordem {selected_order})', s=50, zorder=5)
        self.ax.plot(inv_T, fit_line, color='#3498DB', linestyle='--', label=f'Ajuste Linear (R² = {r_value**2:.4f})')
        legend = self.ax.legend()
        legend.get_frame().set_facecolor("#2c2e3a")
        for text in legend.get_texts(): text.set_color("white")
        self.canvas.draw()
    
    def _update_plot_style(self):
        self.ax.clear()
        self.ax.set_facecolor("#2c2e3a")
        for spine in self.ax.spines.values(): spine.set_color("#555")
        self.ax.tick_params(axis='x', colors="#e0e0e0")
        self.ax.tick_params(axis='y', colors="#e0e0e0")
        
        self.ax.set_xlabel('1/T (K⁻¹)', color="#b0b0b0")
        self.ax.set_ylabel('ln(k)', color="#b0b0b0")
        self.ax.set_title('Gráfico de Arrhenius', color="#e0e0e0", weight='bold')
        self.ax.grid(True, linestyle='--', alpha=0.2, color="#777")
        self.canvas.figure.tight_layout()
        self.canvas.draw()