"""
Diálogo para ver detalles completos de un cliente
"""
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QGroupBox, QGridLayout, QScrollArea,
                             QWidget)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QFont
from app.ui.transparent_buttons import apply_btn_primary, apply_btn_cancel


class ClienteDetalleDialog(QDialog):
    def __init__(self, db, cliente, parent=None):
        super().__init__(parent)
        self.db = db
        self.cliente = cliente
        self.setWindowTitle(f"Detalles del Cliente - {cliente['nombre']}")
        self.setModal(True)
        self.setMinimumSize(550, 500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Scroll area para contenido largo
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # === CABECERA ===
        header = QLabel(f"👤 {self.cliente['nombre']}")
        header.setFont(QFont('Arial', 18, QFont.Bold))
        header.setStyleSheet("color: #2E3440; padding: 10px;")
        header.setAlignment(Qt.AlignCenter)
        scroll_layout.addWidget(header)
        
        # === DATOS PERSONALES ===
        datos_group = QGroupBox("📋 Datos Personales")
        datos_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #5E81AC;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
            }
        """)
        datos_layout = QGridLayout()
        datos_layout.setSpacing(10)
        
        # Estilo para las etiquetas
        label_style = "font-weight: bold; color: #7B88A0;"
        value_style = "color: #2E3440; font-size: 13px; padding: 5px; background-color: #3B4252; border-radius: 4px;"
        
        row = 0
        campos = [
            ("ID:", str(self.cliente['id'])),
            ("NIF/CIF:", self.cliente.get('nif') or 'No registrado'),
            ("Dirección:", self.cliente.get('direccion') or 'No registrada'),
            ("C.P.:", self.cliente.get('codigo_postal') or '—'),
            ("Ciudad:", self.cliente.get('ciudad') or '—'),
            ("Teléfono:", self.cliente.get('telefono') or 'No registrado'),
            ("Email:", self.cliente.get('email') or 'No registrado'),
        ]
        
        for label_text, value_text in campos:
            label = QLabel(label_text)
            label.setStyleSheet(label_style)
            value = QLabel(value_text)
            value.setStyleSheet(value_style)
            value.setWordWrap(True)
            datos_layout.addWidget(label, row, 0)
            datos_layout.addWidget(value, row, 1)
            row += 1
        
        # Fecha de registro si existe
        if self.cliente.get('fecha_registro'):
            label = QLabel("Registrado:")
            label.setStyleSheet(label_style)
            value = QLabel(str(self.cliente['fecha_registro'])[:10])
            value.setStyleSheet(value_style)
            datos_layout.addWidget(label, row, 0)
            datos_layout.addWidget(value, row, 1)
        
        datos_group.setLayout(datos_layout)
        scroll_layout.addWidget(datos_group)
        
        # === FOTO DEL DNI ===
        dni_group = QGroupBox("🪪 Documento de Identidad")
        dni_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #B48EAD;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
            }
        """)
        dni_layout = QVBoxLayout()
        
        dni_imagen = self.cliente.get('dni_imagen')
        
        if dni_imagen and os.path.exists(dni_imagen):
            # Mostrar imagen del DNI
            dni_label = QLabel()
            pixmap = QPixmap(dni_imagen)
            # Escalar manteniendo proporción
            scaled = pixmap.scaled(450, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            dni_label.setPixmap(scaled)
            dni_label.setAlignment(Qt.AlignCenter)
            dni_label.setStyleSheet("""
                border: 2px solid #A3BE8C;
                border-radius: 8px;
                padding: 10px;
                background-color: white;
            """)
            dni_layout.addWidget(dni_label)
            
            # Info de la imagen
            info_label = QLabel(f"📁 {os.path.basename(dni_imagen)}")
            info_label.setStyleSheet("color: #7B88A0; font-size: 11px;")
            info_label.setAlignment(Qt.AlignCenter)
            dni_layout.addWidget(info_label)
        else:
            # Sin imagen
            no_dni_label = QLabel("❌ Sin imagen de DNI registrada")
            no_dni_label.setAlignment(Qt.AlignCenter)
            no_dni_label.setStyleSheet("""
                color: #BF616A;
                font-size: 14px;
                padding: 30px;
                background-color: rgba(191, 97, 106, 0.15);
                border-radius: 8px;
            """)
            dni_layout.addWidget(no_dni_label)
        
        dni_group.setLayout(dni_layout)
        scroll_layout.addWidget(dni_group)
        
        # === ESTADÍSTICAS ===
        stats_group = QGroupBox("📊 Historial")
        stats_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #A3BE8C;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
            }
        """)
        stats_layout = QHBoxLayout()
        
        # Contar compras
        compras = self.db.fetch_one(
            "SELECT COUNT(*) as total, COALESCE(SUM(total), 0) as importe FROM compras WHERE proveedor_nombre = ?",
            (self.cliente['nombre'],)
        )
        
        # Contar ventas
        ventas = self.db.fetch_one(
            "SELECT COUNT(*) as total, COALESCE(SUM(total), 0) as importe FROM facturas WHERE cliente_id = ?",
            (self.cliente['id'],)
        )
        
        # Contar reparaciones
        reparaciones = self.db.fetch_one(
            "SELECT COUNT(*) as total FROM reparaciones WHERE cliente_id = ? OR cliente_nombre = ?",
            (self.cliente['id'], self.cliente['nombre'])
        )
        
        # Widgets de estadísticas
        for titulo, cantidad, importe, color in [
            ("Compras", compras['total'] if compras else 0, compras['importe'] if compras else 0, "#BF616A"),
            ("Ventas", ventas['total'] if ventas else 0, ventas['importe'] if ventas else 0, "#A3BE8C"),
            ("Reparaciones", reparaciones['total'] if reparaciones else 0, None, "#B48EAD"),
        ]:
            stat_widget = QWidget()
            stat_layout = QVBoxLayout(stat_widget)
            stat_layout.setAlignment(Qt.AlignCenter)
            
            num_label = QLabel(str(cantidad))
            num_label.setFont(QFont('Arial', 24, QFont.Bold))
            num_label.setStyleSheet(f"color: {color};")
            num_label.setAlignment(Qt.AlignCenter)
            
            title_label = QLabel(titulo)
            title_label.setStyleSheet("color: #7B88A0; font-size: 12px;")
            title_label.setAlignment(Qt.AlignCenter)
            
            stat_layout.addWidget(num_label)
            stat_layout.addWidget(title_label)
            
            if importe is not None and importe > 0:
                importe_label = QLabel(f"{importe:.2f} €")
                importe_label.setStyleSheet("color: #4C566A; font-size: 11px;")
                importe_label.setAlignment(Qt.AlignCenter)
                stat_layout.addWidget(importe_label)
            
            stats_layout.addWidget(stat_widget)
        
        stats_group.setLayout(stats_layout)
        scroll_layout.addWidget(stats_group)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        # === BOTONES ===
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_editar = QPushButton("✏️ Editar Cliente")
        btn_editar.clicked.connect(self.editar_cliente)
        apply_btn_primary(btn_editar)
        btn_layout.addWidget(btn_editar)
        
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        apply_btn_cancel(btn_cerrar)
        btn_layout.addWidget(btn_cerrar)
        
        layout.addLayout(btn_layout)
    
    def editar_cliente(self):
        """Abre el diálogo de edición"""
        from app.ui.cliente_dialog import ClienteDialog
        dialog = ClienteDialog(self.db, cliente=self.cliente, parent=self)
        if dialog.exec_():
            # Recargar datos del cliente
            cliente_actualizado = self.db.fetch_one(
                "SELECT * FROM clientes WHERE id = ?", 
                (self.cliente['id'],)
            )
            if cliente_actualizado:
                self.cliente = cliente_actualizado
                # Cerrar y reabrir para actualizar vista
                self.accept()












