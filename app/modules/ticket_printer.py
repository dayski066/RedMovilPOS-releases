"""
Módulo para generar e imprimir tickets para impresoras térmicas POS58
Ancho: 58mm (aprox. 32-48 caracteres por línea)
"""
import sqlite3
from datetime import datetime
import subprocess
from app.utils.logger import logger

# Importación opcional de python-escpos (solo si está instalado)
try:
    from escpos.printer import Win32Raw, Usb, Network, File
    from escpos.exceptions import Error as EscposError
    ESCPOS_AVAILABLE = True
except ImportError:
    ESCPOS_AVAILABLE = False
    EscposError = Exception


class TicketPrinter:
    """Gestor de impresión de tickets para impresoras térmicas"""

    def __init__(self, db):
        self.db = db
        self.ancho = 42  # Caracteres por línea para POS58 (58mm)

    def obtener_datos_establecimiento(self, establecimiento_id=None):
        """Obtiene los datos del establecimiento desde la BD"""
        datos = {
            'nombre': 'ESTABLECIMIENTO',
            'nif': '',
            'direccion': '',
            'telefono': '',
            'logo_path': ''
        }

        try:
            # Si se proporciona un establecimiento_id específico, usarlo
            if establecimiento_id:
                establecimiento = self.db.fetch_one(
                    "SELECT * FROM establecimientos WHERE id = ? AND activo = 1",
                    (establecimiento_id,)
                )
            else:
                # Obtener el primer establecimiento activo
                establecimiento = self.db.fetch_one(
                    "SELECT * FROM establecimientos WHERE activo = 1 ORDER BY id LIMIT 1"
                )

            if establecimiento:
                datos['nombre'] = establecimiento.get('nombre') or 'ESTABLECIMIENTO'
                datos['nif'] = establecimiento.get('nif') or ''
                datos['direccion'] = establecimiento.get('direccion') or ''
                datos['telefono'] = establecimiento.get('telefono') or ''
                datos['logo_path'] = establecimiento.get('logo_path') or ''

        except (sqlite3.Error, OSError, ValueError) as e:
            logger.error(f"Error obteniendo datos de establecimiento: {e}")

        return datos

    def centrar_texto(self, texto):
        """Centra un texto en el ancho del ticket"""
        espacios = (self.ancho - len(texto)) // 2
        return ' ' * espacios + texto

    def linea_divisor(self, caracter='-'):
        """Genera una línea divisoria"""
        return caracter * self.ancho

    def formatear_linea_item(self, cantidad, nombre, precio):
        """Formatea una línea de producto: cantidad + nombre + precio"""
        # Formato: "2x Producto...            12.50"
        cant_str = f"{cantidad}x"
        precio_str = f"{precio:.2f}"

        # Espacio disponible para el nombre
        espacio_nombre = self.ancho - len(cant_str) - len(precio_str) - 2

        # Truncar nombre si es necesario
        if len(nombre) > espacio_nombre:
            nombre = nombre[:espacio_nombre-3] + '...'

        # Rellenar con espacios
        linea = cant_str + ' ' + nombre.ljust(espacio_nombre) + ' ' + precio_str
        return linea

    def formatear_linea_total(self, etiqueta, valor):
        """Formatea una línea de total: etiqueta a la izquierda, valor a la derecha"""
        valor_str = f"{valor:.2f} EUR" if isinstance(valor, (int, float)) else str(valor)
        espacios = self.ancho - len(etiqueta) - len(valor_str)
        return etiqueta + ' ' * espacios + valor_str

    def generar_contenido_ticket(self, venta):
        """
        Genera el contenido del ticket en texto plano
        venta: dict con los datos de la venta (incluye items)
        """
        lineas = []

        # === ENCABEZADO: Datos del establecimiento ===
        datos_est = self.obtener_datos_establecimiento()

        lineas.append('')
        lineas.append(self.centrar_texto(datos_est['nombre']))

        if datos_est['nif']:
            lineas.append(self.centrar_texto(f"NIF: {datos_est['nif']}"))

        if datos_est['direccion']:
            # Dividir dirección si es muy larga
            direccion = datos_est['direccion']
            if len(direccion) > self.ancho:
                # Dividir en múltiples líneas
                palabras = direccion.split()
                linea_actual = ''
                for palabra in palabras:
                    if len(linea_actual) + len(palabra) + 1 <= self.ancho:
                        linea_actual += ('' if not linea_actual else ' ') + palabra
                    else:
                        lineas.append(self.centrar_texto(linea_actual))
                        linea_actual = palabra
                if linea_actual:
                    lineas.append(self.centrar_texto(linea_actual))
            else:
                lineas.append(self.centrar_texto(direccion))

        if datos_est['telefono']:
            lineas.append(self.centrar_texto(f"Tel: {datos_est['telefono']}"))

        lineas.append(self.linea_divisor('='))

        # === INFORMACIÓN DE LA VENTA ===
        # Fecha y hora
        if 'fecha' in venta:
            fecha_venta = venta['fecha']
            if isinstance(fecha_venta, str):
                try:
                    fecha_obj = datetime.strptime(fecha_venta, '%Y-%m-%d %H:%M:%S')
                    fecha_formateada = fecha_obj.strftime('%d/%m/%Y %H:%M')
                except (ValueError, TypeError):
                    fecha_formateada = fecha_venta
            else:
                fecha_formateada = fecha_venta.strftime('%d/%m/%Y %H:%M') if hasattr(fecha_venta, 'strftime') else str(fecha_venta)
        else:
            fecha_formateada = datetime.now().strftime('%d/%m/%Y %H:%M')

        lineas.append(f"Fecha: {fecha_formateada}")

        # Número de ticket
        lineas.append(f"Ticket: {venta.get('numero_ticket', 'N/A')}")

        # Usuario (si existe)
        if venta.get('usuario_nombre'):
            lineas.append(f"Atendido por: {venta['usuario_nombre']}")

        lineas.append(self.linea_divisor('-'))

        # === LISTA DE ARTÍCULOS ===
        items = venta.get('items', [])

        for item in items:
            cantidad = item.get('cantidad', 1)
            nombre = item.get('nombre_producto', item.get('nombre', 'Producto'))
            # Precio total del item (precio unitario * cantidad ya viene en total_item)
            precio_total = item.get('total_item', item.get('precio_unitario', 0) * cantidad)

            lineas.append(self.formatear_linea_item(cantidad, nombre, precio_total))

        lineas.append(self.linea_divisor('-'))

        # === TOTALES ===
        subtotal = venta.get('subtotal', 0)
        iva = venta.get('iva', 0)
        total = venta.get('total', 0)

        lineas.append(self.formatear_linea_total('Subtotal:', subtotal))
        lineas.append(self.formatear_linea_total('IVA (21%):', iva))
        lineas.append(self.linea_divisor('='))
        lineas.append(self.formatear_linea_total('TOTAL:', total))
        lineas.append(self.linea_divisor('='))

        # === FORMA DE PAGO ===
        metodo_pago = venta.get('metodo_pago', 'efectivo').upper()
        lineas.append('')
        lineas.append(f"Forma de pago: {metodo_pago}")

        # Si es efectivo, mostrar cantidad recibida y cambio
        if venta.get('metodo_pago') == 'efectivo':
            cantidad_recibida = venta.get('cantidad_recibida')
            cambio_devuelto = venta.get('cambio_devuelto')

            if cantidad_recibida is not None:
                lineas.append(self.formatear_linea_total('Recibido:', cantidad_recibida))

            if cambio_devuelto is not None and cambio_devuelto > 0:
                lineas.append(self.formatear_linea_total('Cambio:', cambio_devuelto))

        lineas.append('')
        lineas.append(self.linea_divisor('-'))

        # === MENSAJE DE AGRADECIMIENTO ===
        lineas.append('')
        lineas.append(self.centrar_texto('¡Gracias por su compra!'))
        lineas.append(self.centrar_texto('Vuelva pronto'))
        lineas.append('')
        lineas.append('')
        lineas.append('')

        return '\n'.join(lineas)

    def imprimir_ticket_thermal(self, venta, printer_name=None):
        """
        Imprime el ticket en una impresora térmica usando python-escpos

        venta: dict con datos de la venta
        printer_name: nombre de la impresora Windows (para Win32Raw)
        """
        try:
            # Intentar conectar con impresora
            if printer_name:
                # Impresora Windows
                printer = Win32Raw(printer_name)
            else:
                # Intentar detectar impresora USB (requiere configuración)
                # Esto es un ejemplo, ajustar vendor_id y product_id según tu impresora
                raise Exception("No se ha especificado impresora")

            # Obtener contenido del ticket
            contenido = self.generar_contenido_ticket(venta)

            # Configurar impresora
            printer.set(align='left', font='a', width=1, height=1)

            # Procesar línea por línea para aplicar estilos
            lineas = contenido.split('\n')
            for i, linea in enumerate(lineas):
                # Detectar líneas especiales para aplicar estilos
                if '===' in linea or linea.startswith('TOTAL:'):
                    printer.set(bold=True, width=2, height=2)
                    printer.text(linea + '\n')
                    printer.set(bold=False, width=1, height=1)
                elif 'Gracias por su compra' in linea or datos_est.get('nombre', '') in linea:
                    printer.set(bold=True)
                    printer.text(linea + '\n')
                    printer.set(bold=False)
                else:
                    printer.text(linea + '\n')

            # Cortar papel
            printer.cut()

            # Cerrar conexión
            printer.close()

            return True, "Ticket impreso correctamente"

        except EscposError as e:
            return False, f"Error de impresora ESC/POS: {str(e)}"
        except (sqlite3.Error, OSError, ValueError) as e:
            return False, f"Error al imprimir: {str(e)}"

    def guardar_ticket_txt(self, venta, ruta_archivo=None):
        """
        Guarda el ticket como archivo de texto
        Útil para previsualizar o enviar por email
        """
        try:
            import os

            contenido = self.generar_contenido_ticket(venta)

            if not ruta_archivo:
                # Generar nombre de archivo con número de ticket
                ticket_num = venta.get('numero_ticket', 'TICKET').replace('/', '_')
                ruta_archivo = f"tickets/{ticket_num}.txt"

            # Crear directorio si no existe
            directorio = os.path.dirname(ruta_archivo)
            if directorio:
                os.makedirs(directorio, exist_ok=True)
            else:
                # Si no hay directorio en la ruta, usar directorio actual
                os.makedirs('.', exist_ok=True)

            # Guardar con codificación UTF-8
            with open(ruta_archivo, 'w', encoding='utf-8') as f:
                f.write(contenido)

            return True, ruta_archivo

        except (sqlite3.Error, OSError, ValueError) as e:
            return False, f"Error al guardar ticket: {str(e)}"

    def imprimir_a_impresora_windows(self, venta, printer_name):
        """
        Imprime el ticket directamente a una impresora Windows
        Envía el texto plano sin usar ESC/POS
        """
        try:
            import win32print
            import win32ui
            from PIL import Image, ImageDraw, ImageFont
            import tempfile
            import os

            # Generar contenido
            contenido = self.generar_contenido_ticket(venta)

            # Obtener datos del establecimiento para el logo
            datos_est = self.obtener_datos_establecimiento()
            logo_path = datos_est.get('logo_path', '')

            # Crear imagen del ticket
            # Fuente monoespaciada optimizada para POS58
            font = None
            font_size = 13  # Tamaño ajustado para 42 caracteres en POS58

            # Intentar cargar fuentes en orden de preferencia (más gruesas primero)
            fuentes_preferidas = [
                "consolab.ttf",   # Consolas Bold
                "courbd.ttf",     # Courier New Bold
                "lucon.ttf",      # Lucida Console
                "consola.ttf",    # Consolas Regular
                "cour.ttf",       # Courier New Regular
            ]

            for fuente in fuentes_preferidas:
                try:
                    font = ImageFont.truetype(fuente, font_size)
                    break
                except (sqlite3.Error, OSError, ValueError):
                    continue

            if font is None:
                font = ImageFont.load_default()

            # Calcular tamaño de imagen
            lineas = contenido.split('\n')
            line_height = 16  # Altura de línea para fuente 13
            img_width = 384  # Ancho para POS58 (58mm)

            # Cargar logo si existe
            logo_img = None
            logo_height = 0
            logo_size = 80  # Tamaño del logo en píxeles (ancho y alto)

            if logo_path and os.path.exists(logo_path):
                try:
                    logo_img = Image.open(logo_path)
                    # Redimensionar logo manteniendo proporción
                    logo_img.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)
                    # Convertir a RGB si es necesario (por si tiene transparencia)
                    if logo_img.mode in ('RGBA', 'P'):
                        background = Image.new('RGB', logo_img.size, (255, 255, 255))
                        if logo_img.mode == 'RGBA':
                            background.paste(logo_img, mask=logo_img.split()[3])
                        else:
                            background.paste(logo_img)
                        logo_img = background
                    logo_height = logo_img.size[1] + 10  # Altura del logo + margen
                except (sqlite3.Error, OSError, ValueError) as e:
                    logger.error(f"Error cargando logo: {e}")
                    logo_img = None

            # Altura total: logo + texto + márgenes
            img_height = logo_height + len(lineas) * line_height + 40

            # Crear imagen
            img = Image.new('RGB', (img_width, img_height), color='white')
            draw = ImageDraw.Draw(img)

            # Posición Y inicial
            y = 10

            # Dibujar logo centrado si existe
            if logo_img:
                logo_x = (img_width - logo_img.size[0]) // 2  # Centrar horizontalmente
                img.paste(logo_img, (logo_x, y))
                y += logo_height

            # Dibujar texto con color negro intenso
            for linea in lineas:
                draw.text((4, y), linea, fill='black', font=font)
                y += line_height

            # Guardar temporalmente
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.bmp')
            img.save(temp_file.name, 'BMP')
            temp_file.close()

            # Imprimir usando win32print
            from PIL import ImageWin

            hprinter = win32print.OpenPrinter(printer_name)
            bmp = None
            try:
                hdc = win32ui.CreateDC()
                hdc.CreatePrinterDC(printer_name)
                hdc.StartDoc('Ticket')
                hdc.StartPage()

                # Imprimir imagen
                bmp = Image.open(temp_file.name)
                dib = ImageWin.Dib(bmp)
                dib.draw(hdc.GetHandleOutput(), (0, 0, img_width, img_height))

                hdc.EndPage()
                hdc.EndDoc()
                hdc.DeleteDC()
            finally:
                win32print.ClosePrinter(hprinter)
                # Cerrar la imagen antes de eliminar el archivo
                if bmp:
                    bmp.close()
                # Eliminar archivo temporal
                try:
                    os.unlink(temp_file.name)
                except (sqlite3.Error, OSError, ValueError):
                    pass  # Ignorar si no se puede eliminar

            return True, "Ticket impreso correctamente"

        except ImportError:
            # Si no está disponible win32print, usar método alternativo
            return self._imprimir_texto_plano(venta, printer_name)
        except (sqlite3.Error, OSError, ValueError) as e:
            return False, f"Error al imprimir: {str(e)}"

    def _imprimir_texto_plano(self, venta, printer_name):
        """
        Imprime texto plano directamente a la impresora
        Método de respaldo si no hay librerías gráficas
        """
        try:
            import tempfile
            import os

            # Generar contenido
            contenido = self.generar_contenido_ticket(venta)

            # Guardar en archivo temporal
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='cp850')
            temp_file.write(contenido)
            temp_file.close()

            # Imprimir usando comando de Windows (sin ventana de consola)
            subprocess.run(
                f'print /D:"{printer_name}" "{temp_file.name}"',
                shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # Esperar un poco y eliminar archivo temporal
            import time
            time.sleep(2)
            os.unlink(temp_file.name)

            return True, "Ticket enviado a impresora"

        except (sqlite3.Error, OSError, ValueError) as e:
            return False, f"Error al imprimir: {str(e)}"
