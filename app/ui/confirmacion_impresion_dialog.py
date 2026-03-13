"""
Diálogo de confirmación con opción de impresión
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QRadioButton, QButtonGroup)
from PyQt5.QtCore import Qt
from app.i18n import tr
from app.ui.transparent_buttons import apply_btn_success, apply_btn_cancel


class ConfirmacionImpresionDialog(QDialog):
    def __init__(self, titulo="Confirmar", mensaje="¿Continuar?", parent=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setModal(True)
        self.setMinimumWidth(400)
        self.accion = None
        self.setup_ui(mensaje)

    def setup_ui(self, mensaje):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        # Mensaje
        lbl_mensaje = QLabel(mensaje)
        lbl_mensaje.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 15px;")
        layout.addWidget(lbl_mensaje)

        # Pregunta
        lbl_pregunta = QLabel(tr("¿Qué deseas hacer?"))
        lbl_pregunta.setStyleSheet("margin-top: 10px; margin-bottom: 10px;")
        layout.addWidget(lbl_pregunta)

        # Opciones de radio buttons
        self.btn_group = QButtonGroup()

        self.radio_guardar = QRadioButton(tr("Solo guardar (sin imprimir)"))
        self.radio_guardar.setStyleSheet("padding: 8px;")
        self.btn_group.addButton(self.radio_guardar, 1)
        layout.addWidget(self.radio_guardar)

        self.radio_imprimir = QRadioButton(tr("Guardar e imprimir factura"))
        self.radio_imprimir.setStyleSheet("padding: 8px;")
        self.radio_imprimir.setChecked(True)  # Por defecto
        self.btn_group.addButton(self.radio_imprimir, 2)
        layout.addWidget(self.radio_imprimir)

        self.radio_garantia = QRadioButton(tr("Guardar e imprimir garantía"))
        self.radio_garantia.setStyleSheet("padding: 8px;")
        self.btn_group.addButton(self.radio_garantia, 3)
        layout.addWidget(self.radio_garantia)

        # Botones
        botones_layout = QHBoxLayout()
        botones_layout.addStretch()

        btn_cancelar = QPushButton(tr("Cancelar"))
        btn_cancelar.clicked.connect(self.reject)
        apply_btn_cancel(btn_cancelar)
        botones_layout.addWidget(btn_cancelar)

        btn_aceptar = QPushButton(tr("Aceptar"))
        btn_aceptar.clicked.connect(self.aceptar)
        apply_btn_success(btn_aceptar)
        botones_layout.addWidget(btn_aceptar)

        layout.addLayout(botones_layout)

    def aceptar(self):
        if self.radio_imprimir.isChecked():
            self.accion = 'imprimir'
        elif self.radio_garantia.isChecked():
            self.accion = 'garantia'
        else:
            self.accion = 'guardar'
        self.accept()
