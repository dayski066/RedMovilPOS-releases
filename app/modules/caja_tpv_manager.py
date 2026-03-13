"""
Gestor de Caja/TPV para ventas rápidas con tickets
"""
import sqlite3
from datetime import datetime, date
from config import calcular_desglose_iva
from app.utils.logger import get_logger
from app.exceptions import DatabaseQueryError

# Logger para el módulo TPV
logger = get_logger('caja_tpv')


class CajaTpvManager:
    """Gestiona las operaciones de caja/TPV"""

    def __init__(self, db):
        self.db = db
        self._caja_manager = None

    def crear_venta(self, subtotal, iva, total, metodo_pago, items, usuario_id=None,
                     cantidad_recibida=None, cambio_devuelto=None):
        """Método simplificado para crear venta desde TPV"""
        resultado, error = self.guardar_venta(
            items=items,
            metodo_pago=metodo_pago,
            usuario_id=usuario_id,
            cantidad_recibida=cantidad_recibida,
            cambio_devuelto=cambio_devuelto
        )
        if error:
            return None
        return resultado.get('numero_ticket') if resultado else None

    @property
    def caja_manager(self):
        """Lazy load del CajaManager para evitar imports circulares"""
        if self._caja_manager is None:
            from app.modules.caja_manager import CajaManager
            self._caja_manager = CajaManager(self.db)
        return self._caja_manager
    
    def obtener_siguiente_ticket(self):
        """
        Obtiene el siguiente número de ticket de forma REALMENTE atómica.

        IMPORTANTE: Usa transacción explícita para garantizar que UPDATE + SELECT
        sean atómicos incluso con múltiples usuarios concurrentes.

        Returns:
            str: Número de ticket en formato TXXXXX

        Raises:
            Exception: Si no se puede generar el ticket
        """
        # TRANSACCIÓN EXPLÍCITA para atomicidad real
        if not self.db.begin_transaction():
            raise DatabaseQueryError(original_error="No se pudo iniciar transacción para generar ticket")

        try:
            # Intentar actualizar atómicamente dentro de la transacción
            self.db.execute_query(
                """UPDATE configuracion
                   SET valor = CAST(CAST(valor AS INTEGER) + 1 AS TEXT)
                   WHERE clave = 'ultimo_ticket_caja'"""
            )

            # Obtener el valor actualizado (dentro de la misma transacción)
            result = self.db.fetch_one(
                "SELECT valor FROM configuracion WHERE clave = 'ultimo_ticket_caja'"
            )

            if result:
                nuevo = int(result['valor'])
            else:
                # Si no existe, crearlo con valor 1
                nuevo = 1
                self.db.execute_query(
                    "INSERT INTO configuracion (clave, valor) VALUES ('ultimo_ticket_caja', '1')"
                )

            # Confirmar transacción
            self.db.commit()
            return f"T{nuevo:05d}"  # T00001, T00002...

        except sqlite3.Error as e:
            self.db.rollback()
            raise DatabaseQueryError(original_error=f"Error generando ticket: {str(e)}")
    
    def validar_stock_disponible(self, items):
        """
        Valida que haya stock suficiente para todos los items.
        Retorna (True, None) si hay stock, o (False, mensaje_error) si no.
        Los productos manuales (sin producto_id) no requieren validación de stock.
        """
        for item in items:
            origen = item.get('origen', 'productos')
            cantidad = int(item.get('cantidad', 1))

            # Productos manuales no requieren validación de stock
            if origen == 'manual' or (origen == 'productos' and not item.get('producto_id')):
                continue

            if origen == 'productos' and item.get('producto_id'):
                producto = self.db.fetch_one(
                    "SELECT stock, descripcion FROM productos WHERE id = ?",
                    (item['producto_id'],)
                )
                if producto:
                    if producto['stock'] < cantidad:
                        return False, f"Stock insuficiente para '{producto['descripcion']}'. Disponible: {producto['stock']}, Solicitado: {cantidad}"

            elif origen == 'compras_items' and item.get('compra_item_id'):
                compra_item = self.db.fetch_one(
                    "SELECT cantidad, descripcion FROM compras_items WHERE id = ?",
                    (item['compra_item_id'],)
                )
                if compra_item:
                    if compra_item['cantidad'] < cantidad:
                        return False, f"Stock insuficiente para '{compra_item['descripcion']}'. Disponible: {compra_item['cantidad']}, Solicitado: {cantidad}"

        return True, None

    def guardar_venta(self, items, metodo_pago='efectivo', usuario_id=None, notas='',
                     cantidad_recibida=None, cambio_devuelto=None):
        """
        Guarda una venta de caja con sus items.
        Items: lista de diccionarios con {nombre, precio, cantidad, producto_id (opcional), origen, compra_item_id}

        Mejoras implementadas:
        - Validación de stock antes de descontar (evita stock negativo)
        - Guarda origen y compra_item_id en ventas_caja_items (para anulación correcta)
        - Registra movimiento en caja_movimientos (para arqueo de caja)
        - Verificación de apertura de caja (requiere apertura antes de vender)
        """
        if not items:
            return None, "No hay productos en la venta"

        # VERIFICACIÓN: Comprobar estado de caja antes de procesar venta
        # Usa verificación COMPLETA que detecta cierres pendientes de días anteriores
        fecha_hoy = date.today().strftime('%Y-%m-%d')
        estado_apertura, data = self.caja_manager.verificar_estado_caja_completo(fecha_hoy)

        if estado_apertura != 'ok':
            # Return special error code so UI can handle apertura dialog
            # Para cierre_pendiente, incluir la fecha pendiente
            if estado_apertura == 'cierre_pendiente' and data:
                return None, f"APERTURA_REQUIRED:{estado_apertura}:{data['fecha']}"
            return None, f"APERTURA_REQUIRED:{estado_apertura}"

        # VALIDACIÓN: Verificar stock disponible ANTES de procesar
        stock_ok, error_stock = self.validar_stock_disponible(items)
        if not stock_ok:
            return None, error_stock

        # IMPORTANTE: Obtener ticket ANTES de iniciar transacción principal
        # (porque obtener_siguiente_ticket tiene su propia transacción)
        try:
            numero_ticket = self.obtener_siguiente_ticket()
        except sqlite3.Error as e:
            return None, f"Error generando ticket: {str(e)}"

        # Calcular totales
        total_general = 0
        subtotal_general = 0
        iva_general = 0

        items_procesados = []
        for item in items:
            # El precio puede venir como 'precio' o 'precio_unit'
            try:
                precio_con_iva = float(item.get('precio') or item.get('precio_unit', 0))
            except (ValueError, TypeError):
                precio_con_iva = 0.0

            try:
                cantidad = int(item.get('cantidad', 1))
            except (ValueError, TypeError):
                cantidad = 1

            # Calcular desglose IVA (precio incluye IVA)
            subtotal_item, iva_item, _ = calcular_desglose_iva(precio_con_iva * cantidad)
            total_item = precio_con_iva * cantidad

            items_procesados.append({
                'producto_id': item.get('producto_id'),
                'origen': item.get('origen', 'productos'),
                'compra_item_id': item.get('compra_item_id'),
                'nombre': item['nombre'],
                'precio_unitario': precio_con_iva,
                'cantidad': cantidad,
                'subtotal_item': subtotal_item,
                'iva_item': iva_item,
                'total_item': total_item
            })

            subtotal_general += subtotal_item
            iva_general += iva_item
            total_general += total_item

        # INICIAR TRANSACCIÓN: Todo debe ser atómico
        if not self.db.begin_transaction():
            return None, "Error iniciando transacción"

        try:
            # RE-VALIDAR STOCK DENTRO de la transacción para evitar race conditions
            # Esto asegura que dos usuarios no puedan vender el mismo producto simultáneamente
            stock_ok_atomic, error_stock_atomic = self.validar_stock_disponible(items)
            if not stock_ok_atomic:
                self.db.rollback()
                return None, f"Stock insuficiente (verificación atómica): {error_stock_atomic}"

            # Insertar venta
            venta_id = self.db.execute_query("""
                INSERT INTO ventas_caja
                (numero_ticket, subtotal, iva, total, metodo_pago, usuario_id, notas,
                 cantidad_recibida, cambio_devuelto)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (numero_ticket, subtotal_general, iva_general, total_general,
                  metodo_pago, usuario_id, notas, cantidad_recibida, cambio_devuelto))

            if not venta_id:
                self.db.rollback()
                return None, "Error al crear la venta"

            # Insertar items con origen y compra_item_id, y actualizar stock
            for item in items_procesados:
                # Guardar item CON origen y compra_item_id para poder restaurar al anular
                self.db.execute_query("""
                    INSERT INTO ventas_caja_items
                    (venta_caja_id, producto_id, nombre_producto, precio_unitario,
                     cantidad, subtotal_item, iva_item, total_item, origen, compra_item_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (venta_id, item['producto_id'], item['nombre'],
                      item['precio_unitario'], item['cantidad'],
                      item['subtotal_item'], item['iva_item'], item['total_item'],
                      item['origen'], item['compra_item_id']))

                # Actualizar stock según el origen (permite stock negativo para backorders)
                if item['origen'] == 'productos' and item['producto_id']:
                    self.db.execute_query(
                        """UPDATE productos
                           SET stock = stock - ?
                           WHERE id = ?""",
                        (item['cantidad'], item['producto_id'])
                    )
                elif item['origen'] == 'compras_items' and item['compra_item_id']:
                    self.db.execute_query(
                        """UPDATE compras_items
                           SET cantidad = cantidad - ?
                           WHERE id = ?""",
                        (item['cantidad'], item['compra_item_id'])
                    )

            # REGISTRAR EN CAJA: Solo si es efectivo (el dinero entra en caja física)
            if metodo_pago == 'efectivo':
                # Este método ahora lanza excepciones si falla
                self._registrar_movimiento_caja(venta_id, numero_ticket, total_general, metodo_pago)

            # Todo bien, confirmar transacción
            self.db.commit()

            return {
                'id': venta_id,
                'numero_ticket': numero_ticket,
                'subtotal': subtotal_general,
                'iva': iva_general,
                'total': total_general,
                'items': items_procesados
            }, None

        except sqlite3.Error as e:
            # Revertir TODO si algo falla
            self.db.rollback()
            return None, f"Error guardando venta: {str(e)}"

    def _registrar_movimiento_caja(self, venta_id, numero_ticket, total, metodo_pago):
        """Registra un movimiento de ingreso en caja_movimientos para ventas TPV

        IMPORTANTE: Este método se ejecuta dentro de una transacción.
        Si falla, la excepción se propaga para revertir toda la venta.

        Args:
            venta_id: ID de la venta
            numero_ticket: Número de ticket
            total: Total de la venta
            metodo_pago: Método de pago ('efectivo', 'tarjeta', 'bizum')
        """
        # Usar el método del CajaManager que ya maneja todo correctamente
        from datetime import date

        resultado = self.caja_manager.registrar_movimiento_automatico(
            tipo='ingreso',
            concepto=f'Ticket {numero_ticket}',
            monto=total,
            fecha=date.today().strftime('%Y-%m-%d'),
            ref_id=venta_id,
            ref_type='venta_caja',
            metodo_pago=metodo_pago
        )

        if not resultado:
            raise DatabaseQueryError(original_error="No se pudo registrar el movimiento de caja")

        return resultado
    
    def obtener_ventas_dia(self, fecha=None):
        """Obtiene las ventas del día especificado (o hoy)"""
        if fecha is None:
            fecha = date.today().strftime('%Y-%m-%d')
        
        ventas = self.db.fetch_all("""
            SELECT vc.*, u.username as usuario_nombre
            FROM ventas_caja vc
            LEFT JOIN usuarios u ON vc.usuario_id = u.id
            WHERE DATE(vc.fecha) = ?
            ORDER BY vc.fecha DESC
        """, (fecha,))
        
        return ventas
    
    def obtener_total_dia(self, fecha=None):
        """Obtiene el total de ventas del día"""
        if fecha is None:
            fecha = date.today().strftime('%Y-%m-%d')
        
        result = self.db.fetch_one("""
            SELECT COUNT(*) as num_ventas, 
                   COALESCE(SUM(total), 0) as total,
                   COALESCE(SUM(subtotal), 0) as subtotal,
                   COALESCE(SUM(iva), 0) as iva
            FROM ventas_caja 
            WHERE DATE(fecha) = ? AND estado = 'completada'
        """, (fecha,))
        
        return result
    
    def obtener_venta(self, venta_id):
        """Obtiene una venta con sus items"""
        venta = self.db.fetch_one("""
            SELECT vc.*, u.username as usuario_nombre
            FROM ventas_caja vc
            LEFT JOIN usuarios u ON vc.usuario_id = u.id
            WHERE vc.id = ?
        """, (venta_id,))
        
        if venta:
            items = self.db.fetch_all("""
                SELECT * FROM ventas_caja_items WHERE venta_caja_id = ?
            """, (venta_id,))
            venta['items'] = items
        
        return venta
    
    def anular_venta(self, venta_id):
        """
        Anula una venta y restaura el stock según el origen de cada item.

        Mejoras implementadas:
        - Restaura stock en tabla productos O compras_items según el origen guardado
        - Elimina el movimiento de caja asociado y restaura el saldo
        - Transacción atómica: todo se revierte si algo falla
        """
        venta = self.obtener_venta(venta_id)
        if not venta:
            return False, "Venta no encontrada"

        if venta['estado'] == 'anulada':
            return False, "La venta ya está anulada"

        # Iniciar transacción
        if not self.db.begin_transaction():
            return False, "Error iniciando transacción"

        try:
            # Restaurar stock según ORIGEN de cada item
            for item in venta.get('items', []):
                origen = item.get('origen', 'productos')  # Default a productos para ventas antiguas
                cantidad = item['cantidad']

                if origen == 'compras_items' and item.get('compra_item_id'):
                    # Restaurar en compras_items (móviles únicos)
                    self.db.execute_query(
                        "UPDATE compras_items SET cantidad = cantidad + ? WHERE id = ?",
                        (cantidad, item['compra_item_id'])
                    )
                elif item.get('producto_id'):
                    # Restaurar en productos (inventario)
                    self.db.execute_query(
                        "UPDATE productos SET stock = stock + ? WHERE id = ?",
                        (cantidad, item['producto_id'])
                    )

            # Revertir movimiento de caja si existe
            if venta.get('metodo_pago') == 'efectivo':
                self._revertir_movimiento_caja(venta_id, venta['total'])

            # Marcar como anulada
            self.db.execute_query(
                "UPDATE ventas_caja SET estado = 'anulada' WHERE id = ?",
                (venta_id,)
            )

            # Confirmar transacción
            self.db.commit()
            return True, "Venta anulada correctamente"

        except sqlite3.Error as e:
            # Revertir todo si algo falla
            self.db.rollback()
            return False, f"Error anulando venta: {str(e)}"

    def _revertir_movimiento_caja(self, venta_id, total):
        """
        Revierte el movimiento de caja al anular una venta.

        IMPORTANTE: Este método se ejecuta dentro de una transacción.
        Si falla, la excepción se propaga para revertir toda la anulación.
        """
        try:
            # Buscar y eliminar el movimiento de caja asociado
            movimiento = self.db.fetch_one(
                "SELECT id FROM caja_movimientos WHERE referencia_id = ? AND referencia_tipo = 'venta_caja'",
                (venta_id,)
            )

            if movimiento:
                # Eliminar el movimiento
                self.db.execute_query(
                    "DELETE FROM caja_movimientos WHERE id = ?",
                    (movimiento['id'],)
                )

                # Descontar el total del saldo de caja
                saldo_actual = self.caja_manager.obtener_saldo_actual()
                nuevo_saldo = saldo_actual - total
                self.caja_manager.actualizar_saldo_caja(nuevo_saldo)

                logger.info(f"Movimiento de caja revertido: venta_id={venta_id}, total={total}€")

        except sqlite3.Error as e:
            logger.error(f"Error revirtiendo movimiento de caja: {e}", exc_info=True)
            # PROPAGAR la excepción para que la transacción se revierta completamente
            raise DatabaseQueryError(original_error=f"No se pudo revertir movimiento de caja: {str(e)}")
    
    # === Gestión de Favoritos ===
    
    def obtener_favoritos(self):
        """Obtiene los productos favoritos ordenados"""
        return self.db.fetch_all("""
            SELECT pf.*, p.stock 
            FROM productos_favoritos pf
            LEFT JOIN productos p ON pf.producto_id = p.id
            ORDER BY pf.orden, pf.id
        """)
    
    def agregar_favorito(self, producto_id=None, nombre=None, precio=None, color='#5E81AC'):
        """Agrega un producto a favoritos"""
        try:
            if producto_id:
                # Desde inventario
                producto = self.db.fetch_one(
                    "SELECT descripcion as nombre, precio FROM productos WHERE id = ?", 
                    (producto_id,)
                )
                if not producto:
                    return False
                nombre = producto['nombre']
                precio = producto['precio']
                es_manual = 0
            else:
                es_manual = 1
            
            if not nombre or precio is None:
                return False
            
            # Obtener siguiente orden
            result = self.db.fetch_one("SELECT MAX(orden) as max_orden FROM productos_favoritos")
            orden = (result['max_orden'] or 0) + 1 if result else 1
            
            self.db.execute_query("""
                INSERT INTO productos_favoritos (producto_id, nombre, precio, color, orden, es_manual)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (producto_id, nombre, precio, color, orden, es_manual))
            
            return True
        except sqlite3.Error as e:
            logger.error(f"Error agregando favorito: {e}", exc_info=True)
            return False
    
    def eliminar_favorito(self, favorito_id):
        """Elimina un producto de favoritos"""
        self.db.execute_query(
            "DELETE FROM productos_favoritos WHERE id = ?",
            (favorito_id,)
        )
        return True
    
    def actualizar_orden_favoritos(self, favoritos_ids):
        """Actualiza el orden de los favoritos"""
        for i, fav_id in enumerate(favoritos_ids):
            self.db.execute_query(
                "UPDATE productos_favoritos SET orden = ? WHERE id = ?",
                (i, fav_id)
            )
    
    # === Búsqueda de productos ===

    def buscar_productos(self, texto):
        """Busca productos en inventario Y en compras (móviles únicos con IMEI)"""
        resultados = []

        # 1. Buscar en productos (inventario)
        productos_inv = self.db.fetch_all("""
            SELECT id, descripcion as nombre, precio, stock as cantidad,
                   codigo_ean as codigo_barras, imei, 'productos' as origen
            FROM productos
            WHERE (descripcion LIKE ? OR codigo_ean LIKE ? OR imei LIKE ?)
            AND activo = 1 AND stock > 0
            LIMIT 20
        """, (f'%{texto}%', f'%{texto}%', f'%{texto}%'))

        resultados.extend(productos_inv)

        # 2. Buscar en compras_items (móviles comprados con IMEI único)
        compras_items = self.db.fetch_all("""
            SELECT ci.id, ci.descripcion as nombre, ci.precio_unitario as precio,
                   ci.cantidad, ci.codigo_ean as codigo_barras, ci.imei,
                   'compras_items' as origen, c.numero_compra
            FROM compras_items ci
            INNER JOIN compras c ON ci.compra_id = c.id
            WHERE (ci.descripcion LIKE ? OR ci.codigo_ean LIKE ? OR ci.imei LIKE ?)
            AND ci.cantidad > 0
            AND ci.imei IS NOT NULL AND ci.imei != ''
            LIMIT 20
        """, (f'%{texto}%', f'%{texto}%', f'%{texto}%'))

        resultados.extend(compras_items)

        return resultados[:20]  # Limitar a 20 resultados totales

