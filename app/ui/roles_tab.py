"""
Pestaña de gestión de roles y permisos
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QDialog, QLineEdit,
                             QTextEdit, QGroupBox, QCheckBox, QScrollArea,
                             QFrame, QGridLayout)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from app.utils.notify import notify_success, notify_warning
from app.modules.permission_manager import PermissionManager
from app.i18n import tr
from app.ui.transparent_buttons import apply_btn_success, apply_btn_cancel, apply_btn_primary, set_btn_icon
from qfluentwidgets import FluentIcon


class RolesTab(QWidget):
    """Pestaña para gestionar roles y permisos"""

    def __init__(self, db, auth_manager=None):
        super().__init__()
        self.db = db
        self.auth_manager = auth_manager
        self.permission_manager = PermissionManager(db)
        self.setup_ui()
        self.cargar_roles()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel(tr("Gestión de Roles y Permisos"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        btn_nuevo = QPushButton(tr("Nuevo Rol"))
        btn_nuevo.clicked.connect(self.nuevo_rol)
        apply_btn_success(btn_nuevo)
        set_btn_icon(btn_nuevo, FluentIcon.ADD, color="#A3BE8C")
        header_layout.addWidget(btn_nuevo)

        layout.addLayout(header_layout)

        # Descripción
        desc = QLabel(tr("Configure los permisos de cada rol. Los usuarios heredan los permisos de su rol asignado."))
        desc.setStyleSheet("color: #7B88A0; margin-bottom: 10px;")
        layout.addWidget(desc)

        # Tabla de roles
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(5)
        self.tabla.setHorizontalHeaderLabels([
            tr("Rol"), tr("Descripción"), tr("Usuarios"), tr("Sistema"), tr("Acciones")
        ])

        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.tabla.setColumnWidth(4, 120)

        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Altura de fila de máxima gama
        self.tabla.verticalHeader().setDefaultSectionSize(60)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setStyleSheet("QTableWidget::item { padding: 0px; }")

        layout.addWidget(self.tabla)

    def cargar_roles(self):
        """Carga los roles en la tabla"""
        roles = self.permission_manager.obtener_roles()

        self.tabla.setRowCount(0)

        for rol in roles:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            self.tabla.setRowHeight(row, 60)

            # Nombre del rol
            nombre_item = QTableWidgetItem(rol['nombre'].upper())
            nombre_item.setFont(QFont("", -1, QFont.Bold))
            if rol['nombre'] == 'admin':
                nombre_item.setForeground(QColor('#5E81AC'))
            nombre_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 0, nombre_item)

            # Descripción
            desc_item = QTableWidgetItem(rol['descripcion'] or '')
            desc_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 1, desc_item)

            # Número de usuarios
            num_usuarios = QTableWidgetItem(str(rol.get('num_usuarios', 0)))
            num_usuarios.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 2, num_usuarios)

            # Es sistema
            es_sistema = QTableWidgetItem(tr("Sí") if rol['es_sistema'] else tr("No"))
            es_sistema.setTextAlignment(Qt.AlignCenter)
            if rol['es_sistema']:
                es_sistema.setForeground(QColor('#88C0D0'))
            self.tabla.setItem(row, 3, es_sistema)

            # Botones de acción - Centrado estructural
            container = QWidget()
            v_layout = QVBoxLayout(container)
            v_layout.setContentsMargins(8, 0, 8, 10)
            v_layout.setAlignment(Qt.AlignCenter)

            h_layout = QHBoxLayout()
            h_layout.setContentsMargins(0, 0, 0, 0)
            h_layout.setSpacing(15)
            h_layout.setAlignment(Qt.AlignCenter)

            from app.ui.styles import estilizar_btn_permisos, estilizar_btn_eliminar
            
            # Botón editar permisos
            btn_permisos = QPushButton()
            btn_permisos.setToolTip(tr("Permisos"))
            btn_permisos.clicked.connect(lambda checked, r=rol: self.editar_permisos(r))
            estilizar_btn_permisos(btn_permisos)

            h_layout.addWidget(btn_permisos)

            # Botón eliminar (solo si no es sistema y no tiene usuarios)
            if not rol['es_sistema'] and rol.get('num_usuarios', 0) == 0:
                btn_eliminar = QPushButton()
                btn_eliminar.setToolTip(tr("Eliminar"))
                btn_eliminar.clicked.connect(lambda checked, r=rol: self.eliminar_rol(r))
                estilizar_btn_eliminar(btn_eliminar)
                h_layout.addWidget(btn_eliminar)

            v_layout.addLayout(h_layout)
            self.tabla.setCellWidget(row, 4, container)

    def nuevo_rol(self):
        """Crea un nuevo rol"""
        # Verificar permisos
        if self.auth_manager:
            from app.ui.confirmar_accion_dialog import confirmar_accion_sensible
            if not confirmar_accion_sensible(
                self.auth_manager,
                'configuracion.roles',
                tr('Crear Rol'),
                tr("¿Crear un nuevo rol?"),
                self
            ):
                return

        dialog = RolDialog(self.db, parent=self)
        if dialog.exec_():
            self.cargar_roles()

    def editar_permisos(self, rol):
        """Edita los permisos de un rol"""
        # Verificar permisos
        if self.auth_manager:
            from app.ui.confirmar_accion_dialog import confirmar_accion_sensible
            if not confirmar_accion_sensible(
                self.auth_manager,
                'configuracion.roles',
                tr('Editar Permisos'),
                f"{tr('¿Editar permisos del rol')} '{rol['nombre']}'?",
                self
            ):
                return

        dialog = PermisosDialog(self.db, rol, parent=self)
        if dialog.exec_():
            self.cargar_roles()

    def eliminar_rol(self, rol):
        """Elimina un rol"""
        # Verificar permisos y pedir contraseña
        if self.auth_manager:
            from app.ui.confirmar_accion_dialog import confirmar_accion_sensible
            if not confirmar_accion_sensible(
                self.auth_manager,
                'configuracion.roles',
                tr('Eliminar Rol'),
                f"{tr('¿Eliminar el rol')} '{rol['nombre']}'?\n\n"
                f"{tr('Esta acción no se puede deshacer.')}",
                self
            ):
                return

        exito, mensaje = self.permission_manager.eliminar_rol(rol['id'])
        if exito:
            notify_success(self, tr("Éxito"), mensaje)
            self.cargar_roles()
        else:
            notify_warning(self, tr("Error"), mensaje)


class RolDialog(QDialog):
    """Diálogo para crear un nuevo rol"""

    def __init__(self, db, rol=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.rol = rol
        self.permission_manager = PermissionManager(db)
        self.setup_ui()

        if rol:
            self.setWindowTitle(f"{tr('Editar Rol')}: {rol['nombre']}")
            self.nombre_input.setText(rol['nombre'])
            self.descripcion_input.setText(rol.get('descripcion', ''))
            if rol['es_sistema']:
                self.nombre_input.setEnabled(False)
        else:
            self.setWindowTitle(tr("Nuevo Rol"))

    def setup_ui(self):
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)

        # Nombre
        layout.addWidget(QLabel(tr("Nombre del Rol") + ":"))
        self.nombre_input = QLineEdit()
        self.nombre_input.setPlaceholderText(tr("Ej") + ": supervisor")
        layout.addWidget(self.nombre_input)

        # Descripción
        layout.addWidget(QLabel(tr("Descripción") + ":"))
        self.descripcion_input = QTextEdit()
        self.descripcion_input.setMaximumHeight(80)
        self.descripcion_input.setPlaceholderText(tr("Descripción del rol") + "...")
        layout.addWidget(self.descripcion_input)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancelar = QPushButton(tr("Cancelar"))
        btn_cancelar.clicked.connect(self.reject)
        apply_btn_cancel(btn_cancelar)
        btn_layout.addWidget(btn_cancelar)

        btn_guardar = QPushButton(tr("Guardar"))
        btn_guardar.clicked.connect(self.guardar)
        apply_btn_success(btn_guardar)
        btn_layout.addWidget(btn_guardar)

        layout.addLayout(btn_layout)

    def guardar(self):
        nombre = self.nombre_input.text().strip().lower()
        descripcion = self.descripcion_input.toPlainText().strip()

        if not nombre:
            notify_warning(self, tr("Error"), tr("El nombre es obligatorio"))
            return

        if self.rol:
            # Actualizar
            exito = self.permission_manager.actualizar_rol(
                self.rol['id'], nombre, descripcion,
                self.rol.get('permisos', [])
            )
            if exito:
                self.accept()
            else:
                notify_warning(self, tr("Error"), tr("No se pudo actualizar el rol"))
        else:
            # Crear nuevo
            rol_id = self.permission_manager.crear_rol(nombre, descripcion, [])
            if rol_id:
                self.accept()
            else:
                notify_warning(self, tr("Error"), tr("No se pudo crear el rol"))


class PermisosDialog(QDialog):
    """Diálogo para editar permisos de un rol"""

    def __init__(self, db, rol, parent=None):
        super().__init__(parent)
        self.db = db
        self.rol = rol
        self.permission_manager = PermissionManager(db)
        self.checkboxes = {}
        self.setup_ui()
        self.cargar_permisos()

    def setup_ui(self):
        self.setWindowTitle(f"{tr('Permisos')}: {self.rol['nombre'].upper()}")
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout(self)

        # Info del rol
        info = QLabel(f"<b>{tr('Rol')}:</b> {self.rol['nombre'].upper()} - {self.rol.get('descripcion', '')}")
        info.setStyleSheet("background-color: transparent; color: #88C0D0; border: 2px solid #88C0D0; border-radius: 6px; padding: 10px;")
        layout.addWidget(info)

        if self.rol['nombre'] == 'admin':
            warning = QLabel(tr("El rol Admin tiene todos los permisos automáticamente."))
            warning.setStyleSheet("color: #BF616A; font-weight: bold;")
            layout.addWidget(warning)

        # Área scrollable para permisos
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Obtener permisos agrupados
        permisos_por_modulo = self.permission_manager.obtener_todos_permisos()

        for modulo, permisos in permisos_por_modulo.items():
            group = QGroupBox(modulo)
            group.setStyleSheet("""
                QGroupBox {
                    font-weight: bold;
                    border: 1px solid #4C566A;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }
            """)
            group_layout = QGridLayout()

            for i, permiso in enumerate(permisos):
                checkbox = QCheckBox(permiso['nombre'])
                checkbox.setToolTip(permiso['codigo'])
                checkbox.setProperty('codigo', permiso['codigo'])

                if self.rol['nombre'] == 'admin':
                    checkbox.setChecked(True)
                    checkbox.setEnabled(False)

                self.checkboxes[permiso['codigo']] = checkbox
                group_layout.addWidget(checkbox, i // 2, i % 2)

            group.setLayout(group_layout)
            scroll_layout.addWidget(group)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Botones rápidos
        btn_rapidos = QHBoxLayout()

        btn_todos = QPushButton(tr("Marcar Todos"))
        btn_todos.clicked.connect(self.marcar_todos)
        apply_btn_primary(btn_todos)
        btn_rapidos.addWidget(btn_todos)

        btn_ninguno = QPushButton(tr("Desmarcar Todos"))
        btn_ninguno.clicked.connect(self.desmarcar_todos)
        apply_btn_cancel(btn_ninguno)
        btn_rapidos.addWidget(btn_ninguno)

        btn_rapidos.addStretch()
        layout.addLayout(btn_rapidos)

        # Botones principales
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancelar = QPushButton(tr("Cancelar"))
        btn_cancelar.clicked.connect(self.reject)
        apply_btn_cancel(btn_cancelar)
        btn_layout.addWidget(btn_cancelar)

        btn_guardar = QPushButton(tr("Guardar Permisos"))
        btn_guardar.clicked.connect(self.guardar)
        apply_btn_success(btn_guardar)
        btn_layout.addWidget(btn_guardar)

        layout.addLayout(btn_layout)

    def cargar_permisos(self):
        """Carga los permisos actuales del rol"""
        rol_completo = self.permission_manager.obtener_rol(self.rol['id'])
        if rol_completo and 'permisos' in rol_completo:
            for codigo in rol_completo['permisos']:
                if codigo in self.checkboxes:
                    self.checkboxes[codigo].setChecked(True)

    def marcar_todos(self):
        for cb in self.checkboxes.values():
            if cb.isEnabled():
                cb.setChecked(True)

    def desmarcar_todos(self):
        for cb in self.checkboxes.values():
            if cb.isEnabled():
                cb.setChecked(False)

    def guardar(self):
        if self.rol['nombre'] == 'admin':
            self.accept()
            return

        # Recoger permisos seleccionados
        permisos_seleccionados = []
        for codigo, checkbox in self.checkboxes.items():
            if checkbox.isChecked():
                permisos_seleccionados.append(codigo)

        # Actualizar
        exito = self.permission_manager.actualizar_rol(
            self.rol['id'],
            self.rol['nombre'],
            self.rol.get('descripcion', ''),
            permisos_seleccionados
        )

        if exito:
            notify_success(self, tr("Éxito"), tr("Permisos actualizados correctamente"))
            self.accept()
        else:
            notify_warning(self, tr("Error"), tr("No se pudieron actualizar los permisos"))
