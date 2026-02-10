"""
Utilidades para impresión física de documentos
Sistema de impresión directa con monitoreo en tiempo real
Soporta 3 tipos de impresora: general (A4), tickets (térmica), etiquetas
"""
import sqlite3
import os
import platform
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal
from app.utils.logger import logger


# Tipos de impresora disponibles
PRINTER_GENERAL = 'printer_general'    # Facturas, Contratos, Órdenes SAT
PRINTER_TICKET = 'printer_ticket'      # Tickets de venta
PRINTER_LABELS = 'printer_labels'      # Etiquetas/Pegatinas


def imprimir_pdf(pdf_path, db, parent_widget=None, tipo_impresora=PRINTER_GENERAL, delete_after=True):
    """
    Imprime un PDF mostrando el progreso en tiempo real.

    Args:
        pdf_path: Ruta al archivo PDF
        db: Conexión a la base de datos
        parent_widget: Widget padre para diálogos
        tipo_impresora: PRINTER_GENERAL, PRINTER_TICKET o PRINTER_LABELS
        delete_after: Si True, borra el archivo PDF después de imprimir

    Returns:
        bool: True si se inició la impresión correctamente
    """
    if not pdf_path or not os.path.exists(pdf_path):
        if parent_widget:
            QMessageBox.warning(parent_widget, "Error", "El archivo PDF no existe")
        return False

    # Obtener impresora configurada según el tipo
    printer_name = None
    duplex_enabled = False
    try:
        res = db.fetch_one("SELECT valor FROM configuracion WHERE clave = ?", (tipo_impresora,))
        if res and res['valor'] and "---" not in res['valor']:
            printer_name = res['valor']

        # Obtener duplex
        if tipo_impresora == PRINTER_GENERAL:
            duplex_res = db.fetch_one("SELECT valor FROM configuracion WHERE clave = 'printer_duplex'")
            if duplex_res and duplex_res['valor'] == '1':
                duplex_enabled = True
    except (sqlite3.Error, OSError, ValueError) as e:
        logger.error(f"Error leyendo configuración: {e}")

    if not printer_name:
        tipo_nombre = {
            PRINTER_GENERAL: "General (A4)",
            PRINTER_TICKET: "Tickets",
            PRINTER_LABELS: "Etiquetas"
        }.get(tipo_impresora, tipo_impresora)

        if parent_widget:
            QMessageBox.warning(parent_widget, "Sin Impresora",
                f"No hay impresora '{tipo_nombre}' configurada.\n"
                "Ve a Ajustes > Impresoras para configurarla.")
        return False

    # Usar el nuevo diálogo de progreso unificado
    from app.ui.print_progress_dialog import PrintProgressDialog

    es_ticket = (tipo_impresora == PRINTER_TICKET)

    def do_print():
        """Ejecuta la impresión y muestra el diálogo de progreso"""
        dialog = PrintProgressDialog(parent_widget, "Imprimiendo Documento")
        dialog.set_stage(dialog.STAGE_PREPARING, "Preparando documento...")

        # Función para manejar el resultado
        def on_success():
            # Borrar archivo temporal
            if delete_after and pdf_path and os.path.exists(pdf_path):
                try:
                    os.remove(pdf_path)
                    logger.info(f"Archivo temporal borrado: {pdf_path}")
                except (sqlite3.Error, OSError, ValueError) as e:
                    logger.warning(f"No se pudo borrar archivo: {e}")

        def on_failed(result):
            if result == "RETRY":
                # Reintentar impresión
                do_print()
            elif result == "CANCEL":
                # Cancelar - borrar archivo
                if delete_after and pdf_path and os.path.exists(pdf_path):
                    try:
                        os.remove(pdf_path)
                    except (sqlite3.Error, OSError, ValueError):
                        pass

        dialog.print_success.connect(on_success)
        dialog.print_failed.connect(on_failed)

        # Ejecutar impresión antes de mostrar diálogo
        dialog.set_stage(dialog.STAGE_SENDING, "Enviando a impresora...")

        try:
            if platform.system() == 'Windows':
                result = _imprimir_windows(pdf_path, printer_name, duplex_enabled, es_ticket)

                if result[0]:  # Éxito
                    # Iniciar monitoreo del trabajo
                    dialog.start_monitoring(result[1], result[2], pdf_path)
                else:
                    dialog._show_error("Error al enviar el documento a la impresora")
            else:
                # Linux/Mac
                import subprocess
                ret = subprocess.call(['lp', '-d', printer_name, pdf_path])
                if ret == 0:
                    dialog.set_stage(dialog.STAGE_COMPLETED, "")
                    dialog._show_success()
                else:
                    dialog._show_error("Error al enviar a la impresora")

        except (sqlite3.Error, OSError, ValueError) as e:
            dialog._show_error(f"Error: {str(e)}")

        # Mostrar diálogo y bloquear hasta que termine
        dialog.exec_()

    # Ejecutar
    do_print()
    return True


