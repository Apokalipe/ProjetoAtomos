# tab_thermo.py
import pandas as pd
import yaml
from scipy.ndimage import gaussian_filter1d
import pyqtgraph as pg
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, 
                             QLabel, QSlider, QFileDialog, QMessageBox, QFrame)
from PyQt6.QtCore import Qt

class ThermoAnalysisTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.PLOT_COLORS = {"Temp": "#E74C3C", "Press": "#2ECC71", "Volume": "#F39C12", "Density": "#9B59B6", "PotEng": "#E67E22", "KinEng": "#F1C40F", "TotEng": "#3498DB", "Enthalpy": "#1ABC9C"}
        self.thermo_df = None
        self.current_theme = 'dark' # Armazena o tema atual

        self.CONVERSION_FUNCTIONS = {
            'Energia': {'kcal/mol': lambda x: x, 'kJ/mol': lambda x: x * 4.184, 'eV': lambda x: x * 0.04336},
            'Pressão': {'atm': lambda x: x, 'bar': lambda x: x * 1.01325, 'Pa': lambda x: x * 101325, 'MPa': lambda x: x * 0.101325},
            'Temperatura': {'K': lambda k: k, '°C': lambda k: k - 273.15, '°F': lambda k: (k - 273.15) * 9/5 + 32},
            'Volume': {'Å³': lambda v: v, 'nm³': lambda v: v * 1e-3},
            'Densidade': {'g/cm³': lambda d: d}
        }
        self.PROPERTY_TO_UNIT_TYPE = {
            'PotEng': 'Energia', 'KinEng': 'Energia', 'TotEng': 'Energia', 'Enthalpy': 'Energia',
            'Press': 'Pressão', 'Temp': 'Temperatura', 'Volume': 'Volume', 'Density': 'Densidade'
        }
        
        self._create_widgets()
        self.update_theme(self.current_theme) # Seta o tema inicial

    def _create_widgets(self):
        main_layout = QVBoxLayout(self)
        
        top_frame = QFrame()
        top_frame.setObjectName("Card")
        top_layout = QHBoxLayout(top_frame)

        btn_load = QPushButton("Carregar log.lammps...")
        btn_load.clicked.connect(self._load_and_plot)
        top_layout.addWidget(btn_load)

        top_layout.addWidget(QLabel("Propriedade:"))
        self.prop_combo = QComboBox()
        self.prop_combo.setEnabled(False)
        self.prop_combo.currentTextChanged.connect(self._on_property_change)
        top_layout.addWidget(self.prop_combo)

        top_layout.addWidget(QLabel("Unidade:"))
        self.unit_combo = QComboBox()
        self.unit_combo.setEnabled(False)
        self.unit_combo.currentTextChanged.connect(self._update_plots)
        top_layout.addWidget(self.unit_combo)

        top_layout.addWidget(QLabel("Suavização (sigma):"))
        self.sigma_slider = QSlider(Qt.Orientation.Horizontal)
        self.sigma_slider.setRange(1, 100)
        self.sigma_slider.setValue(20)
        self.sigma_slider.valueChanged.connect(self._update_plots)
        self.sigma_slider.setEnabled(False)
        top_layout.addWidget(self.sigma_slider)
        
        self.sigma_label = QLabel("20.0")
        top_layout.addWidget(self.sigma_label)

        main_layout.addWidget(top_frame)
        
        self.plot_widget = pg.PlotWidget()
        self.plot_item = self.plot_widget.getPlotItem()
        main_layout.addWidget(self.plot_widget)
        
        self._update_plots()

    def _load_and_plot(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Selecionar log.lammps", "", "LAMMPS Log (log.lammps);;All Files (*.*)")
        if not filepath: return
        status, result = self._parse_log_to_dataframe(filepath)
        if status == 'error':
            QMessageBox.critical(self, "Erro ao Processar Log", result)
            return
        self.thermo_df = result
        thermo_properties = [col for col in self.thermo_df.columns if col not in ['Step', 'Time']]
        
        self.prop_combo.clear()
        self.prop_combo.addItems(thermo_properties)
        self.prop_combo.setEnabled(True)
        self.sigma_slider.setEnabled(True)
        
        self._on_property_change()

    def _parse_log_to_dataframe(self, log_file):
        # Lógica idêntica à anterior
        blocos_yaml = []; bloco_atual = []; dentro_do_bloco = False
        try:
            with open(log_file, "r") as f:
                for linha in f:
                    if linha.strip() == "---": dentro_do_bloco = True; bloco_atual = [linha]
                    elif linha.strip() == "..." and dentro_do_bloco: bloco_atual.append(linha); blocos_yaml.append("\n".join(bloco_atual)); dentro_do_bloco = False
                    elif dentro_do_bloco: bloco_atual.append(linha)
        except Exception as e: return ('error', f"Não foi possível ler o arquivo: {e}")
        
        dados_final = []; cabecalho = []
        for bloco in blocos_yaml:
            try:
                dados = yaml.safe_load(bloco)
                if isinstance(dados, dict) and "keywords" in dados and "data" in dados:
                    if not cabecalho: cabecalho = dados["keywords"]
                    dados_final.extend(dados["data"])
            except yaml.YAMLError: continue
                
        if not cabecalho or not dados_final: return ('error', "Nenhum bloco de dados YAML válido foi encontrado no log.")
        df = pd.DataFrame(dados_final, columns=cabecalho)
        return ('success', df)

    def _on_property_change(self):
        prop_to_plot = self.prop_combo.currentText()
        if not prop_to_plot: return
        
        unit_type = self.PROPERTY_TO_UNIT_TYPE.get(prop_to_plot, None)
        
        self.unit_combo.clear()
        if unit_type and unit_type in self.CONVERSION_FUNCTIONS:
            units = list(self.CONVERSION_FUNCTIONS[unit_type].keys())
            self.unit_combo.addItems(units)
            self.unit_combo.setEnabled(True)
        else:
            self.unit_combo.setEnabled(False)
            
        self._update_plots()

    def _update_plots(self):
        self.plot_item.clear()
        self.legend = self.plot_item.addLegend(offset=(-10, 10))
        # Aplica o estilo do tema atual à legenda recém-criada
        self.update_theme(self.current_theme)

        # Configuração do texto de placeholder
        placeholder_color = '#A0A0A0' if self.current_theme == 'dark' else '#606060'

        if self.thermo_df is None:
            text_item = pg.TextItem('Carregue um arquivo log.lammps', color=placeholder_color, anchor=(0.5, 0.5))
            self.plot_item.addItem(text_item)
            self.plot_item.setTitle("")
            self.plot_item.setLabel('bottom', "")
            self.plot_item.setLabel('left', "")
            return
            
        prop_to_plot = self.prop_combo.currentText()
        if not prop_to_plot: 
            text_item = pg.TextItem('Selecione uma propriedade para visualizar', color=placeholder_color, anchor=(0.5, 0.5))
            self.plot_item.addItem(text_item)
            self.plot_item.setTitle("")
            self.plot_item.setLabel('bottom', "")
            self.plot_item.setLabel('left', "")
            return
        
        sigma = self.sigma_slider.value()
        self.sigma_label.setText(f"{sigma:.1f}")
        
        original_data = self.thermo_df[prop_to_plot]
        selected_unit = self.unit_combo.currentText()
        unit_type = self.PROPERTY_TO_UNIT_TYPE.get(prop_to_plot)
        
        conversion_function = self.CONVERSION_FUNCTIONS.get(unit_type, {}).get(selected_unit, lambda x: x)
        
        converted_data = conversion_function(original_data)
        suavizado = gaussian_filter1d(converted_data.to_numpy(dtype=float), sigma=sigma)
        
        color_hex = self.PLOT_COLORS.get(prop_to_plot, '#FFFFFF')
        x_data = self.thermo_df["Step"].to_numpy(dtype=float)
        
        h = color_hex.lstrip('#')
        base_rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        
        transparent_color = base_rgb + (80,)
        pen_original = pg.mkPen(color=transparent_color, width=1.0)
        self.plot_item.plot(x_data, converted_data.to_numpy(dtype=float), pen=pen_original, name='Original')

        pen_suavizada = pg.mkPen(color=base_rgb, width=2.5)
        self.plot_item.plot(x_data, suavizado, pen=pen_suavizada, name='Suavizada')
        
        y_label_text = f"{prop_to_plot}"
        if selected_unit:
            y_label_text += f" ({selected_unit})"
        
        self.plot_item.setTitle(f"{prop_to_plot} vs. Passo de Tempo")
        self.plot_item.setLabel('bottom', "Passo de Tempo (Timestep)")
        self.plot_item.setLabel('left', y_label_text)
        self.plot_item.showGrid(x=True, y=True, alpha=0.2)
    
    def update_theme(self, theme):
        self.current_theme = theme # Armazena o tema
        if theme == 'dark':
            text_color = '#e0e0e0'
            bg_color = pg.mkBrush(44, 46, 58, 200) # (R, G, B, Alpha)
        else:
            text_color = '#1a1a1a'
            bg_color = pg.mkBrush(255, 255, 255, 200)

        # A legenda é recriada em _update_plots, então estilizamos aqui
        if hasattr(self, 'legend') and self.legend:
            self.legend.setBrush(bg_color)
            for _, label in self.legend.items:
                label.setText(label.text, color=text_color)