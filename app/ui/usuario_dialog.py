"""
Diálogo para crear/editar usuarios
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QFormLayout, QComboBox, QCheckBox)
from PyQt5.QtCore import Qt
from app.utils.notify import notify_success, notify_error, notify_warning
from app.i18n import tr
from app.ui.transparent_buttons import apply_btn_cancel, apply_btn_success


class UsuarioDialog(QDialog):
    def __init__(self, auth_manager, usuario=None, parent=None):
        super().__init__(parent)
        self.auth_manager = auth_manager
        self.usuario = usuario

        self.setWindowTitle(tr("Nuevo Usuario") if not usuario else tr("Editar Usuario"))
        self.setModal(True)
        self.setMinimumWidth(500)
        self.cargar_establecimientos()
        self.setup_ui()

        if usuario:
            self.cargar_datos()

    def cargar_establecimientos(self):
        """Carga los establecimientos disponibles"""
        self.establecimientos = self.auth_manager.obtener_establecimientos()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Formulario
        form_layout = QFormLayout()

        # Username (solo en creación)
        if not self.usuario:
            self.username_input = QLineEdit()
            self.username_input.setPlaceholderText(tr("Ejemplo") + ": jperez")
            form_layout.addRow(tr("Nombre de usuario") + ":", self.username_input)
        else:
            username_label = QLabel(self.usuario['username'])
            username_label.setStyleSheet("font-weight: bold; color: #7B88A0;")
            form_layout.addRow(tr("Nombre de usuario") + ":", username_label)

        # Nombre completo
        self.nombre_input = QLineEdit()
        self.nombre_input.setPlaceholderText(tr("Ejemplo") + ": Juan Pérez")
        form_layout.addRow(tr("Nombre completo") + ":", self.nombre_input)

        # Contraseña (solo en creación o si se quiere cambiar)
        if not self.usuario:
            self.password_input = QLineEdit()
            self.password_input.setEchoMode(QLineEdit.Password)
            self.password_input.setPlaceholderText(tr("Mínimo 6 caracteres"))
            form_layout.addRow(tr("Contraseña") + ":", self.password_input)

            self.password_confirm_input = QLineEdit()
            self.password_confirm_input.setEchoMode(QLineEdit.Password)
            self.password_confirm_input.setPlaceholderText(tr("Repetir contraseña"))
            form_layout.addRow(tr("Confirmar contraseña") + ":", self.password_confirm_input)
        else:
            cambiar_pass_label = QLabel("(" + tr("Usa 'Cambiar Pass' en la tabla") + ")")
            cambiar_pass_label.setStyleSheet("font-size: 11px; color: #7B88A0;")
            form_layout.addRow(tr("Contraseña") + ":", cambiar_pass_label)

        # Establecimiento (obligatorio para nuevos usuarios)
        self.establecimiento_combo = QComboBox()
        self.establecimiento_combo.addItem("-- " + tr("Seleccionar Establecimiento") + " --", None)
        for est in self.establecimientos:
            self.establecimiento_combo.addItem(est['nombre'], est['id'])
        form_layout.addRow(tr("Establecimiento") + " *:", self.establecimiento_combo)

        # Rol
        self.rol_combo = QComboBox()
        self.rol_combo.addItem(tr("Usuario Normal"), "usuario")
        self.rol_combo.addItem(tr("Administrador"), "admin")
        form_layout.addRow(tr("Rol") + ":", self.rol_combo)

        # Activo (solo en edición)
        if self.usuario:
            self.activo_check = QCheckBox(tr("Usuario activo"))
            self.activo_check.setChecked(self.usuario['activo'])
            form_layout.addRow(tr("Estado") + ":", self.activo_check)

        layout.addLayout(form_layout)

        # Info
        if not self.usuario:
            info_label = QLabel(
                "💡 " + tr("El usuario será activo por defecto.") + "\n" +
                tr("Los administradores pueden gestionar todos los usuarios.")
            )
            info_label.setStyleSheet("""
                background-color: rgba(163, 190, 140, 0.15);
                padding: 10px;
                border-radius: 5px;
                font-size: 11px;
                color: #A3BE8C;
            """)
            layout.addWidget(info_label)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancelar = QPushButton(tr("Cancelar"))
        btn_cancelar.clicked.connect(self.reject)
        apply_btn_cancel(btn_cancelar)

        btn_guardar = QPushButton(tr("Guardar"))
        btn_guardar.clicked.connect(self.guardar)
        apply_btn_success(btn_guardar)

        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_guardar)

        layout.addLayout(btn_layout)

    def cargar_datos(self):
        """Carga los datos del usuario en el formulario"""
        self.nombre_input.setText(self.usuario['nombre_completo'])

        # Seleccionar establecimiento
        est_id = self.usuario.get('establecimiento_id')
        if est_id:
            index = self.establecimiento_combo.findData(est_id)
            if index >= 0:
                self.establecimiento_combo.setCurrentIndex(index)

        # Seleccionar rol
        index = self.rol_combo.findData(self.usuario['rol'])
        if index >= 0:
            self.rol_combo.setCurrentIndex(index)

    def guardar(self):
        """Guarda el usuario"""
        nombre_completo = self.nombre_input.text().strip()

        if not nombre_completo:
            notify_warning(self, tr("Error"), tr("El nombre completo es obligatorio"))
            return

        # Validar establecimiento
        establecimiento_id = self.establecimiento_combo.currentData()
        if not establecimiento_id:
            notify_warning(self, tr("Error"), tr("Debe seleccionar un establecimiento"))
            return

        if self.usuario:
            # Editar usuario existente
            datos = {
                'nombre_completo': nombre_completo,
                'rol': self.rol_combo.currentData(),
                'activo': self.activo_check.isChecked(),
                'establecimiento_id': establecimiento_id
            }

            exito, mensaje = self.auth_manager.actualizar_usuario(self.usuario['id'], datos)

            if exito:
                notify_success(self, tr("Éxito"), tr(mensaje))
                self.accept()
            else:
                notify_error(self, tr("Error"), tr(mensaje))

        else:
            # Crear nuevo usuario
            username = self.username_input.text().strip()
            password = self.password_input.text()
            password_confirm = self.password_confirm_input.text()

            if not username:
                notify_warning(self, tr("Error"), tr("El nombre de usuario es obligatorio"))
                return

            if not password:
                notify_warning(self, tr("Error"), tr("La contraseña es obligatoria"))
                return

            if password != password_confirm:
                notify_warning(self, tr("Error"), tr("Las contraseñas no coinciden"))
                return

            rol = self.rol_combo.currentData()

            exito, mensaje = self.auth_manager.crear_usuario(
                username, password, nombre_completo, rol, establecimiento_id
            )

            if exito:
                notify_success(self, tr("Éxito"), tr(mensaje))
                self.accept()
            else:
                notify_error(self, tr("Error"), tr(mensaje))
