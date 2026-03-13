"""
Tour Overlay — Coach Marks / Feature Spotlight
Widget semitransparente con spotlight sobre el widget objetivo.
"""
from dataclasses import dataclass, field
from typing import Callable, Optional

from PyQt5.QtWidgets import (QWidget, QFrame, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QApplication)
from PyQt5.QtCore import Qt, QRect, QRectF, QPoint, QTimer, QEvent
from PyQt5.QtGui import QPainter, QPainterPath, QColor, QPen, QFont

from app.i18n import tr


@dataclass
class TourStep:
    widget_getter: Callable        # () -> QWidget objetivo
    title_key: str                 # clave tr() para el título
    text_key: str                  # clave tr() para el texto
    navigate: Optional[Callable] = None  # () -> None  (navegar a la tab)
    bubble_pos: str = 'bottom'     # 'bottom' | 'top' | 'right' | 'left'


# ─────────────────────────── Burbuja ───────────────────────────

class TourBubble(QFrame):
    """Burbuja de información que acompaña al spotlight."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("tourBubble")
        self.setStyleSheet("""
            QFrame#tourBubble {
                background-color: #2E3440;
                border: 2px solid #88C0D0;
                border-radius: 12px;
            }
            QLabel { color: #ECEFF4; background: transparent; border: none; }
            QPushButton {
                border: 1px solid #4C566A;
                border-radius: 6px;
                padding: 6px 14px;
                color: #D8DEE9;
                background: #3B4252;
                font-size: 13px;
            }
            QPushButton:hover { background: #434C5E; color: #ffffff; }
            QPushButton#btnNext {
                background: #5E81AC;
                border-color: #81A1C1;
                color: #ECEFF4;
                font-weight: bold;
            }
            QPushButton#btnNext:hover { background: #81A1C1; }
        """)
        self.setFixedWidth(340)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # Indicador de paso
        self.lbl_step = QLabel()
        self.lbl_step.setStyleSheet("color: #88C0D0; font-size: 11px;")
        layout.addWidget(self.lbl_step)

        # Título
        self.lbl_title = QLabel()
        font = QFont()
        font.setBold(True)
        font.setPointSize(13)
        self.lbl_title.setFont(font)
        self.lbl_title.setWordWrap(True)
        layout.addWidget(self.lbl_title)

        # Texto descriptivo
        self.lbl_text = QLabel()
        self.lbl_text.setWordWrap(True)
        self.lbl_text.setStyleSheet("color: #D8DEE9; font-size: 12px; border: none;")
        layout.addWidget(self.lbl_text)

        layout.addSpacing(4)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_skip = QPushButton()
        self.btn_skip.setObjectName("btnSkip")
        self.btn_prev = QPushButton()
        self.btn_prev.setObjectName("btnPrev")
        self.btn_next = QPushButton()
        self.btn_next.setObjectName("btnNext")

        btn_layout.addWidget(self.btn_skip)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_prev)
        btn_layout.addWidget(self.btn_next)
        layout.addLayout(btn_layout)

    def update_content(self, step_n: int, total: int, title: str, text: str,
                       is_first: bool, is_last: bool):
        self.lbl_step.setText(
            tr("Paso {n} de {total}").format(n=step_n, total=total)
        )
        self.lbl_title.setText(title)
        self.lbl_text.setText(text)
        self.btn_skip.setText(tr("Saltar"))
        self.btn_prev.setText(f"← {tr('Anterior')}")
        self.btn_next.setText(
            f"{tr('Finalizar')} ✓" if is_last else f"{tr('Siguiente')} →"
        )
        self.btn_prev.setVisible(not is_first)
        self.adjustSize()


# ─────────────────────────── Overlay ───────────────────────────

class TourOverlay(QWidget):
    """
    Widget superpuesto sobre main_window que implementa el spotlight tour.
    Uso:
        overlay = TourOverlay(main_window)
        overlay.start(steps)
    """

    def __init__(self, main_window: QWidget):
        super().__init__(main_window)
        self._main_window = main_window
        self._steps: list[TourStep] = []
        self._current_index: int = 0
        self._spotlight_rect: Optional[QRect] = None

        # Ocupar todo el espacio de la ventana
        self.setGeometry(main_window.rect())
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)

        # Burbuja hija
        self._bubble = TourBubble(self)
        self._bubble.btn_skip.clicked.connect(self._saltar)
        self._bubble.btn_prev.clicked.connect(self._anterior)
        self._bubble.btn_next.clicked.connect(self._siguiente)

        self.hide()

        # Escuchar resize/move de la ventana principal
        main_window.installEventFilter(self)

    # ── API pública ────────────────────────────────────────────

    def start(self, steps: list[TourStep]):
        if not steps:
            return
        self._steps = steps
        self._current_index = 0
        self.setGeometry(self._main_window.rect())
        self.raise_()
        self.show()
        QTimer.singleShot(100, lambda: self._ir_a_paso(0))

    # ── Navegación interna ──────────────────────────────────────

    def _ir_a_paso(self, index: int):
        if index < 0 or index >= len(self._steps):
            return
        self._current_index = index
        step = self._steps[index]

        # Navegar a la tab correcta si es necesario
        if step.navigate:
            step.navigate()
            QApplication.processEvents()

        # Actualizar spotlight
        self._actualizar_spotlight(step)

        # Actualizar burbuja
        total = len(self._steps)
        title = tr(step.title_key)
        text = tr(step.text_key)
        self._bubble.update_content(
            step_n=index + 1,
            total=total,
            title=title,
            text=text,
            is_first=(index == 0),
            is_last=(index == total - 1),
        )

        # Posicionar burbuja
        self._posicionar_burbuja(step.bubble_pos)
        self._bubble.show()
        self.update()

    def _actualizar_spotlight(self, step: TourStep):
        try:
            widget = step.widget_getter()
            if widget and widget.isVisible():
                global_pos = widget.mapToGlobal(QPoint(0, 0))
                local_pos = self.mapFromGlobal(global_pos)
                self._spotlight_rect = QRect(local_pos, widget.size())
            else:
                self._spotlight_rect = None
        except RuntimeError:
            self._spotlight_rect = None

    def _posicionar_burbuja(self, pos: str):
        """Posiciona la burbuja respecto al spotlight."""
        self._bubble.adjustSize()
        bw = self._bubble.width()
        bh = self._bubble.height()
        ow = self.width()
        oh = self.height()
        margin = 16

        if self._spotlight_rect:
            sr = self._spotlight_rect.adjusted(-10, -10, 10, 10)
            cx = sr.center().x()
            cy = sr.center().y()

            if pos == 'bottom':
                x = max(margin, min(cx - bw // 2, ow - bw - margin))
                y = sr.bottom() + margin
                # Si no cabe abajo, poner arriba
                if y + bh > oh - margin:
                    y = max(margin, sr.top() - bh - margin)
            elif pos == 'top':
                x = max(margin, min(cx - bw // 2, ow - bw - margin))
                y = sr.top() - bh - margin
                # Si no cabe arriba, solapar sobre el borde superior del spotlight
                if y < margin:
                    y = sr.top() + margin
            elif pos == 'right':
                x = sr.right() + margin
                y = max(margin, min(cy - bh // 2, oh - bh - margin))
                if x + bw > ow - margin:
                    x = sr.left() - bw - margin
            else:  # left
                x = sr.left() - bw - margin
                y = max(margin, min(cy - bh // 2, oh - bh - margin))
                if x < margin:
                    x = sr.right() + margin

            # Clamp final para no salirse nunca de la ventana
            x = max(margin, min(x, ow - bw - margin))
            y = max(margin, min(y, oh - bh - margin))
        else:
            # Centrar si no hay spotlight
            x = (ow - bw) // 2
            y = (oh - bh) // 2

        self._bubble.move(x, max(margin, y))

    def _siguiente(self):
        if self._current_index >= len(self._steps) - 1:
            self._terminar()
        else:
            self._ir_a_paso(self._current_index + 1)

    def _anterior(self):
        if self._current_index > 0:
            self._ir_a_paso(self._current_index - 1)

    def _saltar(self):
        self._terminar()

    def _terminar(self):
        self._main_window.removeEventFilter(self)
        self.hide()
        self.deleteLater()

    # ── Eventos Qt ─────────────────────────────────────────────

    def eventFilter(self, obj, event):
        """Detecta resize/maximizar de la ventana principal y actualiza el overlay."""
        if obj is self._main_window and event.type() in (
            QEvent.Resize, QEvent.WindowStateChange, QEvent.Move
        ):
            self._sincronizar_geometria()
        return super().eventFilter(obj, event)

    def _sincronizar_geometria(self):
        """Ajusta el overlay y recalcula spotlight + burbuja."""
        self.setGeometry(self._main_window.rect())
        if self._steps and self._current_index < len(self._steps):
            step = self._steps[self._current_index]
            self._actualizar_spotlight(step)
            self._posicionar_burbuja(step.bubble_pos)
        self.update()

    def resizeEvent(self, event):
        # El overlay se redimensiona cuando main_window lo hace (hijo directo)
        # La sincronización ya la gestiona eventFilter
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Overlay oscuro full-screen con agujero para el spotlight
        full = QPainterPath()
        full.addRect(QRectF(self.rect()))

        if self._spotlight_rect:
            r = self._spotlight_rect.adjusted(-10, -10, 10, 10)
            hole = QPainterPath()
            hole.addRoundedRect(QRectF(r), 10, 10)
            full = full.subtracted(hole)

        painter.fillPath(full, QColor(0, 0, 0, 170))

        # Borde brillante alrededor del spotlight
        if self._spotlight_rect:
            r = self._spotlight_rect.adjusted(-10, -10, 10, 10)
            painter.setPen(QPen(QColor("#88C0D0"), 2))
            painter.drawRoundedRect(QRectF(r), 10, 10)

    def mousePressEvent(self, event):
        # Permitir clics dentro del spotlight (pasan al widget subyacente)
        if self._spotlight_rect and self._spotlight_rect.adjusted(-10, -10, 10, 10).contains(event.pos()):
            event.ignore()
        else:
            event.accept()  # Bloquear clics fuera del spotlight

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self._saltar()
        elif event.key() in (Qt.Key_Right, Qt.Key_Return):
            self._siguiente()
        elif event.key() == Qt.Key_Left:
            self._anterior()
        else:
            super().keyPressEvent(event)
