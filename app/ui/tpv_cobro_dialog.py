"""
Diálogo para procesar el cobro en el TPV
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QFormLayout, QDoubleSpinBox,
                             QComboBox, QCheckBox, QGroupBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from app.utils.notify import notify_warning
from app.i18n import tr
from app.ui.transparent_buttons import apply_btn_cancel, apply_btn_warning


class TPVCobroDialog(QDialog):
    def __init__(self, total, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Procesar Cobro"))
        self.setModal(True)
        self.setMinimumWidth(450)
        self.total = total
        self.datos = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        # Total a cobrar
        total_frame = QGroupBox(tr("Total a Cobrar"))
        total_frame.setObjectName("cardGroup")
        total_layout = QVBoxLayout(total_frame)
        
        self.total_label = QLabel(f"{self.total:.2f} €")
        self.total_label.setAlignment(Qt.AlignCenter)
        self.total_label.setFont(QFont("", 28, QFont.Bold))
        self.total_label.setStyleSheet("color: #A3BE8C; padding: 20px;")
        total_layout.addWidget(self.total_label)
        
        layout.addWidget(total_frame)

        # Método de pago
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.metodo_pago_combo = QComboBox()
        self.metodo_pago_combo.addItems([tr("efectivo"), tr("tarjeta"), tr("transferencia")])
        self.metodo_pago_combo.setCurrentText(tr("efectivo"))
        self.metodo_pago_combo.currentTextChanged.connect(self.on_metodo_pago_changed)
        form_layout.addRow(tr("Método de Pago") + ":", self.metodo_pago_combo)

        # Efectivo recibido (solo para efectivo)
        self.efectivo_recibido_label = QLabel(tr("Efectivo Recibido") + ":")
        self.efectivo_recibido_input = QDoubleSpinBox()
        # El mínimo es el total a pagar (no se puede pagar menos)
        self.efectivo_recibido_input.setMinimum(self.total)
        self.efectivo_recibido_input.setMaximum(999999.99)
        self.efectivo_recibido_input.setDecimals(2)
        self.efectivo_recibido_input.setSuffix(" €")
        self.efectivo_recibido_input.setValue(self.total)
        self.efectivo_recibido_input.setSingleStep(0.05)  # Incrementos de 5 céntimos
        self.efectivo_recibido_input.valueChanged.connect(self.calcular_cambio)
        
        form_layout.addRow(self.efectivo_recibido_label, self.efectivo_recibido_input)

        # Cambio
        self.cambio_label = QLabel(tr("Cambio") + ":")
        self.cambio_display = QLabel("0.00 €")
        self.cambio_display.setAlignment(Qt.AlignRight)
        self.cambio_display.setFont(QFont("", 14, QFont.Bold))
        self.cambio_display.setStyleSheet("color: #D08770; padding: 5px;")
        form_layout.addRow(self.cambio_label, self.cambio_display)

        layout.addLayout(form_layout)

        # Opciones
        opciones_frame = QGroupBox(tr("Opciones"))
        opciones_frame.setObjectName("cardGroup")
        opciones_layout = QVBoxLayout(opciones_frame)

        self.imprimir_check = QCheckBox(tr("Imprimir ticket"))
        self.imprimir_check.setChecked(True)
        opciones_layout.addWidget(self.imprimir_check)

        layout.addWidget(opciones_frame)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancelar = QPushButton(tr("Cancelar"))
        btn_cancelar.clicked.connect(self.reject)
        apply_btn_cancel(btn_cancelar)

        btn_cobrar = QPushButton(tr("Cobrar"))
        btn_cobrar.clicked.connect(self.aceptar)
        apply_btn_warning(btn_cobrar)

        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_cobrar)

        layout.addLayout(btn_layout)

        # Inicializar visibilidad
        self.on_metodo_pago_changed(tr("efectivo"))
        self.calcular_cambio()

        # Enfocar en efectivo recibido
        self.efectivo_recibido_input.setFocus()
        self.efectivo_recibido_input.selectAll()

    def on_metodo_pago_changed(self, metodo):
        """Muestra/oculta campos según el método de pago"""
        es_efectivo = metodo == tr("efectivo")
        self.efectivo_recibido_label.setVisible(es_efectivo)
        self.efectivo_recibido_input.setVisible(es_efectivo)
        self.cambio_label.setVisible(es_efectivo)
        self.cambio_display.setVisible(es_efectivo)

    def calcular_cambio(self):
        """Calcula el cambio a devolver"""
        if self.metodo_pago_combo.currentText() == tr("efectivo"):
            recibido = self.efectivo_recibido_input.value()
            cambio = recibido - self.total
            if cambio < 0:
                self.cambio_display.setText(f"{cambio:.2f} €")
                self.cambio_display.setStyleSheet("color: #BF616A; padding: 5px;")
            else:
                self.cambio_display.setText(f"{cambio:.2f} €")
                self.cambio_display.setStyleSheet("color: #A3BE8C; padding: 5px;")

    def aceptar(self):
        """Valida y acepta el diálogo"""
        metodo_pago = self.metodo_pago_combo.currentText()
        
        # Validar efectivo recibido
        if metodo_pago == tr("efectivo"):
            recibido = self.efectivo_recibido_input.value()
            if recibido < self.total:
                notify_warning(
                    self,
                    tr("Efectivo insuficiente"),
                    f"{tr('El efectivo recibido')} ({recibido:.2f} €) {tr('es menor que el total')} ({self.total:.2f} €)"
                )
                self.efectivo_recibido_input.setFocus()
                return

        self.datos = {
            'metodo_pago': metodo_pago,
            'imprimir': self.imprimir_check.isChecked(),
            'cantidad_recibida': self.efectivo_recibido_input.value() if metodo_pago == tr("efectivo") else None,
            'cambio_devuelto': (self.efectivo_recibido_input.value() - self.total) if metodo_pago == tr("efectivo") else None
        }

        self.accept()

    def get_datos(self):
        """Retorna los datos del cobro"""
        return self.datos






