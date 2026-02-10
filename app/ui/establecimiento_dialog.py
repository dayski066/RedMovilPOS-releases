"""
Diálogo para crear/editar establecimientos
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QMessageBox, QFormLayout, QFileDialog, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
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
            self.setWindowTitle("Configurar Establecimiento")
        else:
            self.setWindowTitle("Nuevo Establecimiento" if not establecimiento else "Editar Establecimiento")

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

            title = QLabel("Configura tu Establecimiento")
            title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)

            subtitle = QLabel("Estos datos aparecerán en facturas, tickets y documentos.")
            subtitle.setStyleSheet("font-size: 11px; color: #7f8c8d;")
            subtitle.setAlignment(Qt.AlignCenter)
            subtitle.setWordWrap(True)
            layout.addWidget(subtitle)

            layout.addSpacing(10)

        # Formulario
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # Nombre (obligatorio)
        self.nombre_input = QLineEdit()
        self.nombre_input.setPlaceholderText("Ej: Mi Tienda de Móviles")
        self.nombre_input.setMinimumHeight(38)
        form_layout.addRow("Nombre *:", self.nombre_input)

        # NIF/CIF
        self.nif_input = QLineEdit()
        self.nif_input.setPlaceholderText("Ej: B12345678")
        self.nif_input.setMinimumHeight(38)
        form_layout.addRow("NIF/CIF:", self.nif_input)

        # Dirección
        self.direccion_input = QLineEdit()
        self.direccion_input.setPlaceholderText("Ej: Calle Mayor 123, Madrid")
        self.direccion_input.setMinimumHeight(38)
        form_layout.addRow("Dirección:", self.direccion_input)

        # Teléfono
        self.telefono_input = QLineEdit()
        self.telefono_input.setPlaceholderText("Ej: 912345678")
        self.telefono_input.setMinimumHeight(38)
        form_layout.addRow("Teléfono:", self.telefono_input)

        # Email
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Ej: info@mitienda.com")
        self.email_input.setMinimumHeight(38)
        form_layout.addRow("Email:", self.email_input)

        layout.addLayout(form_layout)

        # Sección de Logo
        logo_group = QFrame()
        logo_group.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        logo_layout = QVBoxLayout(logo_group)

        logo_header = QLabel("Logo del Establecimiento")
        logo_header.setStyleSheet("font-weight: bold; color: #2c3e50; border: none;")
        logo_layout.addWidget(logo_header)

        logo_content = QHBoxLayout()

        # Preview del logo
        self.logo_preview = QLabel()
        self.logo_preview.setFixedSize(100, 100)
        self.logo_preview.setStyleSheet("""
            background-color: #2d2d30;
            border: 2px dashed #3e3e42;
            border-radius: 5px;
            color: #969696;
        """)
        self.logo_preview.setAlignment(Qt.AlignCenter)
        self.logo_preview.setText("Sin logo")
        logo_content.addWidget(self.logo_preview)

        # Botones de logo
        logo_buttons = QVBoxLayout()

        btn_seleccionar = QPushButton("📁 Seleccionar Logo")
        btn_seleccionar.clicked.connect(self.seleccionar_logo)
        btn_seleccionar.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #5E81AC; border: 2px solid #5E81AC;
                padding: 8px 15px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: transparent; color: #5E81AC; border: 2px solid #5E81AC; }
        """)
        logo_buttons.addWidget(btn_seleccionar)

        btn_quitar = QPushButton("🗑️ Quitar Logo")
        btn_quitar.clicked.connect(self.quitar_logo)
        btn_quitar.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #BF616A; border: 2px solid #BF616A;
                padding: 8px 15px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: transparent; color: #BF616A; border: 2px solid #BF616A; }
        """)
        logo_buttons.addWidget(btn_quitar)

        logo_buttons.addStretch()
        logo_content.addLayout(logo_buttons)
        logo_content.addStretch()

        logo_layout.addLayout(logo_content)

        info_logo = QLabel("Formatos: PNG, JPG. Tamaño recomendado: 200x200px")
        info_logo.setStyleSheet("font-size: 10px; color: #7f8c8d; border: none;")
        logo_layout.addWidget(info_logo)

        layout.addWidget(logo_group)

        # Info
        if self.es_inicial:
            info = QLabel(
                "💡 Podrás modificar estos datos más tarde desde Ajustes > Establecimientos."
            )
            info.setStyleSheet("""
                background-color: #e8f5e9;
                padding: 12px;
                border-radius: 5px;
                font-size: 11px;
                color: #2e7d32;
            """)
            info.setWordWrap(True)
            layout.addWidget(info)

        layout.addSpacing(15)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        if not self.es_inicial:
            btn_cancelar = QPushButton("Cancelar")
            btn_cancelar.clicked.connect(self.reject)
            btn_cancelar.setStyleSheet("background-color: transparent; color: #5E6B7D; border: 2px solid #5E6B7D; border-radius: 6px; padding: 10px 20px;")
            btn_layout.addWidget(btn_cancelar)

        btn_text = "Guardar y Continuar" if self.es_inicial else "Guardar"
        btn_guardar = QPushButton(btn_text)
        btn_guardar.clicked.connect(self.guardar)
        btn_guardar.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #A3BE8C; border: 2px solid #A3BE8C;
                font-weight: bold;
                padding: 12px 25px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: transparent; color: #A3BE8C; border: 2px solid #A3BE8C; }
        """)
        btn_layout.addWidget(btn_guardar)

        layout.addLayout(btn_layout)

        # Estilos - DARK MODE
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; }
            QLabel { color: #cccccc; }
            QLineEdit {
                padding: 8px 12px;
                border: 2px solid #3e3e42;
                border-radius: 5px;
                background-color: #3c3c3c;
                color: #ffffff;
            }
            QLineEdit:focus { border: 2px solid #007acc; }
        """)

    def seleccionar_logo(self):
        """Abre diálogo para seleccionar logo"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Logo",
            "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp)"
        )

        if file_path:
            self.logo_path = file_path
            self.mostrar_preview_logo(file_path)

    def quitar_logo(self):
        """Quita el logo seleccionado"""
        self.logo_path = ""  # String vacío indica quitar logo
        self.logo_preview.setPixmap(QPixmap())
        self.logo_preview.setText("Sin logo")
        self.logo_preview.setStyleSheet("""
            background-color: #2d2d30;
            border: 2px dashed #3e3e42;
            border-radius: 5px;
            color: #969696;
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
                    border: 2px solid #27ae60;
                    border-radius: 5px;
                """)

    def cargar_datos(self):
        """Carga los datos del establecimiento en el formulario"""
        self.nombre_input.setText(self.establecimiento.get('nombre', ''))
        self.nif_input.setText(self.establecimiento.get('nif', '') or '')
        self.direccion_input.setText(self.establecimiento.get('direccion', '') or '')
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
            QMessageBox.warning(self, "Error", "El nombre del establecimiento es obligatorio")
            return

        datos = {
            'nombre': nombre,
            'nif': self.nif_input.text().strip() or None,
            'direccion': self.direccion_input.text().strip() or None,
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
                    SET nombre = ?, nif = ?, direccion = ?, telefono = ?, email = ?, logo_path = ?
                    WHERE id = ?
                """
                self.db.execute_query(query, (
                    datos['nombre'], datos['nif'], datos['direccion'],
                    datos['telefono'], datos['email'], logo_final,
                    self.establecimiento['id']
                ))
            else:
                # Crear nuevo
                query = """
                    INSERT INTO establecimientos (nombre, nif, direccion, telefono, email)
                    VALUES (?, ?, ?, ?, ?)
                """
                self.establecimiento_id = self.db.execute_query(query, (
                    datos['nombre'], datos['nif'], datos['direccion'],
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
                    QMessageBox.information(self, "Éxito", "Establecimiento guardado correctamente")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "No se pudo guardar el establecimiento")

        except (OSError, ValueError, RuntimeError) as e:
            QMessageBox.critical(self, "Error", f"Error al guardar: {e}")

    def obtener_establecimiento_id(self):
        """Retorna el ID del establecimiento creado/editado"""
        return self.establecimiento_id
