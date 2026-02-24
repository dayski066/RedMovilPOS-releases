"""
GENERADOR DE CLAVES DE LICENCIA - RedMovilPOS (GUI)
===================================================
IMPORTANTE: Este archivo es CONFIDENCIAL y debe mantenerse
solo en poder del desarrollador. NO incluir en la distribución.

Uso:
    python keygen_gui.py

Versión gráfica del generador de claves.
"""
import sys
import os

# Añadir el directorio raíz al path para importar módulos de la app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFrame
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QIcon, QClipboard

from app.modules.license_secret import generar_hash_licencia_keygen


def resource_path(relative_path):
    """Obtiene la ruta correcta tanto en desarrollo como en exe compilado."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


def generar_clave(machine_id):
    """Genera la clave de licencia usando PBKDF2 directo."""
    return generar_hash_licencia_keygen(machine_id)


STYLE = """
QWidget {
    background-color: #2E3440;
    color: #ECEFF4;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}

QLineEdit {
    background-color: #3B4252;
    color: #ECEFF4;
    border: 2px solid #434C5E;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
}

QLineEdit:focus {
    border-color: #81A1C1;
}

QLineEdit[readOnly="true"] {
    background-color: #3B4252;
    color: #A3BE8C;
    border-color: #A3BE8C;
    font-size: 15px;
    font-weight: bold;
    font-family: 'Consolas', 'Courier New', monospace;
    letter-spacing: 2px;
}

QPushButton#btn_generar {
    background-color: #5E81AC;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: bold;
}
QPushButton#btn_generar:hover {
    background-color: #81A1C1;
}
QPushButton#btn_generar:pressed {
    background-color: #4C6B91;
}

QPushButton#btn_copiar {
    background-color: #A3BE8C;
    color: #2E3440;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: bold;
}
QPushButton#btn_copiar:hover {
    background-color: #8FBC8B;
}
QPushButton#btn_copiar:pressed {
    background-color: #7AAD78;
}
QPushButton#btn_copiar:disabled {
    background-color: #434C5E;
    color: #4C566A;
}

QFrame#card {
    background-color: #3B4252;
    border: 1px solid #434C5E;
    border-radius: 8px;
}

QLabel#label_title {
    font-size: 20px;
    font-weight: bold;
    color: #ECEFF4;
}

QLabel#label_subtitle {
    font-size: 12px;
    color: #7B88A0;
}

QLabel#label_section {
    font-size: 12px;
    font-weight: bold;
    color: #81A1C1;
    letter-spacing: 1px;
}

QLabel#label_result {
    font-size: 12px;
    font-weight: bold;
    color: #A3BE8C;
    letter-spacing: 1px;
}

QLabel#label_warning {
    font-size: 11px;
    color: #4C566A;
}

QLabel#label_status_ok {
    font-size: 12px;
    color: #A3BE8C;
    font-weight: bold;
}

