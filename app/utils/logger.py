"""
Sistema de logging centralizado para REDMOVILPOS
Proporciona logging estructurado con rotación automática de archivos
Compatible con Windows (evita problemas de bloqueo de archivos)
"""
# sqlite3 no se usa en este módulo — se eliminó del except catch-all
import logging
import os
import glob
import json
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta, timezone
from app_paths import APP_DATA_DIR


class JsonFormatter(logging.Formatter):
    """
    Formatter que produce logs en formato JSON estructurado.
    
    Cada línea de log es un objeto JSON con campos estandarizados,
    permitiendo análisis con herramientas como jq, Elasticsearch, Splunk, etc.
    """
    
    def format(self, record):
        """Formatea el record como JSON"""
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        
        # Añadir información de excepción si existe
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        # Añadir campos extra si existen
        if hasattr(record, 'extra_data'):
            log_obj["data"] = record.extra_data
            
        return json.dumps(log_obj, ensure_ascii=False)

class WindowsSafeDailyHandler(logging.FileHandler):
    """
    Handler de logging diario compatible con Windows.

    En lugar de rotar archivos (que causa problemas de bloqueo en Windows),
    este handler escribe directamente a un archivo con la fecha en el nombre.
    Cada día se crea un nuevo archivo automáticamente.
    """

    def __init__(self, log_dir, base_name='redmovilpos', backup_count=30, encoding='utf-8'):
        self.log_dir = log_dir
        self.base_name = base_name
        self.backup_count = backup_count
        self.current_date = None

        # Crear directorio si no existe
        os.makedirs(log_dir, exist_ok=True)

        # Obtener el archivo actual
        self.baseFilename = self._get_current_filename()
        self.current_date = datetime.now().date()

        # Inicializar el handler padre
        super().__init__(self.baseFilename, mode='a', encoding=encoding)

        # Limpiar archivos antiguos al iniciar
        self._cleanup_old_logs()

    def _get_current_filename(self):
        """Obtiene el nombre del archivo de log para la fecha actual"""
        fecha = datetime.now().strftime('%Y-%m-%d')
        return os.path.join(self.log_dir, f'{self.base_name}_{fecha}.log')

    def _should_rollover(self):
        """Verifica si necesitamos cambiar a un nuevo archivo (nuevo día)"""
        return datetime.now().date() != self.current_date

    def _do_rollover(self):
        """Cambia al archivo del nuevo día"""
        # Cerrar el archivo actual
        if self.stream:
            self.stream.close()
            self.stream = None

        # Actualizar al nuevo archivo
        self.current_date = datetime.now().date()
        self.baseFilename = self._get_current_filename()

        # Abrir el nuevo archivo
        self.stream = self._open()

        # Limpiar archivos antiguos
        self._cleanup_old_logs()

    def _cleanup_old_logs(self):
        """Elimina archivos de log más antiguos que backup_count días"""
        try:
            pattern = os.path.join(self.log_dir, f'{self.base_name}_*.log')
            log_files = glob.glob(pattern)

            # Ordenar por fecha de modificación (más antiguos primero)
            log_files.sort(key=lambda x: os.path.getmtime(x))

            # Eliminar archivos extra
            while len(log_files) > self.backup_count:
                old_file = log_files.pop(0)
                try:
                    os.remove(old_file)
                except (OSError, PermissionError):
                    pass  # Ignorar si no se puede eliminar
        except OSError:
            pass  # No fallar por errores de limpieza

    def emit(self, record):
        """Emite un registro de log, verificando si hay que cambiar de archivo"""
        try:
            if self._should_rollover():
                self._do_rollover()
            super().emit(record)
        except OSError:
            self.handleError(record)


