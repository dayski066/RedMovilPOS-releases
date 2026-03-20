"""
Pestaña mejorada para crear facturas con detección automática de clientes y productos
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QTableWidget, QTableWidgetItem, QGroupBox,
                             QDateEdit, QComboBox, QHeaderView, QDoubleSpinBox,
                             QSpinBox, QCompleter, QApplication, QScrollArea, QFrame,
                             QListWidget, QListWidgetItem)
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QColor, QFont
from app.utils.notify import notify_success, notify_error, notify_warning, notify_info, ask_confirm
from app.db.database import Database
from app.modules.factura_manager import FacturaManager
from app.modules.pdf_generator import PDFGenerator
from app.modules.producto_manager import ProductoManager
from app.ui.articulo_dialog import ArticuloDialog
from app.ui.styles import estilizar_btn_eliminar, THEMES
from app.ui.transparent_buttons import apply_btn_success, apply_btn_cancel, apply_btn_primary, set_btn_icon
from config import IVA_RATE, calcular_desglose_iva
from app.i18n import tr
from qfluentwidgets import SearchLineEdit, FluentIcon
import datetime
import os
import platform


class FacturaTabMejorada(QWidget):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.db.connect()
        self.factura_manager = FacturaManager(self.db)
        self.pdf_generator = PDFGenerator(self.db)
        self.producto_manager = ProductoManager(self.db)
        self.setup_ui()
        self.load_clientes()
        self.cargar_nuevo_numero_factura()

    def _obtener_usuario_id(self):
        """Obtiene el ID del usuario actual para auditoría"""
        try:
            main_window = self.window()
            if hasattr(main_window, 'auth_manager') and main_window.auth_manager:
                usuario = main_window.auth_manager.obtener_usuario_actual()
                if usuario:
                    return usuario.get('id')
        except (OSError, ValueError, RuntimeError):
            pass
        return None

    def setup_ui(self):
        # Layout principal con scroll
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Crear scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Widget contenedor para el contenido
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(4)

        # Header con número y fecha
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        numero_label = QLabel(tr("Nº Factura") + ":")
        numero_label.setStyleSheet("font-weight: bold;")
        self.numero_input = QLineEdit()
        self.numero_input.setReadOnly(True)
        self.numero_input.setMaximumWidth(150)
        self.numero_input.setStyleSheet("color: #ffffff; font-weight: bold;")

        fecha_label = QLabel(tr("Fecha") + ":")
        fecha_label.setStyleSheet("font-weight: bold;")
        self.fecha_input = QDateEdit()
        self.fecha_input.setDate(QDate.currentDate())
        self.fecha_input.setCalendarPopup(True)
        self.fecha_input.setMaximumWidth(150)

        header_layout.addWidget(numero_label)
        header_layout.addWidget(self.numero_input)
        header_layout.addSpacing(20)
        header_layout.addWidget(fecha_label)
        header_layout.addWidget(self.fecha_input)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Datos del cliente con detección automática
        cliente_title = QLabel(tr("DATOS DEL CLIENTE") + " - " + tr("Detección Automática"))
        cliente_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #ffffff; padding: 2px 0; background: transparent;")
        layout.addWidget(cliente_title)

        cliente_group = QGroupBox()
        cliente_layout = QVBoxLayout()
        cliente_layout.setContentsMargins(8, 6, 8, 6)
        cliente_layout.setSpacing(10)

        # Búsqueda rápida por nombre, DNI o Teléfono
        busqueda_layout = QHBoxLayout()
        busqueda_layout.setAlignment(Qt.AlignVCenter)
        busqueda_layout.addWidget(QLabel(tr("Buscar cliente") + ":"))
        self.busqueda_cliente_input = SearchLineEdit()
        self.busqueda_cliente_input.setFixedHeight(36)
        self.busqueda_cliente_input.setPlaceholderText(tr("Nombre, DNI o Teléfono..."))
        self.busqueda_cliente_input.textChanged.connect(self._filtrar_clientes_live)
        self.busqueda_cliente_input.returnPressed.connect(self.buscar_cliente_auto)
        busqueda_layout.addWidget(self.busqueda_cliente_input)

        btn_buscar_cliente = QPushButton(tr("Buscar"))
        btn_buscar_cliente.clicked.connect(self.buscar_cliente_auto)
        apply_btn_primary(btn_buscar_cliente)
        set_btn_icon(btn_buscar_cliente, FluentIcon.SEARCH, color="#5E81AC")
        btn_buscar_cliente.setFixedHeight(36)
        btn_buscar_cliente.setMaximumWidth(100)
        busqueda_layout.addWidget(btn_buscar_cliente)

        cliente_layout.addLayout(busqueda_layout)

        # Lista de sugerencias en tiempo real
        self.lista_sugerencias = QListWidget()
        self.lista_sugerencias.setMaximumHeight(100)
        self.lista_sugerencias.setVisible(False)
        self.lista_sugerencias.setStyleSheet("""
            QListWidget {
                background-color: #2E3440;
                border: 1px solid #5E81AC;
                border-radius: 6px;
                color: #ECEFF4;
                font-size: 13px;
            }
            QListWidget::item { padding: 6px 10px; border-bottom: 1px solid #3B4252; }
            QListWidget::item:hover { background-color: #3B4252; }
            QListWidget::item:selected { background-color: #5E81AC; color: #ffffff; }
        """)
        self.lista_sugerencias.itemClicked.connect(self._seleccionar_cliente_lista)
        cliente_layout.addWidget(self.lista_sugerencias)

        # Selector de cliente existente
        selector_layout = QHBoxLayout()
        selector_layout.setAlignment(Qt.AlignVCenter)
        selector_layout.addWidget(QLabel(tr("O seleccionar") + ":"))
        self.cliente_combo = QComboBox()
        self.cliente_combo.setEditable(True)
        self.cliente_combo.setFixedHeight(36)
        self.cliente_combo.currentIndexChanged.connect(self.on_cliente_selected)
        selector_layout.addWidget(self.cliente_combo)

        btn_nuevo_cliente = QPushButton(tr("Nuevo Cliente"))
        btn_nuevo_cliente.clicked.connect(self.abrir_nuevo_cliente)
        btn_nuevo_cliente.setFixedHeight(36)
        btn_nuevo_cliente.setMaximumWidth(150)
        apply_btn_success(btn_nuevo_cliente)
        set_btn_icon(btn_nuevo_cliente, FluentIcon.ADD, color="#A3BE8C")
        selector_layout.addWidget(btn_nuevo_cliente)

        cliente_layout.addLayout(selector_layout)

        # Campos del cliente - Layout responsivo y compacto
        campos_layout = QHBoxLayout()
        campos_layout.setSpacing(10)

        # Estilo compacto
        current_theme = QApplication.instance().property("theme") or "dark"
        t = THEMES[current_theme]
        label_style = f"font-size: 11px; color: {t['text_secondary']}; margin: 0; padding: 0;"

        # Estilo para campos de solo lectura con texto visible usando el color principal del tema
        readonly_style = f"""
            QLineEdit {{
                color: {t['text_main']};
                font-weight: bold;
            }}
        """

        left_col = QVBoxLayout()
        left_col.setSpacing(2)
        lbl = QLabel(tr("Nombre") + ":")
        lbl.setStyleSheet(label_style)
        left_col.addWidget(lbl)
        self.nombre_input = QLineEdit()
        self.nombre_input.setReadOnly(True)
        self.nombre_input.setMinimumWidth(150)
        self.nombre_input.setStyleSheet(readonly_style)
        left_col.addWidget(self.nombre_input)
        lbl2 = QLabel(tr("NIF/CIF") + ":")
        lbl2.setStyleSheet(label_style)
        left_col.addWidget(lbl2)
        self.nif_input = QLineEdit()
        self.nif_input.setReadOnly(True)
        self.nif_input.setMinimumWidth(150)
        self.nif_input.setStyleSheet(readonly_style)
        left_col.addWidget(self.nif_input)
        lbl_cp = QLabel(tr("C.P.") + ":")
        lbl_cp.setStyleSheet(label_style)
        left_col.addWidget(lbl_cp)
        self.cp_input = QLineEdit()
        self.cp_input.setReadOnly(True)
        self.cp_input.setMinimumWidth(150)
        self.cp_input.setStyleSheet(readonly_style)
        left_col.addWidget(self.cp_input)

        right_col = QVBoxLayout()
        right_col.setSpacing(2)
        lbl3 = QLabel(tr("Dirección") + ":")
        lbl3.setStyleSheet(label_style)
        right_col.addWidget(lbl3)
        self.direccion_input = QLineEdit()
        self.direccion_input.setReadOnly(True)
        self.direccion_input.setMinimumWidth(150)
        self.direccion_input.setStyleSheet(readonly_style)
        right_col.addWidget(self.direccion_input)
        lbl_ciudad = QLabel(tr("Ciudad") + ":")
        lbl_ciudad.setStyleSheet(label_style)
        right_col.addWidget(lbl_ciudad)
        self.ciudad_input = QLineEdit()
        self.ciudad_input.setReadOnly(True)
        self.ciudad_input.setMinimumWidth(150)
        self.ciudad_input.setStyleSheet(readonly_style)
        right_col.addWidget(self.ciudad_input)
        lbl_provincia = QLabel(tr("Provincia:"))
        lbl_provincia.setStyleSheet(label_style)
        right_col.addWidget(lbl_provincia)
        self.provincia_input = QLineEdit()
        self.provincia_input.setReadOnly(True)
        self.provincia_input.setMinimumWidth(150)
        self.provincia_input.setStyleSheet(readonly_style)
        right_col.addWidget(self.provincia_input)
        lbl4 = QLabel(tr("Teléfono") + ":")
        lbl4.setStyleSheet(label_style)
        right_col.addWidget(lbl4)
        self.telefono_input = QLineEdit()
        self.telefono_input.setReadOnly(True)
        self.telefono_input.setMinimumWidth(150)
        self.telefono_input.setStyleSheet(readonly_style)
        right_col.addWidget(self.telefono_input)

        campos_layout.addLayout(left_col, 1)
        campos_layout.addLayout(right_col, 1)
        cliente_layout.addLayout(campos_layout)

        cliente_group.setLayout(cliente_layout)
        layout.addWidget(cliente_group)

        # Búsqueda rápida de productos
        producto_title = QLabel(tr("AÑADIR PRODUCTOS") + " - " + tr("Escanear EAN o IMEI"))
        producto_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #ffffff; padding: 2px 0; background: transparent;")
        layout.addWidget(producto_title)

        producto_busqueda_group = QGroupBox()
        producto_busqueda_layout = QHBoxLayout()
        producto_busqueda_layout.setContentsMargins(8, 6, 8, 6)

        producto_busqueda_layout.setAlignment(Qt.AlignVCenter)
        producto_busqueda_layout.addWidget(QLabel(tr("Código EAN / IMEI") + ":"))
        self.producto_busqueda_input = SearchLineEdit()
        self.producto_busqueda_input.setFixedHeight(36)
        self.producto_busqueda_input.setPlaceholderText(tr("Escanear código de barras o introducir IMEI..."))
        self.producto_busqueda_input.returnPressed.connect(self.buscar_producto_auto)
        producto_busqueda_layout.addWidget(self.producto_busqueda_input)

        btn_buscar_producto = QPushButton(tr("Buscar"))
        btn_buscar_producto.clicked.connect(self.buscar_producto_auto)
        apply_btn_primary(btn_buscar_producto)
        set_btn_icon(btn_buscar_producto, FluentIcon.SEARCH, color="#5E81AC")
        btn_buscar_producto.setFixedHeight(36)
        btn_buscar_producto.setMaximumWidth(100)
        producto_busqueda_layout.addWidget(btn_buscar_producto)

        producto_busqueda_group.setLayout(producto_busqueda_layout)
        layout.addWidget(producto_busqueda_group)

        # Tabla de artículos
        articulos_label = QLabel(tr("Artículos / Servicios"))
        articulos_label.setStyleSheet("font-weight: bold; font-size: 12px; padding: 2px 0;")
        layout.addWidget(articulos_label)

        self.tabla_articulos = QTableWidget(0, 6)
        self.tabla_articulos.setHorizontalHeaderLabels([
            tr("Descripción"), "IMEI/SN", tr("Cantidad"), tr("Precio"), "PVP", tr("Acciones")
        ])

        header = self.tabla_articulos.horizontalHeader()
        # Descripción variable, resto fijo
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Descripción - variable
        header.setSectionResizeMode(1, QHeaderView.Fixed)    # IMEI - fijo
        header.setSectionResizeMode(2, QHeaderView.Fixed)    # Cantidad - fijo
        header.setSectionResizeMode(3, QHeaderView.Fixed)    # Precio - fijo
        header.setSectionResizeMode(4, QHeaderView.Fixed)    # PVP - fijo
        header.setSectionResizeMode(5, QHeaderView.Fixed)    # Acciones - fijo
        # Anchos fijos para columnas
        self.tabla_articulos.setColumnWidth(1, 180)  # IMEI
        self.tabla_articulos.setColumnWidth(2, 90)   # Cantidad
        self.tabla_articulos.setColumnWidth(3, 100)  # Precio
        self.tabla_articulos.setColumnWidth(4, 100)  # PVP
        self.tabla_articulos.setColumnWidth(5, 80)   # Acciones
        
        self.tabla_articulos.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_articulos.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Estilo Global de Tabla
        self.tabla_articulos.verticalHeader().setDefaultSectionSize(60)
        self.tabla_articulos.verticalHeader().setVisible(False)
        self.tabla_articulos.setStyleSheet("QTableWidget::item { padding: 0px; }")

        # Tamaño mínimo para que el scroll se active antes de ocultar la tabla
        self.tabla_articulos.setMinimumHeight(150)

        layout.addWidget(self.tabla_articulos) 

        # Botones de artículos
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("+ " + tr("Añadir Dispositivo"))
        btn_add.clicked.connect(self.agregar_fila_articulo)
        apply_btn_success(btn_add)
        btn_add.setFixedSize(180, 40)
        btn_layout.addWidget(btn_add)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Totales (compacto en línea)
        totales_layout = QHBoxLayout()
        totales_layout.addStretch()

        self.subtotal_label = QLabel(tr("Subtotal") + ": 0.00 €")
        self.subtotal_label.setStyleSheet("font-size: 11px; color: #7B88A0; padding: 0 10px;")
        totales_layout.addWidget(self.subtotal_label)

        self.iva_label = QLabel(f"{tr('IVA')} ({int(IVA_RATE*100)}%): 0.00 €")
        self.iva_label.setStyleSheet("font-size: 11px; color: #7B88A0; padding: 0 10px;")
        totales_layout.addWidget(self.iva_label)

        self.total_label = QLabel(tr("Total").upper() + ": 0.00 €")
        self.total_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #A3BE8C; padding: 0 10px;")
        totales_layout.addWidget(self.total_label)

        layout.addLayout(totales_layout)

        # Botones de acción (compactos)
        acciones_layout = QHBoxLayout()
        acciones_layout.addStretch()

        btn_limpiar = QPushButton(tr("Limpiar"))
        btn_limpiar.clicked.connect(self.limpiar_formulario)
        apply_btn_cancel(btn_limpiar)

        btn_guardar = QPushButton(tr("Finalizar Venta"))
        btn_guardar.clicked.connect(self.guardar_factura)
        apply_btn_success(btn_guardar)

        acciones_layout.addWidget(btn_limpiar)
        acciones_layout.addWidget(btn_guardar)
        layout.addLayout(acciones_layout)

        # Conectar scroll area con el contenido
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

    def _filtrar_clientes_live(self, texto):
        """Filtra clientes en tiempo real por nombre, DNI o teléfono"""
        texto = texto.strip()
        self.lista_sugerencias.clear()
        if len(texto) < 2:
            self.lista_sugerencias.setVisible(False)
            return
        like = f'%{texto}%'
        clientes = self.db.fetch_all(
            "SELECT * FROM clientes WHERE nombre LIKE ? OR nif LIKE ? OR telefono LIKE ? LIMIT 8",
            (like, like, like)
        )
        if not clientes:
            self.lista_sugerencias.setVisible(False)
            return
        for c in clientes:
            item = QListWidgetItem(f"{c.get('nombre','')}   |   {c.get('nif','-') or '-'}   |   {c.get('telefono','-') or '-'}")
            item.setData(Qt.UserRole, dict(c))
            self.lista_sugerencias.addItem(item)
        self.lista_sugerencias.setVisible(True)

    def _seleccionar_cliente_lista(self, item):
        cliente = item.data(Qt.UserRole)
        self._rellenar_campos_cliente(cliente)
        self.lista_sugerencias.setVisible(False)
        self.busqueda_cliente_input.clear()

    def _rellenar_campos_cliente(self, cliente):
        self.nombre_input.setText(cliente.get('nombre') or '')
        self.nif_input.setText(cliente.get('nif') or '')
        self.direccion_input.setText(cliente.get('direccion') or '')
        self.telefono_input.setText(cliente.get('telefono') or '')
        self.cp_input.setText(cliente.get('codigo_postal') or '')
        self.ciudad_input.setText(cliente.get('ciudad') or '')
        self.provincia_input.setText(cliente.get('provincia') or '')
        index = self.cliente_combo.findData(cliente['id'])
        if index >= 0:
            self.cliente_combo.setCurrentIndex(index)

    def buscar_cliente_auto(self):
        """Busca cliente al pulsar Enter o Buscar"""
        if self.lista_sugerencias.isVisible() and self.lista_sugerencias.count() > 0:
            self._seleccionar_cliente_lista(self.lista_sugerencias.item(0))
            return
        busqueda = self.busqueda_cliente_input.text().strip()
        if not busqueda:
            return
        like = f'%{busqueda}%'
        cliente = self.db.fetch_one(
            "SELECT * FROM clientes WHERE nif LIKE ? OR telefono LIKE ? OR nombre LIKE ? LIMIT 1",
            (like, like, like)
        )
        if cliente:
            self._rellenar_campos_cliente(dict(cliente))
            notify_success(self, "✓ " + tr("Cliente Encontrado"), tr("Cliente") + f": {cliente['nombre']}")
        else:
            if ask_confirm(
                self,
                tr("Cliente No Encontrado"),
                tr("No se encontró ningún cliente con") + f": {busqueda}\n\n" + tr("¿Desea crear un nuevo cliente?")
            ):
                if busqueda.isdigit() and len(busqueda) >= 9:
                    self.telefono_input.setText(busqueda)
                else:
                    self.nif_input.setText(busqueda)
                self.nombre_input.setFocus()

    def buscar_producto_auto(self):
        """Busca producto automáticamente por EAN o IMEI y lo añade a la factura"""
        try:
            busqueda = self.producto_busqueda_input.text().strip()

            if not busqueda:
                return

            # Buscar por código EAN en productos
            producto = self.producto_manager.buscar_por_ean(busqueda)

            # Si no se encuentra, buscar por IMEI en productos
            if not producto:
                producto = self.producto_manager.buscar_por_imei(busqueda)

            # Si no se encuentra en productos, buscar en compras_items


            if producto:
                # Producto encontrado - añadir a la tabla
                añadido = self.agregar_producto_encontrado(producto)

                self.producto_busqueda_input.clear()
                self.producto_busqueda_input.setFocus()

                # Solo mostrar mensaje si realmente se añadió
                if añadido:
                    marca = producto.get('marca_nombre') or ''
                    modelo = producto.get('modelo_nombre') or ''
                    nombre_producto = f"{marca} {modelo}".strip() or producto.get('descripcion') or 'Producto'

                    notify_success(
                        self,
                        "✓ " + tr("Producto Añadido"),
                        f"{nombre_producto}\n" + tr("Precio") + f": {float(producto.get('precio') or 0):.2f} €"
                    )

            else:
                # No encontrado con stock > 0, verificar si existe pero sin stock
                producto_sin_stock = None
                
                # Buscar por EAN sin filtro de stock
                producto_sin_stock = self.db.fetch_one(
                    """SELECT p.*, c.nombre as categoria_nombre FROM productos p
                       LEFT JOIN categorias c ON p.categoria_id = c.id
                       WHERE p.codigo_ean = ? AND p.activo = 1""",
                    (busqueda,)
                )
                
                # Si no se encuentra por EAN, buscar por IMEI sin filtro de stock
                if not producto_sin_stock:
                    producto_sin_stock = self.db.fetch_one(
                        """SELECT p.*, c.nombre as categoria_nombre FROM productos p
                           LEFT JOIN categorias c ON p.categoria_id = c.id
                           WHERE p.imei = ? AND p.activo = 1""",
                        (busqueda,)
                    )
                
                if producto_sin_stock and producto_sin_stock.get('stock', 0) == 0:
                    # El producto existe pero está sin stock (vendido)
                    notify_warning(
                        self,
                        tr("Terminal Vendido"),
                        f"{tr('Este producto ya fue vendido o no tiene stock')}\n\n"
                        f"{tr('Producto')}: {producto_sin_stock.get('descripcion') or busqueda}\n"
                        f"{tr('Stock')}: 0"
                    )
                else:
                    # No existe en la base de datos
                    notify_warning(
                        self,
                        tr("Producto No Encontrado"),
                        tr("No se encontró ningún producto con EAN/IMEI") + f": {busqueda}\n\n" + tr("Puedes añadirlo manualmente")
                    )
        except (OSError, ValueError, RuntimeError) as e:
            import traceback
            error_msg = traceback.format_exc()
            notify_error(self, "Error", f"Error al buscar producto:\n\n{error_msg}")

    def agregar_producto_encontrado(self, producto):
        """Añade un producto encontrado automáticamente a la tabla. Devuelve True si se añadió."""
        # Verificar si el IMEI ya está en la tabla (no permitir duplicados)
        imei_nuevo = producto.get('imei') or ''
        if imei_nuevo:
            for row in range(self.tabla_articulos.rowCount()):
                imei_container = self.tabla_articulos.cellWidget(row, 1)
                if imei_container:
                    imei_widget = imei_container.findChild(QLineEdit)
                    if imei_widget and imei_widget.text() == imei_nuevo:
                        notify_warning(
                            self,
                            tr("Producto Duplicado"),
                            tr("Este terminal ya está en la lista") + f":\nIMEI: {imei_nuevo}"
                        )
                        return False

        row = self.tabla_articulos.rowCount()
        self.tabla_articulos.insertRow(row)
        self.tabla_articulos.setRowHeight(row, 60)

        # Descripción - usar marca + modelo si están disponibles
        marca = producto.get('marca_nombre') or ''
        modelo = producto.get('modelo_nombre') or ''
        descripcion = f"{marca} {modelo}".strip() or producto.get('descripcion') or ''

        desc_input = QLineEdit()
        desc_input.setText(descripcion)
        desc_input.setFixedHeight(32)
        # Guardar producto_id y categoria para usar al guardar la factura
        desc_input.setProperty("producto_id", producto.get('id'))
        desc_input.setProperty("categoria", producto.get('categoria_nombre') or '')

        container_desc = QWidget()
        v_layout_desc = QVBoxLayout(container_desc)
        v_layout_desc.setContentsMargins(5, 0, 5, 10)
        v_layout_desc.setAlignment(Qt.AlignCenter)
        v_layout_desc.addWidget(desc_input)
        self.tabla_articulos.setCellWidget(row, 0, container_desc)

        # IMEI/SN
        imei_input = QLineEdit()
        imei_input.setText(producto.get('imei') or '')
        imei_input.setPlaceholderText("IMEI/Nº Serie")
        imei_input.setFixedSize(170, 32)

        container_imei = QWidget()
        v_layout_imei = QVBoxLayout(container_imei)
        v_layout_imei.setContentsMargins(5, 0, 5, 10)
        v_layout_imei.setAlignment(Qt.AlignCenter)
        v_layout_imei.addWidget(imei_input)
        self.tabla_articulos.setCellWidget(row, 1, container_imei)

        # Cantidad - con límite basado en stock disponible
        stock_disponible = int(producto.get('stock') or 1)
        categoria = producto.get('categoria_nombre') or ''
        es_movil = categoria.lower() in ['móviles', 'moviles']
        
        cantidad_spin = QSpinBox()
        cantidad_spin.setMinimum(1)
        if es_movil:
            cantidad_spin.setMaximum(1)  # Móviles siempre cantidad 1
        else:
            cantidad_spin.setMaximum(stock_disponible)  # Máximo = stock
        cantidad_spin.setValue(1)
        cantidad_spin.setFixedSize(60, 32)
        # Capturar row por valor usando default argument
        cantidad_spin.valueChanged.connect(lambda _, r=row: self.actualizar_pvp(r))
        # Guardar stock máximo para referencia
        cantidad_spin.setProperty("stock_max", stock_disponible)

        container_cantidad = QWidget()
        v_layout_cantidad = QVBoxLayout(container_cantidad)
        v_layout_cantidad.setContentsMargins(5, 0, 5, 10)
        v_layout_cantidad.setAlignment(Qt.AlignCenter)
        v_layout_cantidad.addWidget(cantidad_spin)
        self.tabla_articulos.setCellWidget(row, 2, container_cantidad)

        # Precio (sin IVA) - El valor de la BD es PVP (con IVA), calculamos el precio base
        pvp_valor = float(producto.get('precio') or 0)  # Este es el PVP (con IVA 21%)
        precio_sin_iva = pvp_valor / 1.21  # Calculamos el precio base (sin IVA)
        
        precio_spin = QDoubleSpinBox()
        precio_spin.setMinimum(0)
        precio_spin.setMaximum(999999)
        precio_spin.setDecimals(2)
        precio_spin.setValue(precio_sin_iva)
        # Capturar row por valor usando default argument
        precio_spin.valueChanged.connect(lambda _, r=row: self.actualizar_pvp(r))
        precio_spin.setFixedSize(90, 32)
        
        # Recuperar tema para estilos
        current_theme = QApplication.instance().property("theme") or "dark"
        t = THEMES[current_theme]
        
        # Sin stylesheet personalizado - usa el estilo global igual que IMEI

        container_precio = QWidget()
        v_layout_precio = QVBoxLayout(container_precio)
        v_layout_precio.setContentsMargins(5, 0, 5, 10)
        v_layout_precio.setAlignment(Qt.AlignCenter)
        v_layout_precio.addWidget(precio_spin)
        self.tabla_articulos.setCellWidget(row, 3, container_precio)


        # PVP (con IVA) - QLineEdit de solo lectura (misma altura que IMEI y Precio)
        pvp_input = QLineEdit(f"{pvp_valor:.2f} €")
        pvp_input.setReadOnly(True)
        pvp_input.setAlignment(Qt.AlignCenter)
        pvp_input.setFixedSize(90, 32)
        pvp_input.setStyleSheet(f"color: white; background-color: {t['bg_input']};")


        container_pvp = QWidget()
        v_layout_pvp = QVBoxLayout(container_pvp)
        v_layout_pvp.setContentsMargins(5, 0, 5, 10)
        v_layout_pvp.setAlignment(Qt.AlignCenter)
        v_layout_pvp.addWidget(pvp_input)
        self.tabla_articulos.setCellWidget(row, 4, container_pvp)


        # Botones
        self.agregar_botones_fila(row)

        # Recalcular totales
        self.calcular_totales()

        # Highlight de la fila añadida
        for col in range(self.tabla_articulos.columnCount()):
            item = self.tabla_articulos.item(row, col)
            if item:
                item.setBackground(QColor("rgba(163, 190, 140, 0.15)"))

        return True

    def agregar_fila_articulo(self):
        """Abre diálogo para añadir un nuevo artículo con marca y modelo"""
        dialog = ArticuloDialog(self.db, parent=self)

        if dialog.exec_():
            resultado = dialog.obtener_resultado()

            if resultado:
                # Verificar si el IMEI ya está en la tabla (no permitir duplicados)
                imei_nuevo = resultado.get('imei') or ''
                if imei_nuevo:
                    for row in range(self.tabla_articulos.rowCount()):
                        imei_container = self.tabla_articulos.cellWidget(row, 1)
                        if imei_container:
                            imei_widget = imei_container.findChild(QLineEdit)
                            if imei_widget and imei_widget.text() == imei_nuevo:
                                notify_warning(
                                    self,
                                    tr("Producto Duplicado"),
                                    tr("Este terminal ya está en la lista") + f":\nIMEI: {imei_nuevo}"
                                )
                                return

                # Crear fila con los datos del diálogo
                row = self.tabla_articulos.rowCount()
                self.tabla_articulos.insertRow(row)
                self.tabla_articulos.setRowHeight(row, 60)

                # Recuperar tema para estilos
                current_theme = QApplication.instance().property("theme") or "dark"
                t = THEMES[current_theme]

                # COLUMNA 0: Descripción
                desc_input = QLineEdit()
                desc_input.setText(resultado['descripcion'])
                desc_input.setFixedHeight(32)
                container_desc = QWidget()
                v_layout_desc = QVBoxLayout(container_desc)
                v_layout_desc.setContentsMargins(5, 0, 5, 10)
                v_layout_desc.setAlignment(Qt.AlignCenter)
                v_layout_desc.addWidget(desc_input)
                self.tabla_articulos.setCellWidget(row, 0, container_desc)

                # COLUMNA 1: IMEI/SN
                imei_input = QLineEdit()
                imei_input.setText(resultado.get('imei') or '')
                imei_input.setPlaceholderText("IMEI/Nº Serie")
                imei_input.setFixedSize(170, 32)
                container_imei = QWidget()
                v_layout_imei = QVBoxLayout(container_imei)
                v_layout_imei.setContentsMargins(5, 0, 5, 10)
                v_layout_imei.setAlignment(Qt.AlignCenter)
                v_layout_imei.addWidget(imei_input)
                self.tabla_articulos.setCellWidget(row, 1, container_imei)

                # COLUMNA 2: Cantidad
                cantidad_spin = QSpinBox()
                cantidad_spin.setMinimum(1)
                cantidad_spin.setMaximum(999)
                cantidad_spin.setValue(resultado.get('cantidad', 1))
                cantidad_spin.setFixedSize(60, 32)
                # Capturar row por valor usando default argument
                cantidad_spin.valueChanged.connect(lambda _, r=row: self.actualizar_pvp(r))
                container_cantidad = QWidget()
                v_layout_cantidad = QVBoxLayout(container_cantidad)
                v_layout_cantidad.setContentsMargins(5, 0, 5, 10)
                v_layout_cantidad.setAlignment(Qt.AlignCenter)
                v_layout_cantidad.addWidget(cantidad_spin)
                self.tabla_articulos.setCellWidget(row, 2, container_cantidad)

                # COLUMNA 3: Precio (sin IVA)
                pvp_valor = resultado.get('precio', 0)
                precio_sin_iva = pvp_valor / 1.21 if pvp_valor > 0 else 0

                precio_spin = QDoubleSpinBox()
                precio_spin.setMinimum(0)
                precio_spin.setMaximum(999999)
                precio_spin.setDecimals(2)
                precio_spin.setValue(precio_sin_iva)
                precio_spin.setFixedSize(90, 32)
                # Capturar row por valor usando default argument
                precio_spin.valueChanged.connect(lambda _, r=row: self.actualizar_pvp(r))
                container_precio = QWidget()
                v_layout_precio = QVBoxLayout(container_precio)
                v_layout_precio.setContentsMargins(5, 0, 5, 10)
                v_layout_precio.setAlignment(Qt.AlignCenter)
                v_layout_precio.addWidget(precio_spin)
                self.tabla_articulos.setCellWidget(row, 3, container_precio)

                # COLUMNA 4: PVP (con IVA) - solo lectura
                pvp_input = QLineEdit(f"{pvp_valor:.2f} €")
                pvp_input.setReadOnly(True)
                pvp_input.setAlignment(Qt.AlignCenter)
                pvp_input.setFixedSize(90, 32)
                pvp_input.setStyleSheet(f"color: white; background-color: {t['bg_input']};")
                container_pvp = QWidget()
                v_layout_pvp = QVBoxLayout(container_pvp)
                v_layout_pvp.setContentsMargins(5, 0, 5, 10)
                v_layout_pvp.setAlignment(Qt.AlignCenter)
                v_layout_pvp.addWidget(pvp_input)
                self.tabla_articulos.setCellWidget(row, 4, container_pvp)

                # COLUMNA 5: Botones
                self.agregar_botones_fila(row)

                # Recalcular totales
                self.calcular_totales()

    def actualizar_pvp(self, row):
        """Actualiza el PVP cuando cambia el Precio (sin IVA) o Cantidad"""
        precio_container = self.tabla_articulos.cellWidget(row, 3)
        pvp_container = self.tabla_articulos.cellWidget(row, 4)
        
        if precio_container and pvp_container:
            precio_spin = precio_container.findChild(QDoubleSpinBox)
            # PVP ahora es un QLineEdit de solo lectura
            pvp_widgets = pvp_container.findChildren(QLineEdit)
            pvp_input = pvp_widgets[0] if pvp_widgets else None
            
            if precio_spin and pvp_input:
                precio_sin_iva = precio_spin.value()
                pvp_con_iva = precio_sin_iva * 1.21  # Calculamos el PVP (precio + 21% IVA)
                pvp_input.setText(f"{pvp_con_iva:.2f} €")
                
                # Recalcular totales generales
                self.calcular_totales()


    def agregar_botones_fila(self, row):
        """Añade botón de eliminar a una fila - Centrado estructural"""
        container = QWidget()
        v_layout = QVBoxLayout(container)
        v_layout.setContentsMargins(8, 0, 8, 10)
        v_layout.setAlignment(Qt.AlignCenter)

        btn_del = QPushButton()
        btn_del.setToolTip(tr("Eliminar"))
        # Capturar row por valor usando default argument
        btn_del.clicked.connect(lambda checked=False, r=row: self.eliminar_fila(r))
        estilizar_btn_eliminar(btn_del)

        v_layout.addWidget(btn_del)
        self.tabla_articulos.setCellWidget(row, 5, container)

    def eliminar_fila(self, row):
        """Elimina una fila de artículos"""
        if self.tabla_articulos.rowCount() > 0:
            self.tabla_articulos.removeRow(row)
            self.calcular_totales()

    def calcular_totales(self):
        """Calcula y actualiza los totales.
        Suma los PVP (con IVA) y extrae el desglose.
        Cantidad siempre es 1 (móviles son unidades únicas)."""
        total_general = 0

        for row in range(self.tabla_articulos.rowCount()):
            pvp_container = self.tabla_articulos.cellWidget(row, 4)  # Columna PVP (índice 4)

            if pvp_container:
                # PVP ahora es un QLineEdit de solo lectura
                pvp_widgets = pvp_container.findChildren(QLineEdit)
                pvp_input = pvp_widgets[0] if pvp_widgets else None

                if pvp_input:

                    # Extraer el valor numérico del texto "XXX.XX €"
                    pvp_text = pvp_input.text().replace(' €', '').replace('€', '').strip()

                    try:
                        pvp_con_iva = float(pvp_text)
                        total_general += pvp_con_iva
                    except ValueError:
                        pass  # Si hay error al convertir, ignorar

        # Extraer IVA del total (el PVP YA incluye IVA)
        subtotal, iva, total_general = calcular_desglose_iva(total_general)

        self.subtotal_label.setText(f"{tr('Subtotal')}: {subtotal:.2f} €")
        self.iva_label.setText(f"{tr('IVA')} ({int(IVA_RATE*100)}%): {iva:.2f} €")
        self.total_label.setText(f"{tr('Total').upper()}: {total_general:.2f} €")

    def load_clientes(self):
        """Carga la lista de clientes"""
        self.cliente_combo.clear()
        self.cliente_combo.addItem("-- " + tr("Seleccionar Cliente") + " --", None)

        clientes = self.db.fetch_all("SELECT id, nombre FROM clientes ORDER BY nombre")
        for cliente in clientes:
            self.cliente_combo.addItem(cliente['nombre'], cliente['id'])

    def on_cliente_selected(self, index):
        """Cuando se selecciona un cliente, carga sus datos"""
        cliente_id = self.cliente_combo.currentData()
        if cliente_id:
            cliente = self.db.fetch_one("SELECT * FROM clientes WHERE id = ?", (cliente_id,))
            if cliente:
                self.nombre_input.setText(cliente['nombre'])
                self.nif_input.setText(cliente['nif'] or '')
                self.direccion_input.setText(cliente['direccion'] or '')
                self.telefono_input.setText(cliente['telefono'] or '')
                self.cp_input.setText(cliente.get('codigo_postal') or '')
                self.ciudad_input.setText(cliente.get('ciudad') or '')
                self.provincia_input.setText(cliente.get('provincia') or '')

    def abrir_nuevo_cliente(self):
        """Abre diálogo para crear nuevo cliente"""
        from app.ui.cliente_dialog import ClienteDialog
        dialog = ClienteDialog(self.db, parent=self)
        if dialog.exec_():
            self.load_clientes()

    def cargar_nuevo_numero_factura(self):
        """Carga el siguiente número de factura"""
        numero = self.factura_manager.obtener_siguiente_numero()
        self.numero_input.setText(numero)

    def guardar_factura(self):
        """Guarda la factura y genera el PDF"""
        if not self.nombre_input.text().strip():
            notify_warning(self, tr("Error"), tr("Debe ingresar el nombre del cliente"))
            return

        # ========== VERIFICACIÓN DE CAJA ==========
        from app.modules.caja_manager import CajaManager
        from datetime import date as date_module

        caja_manager = CajaManager(self.db)
        fecha_hoy = date_module.today().strftime('%Y-%m-%d')
        estado_caja, data_caja = caja_manager.verificar_estado_caja_completo(fecha_hoy)

        # CASO 1: Cierre pendiente de día anterior
        if estado_caja == 'cierre_pendiente':
            fecha_pendiente = data_caja['fecha'] if data_caja else 'anterior'
            notify_warning(
                self,
                tr("Cierre de Caja Pendiente"),
                tr("Hay una caja del día") + f" {fecha_pendiente} " + tr("sin cerrar.") + "\n\n"
                + tr("Debe cerrar esa caja antes de registrar ventas.") + "\n\n"
                + "👉 " + tr("Vaya a") + ": " + tr("Caja") + " → " + tr("Movimientos") + "\n"
                + "👉 " + tr("Use el botón") + " 🔒 " + tr("Cerrar Caja")
            )
            return

        # CASO 2: Caja de hoy no abierta
        if estado_caja in ['apertura_requerida', 'apertura_nueva_dia']:
            notify_warning(
                self,
                tr("Apertura de Caja Requerida"),
                tr("La caja de hoy no está abierta.") + "\n\n"
                + tr("Debe abrir la caja antes de registrar ventas.") + "\n\n"
                + "👉 " + tr("Vaya a") + ": " + tr("Caja") + " → " + tr("Movimientos") + "\n"
                + "👉 " + tr("Use el botón") + " 🔓 " + tr("Abrir Caja")
            )
            return

        # CASO 3: Caja ya cerrada hoy
        if estado_caja == 'reapertura_requerida':
            notify_warning(
                self,
                tr("Caja Ya Cerrada"),
                tr("La caja de hoy ya fue cerrada.") + "\n\n"
                + tr("Para registrar ventas debe reabrir la caja.") + "\n\n"
                + "👉 " + tr("Vaya a") + ": " + tr("Caja") + " → " + tr("Movimientos")
            )
            return
        # ========== FIN VERIFICACIÓN DE CAJA ==========

        datos_factura = {
            'numero': self.numero_input.text(),
            'fecha': self.fecha_input.date().toPyDate(),
            'cliente': {
                'nombre': self.nombre_input.text(),
                'nif': self.nif_input.text(),
                'direccion': self.direccion_input.text(),
                'telefono': self.telefono_input.text(),
                'codigo_postal': self.cp_input.text(),
                'ciudad': self.ciudad_input.text(),
                'provincia': self.provincia_input.text()
            },
            'items': [],
            'totales': {}
        }

        # Recopilar items con cantidad
        for row in range(self.tabla_articulos.rowCount()):
            desc_container = self.tabla_articulos.cellWidget(row, 0)
            imei_container = self.tabla_articulos.cellWidget(row, 1)
            cantidad_container = self.tabla_articulos.cellWidget(row, 2)
            pvp_container = self.tabla_articulos.cellWidget(row, 4)  # Columna PVP (con IVA)

            if desc_container and pvp_container:
                # Obtener widgets internos
                desc_widget = desc_container.findChild(QLineEdit)
                imei_widget = imei_container.findChild(QLineEdit) if imei_container else None
                cantidad_widget = cantidad_container.findChild(QSpinBox) if cantidad_container else None
                pvp_widget = pvp_container.findChild(QLineEdit)  # PVP es QLineEdit readonly

                if desc_widget and pvp_widget:
                    descripcion = desc_widget.text()
                    # Recuperar producto_id guardado en la propiedad del widget
                    producto_id = desc_widget.property("producto_id")
                    cantidad = cantidad_widget.value() if cantidad_widget else 1
                    
                    # Extraer valor numérico del PVP (formato "XXX.XX €")
                    pvp_text = pvp_widget.text().replace(' €', '').replace('€', '').strip()
                    try:
                        pvp_valor = float(pvp_text)
                    except ValueError:
                        pvp_valor = 0
                    
                    if descripcion.strip():
                        # Obtener estado del producto desde la BD (para el documento de garantía)
                        estado_producto = None
                        if producto_id:
                            row_prod = self.db.fetch_one(
                                "SELECT estado FROM productos WHERE id = ?", (producto_id,)
                            )
                            if row_prod:
                                estado_producto = row_prod.get('estado')
                        datos_factura['items'].append({
                            'descripcion': descripcion,
                            'producto_id': producto_id,
                            'imei': imei_widget.text() if imei_widget else '',
                            'cantidad': cantidad,
                            'precio': pvp_valor,  # Ahora guardamos el PVP directamente
                            'estado': estado_producto,
                        })

        if not datos_factura['items']:
            notify_warning(self, tr("Error"), tr("Debe añadir al menos un artículo"))
            return

        # Calcular totales (los precios YA incluyen IVA)
        total = sum(item['cantidad'] * item['precio'] for item in datos_factura['items'])
        subtotal, iva, total = calcular_desglose_iva(total)

        datos_factura['totales'] = {
            'subtotal': subtotal,
            'iva': iva,
            'total': total
        }

        # Confirmación
        from app.ui.confirmacion_impresion_dialog import ConfirmacionImpresionDialog
        dialog = ConfirmacionImpresionDialog(titulo=tr("Finalizar Venta"), mensaje=f"{tr('Total')}: {total:.2f} €\n{tr('¿Cómo desea procesar la venta?')}")
        if not dialog.exec_():
            return
        
        accion = dialog.accion

        if accion == 'imprimir':
            # === MODO COMPLETO: Guardar + Imprimir ===
            from app.ui.unified_progress_dialog import UnifiedProgressDialog

            # Verificar impresora ANTES de empezar
            result = self.db.fetch_one(
                "SELECT valor FROM configuracion WHERE clave = 'printer_general'"
            )
            printer_name = result['valor'] if result and result['valor'] and '---' not in result['valor'] else None

            if not printer_name:
                notify_warning(self, tr("Sin Impresora"),
                    tr("No hay impresora general configurada.") + "\n" +
                    tr("Ve a Ajustes > Impresoras para configurarla."))
                return

            # Variable para guardar el ID
            factura_id_result = [None]

            def do_save():
                usuario_id = self._obtener_usuario_id()
                factura_id_result[0] = self.factura_manager.guardar_factura(datos_factura, usuario_id=usuario_id)
                # El movimiento de caja ahora se registra DENTRO de guardar_factura
                return factura_id_result[0]

            def do_generate_pdf(factura_id):
                return self.pdf_generator.generar_factura(datos_factura, factura_id)

            # Crear y configurar diálogo unificado
            progress = UnifiedProgressDialog(self, UnifiedProgressDialog.MODE_FULL, tr("Procesando Venta"))
            progress.set_save_callback(do_save)
            progress.set_pdf_callback(do_generate_pdf)
            progress.set_printer_config(printer_name)

            # Ejecutar (bloquea hasta terminar)
            success = progress.execute()

            # Limpiar si se guardó en BD (aunque impresión falle)
            if progress.save_completed:
                # Refrescar historial
                try:
                    main_window = self.window()
                    if hasattr(main_window, 'historial_tab'):
                        main_window.historial_tab.cargar_facturas()
                except (OSError, ValueError, RuntimeError):
                    pass
                self.limpiar_formulario()

        elif accion == 'garantia':
            # === MODO COMPLETO: Guardar + Imprimir GARANTÍA ===
            from app.ui.unified_progress_dialog import UnifiedProgressDialog

            # Verificar impresora ANTES de empezar
            result = self.db.fetch_one(
                "SELECT valor FROM configuracion WHERE clave = 'printer_general'"
            )
            printer_name = result['valor'] if result and result['valor'] and '---' not in result['valor'] else None

            if not printer_name:
                notify_warning(self, tr("Sin Impresora"),
                    tr("No hay impresora general configurada.") + "\n" +
                    tr("Ve a Ajustes > Impresoras para configurarla."))
                return

            factura_id_result = [None]

            def do_save_garantia():
                usuario_id = self._obtener_usuario_id()
                factura_id_result[0] = self.factura_manager.guardar_factura(datos_factura, usuario_id=usuario_id)
                return factura_id_result[0]

            def do_generate_garantia(factura_id):
                return self.pdf_generator.generar_garantia(datos_factura, factura_id)

            progress = UnifiedProgressDialog(self, UnifiedProgressDialog.MODE_FULL, tr("Procesando Garantía"))
            progress.set_save_callback(do_save_garantia)
            progress.set_pdf_callback(do_generate_garantia)
            progress.set_printer_config(printer_name)

            progress.execute()

            if progress.save_completed:
                try:
                    main_window = self.window()
                    if hasattr(main_window, 'historial_tab'):
                        main_window.historial_tab.cargar_facturas()
                except (OSError, ValueError, RuntimeError):
                    pass
                self.limpiar_formulario()

        else:
            # === SOLO GUARDAR (sin imprimir) ===
            try:
                usuario_id = self._obtener_usuario_id()
                factura_id = self.factura_manager.guardar_factura(datos_factura, usuario_id=usuario_id)

                if not factura_id:
                    notify_error(self, tr("Error"), tr("No se pudo guardar la venta"))
                    return

                # El movimiento de caja ahora se registra DENTRO de guardar_factura

                notify_success(self, tr("Venta Guardada"),
                    tr("¡Venta guardada con éxito!") + f"\n{datos_factura['numero']}\n\n{tr('Total')}: {total:.2f} €")

                # Refrescar historial
                try:
                    main_window = self.window()
                    if hasattr(main_window, 'historial_tab'):
                        main_window.historial_tab.cargar_facturas()
                except (OSError, ValueError, RuntimeError):
                    pass

                self.limpiar_formulario()

            except (OSError, ValueError, RuntimeError) as e:
                notify_error(self, tr("Error"), tr("Error al guardar") + f":\n{str(e)}")

    def limpiar_formulario(self):
        """Limpia el formulario para una nueva factura"""
        self.cliente_combo.setCurrentIndex(0)
        self.nombre_input.clear()
        self.nif_input.clear()
        self.direccion_input.clear()
        self.telefono_input.clear()
        self.cp_input.clear()
        self.ciudad_input.clear()
        self.provincia_input.clear()
        self.busqueda_cliente_input.clear()
        self.producto_busqueda_input.clear()

        # Limpiar tabla
        self.tabla_articulos.setRowCount(0)

        # Actualizar número
        self.cargar_nuevo_numero_factura()
        self.fecha_input.setDate(QDate.currentDate())

        self.calcular_totales()

    def closeEvent(self, event):
        if hasattr(self, 'db') and self.db:
            self.db.disconnect()
        super().closeEvent(event)