QLabel#label_status_err {
    font-size: 12px;
    color: #BF616A;
    font-weight: bold;
}
"""


class KeygenWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Generador de Claves · RedMovilPOS")
        self.setFixedSize(480, 540)
        self.setStyleSheet(STYLE)

        try:
            self.setWindowIcon(QIcon(resource_path('keygen_icon.ico')))
        except Exception:
            pass

        self._build_ui()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(0)

        # ── Cabecera ──────────────────────────────────────────
        title = QLabel("GENERADOR DE CLAVES")
        title.setObjectName("label_title")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Herramienta confidencial del desarrollador · RedMovilPOS")
        subtitle.setObjectName("label_subtitle")
        subtitle.setAlignment(Qt.AlignCenter)

        root_layout.addWidget(title)
        root_layout.addSpacing(4)
        root_layout.addWidget(subtitle)
        root_layout.addSpacing(24)

        # ── Tarjeta ID ────────────────────────────────────────
        card_id = QFrame()
        card_id.setObjectName("card")
        id_layout = QVBoxLayout(card_id)
        id_layout.setContentsMargins(16, 14, 16, 14)
        id_layout.setSpacing(8)

        lbl_id = QLabel("ID DE MÁQUINA DEL CLIENTE")
        lbl_id.setObjectName("label_section")

        self.input_id = QLineEdit()
        self.input_id.setPlaceholderText("RMPV-XXXX-XXXX-XXXX-XXXX")
        self.input_id.setFixedHeight(42)
        font_mono = QFont("Consolas", 12)
        self.input_id.setFont(font_mono)
        self.input_id.setAlignment(Qt.AlignCenter)
        self.input_id.returnPressed.connect(self.generar)

        id_layout.addWidget(lbl_id)
        id_layout.addWidget(self.input_id)

        root_layout.addWidget(card_id)
        root_layout.addSpacing(12)

        # ── Botón generar ─────────────────────────────────────
        self.btn_generar = QPushButton("Generar Clave")
        self.btn_generar.setObjectName("btn_generar")
        self.btn_generar.setFixedHeight(44)
        self.btn_generar.setCursor(Qt.PointingHandCursor)
        self.btn_generar.clicked.connect(self.generar)

        root_layout.addWidget(self.btn_generar)
        root_layout.addSpacing(12)

        # ── Tarjeta resultado ─────────────────────────────────
        card_result = QFrame()
        card_result.setObjectName("card")
        result_layout = QVBoxLayout(card_result)
        result_layout.setContentsMargins(16, 14, 16, 14)
        result_layout.setSpacing(8)

        lbl_result = QLabel("CLAVE DE LICENCIA GENERADA")
        lbl_result.setObjectName("label_result")

        self.output_key = QLineEdit()
        self.output_key.setReadOnly(True)
        self.output_key.setFixedHeight(48)
        self.output_key.setAlignment(Qt.AlignCenter)
        self.output_key.setPlaceholderText("—")

        self.btn_copiar = QPushButton("Copiar al Portapapeles")
        self.btn_copiar.setObjectName("btn_copiar")
        self.btn_copiar.setFixedHeight(40)
        self.btn_copiar.setCursor(Qt.PointingHandCursor)
        self.btn_copiar.setEnabled(False)
        self.btn_copiar.clicked.connect(self.copiar)

        result_layout.addWidget(lbl_result)
        result_layout.addWidget(self.output_key)
        result_layout.addWidget(self.btn_copiar)

        root_layout.addWidget(card_result)
        root_layout.addSpacing(12)

        # ── Estado ────────────────────────────────────────────
        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        root_layout.addWidget(self.lbl_status)

        root_layout.addStretch()

        # ── Pie ───────────────────────────────────────────────
        lbl_warning = QLabel("Esta clave solo funcionará en la máquina con ese ID exacto")
        lbl_warning.setObjectName("label_warning")
        lbl_warning.setAlignment(Qt.AlignCenter)
        root_layout.addWidget(lbl_warning)

    def generar(self):
        machine_id = self.input_id.text().strip().upper()

        if not machine_id:
            self._set_status("Introduce el ID de máquina del cliente", error=True)
            return

        if not machine_id.startswith("RMPV-"):
            self._set_status("Aviso: el ID no empieza por RMPV-", error=True)

        clave = generar_clave(machine_id)
        self.output_key.setText(clave)
        self.btn_copiar.setEnabled(True)
        self._set_status(f"Clave generada para {machine_id}", error=False)

    def copiar(self):
        clave = self.output_key.text()
        if clave:
            QApplication.clipboard().setText(clave)
            self._set_status("Clave copiada al portapapeles", error=False)

    def _set_status(self, msg, error=False):
        self.lbl_status.setText(msg)
        self.lbl_status.setObjectName("label_status_err" if error else "label_status_ok")
        self.lbl_status.setStyleSheet(
            "color: #BF616A;" if error else "color: #A3BE8C;"
        )


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = KeygenWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
