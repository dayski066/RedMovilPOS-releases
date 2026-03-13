"""
Diálogo para ver detalles de una factura
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
                             QTableWidgetItem, QPushButton, QGroupBox, QHeaderView)
from PyQt5.QtCore import Qt
from app.i18n import tr
from app.modules.factura_manager import FacturaManager
from config import IVA_RATE
from datetime import datetime
from app.ui.transparent_buttons import apply_btn_cancel


class FacturaDetalleDialog(QDialog):
    def __init__(self, db, factura_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.factura_manager = FacturaManager(db)
        self.factura = self.factura_manager.obtener_factura(factura_id)

        self.setWindowTitle(f"{tr('Detalle de Factura')} {self.factura['numero_factura']}")
        self.setModal(True)
        self.setMinimumSize(700, 500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Información de factura
        info_group = QGroupBox(tr("Información General"))
        info_layout = QVBoxLayout()

        info_grid = QHBoxLayout()

        # Columna izquierda
        left_col = QVBoxLayout()
        left_col.addWidget(QLabel(f"<b>{tr('Nº Factura')}:</b> {self.factura['numero_factura']}"))

        # Convertir fecha (SQLite devuelve string)
        fecha_str = self.factura['fecha']
        if isinstance(fecha_str, str):
            try:
                fecha_dt = datetime.strptime(fecha_str, '%Y-%m-%d')
                fecha_display = fecha_dt.strftime('%d/%m/%Y')
            except (OSError, ValueError, RuntimeError):
                fecha_display = fecha_str
        else:
            fecha_display = fecha_str.strftime('%d/%m/%Y')

        left_col.addWidget(QLabel(f"<b>{tr('Fecha')}:</b> {fecha_display}"))
        left_col.addWidget(QLabel(f"<b>{tr('Cliente')}:</b> {self.factura['cliente_nombre'] or tr('Sin nombre')}"))

        # Columna derecha
        right_col = QVBoxLayout()
        if self.factura['cliente_nif']:
            right_col.addWidget(QLabel(f"<b>{tr('NIF')}:</b> {self.factura['cliente_nif']}"))
        if self.factura['cliente_direccion']:
            right_col.addWidget(QLabel(f"<b>{tr('Dirección')}:</b> {self.factura['cliente_direccion']}"))
        if self.factura['cliente_telefono']:
            right_col.addWidget(QLabel(f"<b>{tr('Teléfono')}:</b> {self.factura['cliente_telefono']}"))

        info_grid.addLayout(left_col)
        info_grid.addLayout(right_col)
        info_layout.addLayout(info_grid)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Tabla de items
        items_label = QLabel(tr("Artículos / Servicios"))
        items_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 10px;")
        layout.addWidget(items_label)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(7)
        self.tabla.setHorizontalHeaderLabels([
            tr("Descripción"), tr("Marca"), tr("Modelo"), tr("IMEI/SN"), tr("Cantidad"), tr("Precio Unit."), tr("Total")
        ])

        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)

        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Estilo Global de Tabla
        self.tabla.verticalHeader().setDefaultSectionSize(60)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setStyleSheet("QTableWidget::item { padding: 0px; }")

        # Llenar tabla
        for item in self.factura['items']:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            self.tabla.setRowHeight(row, 60)

            # Centrado de todos los items
            for i, val in enumerate([
                item['descripcion'],
                item.get('marca_nombre') or tr('N/A'),
                item.get('modelo_nombre') or tr('N/A'),
                item['imei_sn'] or '-',
                str(item['cantidad']),
                f"{float(item['precio_unitario']):.2f} €",
                f"{float(item['total']):.2f} €"
            ]):
                table_item = QTableWidgetItem(val)
                table_item.setTextAlignment(Qt.AlignCenter)
                self.tabla.setItem(row, i, table_item)

        layout.addWidget(self.tabla)

        # Totales
        totales_group = QGroupBox(tr("Totales"))
        totales_layout = QVBoxLayout()

        totales_layout.addWidget(QLabel(f"{tr('Subtotal')}: {float(self.factura['subtotal']):.2f} €"))
        totales_layout.addWidget(QLabel(f"{tr('IVA')} ({int(IVA_RATE*100)}%): {float(self.factura['iva']):.2f} €"))

        total_label = QLabel(f"{tr('TOTAL')}: {float(self.factura['total']):.2f} €")
        total_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #A3BE8C;")
        totales_layout.addWidget(total_label)

        totales_group.setLayout(totales_layout)
        totales_group.setMaximumWidth(250)

        totales_container = QHBoxLayout()
        totales_container.addStretch()
        totales_container.addWidget(totales_group)
        layout.addLayout(totales_container)

        # Botón cerrar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cerrar = QPushButton(tr("Cerrar"))
        btn_cerrar.clicked.connect(self.accept)
        apply_btn_cancel(btn_cerrar)

        btn_layout.addWidget(btn_cerrar)
        layout.addLayout(btn_layout)
