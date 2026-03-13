"""
Diálogo de confirmación de acciones sensibles
Verifica permisos y requiere contraseña del usuario actual
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from app.utils.notify import notify_warning
from app.ui.transparent_buttons import apply_btn_cancel, apply_btn_danger
from app.i18n import tr


class ConfirmarAccionDialog(QDialog):
    """
    Diálogo para confirmar acciones sensibles (eliminar, editar)
    Verifica que el usuario tenga permiso y pide contraseña
    """

    def __init__(self, auth_manager, permiso_requerido, titulo, mensaje, parent=None):
        """
        Args:
            auth_manager: Instancia de AuthManager con el usuario actual
            permiso_requerido: Código del permiso necesario (ej: 'ventas.eliminar')
            titulo: Título del diálogo
            mensaje: Mensaje descriptivo de la acción
            parent: Widget padre
        """
        super().__init__(parent)
        self.auth_manager = auth_manager
        self.permiso_requerido = permiso_requerido
        self.titulo = titulo
        self.mensaje = mensaje
        self.accion_confirmada = False

        # Verificar permiso antes de mostrar
        if not self._verificar_permiso():
            return

        self.setup_ui()

    def _verificar_permiso(self):
        """Verifica si el usuario tiene el permiso necesario"""
        usuario = self.auth_manager.obtener_usuario_actual()
        if not usuario:
            notify_warning(self.parent(), tr("Error"), tr("No hay usuario autenticado"))
            return False

        # Admin siempre tiene permiso
        if usuario['rol'] == 'admin':
            return True

        # Verificar permiso específico
        from app.modules.permission_manager import PermissionManager
        perm_manager = PermissionManager(self.auth_manager.db)
        perm_manager.cargar_permisos_usuario(usuario['id'])

        if not perm_manager.tiene_permiso(self.permiso_requerido):
            notify_warning(
                self.parent(),
                tr("Sin Permiso"),
                tr("No tienes permiso para realizar esta acción.\n\nPermiso requerido: {permiso}\nTu rol: {rol}\n\nContacta con un administrador.",
                   permiso=self.permiso_requerido, rol=usuario['rol'].upper())
            )
            return False

        return True

    def setup_ui(self):
        self.setWindowTitle(self.titulo)
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        # Icono y título
        header = QLabel(f"⚠️ {self.titulo}")
        header.setFont(QFont("", 14, QFont.Bold))
        header.setStyleSheet("color: #BF616A;")
        layout.addWidget(header)

        # Mensaje
        msg_label = QLabel(self.mensaje)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("""
            background-color: rgba(235, 203, 139, 0.15);
            border: 1px solid #EBCB8B;
            border-radius: 5px;
            padding: 15px;
            color: #EBCB8B;
        """)
        layout.addWidget(msg_label)

        # Separador
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: transparent; color: #88C0D0; border: 2px solid #88C0D0; border-radius: 6px;")
        layout.addWidget(line)

        # Info del usuario
        usuario = self.auth_manager.obtener_usuario_actual()
        user_info = QLabel(tr("Usuario: <b>{nombre}</b> ({username})", nombre=usuario['nombre_completo'], username=usuario['username']))
        user_info.setStyleSheet("color: #7B88A0;")
        layout.addWidget(user_info)

        # Campo de contraseña
        layout.addWidget(QLabel(tr("Introduce tu contraseña para confirmar:")))

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText(tr("Contraseña actual"))
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #4C566A;
                border-radius: 5px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #5E81AC;
            }
        """)
        self.password_input.returnPressed.connect(self.confirmar)
        layout.addWidget(self.password_input)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancelar = QPushButton(tr("Cancelar"))
        btn_cancelar.clicked.connect(self.reject)
        apply_btn_cancel(btn_cancelar)
        btn_layout.addWidget(btn_cancelar)

        btn_confirmar = QPushButton(tr("Confirmar"))
        btn_confirmar.clicked.connect(self.confirmar)
        apply_btn_danger(btn_confirmar)
        btn_layout.addWidget(btn_confirmar)

        layout.addLayout(btn_layout)

    def confirmar(self):
        """Verifica la contraseña y confirma la acción"""
        password = self.password_input.text()

        if not password:
            notify_warning(self, tr("Error"), tr("Introduce tu contraseña"))
            return

        usuario = self.auth_manager.obtener_usuario_actual()

        # Verificar contraseña
        if self.auth_manager.verificar_password(usuario['id'], password):
            self.accion_confirmada = True
            self.accept()
        else:
            notify_warning(self, tr("Error"), tr("Contraseña incorrecta"))
            self.password_input.clear()
            self.password_input.setFocus()

    def exec_(self):
        """Override para verificar permiso antes de mostrar"""
        if not self._verificar_permiso():
            return QDialog.Rejected
        return super().exec_()


def confirmar_accion_sensible(auth_manager, permiso, titulo, mensaje, parent=None):
    """
    Función helper para confirmar una acción sensible.

    Returns:
        bool: True si la acción fue confirmada, False en caso contrario

    Ejemplo:
        if confirmar_accion_sensible(
            auth_manager,
            'ventas.eliminar',
            'Eliminar Venta',
            f'¿Eliminar la factura {numero}?',
            self
        ):
            # Proceder con la eliminación
    """
    # Verificar si la protección está activada
    from app.db.database import Database
    db = Database()
    db.connect()
    result = db.fetch_one("SELECT valor FROM configuracion WHERE clave = 'seguridad_proteccion_operaciones'")
    db.disconnect()

    # Si la protección está desactivada (valor = '0'), permitir sin contraseña
    if result and result.get('valor') == '0':
        # Aún así verificar permisos, pero sin pedir contraseña
        usuario = auth_manager.obtener_usuario_actual()
        if not usuario:
            notify_warning(parent, tr("Error"), tr("No hay usuario autenticado"))
            return False

        # Admin siempre tiene permiso
        if usuario['rol'] == 'admin':
            return True

        # Verificar permiso específico
        from app.modules.permission_manager import PermissionManager
        perm_manager = PermissionManager(auth_manager.db)
        perm_manager.cargar_permisos_usuario(usuario['id'])

        if not perm_manager.tiene_permiso(permiso):
            notify_warning(
                parent,
                tr("Sin Permiso"),
                tr("No tienes permiso para realizar esta acción.\n\nPermiso requerido: {permiso}\nTu rol: {rol}\n\nContacta con un administrador.",
                   permiso=permiso, rol=usuario['rol'].upper())
            )
            return False

        return True  # Tiene permiso, no se pide contraseña

    # Protección activada: mostrar diálogo de confirmación con contraseña
    dialog = ConfirmarAccionDialog(auth_manager, permiso, titulo, mensaje, parent)
    result = dialog.exec_()
    return result == QDialog.Accepted and dialog.accion_confirmada
