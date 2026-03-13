"""
Pestaña de gestión de establecimientos
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QAbstractItemView)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from app.utils.notify import notify_success, notify_error, notify_warning
from app.db.database import Database
from app.i18n import tr


class EstablecimientosTab(QWidget):
    def __init__(self, auth_manager, parent=None):
        super().__init__(parent)
        self.db = Database()
        self.db.connect()
        self.auth_manager = auth_manager
        self.setup_ui()
        self.cargar_establecimientos()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel(tr("Gestión de Establecimientos"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Botón añadir
        btn_nuevo = QPushButton(tr("+ Nuevo Establecimiento"))
        btn_nuevo.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #A3BE8C;
                border: 2px solid #A3BE8C;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: rgba(163, 190, 140, 0.1);
            }
        """)
        btn_nuevo.clicked.connect(self.nuevo_establecimiento)
        header_layout.addWidget(btn_nuevo)

        layout.addLayout(header_layout)

        # Tabla de establecimientos
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(7)
        self.tabla.setHorizontalHeaderLabels([
            "ID", tr("Logo"), tr("Nombre"), "NIF", tr("Teléfono"), tr("Usuarios"), tr("Acciones")
        ])

        # Configurar columnas
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Logo
        header.setSectionResizeMode(2, QHeaderView.Stretch)           # Nombre
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # NIF
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Teléfono
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Usuarios
        header.setSectionResizeMode(6, QHeaderView.Fixed)             # Acciones
        self.tabla.setColumnWidth(6, 180)

        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setAlternatingRowColors(True)
        
        # Altura de fila de máxima gama para total elegancia
        self.tabla.verticalHeader().setDefaultSectionSize(60)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setStyleSheet("QTableWidget::item { padding: 0px; }")

        layout.addWidget(self.tabla)

        # Info
        info = QLabel(
            tr("Solo se pueden eliminar establecimientos que no tienen usuarios asignados.") + " " +
            tr("Para editar o eliminar se requiere verificación de contraseña.")
        )
        info.setStyleSheet("color: #7B88A0; font-size: 11px;")
        info.setWordWrap(True)
        layout.addWidget(info)

    def cargar_establecimientos(self):
        """Carga la lista de establecimientos"""
        self.tabla.setRowCount(0)

        # Obtener establecimientos con conteo de usuarios
        query = """
            SELECT e.*,
                   (SELECT COUNT(*) FROM usuarios WHERE establecimiento_id = e.id) as num_usuarios
            FROM establecimientos e
            WHERE e.activo = 1
            ORDER BY e.nombre
        """
        establecimientos = self.db.fetch_all(query)

        for est in establecimientos:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            self.tabla.setRowHeight(row, 60)

            # ID
            id_item = QTableWidgetItem(str(est['id']))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 0, id_item)

            # Logo - Centrado verticalmente
            logo_container = QWidget()
            logo_layout = QVBoxLayout(logo_container)
            logo_layout.setContentsMargins(0, 0, 0, 0)
            logo_layout.setAlignment(Qt.AlignCenter)
            
            logo_label = QLabel()
            logo_label.setAlignment(Qt.AlignCenter)
            if est.get('logo_path'):
                import os
                if os.path.exists(est['logo_path']):
                    pixmap = QPixmap(est['logo_path'])
                    scaled = pixmap.scaled(45, 45, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    logo_label.setPixmap(scaled)
                else:
                    logo_label.setText("📷")
            else:
                logo_label.setText("—")
            logo_layout.addWidget(logo_label)
            self.tabla.setCellWidget(row, 1, logo_container)

            # Nombre
            nombre_item = QTableWidgetItem(est['nombre'])
            nombre_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 2, nombre_item)

            # NIF
            nif_item = QTableWidgetItem(est.get('nif') or '—')
            nif_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 3, nif_item)

            # Teléfono
            tel_item = QTableWidgetItem(est.get('telefono') or '—')
            tel_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 4, tel_item)

            # Usuarios vinculados
            num_usuarios = est.get('num_usuarios', 0)
            usuarios_item = QTableWidgetItem(str(num_usuarios))
            usuarios_item.setTextAlignment(Qt.AlignCenter)
            if num_usuarios > 0:
                usuarios_item.setForeground(Qt.white)
            self.tabla.setItem(row, 5, usuarios_item)

            # Acciones - Centrado "Bulletproof" (Layout anidado)
            container = QWidget()
            # Centrado Vertical con el mismo margen de 10px para subir un poco los botones
            v_layout = QVBoxLayout(container)
            v_layout.setContentsMargins(8, 0, 8, 10)
            v_layout.setAlignment(Qt.AlignCenter)

            h_layout = QHBoxLayout()
            h_layout.setContentsMargins(0, 0, 0, 0)
            h_layout.setSpacing(15)
            h_layout.setAlignment(Qt.AlignCenter)

            from app.ui.styles import estilizar_btn_editar, estilizar_btn_eliminar
            
            btn_editar = QPushButton()
            btn_editar.setToolTip(tr("Editar"))
            btn_editar.clicked.connect(lambda checked, e=est: self.editar_establecimiento(e))
            estilizar_btn_editar(btn_editar)

            btn_eliminar = QPushButton()
            btn_eliminar.setToolTip(tr("Eliminar"))
            if num_usuarios > 0:
                btn_eliminar.setEnabled(False)
                # Mantener tooltip explicativo
                btn_eliminar.setToolTip(f"{tr('No se puede eliminar')}: {num_usuarios} {tr('usuario(s) vinculado(s)')}")
            
            estilizar_btn_eliminar(btn_eliminar)
            if not num_usuarios > 0:
                btn_eliminar.clicked.connect(lambda checked, e=est: self.eliminar_establecimiento(e))
            
            h_layout.addWidget(btn_editar)
            h_layout.addWidget(btn_eliminar)

            v_layout.addLayout(h_layout)
            self.tabla.setCellWidget(row, 6, container)

    def nuevo_establecimiento(self):
        """Abre diálogo para crear nuevo establecimiento"""
        from app.ui.establecimiento_dialog import EstablecimientoDialog
        dialog = EstablecimientoDialog(self.db, parent=self)
        if dialog.exec_():
            self.cargar_establecimientos()

    def editar_establecimiento(self, establecimiento):
        """Edita un establecimiento (requiere contraseña)"""
        from app.ui.confirmar_accion_dialog import confirmar_accion_sensible

        if not confirmar_accion_sensible(
            self.auth_manager,
            'establecimientos.editar',
            tr('Editar Establecimiento'),
            f"{tr('Va a editar el establecimiento')}: {establecimiento['nombre']}\n\n"
            f"{tr('Confirme su contraseña para continuar.')}",
            self
        ):
            return

        from app.ui.establecimiento_dialog import EstablecimientoDialog
        dialog = EstablecimientoDialog(self.db, establecimiento=establecimiento, parent=self)
        if dialog.exec_():
            self.cargar_establecimientos()

    def eliminar_establecimiento(self, establecimiento):
        """Elimina un establecimiento (requiere contraseña)"""
        from app.ui.confirmar_accion_dialog import confirmar_accion_sensible

        # Verificar que no tenga usuarios
        count = self.db.fetch_one(
            "SELECT COUNT(*) as c FROM usuarios WHERE establecimiento_id = ?",
            (establecimiento['id'],)
        )
        if count and count['c'] > 0:
            notify_warning(
                self, tr("No se puede eliminar"),
                f"{tr('El establecimiento tiene')} {count['c']} {tr('usuario(s) vinculado(s)')}.\n"
                f"{tr('Reasigne los usuarios a otro establecimiento primero.')}"
            )
            return

        # Confirmar con contraseña
        if not confirmar_accion_sensible(
            self.auth_manager,
            'establecimientos.eliminar',
            tr('Eliminar Establecimiento'),
            f"{tr('¿Está seguro de eliminar el establecimiento')} '{establecimiento['nombre']}'?\n\n"
            f"{tr('Esta acción no se puede deshacer.')}",
            self
        ):
            return

        # Marcar como inactivo (soft delete)
        result = self.db.execute_query(
            "UPDATE establecimientos SET activo = 0 WHERE id = ?",
            (establecimiento['id'],)
        )

        if result is not None:
            notify_success(self, tr("Éxito"), tr("Establecimiento eliminado correctamente"))
            self.cargar_establecimientos()
        else:
            notify_error(self, tr("Error"), tr("No se pudo eliminar el establecimiento"))

    def closeEvent(self, event):
        """Cierra la conexión a la base de datos al cerrar el tab"""
        if hasattr(self, 'db') and self.db:
            self.db.disconnect()
        super().closeEvent(event)
