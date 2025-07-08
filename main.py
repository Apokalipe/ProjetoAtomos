# main.py
import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTabWidget, QPushButton, QLabel, QFrame)
from PyQt6.QtCore import QFile, QTextStream, Qt, QPoint
from PyQt6.QtGui import QIcon
import qtawesome as qta
import pyqtgraph as pg

# (código de SSL - inalterado)
import ssl
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError: pass
else: ssl._create_default_https_context = _create_unverified_https_context

from tab_welcome import WelcomeTab
from tab_builder import SystemBuilderTab
from tab_control import InputGeneratorTab
from tab_analysis_hub import AnalysisHubTab

class CustomTitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5, 0, 5, 0)
        self.layout.setSpacing(0)

        self.icon_label = QLabel()
        self.title_label = QLabel("Átomos - Analisador Multifuncional LAMMPS")
        self.title_label.setObjectName("TitleLabel")
        
        self.layout.addWidget(self.icon_label)
        self.layout.addWidget(self.title_label)
        self.layout.addStretch()

        self.theme_button = QPushButton()
        self.minimize_button = QPushButton()
        self.maximize_button = QPushButton()
        self.close_button = QPushButton()

        self.theme_button.clicked.connect(self.parent.toggle_theme)
        self.minimize_button.clicked.connect(self.parent.showMinimized)
        self.maximize_button.clicked.connect(self.toggle_maximize)
        self.close_button.clicked.connect(self.parent.close)

        for btn in [self.theme_button, self.minimize_button, self.maximize_button, self.close_button]:
            btn.setFixedSize(45, 30)
            self.layout.addWidget(btn)

        self.start_move_pos = None
        
        # --- CORREÇÃO: Centralizar a atualização do tema ---
        self.update_theme('dark') # Define o estado visual inicial

    # --- CORREÇÃO: Método dedicado para atualizar a aparência da barra de título ---
    def update_theme(self, theme):
        """Atualiza todos os ícones e estilos da barra de título."""
        if theme == 'dark':
            icon_color = '#e0e0e0'
            hover_color = '#555'
        else:
            icon_color = '#333333'
            hover_color = '#e0e0e0'

        # Atualiza ícones
        self.icon_label.setPixmap(qta.icon('fa5s.atom', color=icon_color).pixmap(22, 22))
        theme_icon = 'fa5s.lightbulb' if theme == 'dark' else 'fa5s.moon'
        self.theme_button.setIcon(qta.icon(theme_icon, color=icon_color))
        self.minimize_button.setIcon(qta.icon('fa5s.window-minimize', color=icon_color))
        self.maximize_button.setIcon(qta.icon('fa5s.window-maximize', color=icon_color))
        self.close_button.setIcon(qta.icon('fa5s.times', color=icon_color))

        # Atualiza estilos (especialmente hover)
        for btn in [self.theme_button, self.minimize_button, self.maximize_button]:
            btn.setStyleSheet(f"""
                QPushButton {{ border: none; background-color: transparent; }}
                QPushButton:hover {{ background-color: {hover_color}; }}
            """)
        
        self.close_button.setStyleSheet("""
            QPushButton { border: none; background-color: transparent; }
            QPushButton:hover { background-color: #E81123; }
        """)

    def toggle_maximize(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
        else:
            self.parent.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.parent.isMaximized():
            self.start_move_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.start_move_pos:
            delta = event.globalPosition().toPoint() - self.start_move_pos
            self.parent.move(self.parent.pos() + delta)
            self.start_move_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.start_move_pos = None
    
    def mouseDoubleClickEvent(self, event):
        self.toggle_maximize()
        
class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_theme = 'dark'
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint); self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("Átomos - Analisador Multifuncional LAMMPS"); self.setGeometry(100, 100, 1400, 900)
        self.main_container = QFrame(); self.main_container.setObjectName("MainWindowContainer")
        container_layout = QVBoxLayout(self.main_container); container_layout.setContentsMargins(0,0,0,0); container_layout.setSpacing(0)
        self.title_bar = CustomTitleBar(self); container_layout.addWidget(self.title_bar)
        separator = QFrame(); separator.setFrameShape(QFrame.Shape.HLine); separator.setFrameShadow(QFrame.Shadow.Sunken); container_layout.addWidget(separator)
        content_widget = QWidget(); content_layout = QVBoxLayout(content_widget); content_layout.setContentsMargins(0, 0, 0, 0); self.tab_view = QTabWidget(); content_layout.addWidget(self.tab_view); container_layout.addWidget(content_widget)
        self.setCentralWidget(self.main_container)
        self.welcome_tab = WelcomeTab(); self.builder_tab = SystemBuilderTab(); self.control_tab = InputGeneratorTab(); self.analysis_hub = AnalysisHubTab()
        self.tab_view.addTab(self.welcome_tab, "Início"); self.tab_view.addTab(self.builder_tab, "Construtor de Sistema"); self.tab_view.addTab(self.control_tab, "Controle da Simulação"); self.tab_view.addTab(self.analysis_hub, "Análises")
    
    def toggle_theme(self):
        if self.current_theme == 'dark':
            self.current_theme = 'light'
            self.load_stylesheet('light_theme.qss')
            pg.setConfigOption('background', '#ffffff'); pg.setConfigOption('foreground', '#1a1a1a')
        else:
            self.current_theme = 'dark'
            self.load_stylesheet('dark_theme.qss')
            pg.setConfigOption('background', '#2c2e3a'); pg.setConfigOption('foreground', '#e0e0e0')

        # --- CORREÇÃO: Delegar a atualização para os componentes ---
        self.title_bar.update_theme(self.current_theme)
        self.welcome_tab.update_theme(self.current_theme)
        self.analysis_hub.update_theme(self.current_theme)

    def load_stylesheet(self, filename):
        app = QApplication.instance()
        style_file = QFile(filename)
        if style_file.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text):
            stream = QTextStream(style_file)
            app.setStyleSheet(stream.readAll())
        else:
            print(f"Não foi possível carregar o arquivo de estilo: {filename}")

    def closeEvent(self, event):
        if hasattr(self, 'control_tab'): self.control_tab.stop_simulation()
        event.accept()

if __name__ == '__main__':
    # ... (código inalterado) ...
    import multiprocessing
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    
    icon_path = 'atom_icon.png' 
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    else:
        print(f"Aviso: Ícone '{icon_path}' não encontrado. Usando ícone padrão.")
        app.setWindowIcon(qta.icon('fa5s.atom'))
        
    if sys.platform == 'win32':
        import ctypes
        myappid = 'mycompany.atomos.analisador.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        
    main_window = MainApp()
    main_window.load_stylesheet('dark_theme.qss')
    main_window.show()
    sys.exit(app.exec())