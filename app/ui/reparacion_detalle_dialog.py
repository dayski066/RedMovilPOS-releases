"""
Diálogo para ver detalles de una reparación (Multidispositivo)
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
                             QPushButton, QHBoxLayout, QHeaderView, QFrame,
                             QScrollArea, QWidget)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from app.modules.reparacion_manager import ReparacionManager
from app.i18n import tr
from app.ui.transparent_buttons import apply_btn_cancel

class ReparacionDetalleDialog(QDialog):
    def __init__(self, db, reparacion_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.reparacion_id = reparacion_id
        self.reparacion_manager = ReparacionManager(db)
        self.setup_ui()
        self.cargar_datos()

    def setup_ui(self):
        self.setWindowTitle(tr("Detalle Reparación"))
        self.setMinimumWidth(850)
        self.setMinimumHeight(750)

        main_layout = QVBoxLayout(self)

        # Scroll área para contenido
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setSpacing(10)

        # Header
        self.lbl_titulo = QLabel(tr("Orden de Reparación"))
        self.lbl_titulo.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        layout.addWidget(self.lbl_titulo)

        # Info Cliente
        self.lbl_cliente = QLabel()
        self.lbl_cliente.setStyleSheet("font-size: 13px; padding: 10px; background: #3B4252; border-radius: 5px; color: #ECEFF4;")
        layout.addWidget(self.lbl_cliente)

        # Tabla Dispositivos
        layout.addWidget(QLabel("<b>" + tr("Dispositivos") + ":</b>"))
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(5)
        self.tabla.setHorizontalHeaderLabels([tr("Dispositivo"), "IMEI", tr("Precio"), tr("Patrón/Código"), tr("Notas")])
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tabla.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tabla.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tabla.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.verticalHeader().setDefaultSectionSize(45)
        self.tabla.verticalHeader().setVisible(False)
        layout.addWidget(self.tabla)

        # Tabla Averías/Soluciones
        self.lbl_averias_titulo = QLabel("<b>" + tr("Averías y Soluciones") + ":</b>")
        layout.addWidget(self.lbl_averias_titulo)

        self.tabla_averias = QTableWidget()
        self.tabla_averias.setColumnCount(4)
        self.tabla_averias.setHorizontalHeaderLabels([tr("Dispositivo"), tr("Avería"), tr("Solución"), tr("Precio")])
        self.tabla_averias.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tabla_averias.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabla_averias.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tabla_averias.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tabla_averias.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla_averias.verticalHeader().setDefaultSectionSize(40)
        self.tabla_averias.verticalHeader().setVisible(False)
        layout.addWidget(self.tabla_averias)

        # Tabla Recambios (solo si hay)
        self.lbl_recambios_titulo = QLabel("<b>" + tr("Recambios Utilizados") + ":</b>")
        self.lbl_recambios_titulo.setStyleSheet("color: #5E81AC;")
        layout.addWidget(self.lbl_recambios_titulo)
        self.lbl_recambios_titulo.setVisible(False)

        self.tabla_recambios = QTableWidget()
        self.tabla_recambios.setColumnCount(4)
        self.tabla_recambios.setHorizontalHeaderLabels([tr("Descripción"), tr("Cantidad"), tr("Precio Unit."), tr("Total")])
        self.tabla_recambios.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tabla_recambios.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tabla_recambios.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tabla_recambios.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tabla_recambios.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla_recambios.verticalHeader().setDefaultSectionSize(35)
        self.tabla_recambios.verticalHeader().setVisible(False)
        self.tabla_recambios.setVisible(False)
        layout.addWidget(self.tabla_recambios)

        self.lbl_total_recambios = QLabel()
        self.lbl_total_recambios.setStyleSheet("font-size: 14px; font-weight: bold; color: #5E81AC;")
        self.lbl_total_recambios.setAlignment(Qt.AlignRight)
        self.lbl_total_recambios.setVisible(False)
        layout.addWidget(self.lbl_total_recambios)

        # Estado y Total
        self.lbl_estado = QLabel()
        self.lbl_total = QLabel()
        self.lbl_total.setStyleSheet("font-size: 16px; font-weight: bold; color: #A3BE8C;")

        layout.addWidget(self.lbl_estado)
        layout.addWidget(self.lbl_total)

        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

        # Botón Cerrar
        btn_cerrar = QPushButton(tr("Cerrar"))
        btn_cerrar.clicked.connect(self.accept)
        apply_btn_cancel(btn_cerrar)
        main_layout.addWidget(btn_cerrar)

    def cargar_datos(self):
        reparacion = self.reparacion_manager.obtener_reparacion(self.reparacion_id)
        if not reparacion:
            self.lbl_titulo.setText("Error: " + tr("No encontrada"))
            return

        # Titulo
        self.lbl_titulo.setText(f"{tr('Orden')}: {reparacion.get('numero_orden')} - {tr('Fecha')}: {reparacion.get('fecha_entrada')}")

        # Cliente
        self.lbl_cliente.setText(
            f"<b>{tr('Cliente')}:</b> {reparacion.get('cliente_nombre')}<br>"
            f"<b>{tr('Teléfono')}:</b> {reparacion.get('cliente_telefono') or 'N/A'}<br>"
            f"<b>{tr('Dirección')}:</b> {reparacion.get('cliente_direccion') or 'N/A'}"
        )

        # Items (Dispositivos)
        items = reparacion.get('items', [])
        self.tabla.setRowCount(len(items))
        total = 0

        for i, item in enumerate(items):
            dispositivo = f"{item.get('marca_nombre', '')} {item.get('modelo_nombre', '')}".strip() or '-'
            celdas = [
                dispositivo,
                item.get('imei', '') or '-',
                f"{item.get('precio_estimado', 0):.2f} €",
                item.get('patron_codigo', '') or '-',
                item.get('notas', '') or '-'
            ]

            for col, texto in enumerate(celdas):
                t_item = QTableWidgetItem(texto)
                t_item.setTextAlignment(Qt.AlignCenter)
                self.tabla.setItem(i, col, t_item)

            total += item.get('precio_estimado', 0)

        # Averías y Soluciones (de todos los items)
        todas_averias = []
        for item in items:
            dispositivo = f"{item.get('marca_nombre', '')} {item.get('modelo_nombre', '')}".strip() or '-'
            averias = item.get('averias', [])

            if averias:
                for averia in averias:
                    todas_averias.append({
                        'dispositivo': dispositivo,
                        'averia': averia.get('descripcion_averia', '') or '-',
                        'solucion': averia.get('solucion', '') or '-',
                        'precio': averia.get('precio', 0)
                    })
            else:
                # Si no hay averías en la tabla separada, usar los campos del item
                averia_texto = item.get('averia_texto') or item.get('averia', '')
                solucion_texto = item.get('solucion_texto', '')
                if averia_texto or solucion_texto:
                    todas_averias.append({
                        'dispositivo': dispositivo,
                        'averia': averia_texto or '-',
                        'solucion': solucion_texto or '-',
                        'precio': 0
                    })

        # Mostrar u ocultar tabla de averías
        if todas_averias:
            self.tabla_averias.setRowCount(len(todas_averias))
            for i, av in enumerate(todas_averias):
                celdas = [
                    av['dispositivo'],
                    av['averia'],
                    av['solucion'],
                    f"{av['precio']:.2f} €" if av['precio'] else '-'
                ]
                for col, texto in enumerate(celdas):
                    t_item = QTableWidgetItem(texto)
                    t_item.setTextAlignment(Qt.AlignCenter)
                    self.tabla_averias.setItem(i, col, t_item)
            self.lbl_averias_titulo.setVisible(True)
            self.tabla_averias.setVisible(True)
        else:
            self.lbl_averias_titulo.setVisible(False)
            self.tabla_averias.setVisible(False)

        # Recambios (solo si hay)
        recambios = self.reparacion_manager.obtener_recambios(self.reparacion_id)
        if recambios:
            self.tabla_recambios.setRowCount(len(recambios))
            total_recambios = 0

            for i, rec in enumerate(recambios):
                cantidad = rec.get('cantidad', 1)
                precio_unit = rec.get('precio_unitario', 0)
                total_rec = cantidad * precio_unit
                total_recambios += total_rec

                celdas = [
                    rec.get('descripcion', '-'),
                    str(cantidad),
                    f"{precio_unit:.2f} €",
                    f"{total_rec:.2f} €"
                ]
                for col, texto in enumerate(celdas):
                    t_item = QTableWidgetItem(texto)
                    t_item.setTextAlignment(Qt.AlignCenter)
                    if col == 3:  # Total en verde
                        t_item.setForeground(QColor('#A3BE8C'))
                    self.tabla_recambios.setItem(i, col, t_item)

            self.lbl_recambios_titulo.setVisible(True)
            self.tabla_recambios.setVisible(True)
            self.lbl_total_recambios.setText(f"{tr('Total Recambios')}: {total_recambios:.2f} €")
            self.lbl_total_recambios.setVisible(True)
        else:
            self.lbl_recambios_titulo.setVisible(False)
            self.tabla_recambios.setVisible(False)
            self.lbl_total_recambios.setVisible(False)

        self.lbl_total.setText(f"{tr('Total Estimado')}: {total:.2f} €")
        self.lbl_estado.setText(f"<b>{tr('Estado')}:</b> {reparacion.get('estado')}")
