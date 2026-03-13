"""
Gestor de caja
"""
import sqlite3
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
from app.utils.logger import get_logger

# Logger para el módulo de caja
logger = get_logger('caja')


def validar_fecha(fecha_str: Optional[str]) -> Tuple[bool, str]:
    """
    Valida que una fecha tenga formato correcto YYYY-MM-DD

    Args:
        fecha_str: String con la fecha a validar

    Returns:
        tuple: (bool, str) - (es_valida, fecha_normalizada o mensaje_error)
    """
    if not fecha_str:
        return False, "Fecha no puede estar vacía"

    try:
        # Intentar parsear la fecha
        fecha_obj = datetime.strptime(str(fecha_str), '%Y-%m-%d')
        # Retornar fecha normalizada
        return True, fecha_obj.strftime('%Y-%m-%d')
    except ValueError:
        try:
            # Intentar formato alternativo DD/MM/YYYY
            fecha_obj = datetime.strptime(str(fecha_str), '%d/%m/%Y')
            return True, fecha_obj.strftime('%Y-%m-%d')
        except ValueError:
            return False, f"Formato de fecha inválido: {fecha_str}. Use YYYY-MM-DD o DD/MM/YYYY"


class CajaManager:
    def __init__(self, db) -> None:
        self.db = db

    def obtener_saldo_actual(self) -> float:
        """Obtiene el saldo actual de caja desde la configuración"""
        config = self.db.fetch_one("SELECT valor FROM configuracion WHERE clave = 'saldo_caja'")
        if config and config.get('valor'):
            try:
                return float(config['valor'])
            except (ValueError, TypeError):
                return 0.0
        return 0.0

    def actualizar_saldo_caja(self, nuevo_saldo):
        """Actualiza el saldo de caja en la configuración (valor absoluto)"""
        self.db.execute_query(
            "UPDATE configuracion SET valor = ? WHERE clave = 'saldo_caja'",
            (str(nuevo_saldo),)
        )

    def ajustar_saldo_caja_atomico(self, cantidad, es_ingreso=True):
        """Ajusta el saldo de caja de forma atómica con UPDATE SQL.
        Previene race conditions al no usar READ-MODIFY-WRITE.

        Args:
            cantidad: Monto a sumar o restar
            es_ingreso: True para sumar, False para restar
        Returns:
            float: Nuevo saldo después del ajuste
        """
        if es_ingreso:
            self.db.execute_query(
                """UPDATE configuracion
                   SET valor = CAST(CAST(valor AS REAL) + ? AS TEXT)
                   WHERE clave = 'saldo_caja'""",
                (cantidad,)
            )
        else:
            self.db.execute_query(
                """UPDATE configuracion
                   SET valor = CAST(CAST(valor AS REAL) - ? AS TEXT)
                   WHERE clave = 'saldo_caja'""",
                (cantidad,)
            )
        return self.obtener_saldo_actual()

    def registrar_movimiento(self, datos):
        """Registra un movimiento manual de caja con transacción atómica

        IMPORTANTE: Solo los movimientos en EFECTIVO afectan el saldo de caja física.
        Movimientos en tarjeta/bizum se registran pero NO afectan saldo_caja.
        """
        # Validar fecha
        fecha_valida, fecha_resultado = validar_fecha(datos.get('fecha'))
        if not fecha_valida:
            logger.error(f"Fecha inválida en movimiento: {fecha_resultado}")
            return None
        datos['fecha'] = fecha_resultado  # Usar fecha normalizada

        # Iniciar transacción para prevenir race conditions
        if not self.db.begin_transaction():
            return None

        try:
            # Obtener método de pago (por defecto efectivo para compatibilidad)
            metodo_pago = datos.get('metodo_pago', 'efectivo')

            # Obtener saldo actual
            saldo_actual = self.obtener_saldo_actual()

            # Calcular nuevo saldo SOLO si el pago es en efectivo
            if metodo_pago == 'efectivo':
                if datos['tipo'] == 'ingreso':
                    nuevo_saldo = saldo_actual + datos['monto']
                else:  # egreso
                    nuevo_saldo = saldo_actual - datos['monto']

                    # VALIDACIÓN: Advertir si el saldo queda negativo
                    if nuevo_saldo < 0:
                        logger.warning(
                            f"Saldo de caja quedaría NEGATIVO: {nuevo_saldo:.2f}€ | "
                            f"Saldo actual: {saldo_actual:.2f}€ | "
                            f"Egreso: {datos['monto']:.2f}€ | "
                            f"Concepto: {datos['concepto']}"
                        )
                        # Permitir pero registrar el warning
            else:
                # Tarjeta/Bizum: NO afecta saldo de caja física
                nuevo_saldo = saldo_actual

            # Insertar movimiento
            movimiento_id = self.db.execute_query(
                """INSERT INTO caja_movimientos (tipo, categoria, concepto, monto, fecha,
                                                notas, saldo_anterior, saldo_nuevo, metodo_pago)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (datos['tipo'], datos['categoria'], datos['concepto'], datos['monto'],
                 datos['fecha'], datos.get('notas', ''), saldo_actual, nuevo_saldo, metodo_pago)
            )

            if movimiento_id:
                # Actualizar saldo atómicamente SOLO si es efectivo
                if metodo_pago == 'efectivo':
                    es_ingreso = datos['tipo'] == 'ingreso'
                    self.ajustar_saldo_caja_atomico(datos['monto'], es_ingreso=es_ingreso)
                self.db.commit()
                return movimiento_id
            else:
                self.db.rollback()
                return None

        except sqlite3.Error as e:
            self.db.rollback()
            logger.error(f"Error registrando movimiento de caja: {e}", exc_info=True)
            return None

    def registrar_movimiento_automatico(self, tipo, concepto, monto, fecha, ref_id, ref_type, metodo_pago='efectivo'):
        """Registra un movimiento automático desde otras operaciones (ventas, compras, reparaciones)

        IMPORTANTE: Solo actualiza saldo si metodo_pago='efectivo'.
        Tarjeta y Bizum se registran pero NO afectan el saldo de caja física.

        Args:
            tipo: 'ingreso' o 'egreso'
            concepto: Descripción del movimiento
            monto: Cantidad
            fecha: Fecha del movimiento
            ref_id: ID de referencia (venta, factura, etc.)
            ref_type: Tipo de referencia ('venta_caja', 'factura', etc.)
            metodo_pago: 'efectivo', 'tarjeta' o 'bizum' (default: 'efectivo')
        """
        # Validar fecha
        fecha_valida, fecha_resultado = validar_fecha(fecha)
        if not fecha_valida:
            logger.error(f"Fecha inválida en movimiento automático: {fecha_resultado}")
            return None
        fecha = fecha_resultado  # Usar fecha normalizada

        # Iniciar transacción para prevenir race conditions
        if not self.db.begin_transaction():
            return None

        try:
            # Obtener saldo actual
            saldo_actual = self.obtener_saldo_actual()

            # Calcular nuevo saldo SOLO si es efectivo
            if metodo_pago == 'efectivo':
                if tipo == 'ingreso':
                    nuevo_saldo = saldo_actual + monto
                else:  # egreso
                    nuevo_saldo = saldo_actual - monto

                    # VALIDACIÓN: Advertir si el saldo queda negativo
                    if nuevo_saldo < 0:
                        logger.warning(
                            f"Saldo de caja quedaría NEGATIVO: {nuevo_saldo:.2f}€ | "
                            f"Saldo actual: {saldo_actual:.2f}€ | "
                            f"Egreso automático: {monto:.2f}€ | "
                            f"Concepto: {concepto}"
                        )
                        # Permitir pero registrar el warning
            else:
                # Tarjeta/Bizum: NO afecta saldo de caja física
                nuevo_saldo = saldo_actual

            # Determinar categoría según tipo de referencia
            if tipo == 'ingreso':
                if ref_type == 'factura':
                    categoria = 'Venta Mostrador'
                elif ref_type == 'venta_caja':
                    categoria = 'Venta TPV'
                elif ref_type == 'reparacion':
                    categoria = 'Cobro Reparación'
                else:
                    categoria = 'Ingreso'
            else:  # egreso
                categoria = 'Compra Mercancía'

            # Insertar movimiento con metodo_pago
            movimiento_id = self.db.execute_query(
                """INSERT INTO caja_movimientos (tipo, categoria, concepto, monto, fecha,
                                                saldo_anterior, saldo_nuevo, referencia_id,
                                                referencia_tipo, metodo_pago)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (tipo, categoria, concepto, monto, fecha, saldo_actual, nuevo_saldo,
                 ref_id, ref_type, metodo_pago)
            )

            if movimiento_id:
                # Actualizar saldo atómicamente SOLO si es efectivo
                if metodo_pago == 'efectivo':
                    es_ingreso = tipo == 'ingreso'
                    self.ajustar_saldo_caja_atomico(monto, es_ingreso=es_ingreso)
                self.db.commit()
                return movimiento_id
            else:
                self.db.rollback()
                return None

        except sqlite3.Error as e:
            self.db.rollback()
            logger.error(f"Error registrando movimiento automático: {e}", exc_info=True)
            return None

    def obtener_movimientos(self, filtros=None):
        """Obtiene movimientos de caja con filtros opcionales"""
        query = """
            SELECT * FROM caja_movimientos
            WHERE 1=1
        """
        params = []

        if filtros:
            if filtros.get('tipo'):
                query += " AND tipo = ?"
                params.append(filtros['tipo'])

            if filtros.get('fecha_desde'):
                query += " AND fecha >= ?"
                params.append(filtros['fecha_desde'])

            if filtros.get('fecha_hasta'):
                query += " AND fecha <= ?"
                params.append(filtros['fecha_hasta'])

            if filtros.get('categoria'):
                query += " AND categoria = ?"
                params.append(filtros['categoria'])

        query += " ORDER BY fecha DESC, id DESC"

        # Limitar a los últimos 100 movimientos si no hay filtros de fecha
        if not filtros or (not filtros.get('fecha_desde') and not filtros.get('fecha_hasta')):
            query += " LIMIT 100"

        return self.db.fetch_all(query, params if params else None)

    def obtener_movimientos_paginado(self, filtros=None, limit=50, offset=0):
        """Obtiene movimientos con paginación. Retorna (movimientos, total_count)"""
        where_parts = []
        params = []

        if filtros:
            if filtros.get('tipo'):
                where_parts.append("tipo = ?")
                params.append(filtros['tipo'])
            if filtros.get('fecha_desde'):
                where_parts.append("fecha >= ?")
                params.append(filtros['fecha_desde'])
            if filtros.get('fecha_hasta'):
                where_parts.append("fecha <= ?")
                params.append(filtros['fecha_hasta'])
            if filtros.get('categoria'):
                where_parts.append("categoria = ?")
                params.append(filtros['categoria'])

        where_clause = " AND ".join(where_parts) if where_parts else "1=1"

        count_result = self.db.fetch_one(
            f"SELECT COUNT(*) as total FROM caja_movimientos WHERE {where_clause}",
            params if params else None
        )
        total = count_result['total'] if count_result else 0

        data_params = (params + [limit, offset]) if params else [limit, offset]
        movimientos = self.db.fetch_all(
            f"SELECT * FROM caja_movimientos WHERE {where_clause} ORDER BY fecha DESC, id DESC LIMIT ? OFFSET ?",
            data_params
        )

        return movimientos, total

    def calcular_totales_dia(self, fecha):
        """Calcula los totales de ingresos y egresos EN EFECTIVO para un día específico

        IMPORTANTE: Solo cuenta movimientos con metodo_pago='efectivo' porque:
        - Tarjeta/Bizum NO afectan el saldo de caja física
        - El cierre de caja es un arqueo de EFECTIVO
        """
        # Validar fecha
        fecha_valida, fecha_resultado = validar_fecha(fecha)
        if not fecha_valida:
            logger.error(f"Fecha inválida en calcular_totales_dia: {fecha_resultado}")
            return {'total_ingresos': 0.0, 'total_egresos': 0.0, 'saldo_esperado': 0.0}
        fecha = fecha_resultado  # Usar fecha normalizada

        # Total ingresos EN EFECTIVO (excluyendo tarjeta y bizum)
        resultado_ingresos = self.db.fetch_one(
            """SELECT SUM(monto) as total FROM caja_movimientos
               WHERE tipo = 'ingreso' AND fecha = ? AND metodo_pago = 'efectivo'""",
            (fecha,)
        )
        total_ingresos = resultado_ingresos['total'] if resultado_ingresos and resultado_ingresos['total'] else 0.0

        # Total egresos EN EFECTIVO (excluyendo tarjeta y bizum)
        resultado_egresos = self.db.fetch_one(
            """SELECT SUM(monto) as total FROM caja_movimientos
               WHERE tipo = 'egreso' AND fecha = ? AND metodo_pago = 'efectivo'""",
            (fecha,)
        )
        total_egresos = resultado_egresos['total'] if resultado_egresos and resultado_egresos['total'] else 0.0

        # Obtener saldo inicial del día (saldo anterior del primer movimiento del día)
        primer_movimiento = self.db.fetch_one(
            "SELECT saldo_anterior FROM caja_movimientos WHERE fecha = ? ORDER BY id ASC LIMIT 1",
            (fecha,)
        )
        saldo_inicial = primer_movimiento['saldo_anterior'] if primer_movimiento else self.obtener_saldo_actual()

        return {
            'saldo_inicial': saldo_inicial,
            'total_ingresos': total_ingresos,
            'total_egresos': total_egresos,
            'saldo_esperado': saldo_inicial + total_ingresos - total_egresos
        }

    def calcular_ingresos_por_metodo(self, fecha):
        """Calcula los ingresos del día desglosados por método de pago y categoría"""
        # Validar fecha
        fecha_valida, fecha_resultado = validar_fecha(fecha)
        if not fecha_valida:
            return {}
        fecha = fecha_resultado

        resultado = {
            'efectivo': {'total': 0.0, 'tpv': 0.0, 'ventas': 0.0, 'reparaciones': 0.0, 'otros': 0.0},
            'tarjeta': {'total': 0.0, 'tpv': 0.0, 'ventas': 0.0, 'reparaciones': 0.0, 'otros': 0.0},
            'bizum': {'total': 0.0, 'tpv': 0.0, 'ventas': 0.0, 'reparaciones': 0.0, 'otros': 0.0}
        }

        # Obtener todos los ingresos del día
        movimientos = self.db.fetch_all(
            """SELECT monto, metodo_pago, categoria, referencia_tipo
               FROM caja_movimientos
               WHERE tipo = 'ingreso' AND fecha = ?""",
            (fecha,)
        )

        for mov in movimientos:
            metodo = mov.get('metodo_pago', 'efectivo') or 'efectivo'
            monto = float(mov.get('monto', 0))
            categoria = mov.get('categoria', '') or ''
            ref_tipo = mov.get('referencia_tipo', '') or ''

            if metodo not in resultado:
                metodo = 'efectivo'

            resultado[metodo]['total'] += monto

            # Clasificar por tipo de ingreso
            if ref_tipo == 'venta_caja' or 'TPV' in categoria.upper():
                resultado[metodo]['tpv'] += monto
            elif ref_tipo == 'factura' or 'MOSTRADOR' in categoria.upper():
                resultado[metodo]['ventas'] += monto
            elif ref_tipo == 'reparacion' or 'REPARACIÓN' in categoria.upper() or 'REPARACION' in categoria.upper():
                resultado[metodo]['reparaciones'] += monto
            else:
                resultado[metodo]['otros'] += monto

        return resultado

    def realizar_cierre(self, datos):
        """Realiza un cierre de caja diario con transacción atómica

        IMPORTANTE: Todo el proceso (cierre + ajustes) se realiza en una transacción.
        Si algo falla, se revierte completamente.
        """
        # Iniciar transacción
        if not self.db.begin_transaction():
            return None

        try:
            # Calcular totales del día (solo efectivo)
            totales = self.calcular_totales_dia(datos['fecha'])

            # Calcular diferencia entre efectivo contado y esperado
            diferencia = datos['efectivo_contado'] - totales['saldo_esperado']

            # Insertar cierre
            cierre_id = self.db.execute_query(
                """INSERT INTO caja_cierres (fecha, saldo_inicial, total_ingresos, total_egresos,
                                            saldo_final, saldo_efectivo_contado, diferencia, notas, usuario_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (datos['fecha'], totales['saldo_inicial'], totales['total_ingresos'],
                 totales['total_egresos'], totales['saldo_esperado'], datos['efectivo_contado'],
                 diferencia, datos.get('notas', ''), datos.get('usuario_id'))
            )

            if not cierre_id:
                self.db.rollback()
                return None

            # Si hay diferencia, registrarla como movimiento de ajuste
            if abs(diferencia) > 0.01:  # Mayor a 1 céntimo
                # AUDITORÍA: Registrar quién aprobó el ajuste
                usuario_id = datos.get('usuario_id')

                if diferencia > 0:
                    # Sobrante - registrar como ingreso
                    ajuste_result = self.registrar_movimiento({
                        'tipo': 'ingreso',
                        'categoria': 'Ajuste de Cierre',
                        'concepto': f'Ajuste por cierre - Sobrante',
                        'monto': abs(diferencia),
                        'fecha': datos['fecha'],
                        'notas': f'Cierre ID {cierre_id} - Diferencia: +{diferencia:.2f}€ - Aprobado por usuario_id={usuario_id}',
                        'metodo_pago': 'efectivo',  # Explícito: es efectivo
                        'usuario_id': usuario_id  # AUDITORÍA
                    })
                else:
                    # Faltante - registrar como egreso
                    ajuste_result = self.registrar_movimiento({
                        'tipo': 'egreso',
                        'categoria': 'Ajuste de Cierre',
                        'concepto': f'Ajuste por cierre - Faltante',
                        'monto': abs(diferencia),
                        'fecha': datos['fecha'],
                        'notas': f'Cierre ID {cierre_id} - Diferencia: {diferencia:.2f}€ - Aprobado por usuario_id={usuario_id}',
                        'metodo_pago': 'efectivo',  # Explícito: es efectivo
                        'usuario_id': usuario_id  # AUDITORÍA
                    })

                if not ajuste_result:
                    self.db.rollback()
                    return None

            # Todo bien, confirmar transacción
            self.db.commit()
            return cierre_id

        except sqlite3.Error as e:
            self.db.rollback()
            logger.error(f"Error realizando cierre de caja: {e}", exc_info=True)
            return None

    def obtener_cierres(self, filtros=None):
        """Obtiene histórico de cierres de caja"""
        query = "SELECT * FROM caja_cierres WHERE 1=1"
        params = []

        if filtros:
            if filtros.get('fecha_desde'):
                query += " AND fecha >= ?"
                params.append(filtros['fecha_desde'])

            if filtros.get('fecha_hasta'):
                query += " AND fecha <= ?"
                params.append(filtros['fecha_hasta'])

        query += " ORDER BY fecha DESC, id DESC"

        return self.db.fetch_all(query, params if params else None)

    def obtener_cierre(self, cierre_id):
        """Obtiene un cierre específico por ID"""
        return self.db.fetch_one(
            "SELECT * FROM caja_cierres WHERE id = ?",
            (cierre_id,)
        )

    def verificar_cierre_existente(self, fecha):
        """Verifica si ya existe un cierre para una fecha"""
        cierre = self.db.fetch_one(
            "SELECT id FROM caja_cierres WHERE fecha = ?",
            (fecha,)
        )
        return cierre is not None

    # ========== MÉTODOS DE APERTURA DE CAJA ==========

    def obtener_ultima_apertura(self):
        """Obtiene la última apertura registrada"""
        return self.db.fetch_one(
            "SELECT * FROM aperturas_caja ORDER BY fecha DESC LIMIT 1"
        )

    def obtener_ultimo_cierre(self):
        """Obtiene el último cierre registrado"""
        return self.db.fetch_one(
            "SELECT * FROM caja_cierres ORDER BY fecha DESC LIMIT 1"
        )

    def verificar_apertura_existente(self, fecha):
        """Verifica si ya existe apertura para una fecha"""
        apertura = self.db.fetch_one(
            "SELECT id FROM aperturas_caja WHERE fecha = ?",
            (fecha,)
        )
        return apertura is not None

    def registrar_apertura(self, datos):
        """
        Registra una apertura de caja.
        datos = {
            'fecha': 'YYYY-MM-DD',
            'saldo_inicial': float,
            'usuario_id': int,
            'notas': str
        }
        """
        # Iniciar transacción para garantizar consistencia
        if not self.db.begin_transaction():
            return None

        try:
            apertura_id = self.db.execute_query(
                """INSERT INTO aperturas_caja (fecha, saldo_inicial, usuario_id, notas)
                   VALUES (?, ?, ?, ?)""",
                (datos['fecha'], datos['saldo_inicial'], datos.get('usuario_id'),
                 datos.get('notas', ''))
            )

            # Actualizar saldo de caja en configuración
            if apertura_id:
                self.actualizar_saldo_caja(datos['saldo_inicial'])
                self.db.commit()
                return apertura_id
            else:
                self.db.rollback()
                return None

        except sqlite3.Error as e:
            self.db.rollback()
            logger.error(f"Error registrando apertura: {e}", exc_info=True)
            return None

    def eliminar_cierre(self, cierre_id):
        """
        Elimina/anula un cierre de caja (para reapertura del día).
        IMPORTANTE:
        - Elimina movimientos de ajuste asociados al cierre
        - Revierte el saldo de caja al estado anterior al cierre
        - Todo en una transacción atómica
        """
        # Verificar que existe
        cierre = self.db.fetch_one(
            "SELECT * FROM caja_cierres WHERE id = ?",
            (cierre_id,)
        )

        if not cierre:
            return False, "Cierre no encontrado"

        # VERIFICAR que no existan cierres o aperturas posteriores
        # Esto previene romper la cadena de saldos
        cierre_posterior = self.db.fetch_one(
            "SELECT id, fecha FROM caja_cierres WHERE fecha > ? ORDER BY fecha ASC LIMIT 1",
            (cierre['fecha'],)
        )

        if cierre_posterior:
            return False, f"No se puede eliminar este cierre. Existe un cierre posterior del {cierre_posterior['fecha']}. Debe eliminar los cierres posteriores primero."

        apertura_posterior = self.db.fetch_one(
            "SELECT id, fecha FROM aperturas_caja WHERE fecha > ? ORDER BY fecha ASC LIMIT 1",
            (cierre['fecha'],)
        )

        if apertura_posterior:
            return False, f"No se puede eliminar este cierre. Existe una apertura posterior del {apertura_posterior['fecha']}. Debe eliminar las aperturas posteriores primero."

        # TRANSACCIÓN ATÓMICA: Todo o nada
        if not self.db.begin_transaction():
            return False, "Error iniciando transacción"

        try:
            # 1. ELIMINAR MOVIMIENTOS DE AJUSTE asociados al cierre
            # Los ajustes tienen categoria='Ajuste de Cierre' y notas con "Cierre ID {cierre_id}"
            self.db.execute_query(
                """DELETE FROM caja_movimientos
                   WHERE categoria = 'Ajuste de Cierre'
                   AND notas LIKE ?""",
                (f'Cierre ID {cierre_id}%',)
            )

            # 2. RESTAURAR SALDO al inicial del día
            self.actualizar_saldo_caja(cierre['saldo_inicial'])

            # 3. ELIMINAR CIERRE
            self.db.execute_query(
                "DELETE FROM caja_cierres WHERE id = ?",
                (cierre_id,)
            )

            self.db.commit()
            return True, "Cierre eliminado correctamente"

        except sqlite3.Error as e:
            self.db.rollback()
            logger.error(f"Error eliminando cierre: {e}", exc_info=True)
            return False, f"Error eliminando cierre: {str(e)}"

    def verificar_necesita_apertura(self, fecha_venta):
        """
        Verifica si se necesita apertura para una venta en fecha_venta.

        Returns:
            ('apertura_requerida', None) - Primera venta, pedir apertura
            ('reapertura_requerida', cierre_obj) - Ya cerrado hoy, pedir reapertura
            ('apertura_nueva_dia', None) - Nuevo día, pedir apertura
            ('ok', apertura_obj) - Todo bien, hay apertura
        """
        # PRIMERO: Verificar si ya existe apertura para la fecha de venta
        if self.verificar_apertura_existente(fecha_venta):
            apertura = self.db.fetch_one(
                "SELECT * FROM aperturas_caja WHERE fecha = ?",
                (fecha_venta,)
            )
            return ('ok', apertura)

        # Si no hay apertura, verificar cierres
        ultimo_cierre = self.obtener_ultimo_cierre()

        # CASO C: Primera venta ever (no hay cierres ni apertura)
        if not ultimo_cierre:
            return ('apertura_requerida', None)

        fecha_ultimo_cierre = ultimo_cierre['fecha']

        # CASO B: Fecha de venta es IGUAL a fecha del último cierre
        if fecha_venta == fecha_ultimo_cierre:
            return ('reapertura_requerida', ultimo_cierre)

        # CASO A: Fecha de venta es DESPUÉS del último cierre (nuevo día sin apertura)
        if fecha_venta > fecha_ultimo_cierre:
            return ('apertura_nueva_dia', None)

        # Fecha de venta es ANTES del último cierre (venta retroactiva - permitir)
        return ('ok', None)

    def obtener_apertura_sin_cierre(self):
        """
        Busca si hay alguna apertura que NO tenga cierre correspondiente.
        Esto detecta días que se abrieron pero nunca se cerraron.
        
        Returns:
            dict con datos de la apertura pendiente o None si todo está cerrado
        """
        return self.db.fetch_one("""
            SELECT a.* FROM aperturas_caja a
            LEFT JOIN caja_cierres c ON a.fecha = c.fecha
            WHERE c.id IS NULL
            ORDER BY a.fecha ASC
            LIMIT 1
        """)

    def verificar_estado_caja_completo(self, fecha_operacion):
        """
        Verificación COMPLETA del estado de caja para cualquier operación de cobro.
        Esta función unifica la verificación para TPV, Ventas y SAT.
        
        IMPORTANTE: Primero verifica si hay días anteriores sin cerrar.
        
        Returns:
            ('cierre_pendiente', apertura_sin_cerrar) - Hay día anterior sin cerrar → BLOQUEAR
            ('apertura_requerida', None) - Primera vez ever, pedir apertura
            ('apertura_nueva_dia', None) - Nuevo día sin apertura
            ('reapertura_requerida', cierre) - Ya cerrado hoy, ofrecer reapertura
            ('ok', apertura) - Todo correcto, proceder con la operación
        """
        # PASO 1: Verificar si hay apertura de día ANTERIOR sin cierre
        apertura_pendiente = self.obtener_apertura_sin_cierre()
        
        if apertura_pendiente:
            fecha_pendiente = apertura_pendiente['fecha']
            # Solo bloquear si es de un día ANTERIOR (no de hoy)
            if fecha_pendiente < fecha_operacion:
                logger.warning(
                    f"Cierre pendiente detectado: {fecha_pendiente} | "
                    f"Fecha operación: {fecha_operacion}"
                )
                return ('cierre_pendiente', apertura_pendiente)
        
        # PASO 2: Si no hay pendientes de días anteriores, usar lógica existente
        return self.verificar_necesita_apertura(fecha_operacion)
