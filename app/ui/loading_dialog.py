"""
Diálogo de carga profesional con animación premium
Se muestra durante la transición entre login y ventana principal
"""
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QWidget, QProgressBar
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QColor, QPainter, QPen, QLinearGradient, QFont

from config import APP_NAME, APP_VERSION
from app.i18n import tr


class AnimatedDots(QLabel):
    """Label con puntos animados: Cargando. -> Cargando.. -> Cargando..."""

    def __init__(self, base_text="Cargando", parent=None):
        super().__init__(parent)
        self.base_text = base_text
        self.dot_count = 0
        self.max_dots = 3

        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                color: #88C0D0;
                font-size: 15px;
                font-weight: 600;
                background: transparent;
                letter-spacing: 0.5px;
            }
        """)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_dots)
        self.timer.start(400)
        self._update_dots()

    def _update_dots(self):
        self.dot_count = (self.dot_count + 1) % (self.max_dots + 1)
        dots = "." * self.dot_count
        spaces = " " * (self.max_dots - self.dot_count)
        self.setText(f"{self.base_text}{dots}{spaces}")

    def stop(self):
        self.timer.stop()


class SpinnerWidget(QLabel):
    """Widget con spinner circular animado con doble arco y glow"""

    def __init__(self, size=65, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._angle = 0
        self._size = size

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._rotate)
        self.timer.start(20)

    def _rotate(self):
        self._angle = (self._angle + 5) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        center = self._size // 2
        radius = center - 7

        # Anillo de fondo tenue
        pen = QPen(QColor("#3B4252"))
        pen.setWidth(4)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawEllipse(center - radius, center - radius, radius * 2, radius * 2)

        # Arco principal (cyan brillante)
        pen = QPen(QColor("#88C0D0"))
        pen.setWidth(4)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(
            center - radius, center - radius,
            radius * 2, radius * 2,
            self._angle * 16,
            110 * 16
        )

        # Segundo arco (azul, opuesto)
        pen = QPen(QColor("#5E81AC"))
        pen.setWidth(4)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(
            center - radius, center - radius,
            radius * 2, radius * 2,
            (self._angle + 180) * 16,
            70 * 16
        )

    def stop(self):
        self.timer.stop()


class LoadingDialog(QDialog):
    """
    Diálogo de carga premium con:
    - Nombre de la aplicación con tipografía grande
    - Mensaje de bienvenida personalizado
    - Spinner animado con doble arco
    - Barra de progreso indeterminada con gradiente
    - Fondo con gradiente sutil y borde luminoso
    """

    def __init__(self, parent=None, welcome_name=None):
        super().__init__(parent)
        self.welcome_name = welcome_name
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Dialog
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(460, 430 if welcome_name else 380)

        self._setup_ui()
        self._center_on_screen()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── Contenedor principal con fondo gradiente ──
        h = 430 if self.welcome_name else 380
        container = QWidget(self)
        container.setFixedSize(460, h)
        container.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2E3440, stop:1 #272C36
                );
                border: 1px solid rgba(136, 192, 208, 0.35);
                border-radius: 18px;
            }
        """)

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(45, 35, 45, 28)
        container_layout.setSpacing(0)

        # ── Nombre de la app ──
        app_label = QLabel(APP_NAME)
        app_label.setAlignment(Qt.AlignCenter)
        app_label.setStyleSheet("""
            QLabel {
                color: #ECEFF4;
                font-size: 28px;
                font-weight: bold;
                background: transparent;
                border: none;
                letter-spacing: 2px;
            }
        """)
        container_layout.addWidget(app_label)

        container_layout.addSpacing(4)

        # ── Versión ──
        version_label = QLabel(f"v{APP_VERSION}")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("""
            QLabel {
                color: #4C566A;
                font-size: 12px;
                background: transparent;
                border: none;
                letter-spacing: 1px;
            }
        """)
        container_layout.addWidget(version_label)

        container_layout.addSpacing(16)

        # ── Separador decorativo ──
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("""
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 transparent,
                stop:0.3 #5E81AC,
                stop:0.7 #5E81AC,
                stop:1 transparent
            );
            border: none;
        """)
        container_layout.addWidget(sep)

        container_layout.addSpacing(16)

        # ── Mensaje de bienvenida ──
        if self.welcome_name:
            welcome_label = QLabel(f"👋  {tr('Bienvenido, {usuario}', usuario=self.welcome_name)}")
            welcome_label.setAlignment(Qt.AlignCenter)
            welcome_label.setStyleSheet("""
                QLabel {
                    color: #A3BE8C;
                    font-size: 16px;
                    font-weight: 600;
                    background: transparent;
                    border: none;
                    padding: 8px 0;
                }
            """)
            container_layout.addWidget(welcome_label)

            container_layout.addSpacing(10)

        # ── Spinner ──
        container_layout.addSpacing(8)

        self.spinner = SpinnerWidget(65)
        spinner_container = QWidget()
        spinner_container.setStyleSheet("background: transparent; border: none;")
        spinner_layout = QVBoxLayout(spinner_container)
        spinner_layout.setContentsMargins(0, 0, 0, 0)
        spinner_layout.addWidget(self.spinner, alignment=Qt.AlignCenter)
        container_layout.addWidget(spinner_container)

        container_layout.addSpacing(12)

        # ── Texto animado ──
        self.loading_text = AnimatedDots(tr("Preparando tu espacio de trabajo"))
        container_layout.addWidget(self.loading_text)

        container_layout.addSpacing(20)

        # ── Barra de progreso indeterminada ──
        self.progress = QProgressBar()
        self.progress.setFixedHeight(5)
        self.progress.setRange(0, 0)  # Indeterminado
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: #3B4252;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5E81AC,
                    stop:0.5 #88C0D0,
                    stop:1 #5E81AC
                );
                border-radius: 2px;
            }
        """)
        container_layout.addWidget(self.progress)

        container_layout.addStretch()

        # ── Copyright ──
        copyright_label = QLabel(f"\u00a9 2024-2026 RedMovilPOS")
        copyright_label.setAlignment(Qt.AlignCenter)
        copyright_label.setStyleSheet("""
            QLabel {
                color: #434C5E;
                font-size: 10px;
                background: transparent;
                border: none;
            }
        """)
        container_layout.addWidget(copyright_label)

        layout.addWidget(container)

    def _center_on_screen(self):
        """Centra el diálogo en la pantalla"""
        from PyQt5.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def closeEvent(self, event):
        """Detener animaciones al cerrar"""
        self.spinner.stop()
        self.loading_text.stop()
        super().closeEvent(event)

    def done(self, result):
        """Detener animaciones al terminar"""
        self.spinner.stop()
        self.loading_text.stop()
        super().done(result)
