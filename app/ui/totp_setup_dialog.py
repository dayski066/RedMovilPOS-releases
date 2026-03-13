"""
Dialog para configurar TOTP 2FA (Autenticacion en Dos Pasos)
Muestra QR para escanear con Google Authenticator y verifica el primer codigo.
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QStackedWidget, QWidget)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage
from app.ui.transparent_buttons import apply_btn_primary, apply_btn_success, apply_btn_cancel
from app.utils.notify import notify_success, notify_error, notify_warning
from app.i18n import tr
import qrcode
import io


class TOTPSetupDialog(QDialog):
    """Dialog de configuracion de TOTP 2FA con QR y verificacion"""

    def __init__(self, db, auth_manager, usuario_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.auth_manager = auth_manager
        self.usuario_id = usuario_id
        self.secret = None
        self.setup_ui()
        self._generar_qr()

    def setup_ui(self):
        self.setWindowTitle(tr("Configurar Autenticación en Dos Pasos"))
        self.setFixedSize(480, 620)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()

        # Pagina 0: Mostrar QR
        self.stack.addWidget(self._crear_pagina_qr())

        # Pagina 1: Verificar codigo
        self.stack.addWidget(self._crear_pagina_verificar())

        layout.addWidget(self.stack)

    def _crear_pagina_qr(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 25, 30, 25)

        # Header
        icon = QLabel("🛡️")
        icon.setStyleSheet("font-size: 40px;")
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)

        title = QLabel(tr("Configurar Autenticación 2FA"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        instrucciones = QLabel(
            tr("Escanea este código QR con tu app de autenticación") + "\n" +
            tr("(Google Authenticator, Authy, etc.)")
        )
        instrucciones.setStyleSheet("color: #D8DEE9; font-size: 12px;")
        instrucciones.setAlignment(Qt.AlignCenter)
        instrucciones.setWordWrap(True)
        layout.addWidget(instrucciones)

        layout.addSpacing(10)

        # QR Code
        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setStyleSheet("""
            background-color: #ffffff;
            border-radius: 10px;
            padding: 10px;
        """)
        self.qr_label.setFixedSize(220, 220)

        qr_container = QHBoxLayout()
        qr_container.addStretch()
        qr_container.addWidget(self.qr_label)
        qr_container.addStretch()
        layout.addLayout(qr_container)

        layout.addSpacing(10)

        # Codigo manual
        manual_label = QLabel(tr("O introduce este código manualmente") + ":")
        manual_label.setStyleSheet("color: #7B88A0; font-size: 11px;")
        manual_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(manual_label)

        self.secret_label = QLabel("")
        self.secret_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            font-family: 'Consolas', 'Courier New', monospace;
            color: #88C0D0;
            letter-spacing: 3px;
            padding: 8px;
            background-color: #2E3440;
            border: 1px solid #4C566A;
            border-radius: 6px;
        """)
        self.secret_label.setAlignment(Qt.AlignCenter)
        self.secret_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.secret_label)

        layout.addSpacing(15)

        # Boton siguiente
        btns = QHBoxLayout()
        btns.addStretch()

        btn_cancelar = QPushButton(tr("Cancelar"))
        btn_cancelar.clicked.connect(self.reject)
        apply_btn_cancel(btn_cancelar)
        btns.addWidget(btn_cancelar)

        btn_siguiente = QPushButton(tr("Siguiente"))
        btn_siguiente.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        apply_btn_primary(btn_siguiente)
        btns.addWidget(btn_siguiente)

        btns.addStretch()
        layout.addLayout(btns)

        layout.addStretch()
        return page

    def _crear_pagina_verificar(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 25, 30, 25)

        # Header
        icon = QLabel("🔑")
        icon.setStyleSheet("font-size: 40px;")
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)

        title = QLabel(tr("Verificar Configuración"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        instrucciones = QLabel(
            tr("Introduce el código de 6 dígitos que aparece en tu app de autenticación para confirmar la configuración")
        )
        instrucciones.setStyleSheet("color: #D8DEE9; font-size: 12px;")
        instrucciones.setAlignment(Qt.AlignCenter)
        instrucciones.setWordWrap(True)
        layout.addWidget(instrucciones)

        layout.addSpacing(40)

        # Campo de codigo
        self.codigo_input = QLineEdit()
        self.codigo_input.setPlaceholderText("000000")
        self.codigo_input.setMaxLength(6)
        self.codigo_input.setAlignment(Qt.AlignCenter)
        self.codigo_input.setStyleSheet("""
            QLineEdit {
                font-size: 32px;
                font-weight: bold;
                font-family: 'Consolas', 'Courier New', monospace;
                letter-spacing: 10px;
                padding: 15px;
                border: 2px solid #5E81AC;
                border-radius: 8px;
                background-color: #2E3440;
                color: #ECEFF4;
                max-width: 250px;
            }
            QLineEdit:focus {
                border: 2px solid #88C0D0;
            }
        """)
        self.codigo_input.returnPressed.connect(self._activar_2fa)

        input_layout = QHBoxLayout()
        input_layout.addStretch()
        input_layout.addWidget(self.codigo_input)
        input_layout.addStretch()
        layout.addLayout(input_layout)

        layout.addSpacing(10)

        info = QLabel(tr("El código cambia cada 30 segundos"))
        info.setStyleSheet("color: #7B88A0; font-size: 11px;")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)

        layout.addSpacing(30)

        # Botones
        btns = QHBoxLayout()
        btns.addStretch()

        btn_volver = QPushButton(tr("Volver"))
        btn_volver.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        apply_btn_cancel(btn_volver)
        btns.addWidget(btn_volver)

        btn_activar = QPushButton(tr("Activar 2FA"))
        btn_activar.clicked.connect(self._activar_2fa)
        apply_btn_success(btn_activar)
        btns.addWidget(btn_activar)

        btns.addStretch()
        layout.addLayout(btns)

        layout.addStretch()
        return page

    def _generar_qr(self):
        """Genera el secreto TOTP y muestra el QR"""
        exito, secret, provisioning_uri = self.auth_manager.generar_totp_secret(self.usuario_id)

        if not exito:
            notify_error(self, tr("Error"), provisioning_uri)  # provisioning_uri contiene el mensaje de error
            self.reject()
            return

        self.secret = secret

        # Mostrar secreto formateado (grupos de 4)
        formatted = ' '.join([secret[i:i+4] for i in range(0, len(secret), 4)])
        self.secret_label.setText(formatted)

        # Generar QR
        qr = qrcode.QRCode(version=1, box_size=5, border=2)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # Convertir PIL Image a QPixmap
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        qimage = QImage()
        qimage.loadFromData(buffer.getvalue())
        pixmap = QPixmap.fromImage(qimage)
        self.qr_label.setPixmap(pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _activar_2fa(self):
        """Verifica el codigo y activa 2FA"""
        codigo = self.codigo_input.text().strip()

        if not codigo or len(codigo) != 6 or not codigo.isdigit():
            notify_warning(self, tr("Error"), tr("Introduce un código de 6 dígitos"))
            return

        exito, mensaje = self.auth_manager.activar_totp(self.usuario_id, codigo)

        if exito:
            notify_success(self, tr("2FA Activado"), mensaje)
            self.accept()
        else:
            notify_error(self, tr("Error"), mensaje)
            self.codigo_input.clear()
            self.codigo_input.setFocus()
