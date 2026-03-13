"""
Notificaciones modernas (Fluent Design)
========================================
Reemplaza QMessageBox por InfoBar (toast) y MessageBox (confirmación).
Importar: from app.utils.notify import notify_success, notify_error, notify_warning, notify_info, ask_confirm
"""
from qfluentwidgets import InfoBar, InfoBarPosition, MessageBox


def _find_top_widget(widget):
    """Busca el widget de nivel superior para posicionar el InfoBar."""
    parent = widget
    while parent.parent() is not None:
        parent = parent.parent()
    return parent


def notify_success(parent, title, message, duration=3000):
    """Notificación de éxito (verde, auto-desaparece)."""
    InfoBar.success(
        title=title,
        content=message,
        orient=1,  # Vertical
        isClosable=True,
        position=InfoBarPosition.TOP_RIGHT,
        duration=duration,
        parent=_find_top_widget(parent),
    )


def notify_error(parent, title, message, duration=5000):
    """Notificación de error (roja, duración más larga)."""
    InfoBar.error(
        title=title,
        content=message,
        orient=1,
        isClosable=True,
        position=InfoBarPosition.TOP_RIGHT,
        duration=duration,
        parent=_find_top_widget(parent),
    )


def notify_warning(parent, title, message, duration=4000):
    """Notificación de advertencia (amarilla)."""
    InfoBar.warning(
        title=title,
        content=message,
        orient=1,
        isClosable=True,
        position=InfoBarPosition.TOP_RIGHT,
        duration=duration,
        parent=_find_top_widget(parent),
    )


def notify_info(parent, title, message, duration=3000):
    """Notificación informativa (azul)."""
    InfoBar.info(
        title=title,
        content=message,
        orient=1,
        isClosable=True,
        position=InfoBarPosition.TOP_RIGHT,
        duration=duration,
        parent=_find_top_widget(parent),
    )


def ask_confirm(parent, title, message):
    """
    Diálogo de confirmación fluent (reemplaza QMessageBox.question).

    Returns:
        bool: True si el usuario confirma, False si cancela.
    """
    dialog = MessageBox(title, message, parent)
    
    # IMPORTANTE: Traducir botones explícitamente porque QFluentWidgets por defecto pone OK/Cancel en inglés
    from app.i18n.translator import tr
    dialog.yesButton.setText(tr("Aceptar"))
    dialog.cancelButton.setText(tr("Cancelar"))
    
    # Hacer el marco de botones transparente y centrar
    dialog.buttonGroup.setStyleSheet("QFrame { background: transparent; }")
    dialog.buttonLayout.setContentsMargins(24, 12, 24, 20)
    return dialog.exec()


def ask_three_options(parent, title, message, btn1_text, btn2_text, btn3_text="Cancelar"):
    """
    Diálogo con 3 botones personalizados.

    Returns:
        int: 0=btn1, 1=btn2, 2=btn3/cancelar
    """
    from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
    from app.ui.transparent_buttons import apply_btn_primary, apply_btn_success, apply_btn_cancel

    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setMinimumWidth(420)
    dialog.result_value = 2  # Cancelar por defecto

    layout = QVBoxLayout(dialog)
    layout.setSpacing(15)
    layout.setContentsMargins(20, 20, 20, 20)

    label = QLabel(message)
    label.setWordWrap(True)
    label.setStyleSheet("font-size: 13px; color: #D8DEE9;")
    layout.addWidget(label)

    btn_layout = QHBoxLayout()
    btn_layout.addStretch()

    btn3 = QPushButton(btn3_text)
    apply_btn_cancel(btn3)
    btn3.clicked.connect(lambda: _close_with(dialog, 2))
    btn_layout.addWidget(btn3)

    btn1 = QPushButton(btn1_text)
    apply_btn_primary(btn1)
    btn1.clicked.connect(lambda: _close_with(dialog, 0))
    btn_layout.addWidget(btn1)

    btn2 = QPushButton(btn2_text)
    apply_btn_success(btn2)
    btn2.clicked.connect(lambda: _close_with(dialog, 1))
    btn_layout.addWidget(btn2)

    layout.addLayout(btn_layout)
    dialog.exec_()
    return dialog.result_value


def _close_with(dialog, value):
    dialog.result_value = value
    dialog.accept()
