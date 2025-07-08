# tab_analysis_hub.py
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QStackedWidget, 
                             QListWidgetItem, QPushButton, QLabel, QFrame, QSpacerItem, QSizePolicy)
from PyQt6.QtCore import QSize, Qt
import qtawesome as qta

from tab_species import SpeciesAnalysisTab; from tab_thermo import ThermoAnalysisTab
from tab_kinetic import KineticAnalysisTab; from tab_analysis import AnalysisTab

class AnalysisHubTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.is_menu_expanded = True
        self.expanded_width = 200
        self.collapsed_width = 65
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.nav_container = QFrame()
        self.nav_container.setObjectName("AnalysisNavContainer")
        self.nav_container.setFixedWidth(self.expanded_width)
        nav_container_layout = QVBoxLayout(self.nav_container)
        nav_container_layout.setContentsMargins(0, 0, 0, 0)
        nav_container_layout.setSpacing(0)

        self.nav_list = QListWidget()
        self.nav_list.setObjectName("AnalysisNavList")
        self.nav_list.setIconSize(QSize(24, 24))
        
        # --- CORREÇÃO APLICADA AQUI ---
        self.nav_list.setStyleSheet("""
            /* O seletor QListWidget agora também afeta o container do item */
            QListWidget#AnalysisNavList {
                border: none;
                padding-top: 10px;
                font-size: 11pt;
            }
            QListWidget#AnalysisNavList::item {
                padding: 15px;
            }
            /* Remove o retângulo pontilhado de foco */
            QListWidget#AnalysisNavList:focus {
                outline: 0;
                border: none;
            }
            /* Também remove o foco do item individual */
            QListWidget#AnalysisNavList::item:focus {
                outline: 0;
                border: none;
            }
            /* A cor do item selecionado agora é controlada pelo QSS global */
            QListWidget#AnalysisNavList::item:selected {
                 /* Apenas para garantir que a borda de foco seja sobrescrita */
                border: none;
            }
        """)
        
        self.toggle_button = QPushButton()
        self.toggle_button.setObjectName("ToggleButton")
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(True)
        self.toggle_button.clicked.connect(self.toggle_menu)
        self.toggle_button.setFlat(True)
        self.toggle_button.setIconSize(QSize(24, 24))
        self.toggle_button.setFixedHeight(55)
        
        nav_container_layout.addWidget(self.toggle_button)
        nav_container_layout.addWidget(self.nav_list)
        
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.nav_container)
        main_layout.addWidget(self.stacked_widget)
        
        self.nav_list.currentRowChanged.connect(self.stacked_widget.setCurrentIndex)
        
        self.tab_info = [
            (SpeciesAnalysisTab(), "Análise de Espécies", "fa5s.flask"),
            (ThermoAnalysisTab(), "Análise Termodinâmica", "fa5s.chart-line"),
            (KineticAnalysisTab(), "Análise Cinética", "fa5s.hourglass-half"),
            (AnalysisTab(), "Estrutura e Transporte", "fa5s.sitemap")
        ]
        
        self.nav_list.setCurrentRow(0)
        self.update_theme('dark')

    def _add_analysis_tab(self, widget, label, icon_name, icon_color):
        icon = qta.icon(icon_name, color=icon_color)
        item = QListWidgetItem(icon, label)
        item.setData(Qt.ItemDataRole.UserRole, (label, icon_name))
        item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.nav_list.addItem(item)
        self.stacked_widget.addWidget(widget)

    def toggle_menu(self):
        self.is_menu_expanded = not self.is_menu_expanded
        self.update_menu_state()

    def update_menu_state(self):
        self.toggle_button.setChecked(self.is_menu_expanded)
        icon_color = 'white' if self.palette().windowText().color().lightness() < 128 else '#333'
        
        if self.is_menu_expanded:
            self.nav_container.setFixedWidth(self.expanded_width)
            self.toggle_button.setText(" Recolher Menu")
            self.toggle_button.setIcon(qta.icon('fa5s.align-justify', color=icon_color))
            self.toggle_button.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            for i in range(self.nav_list.count()):
                item = self.nav_list.item(i)
                label, _ = item.data(Qt.ItemDataRole.UserRole)
                item.setText(label)
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        else:
            self.nav_container.setFixedWidth(self.collapsed_width)
            self.toggle_button.setText("")
            self.toggle_button.setIcon(qta.icon('fa5s.bars', color=icon_color))
            self.toggle_button.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            for i in range(self.nav_list.count()):
                item = self.nav_list.item(i)
                item.setText("")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    def update_theme(self, theme):
        current_selection = self.nav_list.currentRow()
        if current_selection == -1: current_selection = 0
        self.nav_list.clear()
        icon_color = 'white' if theme == 'dark' else '#333'
        for widget, label, icon_name in self.tab_info:
            self._add_analysis_tab(widget, label, icon_name, icon_color)
        self.nav_list.setCurrentRow(current_selection)
        self.update_menu_state()