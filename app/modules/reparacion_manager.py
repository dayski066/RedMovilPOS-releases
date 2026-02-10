"""
Gestor de reparaciones (SAT)
Incluye generación de códigos QR para localización rápida de órdenes
"""
import sqlite3
from app.utils.qr_generator import QRGenerator
from app.utils.logger import get_logger

logger = get_logger('reparacion')


class ReparacionManager:
    def __init__(self, db):
        self.db = db
        self.qr_generator = QRGenerator()

    def obtener_siguiente_numero(self):
        """
        Obtiene el siguiente número de orden (formato O00001) de forma atómica.
        Usa UPDATE + SELECT para evitar condiciones de carrera.
        """
        # Actualizar atómicamente e incrementar en 1
        self.db.execute_query(
            """UPDATE configuracion
               SET valor = CAST(CAST(valor AS INTEGER) + 1 AS TEXT)
               WHERE clave = 'ultimo_numero_reparacion'"""
        )

        # Obtener el valor actualizado
        config = self.db.fetch_one(
            "SELECT valor FROM configuracion WHERE clave = 'ultimo_numero_reparacion'"
        )

        if config:
            siguiente = int(config['valor'])
        else:
            # Si no existe, crear con valor 1
            siguiente = 1
            self.db.execute_query(
                "INSERT INTO configuracion (clave, valor) VALUES ('ultimo_numero_reparacion', '1')"
            )

        return f"O{siguiente:05d}"  # O00001, O00002, etc.

    def actualizar_numero_reparacion(self, numero):
        """
        Ya no es necesario llamar este método después de guardar_reparacion.
        Se mantiene por compatibilidad, pero obtener_siguiente_numero ya actualiza el valor.
        """
        pass  # La actualización ya se hace en obtener_siguiente_numero

    def guardar_reparacion(self, datos, usuario_id=None):
        """
        Guarda una reparación con múltiples dispositivos.

        TRANSACCIONAL: Todas las operaciones se realizan en una transacción.
        Si cualquier operación falla, se revierten TODOS los cambios.

        Operaciones incluidas:
        1. INSERT clientes (si es necesario)
        2. INSERT reparaciones
        3. INSERT reparaciones_items (múltiples)
        4. Registro en historial de auditoría
        """
        # INICIAR TRANSACCIÓN
        if not self.db.begin_transaction():
            logger.error("No se pudo iniciar transacción para guardar reparación")
            return None

        try:
            # Validar datos básicos
            if not datos.get('items'):
                raise ValueError("La reparación debe tener al menos un dispositivo")

            # 1. Guardar/Buscar Cliente
            cliente_id = None
            if datos['cliente'].get('id'):
                cliente_id = datos['cliente']['id']
            else:
                # Buscar cliente existente por NIF (case-insensitive) o por nombre
                nif_cliente = datos['cliente'].get('nif', '').strip()
                nombre_cliente = datos['cliente'].get('nombre', '').strip()
                cliente_existente = None
                
                # Primero buscar por NIF si existe
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
                    # Crear cliente si no existe
                    cliente_id = self.db.execute_query(
                        "INSERT INTO clientes (nombre, nif, direccion, codigo_postal, ciudad, telefono) VALUES (?, ?, ?, ?, ?, ?)",
                        (nombre_cliente, nif_cliente,
                         datos['cliente'].get('direccion', ''), datos['cliente'].get('codigo_postal', ''),
                         datos['cliente'].get('ciudad', ''), datos['cliente'].get('telefono', ''))
                    )

                    if not cliente_id:
                        raise Exception("No se pudo crear el cliente")

            # 2. Insertar Reparación (Cabecera)
            # Calculamos totales basados en los items
            costo_estimado_total = 0
            for item in datos['items']:
                precio = item.get('precio_estimado', 0)
                if precio < 0:
                    raise ValueError(f"Precio estimado inválido: {precio}")
                costo_estimado_total += precio

            # Usamos los datos del PRIMER dispositivo como resumen para compatibilidad con campos legacy
            primer_item = datos['items'][0] if datos['items'] else {}
            dispositivo_resumen = f"{primer_item.get('marca_nombre','')} {primer_item.get('modelo_nombre','')}"

            # Generar código QR para la orden (opcional, no bloquea la creación)
            try:
                qr_code = self.qr_generator.generar_qr_reparacion(datos['numero'])
            except Exception:
                qr_code = None

            reparacion_id = self.db.execute_query(
                """INSERT INTO reparaciones (
                    numero_orden, cliente_id, cliente_nombre, cliente_nif, cliente_direccion,
                    cliente_codigo_postal, cliente_ciudad, cliente_telefono,
                    dispositivo, imei, problema_descripcion,
                    costo_estimado, fecha_entrada, estado, qr_code
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (datos['numero'], cliente_id,
                 datos['cliente']['nombre'],
                 datos['cliente'].get('nif', ''),
                 datos['cliente'].get('direccion', ''),
                 datos['cliente'].get('codigo_postal', ''),
                 datos['cliente'].get('ciudad', ''),
                 datos['cliente'].get('telefono', ''),
                 dispositivo_resumen, primer_item.get('imei',''), primer_item.get('averia',''),
                 costo_estimado_total, datos['fecha'], 'pendiente', qr_code)
            )

            if not reparacion_id:
                raise Exception("No se pudo insertar la reparación")

            # 3. Insertar Items y sus Averías
            for item in datos['items']:
                # Insertar el dispositivo/item
                item_id = self.db.execute_query(
                    """INSERT INTO reparaciones_items (
                        reparacion_id, marca_id, modelo_id, imei,
                        averia, patron_codigo, notas, precio_estimado,
                        averia_texto, solucion_texto
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (reparacion_id, item['marca_id'], item['modelo_id'], item['imei'],
                     item.get('averia', ''), item.get('patron_codigo', ''), item.get('notas', ''),
                     item.get('precio_estimado', 0),
                     item.get('averia_texto'), item.get('solucion_texto'))
                )

                if not item_id:
                    raise Exception(f"No se pudo insertar dispositivo con IMEI: {item.get('imei')}")

                # Insertar las averías del dispositivo
                averias = item.get('averias', [])
                for orden, averia in enumerate(averias, 1):
                    averia_id = self.db.execute_query(
                        """INSERT INTO reparaciones_averias (
                            reparacion_item_id, descripcion_averia, solucion, precio, orden
                        ) VALUES (?, ?, ?, ?, ?)""",
                        (item_id, averia['averia_texto'], averia['solucion_texto'],
                         averia['precio'], orden)
                    )

                    if not averia_id:
                        raise Exception(f"No se pudo insertar avería: {averia.get('averia_texto')}")

            # 4. REGISTRAR AUDITORÍA (creación de reparación)
            if usuario_id:
                try:
                    from app.modules.auditoria_manager import AuditoriaManager
                    auditoria = AuditoriaManager(self.db)
                    auditoria.registrar_creacion(
                        usuario_id=usuario_id,
                        tabla='reparaciones',
                        registro_id=reparacion_id,
                        descripcion=f"Reparación {datos['numero']} creada - {datos['cliente']['nombre']}",
                        datos={'numero': datos['numero'], 'cliente': datos['cliente'].get('nombre'), 'dispositivo': dispositivo_resumen}
                    )
                except (sqlite3.Error, ValueError) as audit_error:
                    logger.warning(f"Error registrando auditoría: {audit_error}")

            # CONFIRMAR TRANSACCIÓN - Todo salió bien
            self.db.commit()
            logger.info(f"Reparación {datos['numero']} guardada exitosamente")
            return reparacion_id

        except (sqlite3.Error, OSError, ValueError) as e:
            # REVERTIR TRANSACCIÓN - Algo falló
            self.db.rollback()
            logger.error(f"Error guardando reparación (transacción revertida): {e}")
            return None

    def obtener_reparacion(self, reparacion_id):
        """Obtiene reparación completa con items y averías"""
        reparacion = self.db.fetch_one("SELECT * FROM reparaciones WHERE id = ?", (reparacion_id,))
        if reparacion:
            # Convertir a diccionario para poder modificarlo
            reparacion = dict(reparacion)
            items = self.db.fetch_all(
                """SELECT ri.*, m.nombre as marca_nombre, mod.nombre as modelo_nombre
                   FROM reparaciones_items ri
                   LEFT JOIN marcas m ON ri.marca_id = m.id
                   LEFT JOIN modelos mod ON ri.modelo_id = mod.id
                   WHERE ri.reparacion_id = ?
                   ORDER BY ri.id""",
                (reparacion_id,)
            )

            # Para cada item, obtener sus averías
            items_con_averias = []
            for item in items:
                item_dict = dict(item)
                averias = self.db.fetch_all(
                    """SELECT * FROM reparaciones_averias
                       WHERE reparacion_item_id = ?
                       ORDER BY orden""",
                    (item['id'],)
                )
                item_dict['averias'] = [dict(a) for a in averias] if averias else []
                items_con_averias.append(item_dict)

            reparacion['items'] = items_con_averias
        return reparacion

    def buscar_por_qr(self, qr_data: str):
        """
        Busca una reparación por código QR escaneado.

        Args:
            qr_data: Datos leídos del QR (ej: "SAT:O00001" o "O00001")

        Returns:
            dict: Datos de la reparación completa o None si no se encuentra
        """
        # Extraer el número de orden del QR
        numero_orden = self.qr_generator.extraer_numero_orden(qr_data)

        if not numero_orden:
            logger.warning(f"Código QR inválido: {qr_data}")
            return None

        # Buscar por número de orden
        reparacion = self.db.fetch_one(
            "SELECT * FROM reparaciones WHERE numero_orden = ?",
            (numero_orden,)
        )

        if not reparacion:
            logger.warning(f"No se encontró reparación con número: {numero_orden}")
            return None

        # Obtener datos completos usando la función existente
        return self.obtener_reparacion(reparacion['id'])

    def buscar_reparaciones(self, filtros=None):
        """Busca reparaciones con filtros opcionales"""
        query = "SELECT * FROM reparaciones WHERE 1=1"
        params = []

        if filtros:
            if filtros.get('fecha_desde'):
                query += " AND fecha_entrada >= ?"
                params.append(filtros['fecha_desde'])
            
            if filtros.get('fecha_hasta'):
                query += " AND fecha_entrada <= ?"
                params.append(filtros['fecha_hasta'])
            
            if filtros.get('cliente'):
                query += " AND cliente_nombre LIKE ?"
                params.append(f"%{filtros['cliente']}%")
            
            if filtros.get('numero'):
                query += " AND numero_orden LIKE ?"
                params.append(f"%{filtros['numero']}%")
            
            if filtros.get('estado'):
                query += " AND estado = ?"
                params.append(filtros['estado'])

        query += " ORDER BY fecha_entrada DESC, id DESC"
        return self.db.fetch_all(query, params if params else None)

    def actualizar_estado(self, reparacion_id, nuevo_estado, metodo_pago='efectivo', usuario_id=None):
        """
        Actualiza el estado de una reparación.
        Si el estado cambia a 'entregado', registra automáticamente el ingreso en caja.
        
        TRANSACCIONAL: Todo se hace en una transacción atómica.
        """
        # Obtener reparación para verificar estado anterior y monto
        reparacion = self.obtener_reparacion(reparacion_id)
        if not reparacion:
            raise Exception("Reparación no encontrada")

        estado_anterior = reparacion.get('estado')

        # INICIAR TRANSACCIÓN
        if not self.db.begin_transaction():
            raise Exception("No se pudo iniciar transacción")

        try:
            # Actualizar estado
            self.db.execute_query(
                "UPDATE reparaciones SET estado = ?, fecha_entrega = CASE WHEN ? = 'entregado' THEN DATE('now') ELSE fecha_entrega END WHERE id = ?",
                (nuevo_estado, nuevo_estado, reparacion_id)
            )

            # Si cambia a 'entregado' y antes no lo estaba, registrar ingreso en caja
            if nuevo_estado == 'entregado' and estado_anterior != 'entregado':
                # Usar costo_final si existe, sino costo_estimado
                monto = reparacion.get('costo_final') or reparacion.get('costo_estimado') or 0

                if monto > 0:
                    from app.modules.caja_manager import CajaManager
                    caja_mgr = CajaManager(self.db)

                    fecha_hoy = self.db.fetch_one("SELECT DATE('now') as fecha")['fecha']
                    
                    # Verificar estado de caja antes de registrar
                    estado_caja, data_caja = caja_mgr.verificar_estado_caja_completo(fecha_hoy)
                    
                    if estado_caja == 'cierre_pendiente':
                        fecha_pendiente = data_caja['fecha'] if data_caja else 'anterior'
                        raise Exception(f"Hay una caja del dia {fecha_pendiente} sin cerrar.\n\nVaya a: Caja -> Movimientos\nUse el boton [Cerrar Caja]")

                    if estado_caja in ['apertura_requerida', 'apertura_nueva_dia']:
                        raise Exception(f"La caja de hoy no esta abierta.\n\nVaya a: Caja -> Movimientos\nUse el boton [Abrir Caja]")

                    if estado_caja == 'reapertura_requerida':
                        raise Exception(f"La caja de hoy ya fue cerrada.\n\nVaya a: Caja -> Movimientos\nPara reabrir la caja")

                    if estado_caja != 'ok':
                        raise Exception(f"Estado de caja no valido: {estado_caja}.\n\nVaya a: Caja -> Movimientos")

                    movimiento_id = caja_mgr.registrar_movimiento_automatico(
                        tipo='ingreso',
                        concepto=f"Reparación {reparacion['numero_orden']} - {reparacion['cliente_nombre']}",
                        monto=monto,
                        fecha=fecha_hoy,
                        ref_id=reparacion_id,
                        ref_type='reparacion',
                        metodo_pago=metodo_pago
                    )

                    if not movimiento_id:
                        raise Exception("No se pudo registrar el movimiento de caja")

                    logger.info(f"Ingreso registrado en caja: {monto}€ por reparación {reparacion['numero_orden']}")

            # REGISTRAR AUDITORÍA (cambio de estado)
            if usuario_id:
                try:
                    from app.modules.auditoria_manager import AuditoriaManager
                    auditoria = AuditoriaManager(self.db)
                    auditoria.registrar_edicion(
                        usuario_id=usuario_id,
                        tabla='reparaciones',
                        registro_id=reparacion_id,
                        descripcion=f"Reparación {reparacion['numero_orden']} cambiada a '{nuevo_estado}'",
                        datos_anteriores={'estado': estado_anterior},
                        datos_nuevos={'estado': nuevo_estado}
                    )
                except (sqlite3.Error, ValueError) as audit_error:
                    logger.warning(f"Error registrando auditoría: {audit_error}")

            # CONFIRMAR TRANSACCIÓN
            self.db.commit()
            logger.info(f"Estado de reparación {reparacion['numero_orden']} actualizado a '{nuevo_estado}'")

        except (sqlite3.Error, OSError, ValueError) as e:
            # REVERTIR TRANSACCIÓN
            self.db.rollback()
            logger.error(f"Error actualizando reparación (transacción revertida): {e}")
            raise e

    def eliminar_reparacion(self, reparacion_id, usuario_id=None):
        """Elimina una reparación y sus items"""
        reparacion = self.obtener_reparacion(reparacion_id)
        if not reparacion:
            return False, "Reparación no encontrada"

        try:
            # Eliminar movimiento de caja si existe (opcional, si se ligó a caja)
            self.db.execute_query(
                "DELETE FROM caja_movimientos WHERE reparacion_id = ?",
                (reparacion_id,)
            )

            # Eliminar reparación (ON DELETE CASCADE debería borrar items, pero por seguridad...)
            self.db.execute_query("DELETE FROM reparaciones_items WHERE reparacion_id = ?", (reparacion_id,))
            self.db.execute_query("DELETE FROM reparaciones WHERE id = ?", (reparacion_id,))

            # REGISTRAR AUDITORÍA (eliminación)
            if usuario_id:
                try:
                    from app.modules.auditoria_manager import AuditoriaManager
                    auditoria = AuditoriaManager(self.db)
                    auditoria.registrar_eliminacion(
                        usuario_id=usuario_id,
                        tabla='reparaciones',
                        registro_id=reparacion_id,
                        descripcion=f"Reparación {reparacion['numero_orden']} eliminada",
                        datos={'numero': reparacion['numero_orden'], 'cliente': reparacion.get('cliente_nombre')}
                    )
                except (sqlite3.Error, ValueError) as audit_error:
                    logger.warning(f"Error registrando auditoría: {audit_error}")

            return True, f"Orden {reparacion['numero_orden']} eliminada correctamente"
        except (sqlite3.Error, OSError, ValueError) as e:
            return False, f"Error al eliminar: {str(e)}"

    def guardar_recambios(self, reparacion_id, recambios, usuario_id=None):
        """
        Guarda los recambios utilizados en una reparación.

        TRANSACCIONAL: Si falla alguna operación, revierte todo.

        Args:
            reparacion_id: ID de la reparación
            recambios: Lista de recambios [{descripcion, cantidad, precio_unitario, producto_id?, codigo_ean?}]
            usuario_id: ID del usuario para auditoría

        Returns:
            True si éxito, False si error
        """
        if not recambios:
            return True  # No hay recambios que guardar

        # Obtener datos de la reparación para auditoría
        reparacion = self.obtener_reparacion(reparacion_id)
        if not reparacion:
            logger.error(f"Reparación {reparacion_id} no encontrada")
            return False

        # INICIAR TRANSACCIÓN
        if not self.db.begin_transaction():
            logger.error("No se pudo iniciar transacción para recambios")
            return False

        try:
            for recambio in recambios:
                producto_id = recambio.get('producto_id')
                descripcion = recambio.get('descripcion', '')
                cantidad = int(recambio.get('cantidad', 1))
                precio_unitario = float(recambio.get('precio_unitario', 0))
                codigo_ean = recambio.get('codigo_ean', '')

                # Si tiene producto_id, verificar y descontar stock
                if producto_id:
                    # Verificar stock disponible
                    producto = self.db.fetch_one(
                        "SELECT id, descripcion, stock, codigo_ean FROM productos WHERE id = ?",
                        (producto_id,)
                    )

                    if not producto:
                        raise Exception(f"Producto ID {producto_id} no encontrado")

                    stock_actual = producto.get('stock', 0) or 0
                    if stock_actual < cantidad:
                        raise Exception(
                            f"Stock insuficiente para '{producto['descripcion']}'. "
                            f"Disponible: {stock_actual}, Solicitado: {cantidad}"
                        )

                    # Descontar stock
                    result = self.db.execute_query(
                        "UPDATE productos SET stock = stock - ? WHERE id = ?",
                        (cantidad, producto_id)
                    )

                    if result is None:
                        raise Exception(f"No se pudo descontar stock del producto ID {producto_id}")

                    # Usar código EAN del producto si no se especificó
                    if not codigo_ean:
                        codigo_ean = producto.get('codigo_ean', '')

                # Insertar en reparaciones_recambios
                recambio_id = self.db.execute_query(
                    """INSERT INTO reparaciones_recambios
                       (reparacion_id, producto_id, descripcion, cantidad, precio_unitario, codigo_ean)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (reparacion_id, producto_id, descripcion, cantidad, precio_unitario, codigo_ean)
                )

                if not recambio_id:
                    raise Exception(f"No se pudo insertar recambio: {descripcion}")

            # Registrar en auditoría
            if usuario_id:
                try:
                    from app.modules.auditoria_manager import AuditoriaManager
                    auditoria = AuditoriaManager(self.db)

                    # Calcular total de recambios
                    total_recambios = sum(
                        float(r.get('cantidad', 1)) * float(r.get('precio_unitario', 0))
                        for r in recambios
                    )

                    auditoria.registrar_edicion(
                        usuario_id=usuario_id,
                        tabla='reparaciones',
                        registro_id=reparacion_id,
                        descripcion=f"Recambios añadidos a {reparacion['numero_orden']} - {len(recambios)} items - Total: {total_recambios:.2f}€",
                        datos_anteriores={},
                        datos_nuevos={'recambios': len(recambios), 'total': total_recambios}
                    )
                except (sqlite3.Error, ValueError) as audit_error:
                    logger.warning(f"Error registrando auditoría: {audit_error}")

            # CONFIRMAR TRANSACCIÓN
            self.db.commit()
            logger.info(f"{len(recambios)} recambios guardados para reparación {reparacion['numero_orden']}")
            return True

        except (sqlite3.Error, OSError, ValueError) as e:
            # REVERTIR TRANSACCIÓN
            self.db.rollback()
            logger.error(f"Error guardando recambios (transacción revertida): {e}")
            raise e

    def obtener_recambios(self, reparacion_id):
        """
        Obtiene los recambios asociados a una reparación.

        Args:
            reparacion_id: ID de la reparación

        Returns:
            Lista de recambios con información del producto si existe
        """
        recambios = self.db.fetch_all(
            """SELECT rr.*, p.descripcion as producto_descripcion, p.stock as producto_stock
               FROM reparaciones_recambios rr
               LEFT JOIN productos p ON rr.producto_id = p.id
               WHERE rr.reparacion_id = ?
               ORDER BY rr.fecha_creacion""",
            (reparacion_id,)
        )
        return recambios if recambios else []

    def buscar_producto_por_ean(self, codigo_ean):
        """
        Busca un producto por su código EAN.

        Args:
            codigo_ean: Código EAN del producto

        Returns:
            Dict con datos del producto o None si no existe
        """
        if not codigo_ean:
            return None

        producto = self.db.fetch_one(
            """SELECT id, codigo_ean, descripcion, precio, stock
               FROM productos
               WHERE codigo_ean = ? AND activo = 1""",
            (codigo_ean,)
        )
        return producto
