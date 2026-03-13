"""
Pestaña de estadísticas y reportes - Dashboard con tarjetas KPI
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
                             QTableWidget, QTableWidgetItem,
                             QHeaderView, QScrollArea, QFrame, QGridLayout)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from app.db.database import Database
from app.i18n import tr


class KPICard(QWidget):
    """Tarjeta KPI individual con icono, título y valor"""
    def __init__(self, title, value="0.00 €", color="#88C0D0", icon_text="", parent=None):
        super().__init__(parent)
        self.color = color
        self.setObjectName("kpiCard")
        self.setMinimumHeight(110)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(6)

        # Fila superior: icono + título
        header = QHBoxLayout()
        header.setSpacing(8)

        if icon_text:
            icon_lbl = QLabel(icon_text)
            icon_lbl.setStyleSheet(f"font-size: 18px; background: transparent; color: {color};")
            icon_lbl.setFixedWidth(24)
            header.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #7B88A0; background: transparent; letter-spacing: 1px;")
        header.addWidget(title_lbl)
        header.addStretch()
        layout.addLayout(header)

        # Valor principal
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"font-size: 26px; font-weight: bold; color: {color}; background: transparent; padding: 4px 0;")
        layout.addWidget(self.value_label)

        # Estilo de la tarjeta
        self.setStyleSheet(f"""
            QWidget#kpiCard {{
                background-color: #3B4252;
                border: 1px solid #434C5E;
                border-radius: 12px;
                border-left: 4px solid {color};
            }}
        """)

    def set_value(self, text):
        self.value_label.setText(text)


class EstadisticasTab(QWidget):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.db.connect()
        self.setup_ui()
        self.cargar_estadisticas()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 16, 24, 24)
        layout.setSpacing(20)

        # === CAJA (Ventas TPV) ===
        caja_title = QLabel(tr("CAJA DEL DÍA"))
        caja_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #88C0D0; padding: 0; background: transparent; letter-spacing: 2px;")
        layout.addWidget(caja_title)

        caja_grid = QGridLayout()
        caja_grid.setSpacing(12)

        self.card_efectivo = KPICard(tr("EFECTIVO"), "0.00 €", "#A3BE8C", "$")
        self.card_tarjeta = KPICard(tr("TARJETA"), "0.00 €", "#5E81AC", "⬡")
        self.card_bizum = KPICard(tr("BIZUM"), "0.00 €", "#B48EAD", "⚡")
        self.card_total_caja = KPICard(tr("TOTAL CAJA"), "0.00 €", "#88C0D0", "∑")

        caja_grid.addWidget(self.card_efectivo, 0, 0)
        caja_grid.addWidget(self.card_tarjeta, 0, 1)
        caja_grid.addWidget(self.card_bizum, 0, 2)
        caja_grid.addWidget(self.card_total_caja, 0, 3)
        layout.addLayout(caja_grid)

        # === VENTAS & COMPRAS ===
        ventas_title = QLabel(tr("VENTAS Y COMPRAS"))
        ventas_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #88C0D0; padding: 0; background: transparent; letter-spacing: 2px;")
        layout.addWidget(ventas_title)

        vc_grid = QGridLayout()
        vc_grid.setSpacing(12)

        self.card_ventas_hoy = KPICard(tr("VENTAS HOY"), "0.00 €", "#A3BE8C", "▲")
        self.card_ventas_mes = KPICard(tr("VENTAS MES"), "0.00 €", "#8FBCBB", "▲")
        self.card_compras_hoy = KPICard(tr("COMPRAS HOY"), "0.00 €", "#EBCB8B", "▼")
        self.card_compras_mes = KPICard(tr("COMPRAS MES"), "0.00 €", "#D08770", "▼")

        vc_grid.addWidget(self.card_ventas_hoy, 0, 0)
        vc_grid.addWidget(self.card_ventas_mes, 0, 1)
        vc_grid.addWidget(self.card_compras_hoy, 0, 2)
        vc_grid.addWidget(self.card_compras_mes, 0, 3)
        layout.addLayout(vc_grid)

        # === REPARACIONES ===
        rep_title = QLabel(tr("REPARACIONES"))
        rep_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #88C0D0; padding: 0; background: transparent; letter-spacing: 2px;")
        layout.addWidget(rep_title)

        rep_grid = QGridLayout()
        rep_grid.setSpacing(12)

        self.card_rep_hoy = KPICard(tr("REPARACIONES HOY"), "0.00 €", "#81A1C1", "⚙")
        self.card_rep_mes = KPICard(tr("REPARACIONES MES"), "0.00 €", "#5E81AC", "⚙")

        rep_grid.addWidget(self.card_rep_hoy, 0, 0)
        rep_grid.addWidget(self.card_rep_mes, 0, 1)
        rep_grid.setColumnStretch(2, 1)
        layout.addLayout(rep_grid)

        # === PRODUCTOS CON BAJO STOCK ===
        stock_title = QLabel(tr("PRODUCTOS CON BAJO STOCK"))
        stock_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #BF616A; padding: 0; background: transparent; letter-spacing: 2px;")
        layout.addWidget(stock_title)

        self.tabla_stock = QTableWidget()
        self.tabla_stock.setColumnCount(3)
        self.tabla_stock.setHorizontalHeaderLabels([tr("Producto"), tr("Stock"), tr("Categoría")])

        header_stock = self.tabla_stock.horizontalHeader()
        header_stock.setSectionResizeMode(0, QHeaderView.Stretch)
        header_stock.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_stock.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        self.tabla_stock.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla_stock.verticalHeader().setDefaultSectionSize(48)
        self.tabla_stock.verticalHeader().setVisible(False)
        self.tabla_stock.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tabla_stock.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        layout.addWidget(self.tabla_stock)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        self.tabla_stock.setMinimumHeight(400)

    def cargar_estadisticas(self):
        """Carga todas las estadísticas"""
        self.cargar_resumen_caja_hoy()

        # Ventas (facturas) - Hoy
        query_ventas_hoy = """
            SELECT SUM(total) as total
            FROM facturas
            WHERE DATE(fecha) = DATE('now')
        """
        ventas_hoy = self.db.fetch_one(query_ventas_hoy)
        total_ventas_hoy = float(ventas_hoy['total'] or 0)

        # Ventas (facturas) - Mes
        query_ventas_mes = """
            SELECT SUM(total) as total
            FROM facturas
            WHERE strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now')
        """
        ventas_mes = self.db.fetch_one(query_ventas_mes)
        total_ventas_mes = float(ventas_mes['total'] or 0)

        self.card_ventas_hoy.set_value(f"{total_ventas_hoy:,.2f} €")
        self.card_ventas_mes.set_value(f"{total_ventas_mes:,.2f} €")

        # Reparaciones - Hoy
        query_reparaciones_hoy = """
            SELECT SUM(costo_final) as total
            FROM reparaciones
            WHERE DATE(fecha_entrada) = DATE('now')
        """
        reparaciones_hoy = self.db.fetch_one(query_reparaciones_hoy)
        total_reparaciones_hoy = float(reparaciones_hoy['total'] or 0) if reparaciones_hoy and reparaciones_hoy['total'] else 0.0

        # Reparaciones - Mes
        query_reparaciones_mes = """
            SELECT SUM(costo_final) as total
            FROM reparaciones
            WHERE strftime('%Y-%m', fecha_entrada) = strftime('%Y-%m', 'now')
        """
        reparaciones_mes = self.db.fetch_one(query_reparaciones_mes)
        total_reparaciones_mes = float(reparaciones_mes['total'] or 0) if reparaciones_mes and reparaciones_mes['total'] else 0.0

        self.card_rep_hoy.set_value(f"{total_reparaciones_hoy:,.2f} €")
        self.card_rep_mes.set_value(f"{total_reparaciones_mes:,.2f} €")

        self.cargar_productos_bajo_stock()

    def cargar_resumen_caja_hoy(self):
        """Carga el resumen de caja y compras"""
        query_ventas = """
            SELECT metodo_pago, SUM(total) as total
            FROM ventas_caja
            WHERE DATE(fecha) = DATE('now')
            AND estado = 'completada'
            GROUP BY metodo_pago
        """
        ventas = self.db.fetch_all(query_ventas)

        total_efectivo = 0.0
        total_tarjeta = 0.0
        total_bizum = 0.0

        for venta in ventas:
            metodo = venta['metodo_pago'].lower()
            total = float(venta['total'] or 0)

            if metodo == 'efectivo':
                total_efectivo = total
            elif metodo == 'tarjeta':
                total_tarjeta = total
            elif metodo == 'bizum':
                total_bizum = total

        total_ventas_dia = total_efectivo + total_tarjeta + total_bizum

        self.card_efectivo.set_value(f"{total_efectivo:,.2f} €")
        self.card_tarjeta.set_value(f"{total_tarjeta:,.2f} €")
        self.card_bizum.set_value(f"{total_bizum:,.2f} €")
        self.card_total_caja.set_value(f"{total_ventas_dia:,.2f} €")

        # Compras
        query_compras_hoy = """
            SELECT SUM(total) as total
            FROM compras
            WHERE DATE(fecha) = DATE('now')
        """
        compras_hoy = self.db.fetch_one(query_compras_hoy)
        total_compras_hoy = float(compras_hoy['total'] or 0)

        query_compras_mes = """
            SELECT SUM(total) as total
            FROM compras
            WHERE strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now')
        """
        compras_mes = self.db.fetch_one(query_compras_mes)
        total_compras_mes = float(compras_mes['total'] or 0)

        self.card_compras_hoy.set_value(f"{total_compras_hoy:,.2f} €")
        self.card_compras_mes.set_value(f"{total_compras_mes:,.2f} €")

    def cargar_productos_bajo_stock(self):
        """Carga productos con stock <= 3 excluyendo categoría Móviles (ID=1)"""
        query = """
            SELECT descripcion, stock, categoria_id
            FROM productos
            WHERE stock <= 3
            AND (categoria_id != 1 OR categoria_id IS NULL)
            AND activo = 1
            ORDER BY stock ASC, descripcion
            LIMIT 50
        """
        productos = self.db.fetch_all(query)

        cat_nombres = {}
        if productos:
            cat_ids = [p['categoria_id'] for p in productos if p['categoria_id']]
            if cat_ids:
                placeholders = ','.join(['?' for _ in cat_ids])
                cats_query = f"SELECT id, nombre FROM categorias WHERE id IN ({placeholders})"
                cats = self.db.fetch_all(cats_query, tuple(cat_ids))
                cat_nombres = {c['id']: c['nombre'] for c in cats}

        self.tabla_stock.setRowCount(0)

        for producto in productos:
            row = self.tabla_stock.rowCount()
            self.tabla_stock.insertRow(row)
            self.tabla_stock.setRowHeight(row, 48)

            p_item = QTableWidgetItem(producto['descripcion'])
            p_item.setTextAlignment(Qt.AlignCenter)
            self.tabla_stock.setItem(row, 0, p_item)

            stock_item = QTableWidgetItem(str(producto['stock']))
            stock_item.setTextAlignment(Qt.AlignCenter)
            if producto['stock'] == 0:
                stock_item.setForeground(QColor("#BF616A"))
                stock_item.setFont(QFont("Segoe UI", 11, QFont.Bold))
            elif producto['stock'] == 1:
                stock_item.setForeground(QColor("#D08770"))
            elif producto['stock'] <= 3:
                stock_item.setForeground(QColor("#EBCB8B"))
            self.tabla_stock.setItem(row, 1, stock_item)

            cat_id = producto.get('categoria_id')
            cat_nombre = cat_nombres.get(cat_id, tr('Sin categoría')) if cat_id else tr('Sin categoría')
            c_item = QTableWidgetItem(cat_nombre)
            c_item.setTextAlignment(Qt.AlignCenter)
            self.tabla_stock.setItem(row, 2, c_item)

        rows = self.tabla_stock.rowCount()
        if rows > 0:
            total_height = rows * 48 + 50
            self.tabla_stock.setMinimumHeight(total_height)
            self.tabla_stock.setMaximumHeight(total_height)
        else:
            self.tabla_stock.setMinimumHeight(150)

    def showEvent(self, event):
        """Se ejecuta automáticamente cuando se muestra la pestaña"""
        super().showEvent(event)
        self.cargar_estadisticas()

    def closeEvent(self, event):
        """Cierra la conexión a la base de datos al cerrar el tab"""
        if hasattr(self, 'db') and self.db:
            self.db.disconnect()
        super().closeEvent(event)
