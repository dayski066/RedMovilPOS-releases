"""
Widget indicador de fortaleza de contraseña para REDMOVILPOS
Muestra visualmente qué tan segura es una contraseña
"""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PyQt5.QtCore import Qt
import re


class PasswordStrengthWidget(QWidget):
    """
    Widget que muestra la fortaleza de una contraseña en tiempo real.

    Características evaluadas:
    - Longitud mínima (8 caracteres)
    - Contiene mayúsculas
    - Contiene números
    - Contiene caracteres especiales
    - Longitud extra (+12 caracteres)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def showEvent(self, event):
        """Fuerza repintado al mostrarse para evitar bugs de renderizado"""
        super().showEvent(event)
        self.update()
        self.repaint()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(6)
        self.setMinimumHeight(60)

        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #4C566A;
                border-radius: 4px;
                background-color: #3B4252;
            }
            QProgressBar::chunk {
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Layout horizontal para indicadores
        indicators_layout = QHBoxLayout()
        indicators_layout.setSpacing(8)

        # Indicadores individuales
        self.lbl_longitud = QLabel("8+ chars")
        self.lbl_mayuscula = QLabel("ABC")
        self.lbl_numero = QLabel("123")
        self.lbl_especial = QLabel("@#$")

        for lbl in [self.lbl_longitud, self.lbl_mayuscula, self.lbl_numero, self.lbl_especial]:
            lbl.setFixedHeight(24)
            lbl.setMinimumWidth(55)
            lbl.setStyleSheet("""
                QLabel {
                    color: #4C566A;
                    font-size: 11px;
                    padding: 4px 8px;
                    border-radius: 3px;
                    background-color: #3B4252;
                }
            """)
            indicators_layout.addWidget(lbl)

        indicators_layout.addStretch()

        # Label de estado
        self.lbl_estado = QLabel("")
        self.lbl_estado.setStyleSheet("font-size: 11px; font-weight: bold;")
        indicators_layout.addWidget(self.lbl_estado)

        layout.addLayout(indicators_layout)

    def evaluar_password(self, password: str):
        """
        Evalúa la fortaleza de una contraseña y actualiza la UI.

        Args:
            password: Contraseña a evaluar

        Returns:
            tuple: (puntuacion: int, es_valida: bool, mensaje: str)
        """
        puntos = 0
        criterios = {
            'longitud': False,
            'mayuscula': False,
            'numero': False,
            'especial': False,
            'extra': False
        }

        # Evaluar criterios
        if len(password) >= 8:
            criterios['longitud'] = True
            puntos += 25

        if re.search(r'[A-Z]', password):
            criterios['mayuscula'] = True
            puntos += 25

        if re.search(r'\d', password):
            criterios['numero'] = True
            puntos += 25

        if re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;\'`~]', password):
            criterios['especial'] = True
            puntos += 15

        if len(password) >= 12:
            criterios['extra'] = True
            puntos += 10

        # Actualizar barra de progreso
        self.progress_bar.setValue(puntos)

        # Color según puntuación
        if puntos < 50:
            color = "#BF616A"  # Rojo
            estado = "Débil"
        elif puntos < 75:
            color = "#EBCB8B"  # Naranja
            estado = "Media"
        elif puntos < 90:
            color = "#5E81AC"  # Azul
            estado = "Buena"
        else:
            color = "#A3BE8C"  # Verde
            estado = "Fuerte"

        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #4C566A;
                border-radius: 4px;
                background-color: #3B4252;
            }}
            QProgressBar::chunk {{
                border-radius: 3px;
                background-color: {color};
            }}
        """)

        # Actualizar indicadores
        self._actualizar_indicador(self.lbl_longitud, criterios['longitud'])
        self._actualizar_indicador(self.lbl_mayuscula, criterios['mayuscula'])
        self._actualizar_indicador(self.lbl_numero, criterios['numero'])
        self._actualizar_indicador(self.lbl_especial, criterios['especial'])

        # Actualizar estado
        self.lbl_estado.setText(estado)
        self.lbl_estado.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {color};")

        # Validez (cumple requisitos mínimos)
        es_valida = criterios['longitud'] and criterios['mayuscula'] and criterios['numero']

        return puntos, es_valida, estado

    def _actualizar_indicador(self, label: QLabel, cumple: bool):
        """Actualiza el estilo de un indicador según si cumple el criterio"""
        if cumple:
            label.setStyleSheet("""
                QLabel {
                    color: #A3BE8C;
                    font-size: 10px;
                    padding: 2px 6px;
                    border-radius: 3px;
                    background-color: rgba(39, 174, 96, 0.2);
                    border: 1px solid #A3BE8C;
                }
            """)
        else:
            label.setStyleSheet("""
                QLabel {
                    color: #4C566A;
                    font-size: 10px;
                    padding: 2px 6px;
                    border-radius: 3px;
                    background-color: #3B4252;
                }
            """)

    def reset(self):
        """Reinicia el widget a su estado inicial"""
        self.progress_bar.setValue(0)
        self.lbl_estado.setText("")
        for lbl in [self.lbl_longitud, self.lbl_mayuscula, self.lbl_numero, self.lbl_especial]:
            lbl.setStyleSheet("""
                QLabel {
                    color: #4C566A;
                    font-size: 10px;
                    padding: 2px 6px;
                    border-radius: 3px;
                    background-color: #3B4252;
                }
            """)
