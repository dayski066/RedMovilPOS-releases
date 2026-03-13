"""
Diálogo para agregar productos favoritos al TPV
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QFormLayout, QDoubleSpinBox,
                             QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
                             QAbstractItemView, QGroupBox)
from qfluentwidgets import SearchLineEdit
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from app.i18n import tr
from app.utils.notify import notify_success, notify_error, notify_warning
from app.modules.producto_manager import ProductoManager
from app.ui.transparent_buttons import apply_btn_success, apply_btn_cancel


class TPVAgregarFavoritoDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.producto_manager = ProductoManager(db)
        self.setWindowTitle(tr("Agregar Producto Favorito"))
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self.setup_ui()
        self.cargar_productos()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Opción: Producto del inventario o manual
        opcion_frame = QGroupBox(tr("Tipo de Favorito"))
        opcion_layout = QVBoxLayout(opcion_frame)
        
        self.tipo_combo = QComboBox()
        self.tipo_combo.addItems([tr("Desde Inventario"), tr("Producto Manual")])
        self.tipo_combo.currentTextChanged.connect(self.on_tipo_changed)
        opcion_layout.addWidget(self.tipo_combo)
        
        layout.addWidget(opcion_frame)

        # Panel de búsqueda (solo para inventario)
        self.busqueda_frame = QGroupBox(tr("Buscar Producto"))
        busqueda_layout = QVBoxLayout(self.busqueda_frame)
        
        busqueda_input_layout = QHBoxLayout()
        self.busqueda_input = SearchLineEdit()
        self.busqueda_input.setPlaceholderText(tr("Buscar por nombre, EAN o IMEI..."))
        self.busqueda_input.textChanged.connect(self.buscar_productos)
        busqueda_input_layout.addWidget(self.busqueda_input)
        
        busqueda_layout.addLayout(busqueda_input_layout)
        
        # Tabla de productos
        self.productos_table = QTableWidget()
        self.productos_table.setColumnCount(4)
        self.productos_table.setHorizontalHeaderLabels([tr("ID"), tr("Descripción"), tr("Precio"), tr("Stock")])
        self.productos_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.productos_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.productos_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.productos_table.setAlternatingRowColors(True)
        
        # Estilo Global de Tabla
        self.productos_table.verticalHeader().setDefaultSectionSize(60)
        self.productos_table.verticalHeader().setVisible(False)
        self.productos_table.setStyleSheet("QTableWidget::item { padding: 0px; }")
        
        header = self.productos_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        busqueda_layout.addWidget(self.productos_table)
        
        layout.addWidget(self.busqueda_frame)

        # Panel de producto manual
        self.manual_frame = QGroupBox(tr("Datos del Producto"))
        manual_layout = QFormLayout(self.manual_frame)
        
        self.nombre_input = QLineEdit()
        self.nombre_input.setPlaceholderText(tr("Nombre del producto"))
        manual_layout.addRow(tr("Nombre:"), self.nombre_input)
        
        self.precio_input = QDoubleSpinBox()
        self.precio_input.setMinimum(0)
        self.precio_input.setMaximum(999999.99)
        self.precio_input.setDecimals(2)
        self.precio_input.setSuffix(" €")
        manual_layout.addRow(tr("Precio:"), self.precio_input)
        
        layout.addWidget(self.manual_frame)
        self.manual_frame.setVisible(False)

        # Color del botón favorito
        color_frame = QGroupBox(tr("Color del Botón"))
        color_layout = QFormLayout(color_frame)
        
        self.color_combo = QComboBox()
        colores = [
            (tr("Azul"), "#5E81AC"),
            (tr("Verde"), "#A3BE8C"),
            (tr("Naranja"), "#D08770"),
            (tr("Rojo"), "#BF616A"),
            (tr("Morado"), "#B48EAD"),
            (tr("Turquesa"), "#8FBCBB"),
            (tr("Amarillo"), "#EBCB8B"),
            (tr("Gris"), "#D8DEE9")
        ]
        for nombre, codigo in colores:
            self.color_combo.addItem(nombre, codigo)
        
        color_layout.addRow(tr("Color:"), self.color_combo)
        
        layout.addWidget(color_frame)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancelar = QPushButton(tr("Cancelar"))
        btn_cancelar.clicked.connect(self.reject)
        apply_btn_cancel(btn_cancelar)

        btn_guardar = QPushButton(tr("Agregar Favorito"))
        btn_guardar.clicked.connect(self.aceptar)
        apply_btn_success(btn_guardar)

        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_guardar)

        layout.addLayout(btn_layout)

    def on_tipo_changed(self, texto):
        """Cambia la interfaz según el tipo seleccionado"""
        es_manual = texto == tr("Producto Manual")
        self.busqueda_frame.setVisible(not es_manual)
        self.manual_frame.setVisible(es_manual)

    def cargar_productos(self):
        """Carga todos los productos activos"""
        productos = self.db.fetch_all("""
            SELECT id, descripcion, precio, stock
            FROM productos
            WHERE activo = 1
            ORDER BY descripcion
            LIMIT 100
        """)
        
        self.llenar_tabla(productos)

    def buscar_productos(self, texto):
        """Busca productos según el texto"""
        if not texto.strip():
            self.cargar_productos()
            return
        
        productos = self.db.fetch_all("""
            SELECT id, descripcion, precio, stock
            FROM productos
            WHERE activo = 1
            AND (descripcion LIKE ? OR codigo_ean LIKE ? OR imei LIKE ?)
            ORDER BY descripcion
            LIMIT 50
        """, (f'%{texto}%', f'%{texto}%', f'%{texto}%'))
        
        self.llenar_tabla(productos)

    def llenar_tabla(self, productos):
        """Llena la tabla con productos"""
        self.productos_table.setRowCount(0)
        
        for producto in productos:
            row = self.productos_table.rowCount()
            self.productos_table.insertRow(row)
            self.productos_table.setRowHeight(row, 60)
            
            # Formatear items con centrado
            raw_vals = [
                str(producto['id']),
                producto['descripcion'],
                f"{producto['precio']:.2f} €",
                str(producto['stock'])
            ]
            
            for col, val in enumerate(raw_vals):
                t_item = QTableWidgetItem(val)
                t_item.setTextAlignment(Qt.AlignCenter)
                self.productos_table.setItem(row, col, t_item)

    def aceptar(self):
        """Valida y acepta el diálogo"""
        es_manual = self.tipo_combo.currentText() == tr("Producto Manual")
        color = self.color_combo.currentData()
        # Si currentData() devuelve None, usar el valor por defecto
        if color is None:
            color = "#5E81AC"
        
        if es_manual:
            nombre = self.nombre_input.text().strip()
            precio = self.precio_input.value()
            
            if not nombre:
                notify_warning(self, tr("Campo requerido"), tr("Por favor, introduce un nombre"))
                self.nombre_input.setFocus()
                return
            
            if precio <= 0:
                notify_warning(self, tr("Precio inválido"), tr("El precio debe ser mayor que 0"))
                self.precio_input.setFocus()
                return
            
            # Agregar favorito manual
            try:
                from app.modules.caja_tpv_manager import CajaTpvManager
                tpv_manager = CajaTpvManager(self.db)
                if tpv_manager.agregar_favorito(
                    producto_id=None,
                    nombre=nombre,
                    precio=precio,
                    color=color
                ):
                    notify_success(self, tr("Éxito"), tr("Producto favorito agregado correctamente"))
                    self.accept()
                else:
                    notify_warning(self, tr("Error"), tr("No se pudo agregar el favorito"))
            except (OSError, ValueError, RuntimeError) as e:
                notify_error(self, tr("Error"), tr("Error al agregar favorito") + f":\n{str(e)}")
                import traceback
                traceback.print_exc()
        else:
            # Desde inventario
            selected_rows = self.productos_table.selectionModel().selectedRows()
            if not selected_rows:
                notify_warning(self, tr("Selección requerida"), tr("Por favor, selecciona un producto de la lista"))
                return
            
            row = selected_rows[0].row()
            producto_id_item = self.productos_table.item(row, 0)
            if not producto_id_item:
                notify_warning(self, tr("Error"), tr("No se pudo obtener el ID del producto seleccionado"))
                return
            
            try:
                producto_id = int(producto_id_item.text())
            except (ValueError, AttributeError):
                notify_warning(self, tr("Error"), tr("ID de producto inválido"))
                return
            
            # Agregar favorito desde inventario
            try:
                from app.modules.caja_tpv_manager import CajaTpvManager
                tpv_manager = CajaTpvManager(self.db)
                if tpv_manager.agregar_favorito(
                    producto_id=producto_id,
                    nombre=None,
                    precio=None,
                    color=color
                ):
                    notify_success(self, "Éxito", "Producto favorito agregado correctamente")
                    self.accept()
                else:
                    notify_warning(self, "Error", "No se pudo agregar el favorito")
            except (OSError, ValueError, RuntimeError) as e:
                notify_error(self, "Error", f"Error al agregar favorito:\n{str(e)}")
                import traceback
                traceback.print_exc()






