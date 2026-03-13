"""
Diálogo de novedades de versión
Se muestra una vez después de actualizar el programa
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTextEdit, QFrame, QCheckBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from config import APP_VERSION, APP_NAME
from app.i18n import tr
from app.db.database import Database
from app.utils.logger import logger
from app.ui.transparent_buttons import apply_btn_success


# Notas de cada versión (changelog)
CHANGELOGS = {
    "4.1.0": """
## Novedades en v4.1.0

### Nuevas funciones
- **Factura desde reparación SAT**: Nuevo botón en el historial de reparaciones para generar factura formal
  - La factura queda registrada en la base de datos para Hacienda
  - Incluye desglose de IVA automático (precios en SAT incluyen IVA)
  - Solo disponible cuando el estado es "Entregado" (después de cobrar)

### Correcciones
- Corregido flujo de guardado e impresión: el formulario se limpia siempre después de guardar
- Corregido: el PDF temporal no se borra hasta cerrar la ventana de impresión (permite reintentos)
- Mejorada captura de excepciones en el sistema de impresión
""",
    "3.4.7": """
## Novedades en v3.4.7

### Nuevas funciones
- **Recambios en reparaciones SAT**: Al marcar una reparación como "Reparado", ahora puedes añadir los recambios utilizados
  - Búsqueda por código EAN para añadir productos del inventario
  - Añadir recambios manuales con descripción y precio
  - Descuento automático de stock al guardar
  - Historial de recambios visible en el detalle de cada reparación

### Mejoras
- Detalle de reparación mejorado con tabla de averías/soluciones
- Visualización de recambios utilizados en el detalle de reparación
""",
    "3.4.3": """
## Novedades en v3.4.3

### Correcciones
- **Ventana CMD**: Eliminada la ventana de consola que aparecía brevemente al abrir el programa
  - Corregido subprocess.run sin flag CREATE_NO_WINDOW en verificación de instancia única
""",
    "3.4.2": """
## Novedades en v3.4.2

### Correcciones
- **Impresora de tickets**: Corregido error de archivo bloqueado al imprimir
- **Sistema de licencias**: Nuevo algoritmo de ID basado en hardware fijo (UUID BIOS)
  - El ID ahora es 100% estable y nunca cambia
  - Las licencias existentes se migran automáticamente
""",
    "3.4.1": """
## Novedades en v3.4.1

### Correcciones
- **Impresora de tickets**: Corregido error "El archivo está siendo utilizado por otro proceso" al imprimir tickets
- Mejorada la gestión de archivos temporales de impresión
""",
    "3.4.0": """
## Novedades en v3.4.0

### Nuevas funciones
- **Ventana de novedades**: Ahora verás las novedades de cada versión después de actualizar
- El changelog se muestra solo una vez por versión

### Correcciones
- Corregido error de base de datos "duplicate column name: ram"
- Corregido error del escáner al cargar imágenes
- Mejorada estabilidad del sistema de licencias
""",
    "3.3.1": """
## Novedades en v3.3.1

### Correcciones
- Corregido error de base de datos "duplicate column name: ram" en nuevas instalaciones
- Corregido error del escáner al cargar imágenes existentes

### Nuevas funciones
- **Sistema de actualizaciones automáticas (OTA)**: El programa ahora detecta nuevas versiones y permite actualizar fácilmente
- Opción "Buscar Actualizaciones" en el menú principal
- Backup automático de la base de datos antes de actualizar

### Mejoras
- Títulos unificados en todas las ventanas
- Opción para activar/desactivar contraseña en operaciones críticas
""",
    "3.3.0": """
## Novedades en v3.3.0

### Correcciones
- Corregido error de migración de base de datos
- Corregido error en el escáner de documentos

### Nuevas funciones
- Sistema de actualizaciones OTA implementado
""",
    "3.2.0": """
## Novedades en v3.2.0

### Nuevas funciones
- Logo del establecimiento en la ventana de login
- Botones de guardar separados por pestaña en Ajustes
- Opción de protección de operaciones críticas configurable

