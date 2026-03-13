"""
Diálogo para crear/editar establecimientos
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QFormLayout, QFileDialog, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from app.utils.notify import notify_success, notify_error, notify_warning
from app.ui.transparent_buttons import apply_btn_primary, apply_btn_danger, apply_btn_success, apply_btn_cancel
from app.i18n import tr
import os
import shutil
from app.utils.logger import logger


class EstablecimientoDialog(QDialog):
    def __init__(self, db, establecimiento=None, parent=None, es_inicial=False):
        """
        Args:
            db: Conexión a la base de datos
            establecimiento: Datos del establecimiento a editar (None para nuevo)
            parent: Widget padre
            es_inicial: True si es la configuración inicial (primer establecimiento)
        """
        super().__init__(parent)
        self.db = db
        self.establecimiento = establecimiento
        self.es_inicial = es_inicial
        self.establecimiento_id = None
        self.logo_path = None  # Ruta del logo seleccionado

        if es_inicial:
            self.setWindowTitle(tr("Configurar Establecimiento"))
        else:
            self.setWindowTitle(tr("Nuevo Establecimiento") if not establecimiento else tr("Editar Establecimiento"))

        self.setModal(True)
        self.setMinimumWidth(550)
        self.setup_ui()

        if establecimiento:
            self.cargar_datos()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 25, 30, 25)

        # Header para configuración inicial
        if self.es_inicial:
            icon = QLabel("🏪")
            icon.setStyleSheet("font-size: 40px;")
            icon.setAlignment(Qt.AlignCenter)
            layout.addWidget(icon)

            title = QLabel(tr("Configura tu Establecimiento"))
            title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)

            subtitle = QLabel(tr("Estos datos aparecerán en facturas, tickets y documentos."))
            subtitle.setStyleSheet("font-size: 11px; color: #7B88A0;")
            subtitle.setAlignment(Qt.AlignCenter)
            subtitle.setWordWrap(True)
            layout.addWidget(subtitle)

            layout.addSpacing(10)

        # Formulario
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # Nombre (obligatorio)
        self.nombre_input = QLineEdit()
        self.nombre_input.setPlaceholderText(tr("Ej: Mi Tienda de Móviles"))
        self.nombre_input.setMinimumHeight(38)
        form_layout.addRow(tr("Nombre *:"), self.nombre_input)

        # NIF/CIF
        self.nif_input = QLineEdit()
        self.nif_input.setPlaceholderText(tr("Ej: B12345678"))
        self.nif_input.setMinimumHeight(38)
        form_layout.addRow(tr("NIF/CIF:"), self.nif_input)

        # Dirección
        self.direccion_input = QLineEdit()
        self.direccion_input.setPlaceholderText(tr("Ej: Calle Mayor 123"))
        self.direccion_input.setMinimumHeight(38)
        form_layout.addRow(tr("Dirección:"), self.direccion_input)

        # CP y Ciudad en una misma fila
        cp_ciudad_layout = QHBoxLayout()
        self.cp_input = QLineEdit()
        self.cp_input.setPlaceholderText(tr("Ej: 28001"))
        self.cp_input.setMinimumHeight(38)
        self.cp_input.setMaximumWidth(120)
        self.ciudad_input = QLineEdit()
        self.ciudad_input.setPlaceholderText(tr("Ej: Madrid"))
        self.ciudad_input.setMinimumHeight(38)
        cp_ciudad_layout.addWidget(self.cp_input)
        cp_ciudad_layout.addWidget(self.ciudad_input)
        form_layout.addRow(tr("C.P. / Ciudad:"), cp_ciudad_layout)

        # Provincia
        self.provincia_input = QLineEdit()
        self.provincia_input.setPlaceholderText(tr("Ej: Madrid"))
        self.provincia_input.setMinimumHeight(38)
        form_layout.addRow(tr("Provincia:"), self.provincia_input)

        # Teléfono
        self.telefono_input = QLineEdit()
        self.telefono_input.setPlaceholderText(tr("Ej: 912345678"))
        self.telefono_input.setMinimumHeight(38)
        form_layout.addRow(tr("Teléfono:"), self.telefono_input)

        # Email
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText(tr("Ej: info@mitienda.com"))
        self.email_input.setMinimumHeight(38)
        form_layout.addRow(tr("Email:"), self.email_input)

        layout.addLayout(form_layout)

        # Sección de Logo
        logo_group = QFrame()
        logo_group.setStyleSheet("""
            QFrame {
                background-color: #3B4252;
                border: 1px solid #4C566A;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        logo_layout = QVBoxLayout(logo_group)

        logo_header = QLabel(tr("Logo del Establecimiento"))
        logo_header.setStyleSheet("font-weight: bold; color: #ECEFF4; border: none;")
        logo_layout.addWidget(logo_header)

        logo_content = QHBoxLayout()

        # Preview del logo
        self.logo_preview = QLabel()
        self.logo_preview.setFixedSize(100, 100)
        self.logo_preview.setStyleSheet("""
            background-color: #2E3440;
            border: 2px dashed #4C566A;
            border-radius: 5px;
            color: #7B88A0;
        """)
        self.logo_preview.setAlignment(Qt.AlignCenter)
        self.logo_preview.setText(tr("Sin logo"))
        logo_content.addWidget(self.logo_preview)

        # Botones de logo
        logo_buttons = QVBoxLayout()

        btn_seleccionar = QPushButton("📁 " + tr("Seleccionar Logo"))
        btn_seleccionar.clicked.connect(self.seleccionar_logo)
        apply_btn_primary(btn_seleccionar)
        logo_buttons.addWidget(btn_seleccionar)

        btn_quitar = QPushButton("🗑️ " + tr("Quitar Logo"))
        btn_quitar.clicked.connect(self.quitar_logo)
        apply_btn_danger(btn_quitar)
        logo_buttons.addWidget(btn_quitar)

        logo_buttons.addStretch()
        logo_content.addLayout(logo_buttons)
        logo_content.addStretch()

        logo_layout.addLayout(logo_content)

        info_logo = QLabel(tr("Formatos: PNG, JPG. Tamaño recomendado: 200x200px"))
        info_logo.setStyleSheet("font-size: 10px; color: #7B88A0; border: none;")
        logo_layout.addWidget(info_logo)

        layout.addWidget(logo_group)

        # Info
        if self.es_inicial:
            info = QLabel(
                "💡 " + tr("Podrás modificar estos datos más tarde desde Ajustes > Establecimientos.")
            )
            info.setStyleSheet("""
                background-color: rgba(163, 190, 140, 0.12);
                padding: 12px;
                border-radius: 5px;
                font-size: 11px;
                color: #A3BE8C;
                border: 1px solid #A3BE8C;
            """)
            info.setWordWrap(True)
            layout.addWidget(info)

        layout.addSpacing(15)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        if not self.es_inicial:
            btn_cancelar = QPushButton(tr("Cancelar"))
            btn_cancelar.clicked.connect(self.reject)
            apply_btn_cancel(btn_cancelar)
            btn_layout.addWidget(btn_cancelar)

        btn_text = tr("Guardar y Continuar") if self.es_inicial else tr("Guardar")
        btn_guardar = QPushButton(btn_text)
        btn_guardar.clicked.connect(self.guardar)
        apply_btn_success(btn_guardar)
        btn_layout.addWidget(btn_guardar)

        layout.addLayout(btn_layout)

    def seleccionar_logo(self):
        """Abre diálogo para seleccionar logo"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Seleccionar Logo"),
            "",
            tr("Imágenes") + " (*.png *.jpg *.jpeg *.bmp)"
        )

        if file_path:
            self.logo_path = file_path
            self.mostrar_preview_logo(file_path)

    def quitar_logo(self):
        """Quita el logo seleccionado"""
        self.logo_path = ""  # String vacío indica quitar logo
        self.logo_preview.setPixmap(QPixmap())
        self.logo_preview.setText(tr("Sin logo"))
        self.logo_preview.setStyleSheet("""
            background-color: #2E3440;
            border: 2px dashed #4C566A;
            border-radius: 5px;
            color: #7B88A0;
        """)

    def mostrar_preview_logo(self, path):
        """Muestra preview del logo"""
        if path and os.path.exists(path):
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.logo_preview.setPixmap(scaled)
                self.logo_preview.setText("")
                self.logo_preview.setStyleSheet("""
                    background-color: white;
                    border: 2px solid #A3BE8C;
                    border-radius: 5px;
                """)

    def cargar_datos(self):
        """Carga los datos del establecimiento en el formulario"""
        self.nombre_input.setText(self.establecimiento.get('nombre', ''))
        self.nif_input.setText(self.establecimiento.get('nif', '') or '')
        self.direccion_input.setText(self.establecimiento.get('direccion', '') or '')
        self.cp_input.setText(self.establecimiento.get('cp', '') or '')
        self.ciudad_input.setText(self.establecimiento.get('ciudad', '') or '')
        self.provincia_input.setText(self.establecimiento.get('provincia', '') or '')
        self.telefono_input.setText(self.establecimiento.get('telefono', '') or '')
        self.email_input.setText(self.establecimiento.get('email', '') or '')

        # Cargar logo si existe
        logo = self.establecimiento.get('logo_path')
        if logo:
            self.logo_path = logo
            self.mostrar_preview_logo(logo)

    def _copiar_logo(self, origen):
        """Copia el logo al directorio de datos y retorna la nueva ruta"""
        if not origen or not os.path.exists(origen):
            return None

        # Crear directorio de logos si no existe
        from config import LOGOS_DIR
        os.makedirs(LOGOS_DIR, exist_ok=True)

        # Nombre único para el logo
        ext = os.path.splitext(origen)[1]
        nombre_archivo = f"establecimiento_{self.establecimiento_id or 'new'}{ext}"
        destino = os.path.join(LOGOS_DIR, nombre_archivo)

        try:
            shutil.copy2(origen, destino)
            return destino
        except (OSError, ValueError, RuntimeError) as e:
            logger.error(f"Error copiando logo: {e}")
            return origen

    def guardar(self):
        """Guarda el establecimiento"""
        nombre = self.nombre_input.text().strip()

        if not nombre:
            notify_warning(self, tr("Error"), tr("El nombre del establecimiento es obligatorio"))
            return

        datos = {
            'nombre': nombre,
            'nif': self.nif_input.text().strip() or None,
            'direccion': self.direccion_input.text().strip() or None,
            'cp': self.cp_input.text().strip() or None,
            'ciudad': self.ciudad_input.text().strip() or None,
            'provincia': self.provincia_input.text().strip() or None,
            'telefono': self.telefono_input.text().strip() or None,
            'email': self.email_input.text().strip() or None
        }

        try:
            if self.establecimiento:
                # Actualizar existente
                self.establecimiento_id = self.establecimiento['id']

                # Procesar logo
                logo_final = self.establecimiento.get('logo_path')  # Mantener actual
                if self.logo_path == "":
                    logo_final = None  # Quitar logo
                elif self.logo_path and self.logo_path != logo_final:
                    logo_final = self._copiar_logo(self.logo_path)

                query = """
                    UPDATE establecimientos
                    SET nombre = ?, nif = ?, direccion = ?, cp = ?, ciudad = ?, provincia = ?, telefono = ?, email = ?, logo_path = ?
                    WHERE id = ?
                """
                self.db.execute_query(query, (
                    datos['nombre'], datos['nif'], datos['direccion'],
                    datos['cp'], datos['ciudad'], datos['provincia'],
                    datos['telefono'], datos['email'], logo_final,
                    self.establecimiento['id']
                ))
            else:
                # Crear nuevo
                query = """
                    INSERT INTO establecimientos (nombre, nif, direccion, cp, ciudad, provincia, telefono, email)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                self.establecimiento_id = self.db.execute_query(query, (
                    datos['nombre'], datos['nif'], datos['direccion'],
                    datos['cp'], datos['ciudad'], datos['provincia'],
                    datos['telefono'], datos['email']
                ))

                # Copiar logo si se seleccionó
                if self.logo_path and self.establecimiento_id:
                    logo_final = self._copiar_logo(self.logo_path)
                    if logo_final:
                        self.db.execute_query(
                            "UPDATE establecimientos SET logo_path = ? WHERE id = ?",
                            (logo_final, self.establecimiento_id)
                        )

            if self.establecimiento_id:
                if not self.es_inicial:
                    notify_success(self, tr("Éxito"), tr("Establecimiento guardado correctamente"))
                self.accept()
            else:
                notify_error(self, tr("Error"), tr("No se pudo guardar el establecimiento"))

        except (OSError, ValueError, RuntimeError) as e:
            notify_error(self, tr("Error"), tr("Error al guardar: {error}", error=str(e)))

    def obtener_establecimiento_id(self):
        """Retorna el ID del establecimiento creado/editado"""
        return self.establecimiento_id
