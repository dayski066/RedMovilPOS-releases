"""
Gestor de backups automáticos para REDMOVILPOS
Realiza copias de seguridad de la base de datos de forma automática
"""
import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from app.utils.logger import get_logger

logger = get_logger('backup')


class BackupManager:
    """
    Gestor de copias de seguridad de la base de datos.

    Características:
    - Backup automático al iniciar la aplicación
    - Backup manual bajo demanda
    - Rotación automática (mantiene últimos N backups)
    - Verificación de integridad del backup
    - Restauración desde backup
    """

    # Configuración
    MAX_BACKUPS = 10              # Máximo número de backups a mantener
    MIN_HORAS_ENTRE_BACKUPS = 4   # Mínimo horas entre backups automáticos

    def __init__(self, db_path: str, backup_dir: str = None):
        """
        Inicializa el gestor de backups.

        Args:
            db_path: Ruta completa a la base de datos
            backup_dir: Directorio donde guardar backups (default: mismo dir que BD)
        """
        self.db_path = db_path
        self.backup_dir = backup_dir or os.path.join(os.path.dirname(db_path), 'backups')

        # Crear directorio de backups si no existe
        os.makedirs(self.backup_dir, exist_ok=True)

    def crear_backup(self, motivo: str = 'manual') -> tuple:
        """
        Crea una copia de seguridad de la base de datos.

        Args:
            motivo: Razón del backup ('auto', 'manual', 'pre_update', etc.)

        Returns:
            tuple: (exito: bool, ruta_backup: str o mensaje_error: str)
        """
        if not os.path.exists(self.db_path):
            logger.error(f"Base de datos no encontrada: {self.db_path}")
            return False, "Base de datos no encontrada"

        try:
            # Generar nombre del backup con timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"facturacion_{motivo}_{timestamp}.db"
            backup_path = os.path.join(self.backup_dir, backup_name)

            # Usar SQLite backup API para copia segura (sin corromper si hay escrituras)
            logger.info(f"Iniciando backup: {backup_name}")

            # Conectar a la BD original
            source = sqlite3.connect(self.db_path)

            # Crear conexión al backup
            dest = sqlite3.connect(backup_path)

            # Realizar backup usando la API de SQLite (seguro para BD en uso)
            source.backup(dest)

            # Cerrar conexiones
            source.close()
            dest.close()

            # Verificar integridad del backup
            if not self._verificar_integridad(backup_path):
                os.remove(backup_path)
                logger.error("Backup creado pero falló verificación de integridad")
                return False, "Error de integridad en backup"

            # Obtener tamaño del backup
            size_mb = os.path.getsize(backup_path) / (1024 * 1024)

            logger.info(f"Backup completado: {backup_name} ({size_mb:.2f} MB)")

            # Limpiar backups antiguos
            self._limpiar_backups_antiguos()

            return True, backup_path

        except (sqlite3.Error, OSError) as e:
            logger.error(f"Error creando backup: {e}", exc_info=True)
            return False, f"Error: {str(e)}"

    def backup_automatico(self) -> tuple:
        """
        Realiza backup automático si ha pasado suficiente tiempo desde el último.

        Returns:
            tuple: (realizado: bool, mensaje: str)
        """
        ultimo_backup = self._obtener_ultimo_backup()

        if ultimo_backup:
            # Verificar tiempo desde último backup
            try:
                # Extraer timestamp del nombre del archivo
                nombre = os.path.basename(ultimo_backup)
                # formato: facturacion_motivo_YYYYMMDD_HHMMSS.db
                partes = nombre.replace('.db', '').split('_')
                fecha_str = f"{partes[-2]}_{partes[-1]}"
                fecha_ultimo = datetime.strptime(fecha_str, '%Y%m%d_%H%M%S')

                horas_transcurridas = (datetime.now() - fecha_ultimo).total_seconds() / 3600

                if horas_transcurridas < self.MIN_HORAS_ENTRE_BACKUPS:
                    logger.debug(f"Backup automático omitido: último hace {horas_transcurridas:.1f} horas")
                    return False, f"Último backup hace {horas_transcurridas:.1f} horas"

            except (ValueError, IndexError) as e:
                logger.warning(f"No se pudo verificar fecha de último backup: {e}")

        # Realizar backup automático
        return self.crear_backup(motivo='auto')

    def _verificar_integridad(self, db_path: str) -> bool:
        """Verifica la integridad de una base de datos SQLite"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            conn.close()

            if result[0] == 'ok':
                return True
            else:
                logger.warning(f"Integridad fallida: {result}")
                return False

        except sqlite3.Error as e:
            logger.error(f"Error verificando integridad: {e}")
            return False

    def _obtener_ultimo_backup(self) -> str:
        """Obtiene la ruta del backup más reciente"""
        try:
            backups = self.listar_backups()
            if backups:
                return backups[0]['ruta']  # Ya están ordenados por fecha desc
            return None
        except OSError:
            return None

    def _limpiar_backups_antiguos(self):
        """Elimina backups antiguos manteniendo solo los últimos MAX_BACKUPS"""
        try:
            backups = self.listar_backups()

            if len(backups) > self.MAX_BACKUPS:
                # Eliminar los más antiguos
                for backup in backups[self.MAX_BACKUPS:]:
                    try:
                        os.remove(backup['ruta'])
                        logger.info(f"Backup antiguo eliminado: {backup['nombre']}")
                    except OSError as e:
                        logger.warning(f"No se pudo eliminar backup: {e}")

        except OSError as e:
            logger.error(f"Error limpiando backups antiguos: {e}")

    def listar_backups(self) -> list:
        """
        Lista todos los backups disponibles ordenados por fecha (más reciente primero).

        Returns:
            list: Lista de diccionarios con info de cada backup
        """
        backups = []

        try:
            for archivo in os.listdir(self.backup_dir):
                if archivo.startswith('facturacion_') and archivo.endswith('.db'):
                    ruta = os.path.join(self.backup_dir, archivo)
                    stat = os.stat(ruta)

                    backups.append({
                        'nombre': archivo,
                        'ruta': ruta,
                        'tamaño_mb': stat.st_size / (1024 * 1024),
                        'fecha_modificacion': datetime.fromtimestamp(stat.st_mtime),
                        'fecha_str': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                    })

            # Ordenar por fecha de modificación (más reciente primero)
            backups.sort(key=lambda x: x['fecha_modificacion'], reverse=True)

        except OSError as e:
            logger.error(f"Error listando backups: {e}")

        return backups

    def restaurar_backup(self, backup_path: str) -> tuple:
        """
        Restaura la base de datos desde un backup.

        ADVERTENCIA: Esto reemplazará la base de datos actual.

        Args:
            backup_path: Ruta al archivo de backup

        Returns:
            tuple: (exito: bool, mensaje: str)
        """
        if not os.path.exists(backup_path):
            return False, "Archivo de backup no encontrado"

        # Verificar integridad del backup antes de restaurar
        if not self._verificar_integridad(backup_path):
            return False, "El backup está corrupto o dañado"

        try:
            # Crear backup de seguridad antes de restaurar
            self.crear_backup(motivo='pre_restore')

            # Copiar backup sobre la BD actual
            shutil.copy2(backup_path, self.db_path)

            logger.info(f"Base de datos restaurada desde: {backup_path}")
            return True, "Base de datos restaurada correctamente"

        except (sqlite3.Error, OSError) as e:
            logger.error(f"Error restaurando backup: {e}", exc_info=True)
            return False, f"Error al restaurar: {str(e)}"

    def obtener_info_backup(self, backup_path: str) -> dict:
        """
        Obtiene información detallada de un backup.

        Args:
            backup_path: Ruta al archivo de backup

        Returns:
            dict: Información del backup
        """
        if not os.path.exists(backup_path):
            return {'error': 'Archivo no encontrado'}

        try:
            stat = os.stat(backup_path)
            info = {
                'nombre': os.path.basename(backup_path),
                'ruta': backup_path,
                'tamaño_mb': stat.st_size / (1024 * 1024),
                'fecha_creacion': datetime.fromtimestamp(stat.st_ctime),
                'integridad_ok': self._verificar_integridad(backup_path)
            }

            # Contar registros en tablas principales
            if info['integridad_ok']:
                conn = sqlite3.connect(backup_path)
                cursor = conn.cursor()

                tablas = ['clientes', 'productos', 'facturas', 'ventas_caja', 'compras']
                info['registros'] = {}

                for tabla in tablas:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
                        info['registros'][tabla] = cursor.fetchone()[0]
                    except sqlite3.Error:
                        info['registros'][tabla] = 0

                conn.close()

            return info

        except (sqlite3.Error, OSError) as e:
            logger.error(f"Error obteniendo info de backup: {e}")
            return {'error': str(e)}


def realizar_backup_inicial(db_path: str) -> bool:
    """
    Función auxiliar para realizar backup al iniciar la aplicación.

    Args:
        db_path: Ruta a la base de datos

    Returns:
        bool: True si se realizó backup, False si no fue necesario o falló
    """
    try:
        backup_dir = os.path.join(os.path.dirname(db_path), 'backups')
        manager = BackupManager(db_path, backup_dir)

        exito, mensaje = manager.backup_automatico()

        if exito:
            logger.info(f"Backup automático realizado: {mensaje}")
        else:
            logger.debug(f"Backup automático omitido: {mensaje}")

        return exito

    except Exception as e:
        logger.error(f"Error en backup inicial: {e}")
        return False