def _imprimir_windows(pdf_path, printer_name, duplex=False, es_ticket=False):
    """
    Impresión directa en Windows usando PyMuPDF + win32print

    Returns:
        tuple: (success, printer_name, job_id)
    """
    try:
        import fitz  # PyMuPDF
        import win32print
        import win32ui
        from PIL import Image, ImageWin
    except ImportError as e:
        logger.error(f"Faltan librerías: {e}")
        return (False, None, None)

    doc = None
    hdc = None
    hPrinter = None
    original_devmode = None
    job_id = None

    try:
        # 1. Abrir el PDF
        doc = fitz.open(pdf_path)
        num_pages = len(doc)

        if num_pages == 0:
            raise Exception("El PDF no tiene páginas")

        # 2. Si duplex está habilitado, configurar la impresora temporalmente
        if duplex:
            try:
                hPrinter = win32print.OpenPrinter(printer_name)
                printer_info = win32print.GetPrinter(hPrinter, 2)
                original_devmode = printer_info['pDevMode']

                devmode = original_devmode
                DM_DUPLEX = 0x00001000
                DMDUP_VERTICAL = 2

                if hasattr(devmode, 'Duplex'):
                    devmode.Duplex = DMDUP_VERTICAL
                    devmode.Fields = devmode.Fields | DM_DUPLEX
                    printer_info['pDevMode'] = devmode
                    win32print.SetPrinter(hPrinter, 2, printer_info, 0)
                    logger.info("Impresora configurada para doble cara")

            except (sqlite3.Error, OSError, ValueError) as e:
                logger.warning(f"No se pudo configurar duplex: {e}")
                if hPrinter:
                    win32print.ClosePrinter(hPrinter)
                    hPrinter = None

        # 3. Crear contexto de dispositivo para la impresora
        hdc = win32ui.CreateDC()
        hdc.CreatePrinterDC(printer_name)

        # Obtener dimensiones de la página de la impresora (en píxeles)
        printable_width = hdc.GetDeviceCaps(8)   # HORZRES
        printable_height = hdc.GetDeviceCaps(10)  # VERTRES

        # Obtener DPI de la impresora
        printer_dpi_x = hdc.GetDeviceCaps(88)  # LOGPIXELSX
        printer_dpi_y = hdc.GetDeviceCaps(90)  # LOGPIXELSY

        # 4. Iniciar trabajo de impresión (StartDoc devuelve el job_id)
        job_id = hdc.StartDoc(os.path.basename(pdf_path))
        logger.info(f"Trabajo iniciado con ID: {job_id}")

        # 5. Renderizar e imprimir cada página
        for page_num in range(num_pages):
            page = doc.load_page(page_num)

            # Obtener tamaño del PDF en puntos
            pdf_width_pts = page.rect.width
            pdf_height_pts = page.rect.height

            # Calcular tamaño físico del PDF en pulgadas
            pdf_width_inches = pdf_width_pts / 72.0
            pdf_height_inches = pdf_height_pts / 72.0

            # Calcular tamaño en píxeles de impresora
            target_width_px = int(pdf_width_inches * printer_dpi_x)
            target_height_px = int(pdf_height_inches * printer_dpi_y)

            # Renderizar el PDF a alta resolución
            zoom = printer_dpi_x / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            # Convertir a imagen PIL
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Redimensionar a tamaño exacto si es necesario
            img_width, img_height = img.size
            if img_width != target_width_px or img_height != target_height_px:
                img = img.resize((target_width_px, target_height_px), Image.Resampling.LANCZOS)

            # Si el contenido es más grande que el papel, escalar hacia abajo
            new_width = target_width_px
            new_height = target_height_px

            if new_width > printable_width or new_height > printable_height:
                scale_x = printable_width / new_width
                scale_y = printable_height / new_height
                scale = min(scale_x, scale_y)
                new_width = int(new_width * scale)
                new_height = int(new_height * scale)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Posicionar en la página
            x_pos = (printable_width - new_width) // 2

            if es_ticket:
                y_pos = 0  # Tickets empiezan desde arriba
            else:
                y_pos = (printable_height - new_height) // 2

            # Imprimir página
            hdc.StartPage()
            dib = ImageWin.Dib(img)
            dib.draw(hdc.GetHandleOutput(), (x_pos, y_pos, x_pos + new_width, y_pos + new_height))
            hdc.EndPage()

        # 6. Finalizar
        hdc.EndDoc()
        logger.info("Documento enviado correctamente")

        return (True, printer_name, job_id)

    except (sqlite3.Error, OSError, ValueError) as e:
        logger.error(f"Error impresión: {e}", exc_info=True)
        return (False, None, None)

    finally:
        # Restaurar configuración original de la impresora
        if hPrinter and original_devmode and duplex:
            try:
                printer_info = win32print.GetPrinter(hPrinter, 2)
                printer_info['pDevMode'] = original_devmode
                win32print.SetPrinter(hPrinter, 2, printer_info, 0)
            except (sqlite3.Error, OSError, ValueError):
                pass

        # Cerrar recursos
        if hPrinter:
            try:
                win32print.ClosePrinter(hPrinter)
            except (sqlite3.Error, OSError, ValueError):
                pass
        if doc:
            try:
                doc.close()
            except (sqlite3.Error, OSError, ValueError):
                pass
        if hdc:
            try:
                hdc.DeleteDC()
            except (sqlite3.Error, OSError, ValueError):
                pass


