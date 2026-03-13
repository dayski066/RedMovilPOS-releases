"""
Diálogo "Acerca de" con información de la aplicación
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QFont
from config import APP_VERSION, APP_NAME
from app.ui.styles import app_icon
from app.ui.transparent_buttons import apply_btn_cancel
from app.i18n import tr
import os


class AboutDialog(QDialog):
    """Ventana de información sobre la aplicación"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Acerca de"))
        self.setMinimumWidth(450)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Logo
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)
        logo_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'logos', 'ICONO.png')
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled_pixmap = pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
            logo_label.setMinimumHeight(150)
        else:
            logo_label.setText("📱")
            logo_label.setStyleSheet("font-size: 64px;")
        layout.addWidget(logo_label)

        # Nombre de la aplicación
        name_label = QLabel(APP_NAME)
        name_font = QFont()
        name_font.setPointSize(20)
        name_font.setBold(True)
        name_label.setFont(name_font)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet("color: #88C0D0;")
        layout.addWidget(name_label)

        # Versión
        version_label = QLabel(f"{tr('Versión')} {APP_VERSION}")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("color: #7B88A0; font-size: 14px;")
        layout.addWidget(version_label)

        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: transparent; color: #88C0D0; border: 2px solid #88C0D0; border-radius: 6px;")
        layout.addWidget(separator)

        # Descripción
        desc_label = QLabel(
            tr("Sistema integral de punto de venta (POS)\npara gestión de ventas, compras, inventario,\nservicio técnico y caja.")
        )
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #D8DEE9; font-size: 12px; line-height: 1.5;")
        layout.addWidget(desc_label)

        # Separador
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setStyleSheet("background-color: transparent; color: #88C0D0; border: 2px solid #88C0D0; border-radius: 6px;")
        layout.addWidget(separator2)

        # Desarrollador
        dev_label = QLabel(tr("Desarrollado por") + ":")
        dev_label.setAlignment(Qt.AlignCenter)
        dev_label.setStyleSheet("color: #7B88A0; font-size: 11px;")
        layout.addWidget(dev_label)

        dev_name = QLabel("RABI EL-OUAHIDI Y OTROS ESPJ")
        dev_name.setAlignment(Qt.AlignCenter)
        dev_name.setStyleSheet("color: #88C0D0; font-size: 13px; font-weight: bold;")
        layout.addWidget(dev_name)

        # Copyright
        copyright_label = QLabel(f"© 2024-2025 {tr('Todos los derechos reservados')}")
        copyright_label.setAlignment(Qt.AlignCenter)
        copyright_label.setStyleSheet("color: #4C566A; font-size: 10px;")
        layout.addWidget(copyright_label)

        layout.addStretch()

        # Botón cerrar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_close = QPushButton(tr("Cerrar"))
        btn_close.setFixedSize(100, 36)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.accept)
        apply_btn_cancel(btn_close)
        btn_layout.addWidget(btn_close)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)
