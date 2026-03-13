# ESTILOS DE BOTONES INLINE - GARANTIZADOS TRANSPARENTES
# Usar estas funciones en lugar de los helpers tradicionales
from PyQt5.QtCore import QSize
from app.ui.theme import (
    COLOR_ACCENT, COLOR_SUCCESS, COLOR_PRIMARY, COLOR_DANGER,
    COLOR_WARNING, COLOR_INFO, COLOR_BORDER, COLOR_TEXT,
    NORD2, NORD3,
)


def apply_transparent_button_style(btn, border_color=COLOR_ACCENT, text_color=COLOR_ACCENT):
    """
    Aplica estilo con fondo transparente a cualquier botón.
    Por defecto usa color turquesa (NORD8).
    """
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: transparent !important;
            color: {text_color};
            border: 2px solid {border_color};
            border-radius: 6px;
            padding: 0 16px;
            font-size: 14px;
            font-weight: 600;
            min-width: 120px;
        }}
        QPushButton:hover {{
            background-color: rgba(136, 192, 208, 0.1) !important;
            border: 2px solid {border_color};
        }}
        QPushButton:pressed {{
            background-color: rgba(136, 192, 208, 0.2) !important;
        }}
        QPushButton:disabled {{
            background-color: transparent !important;
            color: {COLOR_BORDER};
            border: 2px solid {NORD2};
        }}
    """)

# Funciones compatibles con los nombres anteriores
def apply_btn_success(btn):
    apply_transparent_button_style(btn, border_color=COLOR_SUCCESS, text_color=COLOR_SUCCESS)

def apply_btn_primary(btn):
    apply_transparent_button_style(btn, border_color=COLOR_PRIMARY, text_color=COLOR_PRIMARY)

def apply_btn_danger(btn):
    apply_transparent_button_style(btn, border_color=COLOR_DANGER, text_color=COLOR_DANGER)

def apply_btn_warning(btn):
    apply_transparent_button_style(btn, border_color=COLOR_WARNING, text_color=COLOR_WARNING)

def apply_btn_info(btn):
    apply_transparent_button_style(btn, border_color=COLOR_INFO, text_color=COLOR_INFO)

def apply_btn_cancel(btn):
    apply_transparent_button_style(btn, border_color=COLOR_BORDER, text_color=COLOR_TEXT)


def set_btn_icon(btn, fluent_icon, color=COLOR_TEXT, size=18):
    """
    Añade un FluentIcon a un botón.
    Uso: set_btn_icon(btn, FluentIcon.SEARCH)
    """
    btn.setIcon(fluent_icon.icon(color=color))
    btn.setIconSize(QSize(size, size))

