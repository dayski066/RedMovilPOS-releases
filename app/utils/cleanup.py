"""
Utilidades de limpieza de archivos temporales.
Limpia archivos temporales huérfanos de la aplicación RedMovilPOS.
"""
import os
import glob
import tempfile
from datetime import datetime, timedelta
from app.utils.logger import get_logger

logger = get_logger('cleanup')

# Patrones de archivos temporales de la aplicación
TEMP_PATTERNS = [
    'redmovilpos_*.pdf',
    'factura_*.pdf',
    'contrato_*.pdf',
    'orden_*.pdf',
    'ticket_*.pdf',
    'redmovilpos_scans/*',
    '*.bmp',  # Bitmaps de ticket_printer
]

# Tiempo máximo de vida de archivos temporales (horas)
MAX_TEMP_AGE_HOURS = 24


def limpiar_temporales(max_age_hours: int = MAX_TEMP_AGE_HOURS, dry_run: bool = False) -> dict:
    """
    Limpia archivos temporales antiguos de la aplicación.
    
    Args:
        max_age_hours: Edad máxima en horas de los archivos a mantener
        dry_run: Si True, solo reporta sin borrar
        
    Returns:
        dict con estadísticas: {'deleted': int, 'size_freed': int, 'errors': int}
    """
    temp_dir = tempfile.gettempdir()
    stats = {'deleted': 0, 'size_freed': 0, 'errors': 0, 'files': []}
    
    now = datetime.now()
    max_age = timedelta(hours=max_age_hours)
    
    for pattern in TEMP_PATTERNS:
        full_pattern = os.path.join(temp_dir, pattern)
        
        for filepath in glob.glob(full_pattern):
            try:
                if not os.path.isfile(filepath):
                    continue
                    
                # Verificar antigüedad
                mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                age = now - mtime
                
                if age > max_age:
                    file_size = os.path.getsize(filepath)
                    
                    if not dry_run:
                        os.remove(filepath)
                        logger.info(f"Eliminado temporal: {filepath} (edad: {age.total_seconds()/3600:.1f}h)")
                    
                    stats['deleted'] += 1
                    stats['size_freed'] += file_size
                    stats['files'].append(filepath)
                    
            except (OSError, PermissionError) as e:
                stats['errors'] += 1
                logger.warning(f"No se pudo eliminar {filepath}: {e}")
    
    # Limpiar directorio de scans si existe y está vacío
    scans_dir = os.path.join(temp_dir, 'redmovilpos_scans')
    if os.path.isdir(scans_dir):
        try:
            if not os.listdir(scans_dir):
                os.rmdir(scans_dir)
                logger.info(f"Eliminado directorio vacío: {scans_dir}")
        except OSError:
            pass
    
    if stats['deleted'] > 0:
        size_mb = stats['size_freed'] / (1024 * 1024)
        logger.info(f"Limpieza completada: {stats['deleted']} archivos, {size_mb:.2f} MB liberados")
    
    return stats


def limpiar_temporales_silencioso():
    """
    Versión silenciosa para ejecutar al inicio de la aplicación.
    No lanza excepciones.
    """
    try:
        stats = limpiar_temporales(max_age_hours=MAX_TEMP_AGE_HOURS)
        if stats['deleted'] > 0:
            logger.info(f"{stats['deleted']} archivos temporales eliminados")
    except Exception as e:
        # No fallar el inicio por errores de limpieza
        logger.error(f"Error en limpieza: {e}")
