"""
Diálogo de activación de licencia
Muestra el ID de máquina y solicita la clave de licencia
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QFrame,
                             QApplication)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QClipboard
from app.utils.notify import notify_success, notify_error, notify_warning
from app.modules.license_manager import LicenseManager
from app.ui.transparent_buttons import apply_btn_primary, apply_btn_success, apply_btn_cancel
from app.i18n import tr


class ActivationDialog(QDialog):
    """Diálogo para activar la licencia del programa"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.license_manager = LicenseManager()
        self.activated = False
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle(tr("Activación de RedMovilPOS"))
        self.setWindowFlags(
            Qt.Dialog |
            Qt.WindowTitleHint |
            Qt.WindowCloseButtonHint
        )
        from PyQt5.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        max_h = int(screen.height() * 0.92)
        self.setFixedWidth(550)
        self.resize(550, min(480, max_h))

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        # Título principal
        title_label = QLabel(tr("Activación del Programa"))
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #ffffff;
            padding: 8px;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Mensaje informativo
        info_label = QLabel(
            tr("Para activar el programa, proporcione el ID de Máquina "
            "al proveedor para obtener su clave de licencia.")
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #7B88A0; padding: 5px;")
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)

        layout.addSpacing(10)

        # --- Sección ID de Máquina ---
        machine_title = QLabel(tr("ID de Máquina"))
        machine_title.setStyleSheet("""
            font-size: 13px;
            font-weight: bold;
            color: #5E81AC;
            padding: 2px 5px;
        """)
        layout.addWidget(machine_title)

        # Frame para ID de máquina
        machine_frame = QFrame()
        machine_frame.setFrameShape(QFrame.StyledPanel)
        machine_frame.setStyleSheet("""
            QFrame {
                border: 2px solid #5E81AC;
                border-radius: 5px;
                background-color: #2E3440;
            }
        """)
        machine_frame.setFixedHeight(110)
        machine_layout = QVBoxLayout(machine_frame)
        machine_layout.setSpacing(8)
        machine_layout.setContentsMargins(15, 12, 15, 12)

        # ID de máquina (solo lectura)
        self.machine_id_label = QLabel(self.license_manager.get_machine_id())
        self.machine_id_label.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
            font-family: 'Consolas', 'Courier New', monospace;
            color: #88C0D0;
            background-color: #2E3440;
            border-radius: 5px;
            border: none;
        """)
        self.machine_id_label.setAlignment(Qt.AlignCenter)
        self.machine_id_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.machine_id_label.setFixedHeight(40)
        machine_layout.addWidget(self.machine_id_label)

        # Botón copiar
        btn_copiar = QPushButton(tr("Copiar ID"))
        btn_copiar.clicked.connect(self.copiar_machine_id)
        apply_btn_primary(btn_copiar)
        btn_copiar.setMaximumWidth(120)

        copiar_layout = QHBoxLayout()
        copiar_layout.addStretch()
        copiar_layout.addWidget(btn_copiar)
        copiar_layout.addStretch()
        machine_layout.addLayout(copiar_layout)

        layout.addWidget(machine_frame)

        layout.addSpacing(15)

        # --- Sección Clave de Licencia ---
        license_title = QLabel(tr("Clave de Licencia"))
        license_title.setStyleSheet("""
            font-size: 13px;
            font-weight: bold;
            color: #A3BE8C;
            padding: 2px 5px;
        """)
        layout.addWidget(license_title)

        # Frame para clave de licencia
        license_frame = QFrame()
        license_frame.setFrameShape(QFrame.StyledPanel)
        license_frame.setStyleSheet("""
            QFrame {
                border: 2px solid #A3BE8C;
                border-radius: 5px;
                background-color: #2E3440;
            }
        """)
        license_frame.setFixedHeight(75)
        license_layout = QVBoxLayout(license_frame)
        license_layout.setSpacing(0)
        license_layout.setContentsMargins(15, 12, 15, 12)

        # Input de clave
        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText(tr("Introduzca la clave (XXXX-XXXX-XXXX-XXXX)"))
        self.license_input.setStyleSheet("""
            font-size: 14px;
            border: 2px solid #4C566A;
            border-radius: 5px;
            background-color: #3B4252;
            color: #ffffff;
        """)
        self.license_input.setAlignment(Qt.AlignCenter)
        self.license_input.setFixedHeight(45)
        self.license_input.returnPressed.connect(self.activar)
        license_layout.addWidget(self.license_input)

        layout.addWidget(license_frame)

        layout.addSpacing(20)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        btn_activar = QPushButton(tr("Activar"))
        btn_activar.clicked.connect(self.activar)
        apply_btn_success(btn_activar)

        btn_salir = QPushButton(tr("Salir"))
        btn_salir.clicked.connect(self.reject)
        apply_btn_cancel(btn_salir)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_activar)
        btn_layout.addWidget(btn_salir)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

    def copiar_machine_id(self):
        """Copia el ID de máquina al portapapeles"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.license_manager.get_machine_id())
        notify_success(
            self,
            tr("Copiado"),
            tr("ID de Máquina copiado al portapapeles")
        )

    def activar(self):
        """Intenta activar con la clave introducida"""
        clave = self.license_input.text().strip()

        if not clave:
            notify_warning(
                self,
                tr("Clave Requerida"),
                tr("Por favor, introduzca la clave de licencia")
            )
            return

        # Intentar activar
        exito, mensaje = self.license_manager.activate(clave)

        if exito:
            self.activated = True
            notify_success(
                self,
                tr("Activación Exitosa"),
                tr("El programa se ha activado correctamente.\n\n"
                "Gracias por usar RedMovilPOS.")
            )
            self.accept()
        else:
            notify_error(
                self,
                tr("Error de Activación"),
                tr("No se pudo activar el programa:\n\n{mensaje}\n\n"
                "Verifique que la clave sea correcta para este equipo.", mensaje=mensaje)
            )

    def is_activated(self):
        """Devuelve True si se activó correctamente"""
        return self.activated
