"""
Generador de PDFs profesionales para facturas, contratos y órdenes
Diseño moderno sin tablas para datos de cabecera
Incluye códigos QR para órdenes de reparación
"""
import sqlite3
import os
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY
from reportlab.lib.utils import ImageReader
from config import COMPANY_INFO as DEFAULT_COMPANY_INFO, IVA_RATE, PDF_DIR
from app.utils.qr_generator import QRGenerator
from app.i18n import tr
from app.utils.logger import logger


class PDFGenerator:
    def __init__(self, db=None):
        self.page_width, self.page_height = A4
        self.margin = 1.5 * cm
        self.usable_width = self.page_width - 2 * self.margin
        self.db = db

        # Cargar datos de empresa desde BD o usar valores por defecto
        self.company_info = self._cargar_datos_empresa()

        # Generador de QR codes para reparaciones
        self.qr_generator = QRGenerator()

        # Crear directorios
        os.makedirs(PDF_DIR, exist_ok=True)
        os.makedirs(os.path.join('data', 'contratos'), exist_ok=True)
        os.makedirs(os.path.join('data', 'reparaciones'), exist_ok=True)
    
    def _cargar_datos_empresa(self, establecimiento_id=None):
        """Carga los datos del establecimiento desde la BD, o usa valores por defecto"""
        if not self.db:
            return DEFAULT_COMPANY_INFO

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

            # Si hay un establecimiento, usar sus datos
            if establecimiento:
                return {
                    'name': establecimiento.get('nombre') or '',
                    'nif': establecimiento.get('nif') or '',
                    'address': establecimiento.get('direccion') or '',
                    'city': '',  # No hay campo ciudad en establecimientos
                    'phone': establecimiento.get('telefono') or '',
                    'logo_path': establecimiento.get('logo_path') or ''
                }
            else:
                # Si no hay establecimiento en BD, usar los valores por defecto
                return DEFAULT_COMPANY_INFO

        except (sqlite3.Error, OSError, ValueError) as e:
            logger.error(f"Error cargando datos de establecimiento: {e}")
            return DEFAULT_COMPANY_INFO

    # ==================== TICKET DE VENTA (TÉRMICO) ====================
    def generar_ticket_venta(self, venta):
        """Genera un ticket de venta para impresora térmica POS 58mm"""
        try:
            # Configuración de tamaño (58mm ancho, alto dinámico)
            TICKET_WIDTH = 58 * mm
            MARGIN = 3 * mm  # Margen aumentado para mejor visibilidad
            CONTENT_WIDTH = TICKET_WIDTH - (2 * MARGIN)

            # Calcular alto estimado
            num_items = len(venta.get('items', []))
            height = 95 * mm + (num_items * 8 * mm)  # Más espacio para logo y texto más grande

            pdf_dir = os.path.join("data", "tickets")
            os.makedirs(pdf_dir, exist_ok=True)

            filename = self._get_unique_filename(
                os.path.join(pdf_dir, f"Ticket_{venta['numero_ticket']}.pdf")
            )

            c = canvas.Canvas(filename, pagesize=(TICKET_WIDTH, height))
            y = height - 5 * mm

            # --- LOGO (si existe) ---
            logo_path = self.company_info.get('logo_path', '')
            if logo_path and os.path.exists(logo_path):
                try:
                    logo_width = 18 * mm
                    logo_height = 18 * mm
                    x_logo = (TICKET_WIDTH - logo_width) / 2
                    c.drawImage(logo_path, x_logo, y - logo_height,
                               width=logo_width, height=logo_height,
                               preserveAspectRatio=True, mask='auto')
                    y -= (logo_height + 2 * mm)
                except (sqlite3.Error, OSError, ValueError):
                    pass  # Si falla el logo, continuar sin él

            # --- CABECERA ---
            c.setFillColor(colors.black)

            # Nombre Empresa (fuente más grande)
            c.setFont("Helvetica-Bold", 10)
            nombre_empresa = self.company_info['name'][:24]
            c.drawCentredString(TICKET_WIDTH / 2, y, nombre_empresa)
            y -= 4 * mm

            # Datos Empresa (fuente más legible)
            c.setFont("Helvetica", 7)
            if self.company_info['address']:
                direccion = self.company_info['address'][:28]
                c.drawCentredString(TICKET_WIDTH / 2, y, direccion)
                y -= 3 * mm
            if self.company_info['city']:
                ciudad = self.company_info['city'][:24]
                c.drawCentredString(TICKET_WIDTH / 2, y, ciudad)
                y -= 3 * mm

            nif_tel = f"NIF: {self.company_info['nif']}"
            c.drawCentredString(TICKET_WIDTH / 2, y, nif_tel)
            y -= 3 * mm
            c.drawCentredString(TICKET_WIDTH / 2, y, f"Tel: {self.company_info['phone']}")
            y -= 4 * mm

            # Separador
            c.setLineWidth(0.5)
            c.setDash(1, 2)
            c.line(MARGIN, y, TICKET_WIDTH - MARGIN, y)
            y -= 5 * mm

            # Datos Ticket
            c.setFont("Helvetica-Bold", 8)
            c.drawString(MARGIN, y, f"Ticket: {venta['numero_ticket']}")
            y -= 3 * mm
            c.setFont("Helvetica", 7)

            # Fecha (manejar str o datetime)
            fecha_val = venta['fecha']
            if isinstance(fecha_val, str):
                fecha_str = fecha_val
            else:
                fecha_str = fecha_val.strftime('%d/%m/%Y %H:%M')

            c.drawString(MARGIN, y, f"Fecha: {fecha_str}")

            if venta.get('usuario_nombre'):
                c.drawRightString(TICKET_WIDTH - MARGIN, y, f"{venta['usuario_nombre'][:12]}")
            y -= 4 * mm

            # Encabezado Items
            c.setDash([]) # Línea sólida
            c.line(MARGIN, y, TICKET_WIDTH - MARGIN, y)
            y -= 3 * mm
            c.setFont("Helvetica-Bold", 7)
            c.drawString(MARGIN, y, tr("Producto"))
            y -= 2 * mm
            c.line(MARGIN, y, TICKET_WIDTH - MARGIN, y)
            y -= 3 * mm

            # --- ITEMS ---
            c.setFont("Helvetica", 7)
            items = venta.get('items', [])

            for item in items:
                # Datos del item
                nombre = item.get('nombre_producto', item.get('nombre', 'Item'))
                cantidad = item.get('cantidad', 1)
                precio = item.get('precio_unitario', item.get('precio_unitario', item.get('precio', 0)))
                total_item = item.get('total_item', item.get('total_item', precio * cantidad))

                # Si el nombre es muy largo, cortarlo
                if len(nombre) > 22:
                    nombre = nombre[:22] + ".."

                # Línea 1: Nombre del artículo
                c.drawString(MARGIN, y, nombre)
                y -= 3 * mm

                # Línea 2: Cantidad x Precio = Total
                c.setFont("Helvetica", 7)
                detalle = f"{cantidad} x {precio:.2f} = {total_item:.2f}€"
                c.drawString(MARGIN, y, detalle)
                y -= 4 * mm

            # Separador
            y -= 2 * mm
            c.line(MARGIN, y, TICKET_WIDTH - MARGIN, y)
            y -= 4 * mm

            # --- TOTALES (etiqueta y valor más cerca) ---
            c.setFont("Helvetica", 7)
            try:
                subtotal = float(venta.get('subtotal', 0))
                iva = float(venta.get('iva', 0))
                total = float(venta.get('total', 0))
            except (ValueError, TypeError):
                subtotal = iva = total = 0.0

            # Base imponible
            c.drawString(MARGIN, y, f"Base:  {subtotal:.2f}€")
            y -= 3 * mm
            # IVA
            c.drawString(MARGIN, y, f"IVA:   {iva:.2f}€")
            y -= 4 * mm

            # TOTAL (destacado)
            c.setFont("Helvetica-Bold", 11)
            c.drawString(MARGIN, y, f"TOTAL: {total:.2f}€")
            y -= 5 * mm

            # --- PAGO ---
            c.setFont("Helvetica", 8)
            metodo = venta.get('metodo_pago', 'efectivo').upper()
            c.drawString(MARGIN, y, f"Pago: {metodo}")
            y -= 3 * mm

            # Si es efectivo y hay datos de entrega
            if metodo == 'EFECTIVO' and venta.get('cantidad_recibida'):
                try:
                    entregado = float(venta.get('cantidad_recibida', 0))
                    cambio = float(venta.get('cambio_devuelto', 0))
                except (ValueError, TypeError):
                    entregado = cambio = 0.0
                c.setFont("Helvetica", 7)
                c.drawString(MARGIN, y, f"Recibido: {entregado:.2f}€")
                y -= 3 * mm
                c.drawString(MARGIN, y, f"Cambio:   {cambio:.2f}€")
                y -= 3 * mm

            # --- PIE ---
            y -= 3 * mm
            c.setFont("Helvetica-Oblique", 7)
            c.drawCentredString(TICKET_WIDTH / 2, y, tr("Gracias"))
            y -= 3 * mm
            c.setFont("Helvetica", 6)
            c.drawCentredString(TICKET_WIDTH / 2, y, "IVA incluido")
            
            c.save()
            return filename
            
        except (sqlite3.Error, OSError, ValueError) as e:
            logger.error(f"Error generando ticket: {e}")
            return None

    def _get_unique_filename(self, filepath):
        """Genera un nombre de archivo único si el original está bloqueado"""
        if not os.path.exists(filepath):
            return filepath
        
        # Intentar abrir para verificar si está bloqueado
        try:
            with open(filepath, 'a'):
                pass
            return filepath
        except (PermissionError, IOError):
            # Archivo bloqueado, generar nombre único
            base, ext = os.path.splitext(filepath)
            counter = 1
            while True:
                new_path = f"{base}_{counter}{ext}"
                if not os.path.exists(new_path):
                    return new_path
                try:
                    with open(new_path, 'a'):
                        pass
                    return new_path
                except (PermissionError, IOError):
                    counter += 1
                    if counter > 100:  # Límite de seguridad
                        raise Exception("No se puede crear archivo PDF único")

    # ==================== FACTURA ====================
    def generar_factura(self, datos, factura_id):
        """Genera un PDF de factura profesional"""
        fecha_str = datos['fecha'].strftime('%Y-%m-%d') if hasattr(datos['fecha'], 'strftime') else str(datos['fecha'])
        cliente_str = datos['cliente']['nombre'].replace(' ', '_')[:20]
        filename = f"Factura_{datos['numero']}_{cliente_str}_{fecha_str}.pdf"
        base_filepath = os.path.join(PDF_DIR, filename)
        filepath = self._get_unique_filename(base_filepath)

        c = canvas.Canvas(filepath, pagesize=A4)
        y = self.page_height - self.margin

        # === CABECERA: Empresa (izq) + Factura (der) ===
        y = self._dibujar_cabecera_factura(c, datos, y)

        # === DATOS CLIENTE ===
        y = self._dibujar_datos_cliente(c, datos['cliente'], y)

        # === TABLA DE ARTÍCULOS ===
        y = self._dibujar_tabla_items(c, datos['items'], y)

        # === TOTALES ===
        y = self._dibujar_totales(c, datos['totales'], y)

        # === PIE DE PÁGINA ===
        self._dibujar_pie_pagina(c)

        c.save()
        return filepath

    def _dibujar_cabecera_factura(self, c, datos, y):
        """Cabecera con empresa a la izquierda y datos factura a la derecha"""
        # Marco de cabecera (sin fondo para impresión B/N)
        c.setStrokeColor(colors.HexColor('#1a252f'))
        c.setLineWidth(2)
        c.rect(0.5*cm, y - 3.5*cm, self.page_width - 1*cm, 3.5*cm, fill=False, stroke=True)
        
        # EMPRESA (Izquierda)
        c.setFillColor(colors.HexColor('#1a252f'))
        c.setFont("Helvetica-Bold", 16)
        c.drawString(self.margin, y - 1.2*cm, self.company_info['name'])
        
        c.setFont("Helvetica", 9)
        c.drawString(self.margin, y - 1.8*cm, f"NIF: {self.company_info['nif']}  |  Tel: {self.company_info['phone']}")
        c.drawString(self.margin, y - 2.3*cm, self.company_info['address'])
        c.drawString(self.margin, y - 2.8*cm, self.company_info['city'])
        
        # FACTURA (Derecha)
        c.setFont("Helvetica-Bold", 22)
        c.drawRightString(self.page_width - self.margin, y - 1.2*cm, tr("FACTURA"))
        
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(colors.HexColor('#3498db'))
        c.drawRightString(self.page_width - self.margin, y - 2*cm, f"Nº {datos['numero']}")
        
        c.setFillColor(colors.HexColor('#1a252f'))
        c.setFont("Helvetica", 10)
        fecha_display = datos['fecha'].strftime('%d/%m/%Y') if hasattr(datos['fecha'], 'strftime') else str(datos['fecha'])
        c.drawRightString(self.page_width - self.margin, y - 2.6*cm, f"{tr('Fecha')}: {fecha_display}")
        
        return y - 4.5*cm

    def _dibujar_datos_cliente(self, c, cliente, y):
        """Datos del cliente sin tabla, solo texto"""
        c.setFillColor(colors.HexColor('#2c3e50'))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(self.margin, y, tr("DATOS DEL CLIENTE"))
        
        c.setStrokeColor(colors.HexColor('#3498db'))
        c.setLineWidth(2)
        c.line(self.margin, y - 0.2*cm, self.margin + 4*cm, y - 0.2*cm)
        
        y -= 0.8*cm
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(self.margin, y, cliente['nombre'])

        y -= 0.5*cm
        c.setFont("Helvetica", 10)
        if cliente.get('nif'):
            c.drawString(self.margin, y, f"NIF/CIF: {cliente['nif']}")
            y -= 0.5*cm
        if cliente.get('direccion'):
            c.drawString(self.margin, y, cliente['direccion'])
            y -= 0.5*cm
            
        cp = cliente.get('codigo_postal', '')
        ciudad = cliente.get('ciudad', '')
        
        if cp:
            c.drawString(self.margin, y, f"C.P.: {cp}")
            y -= 0.5*cm
            
        if ciudad:
            c.drawString(self.margin, y, f"{ciudad}")
            y -= 0.5*cm
        if cliente.get('telefono'):
            c.drawString(self.margin, y, f"Tel: {cliente['telefono']}")
            y -= 0.5*cm
        
        return y - 0.8*cm

    def _dibujar_tabla_items(self, c, items, y):
        """Tabla de artículos con estilo moderno"""
        c.setFillColor(colors.HexColor('#2c3e50'))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(self.margin, y, tr("DETALLE DE ARTÍCULOS"))
        
        c.setStrokeColor(colors.HexColor('#3498db'))
        c.setLineWidth(2)
        c.line(self.margin, y - 0.2*cm, self.margin + 4.5*cm, y - 0.2*cm)
        
        y -= 0.8*cm
        
        # Cabecera de tabla
        col_widths = [8*cm, 3*cm, 1.5*cm, 2.5*cm, 2.5*cm]
        headers = [tr('Descripción'), 'IMEI/SN', tr('Cant.'), tr('P.Unit.'), tr('Total')]
        
        c.setFillColor(colors.HexColor('#34495e'))
        c.rect(self.margin, y - 0.6*cm, self.usable_width, 0.7*cm, fill=True, stroke=False)
        
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 9)
        x = self.margin + 0.2*cm
        for i, header in enumerate(headers):
            c.drawString(x, y - 0.4*cm, header)
            x += col_widths[i]
        
        y -= 0.8*cm
        
        # Filas de datos
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 9)
        
        for item in items:
            if y < 4*cm:  # Salto de página si es necesario
                c.showPage()
                y = self.page_height - 2*cm
            
            total_item = item['cantidad'] * item['precio']
            
            # Fondo alternado
            c.setFillColor(colors.HexColor('#f8f9fa'))
            c.rect(self.margin, y - 0.5*cm, self.usable_width, 0.7*cm, fill=True, stroke=False)
            
            c.setFillColor(colors.black)
            x = self.margin + 0.2*cm
            
            # Descripción (truncar si es muy larga)
            desc = item['descripcion'][:45] + '...' if len(item['descripcion']) > 45 else item['descripcion']
            c.drawString(x, y - 0.3*cm, desc)
            x += col_widths[0]
            
            c.drawString(x, y - 0.3*cm, item.get('imei', '-') or '-')
            x += col_widths[1]
            
            c.drawRightString(x + col_widths[2] - 0.3*cm, y - 0.3*cm, str(item['cantidad']))
            x += col_widths[2]
            
            c.drawRightString(x + col_widths[3] - 0.3*cm, y - 0.3*cm, f"{item['precio']:.2f} €")
            x += col_widths[3]
            
            c.drawRightString(x + col_widths[4] - 0.3*cm, y - 0.3*cm, f"{total_item:.2f} €")
            
            y -= 0.7*cm
        
        # Línea final
        c.setStrokeColor(colors.HexColor('#bdc3c7'))
        c.setLineWidth(1)
        c.line(self.margin, y, self.page_width - self.margin, y)
        
        return y - 0.5*cm

    def _dibujar_totales(self, c, totales, y):
        """Totales alineados a la derecha"""
        x_label = self.page_width - 6*cm
        x_value = self.page_width - self.margin
        
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.black)

        c.drawRightString(x_label, y, tr("Subtotal") + ":")
        c.drawRightString(x_value, y, f"{totales['subtotal']:.2f} €")

        y -= 0.5*cm
        c.drawRightString(x_label, y, f"{tr('IVA')} ({int(IVA_RATE*100)}%):")
        c.drawRightString(x_value, y, f"{totales['iva']:.2f} €")

        y -= 0.7*cm
        c.setFont("Helvetica-Bold", 14)
        c.drawRightString(x_label, y, tr("Total").upper() + ":")
        c.setFillColor(colors.HexColor('#27ae60'))
        c.drawRightString(x_value, y, f"{totales['total']:.2f} €")
        
        return y - 1*cm

    def _dibujar_pie_pagina(self, c):
        """Pie de página"""
        c.setFillColor(colors.grey)
        c.setFont("Helvetica", 8)
        c.drawCentredString(self.page_width / 2, 1.2*cm, f"{tr('Gracias por su confianza')}  •  {self.company_info['name']}")

    # ==================== CONTRATO DE COMPRA ====================
    def generar_contrato_compra(self, datos_compra):
        """Genera un contrato de compraventa legal y profesional"""
        pdf_dir = os.path.join("data", "contratos")
        os.makedirs(pdf_dir, exist_ok=True)

        numero = datos_compra.get('numero') or datos_compra.get('numero_compra')
        base_filename = os.path.join(pdf_dir, f"Contrato_Compra_{numero}.pdf")
        filename = self._get_unique_filename(base_filename)

        c = canvas.Canvas(filename, pagesize=A4)
        y = self.page_height - self.margin

        # === CABECERA ===
        y = self._dibujar_cabecera_contrato(c, numero, y)
        
        # === PARTES DEL CONTRATO ===
        y = self._dibujar_partes_contrato(c, datos_compra, y)
        
        # === DISPOSITIVOS ===
        y = self._dibujar_dispositivos_contrato(c, datos_compra, y)
        
        # === CLÁUSULAS LEGALES ===
        y = self._dibujar_clausulas_contrato(c, y)
        
        # === IMAGEN DNI (entre cláusulas y firmas) ===
        dni_imagen = datos_compra.get('dni_imagen')
        if dni_imagen and os.path.exists(dni_imagen):
            y = self._dibujar_imagen_dni(c, dni_imagen, y)
        
        # === FIRMAS ===
        self._dibujar_firmas(c, 4*cm)
        
        c.save()
        return filename
    
    def _dibujar_imagen_dni(self, c, imagen_path, y):
        """Dibuja la imagen del DNI escaneado"""
        try:
            from reportlab.lib.utils import ImageReader
            from PIL import Image as PILImage
            
            # Abrir imagen para obtener dimensiones
            img = PILImage.open(imagen_path)
            img_width, img_height = img.size
            
            # Calcular tamaño para DNI (formato tarjeta: ~8.5cm x 5.5cm)
            max_width = 8.5 * cm
            max_height = 5.5 * cm
            
            # Escalar manteniendo proporción
            ratio = min(max_width / img_width, max_height / img_height)
            display_width = img_width * ratio
            display_height = img_height * ratio
            
            # Verificar si hay espacio
            if y - display_height < 6*cm:  # Salto de página si no hay espacio
                c.showPage()
                y = self.page_height - 2*cm
            
            # Título
            c.setFillColor(colors.HexColor('#2c3e50'))
            c.setFont("Helvetica-Bold", 10)
            c.drawString(self.margin, y, tr("DOCUMENTO DE IDENTIDAD DEL VENDEDOR"))
            
            c.setStrokeColor(colors.HexColor('#9b59b6'))
            c.setLineWidth(2)
            c.line(self.margin, y - 0.2*cm, self.margin + 6.5*cm, y - 0.2*cm)
            
            y -= 0.8*cm
            
            # Dibujar marco
            c.setStrokeColor(colors.HexColor('#bdc3c7'))
            c.setLineWidth(1)
            c.rect(self.margin, y - display_height - 0.2*cm, display_width + 0.4*cm, display_height + 0.4*cm, fill=False)
            
            # Dibujar imagen
            c.drawImage(imagen_path, self.margin + 0.2*cm, y - display_height, 
                       width=display_width, height=display_height, preserveAspectRatio=True)
            
            y -= display_height + 0.8*cm
            
            return y
            
        except (sqlite3.Error, OSError, ValueError) as e:
            logger.error(f"Error dibujando imagen DNI: {e}")
            # Si hay error, solo mostrar texto indicativo
            c.setFillColor(colors.HexColor('#e74c3c'))
            c.setFont("Helvetica", 9)
            c.drawString(self.margin, y, f"[{tr('Error al cargar imagen del DNI')}: {str(e)}]")
            return y - 1*cm

    def _dibujar_cabecera_contrato(self, c, numero, y):
        """Cabecera del contrato"""
        # Marco de cabecera (sin fondo para impresión B/N)
        c.setStrokeColor(colors.HexColor('#2c3e50'))
        c.setLineWidth(2)
        c.rect(0.5*cm, y - 2.5*cm, self.page_width - 1*cm, 2.5*cm, fill=False, stroke=True)
        
        c.setFillColor(colors.HexColor('#2c3e50'))
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(self.page_width / 2, y - 1.2*cm, tr("CONTRATO DE COMPRAVENTA"))
        
        c.setFont("Helvetica", 11)
        c.drawCentredString(self.page_width / 2, y - 2*cm, f"Nº {numero}  •  {tr('Fecha')}: {datetime.now().strftime('%d/%m/%Y')}")
        
        return y - 3.5*cm

    def _dibujar_partes_contrato(self, c, datos, y):
        """Dibuja las partes del contrato lado a lado"""
        # Extraer datos del cliente/proveedor
        cliente_nombre = datos.get('cliente', {}).get('nombre') or datos.get('proveedor_nombre', '')
        cliente_nif = datos.get('cliente', {}).get('nif') or datos.get('proveedor_nif', '')
        cliente_dir = datos.get('cliente', {}).get('direccion') or datos.get('proveedor_direccion', '')
        cliente_cp = datos.get('cliente', {}).get('codigo_postal') or datos.get('proveedor_codigo_postal', '')
        cliente_ciudad = datos.get('cliente', {}).get('ciudad') or datos.get('proveedor_ciudad', '')
        cliente_tel = datos.get('cliente', {}).get('telefono') or datos.get('proveedor_telefono', '')
        
        # COMPRADOR (Establecimiento) - Izquierda
        c.setFillColor(colors.HexColor('#2c3e50'))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(self.margin, y, tr("PARTE COMPRADORA (Establecimiento)"))
        
        c.setStrokeColor(colors.HexColor('#3498db'))
        c.setLineWidth(2)
        c.line(self.margin, y - 0.2*cm, self.margin + 5.5*cm, y - 0.2*cm)
        
        y_temp = y - 0.8*cm
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(self.margin, y_temp, self.company_info['name'])
        c.setFont("Helvetica", 9)
        c.drawString(self.margin, y_temp - 0.5*cm, f"NIF: {self.company_info['nif']}")
        c.drawString(self.margin, y_temp - 1*cm, self.company_info['address'])
        c.drawString(self.margin, y_temp - 1.5*cm, f"Tel: {self.company_info['phone']}")
        
        # VENDEDOR (Cliente) - Derecha
        x_right = self.page_width / 2 + 0.5*cm
        c.setFillColor(colors.HexColor('#2c3e50'))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x_right, y, tr("PARTE VENDEDORA (Cliente)"))
        
        c.line(x_right, y - 0.2*cm, x_right + 4.5*cm, y - 0.2*cm)
        
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x_right, y_temp, cliente_nombre)
        c.setFont("Helvetica", 9)
        c.drawString(x_right, y_temp - 0.5*cm, f"DNI/NIF: {cliente_nif or 'N/A'}")
        
        # Dirección completa
        # Dirección completa
        dir_y_pos = y_temp - 1*cm
        
        c.drawString(x_right, dir_y_pos, cliente_dir or 'N/A')
        dir_y_pos -= 0.5*cm
        
        if cliente_cp:
            c.drawString(x_right, dir_y_pos, f"C.P.: {cliente_cp}")
            dir_y_pos -= 0.5*cm
            
        if cliente_ciudad:
            c.drawString(x_right, dir_y_pos, f"{cliente_ciudad}")
            dir_y_pos -= 0.5*cm
            
        c.drawString(x_right, dir_y_pos, f"Tel: {cliente_tel or 'N/A'}")
        
        return y - 3*cm

    def _dibujar_dispositivos_contrato(self, c, datos, y):
        """Lista de dispositivos comprados"""
        c.setFillColor(colors.HexColor('#2c3e50'))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(self.margin, y, tr("OBJETO DEL CONTRATO - DISPOSITIVOS"))
        
        c.setStrokeColor(colors.HexColor('#e74c3c'))
        c.setLineWidth(2)
        c.line(self.margin, y - 0.2*cm, self.margin + 6*cm, y - 0.2*cm)
        
        y -= 0.8*cm
        
        items = datos.get('items', [])
        total = 0
        
        for i, item in enumerate(items, 1):
            precio = item.get('precio_unitario') or item.get('precio', 0)
            cantidad = item.get('cantidad', 1)
            subtotal = item.get('total') or (precio * cantidad)
            total += subtotal
            
            c.setFont("Helvetica-Bold", 9)
            c.setFillColor(colors.HexColor('#2c3e50'))
            c.drawString(self.margin, y, f"{i}. {item['descripcion']}")
            
            c.setFont("Helvetica", 9)
            c.setFillColor(colors.black)
            y -= 0.45*cm
            
            detalles = []
            if item.get('imei'):
                detalles.append(f"IMEI/SN: {item['imei']}")
            if item.get('estado'):
                estados = {'nuevo': tr('Nuevo'), 'km0': 'KM0', 'usado': tr('Usado')}
                detalles.append(f"{tr('Estado')}: {estados.get(item['estado'], item['estado'])}")
            
            if detalles:
                c.drawString(self.margin + 0.5*cm, y, "  •  ".join(detalles))
                y -= 0.45*cm
            
            c.drawString(self.margin + 0.5*cm, y, f"{tr('Precio')}: {subtotal:.2f} €")
            y -= 0.6*cm
        
        # Total
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(colors.HexColor('#e74c3c'))
        c.drawRightString(self.page_width - self.margin, y, f"{tr('IMPORTE TOTAL')}: {total:.2f} €")
        
        return y - 1*cm

    def _dibujar_clausulas_contrato(self, c, y):
        """Cláusulas legales del contrato"""
        c.setFillColor(colors.HexColor('#2c3e50'))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(self.margin, y, tr("CLÁUSULAS Y CONDICIONES"))
        
        c.setStrokeColor(colors.HexColor('#27ae60'))
        c.setLineWidth(2)
        c.line(self.margin, y - 0.2*cm, self.margin + 4.5*cm, y - 0.2*cm)
        
        y -= 0.8*cm
        
        clausulas = [
            tr("1. PROPIEDAD: El vendedor declara ser el legítimo propietario de los dispositivos objeto de esta compraventa, garantizando que están libres de cargas, gravámenes y reclamaciones de terceros."),
            tr("2. ORIGEN LÍCITO: El vendedor garantiza que los dispositivos no proceden de robo, hurto, apropiación indebida ni ninguna otra actividad ilícita."),
            tr("3. IDENTIFICACIÓN: El vendedor acredita su identidad mediante documento oficial (DNI/NIE/Pasaporte) cuyo número consta en este contrato."),
            tr("4. IMEI/NÚMERO DE SERIE: Se hace constar el IMEI o número de serie de cada dispositivo como identificación única."),
            tr("5. ESTADO: Los dispositivos se entregan en el estado descrito, aceptado por ambas partes tras su verificación."),
            tr("6. PAGO: El comprador abona el importe total en este acto, sirviendo este documento como justificante de pago."),
            tr("7. RESPONSABILIDAD: El vendedor será responsable ante cualquier reclamación de terceros sobre la propiedad de los dispositivos."),
            tr("8. DATOS PERSONALES: Los datos serán tratados conforme al RGPD y la LOPDGDD, conservándose el tiempo legalmente establecido."),
            tr("9. JURISDICCIÓN: Para cualquier controversia, las partes se someten a los juzgados de la localidad del establecimiento.")
        ]
        
        c.setFont("Helvetica", 7.5)
        c.setFillColor(colors.HexColor('#34495e'))
        
        for clausula in clausulas:
            # Dividir texto largo en líneas
            words = clausula.split()
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + " " + word if current_line else word
                if c.stringWidth(test_line, "Helvetica", 7.5) < self.usable_width:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            
            for line in lines:
                if y < 5*cm:
                    c.showPage()
                    y = self.page_height - 2*cm
                c.drawString(self.margin, y, line)
                y -= 0.35*cm
            y -= 0.15*cm
        
        return y - 0.5*cm

    def _dibujar_firmas(self, c, y):
        """Zona de firmas"""
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.5)
        
        # Firma Vendedor (Izquierda)
        c.line(self.margin, y, self.margin + 6*cm, y)
        c.setFont("Helvetica", 9)
        c.drawString(self.margin, y - 0.4*cm, tr("Firma del VENDEDOR"))
        c.drawString(self.margin, y - 0.8*cm, "DNI: _______________")
        
        # Firma Comprador (Derecha)
        x_right = self.page_width - self.margin - 6*cm
        c.line(x_right, y, self.page_width - self.margin, y)
        c.drawString(x_right, y - 0.4*cm, f"{tr('Firma de')} {self.company_info['name'][:20]}")
        c.drawString(x_right, y - 0.8*cm, tr("Sello del establecimiento"))

    # ==================== ORDEN DE REPARACIÓN ====================
    def generar_orden_reparacion(self, datos):
        """Genera una Orden de Reparación (SAT) profesional de 2 páginas"""
        pdf_dir = os.path.join("data", "reparaciones")
        os.makedirs(pdf_dir, exist_ok=True)

        numero = datos.get('numero_orden') or datos.get('numero')
        base_filename = os.path.join(pdf_dir, f"Orden_SAT_{numero}.pdf")
        filename = self._get_unique_filename(base_filename)

        # Obtener nombre del establecimiento
        nombre_establecimiento = self.company_info.get('name', 'Establecimiento')

        c = canvas.Canvas(filename, pagesize=A4)
        y = self.page_height - self.margin

        # === PÁGINA 1: ORDEN DE REPARACIÓN ===
        # === CABECERA ===
        y = self._dibujar_cabecera_orden(c, numero, datos, y)

        # === DATOS CLIENTE Y TIENDA ===
        y = self._dibujar_partes_orden(c, datos, y)

        # === DISPOSITIVOS ===
        y = self._dibujar_dispositivos_orden(c, datos, y)

        # === CONDICIONES ===
        y = self._dibujar_condiciones_sat(c, y)

        # === FIRMAS ===
        self._dibujar_firmas_orden(c, 3.5*cm)

        # === PÁGINA 2: CONDICIONES LEGALES ===
        self._dibujar_condiciones_legales(c, nombre_establecimiento)

        c.save()
        return filename

    def _dibujar_cabecera_orden(self, c, numero, datos, y):
        """Cabecera de la orden con código QR"""
        # Altura aumentada para que el texto "Escanear QR" se vea completo
        header_height = 2.9*cm
        # Marco de cabecera (sin fondo para impresión B/N)
        c.setStrokeColor(colors.HexColor('#8e44ad'))
        c.setLineWidth(2)
        c.rect(0.5*cm, y - header_height, self.page_width - 1*cm, header_height, fill=False, stroke=True)

        # === CÓDIGO QR (esquina superior derecha) ===
        qr_size = 2.2*cm
        qr_x = self.page_width - self.margin - qr_size - 0.3*cm
        qr_y = y - 2.3*cm

        # Generar imagen QR
        try:
            qr_img = self.qr_generator.generar_imagen_qr(numero, size=200)

            # Convertir PIL Image a BytesIO para ReportLab
            qr_buffer = io.BytesIO()
            qr_img.save(qr_buffer, format='PNG')
            qr_buffer.seek(0)

            # Dibujar QR en el PDF
            c.drawImage(ImageReader(qr_buffer), qr_x, qr_y, width=qr_size, height=qr_size)

            # Etiqueta "Escanear" - ahora dentro del marco
            c.setFillColor(colors.HexColor('#8e44ad'))
            c.setFont("Helvetica", 7)
            c.drawCentredString(qr_x + qr_size/2, qr_y - 0.35*cm, tr("Escanear QR"))

        except (sqlite3.Error, OSError, ValueError) as e:
            logger.error(f"Error al generar QR: {e}")
            # Continuar sin QR si falla

        # === TÍTULO Y DATOS ===
        c.setFillColor(colors.HexColor('#8e44ad'))
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(self.page_width / 2, y - 1.2*cm, tr("ORDEN DE REPARACIÓN"))
 
        fecha = datos.get('fecha_entrada') or datos.get('fecha') or datetime.now()
        fecha_str = fecha.strftime('%d/%m/%Y') if hasattr(fecha, 'strftime') else str(fecha)
 
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(self.page_width / 2, y - 2*cm, f"Nº {numero}  •  {tr('Fecha')}: {fecha_str}")

        return y - header_height - 0.6*cm  # Ajustado al nuevo tamaño

    def _dibujar_partes_orden(self, c, datos, y):
        """Datos de tienda y cliente lado a lado"""
        # ESTABLECIMIENTO (Izquierda)
        c.setFillColor(colors.HexColor('#2c3e50'))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(self.margin, y, tr("SERVICIO TÉCNICO"))
        
        c.setStrokeColor(colors.HexColor('#8e44ad'))
        c.setLineWidth(2)
        c.line(self.margin, y - 0.2*cm, self.margin + 3.5*cm, y - 0.2*cm)
        
        y_temp = y - 0.7*cm
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(self.margin, y_temp, self.company_info['name'])
        c.setFont("Helvetica", 9)
        c.drawString(self.margin, y_temp - 0.45*cm, f"NIF: {self.company_info['nif']}")
        c.drawString(self.margin, y_temp - 0.9*cm, self.company_info['address'])
        c.drawString(self.margin, y_temp - 1.35*cm, f"Tel: {self.company_info['phone']}")
        
        # CLIENTE (Derecha)
        x_right = self.page_width / 2 + 0.5*cm
        c.setFillColor(colors.HexColor('#2c3e50'))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x_right, y, tr("CLIENTE"))
        
        c.line(x_right, y - 0.2*cm, x_right + 2*cm, y - 0.2*cm)
        
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x_right, y_temp, datos.get('cliente_nombre', 'N/A'))
        c.setFont("Helvetica", 9)
        c.drawString(x_right, y_temp - 0.45*cm, f"DNI/NIF: {datos.get('cliente_nif') or 'N/A'}")
        c.drawString(x_right, y_temp - 0.9*cm, f"Tel: {datos.get('cliente_telefono') or 'N/A'}")
        
        # Dirección
        cliente_dir = datos.get('cliente_direccion', '')
        cliente_cp = datos.get('cliente_codigo_postal', '')
        cliente_ciudad = datos.get('cliente_ciudad', '')
        if cliente_dir:
            c.drawString(x_right, y_temp - 1.35*cm, cliente_dir[:40])
            
            y_addr = y_temp - 1.8*cm
            if cliente_cp:
                c.drawString(x_right, y_addr, f"C.P.: {cliente_cp}")
                y_addr -= 0.45*cm
                
            if cliente_ciudad:
                c.drawString(x_right, y_addr, f"{cliente_ciudad}")
        
        return y - 2.8*cm

    def _dibujar_dispositivos_orden(self, c, datos, y):
        """Lista de dispositivos a reparar con averías detalladas"""
        c.setFillColor(colors.HexColor('#2c3e50'))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(self.margin, y, tr("DISPOSITIVOS A REPARAR"))

        c.setStrokeColor(colors.HexColor('#e67e22'))
        c.setLineWidth(2)
        c.line(self.margin, y - 0.2*cm, self.margin + 4.5*cm, y - 0.2*cm)

        y -= 0.8*cm

        items = datos.get('items', [])
        total_estimado = 0

        for i, item in enumerate(items, 1):
            disp = f"{item.get('marca_nombre', '')} {item.get('modelo_nombre', '')}".strip() or 'Dispositivo'

            # Dispositivo principal
            c.setFont("Helvetica-Bold", 10)
            c.setFillColor(colors.HexColor('#2c3e50'))
            c.drawString(self.margin, y, f"{tr('DISPOSITIVO')} {i}: {disp}")
            y -= 0.5*cm

            c.setFont("Helvetica", 9)
            c.setFillColor(colors.black)

            if item.get('imei'):
                c.drawString(self.margin + 0.5*cm, y, f"IMEI/SN: {item['imei']}")
                y -= 0.4*cm

            if item.get('patron_codigo'):
                c.drawString(self.margin + 0.5*cm, y, f"{tr('Patrón')}: {item['patron_codigo']}")
                y -= 0.4*cm

            # Averías del dispositivo
            averias = item.get('averias', [])
            if averias:
                y -= 0.2*cm
                subtotal_dispositivo = 0

                for j, averia in enumerate(averias, 1):
                    c.setFont("Helvetica-Bold", 9)
                    c.setFillColor(colors.HexColor('#e67e22'))
                    c.drawString(self.margin + 1*cm, y, f"• {tr('Avería')} {j}: {averia.get('descripcion_averia', '')}")
                    y -= 0.4*cm

                    c.setFont("Helvetica", 9)
                    c.setFillColor(colors.HexColor('#555555'))
                    c.drawString(self.margin + 1.5*cm, y, f"{tr('Solución')}: {averia.get('solucion', '')}")

                    precio_averia = float(averia.get('precio', 0))
                    subtotal_dispositivo += precio_averia
                    c.setFillColor(colors.HexColor('#27ae60'))
                    c.drawRightString(self.page_width - self.margin, y, f"{precio_averia:.2f} €")
                    y -= 0.5*cm

                # Subtotal del dispositivo
                c.setFont("Helvetica-Bold", 9)
                c.setFillColor(colors.HexColor('#2c3e50'))
                c.drawString(self.margin + 1*cm, y, tr("Subtotal dispositivo") + ":")
                c.setFillColor(colors.HexColor('#27ae60'))
                c.drawRightString(self.page_width - self.margin, y, f"{subtotal_dispositivo:.2f} €")
                total_estimado += subtotal_dispositivo
                y -= 0.6*cm
            else:
                # Si no hay averías, usar el formato antiguo
                precio = item.get('precio_estimado', 0)
                total_estimado += precio

                averia_texto = item.get('averia_texto') or item.get('averia', '')
                if averia_texto:
                    c.drawString(self.margin + 0.5*cm, y, f"{tr('Avería')}: {averia_texto}")
                    y -= 0.4*cm

                solucion_texto = item.get('solucion_texto')
                if solucion_texto:
                    c.drawString(self.margin + 0.5*cm, y, f"{tr('Solución')}: {solucion_texto}")
                    y -= 0.4*cm

                c.setFillColor(colors.HexColor('#27ae60'))
                c.drawRightString(self.page_width - self.margin, y, f"{precio:.2f} €")
                y -= 0.5*cm

            if item.get('notas'):
                c.setFont("Helvetica-Oblique", 8)
                c.setFillColor(colors.HexColor('#7f8c8d'))
                c.drawString(self.margin + 0.5*cm, y, f"{tr('Nota')}: {item['notas']}")
                y -= 0.4*cm

            y -= 0.3*cm

        # Total estimado general
        c.setStrokeColor(colors.HexColor('#8e44ad'))
        c.setLineWidth(1)
        c.line(self.margin, y, self.page_width - self.margin, y)
        y -= 0.5*cm

        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(colors.HexColor('#8e44ad'))
        c.drawString(self.margin, y, tr("TOTAL REPARACIÓN") + ":")
        c.drawRightString(self.page_width - self.margin, y, f"{total_estimado:.2f} €")

        return y - 1*cm

    def _dibujar_condiciones_sat(self, c, y):
        """Condiciones del servicio técnico"""
        c.setFillColor(colors.HexColor('#2c3e50'))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(self.margin, y, tr("CONDICIONES DEL SERVICIO TÉCNICO"))

        c.setStrokeColor(colors.HexColor('#3498db'))
        c.setLineWidth(2)
        c.line(self.margin, y - 0.2*cm, self.margin + 5.5*cm, y - 0.2*cm)

        y -= 0.7*cm

        condiciones = [
            tr("1. El cliente autoriza la revisión y reparación del/los dispositivo(s) descrito(s)."),
            tr("2. El presupuesto inicial es orientativo y puede variar tras diagnóstico completo."),
            tr("3. La empresa NO se responsabiliza de pérdida de datos. Se recomienda copia de seguridad."),
            tr("4. Las reparaciones tienen garantía de 3 meses sobre la misma avería reparada."),
            tr("5. Los dispositivos no recogidos en 3 meses desde el aviso pasarán a reciclaje."),
            tr("6. El diagnóstico es gratuito si se acepta la reparación, 15€ en caso contrario."),
            tr("7. Los precios no incluyen IVA salvo indicación expresa.")
        ]

        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor('#555555'))

        for cond in condiciones:
            c.drawString(self.margin, y, cond)
            y -= 0.4*cm

        # ADVERTENCIAS ADICIONALES
        y -= 0.3*cm
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor('#e74c3c'))
        c.drawString(self.margin, y, tr("ADVERTENCIAS IMPORTANTES") + ":")
        y -= 0.5*cm

        advertencias = [
            tr("• El fallo del terminal puede ocurrir debido a un problema de placa base, y aún cambiando"),
            tr("  la pantalla puede seguir persistiendo el problema."),
            tr("• Se informa que tras la reparación no se garantiza la impermeabilidad del dispositivo,"),
            tr("  incluso si el terminal reparado estuviera fabricado para poder estar en contacto con líquidos."),
            tr("• Se informa al cliente que para este tipo de reparación es posible que el dispositivo"),
            tr("  sea derivado a nuestro laboratorio.")
        ]

        c.setFont("Helvetica", 7.5)
        c.setFillColor(colors.HexColor('#555555'))

        for adv in advertencias:
            c.drawString(self.margin, y, adv)
            y -= 0.35*cm

        return y - 0.5*cm

    def _dibujar_condiciones_legales(self, c, nombre_establecimiento):
        """Dibuja la segunda página con condiciones legales completas"""
        c.showPage()  # Nueva página
        y = self.page_height - self.margin

        # Título
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(colors.HexColor('#2c3e50'))
        c.drawCentredString(self.page_width / 2, y, tr("CONDICIONES GENERALES DE LA CONTRATACIÓN"))
        y -= 0.8*cm

        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(colors.HexColor('#8e44ad'))
        c.drawCentredString(self.page_width / 2, y, nombre_establecimiento)
        y -= 1.2*cm

        # Contenido legal
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(colors.black)
        c.drawString(self.margin, y, tr("INFORMACIÓN OBLIGATORIA"))
        y -= 0.6*cm

        texto_legal = [
            (tr("1. Definición precisa de la prestación del servicio objeto del servicio (reparación, sustitución,"), False),
            (tr("venta de artículos consumibles y/o liberación)"), False),
            ("", False),
            (tr("2. Presupuesto previo: se informa de que el precio por el mero diagnóstico asciende a 35€ IVA incluido."), False),
            (tr("Solo se exonera al cliente del pago en caso de que el terminal no tenga reparación alguna."), False),
            ("", False),
            (tr("3. Presupuesto final: se informa de que el presupuesto final lo constituye el servicio concreto a realizar"), False),
            (tr("(sustitución de pieza, recuperación de datos, etc). El presupuesto dado tiene una validez de 35 días."), False),
            ("", False),
            (tr("4. Condiciones específicas de las reparaciones"), True),
            ("", False),
            (tr("> Sustitución de piezas"), True),
            (tr("La reparación de un terminal se realiza con recambios no originales. El cliente queda informado y autoriza"), False),
            (tr("a que la reparación del terminal se efectúe con recambios compatibles."), False),
            (tr("Las piezas sustituidas estarán a disposición del cliente en el momento de recogida del terminal. Una vez"), False),
            (tr("que el terminal haya sido recogido, las piezas sustituidas que no hayan sido solicitadas por el cliente"), False),
            (tr("se depositarán en un punto limpio."), False),
            ("", False),
            (tr("> Terminal sin diagnóstico evidente o mojado"), True),
            (tr("La reparación de un terminal sin diagnóstico evidente o mojado está dirigida a la recuperación de los datos."), False),
            (tr("En caso de que tras la reparación y posterior encendido del terminal dejasen de funcionar algunos de sus"), False),
            (tr("componentes (audio, micro, altavoz, etcétera) y éstos no tuvieren reparación alguna y por ello el cliente"), False),
            (tr("quisiera desistir de la reparación en su totalidad, es decir, que no quisiera tampoco la recuperación de"), False),
            (tr("los datos, tendrá que abonar 35€ en concepto de mano de obra."), False),
            (tr("En caso de que los componentes averiados, si tuvieran reparación, se informará al cliente del coste de la"), False),
            (tr("misma, teniendo que dar su consentimiento expreso para iniciar la reparación."), False),
            ("", False),
            (tr("> Reparación considerada de alto riesgo"), True),
            (tr("El cliente conoce el riesgo que supone la reparación o sustitución de la pieza señalada. La empresa no se"), False),
            (tr("hace responsable de cualquier daño que pudiera sufrir esta durante la reparación."), False),
            ("", False),
            (tr("5. Garantía del servicio: en cumplimiento con el RD 58/1988, la garantía del servicio prestado es de tres"), False),
            (tr("meses a partir de la entrega del terminal. Dicha garantía se entiende total y exclusivamente sobre la"), False),
            (tr("reparación efectuada, no pudiéndose reclamar nueva reparación con cargo a la garantía, cuando la avería,"), False),
            (tr("se produzca como consecuencia de un uso inadecuado del aparato, o por causas de fuerza mayor."), False),
        ]

        c.setFont("Helvetica", 7)
        for linea, es_negrita in texto_legal:
            if es_negrita:
                c.setFont("Helvetica-Bold", 7)
            else:
                c.setFont("Helvetica", 7)

            c.drawString(self.margin, y, linea)
            y -= 0.32*cm

            if y < 3*cm:  # Nueva página si no hay espacio
                c.showPage()
                y = self.page_height - self.margin

        # Continuar con más condiciones en nueva página si es necesario
        y -= 0.3*cm
        c.setFont("Helvetica", 7)

        texto_legal_2 = [
            (tr("La garantía dejará de tener validez en los siguientes casos:"), False),
            (tr("• El aparato reparado haya sido, total o parcialmente, abierto, montado, desmontado, manipulado y/o"), False),
            (tr("  reparado por otra persona ajena a esta empresa."), False),
            (tr("• El aparato reparado tenga signos de haber sido golpeado, aplastado o con cualquier signo de haber"), False),
            (tr("  sufrido un daño físico."), False),
            ("", False),
            (f"{nombre_establecimiento} {tr('no se hace responsable de la eventual pérdida de datos durante la reparación por lo que')}", False),
            (tr("dichas circunstancias no eximen al cliente del compromiso del pago adquirido."), False),
            (tr("Asimismo, se informa que tras la reparación no se garantiza la impermeabilidad del dispositivo, incluso si"), False),
            (tr("el móvil reparado estuviera fabricado para poder estar en contacto con líquidos. La empresa no se"), False),
            (tr("responsabilizará de la posible pérdida de garantía oficial como consecuencia de cualquier tipo de"), False),
            (tr("reparación en nuestro taller. Esta garantía solo podrá ser convalidada en el establecimiento donde fue reparado."), False),
            ("", False),
            (tr("6. Depósito y abandono de equipos:"), True),
            (tr("En cumplimiento con Ley 7/1996 de Ordenación del comercio minorista y el RD 58/1988 sobre 'Protección de"), False),
            (tr("los derechos del consumidor en el servicio de reparación de aparatos de uso doméstico', se informa de que"), False),
            (tr("todo usuario queda obligado a satisfacer el pago correspondiente a los gastos de almacenamiento a partir del"), False),
            (tr("plazo de 1 mes de la fecha en que debiera haber recogido el terminal. El plazo comenzará a contar a partir"), False),
            (tr("de la comunicación al interesado. La acción o derecho de recuperación de los bienes entregados por el"), False),
            (tr("consumidor o usuario al comerciante para su reparación prescribirá a los tres años a partir del momento de"), False),
            (tr("la entrega. ♦ Gastos de almacenaje: Por cada día devengado se cobrará 1 euro."), False),
            ("", False),
            (tr("7. Entrega de terminales: el cliente deberá identificarse fehacientemente con su DNI o documento oficial"), False),
            (tr("de identidad admitido en el tráfico jurídico. Para la retirada por parte de un representante, deberá aportar"), False),
            (tr("fotocopia del DNI del cliente con autorización expresa para su retirada."), False),
            ("", False),
            (tr("En esta reparación existe riesgo, eximiéndonos de toda responsabilidad en caso de alguna rotura de algún"), False),
            (tr("componente o daño físico."), False),
            ("", False),
            ("", False),
            (tr("El cliente queda informado y acepta todas las condiciones generales de contratación estipuladas en el"), True),
            (tr("presente documento."), True),
            ("", False),
            (tr("Fdo. El cliente."), True),
        ]

        for linea, es_negrita in texto_legal_2:
            if y < 2*cm:
                c.showPage()
                y = self.page_height - self.margin

            if es_negrita:
                c.setFont("Helvetica-Bold", 7)
            else:
                c.setFont("Helvetica", 7)

            c.drawString(self.margin, y, linea)
            y -= 0.32*cm

    def _dibujar_firmas_orden(self, c, y):
        """Firmas para la orden"""
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.5)

        # Firma Cliente
        c.line(self.margin, y, self.margin + 6*cm, y)
        c.setFont("Helvetica", 9)
        c.drawString(self.margin, y - 0.4*cm, tr("Firma del Cliente"))
        c.drawString(self.margin, y - 0.8*cm, f"({tr('Acepto las condiciones')})")

        # Firma Tienda
        x_right = self.page_width - self.margin - 6*cm
        c.line(x_right, y, self.page_width - self.margin, y)
        c.drawString(x_right, y - 0.4*cm, tr("Recibido por") + ":")
        c.drawString(x_right, y - 0.8*cm, tr("Fecha y hora") + ": ____________")
