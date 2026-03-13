# -*- coding: utf-8 -*-
"""
Constantes centralizadas del tema Nord para RedMovilPOS.
Usar estas constantes en lugar de colores hex hardcodeados.

Paleta Nord: https://www.nordtheme.com/
"""

# ═══════════════════════════════════════════════════════════════
# Polar Night (fondos oscuros)
# ═══════════════════════════════════════════════════════════════
NORD0 = "#2E3440"    # Fondo principal
NORD1 = "#3B4252"    # Fondo elevado / cards
NORD2 = "#434C5E"    # Fondo selección / bordes activos
NORD3 = "#4C566A"    # Bordes inactivos / texto deshabilitado

# ═══════════════════════════════════════════════════════════════
# Snow Storm (textos claros)
# ═══════════════════════════════════════════════════════════════
NORD4 = "#D8DEE9"    # Texto secundario / iconos
NORD5 = "#E5E9F0"    # Texto principal
NORD6 = "#ECEFF4"    # Texto destacado / headers

# ═══════════════════════════════════════════════════════════════
# Frost (azules — acento principal)
# ═══════════════════════════════════════════════════════════════
NORD7 = "#8FBCBB"    # Verde-azulado
NORD8 = "#88C0D0"    # Cian / turquesa — acento principal
NORD9 = "#81A1C1"    # Azul claro — informativo
NORD10 = "#5E81AC"   # Azul — primario / enlaces

# ═══════════════════════════════════════════════════════════════
# Aurora (colores semánticos)
# ═══════════════════════════════════════════════════════════════
NORD11 = "#BF616A"   # Rojo — peligro / error / eliminar
NORD12 = "#D08770"   # Naranja — advertencia stock bajo
NORD13 = "#EBCB8B"   # Amarillo — advertencia / atencion
NORD14 = "#A3BE8C"   # Verde — éxito / confirmar
NORD15 = "#B48EAD"   # Púrpura — acento especial

# ═══════════════════════════════════════════════════════════════
# Aliases semánticos (para uso intuitivo)
# ═══════════════════════════════════════════════════════════════
COLOR_BG = NORD0
COLOR_BG_ELEVATED = NORD1
COLOR_BG_ACTIVE = NORD2
COLOR_BORDER = NORD3

COLOR_TEXT = NORD4
COLOR_TEXT_PRIMARY = NORD5
COLOR_TEXT_BRIGHT = NORD6

COLOR_ACCENT = NORD8
COLOR_INFO = NORD9
COLOR_PRIMARY = NORD10

COLOR_DANGER = NORD11
COLOR_WARNING_STOCK = NORD12
COLOR_WARNING = NORD13
COLOR_SUCCESS = NORD14
COLOR_SPECIAL = NORD15

# Texto auxiliar (no está en la paleta Nord oficial)
COLOR_TEXT_MUTED = "#7B88A0"
