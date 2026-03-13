"""
Diálogo para añadir producto manual al TPV
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QFormLayout, QDoubleSpinBox, QSpinBox)
from PyQt5.QtCore import Qt
from app.utils.notify import notify_warning
from app.ui.transparent_buttons import apply_btn_success, apply_btn_cancel
from app.i18n import tr


class TPVProductoManualDialog(QDialog):
    def __init__(self, cantidad_inicial=1, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Añadir Producto Manual"))
        self.setModal(True)
        self.setMinimumWidth(400)
        self.datos = None
        self.setup_ui()

        # Establecer cantidad inicial
        self.cantidad_spin.setValue(cantidad_inicial)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Formulario
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.nombre_input = QLineEdit()
        self.nombre_input.setPlaceholderText(tr("Nombre del producto"))
        self.nombre_input.setFont(self.font())
        form_layout.addRow(tr("Nombre:"), self.nombre_input)

        self.precio_input = QDoubleSpinBox()
        self.precio_input.setMinimum(0)
        self.precio_input.setMaximum(999999.99)
        self.precio_input.setDecimals(2)
        self.precio_input.setSuffix(" €")
        self.precio_input.setValue(0.00)
        form_layout.addRow(tr("Precio:"), self.precio_input)

        self.cantidad_spin = QSpinBox()
        self.cantidad_spin.setMinimum(1)
        self.cantidad_spin.setMaximum(9999)
        self.cantidad_spin.setValue(1)
        form_layout.addRow(tr("Cantidad:"), self.cantidad_spin)

        layout.addLayout(form_layout)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancelar = QPushButton(tr("Cancelar"))
        btn_cancelar.clicked.connect(self.reject)
        apply_btn_cancel(btn_cancelar)

        btn_guardar = QPushButton(tr("Añadir"))
        btn_guardar.clicked.connect(self.aceptar)
        apply_btn_success(btn_guardar)

        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_guardar)

        layout.addLayout(btn_layout)

        # Enfocar en nombre
        self.nombre_input.setFocus()

    def aceptar(self):
        """Valida y acepta el diálogo"""
        nombre = self.nombre_input.text().strip()
        precio = self.precio_input.value()
        cantidad = self.cantidad_spin.value()

        if not nombre:
            notify_warning(self, tr("Campo requerido"), tr("Por favor, introduce un nombre para el producto"))
            self.nombre_input.setFocus()
            return

        if precio <= 0:
            notify_warning(self, tr("Precio inválido"), tr("El precio debe ser mayor que 0"))
            self.precio_input.setFocus()
            return

        self.datos = {
            'nombre': nombre,
            'precio': precio,
            'cantidad': cantidad
        }

        self.accept()

    def get_datos(self):
        """Retorna los datos del producto"""
        return self.datos