def abrir_archivo(path):
    """Abre un archivo con el visor predeterminado del sistema"""
    try:
        if platform.system() == 'Windows':
            os.startfile(path)
        elif platform.system() == 'Darwin':
            import subprocess
            subprocess.call(['open', path])
        else:
            import subprocess
            subprocess.call(['xdg-open', path])
    except (sqlite3.Error, OSError, ValueError) as e:
        logger.error(f"Error abriendo archivo: {e}")


# === Funciones de conveniencia para cada tipo ===

def imprimir_factura(pdf_path, db, parent_widget=None):
    """Imprime una factura usando la impresora General (A4)"""
    return imprimir_pdf(pdf_path, db, parent_widget, PRINTER_GENERAL)


def imprimir_contrato(pdf_path, db, parent_widget=None):
    """Imprime un contrato usando la impresora General (A4)"""
    return imprimir_pdf(pdf_path, db, parent_widget, PRINTER_GENERAL)


def imprimir_orden_reparacion(pdf_path, db, parent_widget=None):
    """Imprime una orden SAT usando la impresora General (A4)"""
    return imprimir_pdf(pdf_path, db, parent_widget, PRINTER_GENERAL)


def imprimir_ticket(pdf_path, db, parent_widget=None):
    """Imprime un ticket usando la impresora de Tickets (Térmica)"""
    return imprimir_pdf(pdf_path, db, parent_widget, PRINTER_TICKET)


def imprimir_etiqueta(pdf_path, db, parent_widget=None):
    """Imprime una etiqueta usando la impresora de Etiquetas"""
    return imprimir_pdf(pdf_path, db, parent_widget, PRINTER_LABELS)
