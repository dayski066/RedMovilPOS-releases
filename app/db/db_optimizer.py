"""
Optimizador de base de datos para REDMOVILPOS
Crea y gestiona índices para mejorar el rendimiento
"""
import sqlite3
import re

from app.utils.logger import get_logger

logger = get_logger('db_optimizer')


class DatabaseOptimizer:
    """
    Gestor de optimización de base de datos

    SEGURIDAD: Todos los nombres de tablas, índices y columnas se validan
    contra una lista blanca para prevenir SQL injection.
    """

    # Lista blanca de tablas permitidas
    TABLAS_PERMITIDAS = {
        'clientes', 'productos', 'facturas', 'factura_items',
        'usuarios', 'compras', 'compras_items', 'reparaciones',
        'reparaciones_items', 'categorias', 'marcas', 'modelos',
        'ventas_caja', 'ventas_caja_items', 'caja_movimientos', 'caja_cierres',
        'establecimientos', 'permisos', 'roles', 'rol_permisos',
        'auditoria', 'configuracion', 'productos_favoritos', 'averias',
        'soluciones', 'intentos_login'
    }

    # Patrón para validar nombres de identificadores SQL
    PATRON_IDENTIFICADOR = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

    def _validar_identificador(self, nombre: str) -> bool:
        """Valida que un nombre sea un identificador SQL seguro"""
        return bool(self.PATRON_IDENTIFICADOR.match(nombre))

    def _validar_tabla(self, tabla: str) -> bool:
        """Valida que una tabla esté en la lista blanca"""
        return tabla in self.TABLAS_PERMITIDAS

    def __init__(self, db):
        """
        Inicializa el optimizador

        Args:
            db: Instancia de Database
        """
        self.db = db

    def obtener_indices_existentes(self):
        """
        Obtiene todos los índices existentes en la base de datos

        Returns:
            list: Lista de índices con tabla y nombre
        """
        try:
            indices = self.db.fetch_all("""
                SELECT
                    m.name as tabla,
                    il.name as indice,
                    GROUP_CONCAT(ii.name) as columnas
                FROM sqlite_master m
                LEFT JOIN pragma_index_list(m.name) il ON 1=1
                LEFT JOIN pragma_index_info(il.name) ii ON 1=1
                WHERE m.type = 'table'
                  AND il.name IS NOT NULL
                  AND il.origin != 'pk'
                GROUP BY m.name, il.name
                ORDER BY m.name, il.name
            """)
            return indices
        except sqlite3.Error as e:
            logger.error(f"Error obteniendo índices: {e}")
            return []

    def analizar_indices(self):
        """
        Analiza los índices existentes y muestra estadísticas

        Returns:
            dict: Estadísticas de índices
        """
        indices = self.obtener_indices_existentes()

        stats = {
            'total_indices': len(indices),
            'por_tabla': {}
        }

        for idx in indices:
            tabla = idx['tabla']
            if tabla not in stats['por_tabla']:
                stats['por_tabla'][tabla] = []
            stats['por_tabla'][tabla].append({
                'nombre': idx['indice'],
                'columnas': idx['columnas']
            })

        return stats

    def crear_indices_clientes(self):
        """
        Crea índices optimizados para la tabla clientes

        Índices creados:
        - nif: Búsquedas rápidas por NIF/CIF
        - nombre: Búsquedas y ordenamiento por nombre
        - telefono: Búsquedas por teléfono
        """
        logger.info("Optimizando tabla: clientes")

        indices = [
            ("idx_clientes_nif", "clientes", "nif"),
            ("idx_clientes_nombre", "clientes", "nombre"),
            ("idx_clientes_telefono", "clientes", "telefono"),
        ]

        for nombre, tabla, columna in indices:
            self._crear_indice_si_no_existe(nombre, tabla, columna)

    def crear_indices_productos(self):
        """
        Crea índices optimizados para la tabla productos

        Índices creados:
        - categoria: Filtrado por categoría
        - precio: Búsquedas por rango de precio
        - descripcion: Búsquedas y ordenamiento por nombre
        """
        logger.info("Optimizando tabla: productos")

        indices = [
            ("idx_productos_categoria", "productos", "categoria"),
            ("idx_productos_precio", "productos", "precio"),
            ("idx_productos_descripcion", "productos", "descripcion"),
        ]

        for nombre, tabla, columna in indices:
            self._crear_indice_si_no_existe(nombre, tabla, columna)

    def crear_indices_facturas(self):
        """
        Crea índices optimizados para la tabla facturas

        Índices creados:
        - cliente_id: JOIN con clientes
        - fecha: Filtrado y ordenamiento por fecha
        - numero_factura: Búsqueda rápida por número
        - cliente_fecha: Índice compuesto para consultas por cliente y período
        """
        logger.info("Optimizando tabla: facturas")

        # Índices simples
        indices_simples = [
            ("idx_facturas_cliente", "facturas", "cliente_id"),
            ("idx_facturas_fecha", "facturas", "fecha"),
            ("idx_facturas_numero", "facturas", "numero_factura"),
        ]

        for nombre, tabla, columna in indices_simples:
            self._crear_indice_si_no_existe(nombre, tabla, columna)

        # Índice compuesto
        self._crear_indice_compuesto_si_no_existe(
            "idx_facturas_cliente_fecha",
            "facturas",
            ["cliente_id", "fecha"]
        )

    def crear_indices_factura_items(self):
        """
        Crea índices optimizados para la tabla factura_items

        Índices creados:
        - factura_id: JOIN con facturas
        - producto_id: JOIN con productos
        """
        logger.info("Optimizando tabla: factura_items")

        indices = [
            ("idx_factura_items_factura", "factura_items", "factura_id"),
            ("idx_factura_items_producto", "factura_items", "producto_id"),
        ]

        for nombre, tabla, columna in indices:
            self._crear_indice_si_no_existe(nombre, tabla, columna)

    def crear_indices_compras(self):
        """
        Crea índices optimizados para la tabla compras

        Índices creados:
        - fecha: Filtrado y ordenamiento por fecha
        - proveedor: Filtrado por proveedor
        """
        logger.info("Optimizando tabla: compras")

        indices = [
            ("idx_compras_fecha", "compras", "fecha"),
            ("idx_compras_proveedor", "compras", "proveedor"),
        ]

        for nombre, tabla, columna in indices:
            self._crear_indice_si_no_existe(nombre, tabla, columna)

    def crear_indices_compras_items(self):
        """
        Crea índices optimizados para la tabla compras_items

        Índices creados:
        - compra_id: JOIN con compras
        - producto_id: JOIN con productos
        """
        logger.info("Optimizando tabla: compras_items")

        indices = [
            ("idx_compras_items_compra", "compras_items", "compra_id"),
            ("idx_compras_items_producto", "compras_items", "producto_id"),
        ]

        for nombre, tabla, columna in indices:
            self._crear_indice_si_no_existe(nombre, tabla, columna)

    def crear_indices_reparaciones(self):
        """
        Crea índices optimizados para la tabla reparaciones

        Índices creados:
        - cliente_id: JOIN con clientes
        - fecha_entrada: Ordenamiento y filtrado
        - estado: Filtrado por estado
        - imei: Búsqueda rápida por IMEI
        """
        logger.info("Optimizando tabla: reparaciones")

        indices = [
            ("idx_reparaciones_cliente", "reparaciones", "cliente_id"),
            ("idx_reparaciones_fecha", "reparaciones", "fecha_entrada"),
            ("idx_reparaciones_estado", "reparaciones", "estado"),
            ("idx_reparaciones_imei", "reparaciones", "imei"),
        ]

        for nombre, tabla, columna in indices:
            self._crear_indice_si_no_existe(nombre, tabla, columna)

        # Índice compuesto para búsquedas por estado y fecha
        self._crear_indice_compuesto_si_no_existe(
            "idx_reparaciones_estado_fecha",
            "reparaciones",
            ["estado", "fecha_entrada"]
        )

    def crear_indices_caja(self):
        """
        Crea índices optimizados para tablas de caja

        Índices creados:
        - caja_movimientos: fecha, tipo
        - caja_cierres: fecha
        """
        logger.info("Optimizando tablas de caja")

        indices = [
            ("idx_caja_mov_fecha", "caja_movimientos", "fecha"),
            ("idx_caja_mov_tipo", "caja_movimientos", "tipo"),
            ("idx_caja_cierres_fecha", "caja_cierres", "fecha"),
        ]

        for nombre, tabla, columna in indices:
            self._crear_indice_si_no_existe(nombre, tabla, columna)

    def crear_indices_usuarios(self):
        """
        Crea índices optimizados para la tabla usuarios

        Índices creados:
        - username: Login y búsquedas
        - rol: Filtrado por rol
        - activo: Filtrado por usuarios activos
        """
        logger.info("Optimizando tabla: usuarios")

        indices = [
            ("idx_usuarios_username", "usuarios", "username"),
            ("idx_usuarios_rol", "usuarios", "rol"),
            ("idx_usuarios_activo", "usuarios", "activo"),
        ]

        for nombre, tabla, columna in indices:
            self._crear_indice_si_no_existe(nombre, tabla, columna)

    def _crear_indice_si_no_existe(self, nombre_indice, tabla, columna):
        """
        Crea un índice simple si no existe

        SEGURIDAD: Valida todos los nombres antes de construir el query.

        Args:
            nombre_indice: Nombre del índice
            tabla: Tabla donde crear el índice
            columna: Columna a indexar
        """
        # SEGURIDAD: Validar tabla contra lista blanca
        if not self._validar_tabla(tabla):
            logger.warning(f"Tabla '{tabla}' no esta en lista blanca, omitiendo")
            return

        # SEGURIDAD: Validar que nombre_indice y columna sean identificadores válidos
        if not self._validar_identificador(nombre_indice):
            logger.warning(f"Nombre de indice '{nombre_indice}' invalido, omitiendo")
            return

        if not self._validar_identificador(columna):
            logger.warning(f"Nombre de columna '{columna}' invalido, omitiendo")
            return

        try:
            # Verificar si existe
            existe = self.db.fetch_one(
                "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
                (nombre_indice,)
            )

            if existe:
                logger.debug(f"{nombre_indice} ya existe")
                return

            # Crear índice (nombres ya validados)
            self.db.execute_query(
                f"CREATE INDEX {nombre_indice} ON {tabla}({columna})"
            )
            logger.info(f"{nombre_indice} creado en {tabla}({columna})")

        except sqlite3.Error as e:
            logger.error(f"Error creando {nombre_indice}: {e}")

    def _crear_indice_compuesto_si_no_existe(self, nombre_indice, tabla, columnas):
        """
        Crea un índice compuesto si no existe

        SEGURIDAD: Valida todos los nombres antes de construir el query.

        Args:
            nombre_indice: Nombre del índice
            tabla: Tabla donde crear el índice
            columnas: Lista de columnas a indexar
        """
        # SEGURIDAD: Validar tabla contra lista blanca
        if not self._validar_tabla(tabla):
            logger.warning(f"Tabla '{tabla}' no esta en lista blanca, omitiendo")
            return

        # SEGURIDAD: Validar nombre del índice
        if not self._validar_identificador(nombre_indice):
            logger.warning(f"Nombre de indice '{nombre_indice}' invalido, omitiendo")
            return

        # SEGURIDAD: Validar cada columna
        for col in columnas:
            if not self._validar_identificador(col):
                logger.warning(f"Nombre de columna '{col}' invalido, omitiendo")
                return

        try:
            # Verificar si existe
            existe = self.db.fetch_one(
                "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
                (nombre_indice,)
            )

            if existe:
                logger.debug(f"{nombre_indice} ya existe")
                return

            # Crear índice compuesto (nombres ya validados)
            columnas_str = ", ".join(columnas)
            self.db.execute_query(
                f"CREATE INDEX {nombre_indice} ON {tabla}({columnas_str})"
            )
            logger.info(f"{nombre_indice} creado en {tabla}({columnas_str})")

        except sqlite3.Error as e:
            logger.error(f"Error creando {nombre_indice}: {e}")

    def optimizar_todas_las_tablas(self):
        """
        Ejecuta la optimización completa de la base de datos

        Crea todos los índices necesarios en todas las tablas
        """
        logger.info("=" * 70)
        logger.info("OPTIMIZACION DE BASE DE DATOS - REDMOVILPOS")
        logger.info("=" * 70)

        # Mostrar índices existentes
        logger.info("Analizando indices existentes...")
        stats = self.analizar_indices()
        logger.info(f"Total de indices existentes: {stats['total_indices']}")

        # Crear índices por tabla
        self.crear_indices_clientes()
        self.crear_indices_productos()
        self.crear_indices_facturas()
        self.crear_indices_factura_items()
        self.crear_indices_compras()
        self.crear_indices_compras_items()
        self.crear_indices_reparaciones()
        self.crear_indices_caja()
        self.crear_indices_usuarios()

        # Analizar VACUUM y ANALYZE
        logger.info("Ejecutando ANALYZE para actualizar estadisticas...")
        try:
            self.db.execute_query("ANALYZE")
            logger.info("ANALYZE completado")
        except sqlite3.Error as e:
            logger.error(f"Error en ANALYZE: {e}")

        # Mostrar estadísticas finales
        stats_finales = self.analizar_indices()
        logger.info(f"Total de indices despues de optimizacion: {stats_finales['total_indices']}")
        logger.info("=" * 70)
        logger.info("OPTIMIZACION COMPLETADA")
        logger.info("=" * 70)
        logger.info("BENEFICIOS DE LA OPTIMIZACION:")
        logger.info("  - Busquedas mas rapidas por cliente, producto, fecha")
        logger.info("  - JOINs optimizados entre tablas relacionadas")
        logger.info("  - Ordenamiento eficiente de resultados")
        logger.info("  - Consultas de rango (fechas, precios) aceleradas")
        logger.info("  - Mejor rendimiento en listados grandes")

    def eliminar_indice(self, nombre_indice):
        """
        Elimina un índice de la base de datos

        SEGURIDAD: Valida el nombre del índice contra el patrón de identificador.

        Args:
            nombre_indice: Nombre del índice a eliminar
        """
        # SEGURIDAD: Validar nombre contra patrón de identificador
        if not self._validar_identificador(nombre_indice):
            logger.error(f"Nombre de índice no válido: {nombre_indice}")
            return
        try:
            self.db.execute_query(f"DROP INDEX IF EXISTS {nombre_indice}")
            logger.info(f"Indice {nombre_indice} eliminado")
        except sqlite3.Error as e:
            logger.error(f"Error eliminando indice: {e}")

    def obtener_estadisticas_tabla(self, tabla):
        """
        Obtiene estadísticas de una tabla

        SEGURIDAD: Usa la lista blanca centralizada de la clase.

        Args:
            tabla: Nombre de la tabla

        Returns:
            dict: Estadísticas de la tabla
        """
        # SEGURIDAD: Validar tabla contra lista blanca de la clase
        if not self._validar_tabla(tabla):
            return {
                'tabla': tabla,
                'error': f'Tabla no permitida: {tabla}'
            }

        try:
            # Número de registros (tabla ya validada contra lista blanca)
            count = self.db.fetch_one(f"SELECT COUNT(*) as total FROM {tabla}")
            total_registros = count['total'] if count else 0

            # Índices de la tabla (usando parámetro preparado)
            indices = self.db.fetch_all(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=?",
                (tabla,)
            )

            return {
                'tabla': tabla,
                'registros': total_registros,
                'indices': [idx['name'] for idx in indices]
            }

        except sqlite3.Error as e:
            logger.error(f"Error obteniendo estadisticas de {tabla}: {e}")
            return {'tabla': tabla, 'error': str(e)}
