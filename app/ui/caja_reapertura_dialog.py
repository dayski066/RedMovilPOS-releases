"""
Diálogo para confirmar reapertura de caja (requiere contraseña)
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QFrame)
from PyQt5.QtCore import Qt
from app.utils.notify import notify_error, notify_warning
from app.ui.transparent_buttons import apply_btn_cancel, apply_btn_warning
from app.i18n import tr


class CajaReaperturaDialog(QDialog):
    def __init__(self, auth_manager, cierre, parent=None):
        """
        Args:
            auth_manager: AuthManager para verificar contraseña
            cierre: Objeto del cierre que se va a eliminar
            parent: Widget padre
        """
        super().__init__(parent)
        self.auth_manager = auth_manager
        self.cierre = cierre
        self.confirmado = False

        self.setWindowTitle(tr("Reapertura de Caja"))
        self.setModal(True)
        self.setMinimumWidth(550)

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 25, 30, 25)

        # Header con icono de advertencia
        icon = QLabel("⚠️")
        icon.setStyleSheet("font-size: 56px;")
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)

        # Título
        title = QLabel(tr("REAPERTURA DE CAJA"))
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #BF616A;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Warning message
        warning_frame = QFrame()
        warning_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(191, 97, 106, 0.15);
                border: 2px solid #BF616A;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        warning_layout = QVBoxLayout(warning_frame)

        warning_text = QLabel(
            tr("La caja ya fue cerrada para la fecha:") + f"\\n"
            f"📅 {self.cierre['fecha']}\\n\\n"
            + tr("Detalles del cierre:") + f"\\n"
            f"• {tr('Saldo Final')}: {self.cierre['saldo_final']:.2f} €\\n"
            f"• {tr('Efectivo Contado')}: {self.cierre['saldo_efectivo_contado']:.2f} €\\n"
            f"• {tr('Diferencia')}: {self.cierre['diferencia']:+.2f} €"
        )
        warning_text.setStyleSheet("color: #ffffff; font-size: 13px; border: none;")
        warning_text.setWordWrap(True)
        warning_layout.addWidget(warning_text)

        layout.addWidget(warning_frame)

        layout.addSpacing(10)

        # Información de la acción
        info_frame = QFrame()
        info_frame.setObjectName("cardPanel")
        info_layout = QVBoxLayout(info_frame)

        info_title = QLabel(tr("Esta acción realizará:"))
        info_title.setStyleSheet("font-weight: bold; color: #ffffff; font-size: 13px; border: none;")
        info_layout.addWidget(info_title)

        acciones = [
            "✓ " + tr("Eliminará el cierre de caja actual"),
            "✓ " + tr("Permitirá realizar nuevas ventas para hoy"),
            "✓ " + tr("Continuará con el saldo del cierre eliminado")
        ]

        for accion in acciones:
            accion_label = QLabel(accion)
            accion_label.setStyleSheet("color: #88C0D0; font-size: 12px; padding-left: 10px; border: none;")
            info_layout.addWidget(accion_label)

        layout.addWidget(info_frame)

        layout.addSpacing(15)

        password_card = QFrame()
        password_card.setObjectName("cardPanel")
        password_layout = QVBoxLayout(password_card)
        password_layout.setSpacing(10)
        password_layout.setContentsMargins(15, 15, 15, 15)

        # Sección de validación de contraseña
        password_label = QLabel(tr("VALIDACIÓN REQUERIDA"))
        password_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #EBCB8B;")
        password_layout.addWidget(password_label)

        # Usuario actual
        usuario = self.auth_manager.obtener_usuario_actual()
        if usuario:
            user_label = QLabel(tr("Usuario") + f": {usuario.get('username', tr('Desconocido'))}")
            user_label.setStyleSheet("color: #D8DEE9; font-size: 12px;")
            password_layout.addWidget(user_label)

        # Input de contraseña
        password_input_label = QLabel(tr("Introduce tu contraseña para confirmar:"))
        password_input_label.setStyleSheet("color: #D8DEE9; font-size: 12px;")
        password_layout.addWidget(password_input_label)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText(tr("Contraseña"))
        self.password_input.setMinimumHeight(40)
        self.password_input.setStyleSheet("""
            QLineEdit {
                background-color: #3B4252;
                color: #ffffff;
                border: 2px solid #4C566A;
                border-radius: 5px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #5E81AC;
            }
        """)
        password_layout.addWidget(self.password_input)

        layout.addWidget(password_card)

        layout.addSpacing(15)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancelar = QPushButton(tr("Cancelar"))
        btn_cancelar.clicked.connect(self.reject)
        apply_btn_cancel(btn_cancelar)
        btn_layout.addWidget(btn_cancelar)

        btn_confirmar = QPushButton("⚠️ " + tr("Confirmar Reapertura"))
        btn_confirmar.clicked.connect(self.confirmar)
        apply_btn_warning(btn_confirmar)
        btn_layout.addWidget(btn_confirmar)

        layout.addLayout(btn_layout)

        # Nord theme inherited from app stylesheet

        # Focus en input de contraseña
        self.password_input.setFocus()

    def confirmar(self):
        """Valida la contraseña y confirma la reapertura"""
        password = self.password_input.text()

        if not password:
            notify_warning(
                self,
                tr("Error"),
                tr("Debes introducir tu contraseña para confirmar esta acción.")
            )
            return

        # Obtener usuario actual
        usuario = self.auth_manager.obtener_usuario_actual()
        if not usuario:
            notify_error(
                self,
                tr("Error"),
                tr("No se pudo obtener el usuario actual.")
            )
            return

        # Verificar contraseña
        if not self.auth_manager.verificar_password(usuario['id'], password):
            notify_error(
                self,
                tr("Contraseña Incorrecta"),
                tr("La contraseña introducida no es correcta.") + "\\n\\n" +
                tr("La reapertura requiere confirmar tu identidad.")
            )
            self.password_input.clear()
            self.password_input.setFocus()
            return

        # Contraseña correcta
        self.confirmado = True
        self.accept()
