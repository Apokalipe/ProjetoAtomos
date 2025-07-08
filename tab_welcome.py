# tab_welcome.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import qtawesome as qta

class WelcomeTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        # 1. Ícone Grande no Centro
        icon_size = 128
        # --- CORREÇÃO: Armazenar o label do ícone como um atributo da classe ---
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 2. Título Principal
        title_font = QFont("Segoe UI", 36, QFont.Weight.Bold)
        title_label = QLabel("Átomos")
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 3. Subtítulo
        subtitle_font = QFont("Segoe UI", 14)
        subtitle_label = QLabel("Analisador Multifuncional LAMMPS")
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setStyleSheet("color: #A0A0A0;")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Adiciona os widgets ao layout
        layout.addWidget(self.icon_label)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)

        # Define o estado inicial do tema
        self.update_theme('dark')

    # --- CORREÇÃO: Adicionar o método update_theme que faltava ---
    def update_theme(self, theme):
        """Atualiza a cor do ícone com base no tema."""
        icon_color = '#e0e0e0' if theme == 'dark' else '#333333'
        icon_pixmap = qta.icon('fa5s.atom', color=icon_color).pixmap(128, 128)
        self.icon_label.setPixmap(icon_pixmap)