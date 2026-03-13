"""
Pestaña para gestión de clientes
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QLabel,
                             QHeaderView, QFrame)
from qfluentwidgets import SearchLineEdit
from PyQt5.QtCore import Qt
from app.utils.notify import notify_success, notify_warning
from app.db.database import Database
from app.i18n import tr
from app.ui.transparent_buttons import apply_btn_success, set_btn_icon
from qfluentwidgets import FluentIcon
from app.ui.cliente_dialog import ClienteDialog
from app.ui.cliente_detalle_dialog import ClienteDetalleDialog
from app.ui.widgets.pagination_widget import PaginationWidget
from app.utils.debounce import Debouncer


class ClientesTab(QWidget):
    def __init__(self, auth_manager=None):
        super().__init__()
        self.auth_manager = auth_manager
        self.db = Database()
        self.db.connect()

        # Debouncer para búsqueda (300ms)
        self.search_debouncer = Debouncer(300)
        self._filtro_actual = None

        self.setup_ui()
        self.cargar_clientes()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        # Header Frame (Card UI)
        header_frame = QFrame()
        header_frame.setObjectName("cardPanel")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 15, 15, 15)
        
        title = QLabel(tr("Gestión de Clientes"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Búsqueda (con debounce para mejor rendimiento)
        self.search_input = SearchLineEdit()
        self.search_input.setPlaceholderText(tr("Buscar cliente..."))
        self.search_input.setMaximumWidth(300)
        self.search_input.textChanged.connect(
            lambda t: self.search_debouncer.debounce(self.filtrar_clientes)
        )
        header_layout.addWidget(self.search_input)

        # Botón nuevo cliente
        btn_nuevo = QPushButton(tr("Nuevo Cliente"))
        btn_nuevo.clicked.connect(self.nuevo_cliente)
        apply_btn_success(btn_nuevo)
        set_btn_icon(btn_nuevo, FluentIcon.ADD, color="#A3BE8C")
        header_layout.addWidget(btn_nuevo)

        layout.addWidget(header_frame)

        # Tabla de clientes
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(6)
        self.tabla.setHorizontalHeaderLabels([
            "ID", tr("Nombre"), tr("NIF/CIF"), tr("Dirección"), tr("Teléfono"), tr("Acciones")
        ])

        # Configurar columnas
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        self.tabla.setColumnWidth(5, 210)  # Acciones: Espacio aumentado
        
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Altura de fila de máxima gama
        self.tabla.verticalHeader().setDefaultSectionSize(60)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setStyleSheet("QTableWidget::item { padding: 0px; }")

        layout.addWidget(self.tabla)

        # Paginación
        self.pagination = PaginationWidget()
        self.pagination.page_changed.connect(self._on_page_changed)
        layout.addWidget(self.pagination)

    def _on_page_changed(self, offset, limit):
        """Callback cuando cambia la página"""
        self.cargar_clientes(self._filtro_actual)

    def cargar_clientes(self, filtro=None):
        """Carga clientes con paginación"""
        self._filtro_actual = filtro
        params = []
        where = ""
        if filtro:
            where = " WHERE nombre LIKE ? OR nif LIKE ?"
            params = [f"%{filtro}%", f"%{filtro}%"]

        # Count
        count_result = self.db.fetch_one(
            f"SELECT COUNT(*) as total FROM clientes{where}",
            params if params else None
        )
        total = count_result['total'] if count_result else 0
        self.pagination.update_total(total)

        # Data
        data_params = params + [self.pagination.limit, self.pagination.offset] if params else [self.pagination.limit, self.pagination.offset]
        clientes = self.db.fetch_all(
            f"SELECT * FROM clientes{where} ORDER BY nombre LIMIT ? OFFSET ?",
            data_params
        )

        self.tabla.setRowCount(0)

        for cliente in clientes:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            self.tabla.setRowHeight(row, 60)

            # ID
            id_item = QTableWidgetItem(str(cliente['id']))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 0, id_item)

            # Nombre
            nombre_item = QTableWidgetItem(cliente['nombre'])
            nombre_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 1, nombre_item)

            # NIF
            nif_item = QTableWidgetItem(cliente['nif'] or '—')
            nif_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 2, nif_item)

            # Dirección
            dir_item = QTableWidgetItem(cliente['direccion'] or '—')
            dir_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 3, dir_item)

            # Teléfono
            tel_item = QTableWidgetItem(cliente['telefono'] or '—')
            tel_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 4, tel_item)

            # Botones de acción - Centrado "Bulletproof"
            container = QWidget()
            # Centrado Vertical con margen de 10px para elevar
            v_layout = QVBoxLayout(container)
            v_layout.setContentsMargins(8, 0, 8, 10)
            v_layout.setAlignment(Qt.AlignCenter)

            h_layout = QHBoxLayout()
            h_layout.setContentsMargins(0, 0, 0, 0)
            h_layout.setSpacing(15)
            h_layout.addStretch()

            from app.ui.styles import estilizar_btn_ver, estilizar_btn_editar, estilizar_btn_eliminar
            
            btn_ver = QPushButton()
            btn_ver.setToolTip(tr("Ver"))
            btn_ver.clicked.connect(lambda checked, c=cliente: self.ver_cliente(c))
            estilizar_btn_ver(btn_ver)

            btn_editar = QPushButton()
            btn_editar.setToolTip(tr("Editar"))
            btn_editar.clicked.connect(lambda checked, c=cliente: self.editar_cliente(c))
            estilizar_btn_editar(btn_editar)

            btn_eliminar = QPushButton()
            btn_eliminar.setToolTip(tr("Eliminar"))
            btn_eliminar.clicked.connect(lambda checked, c_id=cliente['id']: self.eliminar_cliente(c_id))
            estilizar_btn_eliminar(btn_eliminar)

            h_layout.addWidget(btn_ver)
            h_layout.addWidget(btn_editar)
            h_layout.addWidget(btn_eliminar)

            h_layout.addStretch()
            v_layout.addLayout(h_layout)
            self.tabla.setCellWidget(row, 5, container)

    def filtrar_clientes(self):
        """Filtra clientes según el texto de búsqueda"""
        texto = self.search_input.text()
        self.pagination.reset()
        self.cargar_clientes(texto if texto else None)

    def nuevo_cliente(self):
        """Abre diálogo para crear nuevo cliente"""
        dialog = ClienteDialog(self.db, parent=self)
        if dialog.exec_():
            self.cargar_clientes()

    def ver_cliente(self, cliente):
        """Abre diálogo para ver detalles del cliente"""
        dialog = ClienteDetalleDialog(self.db, cliente=cliente, parent=self)
        dialog.exec_()
        # Recargar por si se editó desde el diálogo de detalles
        self.cargar_clientes()

    def editar_cliente(self, cliente):
        """Abre diálogo para editar cliente"""
        # Verificar permisos
        if self.auth_manager:
            from app.ui.confirmar_accion_dialog import confirmar_accion_sensible
            if not confirmar_accion_sensible(
                self.auth_manager,
                'clientes.editar',
                tr('Editar Cliente'),
                tr("¿Editar el cliente?") + f" {cliente['nombre']}",
                self
            ):
                return

        dialog = ClienteDialog(self.db, cliente=cliente, parent=self)
        if dialog.exec_():
            self.cargar_clientes()

    def eliminar_cliente(self, cliente_id):
        """Elimina un cliente (solo si no tiene vínculos)"""
        # Obtener datos del cliente
        cliente = self.db.fetch_one("SELECT * FROM clientes WHERE id = ?", (cliente_id,))
        if not cliente:
            return

        # Verificar permisos y pedir contraseña
        if self.auth_manager:
            from app.ui.confirmar_accion_dialog import confirmar_accion_sensible
            if not confirmar_accion_sensible(
                self.auth_manager,
                'clientes.eliminar',
                tr('Eliminar') + ' ' + tr('Cliente'),
                tr("¿Eliminar el cliente?") + f" {cliente['nombre']}\n\n"
                f"{tr('NIF/CIF')}: {cliente.get('nif', 'N/A')}",
                self
            ):
                return

        # Verificar si el cliente tiene facturas
        facturas = self.db.fetch_one(
            "SELECT COUNT(*) as total FROM facturas WHERE cliente_id = ?",
            (cliente_id,)
        )

        # Verificar si el cliente tiene reparaciones
        reparaciones = self.db.fetch_one(
            "SELECT COUNT(*) as total FROM reparaciones WHERE cliente_id = ?",
            (cliente_id,)
        )

        # Si tiene vínculos, no permitir eliminación
        if facturas and facturas['total'] > 0:
            notify_warning(
                self,
                tr("No se puede eliminar"),
                tr("Este cliente tiene facturas asociadas.") + f" ({facturas['total']})\n\n" +
                tr("No se puede eliminar porque los datos del cliente son necesarios para regenerar las facturas.")
            )
            return

        if reparaciones and reparaciones['total'] > 0:
            notify_warning(
                self,
                tr("No se puede eliminar"),
                tr("Este cliente tiene reparaciones asociadas.") + f" ({reparaciones['total']})\n\n" +
                tr("No se puede eliminar porque los datos del cliente son necesarios para regenerar las órdenes.")
            )
            return

        # Proceder con la eliminación
        self.db.execute_query("DELETE FROM clientes WHERE id = ?", (cliente_id,))
        self.cargar_clientes()
        notify_success(self, tr("Éxito"), tr("Cliente eliminado correctamente"))

    def closeEvent(self, event):
        """Cierra la conexión a la base de datos al cerrar el tab"""
        if hasattr(self, 'db') and self.db:
            self.db.disconnect()
        super().closeEvent(event)
