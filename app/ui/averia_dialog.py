"""
Diálogo para crear/editar averías del sistema SAT
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QFormLayout, QTextEdit)
from PyQt5.QtCore import Qt
from app.utils.notify import notify_success, notify_error, notify_warning
from app.ui.transparent_buttons import apply_btn_success, apply_btn_cancel
from app.i18n import tr


class AveriaDialog(QDialog):
    def __init__(self, db, averia=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.averia = averia
        self.setWindowTitle(tr("Nueva Avería") if not averia else tr("Editar Avería"))
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setup_ui()

        if averia:
            self.cargar_datos()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Formulario
        form_layout = QFormLayout()

        # Campo nombre
        self.nombre_input = QLineEdit()
        self.nombre_input.setPlaceholderText(tr("Ej: Pantalla rota, No enciende, etc."))
        form_layout.addRow(tr("Nombre *:"), self.nombre_input)

        # Campo descripción
        self.descripcion_input = QTextEdit()
        self.descripcion_input.setPlaceholderText(tr("Descripción opcional de la avería"))
        self.descripcion_input.setMaximumHeight(100)
        form_layout.addRow(tr("Descripción:"), self.descripcion_input)

        layout.addLayout(form_layout)

        # Nota informativa
        nota = QLabel(tr("* Campos obligatorios"))
        nota.setStyleSheet("color: #7B88A0; font-size: 10pt; font-style: italic;")
        layout.addWidget(nota)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancelar = QPushButton(tr("Cancelar"))
        btn_cancelar.clicked.connect(self.reject)
        apply_btn_cancel(btn_cancelar)
        btn_cancelar.setMinimumHeight(35)

        btn_guardar = QPushButton(tr("Guardar"))
        btn_guardar.clicked.connect(self.guardar)
        apply_btn_success(btn_guardar)
        btn_guardar.setMinimumHeight(35)

        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_guardar)

        layout.addLayout(btn_layout)

    def cargar_datos(self):
        """Carga los datos de la avería en el formulario"""
        self.nombre_input.setText(self.averia['nombre'])
        self.descripcion_input.setPlainText(self.averia.get('descripcion') or '')

    def guardar(self):
        """Guarda la avería"""
        nombre = self.nombre_input.text().strip()

        if not nombre:
            notify_warning(self, tr("Error"), tr("El nombre de la avería es obligatorio"))
            self.nombre_input.setFocus()
            return

        descripcion = self.descripcion_input.toPlainText().strip()

        try:
            from app.modules.averia_manager import AveriaManager
            averia_mgr = AveriaManager(self.db)

            if self.averia:
                # Actualizar avería existente
                if averia_mgr.actualizar_averia(self.averia['id'], nombre, descripcion):
                    notify_success(self, tr("Éxito"), tr("Avería actualizada correctamente"))
                    self.accept()
                else:
                    notify_error(self, tr("Error"), tr("No se pudo actualizar la avería"))
            else:
                # Crear nueva avería
                averia_id = averia_mgr.crear_averia(nombre, descripcion)
                if averia_id:
                    notify_success(self, tr("Éxito"), tr("Avería creada correctamente"))
                    self.accept()
                else:
                    notify_error(self, tr("Error"), tr("No se pudo crear la avería"))

        except (OSError, ValueError, RuntimeError) as e:
            notify_error(self, tr("Error"), tr("Error al guardar la avería:\n{error}", error=str(e)))
