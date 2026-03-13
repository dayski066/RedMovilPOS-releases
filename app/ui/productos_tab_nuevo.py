"""
Pestaña mejorada para gestión de productos/servicios con categorías y códigos EAN
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QLabel,
                             QHeaderView, QComboBox, QGroupBox)
from qfluentwidgets import SearchLineEdit
from PyQt5.QtCore import Qt
from app.utils.notify import notify_success
from app.db.database import Database
from app.i18n import tr
from app.ui.transparent_buttons import apply_btn_success, set_btn_icon
from qfluentwidgets import FluentIcon
from app.modules.producto_manager import ProductoManager
from app.modules.categoria_manager import CategoriaManager
from app.ui.producto_dialog_nuevo import ProductoDialogNuevo
from app.ui.widgets.pagination_widget import PaginationWidget
from app.utils.debounce import Debouncer


class ProductosTabNuevo(QWidget):
    def __init__(self, auth_manager=None):
        super().__init__()
        self.auth_manager = auth_manager
        self.db = Database()
        self.db.connect()
        self.producto_manager = ProductoManager(self.db)
        self.categoria_manager = CategoriaManager(self.db)

        # Debouncer para búsqueda (300ms de delay)
        self.search_debouncer = Debouncer(300)
        self._filtro_actual = None
        self._categoria_actual = None

        self.setup_ui()
        self.cargar_categorias()
        self.cargar_productos()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel(tr("Catálogo de Productos / Servicios"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Botón nuevo producto
        btn_nuevo = QPushButton(tr("Nuevo Producto"))
        btn_nuevo.clicked.connect(self.nuevo_producto)
        apply_btn_success(btn_nuevo)
        set_btn_icon(btn_nuevo, FluentIcon.ADD, color="#A3BE8C")
        header_layout.addWidget(btn_nuevo)

        layout.addLayout(header_layout)

        # Filtros
        filtros_group = QGroupBox(tr("Búsqueda y Filtros"))
        filtros_group.setObjectName("cardGroup")
        filtros_layout = QHBoxLayout()

        # Búsqueda general (con debounce para mejor rendimiento)
        filtros_layout.addWidget(QLabel(tr("Buscar") + ":"))
        self.search_input = SearchLineEdit()
        self.search_input.setPlaceholderText(tr("Descripción") + ", EAN " + tr("o") + " IMEI...")
        self.search_input.textChanged.connect(self._on_search_changed)
        filtros_layout.addWidget(self.search_input)

        filtros_layout.addSpacing(20)

        # Filtro por categoría
        filtros_layout.addWidget(QLabel(tr("Categoría") + ":"))
        self.categoria_combo = QComboBox()
        self.categoria_combo.currentIndexChanged.connect(self.filtrar_productos)
        filtros_layout.addWidget(self.categoria_combo)

        filtros_layout.addStretch()

        filtros_group.setLayout(filtros_layout)
        layout.addWidget(filtros_group)

        # Tabla de productos
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(10)
        self.tabla.setHorizontalHeaderLabels([
            tr("Producto"), tr("Descripción"), "RAM", tr("Almacenamiento"), "IMEI", tr("Coste"), "PVP", tr("Categoría"), tr("Stock"), tr("Acciones")
        ])

        # Configurar columnas
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Producto (Marca+Modelo)
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Descripción
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # RAM
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Almacenamiento
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # IMEI
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Coste
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # PVP
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # Categoría
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)  # Stock
        header.setSectionResizeMode(9, QHeaderView.Fixed)  # Acciones
        self.tabla.setColumnWidth(9, 180)  # Acciones: Espacio aumentado
        
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
        self.cargar_productos(self._filtro_actual, self._categoria_actual)

    def showEvent(self, event):
        """Auto-refresh products when tab is shown"""
        super().showEvent(event)
        # Recargar productos para reflejar cambios de stock desde TPV
        self.cargar_productos()

    def cargar_categorias(self):
        """Carga las categorías en el combo"""
        self.categoria_combo.clear()
        self.categoria_combo.addItem(tr("Todas las categorías"), None)

        categorias = self.categoria_manager.obtener_todas()
        for categoria in categorias:
            self.categoria_combo.addItem(categoria['nombre'], categoria['id'])

    def cargar_productos(self, filtro=None, categoria_id=None):
        """Carga productos con paginación"""
        self._filtro_actual = filtro
        self._categoria_actual = categoria_id
        productos, total = self.producto_manager.buscar_productos_paginado(
            filtro, categoria_id, limit=self.pagination.limit, offset=self.pagination.offset
        )
        self.pagination.update_total(total)

        self.tabla.setRowCount(0)

        for producto in productos:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            self.tabla.setRowHeight(row, 60)

            # Producto (Marca + Modelo)
            marca = producto.get('marca_nombre') or ''
            modelo = producto.get('modelo_nombre') or ''
            producto_texto = f"{marca} {modelo}".strip() or '-'
            producto_item = QTableWidgetItem(producto_texto)
            self.tabla.setItem(row, 0, producto_item)

            # Descripción
            desc_item = QTableWidgetItem(producto['descripcion'] or '-')
            self.tabla.setItem(row, 1, desc_item)

            # RAM
            ram_item = QTableWidgetItem(producto.get('ram') or '-')
            ram_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 2, ram_item)

            # Almacenamiento
            almac_item = QTableWidgetItem(producto.get('almacenamiento') or '-')
            almac_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 3, almac_item)

            # IMEI
            imei_item = QTableWidgetItem(producto['imei'] or '-')
            imei_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 4, imei_item)

            # Coste (Precio de Compra)
            precio_compra = float(producto.get('precio_compra') or 0)
            coste_item = QTableWidgetItem(f"{precio_compra:.2f} €")
            coste_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 5, coste_item)

            # PVP (Precio de Venta)
            pvp_item = QTableWidgetItem(f"{float(producto['precio']):.2f} €")
            pvp_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 6, pvp_item)

            # Categoría
            cat_item = QTableWidgetItem(producto['categoria_nombre'] or tr('Sin categoría'))
            cat_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 7, cat_item)

            # Stock
            stock_item = QTableWidgetItem(str(producto['stock']))
            stock_item.setTextAlignment(Qt.AlignCenter)
            # Color según stock
            if producto['stock'] == 0:
                stock_item.setForeground(Qt.red)
            elif producto['stock'] < 5:
                stock_item.setForeground(Qt.darkYellow)
            self.tabla.setItem(row, 8, stock_item)

            # Botones de acción - Centrado estructural
            container = QWidget()
            v_layout = QVBoxLayout(container)
            v_layout.setContentsMargins(8, 0, 8, 10)
            v_layout.setAlignment(Qt.AlignCenter)

            h_layout = QHBoxLayout()
            h_layout.setContentsMargins(0, 0, 0, 0)
            h_layout.setSpacing(15)
            h_layout.addStretch()

            from app.ui.styles import estilizar_btn_editar, estilizar_btn_eliminar
            
            btn_editar = QPushButton()
            btn_editar.setToolTip(tr("Editar"))
            btn_editar.clicked.connect(lambda checked, p=producto: self.editar_producto(p))
            estilizar_btn_editar(btn_editar)

            btn_eliminar = QPushButton()
            btn_eliminar.setToolTip(tr("Eliminar"))
            btn_eliminar.clicked.connect(lambda checked, p_id=producto['id']: self.eliminar_producto(p_id))
            estilizar_btn_eliminar(btn_eliminar)

            h_layout.addWidget(btn_editar)
            h_layout.addWidget(btn_eliminar)

            h_layout.addStretch()
            v_layout.addLayout(h_layout)
            self.tabla.setCellWidget(row, 9, container)

    def _on_search_changed(self, texto):
        """Handler de búsqueda con debounce para mejor rendimiento"""
        self.search_debouncer.debounce(self.filtrar_productos)

    def filtrar_productos(self):
        """Filtra productos según búsqueda y categoría"""
        texto = self.search_input.text()
        categoria_id = self.categoria_combo.currentData()

        self.pagination.reset()
        self.cargar_productos(
            filtro=texto if texto else None,
            categoria_id=categoria_id
        )

    def nuevo_producto(self):
        """Abre diálogo para crear nuevo producto"""
        dialog = ProductoDialogNuevo(self.db, parent=self)
        if dialog.exec_():
            self.cargar_productos()
            self.cargar_categorias()

    def editar_producto(self, producto):
        """Abre diálogo para editar producto"""
        # Verificar permisos
        if self.auth_manager:
            from app.ui.confirmar_accion_dialog import confirmar_accion_sensible
            if not confirmar_accion_sensible(
                self.auth_manager,
                'inventario.editar',
                tr('Editar Producto'),
                tr("¿Editar el producto?") + f" {producto['descripcion']}",
                self
            ):
                return

        dialog = ProductoDialogNuevo(self.db, producto=producto, parent=self)
        if dialog.exec_():
            self.cargar_productos()

    def eliminar_producto(self, producto_id):
        """Elimina (desactiva) un producto"""
        # Obtener datos del producto
        producto = self.db.fetch_one("SELECT * FROM productos WHERE id = ?", (producto_id,))
        if not producto:
            return

        # Verificar permisos y pedir contraseña
        if self.auth_manager:
            from app.ui.confirmar_accion_dialog import confirmar_accion_sensible
            if not confirmar_accion_sensible(
                self.auth_manager,
                'inventario.eliminar',
                tr('Eliminar') + ' ' + tr('Producto'),
                tr("¿Eliminar el producto?") + f" {producto['descripcion']}\n\n"
                f"EAN: {producto.get('codigo_ean', 'N/A')}\n"
                f"{tr('Stock')}: {producto.get('stock', 0)}",
                self
            ):
                return

        self.producto_manager.desactivar_producto(producto_id)
        self.cargar_productos()
        notify_success(self, tr("Éxito"), tr("Producto eliminado correctamente"))

    def closeEvent(self, event):
        if hasattr(self, 'db') and self.db:
            self.db.disconnect()
        super().closeEvent(event)
