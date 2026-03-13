"""
Definición de todos los tours interactivos (Coach Marks).
Cada tour es una lista[TourStep].
"""
from PyQt5.QtWidgets import QPushButton, QTabWidget, QApplication
from app.ui.tour_overlay import TourStep


# ─── Helpers ────────────────────────────────────────────────────────────────

def _find_btn(parent, text_fragment: str):
    """Devuelve el primer QPushButton cuyo texto contenga text_fragment."""
    for btn in parent.findChildren(QPushButton):
        if text_fragment.lower() in btn.text().lower():
            return btn
    return parent  # Fallback: retornar el padre si no se encuentra


def _find_btn_tooltip(parent, tooltip_fragment: str):
    """Devuelve el primer QPushButton cuyo tooltip contenga tooltip_fragment."""
    for btn in parent.findChildren(QPushButton):
        if tooltip_fragment.lower() in (btn.toolTip() or '').lower():
            return btn
    return parent


def _get_2fa_btn(usuarios_tab):
    """Devuelve el botón 2FA de la primera fila de la tabla de usuarios."""
    tabla = usuarios_tab.tabla
    if tabla.rowCount() == 0:
        return tabla  # fallback si no hay usuarios
    container = tabla.cellWidget(0, 6)
    if container:
        btn = _find_btn_tooltip(container, '2FA')
        if btn is not container:
            return btn
    return tabla


def _get_tab_widget(stacked_page):
    """Devuelve el primer QTabWidget hijo de una página del stacked_widget."""
    return stacked_page.findChild(QTabWidget)


def _navigate_to(main_window, page_index, subtab_index=None):
    """Navega a una página y opcionalmente a un subtab."""
    def _do_navigate():
        main_window.switch_page(page_index)
        if subtab_index is not None:
            page = main_window.stacked_widget.widget(page_index)
            if page:
                tab_widget = _get_tab_widget(page)
                if tab_widget:
                    tab_widget.setCurrentIndex(subtab_index)
        QApplication.processEvents()
    return _do_navigate


# ─── Tours ───────────────────────────────────────────────────────────────────

