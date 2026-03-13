"""
Gestor de devoluciones/reembolsos
"""
import sqlite3
from datetime import datetime
from app.utils.logger import get_logger
from app.exceptions import DatabaseQueryError

# Logger para el módulo de devoluciones
logger = get_logger('devoluciones')


class DevolucionManager:
    def __init__(self, db):
        self.db = db
        self._caja_manager = None
        self._tpv_manager = None

    @property
    def caja_manager(self):
        if self._caja_manager is None:
            from app.modules.caja_manager import CajaManager
            self._caja_manager = CajaManager(self.db)
        return self._caja_manager

    @property
    def tpv_manager(self):
        if self._tpv_manager is None:
            from app.modules.caja_tpv_manager import CajaTpvManager
            self._tpv_manager = CajaTpvManager(self.db)
        return self._tpv_manager

    def buscar_venta_por_ticket(self, numero_ticket):
        """
        Busca una venta por numero de ticket.
        Retorna la venta con sus items y cantidades ya devueltas.
        """
        venta = self.db.fetch_one("""
            SELECT vc.*, u.username as usuario_nombre
            FROM ventas_caja vc
            LEFT JOIN usuarios u ON vc.usuario_id = u.id
            WHERE vc.numero_ticket = ? AND vc.estado = 'completada'
        """, (numero_ticket,))

        if not venta:
            return None

        # Obtener items con cantidad disponible para devolver
        items = self.db.fetch_all("""
            SELECT vci.*,
                   (vci.cantidad - COALESCE(vci.cantidad_devuelta, 0)) as cantidad_disponible
            FROM ventas_caja_items vci
            WHERE vci.venta_caja_id = ?
        """, (venta['id'],))

        venta['items'] = items

        # Calcular totales ya devueltos
        devoluciones = self.db.fetch_all("""
            SELECT * FROM devoluciones WHERE venta_caja_id = ?
        """, (venta['id'],))

        venta['devoluciones'] = devoluciones
        venta['total_devuelto'] = sum(d['monto_devuelto'] for d in devoluciones)

        return venta

    def procesar_devolucion(self, venta_id, items_devolver, motivo, usuario_id=None, metodo_devolucion=None):
        """
        Procesa una devolucion parcial o total.

        items_devolver: [
            {
                'venta_item_id': int,
                'cantidad_devolver': int,
                'producto_id': int (opcional),
                'compra_item_id': int (opcional),
                'origen': str,
                'precio_unitario': float,
                'subtotal': float,
                'iva': float,
                'total': float
            },
            ...
        ]
        metodo_devolucion: str (opcional) - 'efectivo', 'tarjeta', 'bizum', 'vale'
                          Si None, usa el metodo_pago original de la venta
        """
        if not items_devolver:
            return None, "No hay items para devolver"

        # Obtener venta original
        venta = self.tpv_manager.obtener_venta(venta_id)
        if not venta:
            return None, "Venta no encontrada"

        if venta['estado'] != 'completada':
            return None, "Solo se pueden devolver ventas completadas"

        # INICIAR TRANSACCIÓN PRIMERO para prevenir race conditions
        if not self.db.begin_transaction():
            return None, "Error iniciando transaccion"

        try:
            # VALIDAR CANTIDADES DISPONIBLES DENTRO de la transacción
            # Esto previene que dos usuarios devuelvan el mismo item simultáneamente
            for item in items_devolver:
                venta_item = self.db.fetch_one("""
                    SELECT cantidad, COALESCE(cantidad_devuelta, 0) as cantidad_devuelta
                    FROM ventas_caja_items
                    WHERE id = ?
                """, (item['venta_item_id'],))

                if not venta_item:
                    self.db.rollback()
                    return None, f"Item de venta {item['venta_item_id']} no encontrado"

                cantidad_disponible = venta_item['cantidad'] - venta_item['cantidad_devuelta']

                if item['cantidad_devolver'] > cantidad_disponible:
                    self.db.rollback()
                    nombre = item.get('nombre_producto', f"Item {item['venta_item_id']}")
                    return None, f"{nombre}: No se puede devolver {item['cantidad_devolver']} unidades. Solo hay {cantidad_disponible} disponibles."

                if item['cantidad_devolver'] <= 0:
                    self.db.rollback()
                    return None, "La cantidad a devolver debe ser mayor que cero"
            # Calcular monto total a devolver
            monto_total = sum(item['total'] for item in items_devolver)

            # Determinar método de devolución (usar el especificado o el original)
            metodo_final = metodo_devolucion if metodo_devolucion else venta['metodo_pago']

            # Crear registro de devolucion
            devolucion_id = self.db.execute_query("""
                INSERT INTO devoluciones
                (venta_caja_id, motivo, monto_devuelto, metodo_devolucion, usuario_id)
                VALUES (?, ?, ?, ?, ?)
            """, (venta_id, motivo, monto_total, metodo_final, usuario_id))

            if not devolucion_id:
                self.db.rollback()
                return None, "Error creando devolucion"

            # Procesar cada item devuelto
            for item in items_devolver:
                # Registrar item devuelto
                self.db.execute_query("""
                    INSERT INTO devoluciones_items
                    (devolucion_id, venta_item_id, cantidad_devuelta,
                     precio_unitario, subtotal, iva, total)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (devolucion_id, item['venta_item_id'], item['cantidad_devolver'],
                      item['precio_unitario'], item['subtotal'], item['iva'], item['total']))

                # Actualizar cantidad_devuelta en venta_item original
                self.db.execute_query("""
                    UPDATE ventas_caja_items
                    SET cantidad_devuelta = cantidad_devuelta + ?
                    WHERE id = ?
                """, (item['cantidad_devolver'], item['venta_item_id']))

                # Restaurar stock segun origen
                origen = item.get('origen', 'productos')
                cantidad = item['cantidad_devolver']

                if origen == 'productos' and item.get('producto_id'):
                    self.db.execute_query(
                        "UPDATE productos SET stock = stock + ? WHERE id = ?",
                        (cantidad, item['producto_id'])
                    )
                elif origen == 'compras_items' and item.get('compra_item_id'):
                    self.db.execute_query(
                        "UPDATE compras_items SET cantidad = cantidad + ? WHERE id = ?",
                        (cantidad, item['compra_item_id'])
                    )

            # Registrar movimiento de caja si la devolución es en efectivo
            # (no importa el método original, sino cómo se reembolsa)
            if metodo_final == 'efectivo':
                self._registrar_egreso_devolucion(devolucion_id, venta['numero_ticket'], monto_total)

            # Commit transaction
            self.db.commit()

            return {
                'id': devolucion_id,
                'monto_total': monto_total,
                'items_count': len(items_devolver)
            }, None

        except sqlite3.Error as e:
            self.db.rollback()
            return None, f"Error procesando devolucion: {str(e)}"

    def _registrar_egreso_devolucion(self, devolucion_id, numero_ticket, monto):
        """
        Registra egreso en caja por devolucion en efectivo.
        IMPORTANTE: Solo se llama cuando metodo_pago='efectivo'.
        """
        try:
            saldo_actual = self.caja_manager.obtener_saldo_actual()
            nuevo_saldo = saldo_actual - monto

            # Verificar saldo negativo
            if nuevo_saldo < 0:
                logger.warning(
                    f"Saldo de caja quedaría NEGATIVO por devolución: {nuevo_saldo:.2f}€ | "
                    f"Saldo actual: {saldo_actual:.2f}€ | "
                    f"Devolución: {monto:.2f}€ | "
                    f"Ticket: {numero_ticket}"
                )

            self.db.execute_query("""
                INSERT INTO caja_movimientos
                (tipo, categoria, concepto, monto, fecha, saldo_anterior, saldo_nuevo,
                 referencia_id, referencia_tipo, metodo_pago)
                VALUES (?, ?, ?, ?, DATE('now'), ?, ?, ?, ?, ?)
            """, ('egreso', 'Devolucion', f'Devolucion Ticket {numero_ticket}',
                  monto, saldo_actual, nuevo_saldo, devolucion_id, 'devolucion', 'efectivo'))

            # Actualizar saldo atómicamente para prevenir race conditions
            self.caja_manager.ajustar_saldo_caja_atomico(monto, es_ingreso=False)
        except sqlite3.Error as e:
            # Propagar excepción en lugar de solo advertir
            # (estamos dentro de una transacción que debe revertirse si falla)
            raise DatabaseQueryError(original_error=f"Error registrando egreso por devolución: {str(e)}")

    def obtener_devoluciones(self, filtros=None):
        """Obtiene historico de devoluciones"""
        query = """
            SELECT d.*, vc.numero_ticket, u.username as usuario_nombre
            FROM devoluciones d
            INNER JOIN ventas_caja vc ON d.venta_caja_id = vc.id
            LEFT JOIN usuarios u ON d.usuario_id = u.id
            WHERE 1=1
        """
        params = []

        if filtros:
            if filtros.get('fecha_desde'):
                query += " AND DATE(d.fecha_creacion) >= ?"
                params.append(filtros['fecha_desde'])

            if filtros.get('fecha_hasta'):
                query += " AND DATE(d.fecha_creacion) <= ?"
                params.append(filtros['fecha_hasta'])

        query += " ORDER BY d.fecha_creacion DESC"

        return self.db.fetch_all(query, params if params else None)

    def obtener_devolucion_detalle(self, devolucion_id):
        """Obtiene detalle completo de una devolucion con sus items"""
        devolucion = self.db.fetch_one("""
            SELECT d.*, vc.numero_ticket, u.username as usuario_nombre
            FROM devoluciones d
            INNER JOIN ventas_caja vc ON d.venta_caja_id = vc.id
            LEFT JOIN usuarios u ON d.usuario_id = u.id
            WHERE d.id = ?
        """, (devolucion_id,))

        if devolucion:
            items = self.db.fetch_all("""
                SELECT di.*, vci.nombre_producto
                FROM devoluciones_items di
                INNER JOIN ventas_caja_items vci ON di.venta_item_id = vci.id
                WHERE di.devolucion_id = ?
            """, (devolucion_id,))
            devolucion['items'] = items

        return devolucion