class RedmovilLogger:
    """
    Gestor de logging centralizado para la aplicación

    Características:
    - Múltiples niveles de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - Archivos rotativos por tamaño y fecha
    - Formato estructurado con timestamp, nivel, módulo
    - Separación de logs por módulo
    - Console output para desarrollo
    """

    # Niveles de logging
    DEBUG = logging.DEBUG        # 10 - Información detallada para diagnóstico
    INFO = logging.INFO          # 20 - Confirmación de que las cosas funcionan
    WARNING = logging.WARNING    # 30 - Algo inesperado pero manejable
    ERROR = logging.ERROR        # 40 - Error serio que impidió una operación
    CRITICAL = logging.CRITICAL  # 50 - Error muy grave, la app puede no continuar

    def __init__(self, nombre_modulo, nivel=logging.INFO):
        """
        Inicializa el logger para un módulo específico

        Args:
            nombre_modulo: Nombre del módulo (ej: 'auth', 'factura', 'database')
            nivel: Nivel mínimo de logging (default: INFO)
        """
        self.nombre_modulo = nombre_modulo
        self.logger = logging.getLogger(nombre_modulo)
        self.logger.setLevel(nivel)

        # Evitar duplicación de handlers si ya existe
        if not self.logger.handlers:
            self._configurar_handlers()

    def _configurar_handlers(self):
        """Configura los handlers de logging (archivo y consola)"""

        # Crear directorio de logs en ProgramData (tiene permisos de escritura)
        log_dir = os.path.join(APP_DATA_DIR, 'logs')
        os.makedirs(log_dir, exist_ok=True)

        # Formato detallado para logs
        formato = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)-15s | %(funcName)-20s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 1. Handler de archivo principal - Rotación por tamaño
        # Se crea un nuevo archivo cuando alcanza 10MB, mantiene últimos 5 archivos
        archivo_principal = os.path.join(log_dir, 'redmovilpos.log')
        handler_archivo = RotatingFileHandler(
            archivo_principal,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        handler_archivo.setLevel(logging.DEBUG)
        handler_archivo.setFormatter(formato)
        self.logger.addHandler(handler_archivo)

        # 2. Handler de errores - Solo ERROR y CRITICAL
        archivo_errores = os.path.join(log_dir, 'errors.log')
        handler_errores = RotatingFileHandler(
            archivo_errores,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding='utf-8'
        )
        handler_errores.setLevel(logging.ERROR)
        handler_errores.setFormatter(formato)
        self.logger.addHandler(handler_errores)

        # 3. Handler de consola - Para desarrollo (solo WARNING y superior)
        handler_consola = logging.StreamHandler()
        handler_consola.setLevel(logging.WARNING)
        # Formato más simple para consola
        formato_consola = logging.Formatter(
            '%(levelname)s [%(name)s] %(message)s'
        )
        handler_consola.setFormatter(formato_consola)
        self.logger.addHandler(handler_consola)

        # 4. Handler diario - Archivo por fecha (compatible con Windows)
        # Usa WindowsSafeDailyHandler para evitar problemas de bloqueo de archivos
        handler_diario = WindowsSafeDailyHandler(
            log_dir,
            base_name='redmovilpos_daily',
            backup_count=30,  # Mantener últimos 30 días
            encoding='utf-8'
        )
        handler_diario.setLevel(logging.INFO)
        handler_diario.setFormatter(formato)
        self.logger.addHandler(handler_diario)
        
        # 5. Handler JSON - Logs estructurados para análisis
        # Cada línea es un objeto JSON completo para facilitar parsing
        archivo_json = os.path.join(log_dir, 'redmovilpos.json')
        handler_json = RotatingFileHandler(
            archivo_json,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=3,
            encoding='utf-8'
        )
        handler_json.setLevel(logging.INFO)
        handler_json.setFormatter(JsonFormatter())
        self.logger.addHandler(handler_json)

    # Métodos de conveniencia para logging

    def debug(self, mensaje, *args, **kwargs):
        """Registra mensaje de nivel DEBUG"""
        self.logger.debug(mensaje, *args, **kwargs)

    def info(self, mensaje, *args, **kwargs):
        """Registra mensaje de nivel INFO"""
        self.logger.info(mensaje, *args, **kwargs)

    def warning(self, mensaje, *args, **kwargs):
        """Registra mensaje de nivel WARNING"""
        self.logger.warning(mensaje, *args, **kwargs)

    def error(self, mensaje, *args, exc_info=False, **kwargs):
        """
        Registra mensaje de nivel ERROR

        Args:
            mensaje: Mensaje a registrar
            exc_info: Si True, incluye el stacktrace de la excepción actual
        """
        self.logger.error(mensaje, *args, exc_info=exc_info, **kwargs)

    def critical(self, mensaje, *args, exc_info=False, **kwargs):
        """
        Registra mensaje de nivel CRITICAL

        Args:
            mensaje: Mensaje a registrar
            exc_info: Si True, incluye el stacktrace de la excepción actual
        """
        self.logger.critical(mensaje, *args, exc_info=exc_info, **kwargs)

    def exception(self, mensaje, *args, **kwargs):
        """
        Registra una excepción con stacktrace completo
        Útil en bloques except
        """
        self.logger.exception(mensaje, *args, **kwargs)

    # Métodos de contexto

    def log_operacion(self, operacion, usuario=None, detalles=None):
        """
        Registra una operación de negocio

        Args:
            operacion: Nombre de la operación (ej: "Crear Factura")
            usuario: Usuario que realizó la operación
            detalles: Detalles adicionales
        """
        mensaje = f"Operacion: {operacion}"
        if usuario:
            mensaje += f" | Usuario: {usuario}"
        if detalles:
            mensaje += f" | Detalles: {detalles}"
        self.info(mensaje)

    def log_acceso_bd(self, tabla, operacion, registros_afectados=None):
        """
        Registra operaciones de base de datos

        Args:
            tabla: Nombre de la tabla
            operacion: Tipo de operación (SELECT, INSERT, UPDATE, DELETE)
            registros_afectados: Número de registros afectados
        """
        mensaje = f"BD: {operacion} en {tabla}"
        if registros_afectados is not None:
            mensaje += f" | Registros: {registros_afectados}"
        self.debug(mensaje)

    def log_autenticacion(self, usuario, exito, ip_address=None):
        """
        Registra intentos de autenticación

        Args:
            usuario: Nombre de usuario
            exito: Si el login fue exitoso
            ip_address: IP desde donde se intentó el acceso
        """
        estado = "exitoso" if exito else "fallido"
        mensaje = f"Login {estado}: {usuario}"
        if ip_address:
            mensaje += f" | IP: {ip_address}"

        if exito:
            self.info(mensaje)
        else:
            self.warning(mensaje)


# Instancia global por defecto para compatibilidad
# Muchos módulos usan: from app.utils.logger import logger
logger = RedmovilLogger('app')

# Instancias globales para diferentes módulos
# Se pueden usar directamente en toda la aplicación

def get_logger(nombre_modulo, nivel=logging.INFO):
    """
    Obtiene un logger para un módulo específico

    Args:
        nombre_modulo: Nombre del módulo
        nivel: Nivel mínimo de logging

    Returns:
        RedmovilLogger: Instancia del logger

    Ejemplo:
        logger = get_logger('auth')
        logger.info("Usuario autenticado correctamente")
    """
    return RedmovilLogger(nombre_modulo, nivel)


# Configuración inicial del logging
def setup_logging(nivel_consola=logging.WARNING):
    """
    Configura el sistema de logging global

    Args:
        nivel_consola: Nivel mínimo para output en consola (default: WARNING)

    Esta función debe llamarse al inicio de la aplicación
    """
    # Configurar logging root
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    print("[LOGGING] Sistema de logging inicializado")
    print(f"[LOGGING] Archivos de log en: data/logs/")
    print(f"[LOGGING] - redmovilpos.log (general, 10MB x5)")
    print(f"[LOGGING] - errors.log (solo errores, 5MB x3)")
    print(f"[LOGGING] - redmovilpos_daily_YYYY-MM-DD.log (por dia, 30 dias)")


# Ejemplos de uso en diferentes módulos:
"""
# En auth_manager.py:
from app.utils.logger import get_logger
logger = get_logger('auth')

def login(self, username, password):
    logger.info(f"Intento de login: {username}")
    try:
        # ... lógica de login ...
        logger.log_autenticacion(username, True, ip_address)
        return True
    except sqlite3.Error as e:
        logger.error(f"Error en login: {e}", exc_info=True)
        return False

# En database.py:
from app.utils.logger import get_logger
logger = get_logger('database')

def execute_query(self, query, params=None):
    logger.debug(f"Ejecutando query: {query}")
    try:
        cursor.execute(query, params)
        rows = cursor.rowcount
        logger.log_acceso_bd('tabla', 'INSERT', rows)
    except sqlite3.Error as e:
        logger.error(f"Error en query: {e}", exc_info=True)
        raise

# En factura_manager.py:
from app.utils.logger import get_logger
logger = get_logger('factura')

def crear_factura(self, datos):
    usuario = self.auth.obtener_usuario_actual()
    logger.log_operacion('Crear Factura', usuario['username'],
                         f"Cliente: {datos['cliente']}, Total: {datos['total']}")
"""
