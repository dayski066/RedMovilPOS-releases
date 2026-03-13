"""
Diálogo de información de licencia (solo lectura)
Muestra el estado actual de la licencia sin permitir modificaciones
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QGridLayout, QApplication)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from app.ui.styles import app_icon
from app.modules.license_manager import LicenseManager
from app.i18n import tr
from app.ui.transparent_buttons import apply_btn_cancel
import os
import json
from datetime import datetime


class LicenseInfoDialog(QDialog):
    """Ventana de información de licencia (solo lectura)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Información de Licencia"))
        self.setFixedSize(500, 380)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.license_manager = LicenseManager()
        self.setup_ui()
        self.cargar_info_licencia()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Título
        title_label = QLabel(tr("Estado de Licencia"))
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #88C0D0;")
        layout.addWidget(title_label)

        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: transparent; color: #88C0D0; border: 2px solid #88C0D0; border-radius: 6px;")
        layout.addWidget(separator)

        # Grid de información
        info_grid = QGridLayout()
        info_grid.setSpacing(15)
        info_grid.setColumnStretch(1, 1)

        # ID de Máquina
        lbl_machine_title = QLabel(tr("ID de Máquina") + ":")
        lbl_machine_title.setStyleSheet("color: #7B88A0; font-size: 12px;")
        info_grid.addWidget(lbl_machine_title, 0, 0, Qt.AlignRight)

        machine_id_layout = QHBoxLayout()
        self.lbl_machine_id = QLabel()
        self.lbl_machine_id.setStyleSheet("color: #88C0D0; font-size: 13px; font-weight: bold;")
        self.lbl_machine_id.setTextInteractionFlags(Qt.TextSelectableByMouse)
        machine_id_layout.addWidget(self.lbl_machine_id)

        btn_copy = QPushButton()
        btn_copy.setIcon(app_icon("mdi.content-copy", color="#D8DEE9", size=16))
        btn_copy.setFixedSize(28, 28)
        btn_copy.setCursor(Qt.PointingHandCursor)
        btn_copy.setToolTip(tr("Copiar ID de Máquina"))
        btn_copy.clicked.connect(self._copiar_machine_id)
        btn_copy.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #4C566A;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #4C566A;
            }
        """)
        machine_id_layout.addWidget(btn_copy)
        machine_id_layout.addStretch()

        info_grid.addLayout(machine_id_layout, 0, 1)

        # Estado
        lbl_estado_title = QLabel(tr("Estado") + ":")
        lbl_estado_title.setStyleSheet("color: #7B88A0; font-size: 12px;")
        info_grid.addWidget(lbl_estado_title, 1, 0, Qt.AlignRight)

        self.lbl_estado = QLabel()
        self.lbl_estado.setStyleSheet("font-size: 13px; font-weight: bold;")
        info_grid.addWidget(self.lbl_estado, 1, 1)

        # Fecha de activación
        lbl_fecha_title = QLabel(tr("Fecha de Activación") + ":")
        lbl_fecha_title.setStyleSheet("color: #7B88A0; font-size: 12px;")
        info_grid.addWidget(lbl_fecha_title, 2, 0, Qt.AlignRight)

        self.lbl_fecha = QLabel()
        self.lbl_fecha.setStyleSheet("color: #D8DEE9; font-size: 13px;")
        info_grid.addWidget(self.lbl_fecha, 2, 1)

        # Tipo de licencia
        lbl_tipo_title = QLabel(tr("Tipo de Licencia") + ":")
        lbl_tipo_title.setStyleSheet("color: #7B88A0; font-size: 12px;")
        info_grid.addWidget(lbl_tipo_title, 3, 0, Qt.AlignRight)

        self.lbl_tipo = QLabel()
        self.lbl_tipo.setStyleSheet("color: #D8DEE9; font-size: 13px;")
        info_grid.addWidget(self.lbl_tipo, 3, 1)

        layout.addLayout(info_grid)

        # Separador
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setStyleSheet("background-color: transparent; color: #88C0D0; border: 2px solid #88C0D0; border-radius: 6px;")
        layout.addWidget(separator2)

        # Nota informativa
        nota_label = QLabel(tr("La licencia está vinculada al hardware de este equipo."))
        nota_label.setAlignment(Qt.AlignCenter)
        nota_label.setStyleSheet("color: #4C566A; font-size: 11px; font-style: italic;")
        layout.addWidget(nota_label)

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

    def cargar_info_licencia(self):
        """Carga y muestra la información de la licencia actual"""
        # ID de Máquina
        self.lbl_machine_id.setText(self.license_manager.get_machine_id())

        # Verificar si está activado
        is_activated = self.license_manager.is_activated()

        if is_activated:
            self.lbl_estado.setText("✓ " + tr("Activa"))
            self.lbl_estado.setStyleSheet("color: #88C0D0; font-size: 13px; font-weight: bold;")
            self.lbl_tipo.setText(tr("Licencia Perpetua"))

            # Leer fecha de activación del archivo
            fecha_activacion = self._obtener_fecha_activacion()
            if fecha_activacion:
                self.lbl_fecha.setText(fecha_activacion)
            else:
                self.lbl_fecha.setText("-")
        else:
            self.lbl_estado.setText("✗ " + tr("Sin Activar"))
            self.lbl_estado.setStyleSheet("color: #BF616A; font-size: 13px; font-weight: bold;")
            self.lbl_fecha.setText("-")
            self.lbl_tipo.setText("-")

    def _obtener_fecha_activacion(self):
        """Obtiene la fecha de activación del archivo de licencia"""
        try:
            license_file = self.license_manager.LICENSE_FILE
            if os.path.exists(license_file):
                with open(license_file, 'r') as f:
                    data = json.load(f)
                    activated_at = data.get('activated_at', '')
                    if activated_at:
                        # Parsear y formatear la fecha
                        dt = datetime.fromisoformat(activated_at)
                        return dt.strftime("%d/%m/%Y %H:%M")
        except (OSError, ValueError, RuntimeError):
            pass
        return None

    def _copiar_machine_id(self):
        """Copia el ID de máquina al portapapeles"""
        machine_id = self.license_manager.get_machine_id()
        clipboard = QApplication.clipboard()
        clipboard.setText(machine_id)

        # Feedback visual temporal
        self.lbl_machine_id.setText(f"{machine_id} ✓")
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.lbl_machine_id.setText(machine_id))

