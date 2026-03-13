"""
Diálogo selector de tutoriales interactivos.
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QListWidget, QListWidgetItem)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from app.i18n import tr


# Definición de tours disponibles: (clave_tour, etiqueta_visible, disponible_sin_admin)
_TOUR_ITEMS = [
    ("cliente",    "👤  " + "Cómo crear un cliente",          True),
    ("factura",    "🧾  " + "Cómo crear una factura",         True),
    ("producto",   "📦  " + "Cómo añadir un producto",        True),
    ("reparacion", "🔧  " + "Cómo crear una reparación",      True),
    ("compra",     "🛒  " + "Cómo registrar una compra",      True),
    ("tpv",        "💳  " + "Cómo hacer una venta TPV",       True),
    ("caja",       "🏦  " + "Apertura y cierre de caja",      True),
    ("usuario",    "👥  " + "Crear usuario y configurar 2FA", False),
    ("impresoras", "⚙️   " + "Configurar impresoras",          False),
]


class GuideDialog(QDialog):
    def __init__(self, parent=None, is_admin: bool = True):
        super().__init__(parent)
        self.setWindowTitle(tr("Guía de Uso"))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(420)
        self.setStyleSheet("""
            QDialog {
                background-color: #2E3440;
            }
            QLabel {
                color: #D8DEE9;
            }
            QListWidget {
                background-color: #3B4252;
                border: 1px solid #4C566A;
                border-radius: 8px;
                color: #ECEFF4;
                font-size: 14px;
                padding: 4px;
                outline: none;
            }
            QListWidget::item {
                padding: 10px 14px;
                border-radius: 6px;
            }
            QListWidget::item:selected {
                background-color: #5E81AC;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background-color: #434C5E;
            }
            QPushButton {
                border: 1px solid #4C566A;
                border-radius: 6px;
                padding: 8px 20px;
                color: #D8DEE9;
                background: #3B4252;
                font-size: 13px;
            }
            QPushButton:hover { background: #434C5E; color: #ffffff; }
            QPushButton#btnIniciar {
                background: #5E81AC;
                border-color: #81A1C1;
                color: #ECEFF4;
                font-weight: bold;
            }
            QPushButton#btnIniciar:hover { background: #81A1C1; }
            QPushButton#btnIniciar:disabled { background: #4C566A; color: #616E88; border-color: #4C566A; }
        """)

        self._tour_key = None
        self._is_admin = is_admin
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # Título
        lbl_title = QLabel(tr("Guía de Uso"))
        font = QFont()
        font.setBold(True)
        font.setPointSize(16)
        lbl_title.setFont(font)
        lbl_title.setStyleSheet("color: #ECEFF4;")
        layout.addWidget(lbl_title)

        # Subtítulo
        lbl_sub = QLabel(tr("Selecciona un tutorial:"))
        lbl_sub.setStyleSheet("color: #88C0D0; font-size: 13px;")
        layout.addWidget(lbl_sub)

        # Lista de tutoriales
        self.list_widget = QListWidget()
        self.list_widget.setSpacing(2)
        self.list_widget.itemDoubleClicked.connect(self._iniciar)
        self.list_widget.currentRowChanged.connect(self._on_selection_change)

        for key, label, public in _TOUR_ITEMS:
            if public or self._is_admin:
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, key)
                self.list_widget.addItem(item)

        layout.addWidget(self.list_widget)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton(tr("Cancelar"))
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        self.btn_iniciar = QPushButton(f"▶  {tr('Iniciar')}")
        self.btn_iniciar.setObjectName("btnIniciar")
        self.btn_iniciar.setEnabled(False)
        self.btn_iniciar.clicked.connect(self._iniciar)
        btn_layout.addWidget(self.btn_iniciar)

        layout.addLayout(btn_layout)

        # Seleccionar primer ítem
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def _on_selection_change(self, row: int):
        self.btn_iniciar.setEnabled(row >= 0)

    def _iniciar(self):
        item = self.list_widget.currentItem()
        if item:
            self._tour_key = item.data(Qt.UserRole)
            self.accept()

    def get_tour_seleccionado(self) -> str | None:
        return self._tour_key
