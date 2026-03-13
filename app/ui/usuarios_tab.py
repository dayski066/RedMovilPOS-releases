"""
Pestaña de administración de usuarios (solo para administradores)
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QLabel, QHeaderView, QLineEdit)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from app.i18n import tr
from app.ui.usuario_dialog import UsuarioDialog
from app.ui.cambiar_password_dialog import CambiarPasswordDialog
from app.utils.notify import notify_success, notify_error, notify_warning
from app.ui.transparent_buttons import apply_btn_success, apply_btn_primary, set_btn_icon
from qfluentwidgets import FluentIcon
from datetime import datetime
from app.ui.totp_setup_dialog import TOTPSetupDialog


class UsuariosTab(QWidget):
    def __init__(self, auth_manager):
        super().__init__()
        self.auth_manager = auth_manager
        self.setup_ui()
        self.cargar_usuarios()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel(tr("Administración de Usuarios"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Botones
        btn_nuevo = QPushButton(tr("Nuevo Usuario"))
        btn_nuevo.clicked.connect(self.nuevo_usuario)
        apply_btn_success(btn_nuevo)
        set_btn_icon(btn_nuevo, FluentIcon.ADD, color="#A3BE8C")
        header_layout.addWidget(btn_nuevo)

        btn_mi_password = QPushButton(tr("Cambiar Mi Contraseña"))
        btn_mi_password.clicked.connect(self.cambiar_mi_password)
        apply_btn_primary(btn_mi_password)
        header_layout.addWidget(btn_mi_password)

        layout.addLayout(header_layout)

        # Info del usuario actual
        usuario_actual = self.auth_manager.obtener_usuario_actual()
        info_label = QLabel(
            f"👤 {tr('Sesión')}: {usuario_actual['nombre_completo']} ({usuario_actual['username']}) - "
            f"{tr('Rol')}: {usuario_actual['rol'].upper()}"
        )
        info_label.setStyleSheet("""
            background-color: rgba(46, 77, 60, 0.2);
            color: #A3BE8C;
            padding: 10px;
            border-radius: 5px;
            border-left: 4px solid #A3BE8C;
        """)
        layout.addWidget(info_label)

        # Tabla de usuarios
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(7)
        self.tabla.setHorizontalHeaderLabels([
            tr("Usuario"), tr("Nombre Completo"), tr("Rol"), tr("Estado"), tr("2FA"), tr("Último Acceso"), tr("Acciones")
        ])

        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        self.tabla.setColumnWidth(6, 280)

        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Altura de fila de máxima gama para total elegancia
        self.tabla.verticalHeader().setDefaultSectionSize(60)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setStyleSheet("QTableWidget::item { padding: 0px; }")

        layout.addWidget(self.tabla)

    def cargar_usuarios(self):
        """Carga todos los usuarios en la tabla"""
        usuarios = self.auth_manager.obtener_todos_usuarios()

        self.tabla.setRowCount(0)

        for usuario in usuarios:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            self.tabla.setRowHeight(row, 60)

            # Username
            username_item = QTableWidgetItem(usuario['username'])
            username_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 0, username_item)

            # Nombre completo
            nombre_item = QTableWidgetItem(usuario['nombre_completo'])
            nombre_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 1, nombre_item)

            # Rol
            rol_item = QTableWidgetItem(usuario['rol'].upper())
            if usuario['rol'] == 'admin':
                rol_item.setForeground(QColor("#5E81AC"))
            else:
                rol_item.setForeground(QColor("#D8DEE9"))
            rol_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 2, rol_item)

            # Estado
            estado_item = QTableWidgetItem(tr("ACTIVO") if usuario['activo'] else tr("INACTIVO"))
            if usuario['activo']:
                estado_item.setForeground(QColor("#A3BE8C"))
            else:
                estado_item.setForeground(QColor("#BF616A"))
            estado_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 3, estado_item)

            # 2FA
            tiene_2fa = usuario.get('totp_habilitado', 0)
            fa_item = QTableWidgetItem(tr("Activo") if tiene_2fa else "-")
            if tiene_2fa:
                fa_item.setForeground(QColor("#A3BE8C"))
            else:
                fa_item.setForeground(QColor("#4C566A"))
            fa_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 4, fa_item)

            # Último acceso
            ultimo_acceso = usuario['ultimo_acceso']
            if ultimo_acceso:
                # Convertir string de SQLite a datetime
                if isinstance(ultimo_acceso, str):
                    try:
                        dt = datetime.strptime(ultimo_acceso, '%Y-%m-%d %H:%M:%S')
                        acceso_str = dt.strftime('%d/%m/%Y %H:%M')
                    except (OSError, ValueError, RuntimeError):
                        acceso_str = ultimo_acceso
                else:
                    acceso_str = ultimo_acceso.strftime('%d/%m/%Y %H:%M')
            else:
                acceso_str = tr("Nunca")
            acceso_item = QTableWidgetItem(acceso_str)
            acceso_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 5, acceso_item)

            # Botones de acción - Centrado "Bulletproof" (Layout anidado)
            container = QWidget()
            # Centrado Vertical Estricto - Ajustado con margen inferior para subir los botones
            v_layout = QVBoxLayout(container)
            v_layout.setContentsMargins(8, 0, 8, 10)
            v_layout.setAlignment(Qt.AlignCenter)

            # Centrado Horizontal Estricto
            h_layout = QHBoxLayout()
            h_layout.setContentsMargins(0, 0, 0, 0)
            h_layout.setSpacing(15)
            h_layout.addStretch()

            from app.ui.styles import (estilizar_btn_editar, estilizar_btn_password,
                                       estilizar_btn_activar, estilizar_btn_desactivar,
                                       estilizar_btn_2fa, estilizar_btn_2fa_off)

            btn_editar = QPushButton()
            btn_editar.setToolTip(tr("Editar"))
            btn_editar.clicked.connect(lambda checked, u=usuario: self.editar_usuario(u))
            estilizar_btn_editar(btn_editar)

            btn_password = QPushButton()
            btn_password.setToolTip(tr("Cambiar contraseña"))
            btn_password.clicked.connect(lambda checked, u=usuario: self.cambiar_password_usuario(u))
            estilizar_btn_password(btn_password)

            # Botón 2FA
            btn_2fa = QPushButton()
            if tiene_2fa:
                btn_2fa.setToolTip(tr("Desactivar 2FA"))
                btn_2fa.clicked.connect(lambda checked, u=usuario: self.desactivar_2fa_usuario(u))
                estilizar_btn_2fa(btn_2fa)
            else:
                btn_2fa.setToolTip(tr("Configurar 2FA"))
                btn_2fa.clicked.connect(lambda checked, u=usuario: self.configurar_2fa(u))
                estilizar_btn_2fa_off(btn_2fa)

            # Botón activar/desactivar
            if usuario['activo']:
                btn_toggle = QPushButton()
                btn_toggle.setToolTip(tr("Desactivar"))
                btn_toggle.clicked.connect(lambda checked, u_id=usuario['id']: self.desactivar_usuario(u_id))
                estilizar_btn_desactivar(btn_toggle)
            else:
                btn_toggle = QPushButton()
                btn_toggle.setToolTip(tr("Activar"))
                btn_toggle.clicked.connect(lambda checked, u_id=usuario['id']: self.activar_usuario(u_id))
                estilizar_btn_activar(btn_toggle)

            h_layout.addWidget(btn_editar)
            h_layout.addWidget(btn_password)
            h_layout.addWidget(btn_2fa)
            h_layout.addWidget(btn_toggle)

            h_layout.addStretch()
            v_layout.addLayout(h_layout)
            self.tabla.setCellWidget(row, 6, container)

    def nuevo_usuario(self):
        """Crea un nuevo usuario"""
        # Verificar permisos
        from app.ui.confirmar_accion_dialog import confirmar_accion_sensible
        if not confirmar_accion_sensible(
            self.auth_manager,
            'configuracion.usuarios',
            tr('Crear Usuario'),
            tr("¿Crear un nuevo usuario?"),
            self
        ):
            return

        dialog = UsuarioDialog(self.auth_manager, parent=self)
        if dialog.exec_():
            self.cargar_usuarios()

    def editar_usuario(self, usuario):
        """Edita un usuario existente"""
        # Verificar permisos
        from app.ui.confirmar_accion_dialog import confirmar_accion_sensible
        if not confirmar_accion_sensible(
            self.auth_manager,
            'configuracion.usuarios',
            tr('Editar Usuario'),
            f"{tr('¿Editar el usuario')} {usuario['username']}?",
            self
        ):
            return

        dialog = UsuarioDialog(self.auth_manager, usuario=usuario, parent=self)
        if dialog.exec_():
            self.cargar_usuarios()

    def cambiar_password_usuario(self, usuario):
        """Cambia la contraseña de un usuario (solo admin)"""
        from PyQt5.QtWidgets import QInputDialog

        password, ok = QInputDialog.getText(
            self,
            tr("Cambiar Contraseña"),
            f"{tr('Nueva contraseña para')} {usuario['username']}:",
            QLineEdit.Password
        )

        if ok and password:
            # Validar contraseña usando el auth_manager
            valido, mensaje_validacion = self.auth_manager.validar_password(password)
            if not valido:
                notify_warning(self, tr("Contraseña Inválida"), mensaje_validacion)
                return

            datos = {'password': password}
            exito, mensaje = self.auth_manager.actualizar_usuario(usuario['id'], datos)

            if exito:
                notify_success(self, tr("Éxito"), mensaje)
            else:
                notify_error(self, tr("Error"), mensaje)

    def desactivar_usuario(self, usuario_id):
        """Desactiva un usuario"""
        # Obtener datos del usuario
        usuario = self.auth_manager.db.fetch_one(
            "SELECT username, nombre_completo FROM usuarios WHERE id = ?", (usuario_id,)
        )
        if not usuario:
            return

        # Verificar permisos
        from app.ui.confirmar_accion_dialog import confirmar_accion_sensible
        if not confirmar_accion_sensible(
            self.auth_manager,
            'configuracion.usuarios',
            tr('Desactivar Usuario'),
            f"{tr('¿Desactivar el usuario')} {usuario['username']}?\n\n"
            f"{tr('Nombre')}: {usuario['nombre_completo']}\n"
            f"{tr('El usuario no podrá iniciar sesión.')}",
            self
        ):
            return

        exito, mensaje = self.auth_manager.desactivar_usuario(usuario_id)

        if exito:
            notify_success(self, tr("Éxito"), mensaje)
            self.cargar_usuarios()
        else:
            notify_warning(self, tr("Error"), mensaje)

    def activar_usuario(self, usuario_id):
        """Activa un usuario"""
        exito, mensaje = self.auth_manager.activar_usuario(usuario_id)

        if exito:
            notify_success(self, tr("Éxito"), mensaje)
            self.cargar_usuarios()
        else:
            notify_warning(self, tr("Error"), mensaje)

    def configurar_2fa(self, usuario):
        """Abre el dialog para configurar 2FA de un usuario"""
        from app.ui.confirmar_accion_dialog import confirmar_accion_sensible
        if not confirmar_accion_sensible(
            self.auth_manager,
            'configuracion.usuarios',
            tr('Configurar 2FA'),
            f"{tr('¿Configurar autenticación en dos pasos para')} {usuario['username']}?",
            self
        ):
            return

        dialog = TOTPSetupDialog(
            self.auth_manager.db,
            self.auth_manager,
            usuario['id'],
            parent=self
        )
        if dialog.exec_():
            self.cargar_usuarios()

    def desactivar_2fa_usuario(self, usuario):
        """Desactiva 2FA de un usuario"""
        from app.ui.confirmar_accion_dialog import confirmar_accion_sensible
        if not confirmar_accion_sensible(
            self.auth_manager,
            'configuracion.usuarios',
            tr('Desactivar 2FA'),
            f"{tr('¿Desactivar autenticación en dos pasos para')} {usuario['username']}?\n\n"
            f"{tr('El usuario podrá acceder solo con contraseña.')}",
            self
        ):
            return

        exito, mensaje = self.auth_manager.desactivar_totp(usuario['id'])
        if exito:
            notify_success(self, tr("2FA Desactivado"), mensaje)
            self.cargar_usuarios()
        else:
            notify_error(self, tr("Error"), mensaje)

    def cambiar_mi_password(self):
        """Permite al usuario cambiar su propia contraseña"""
        dialog = CambiarPasswordDialog(self.auth_manager, parent=self)
        dialog.exec_()

    def closeEvent(self, event):
        """Cierra la conexión a la base de datos al cerrar el tab"""
        if hasattr(self, 'db') and self.db:
            self.db.disconnect()
        super().closeEvent(event)
