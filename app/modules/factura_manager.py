"""
Gestor de facturas
"""
import sqlite3
from config import INVOICE_PREFIX
from app.utils.logger import get_logger

logger = get_logger('factura')


class FacturaManager:
    def __init__(self, db):
        self.db = db

    def obtener_siguiente_numero(self):
        """
        Obtiene el siguiente número de factura de forma atómica.
        Usa UPDATE + SELECT para evitar condiciones de carrera.
        """
        # Actualizar atómicamente e incrementar en 1
        self.db.execute_query(
            """UPDATE configuracion
               SET valor = CAST(CAST(valor AS INTEGER) + 1 AS TEXT)
               WHERE clave = 'ultimo_numero_factura'"""
        )

        # Obtener el valor actualizado
        config = self.db.fetch_one(
            "SELECT valor FROM configuracion WHERE clave = 'ultimo_numero_factura'"
        )

        if config:
            siguiente = int(config['valor'])
            return f"{INVOICE_PREFIX}{siguiente}"

        # Si no existe, crear con valor 16 (según config inicial)
        self.db.execute_query(
            "INSERT INTO configuracion (clave, valor) VALUES ('ultimo_numero_factura', '16')"
        )
        return f"{INVOICE_PREFIX}16"

    def actualizar_numero_factura(self, numero):
        """
        Ya no es necesario llamar este método después de guardar_factura.
        Se mantiene por compatibilidad, pero obtener_siguiente_numero ya actualiza el valor.
        """
        pass  # La actualización ya se hace en obtener_siguiente_numero

    def guardar_factura(self, datos, usuario_id=None):
        """
        Guarda una factura completa en la base de datos.

        TRANSACCIONAL: Todas las operaciones se realizan en una transacción.
        Si cualquier operación falla, se revierten TODOS los cambios.

        Operaciones incluidas:
        1. INSERT/SELECT clientes (si es necesario)
        2. INSERT facturas
        3. INSERT factura_items (múltiples)
        4. Registro en historial de auditoría
        """
        # INICIAR TRANSACCIÓN
        if not self.db.begin_transaction():
            logger.error("No se pudo iniciar transacción para guardar factura")
            return None

        try:
            # Validar datos básicos
            if not datos.get('items'):
                raise ValueError("La factura debe tener al menos un item")

            if datos['totales']['total'] <= 0:
                raise ValueError("El total de la factura debe ser mayor a 0")

            # 1. Buscar o crear cliente
            cliente_id = None
            nif_cliente = datos['cliente'].get('nif', '').strip()
            nombre_cliente = datos['cliente'].get('nombre', '').strip()
            
            if nombre_cliente or nif_cliente:
                cliente_existente = None
                
                # Primero buscar por NIF si existe (case-insensitive)
                if nif_cliente:
                    cliente_existente = self.db.fetch_one(
                        "SELECT id FROM clientes WHERE UPPER(nif) = UPPER(?)",
                        (nif_cliente,)
                    )
                
                # Si no encontró por NIF, buscar por nombre exacto
                if not cliente_existente and nombre_cliente:
                    cliente_existente = self.db.fetch_one(
                        "SELECT id FROM clientes WHERE nombre = ?",
                        (nombre_cliente,)
                    )

                if cliente_existente:
                    cliente_id = cliente_existente['id']
                else:
                    # Crear nuevo cliente
                    cliente_id = self.db.execute_query(
                        """INSERT INTO clientes (nombre, nif, direccion, codigo_postal, ciudad, telefono)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (nombre_cliente, nif_cliente,
                         datos['cliente'].get('direccion', ''), datos['cliente'].get('codigo_postal', ''),
                         datos['cliente'].get('ciudad', ''), datos['cliente'].get('telefono', ''))
                    )

                    if not cliente_id:
                        raise Exception("No se pudo crear el cliente")

            # 2. Insertar factura con datos del cliente embebidos (preservación histórica)
            factura_id = self.db.execute_query(
                """INSERT INTO facturas (numero_factura, cliente_id, fecha, subtotal, iva, total,
                                        cliente_nombre, cliente_nif, cliente_direccion, 
                                        cliente_telefono, cliente_codigo_postal, cliente_ciudad)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (datos['numero'], cliente_id, datos['fecha'],
                 datos['totales']['subtotal'], datos['totales']['iva'], datos['totales']['total'],
                 nombre_cliente, nif_cliente,
                 datos['cliente'].get('direccion', ''), datos['cliente'].get('telefono', ''),
                 datos['cliente'].get('codigo_postal', ''), datos['cliente'].get('ciudad', ''))
            )

            if not factura_id:
                raise Exception("No se pudo insertar la factura")

            # 3. Insertar items, actualizar stock y validar totales
            suma_items = 0
            for item in datos['items']:
                # Validar datos del item
                if item['cantidad'] <= 0:
                    raise ValueError(f"Cantidad inválida para item {item['descripcion']}: {item['cantidad']}")

                if item['precio'] < 0:
                    raise ValueError(f"Precio inválido para item {item['descripcion']}: {item['precio']}")

                total_item = item['cantidad'] * item['precio']
                suma_items += total_item

                # Usar producto_id directamente (ya viene del frontend)
                producto_id = item.get('producto_id')

                item_id = self.db.execute_query(
                    """INSERT INTO factura_items (factura_id, producto_id, descripcion, codigo_ean, imei_sn, cantidad, precio_unitario, total)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (factura_id, producto_id, item['descripcion'], '',
                     item.get('imei', ''), item['cantidad'], item['precio'], total_item)
                )

                if not item_id:
                    raise Exception(f"No se pudo insertar item: {item['descripcion']}")

                # Actualizar stock del producto si existe (usando ID directo)
                if producto_id:
                    stock_actualizado = self.db.execute_query(
                        "UPDATE productos SET stock = stock - ? WHERE id = ?",
                        (item['cantidad'], producto_id)
                    )
                    logger.debug(f"Producto ID {producto_id}: stock reducido en {item['cantidad']}")

            # Validar que la suma de items coincida con el total (con margen de 0.01 por redondeo)
            if abs(suma_items - datos['totales']['total']) > 0.01:
                raise ValueError(
                    f"Los items no coinciden con el total. "
                    f"Suma items: {suma_items}, Total factura: {datos['totales']['total']}"
                )

            # 4. REGISTRAR MOVIMIENTO DE CAJA (DENTRO de la transacción)
            # Esto asegura que si algo falla, el movimiento también se revierte
            try:
                from app.modules.caja_manager import CajaManager
                caja_manager = CajaManager(self.db)
                
                # Solo registrar si hay apertura de caja válida
                fecha_str = datos['fecha'].strftime('%Y-%m-%d') if hasattr(datos['fecha'], 'strftime') else str(datos['fecha'])
                estado_caja, _ = caja_manager.verificar_estado_caja_completo(fecha_str)
                
                if estado_caja == 'ok':
                    caja_manager.registrar_movimiento_automatico(
                        tipo='ingreso',
                        concepto=f"Factura {datos['numero']}",
                        monto=datos['totales']['total'],
                        fecha=fecha_str,
                        ref_id=factura_id,
                        ref_type='factura'
                    )
                    logger.info(f"Movimiento de caja registrado: Factura {datos['numero']} - {datos['totales']['total']}€")
            except sqlite3.Error as caja_error:
                # Si falla el registro de caja, revertir TODO
                raise Exception(f"Error registrando movimiento de caja: {caja_error}")

            # 5. REGISTRAR AUDITORÍA (creación de factura)
            if usuario_id:
                try:
                    from app.modules.auditoria_manager import AuditoriaManager
                    auditoria = AuditoriaManager(self.db)
                    auditoria.registrar_creacion(
                        usuario_id=usuario_id,
                        tabla='facturas',
                        registro_id=factura_id,
                        descripcion=f"Factura {datos['numero']} creada - Total: {datos['totales']['total']:.2f}€",
                        datos={'numero': datos['numero'], 'total': datos['totales']['total'], 'cliente': datos['cliente'].get('nombre', 'Sin cliente')}
                    )
                except sqlite3.Error as audit_error:
                    logger.warning(f"Error registrando auditoría: {audit_error}")
                    # No abortar por error de auditoría

            # CONFIRMAR TRANSACCIÓN - Todo salió bien
            self.db.commit()
            logger.info(f"Factura {datos['numero']} guardada exitosamente")
            return factura_id

        except (sqlite3.Error, ValueError, Exception) as e:
            # REVERTIR TRANSACCIÓN - Algo falló
            self.db.rollback()
            logger.error(f"Error guardando factura (transacción revertida): {e}")
            return None

    def obtener_factura(self, factura_id):
        """Obtiene una factura completa por ID"""
        factura = self.db.fetch_one(
            """SELECT f.*,
                      f.cliente_codigo_postal as cliente_cp
               FROM facturas f
               WHERE f.id = ?""",
            (factura_id,)
        )

        if factura:
            items = self.db.fetch_all(
                """SELECT * FROM factura_items WHERE factura_id = ?""",
                (factura_id,)
            )
            factura['items'] = items

        return factura

    def buscar_facturas(self, filtros=None):
        """Busca facturas con filtros opcionales"""
        # Si hay filtro de IMEI o EAN, necesitamos hacer JOIN con facturas_items
        if filtros and (filtros.get('imei') or filtros.get('ean')):
            query = """
                SELECT DISTINCT f.*
                FROM facturas f
                LEFT JOIN facturas_items fi ON f.id = fi.factura_id
                WHERE 1=1
            """
        else:
            query = """
                SELECT f.*
                FROM facturas f
                WHERE 1=1
            """
        params = []

        if filtros:
            if filtros.get('fecha_desde'):
                query += " AND f.fecha >= ?"
                params.append(filtros['fecha_desde'])

            if filtros.get('fecha_hasta'):
                query += " AND f.fecha <= ?"
                params.append(filtros['fecha_hasta'])

            if filtros.get('cliente'):
                query += " AND f.cliente_nombre LIKE ?"
                params.append(f"%{filtros['cliente']}%")

            if filtros.get('numero'):
                query += " AND f.numero_factura LIKE ?"
                params.append(f"%{filtros['numero']}%")

            if filtros.get('imei'):
                query += " AND fi.imei LIKE ?"
                params.append(f"%{filtros['imei']}%")

            if filtros.get('ean'):
                query += " AND fi.ean LIKE ?"
                params.append(f"%{filtros['ean']}%")

        query += " ORDER BY f.fecha DESC, f.id DESC"

        return self.db.fetch_all(query, params if params else None)

    def eliminar_factura(self, factura_id, restaurar_stock=True, usuario_id=None):
        """
        Elimina una factura.

        Args:
            factura_id: ID de la factura a eliminar
            restaurar_stock: Si True, restaura el stock. Si False, solo elimina el registro.
            usuario_id: ID del usuario que elimina (para auditoría)
        """
        factura = self.obtener_factura(factura_id)
        if not factura:
            return False, "Factura no encontrada"

        try:
            # INICIAR TRANSACCIÓN para garantizar consistencia
            self.db.begin_transaction()

            # 1. Restaurar Stock (solo si se solicita)
            if restaurar_stock:
                for item in factura['items']:
                    if item.get('codigo_ean'):
                        producto = self.db.fetch_one(
                            "SELECT id, stock FROM productos WHERE codigo_ean = ?",
                            (item['codigo_ean'],)
                        )
                        if producto:
                            nuevo_stock = producto['stock'] + item['cantidad']
                            self.db.execute_query(
                                "UPDATE productos SET stock = ? WHERE id = ?",
                                (nuevo_stock, producto['id'])
                            )

            # 2. Eliminar movimiento de caja
            self.db.execute_query(
                "DELETE FROM caja_movimientos WHERE factura_id = ?",
                (factura_id,)
            )

            # 3. Eliminar factura (ON DELETE CASCADE eliminará items)
            self.db.execute_query("DELETE FROM facturas WHERE id = ?", (factura_id,))

            # 4. REGISTRAR AUDITORÍA (eliminación de factura)
            if usuario_id:
                try:
                    from app.modules.auditoria_manager import AuditoriaManager
                    auditoria = AuditoriaManager(self.db)
                    auditoria.registrar_eliminacion(
                        usuario_id=usuario_id,
                        tabla='facturas',
                        registro_id=factura_id,
                        descripcion=f"Factura {factura['numero_factura']} eliminada",
                        datos={'numero': factura['numero_factura'], 'total': factura.get('total')}
                    )
                except sqlite3.Error as audit_error:
                    logger.warning(f"Error registrando auditoría: {audit_error}")

            # CONFIRMAR TRANSACCIÓN - todos los cambios se guardan
            self.db.commit()

            msg = f"Factura {factura['numero_factura']} eliminada"
            if restaurar_stock:
                msg += " (stock restaurado)"
            else:
                msg += " (sin modificar stock)"

            return True, msg

        except sqlite3.Error as e:
            # REVERTIR TRANSACCIÓN - deshacer todos los cambios
            self.db.rollback()
            logger.error(f"Error eliminando factura: {e}")
            return False, f"Error al eliminar factura: {str(e)}"

    def generar_pdf_desde_bd(self, factura_id):
        """
        Genera el PDF de una factura desde los datos de la BD.
        No crea nueva factura, solo regenera el archivo PDF.

        Args:
            factura_id: ID de la factura existente

        Returns:
            str: Ruta del PDF generado, o None si hay error
        """
        try:
            # Obtener factura con todos sus datos
            factura = self.obtener_factura(factura_id)
            if not factura:
                logger.error(f"Factura {factura_id} no encontrada")
                return None

            # Preparar datos en el formato que espera PDFGenerator
            from datetime import datetime

            # Convertir fecha si es string
            if isinstance(factura['fecha'], str):
                try:
                    fecha = datetime.strptime(factura['fecha'], '%Y-%m-%d')
                except (ValueError, TypeError):
                    fecha = datetime.now()
            else:
                fecha = factura['fecha']

            # Preparar datos del cliente
            cliente_data = {
                'nombre': factura.get('cliente_nombre', 'Cliente sin nombre'),
                'nif': factura.get('cliente_nif', ''),
                'direccion': factura.get('cliente_direccion', ''),
                'codigo_postal': factura.get('cliente_cp', ''),
                'ciudad': factura.get('cliente_ciudad', ''),
                'telefono': factura.get('cliente_telefono', ''),
                'email': factura.get('cliente_email', '')
            }

            # Preparar items
            items_data = []
            for item in factura.get('items', []):
                items_data.append({
                    'descripcion': item.get('descripcion', ''),
                    'imei_sn': item.get('imei_sn', ''),
                    'cantidad': item.get('cantidad', 1),
                    'precio': item.get('precio', 0.0)
                })

            # Preparar totales
            totales_data = {
                'subtotal': factura.get('subtotal', 0.0),
                'iva': factura.get('iva', 0.0),
                'total': factura.get('total', 0.0)
            }

            # Datos completos para el PDF
            datos_pdf = {
                'numero': factura['numero_factura'],
                'fecha': fecha,
                'cliente': cliente_data,
                'items': items_data,
                'totales': totales_data
            }

            # Generar PDF
            from app.modules.pdf_generator import PDFGenerator
            pdf_gen = PDFGenerator(self.db)
            pdf_path = pdf_gen.generar_factura(datos_pdf, factura_id)

            return pdf_path

        except sqlite3.Error as e:
            logger.error(f"Error generando PDF desde BD: {e}", exc_info=True)
            return None
