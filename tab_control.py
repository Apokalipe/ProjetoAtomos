# tab_control.py
import os
import shutil
import re
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QPushButton,
                             QLineEdit, QComboBox, QCheckBox, QPlainTextEdit, QFileDialog,
                             QMessageBox, QLabel, QFrame, QTabWidget, QProgressBar, QSpinBox)
from PyQt6.QtCore import QProcess, QTimer
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont

import psutil
try:
    import pynvml
    PYNVML_AVAILABLE = True
except ImportError:
    PYNVML_AVAILABLE = False

try:
    from pygments import lex
    from pygments.lexer import RegexLexer, bygroups, words
    from pygments.token import Text, Comment, Operator, Keyword, Name, String, Number, Punctuation
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False

if PYGMENTS_AVAILABLE:
    class LammpsLexer(RegexLexer):
        name = 'LAMMPS'; command_words = ('atom_style', 'atom_modify', 'angle_coeff', 'angle_style', 'balance', 'bond_coeff', 'bond_style', 'boundary', 'change_box', 'clear', 'comm_modify', 'comm_style', 'compute', 'create_atoms', 'create_bonds', 'create_box', 'delete_atoms', 'delete_bonds', 'dielectric', 'dihedral_coeff', 'dihedral_style', 'dimension', 'displace_atoms', 'displace_box', 'dump', 'dump_modify', 'echo', 'fix', 'group', 'if', 'improper_coeff', 'improper_style', 'include', 'info', 'jump', 'kspace_modify', 'kspace_style', 'label', 'lattice', 'log', 'mass', 'message', 'min_modify', 'min_style', 'minimize', 'molecule', 'neighbor', 'neigh_modify', 'newton', 'next', 'package', 'pair_coeff', 'pair_modify', 'pair_style', 'pair_write', 'partition', 'print', 'processors', 'quit', 'read_data', 'read_dump', 'read_restart', 'region', 'replicate', 'reset_timestep', 'restart', 'run', 'run_style', 'server', 'set', 'shell', 'special_bonds', 'suffix', 'thermo', 'thermo_modify', 'thermo_style', 'timer', 'timestep', 'uncompute', 'undump', 'unfix', 'units', 'variable', 'velocity', 'write_data', 'write_dump', 'write_restart'); constant_words = ('all', 'atomic', 'body', 'bond', 'charge', 'colloid', 'dpd', 'edpd', 'electron', 'ellipsoid', 'full', 'hybrid', 'line', 'mdpd', 'mesh', 'molecular', 'peri', 'photoelectron', 'point', 'smd', 'sphere', 'spin', 'template', 'tri', 'wavepacket', 'angle', 'real', 'metal', 'si', 'cgs', 'electron', 'micro', 'nano', 'nve', 'nvt', 'npt', 'nph', 'temp', 'press', 'iso', 'aniso', 'x', 'y', 'z', 'xy', 'yz', 'xz', 'on', 'off', 'yes', 'no', 'NULL')
        tokens = {'root': [(r'#.*$', Comment.Single), (r'\b(next|jump|if|else|then|for|in|loop)\b', Keyword.Reserved), (words(command_words, suffix=r'\b'), Keyword.Declaration), (words(constant_words, suffix=r'\b'), Keyword.Constant), (r'(\$\(|\{)(.*?)(\)|\})', bygroups(Operator, Name.Variable, Operator)), (r'(v_|c_|d_|f_|g_|p_|t_|u_|x_)([a-zA-Z0-9_]+)', bygroups(Name.Function, Name.Variable)), (r'[0-9]+\.[0-9]*([eE][-+]?[0-9]+)?', Number.Float), (r'[0-9]+', Number.Integer), (r'"[^"]*"', String.Double), (r'\'[^\']*\'', String.Single), (r'[=*/+-<>&|!~^%]', Operator), (r'[\s]+', Text), (r'.', Text),]}
    class LammpsHighlighter(QSyntaxHighlighter):
        def __init__(self, parent):
            super().__init__(parent); self.lexer = LammpsLexer()
            self.styles = {Comment.Single: self._format(QColor("#6A9955")), Keyword.Declaration: self._format(QColor("#C586C0")), Keyword.Reserved: self._format(QColor("#D16969")), Keyword.Constant: self._format(QColor("#569CD6")), Name.Variable: self._format(QColor("#9CDCFE")), Name.Function: self._format(QColor("#4EC9B0")), Number: self._format(QColor("#B5CEA8")), String: self._format(QColor("#CE9178")), Operator: self._format(QColor("#D4D4D4")),}
        def _format(self, color, style=''):
            fmt = QTextCharFormat(); fmt.setForeground(color)
            if 'bold' in style: fmt.setFontWeight(QFont.Weight.Bold)
            if 'italic' in style: fmt.setFontItalic(True)
            return fmt
        def highlightBlock(self, text):
            for token_type, token_text in lex(text, self.lexer):
                start_index = 0
                while True:
                    start = text.find(token_text, start_index)
                    if start == -1: break
                    if token_type in self.styles: self.setFormat(start, len(token_text), self.styles[token_type])
                    start_index = start + len(token_text)

class InputGeneratorTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.vars = {}
        self.data_filename_path = None
        self.project_dir = os.getcwd()
        self.script_path = None
        self.process = None
        self.total_steps = 0
        self.nvml_handle = None
        if PYNVML_AVAILABLE:
            try: pynvml.nvmlInit(); self.nvml_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            except pynvml.NVMLError: self.nvml_handle = None
        self._create_widgets()
        self._update_ensemble_options()
        self.monitor_timer = QTimer(self); self.monitor_timer.setInterval(2000)
        self.monitor_timer.timeout.connect(self._update_monitors)

    def _create_widgets(self):
        main_layout = QHBoxLayout(self)
        settings_panel = QFrame(); settings_panel.setObjectName("Card"); settings_layout = QVBoxLayout(settings_panel)
        settings_layout.addWidget(QLabel("<b>Configurações de Simulação</b>"))
        proj_layout = QGridLayout(); proj_layout.addWidget(QLabel("Diretório do Projeto:"), 0, 0); self.proj_dir_edit = QLineEdit(self.project_dir); proj_layout.addWidget(self.proj_dir_edit, 1, 0); btn_select_dir = QPushButton("Selecionar..."); btn_select_dir.clicked.connect(self._select_project_dir); proj_layout.addWidget(btn_select_dir, 1, 1); settings_layout.addLayout(proj_layout)
        data_layout = QGridLayout(); data_layout.addWidget(QLabel("Arquivo de Entrada (.data):"), 0, 0); self.data_file_edit = QLineEdit("Nenhum arquivo carregado"); self.data_file_edit.setReadOnly(True); data_layout.addWidget(self.data_file_edit, 1, 0); btn_load_data = QPushButton("Carregar"); btn_load_data.clicked.connect(self._load_data_file); data_layout.addWidget(btn_load_data, 1, 1); settings_layout.addLayout(data_layout)
        grid_layout = QGridLayout(); grid_layout.setColumnStretch(1, 1)
        self._add_entry(grid_layout, 0, "force_field_file", "Campo de Força:", "CHO-2016.ff")
        self._add_entry(grid_layout, 1, "boundary", "Cond. de Contorno:", "p p p")
        self.timestep_entry = self._add_entry(grid_layout, 2, "timestep", "Passo de Tempo (fs):", "0.25")
        self.run_steps_entry = self._add_entry(grid_layout, 3, "run_steps", "Número de Passos:", "500000")
        self.mpi_cores_spinbox = self._add_spinbox(grid_layout, 4, "mpi_cores", "Núcleos CPU (MPI):", 1, 128, os.cpu_count() or 1)
        self.ensemble_combo = self._add_combo(grid_layout, 5, "ensemble", "Ensemble:", ["nvt", "npt", "nve"], "nvt")
        self.ensemble_combo.currentTextChanged.connect(self._update_ensemble_options)
        self.temp_start_entry = self._add_entry(grid_layout, 6, "temp_start", "Temp. Inicial (K):", "323.0")
        self.temp_end_entry = self._add_entry(grid_layout, 7, "temp_end", "Temp. Final (K):", "323.0")
        self.temp_damp_entry = self._add_entry(grid_layout, 8, "temp_damp", "Amort. Temp. (fs):", "100.0")
        self.press_start_entry = self._add_entry(grid_layout, 9, "press_start", "Pressão Inicial (atm):", "1.0")
        self.press_end_entry = self._add_entry(grid_layout, 10, "press_end", "Pressão Final (atm):", "1.0")
        self.press_damp_entry = self._add_entry(grid_layout, 11, "press_damp", "Amort. Pressão (fs):", "1000.0")
        settings_layout.addLayout(grid_layout)
        self.dump_check = self._add_check(settings_layout, "dump_traj", "Gerar dump.lammpstrj?", True)
        self.species_check = self._add_check(settings_layout, "species_log", "Gerar species.log?", True)
        settings_layout.addStretch()
        btn_generate = QPushButton("Gerar/Atualizar Script"); btn_generate.clicked.connect(self._generate_script)
        settings_layout.addWidget(btn_generate)
        output_panel = QFrame(); output_panel.setObjectName("Card"); output_layout = QVBoxLayout(output_panel)
        monitor_frame = QFrame(); monitor_layout = QGridLayout(monitor_frame)
        self.cpu_label = QLabel("CPU: N/A"); self.ram_label = QLabel("RAM: N/A"); self.gpu_label = QLabel("GPU: N/A")
        monitor_layout.addWidget(self.cpu_label, 0, 0); monitor_layout.addWidget(self.ram_label, 0, 1); monitor_layout.addWidget(self.gpu_label, 0, 2)
        self.progress_bar = QProgressBar(); self.progress_bar.setVisible(False); self.progress_bar.setTextVisible(True)
        monitor_layout.addWidget(self.progress_bar, 1, 0, 1, 3)
        output_layout.addWidget(monitor_frame)
        self.output_tab_view = QTabWidget()
        log_widget = QWidget(); log_layout = QVBoxLayout(log_widget); log_layout.setContentsMargins(0, 5, 0, 0)
        log_controls_layout = QHBoxLayout()
        self.run_button = QPushButton("Rodar Simulação"); self.run_button.setObjectName("AccentButton"); self.run_button.clicked.connect(self.run_simulation); self.run_button.setEnabled(False)
        self.stop_button = QPushButton("Parar Simulação"); self.stop_button.clicked.connect(self.stop_simulation); self.stop_button.setEnabled(False)
        log_controls_layout.addWidget(self.run_button); log_controls_layout.addWidget(self.stop_button); log_controls_layout.addStretch()
        self.log_text = QPlainTextEdit(); self.log_text.setReadOnly(True); self.log_text.setFont(QFont("Consolas", 10))
        log_layout.addLayout(log_controls_layout); log_layout.addWidget(self.log_text)
        editor_widget = QWidget(); editor_layout = QVBoxLayout(editor_widget); editor_layout.setContentsMargins(0, 5, 0, 0)
        self.script_editor_text = QPlainTextEdit(); self.script_editor_text.setFont(QFont("Consolas", 10))
        if PYGMENTS_AVAILABLE: self.highlighter = LammpsHighlighter(self.script_editor_text.document())
        btn_save_script = QPushButton("Salvar Script e Habilitar Execução"); btn_save_script.clicked.connect(self._save_script_from_editor)
        editor_layout.addWidget(self.script_editor_text); editor_layout.addWidget(btn_save_script)
        self.output_tab_view.addTab(log_widget, "Saída do LAMMPS"); self.output_tab_view.addTab(editor_widget, "Editor de Script (in.lammps)")
        output_layout.addWidget(self.output_tab_view); main_layout.addWidget(settings_panel, 1); main_layout.addWidget(output_panel, 2)

    def _add_spinbox(self, layout, row, key, label, min_val, max_val, default_val):
        lbl = QLabel(label); spinbox = QSpinBox(); spinbox.setRange(min_val, max_val); spinbox.setValue(default_val); layout.addWidget(lbl, row, 0); layout.addWidget(spinbox, row, 1); self.vars[key] = spinbox; return spinbox
    def _add_entry(self, layout, row, key, label, default_value):
        lbl = QLabel(label); entry = QLineEdit(default_value); layout.addWidget(lbl, row, 0); layout.addWidget(entry, row, 1); self.vars[key] = entry; return entry
    def _add_combo(self, layout, row, key, label, values, default_value):
        lbl = QLabel(label); combo = QComboBox(); combo.addItems(values); combo.setCurrentText(default_value); layout.addWidget(lbl, row, 0); layout.addWidget(combo, row, 1); self.vars[key] = combo; return combo
    def _add_check(self, layout, key, label, default_value):
        check = QCheckBox(label); check.setChecked(default_value); layout.addWidget(check); self.vars[key] = check; return check
    def _select_project_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Selecione o Diretório do Projeto", self.project_dir)
        if dir_path: self.project_dir = dir_path; self.proj_dir_edit.setText(dir_path); self._log(f"Diretório do projeto definido como: {dir_path}\n")
    def _load_data_file(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Selecione o arquivo .data", "", "LAMMPS Data (*.data);;All files (*.*)")
        if filepath: self.data_filename_path = os.path.abspath(filepath); self.data_file_edit.setText(os.path.basename(filepath))
    def _log(self, message):
        cursor = self.log_text.textCursor(); cursor.movePosition(cursor.MoveOperation.End); self.log_text.setTextCursor(cursor); self.log_text.insertPlainText(message); self.log_text.ensureCursorVisible()
    def _update_ensemble_options(self):
        ensemble = self.vars['ensemble'].currentText(); is_npt = ensemble == 'npt'; is_nvt_or_npt = ensemble in ['nvt', 'npt']
        self.temp_start_entry.setEnabled(is_nvt_or_npt); self.temp_end_entry.setEnabled(is_nvt_or_npt); self.temp_damp_entry.setEnabled(is_nvt_or_npt)
        self.press_start_entry.setEnabled(is_npt); self.press_end_entry.setEnabled(is_npt); self.press_damp_entry.setEnabled(is_npt)
    def _generate_script(self):
        if not self.data_filename_path: QMessageBox.critical(self, "Erro", "Por favor, carregue um arquivo .data primeiro."); return
        v = {key: var.text() if isinstance(var, QLineEdit) else var.currentText() if isinstance(var, QComboBox) else var.isChecked() if isinstance(var, QCheckBox) else var.value() for key, var in self.vars.items()}
        elements_str = "H O C"
        script_content = f"""# SCRIPT DE INPUT GERADO PELO ANALISADOR MULTIFUNCIONAL\n\n# ---- Configurações Iniciais ----\nunits           real\natom_style      charge\nboundary        {v['boundary']}\n\n# ---- Leitura do Sistema e Campo de Força ----\nread_data       {os.path.basename(self.data_filename_path)}\npair_style      reaxff NULL checkqeq yes\npair_coeff      * * {v['force_field_file']} {elements_str}\n\n# ---- Configurações de Vizinhança e Termodinâmica ----\nneighbor        2.5 bin\nneigh_modify    every 1 delay 0 check yes\nfix             qeq all qeq/reaxff 1 0.0 10.0 1.0e-6 reaxff\nthermo_style    custom step temp press vol density pe ke etotal enthalpy\nthermo_modify   line yaml\nthermo          1000\n\n# ---- Minimização de Energia ----\nminimize        1.0e-4 1.0e-6 1000 10000\n\n# ---- Dinâmica Molecular ----\nreset_timestep  0\ntimestep        {v['timestep']}\nvelocity        all create {v['temp_start']} 4928459 dist gaussian\n\n# ---- Saídas (Dumps) ----\n"""
        if v.get('dump_traj', False): script_content += f"dump            dmp all custom 1000 dump.lammpstrj id type element q x y z\ndump_modify     dmp element {elements_str}\n"
        if v.get('species_log', False): script_content += f"fix             spec all reaxff/species 1 1000 1000 species.log element {elements_str}\n"
        script_content += "\n# ---- Ensemble e Execução ----\n"
        if v['ensemble'] == 'nvt': script_content += f"fix             1 all nvt temp {v['temp_start']} {v['temp_end']} {v['temp_damp']}\n"
        elif v['ensemble'] == 'npt': script_content += f"fix             1 all npt temp {v['temp_start']} {v['temp_end']} {v['temp_damp']} iso {v['press_start']} {v['press_end']} {v['press_damp']}\n"
        else: script_content += "fix             1 all nve\n"
        script_content += f"\nrun             {v['run_steps']}\n"
        self.script_editor_text.setPlainText(script_content)
        self.output_tab_view.setCurrentWidget(self.output_tab_view.widget(1)); self._log("Template de script gerado. Verifique e salve no Editor de Script.\n"); self.run_button.setEnabled(False)
    def _save_script_from_editor(self):
        proj_dir = self.proj_dir_edit.text();
        if not os.path.isdir(proj_dir): QMessageBox.critical(self, "Erro", "O diretório do projeto não é válido."); return
        self.script_path = os.path.join(proj_dir, "in.lammps"); script_content = self.script_editor_text.toPlainText()
        try:
            with open(self.script_path, 'w') as f: f.write(script_content)
            QMessageBox.information(self, "Sucesso", f"Script salvo com sucesso em:\n{self.script_path}"); self.run_button.setEnabled(True); self._log(f"Script salvo. Simulação pronta para rodar.\n")
        except Exception as e: QMessageBox.critical(self, "Erro ao Salvar", f"Não foi possível salvar o script:\n{e}")
    def run_simulation(self):
        if self.process: QMessageBox.warning(self, "Aviso", "Uma simulação já está em execução."); return
        if not self.data_filename_path: QMessageBox.critical(self, "Erro", "Arquivo de dados não carregado."); return
        if not self.script_path: QMessageBox.critical(self, "Erro", "Script não salvo."); return
        lmp_path = os.path.abspath(os.path.join("bin", "lmp.exe"))
        if not os.path.exists(lmp_path): QMessageBox.critical(self, "Erro", f"Executável do LAMMPS não encontrado em:\n{lmp_path}"); return
        working_directory = self.proj_dir_edit.text()
        try:
            dest_data_path = os.path.join(working_directory, os.path.basename(self.data_filename_path))
            if os.path.abspath(self.data_filename_path) != os.path.abspath(dest_data_path): shutil.copy(self.data_filename_path, dest_data_path)
            ff_file = self.vars['force_field_file'].text()
            if os.path.exists(ff_file) and not os.path.exists(os.path.join(working_directory, ff_file)): shutil.copy(ff_file, working_directory)
        except Exception as e: QMessageBox.critical(self, "Erro de Preparação", f"Falha ao copiar arquivos para o diretório de trabalho: {e}"); return
        try: self.total_steps = int(self.run_steps_entry.text())
        except (ValueError, TypeError): QMessageBox.critical(self, "Erro", "O número de passos da simulação é inválido."); return
        num_cores = self.mpi_cores_spinbox.value(); script_filename = os.path.basename(self.script_path)
        program = ""; args = []
        if num_cores > 1:
            mpirun_path = os.path.abspath(os.path.join("bin", "mpirun.exe"))
            if not os.path.exists(mpirun_path): QMessageBox.critical(self, "Erro", f"mpirun.exe não encontrado em:\n{mpirun_path}\nExecutando com 1 núcleo."); program = lmp_path; args = ["-in", script_filename]
            else: program = mpirun_path; args = ["-np", str(num_cores), lmp_path, "-in", script_filename]
        else: program = lmp_path; args = ["-in", script_filename]
        self.progress_bar.setValue(0); self.progress_bar.setFormat("Iniciando..."); self.progress_bar.setVisible(True); self.monitor_timer.start(); self._update_monitors()
        self.process = QProcess(); self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._on_ready_read); self.process.finished.connect(self._on_finished)
        self.log_text.clear(); self._log(f"Diretório de Trabalho: {working_directory}\n"); self._log(f"Executando comando: {program} {' '.join(args)}\n\n")
        self.process.setWorkingDirectory(working_directory); self.process.start(program, args)
        self.run_button.setEnabled(False); self.stop_button.setEnabled(True); self.output_tab_view.setCurrentIndex(0)

    def _on_ready_read(self):
        if not self.process: return
        output = self.process.readAllStandardOutput().data().decode('utf-8', errors='ignore')
        self._log(output)
        last_step = -1
        for line in output.strip().split('\n'):
            parts = line.strip().split()
            if parts and parts[0].isdigit():
                try:
                    current_step = int(parts[0])
                    if current_step > last_step:
                        last_step = current_step
                except (ValueError, IndexError):
                    continue
        if last_step > -1 and self.total_steps > 0:
            progress = int((last_step / self.total_steps) * 100)
            self.progress_bar.setValue(progress)
            self.progress_bar.setFormat(f"Progresso: {progress}% (Passo {last_step}/{self.total_steps})")
    
    def _on_finished(self):
        if self.process is None: return
        self.monitor_timer.stop()
        exit_code = self.process.exitCode(); exit_status = self.process.exitStatus()
        if exit_status == QProcess.ExitStatus.NormalExit and exit_code == 0:
            self._log("\n--- SIMULAÇÃO CONCLUÍDA COM SUCESSO ---\n"); self.progress_bar.setValue(100); self.progress_bar.setFormat(f"Concluído!")
        else:
            self._log(f"\n--- SIMULAÇÃO INTERROMPIDA OU FALHOU (Código: {exit_code}) ---\n"); current_progress = self.progress_bar.value(); self.progress_bar.setFormat(f"Interrompido em {current_progress}%")
        self.run_button.setEnabled(True); self.stop_button.setEnabled(False)
        self.process.deleteLater(); self.process = None
        QTimer.singleShot(5000, lambda: self.progress_bar.setVisible(False) if self.progress_bar else None)

    def stop_simulation(self):
        if self.process: self.process.kill()

    def _update_monitors(self):
        cpu_usage = psutil.cpu_percent(); self.cpu_label.setText(f"<b>CPU:</b> {cpu_usage:.1f}%")
        ram = psutil.virtual_memory(); self.ram_label.setText(f"<b>RAM:</b> {ram.percent}% ({ram.used/1e9:.1f}/{ram.total/1e9:.1f} GB)")
        if self.nvml_handle:
            try:
                gpu_info = pynvml.nvmlDeviceGetUtilizationRates(self.nvml_handle); mem_info = pynvml.nvmlDeviceGetMemoryInfo(self.nvml_handle)
                self.gpu_label.setText(f"<b>GPU:</b> {gpu_info.gpu}% | <b>VRAM:</b> {mem_info.used/mem_info.total*100:.1f}%")
            except pynvml.NVMLError: self.gpu_label.setText("<b>GPU:</b> Erro")
        else: self.gpu_label.setText("<b>GPU:</b> N/A")