### Correcciones
- Corregido mapeo de columnas en tabla de ventas
"""
}


class ChangelogDialog(QDialog):
    """
    Diálogo que muestra las novedades de la versión actual.
    Se muestra una sola vez después de actualizar.
    """

    def __init__(self, version: str = None, parent=None):
        super().__init__(parent)
        self.version = version or APP_VERSION
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle(tr("Novedades - {app}", app=APP_NAME))
        self.setMinimumWidth(550)
        self.setMinimumHeight(450)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        # === Header ===
        header_layout = QHBoxLayout()

        icon_label = QLabel("🎉")
        icon_label.setFont(QFont("", 36))
        header_layout.addWidget(icon_label)

        title_layout = QVBoxLayout()

        title_label = QLabel(tr("¡Bienvenido a {app} v{version}!", app=APP_NAME, version=self.version))
        title_label.setFont(QFont("", 16, QFont.Bold))
        title_label.setStyleSheet("color: #A3BE8C;")
        title_layout.addWidget(title_label)

        subtitle = QLabel(tr("Tu programa se ha actualizado correctamente"))
        subtitle.setStyleSheet("color: #7B88A0; font-size: 12px;")
        title_layout.addWidget(subtitle)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # === Separador ===
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #434C5E;")
        layout.addWidget(line)

        # === Changelog ===
        changelog_label = QLabel(tr("¿Qué hay de nuevo?"))
        changelog_label.setFont(QFont("", 11, QFont.Bold))
        layout.addWidget(changelog_label)

        self.changelog_text = QTextEdit()
        self.changelog_text.setReadOnly(True)
        self.changelog_text.setMarkdown(self._get_changelog())
        self.changelog_text.setStyleSheet("""
            QTextEdit {
                background-color: #3B4252;
                border: 1px solid #434C5E;
                border-radius: 8px;
                padding: 15px;
                color: #D8DEE9;
                font-size: 13px;
            }
        """)
        layout.addWidget(self.changelog_text)

        # === Footer ===
        footer_frame = QFrame()
        footer_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(94, 129, 172, 0.15);
                border: 1px solid #81A1C1;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        footer_layout = QVBoxLayout(footer_frame)
        footer_layout.setContentsMargins(10, 10, 10, 10)

        tip_label = QLabel(tr("Puedes buscar actualizaciones en cualquier momento desde el menú ☰ → Buscar Actualizaciones"))
        tip_label.setWordWrap(True)
        tip_label.setStyleSheet("color: #5E81AC; border: none; font-size: 11px;")
        footer_layout.addWidget(tip_label)

        layout.addWidget(footer_frame)

        # === Botón cerrar ===
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_ok = QPushButton(tr("Entendido"))
        btn_ok.clicked.connect(self.accept)
        apply_btn_success(btn_ok)
        btn_layout.addWidget(btn_ok)

        layout.addLayout(btn_layout)

    def _get_changelog(self) -> str:
        """Obtiene el changelog de la versión actual"""
        # Buscar changelog exacto
        if self.version in CHANGELOGS:
            return CHANGELOGS[self.version]

        # Si no hay changelog específico, mostrar mensaje genérico
        return (
            f"## {tr('Versión')} {self.version}\n\n"
            f"{tr('Gracias por actualizar {app}.', app=APP_NAME)}\n\n"
            f"{tr('Esta versión incluye mejoras y correcciones de errores.')}\n"
        )


def marcar_version_vista(db: Database, version: str):
    """Marca la versión como vista para no mostrar el changelog de nuevo"""
    try:
        db.execute_query(
            "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('ultima_version_vista', ?)",
            (version,)
        )
    except (OSError, ValueError, RuntimeError) as e:
        logger.error(f"Error guardando versión vista: {e}")


def obtener_ultima_version_vista(db: Database) -> str:
    """Obtiene la última versión que el usuario ha visto"""
    try:
        result = db.fetch_one(
            "SELECT valor FROM configuracion WHERE clave = 'ultima_version_vista'"
        )
        if result:
            return result.get('valor', '')
    except (OSError, ValueError, RuntimeError):
        pass
    return ''


def mostrar_changelog_si_necesario(db: Database, parent=None) -> bool:
    """
    Muestra el diálogo de changelog si es una versión nueva.

    Returns:
        bool: True si se mostró el diálogo
    """
    ultima_vista = obtener_ultima_version_vista(db)

    # Si es la primera vez o hay nueva versión
    if ultima_vista != APP_VERSION:
        dialog = ChangelogDialog(APP_VERSION, parent)
        dialog.exec_()

        # Marcar como vista
        marcar_version_vista(db, APP_VERSION)
        return True

    return False