def get_tours(main_window) -> dict:
    """
    Retorna un diccionario con todos los tours disponibles.
    Clave: identificador interno del tour.
    Valor: list[TourStep]
    """
    mw = main_window

    tours = {}

    # ─── 1. Crear cliente ──────────────────────────────────────────────────
    tours["cliente"] = [
        TourStep(
            widget_getter=lambda: mw.nav_buttons[3],
            navigate=_navigate_to(mw, 3),
            title_key="tour.cliente.p1.titulo",
            text_key="tour.cliente.p1.texto",
            bubble_pos='bottom',
        ),
        TourStep(
            widget_getter=lambda: _find_btn(mw.clientes_tab, "Nuevo Cliente"),
            navigate=_navigate_to(mw, 3),
            title_key="tour.cliente.p2.titulo",
            text_key="tour.cliente.p2.texto",
            bubble_pos='bottom',
        ),
        TourStep(
            widget_getter=lambda: mw.clientes_tab.search_input,
            navigate=_navigate_to(mw, 3),
            title_key="tour.cliente.p3.titulo",
            text_key="tour.cliente.p3.texto",
            bubble_pos='bottom',
        ),
        TourStep(
            widget_getter=lambda: mw.clientes_tab.tabla,
            navigate=_navigate_to(mw, 3),
            title_key="tour.cliente.p4.titulo",
            text_key="tour.cliente.p4.texto",
            bubble_pos='top',
        ),
    ]

    # ─── 2. Crear factura ─────────────────────────────────────────────────
    tours["factura"] = [
        TourStep(
            widget_getter=lambda: mw.nav_buttons[1],
            navigate=_navigate_to(mw, 1, 0),
            title_key="tour.factura.p1.titulo",
            text_key="tour.factura.p1.texto",
            bubble_pos='bottom',
        ),
        TourStep(
            widget_getter=lambda: mw.factura_tab.cliente_combo,
            navigate=_navigate_to(mw, 1, 0),
            title_key="tour.factura.p2.titulo",
            text_key="tour.factura.p2.texto",
            bubble_pos='bottom',
        ),
        TourStep(
            widget_getter=lambda: _find_btn(mw.factura_tab, "Nuevo Cliente"),
            navigate=_navigate_to(mw, 1, 0),
            title_key="tour.factura.p3.titulo",
            text_key="tour.factura.p3.texto",
            bubble_pos='bottom',
        ),
        TourStep(
            widget_getter=lambda: mw.factura_tab.tabla_articulos,
            navigate=_navigate_to(mw, 1, 0),
            title_key="tour.factura.p4.titulo",
            text_key="tour.factura.p4.texto",
            bubble_pos='top',
        ),
        TourStep(
            widget_getter=lambda: mw.factura_tab.total_label,
            navigate=_navigate_to(mw, 1, 0),
            title_key="tour.factura.p5.titulo",
            text_key="tour.factura.p5.texto",
            bubble_pos='top',
        ),
    ]

    # ─── 3. Añadir producto ───────────────────────────────────────────────
    tours["producto"] = [
        TourStep(
            widget_getter=lambda: mw.nav_buttons[6],
            navigate=_navigate_to(mw, 6, 0),
            title_key="tour.producto.p1.titulo",
            text_key="tour.producto.p1.texto",
            bubble_pos='bottom',
        ),
        TourStep(
            widget_getter=lambda: _find_btn(mw.productos_tab, "Nuevo Producto"),
            navigate=_navigate_to(mw, 6, 0),
            title_key="tour.producto.p2.titulo",
            text_key="tour.producto.p2.texto",
            bubble_pos='bottom',
        ),
        TourStep(
            widget_getter=lambda: mw.productos_tab.search_input,
            navigate=_navigate_to(mw, 6, 0),
            title_key="tour.producto.p3.titulo",
            text_key="tour.producto.p3.texto",
            bubble_pos='bottom',
        ),
        TourStep(
            widget_getter=lambda: mw.productos_tab.tabla,
            navigate=_navigate_to(mw, 6, 0),
            title_key="tour.producto.p4.titulo",
            text_key="tour.producto.p4.texto",
            bubble_pos='top',
        ),
    ]

    # ─── 4. Crear reparación ──────────────────────────────────────────────
    tours["reparacion"] = [
        TourStep(
            widget_getter=lambda: mw.nav_buttons[4],
            navigate=_navigate_to(mw, 4, 0),
            title_key="tour.reparacion.p1.titulo",
            text_key="tour.reparacion.p1.texto",
            bubble_pos='bottom',
        ),
        TourStep(
            widget_getter=lambda: mw.reparaciones_nueva_tab.cliente_combo,
            navigate=_navigate_to(mw, 4, 0),
            title_key="tour.reparacion.p2.titulo",
            text_key="tour.reparacion.p2.texto",
            bubble_pos='bottom',
        ),
        TourStep(
            widget_getter=lambda: _find_btn(mw.reparaciones_nueva_tab, "Nuevo Cliente"),
            navigate=_navigate_to(mw, 4, 0),
            title_key="tour.reparacion.p3.titulo",
            text_key="tour.reparacion.p3.texto",
            bubble_pos='bottom',
        ),
        TourStep(
            widget_getter=lambda: _find_btn(mw.reparaciones_nueva_tab, "Añadir Dispositivo"),
            navigate=_navigate_to(mw, 4, 0),
            title_key="tour.reparacion.p4.titulo",
            text_key="tour.reparacion.p4.texto",
            bubble_pos='bottom',
        ),
        TourStep(
            widget_getter=lambda: _find_btn(mw.reparaciones_nueva_tab, "Guardar"),
            navigate=_navigate_to(mw, 4, 0),
            title_key="tour.reparacion.p5.titulo",
            text_key="tour.reparacion.p5.texto",
            bubble_pos='top',
        ),
    ]

    # ─── 5. Registrar compra ──────────────────────────────────────────────
    tours["compra"] = [
        TourStep(
            widget_getter=lambda: mw.nav_buttons[2],
            navigate=_navigate_to(mw, 2, 0),
            title_key="tour.compra.p1.titulo",
            text_key="tour.compra.p1.texto",
            bubble_pos='bottom',
        ),
        TourStep(
            widget_getter=lambda: mw.compras_nueva_tab.cliente_combo,
            navigate=_navigate_to(mw, 2, 0),
            title_key="tour.compra.p2.titulo",
            text_key="tour.compra.p2.texto",
            bubble_pos='bottom',
        ),
        TourStep(
            widget_getter=lambda: _find_btn(mw.compras_nueva_tab, "Nuevo Cliente"),
            navigate=_navigate_to(mw, 2, 0),
            title_key="tour.compra.p3.titulo",
            text_key="tour.compra.p3.texto",
            bubble_pos='bottom',
        ),
        TourStep(
            widget_getter=lambda: mw.compras_nueva_tab.tabla_productos,
            navigate=_navigate_to(mw, 2, 0),
            title_key="tour.compra.p4.titulo",
            text_key="tour.compra.p4.texto",
            bubble_pos='top',
        ),
        TourStep(
            widget_getter=lambda: _find_btn(mw.compras_nueva_tab, "Guardar"),
            navigate=_navigate_to(mw, 2, 0),
            title_key="tour.compra.p5.titulo",
            text_key="tour.compra.p5.texto",
            bubble_pos='top',
        ),
    ]

    # ─── 6. Venta TPV ─────────────────────────────────────────────────────
    tours["tpv"] = [
        TourStep(
            widget_getter=lambda: mw.nav_buttons[5],
            navigate=_navigate_to(mw, 5, 0),
            title_key="tour.tpv.p1.titulo",
            text_key="tour.tpv.p1.texto",
            bubble_pos='bottom',
        ),
        TourStep(
            widget_getter=lambda: mw.caja_tpv_tab.ean_input,
            navigate=_navigate_to(mw, 5, 0),
            title_key="tour.tpv.p2.titulo",
            text_key="tour.tpv.p2.texto",
            bubble_pos='bottom',
        ),
        TourStep(
            widget_getter=lambda: mw.caja_tpv_tab.tabla_carrito,
            navigate=_navigate_to(mw, 5, 0),
            title_key="tour.tpv.p3.titulo",
            text_key="tour.tpv.p3.texto",
            bubble_pos='top',
        ),
        TourStep(
            widget_getter=lambda: _find_btn(mw.caja_tpv_tab, "= (F5)"),
            navigate=_navigate_to(mw, 5, 0),
            title_key="tour.tpv.p4.titulo",
            text_key="tour.tpv.p4.texto",
            bubble_pos='left',
        ),
    ]

    # ─── 7. Abrir/cerrar caja ─────────────────────────────────────────────
    tours["caja"] = [
        TourStep(
            widget_getter=lambda: mw.nav_buttons[5],
            navigate=_navigate_to(mw, 5, 2),
            title_key="tour.caja.p1.titulo",
            text_key="tour.caja.p1.texto",
            bubble_pos='bottom',
        ),
        TourStep(
            widget_getter=lambda: mw.caja_movimientos_tab.btn_abrir_caja,
            navigate=_navigate_to(mw, 5, 2),
            title_key="tour.caja.p2.titulo",
            text_key="tour.caja.p2.texto",
            bubble_pos='bottom',
        ),
        TourStep(
            widget_getter=lambda: mw.stacked_widget.widget(5).findChild(QTabWidget),
            navigate=_navigate_to(mw, 5, 4),
            title_key="tour.caja.p3.titulo",
            text_key="tour.caja.p3.texto",
            bubble_pos='bottom',
        ),
        TourStep(
            widget_getter=lambda: _find_btn(mw.caja_cierre_tab, "Cerrar Caja"),
            navigate=_navigate_to(mw, 5, 4),
            title_key="tour.caja.p4.titulo",
            text_key="tour.caja.p4.texto",
            bubble_pos='top',
        ),
    ]

    # ─── 8. Crear usuario + 2FA ───────────────────────────────────────────
    if hasattr(mw, 'configuracion_tab'):
        tours["usuario"] = [
            TourStep(
                widget_getter=lambda: mw.nav_buttons[7] if len(mw.nav_buttons) > 7 else mw.nav_buttons[-1],
                navigate=_navigate_to(mw, 7),
                title_key="tour.usuario.p1.titulo",
                text_key="tour.usuario.p1.texto",
                bubble_pos='bottom',
            ),
            TourStep(
                widget_getter=lambda: mw.configuracion_tab.tabs,
                navigate=lambda: (_navigate_to(mw, 7)(),
                                  mw.configuracion_tab.tabs.setCurrentIndex(3)),
                title_key="tour.usuario.p2.titulo",
                text_key="tour.usuario.p2.texto",
                bubble_pos='bottom',
            ),
            TourStep(
                widget_getter=lambda: _find_btn(mw.configuracion_tab.tab_usuarios, "Nuevo Usuario"),
                navigate=lambda: (_navigate_to(mw, 7)(),
                                  mw.configuracion_tab.tabs.setCurrentIndex(3)),
                title_key="tour.usuario.p3.titulo",
                text_key="tour.usuario.p3.texto",
                bubble_pos='bottom',
            ),
            TourStep(
                widget_getter=lambda: mw.configuracion_tab.tab_usuarios.tabla,
                navigate=lambda: (_navigate_to(mw, 7)(),
                                  mw.configuracion_tab.tabs.setCurrentIndex(3)),
                title_key="tour.usuario.p4.titulo",
                text_key="tour.usuario.p4.texto",
                bubble_pos='top',
            ),
            TourStep(
                widget_getter=lambda: _get_2fa_btn(mw.configuracion_tab.tab_usuarios),
                navigate=lambda: (_navigate_to(mw, 7)(),
                                  mw.configuracion_tab.tabs.setCurrentIndex(3)),
                title_key="tour.usuario.p5.titulo",
                text_key="tour.usuario.p5.texto",
                bubble_pos='left',
            ),
            TourStep(
                widget_getter=lambda: mw.configuracion_tab.tabs,
                navigate=lambda: (_navigate_to(mw, 7)(),
                                  mw.configuracion_tab.tabs.setCurrentIndex(2)),
                title_key="tour.usuario.p6.titulo",
                text_key="tour.usuario.p6.texto",
                bubble_pos='bottom',
            ),
        ]

        # ─── 9. Configurar impresoras ──────────────────────────────────────
        tours["impresoras"] = [
            TourStep(
                widget_getter=lambda: mw.nav_buttons[7] if len(mw.nav_buttons) > 7 else mw.nav_buttons[-1],
                navigate=_navigate_to(mw, 7),
                title_key="tour.impresoras.p1.titulo",
                text_key="tour.impresoras.p1.texto",
                bubble_pos='bottom',
            ),
            TourStep(
                widget_getter=lambda: mw.configuracion_tab.tabs,
                navigate=lambda: (_navigate_to(mw, 7)(),
                                  mw.configuracion_tab.tabs.setCurrentIndex(1)),
                title_key="tour.impresoras.p2.titulo",
                text_key="tour.impresoras.p2.texto",
                bubble_pos='bottom',
            ),
            TourStep(
                widget_getter=lambda: _find_btn(mw.configuracion_tab.tab_impresoras, "Guardar"),
                navigate=lambda: (_navigate_to(mw, 7)(),
                                  mw.configuracion_tab.tabs.setCurrentIndex(1)),
                title_key="tour.impresoras.p3.titulo",
                text_key="tour.impresoras.p3.texto",
                bubble_pos='top',
            ),
        ]

    return tours
