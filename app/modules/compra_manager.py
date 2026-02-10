"""
Gestor de compras
"""
import sqlite3
from config import PURCHASE_PREFIX
from app.utils.logger import get_logger

logger = get_logger('compra')


class CompraManager:
    def __init__(self, db):
        self.db = db

    def obtener_siguiente_numero(self):
        """
        Obtiene el siguiente número de compra de forma atómica.
        Usa UPDATE + SELECT para evitar condiciones de carrera.
        """
        # Actualizar atómicamente e incrementar en 1
        self.db.execute_query(
            """UPDATE configuracion
               SET valor = CAST(CAST(valor AS INTEGER) + 1 AS TEXT)
               WHERE clave = 'ultimo_numero_compra'"""
        )

        # Obtener el valor actualizado
        config = self.db.fetch_one(
            "SELECT valor FROM configuracion WHERE clave = 'ultimo_numero_compra'"
        )

        if config:
            siguiente = int(config['valor'])
            return f"{PURCHASE_PREFIX}{siguiente}"

        # Si no existe, crear con valor 1
        self.db.execute_query(
            "INSERT INTO configuracion (clave, valor) VALUES ('ultimo_numero_compra', '1')"
        )
        return f"{PURCHASE_PREFIX}1"

    def actualizar_numero_compra(self, numero):
        """
        Ya no es necesario llamar este método después de guardar_compra.
        Se mantiene por compatibilidad, pero obtener_siguiente_numero ya actualiza el valor.
        """
        pass  # La actualización ya se hace en obtener_siguiente_numero

    def guardar_compra(self, datos, usuario_id=None):
        """
        Guarda una compra completa en la base de datos y actualiza stock.

        TRANSACCIONAL: Todas las operaciones se realizan en una transacción.
        Si cualquier operación falla, se revierten TODOS los cambios.

        Operaciones incluidas:
        1. INSERT compras
        2. INSERT compras_items (múltiples)
        3. UPDATE productos (stock, múltiples)
        4. INSERT caja_movimientos
        5. Registro en historial de auditoría
        """
        # INICIAR TRANSACCIÓN
        if not self.db.begin_transaction():
            logger.error("No se pudo iniciar transacción para guardar compra")
            return None

        try:
            # 1. Insertar compra
            compra_id = self.db.execute_query(
                """INSERT INTO compras (numero_compra, fecha, proveedor_nombre, proveedor_nif,
                                        proveedor_direccion, proveedor_codigo_postal, proveedor_ciudad,
                                        proveedor_telefono, subtotal, iva, total, dni_imagen)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (datos['numero'], datos['fecha'], datos['cliente']['nombre'],
                 datos['cliente']['nif'], datos['cliente']['direccion'],
                 datos['cliente'].get('codigo_postal', ''), datos['cliente'].get('ciudad', ''),
                 datos['cliente']['telefono'], datos['totales']['subtotal'],
                 datos['totales']['iva'], datos['totales']['total'],
                 datos.get('dni_imagen'))
            )

            if not compra_id:
                raise Exception("No se pudo insertar la compra")

            # 2. Insertar items y actualizar stock
            for item in datos['items']:
                # Validar datos del item
                if item['cantidad'] <= 0:
                    raise ValueError(f"Cantidad inválida para item {item['descripcion']}: {item['cantidad']}")

                if item['precio_unitario'] < 0:
                    raise ValueError(f"Precio inválido para item {item['descripcion']}: {item['precio_unitario']}")

                total_item = item['cantidad'] * item['precio_unitario']

                # Sanitizar IDs para asegurar que sean enteros o None
                marca_id = item.get('marca_id')
                if marca_id == '' or marca_id == 0: marca_id = None

                modelo_id = item.get('modelo_id')
                if modelo_id == '' or modelo_id == 0: modelo_id = None

                # Insertar item de compra
                item_id = self.db.execute_query(
                    """INSERT INTO compras_items (compra_id, descripcion, codigo_ean, imei, marca_id, modelo_id, ram, almacenamiento, estado, cantidad, precio_unitario, total)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (compra_id, item['descripcion'], item.get('ean'), item.get('imei'),
                     marca_id, modelo_id,
                     item.get('ram'), item.get('almacenamiento'), item.get('estado'),
                     item['cantidad'], item['precio_unitario'], total_item)
                )

                if not item_id:
                    raise Exception(f"No se pudo insertar item: {item['descripcion']}")

                # 3. Actualizar stock del producto si existe
                if item.get('ean'):
                    producto = self.db.fetch_one(
                        "SELECT id, stock FROM productos WHERE codigo_ean = ?",
                        (item['ean'],)
                    )
                    if producto:
                        nuevo_stock = producto['stock'] + item['cantidad']

                        # Validar que el stock no sea negativo
                        if nuevo_stock < 0:
                            raise ValueError(f"Stock negativo para producto {item['descripcion']}: {nuevo_stock}")

                        self.db.execute_query(
                            "UPDATE productos SET stock = ? WHERE id = ?",
                            (nuevo_stock, producto['id'])
                        )

            # 4. Registrar movimiento de caja automáticamente
            from app.modules.caja_manager import CajaManager
            caja_mgr = CajaManager(self.db)
            caja_mgr.registrar_movimiento_automatico(
                tipo='egreso',
                concepto=f"Compra {datos['numero']} - {datos['cliente']['nombre']}",
                monto=datos['totales']['total'],
                fecha=datos['fecha'],
                ref_id=compra_id,
                ref_type='compra'
            )

            # 5. REGISTRAR AUDITORÍA (creación de compra)
            if usuario_id:
                try:
                    from app.modules.auditoria_manager import AuditoriaManager
                    auditoria = AuditoriaManager(self.db)
                    auditoria.registrar_creacion(
                        usuario_id=usuario_id,
                        tabla='compras',
                        registro_id=compra_id,
                        descripcion=f"Compra {datos['numero']} creada - Total: {datos['totales']['total']:.2f}€",
                        datos={'numero': datos['numero'], 'total': datos['totales']['total'], 'proveedor': datos['cliente'].get('nombre', 'Sin proveedor')}
                    )
                except sqlite3.Error as audit_error:
                    logger.warning(f"Error registrando auditoría: {audit_error}")

            # CONFIRMAR TRANSACCIÓN - Todo salió bien
            self.db.commit()
            logger.info(f"Compra {datos['numero']} guardada exitosamente")
            return compra_id

        except sqlite3.Error as e:
            # REVERTIR TRANSACCIÓN - Algo falló
            self.db.rollback()
            logger.error(f"Error guardando compra (transacción revertida): {e}")
            return None

    def obtener_compra(self, compra_id):
        """Obtiene una compra completa por ID"""
        compra = self.db.fetch_one(
            "SELECT * FROM compras WHERE id = ?",
            (compra_id,)
        )

        if compra:
            items = self.db.fetch_all(
                """SELECT ci.*, ma.nombre as marca_nombre, mo.nombre as modelo_nombre
                   FROM compras_items ci
                   LEFT JOIN marcas ma ON ci.marca_id = ma.id
                   LEFT JOIN modelos mo ON ci.modelo_id = mo.id
                   WHERE ci.compra_id = ?""",
                (compra_id,)
            )
            compra['items'] = items
            
            # Siempre buscar el DNI más actualizado del cliente
            # (prioridad: cliente actual > dni guardado en compra)
            cliente = None
            cliente_dni = None
            
            # Buscar cliente por NIF (más fiable)
            if compra.get('proveedor_nif') and compra['proveedor_nif'].strip():
                cliente = self.db.fetch_one(
                    "SELECT dni_imagen FROM clientes WHERE LOWER(nif) = LOWER(?)",
                    (compra['proveedor_nif'].strip(),)
                )
                if cliente:
                    cliente_dni = cliente.get('dni_imagen')
            
            # Si no encontramos por NIF, buscar por nombre
            if not cliente_dni and compra.get('proveedor_nombre'):
                cliente = self.db.fetch_one(
                    "SELECT dni_imagen FROM clientes WHERE LOWER(nombre) = LOWER(?)",
                    (compra['proveedor_nombre'].strip(),)
                )
                if cliente:
                    cliente_dni = cliente.get('dni_imagen')
            
            # Usar el DNI del cliente si existe (siempre el más actualizado)
            if cliente_dni:
                compra['dni_imagen'] = cliente_dni

        return compra

    def buscar_compras(self, filtros=None):
        """Busca compras con filtros opcionales"""
        # Si hay filtro de IMEI o EAN, necesitamos hacer JOIN con compras_items
        if filtros and (filtros.get('imei') or filtros.get('ean')):
            query = """
                SELECT DISTINCT c.* FROM compras c
                LEFT JOIN compras_items ci ON c.id = ci.compra_id
                WHERE 1=1
            """
        else:
            query = """
                SELECT * FROM compras
                WHERE 1=1
            """
        params = []

        if filtros:
            if filtros.get('fecha_desde'):
                query += " AND fecha >= ?"
                params.append(filtros['fecha_desde'])

            if filtros.get('fecha_hasta'):
                query += " AND fecha <= ?"
                params.append(filtros['fecha_hasta'])

            if filtros.get('proveedor'):
                query += " AND proveedor_nombre LIKE ?"
                params.append(f"%{filtros['proveedor']}%")

            if filtros.get('numero'):
                query += " AND numero_compra LIKE ?"
                params.append(f"%{filtros['numero']}%")

            if filtros.get('imei'):
                query += " AND ci.imei LIKE ?"
                params.append(f"%{filtros['imei']}%")

            if filtros.get('ean'):
                query += " AND ci.ean LIKE ?"
                params.append(f"%{filtros['ean']}%")

        query += " ORDER BY fecha DESC, id DESC"

        return self.db.fetch_all(query, params if params else None)

    def eliminar_compra(self, compra_id, revertir_stock=True, usuario_id=None):
        """
        Elimina una compra.

        Args:
            compra_id: ID de la compra a eliminar
            revertir_stock: Si True, revierte el stock. Si False, mantiene el stock actual.
            usuario_id: ID del usuario que elimina (para auditoría)
        """
        compra = self.obtener_compra(compra_id)
        if not compra:
            return False, "Compra no encontrada"

        try:
            # INICIAR TRANSACCIÓN para garantizar consistencia
            self.db.begin_transaction()

            # 1. Revertir Stock (solo si se solicita)
            if revertir_stock:
                for item in compra['items']:
                    if item.get('codigo_ean'):
                        producto = self.db.fetch_one(
                            "SELECT id, stock FROM productos WHERE codigo_ean = ?",
                            (item['codigo_ean'],)
                        )
                        if producto:
                            nuevo_stock = producto['stock'] - item['cantidad']

                            self.db.execute_query(
                                "UPDATE productos SET stock = ? WHERE id = ?",
                                (nuevo_stock, producto['id'])
                            )

            # 2. Eliminar movimiento de caja
            self.db.execute_query(
                "DELETE FROM caja_movimientos WHERE compra_id = ?",
                (compra_id,)
            )

            # 3. Eliminar compra (ON CASCADE eliminará items)
            self.db.execute_query("DELETE FROM compras WHERE id = ?", (compra_id,))

            # 4. REGISTRAR AUDITORÍA (eliminación de compra)
            if usuario_id:
                try:
                    from app.modules.auditoria_manager import AuditoriaManager
                    auditoria = AuditoriaManager(self.db)
                    auditoria.registrar_eliminacion(
                        usuario_id=usuario_id,
                        tabla='compras',
                        registro_id=compra_id,
                        descripcion=f"Compra {compra['numero_compra']} eliminada",
                        datos={'numero': compra['numero_compra'], 'total': compra.get('total')}
                    )
                except sqlite3.Error as audit_error:
                    logger.warning(f"Error registrando auditoría: {audit_error}")

            # CONFIRMAR TRANSACCIÓN - todos los cambios se guardan
            self.db.commit()

            msg = f"Compra {compra['numero_compra']} eliminada"
            if revertir_stock:
                msg += " (stock revertido)"
            else:
                msg += " (stock mantenido)"

            return True, msg

        except sqlite3.Error as e:
            # REVERTIR TRANSACCIÓN - deshacer todos los cambios
            self.db.rollback()
            logger.error(f"Error eliminando compra: {e}")
            return False, f"Error al eliminar compra: {str(e)}"
