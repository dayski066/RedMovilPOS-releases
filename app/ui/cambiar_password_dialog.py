"""
Diálogo para cambiar la contraseña del usuario actual
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QFormLayout)
from PyQt5.QtCore import Qt
from app.utils.notify import notify_success, notify_error, notify_warning
from app.ui.transparent_buttons import apply_btn_success, apply_btn_cancel
from app.i18n import tr


class CambiarPasswordDialog(QDialog):
    def __init__(self, auth_manager, parent=None):
        super().__init__(parent)
        self.auth_manager = auth_manager

        self.setWindowTitle(tr("Cambiar Mi Contraseña"))
        self.setModal(True)
        self.setMinimumWidth(450)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Info
        usuario = self.auth_manager.obtener_usuario_actual()
        info = QLabel(tr("Usuario: {nombre} ({username})", nombre=usuario['nombre_completo'], username=usuario['username']))
        info.setStyleSheet("background-color: transparent; color: #88C0D0; border: 2px solid #88C0D0; border-radius: 6px; font-weight: bold; padding: 10px;")
        layout.addWidget(info)

        layout.addSpacing(20)

        # Formulario
        form_layout = QFormLayout()

        self.password_actual_input = QLineEdit()
        self.password_actual_input.setEchoMode(QLineEdit.Password)
        self.password_actual_input.setPlaceholderText(tr("Tu contraseña actual"))
        form_layout.addRow(tr("Contraseña actual:"), self.password_actual_input)

        self.password_nueva_input = QLineEdit()
        self.password_nueva_input.setEchoMode(QLineEdit.Password)
        self.password_nueva_input.setPlaceholderText(tr("Mínimo 6 caracteres"))
        form_layout.addRow(tr("Nueva contraseña:"), self.password_nueva_input)

        self.password_confirm_input = QLineEdit()
        self.password_confirm_input.setEchoMode(QLineEdit.Password)
        self.password_confirm_input.setPlaceholderText(tr("Repetir nueva contraseña"))
        form_layout.addRow(tr("Confirmar nueva:"), self.password_confirm_input)

        layout.addLayout(form_layout)

        layout.addSpacing(10)

        # Ayuda
        help_label = QLabel(tr("La contraseña debe tener al menos 6 caracteres"))
        help_label.setStyleSheet("font-size: 11px; color: #7B88A0; padding: 5px;")
        layout.addWidget(help_label)

        layout.addSpacing(20)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancelar = QPushButton(tr("Cancelar"))
        btn_cancelar.clicked.connect(self.reject)
        apply_btn_cancel(btn_cancelar)

        btn_cambiar = QPushButton(tr("Cambiar Contraseña"))
        btn_cambiar.clicked.connect(self.cambiar_password)
        apply_btn_success(btn_cambiar)

        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_cambiar)

        layout.addLayout(btn_layout)

    def cambiar_password(self):
        """Cambia la contraseña del usuario"""
        password_actual = self.password_actual_input.text()
        password_nueva = self.password_nueva_input.text()
        password_confirm = self.password_confirm_input.text()

        if not password_actual or not password_nueva:
            notify_warning(self, tr("Error"), tr("Todos los campos son obligatorios"))
            return

        if password_nueva != password_confirm:
            notify_warning(self, tr("Error"), tr("Las contraseñas nuevas no coinciden"))
            return

        exito, mensaje = self.auth_manager.cambiar_password(password_actual, password_nueva)

        if exito:
            notify_success(self, tr("Éxito"), mensaje)
            self.accept()
        else:
            notify_error(self, tr("Error"), mensaje)
            self.password_actual_input.clear()
            self.password_actual_input.setFocus()
