"""
Sistema de actualizaciones OTA para RedMovilPOS
Comprueba actualizaciones en GitHub Releases y las descarga de forma segura
"""
import sqlite3
import os
import sys
import json
import hashlib
import tempfile
import subprocess
from datetime import datetime
from typing import Optional, Callable
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from config import APP_VERSION
from app_paths import APP_DATA_DIR, DB_PATH
from app.modules.backup_manager import BackupManager
from app.utils.logger import get_logger

logger = get_logger('updater')


class UpdateInfo:
    """Información sobre una actualización disponible"""
    def __init__(self, version: str, download_url: str, changelog: str,
                 file_size: int = 0, sha256: str = None, published_at: str = None):
        self.version = version
        self.download_url = download_url
        self.changelog = changelog
        self.file_size = file_size
        self.sha256 = sha256
        self.published_at = published_at

    def __repr__(self):
        return f"UpdateInfo(version={self.version}, size={self.file_size})"


class Updater:
    """
    Gestor de actualizaciones OTA para RedMovilPOS.

    Funcionalidades:
    - Comprueba nuevas versiones en GitHub Releases
    - Descarga actualizaciones con verificación de integridad
    - Realiza backup automático de BD antes de actualizar
    - Ejecuta instalador y reinicia la aplicación
    """

    GITHUB_USER = "dayski066"
    GITHUB_REPO = "RedMovilPOS-releases"
    GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"

    # Directorio para descargas temporales
    DOWNLOAD_DIR = os.path.join(APP_DATA_DIR, 'updates')

    def __init__(self):
        """Inicializa el updater"""
        self.current_version = APP_VERSION
        self.update_info: Optional[UpdateInfo] = None

        # Crear directorio de descargas si no existe
        os.makedirs(self.DOWNLOAD_DIR, exist_ok=True)

        # Backup manager para proteger la BD
        backup_dir = os.path.join(os.path.dirname(DB_PATH), 'backups')
        self.backup_manager = BackupManager(DB_PATH, backup_dir)

    def _comparar_versiones(self, version1: str, version2: str) -> int:
        """
        Compara dos versiones semánticas.

        Returns:
            -1 si version1 < version2
             0 si version1 == version2
             1 si version1 > version2
        """
        def parse_version(v: str) -> tuple:
            # Eliminar 'v' inicial si existe
            v = v.lstrip('v')
            # Separar por puntos y convertir a enteros
            parts = []
            for part in v.split('.'):
                # Manejar sufijos como -beta, -rc1, etc.
                num = ''
                for char in part:
                    if char.isdigit():
                        num += char
                    else:
                        break
                parts.append(int(num) if num else 0)
            # Asegurar al menos 3 componentes (major.minor.patch)
            while len(parts) < 3:
                parts.append(0)
            return tuple(parts)

        v1 = parse_version(version1)
        v2 = parse_version(version2)

        if v1 < v2:
            return -1
        elif v1 > v2:
            return 1
        return 0

    def comprobar_actualizacion(self) -> Optional[UpdateInfo]:
        """
        Comprueba si hay una nueva versión disponible en GitHub.

        Returns:
            UpdateInfo si hay actualización disponible, None si no
        """
        logger.info(f"Comprobando actualizaciones... (versión actual: {self.current_version})")

        try:
            # Crear request con User-Agent (requerido por GitHub API)
            request = Request(
                self.GITHUB_API_URL,
                headers={
                    'User-Agent': f'RedMovilPOS/{self.current_version}',
                    'Accept': 'application/vnd.github.v3+json'
                }
            )

            with urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))

            # Extraer información de la release
            latest_version = data.get('tag_name', '').lstrip('v')
            changelog = data.get('body', 'Sin descripción')
            published_at = data.get('published_at', '')

            # Buscar el asset descargable (instalador .exe)
            download_url = None
            file_size = 0
            sha256 = None

            for asset in data.get('assets', []):
                asset_name = asset.get('name', '').lower()
                # Buscar el instalador .exe o .zip
                if asset_name.endswith('.exe') or asset_name.endswith('.zip'):
                    download_url = asset.get('browser_download_url')
                    file_size = asset.get('size', 0)
                    break

            # Buscar archivo SHA256 si existe
            for asset in data.get('assets', []):
                if 'sha256' in asset.get('name', '').lower():
                    try:
                        sha_request = Request(
                            asset.get('browser_download_url'),
                            headers={'User-Agent': f'RedMovilPOS/{self.current_version}'}
                        )
                        with urlopen(sha_request, timeout=10) as sha_response:
                            sha256 = sha_response.read().decode('utf-8').strip().split()[0]
                    except (sqlite3.Error, OSError, ValueError):
                        pass
                    break

            if not latest_version:
                logger.warning("No se pudo obtener la versión de la release")
                return None

            if not download_url:
                logger.warning("No se encontró archivo descargable en la release")
                return None

            # Comparar versiones
            if self._comparar_versiones(latest_version, self.current_version) > 0:
                self.update_info = UpdateInfo(
                    version=latest_version,
                    download_url=download_url,
                    changelog=changelog,
                    file_size=file_size,
                    sha256=sha256,
                    published_at=published_at
                )
                logger.info(f"Nueva versión disponible: {latest_version}")
                return self.update_info
            else:
                logger.info(f"Ya tienes la última versión ({self.current_version})")
                return None

        except HTTPError as e:
            if e.code == 404:
                logger.info("No hay releases publicadas aún")
            else:
                logger.error(f"Error HTTP comprobando actualizaciones: {e.code}")
            return None
        except URLError as e:
            logger.error(f"Error de conexión: {e.reason}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando respuesta de GitHub: {e}")
            return None
        except (sqlite3.Error, OSError, ValueError) as e:
            logger.error(f"Error comprobando actualizaciones: {e}", exc_info=True)
            return None

    def descargar_actualizacion(self, progress_callback: Callable[[int, int], None] = None) -> Optional[str]:
        """
        Descarga la actualización disponible.

        Args:
            progress_callback: Función callback(bytes_descargados, bytes_totales)

        Returns:
            Ruta al archivo descargado o None si falla
        """
        if not self.update_info:
            logger.error("No hay información de actualización. Llama a comprobar_actualizacion() primero")
            return None

        try:
            logger.info(f"Descargando actualización v{self.update_info.version}...")

            # Nombre del archivo
            filename = os.path.basename(self.update_info.download_url)
            download_path = os.path.join(self.DOWNLOAD_DIR, filename)

            # Eliminar archivo anterior si existe
            if os.path.exists(download_path):
                os.remove(download_path)

            # Crear request
            request = Request(
                self.update_info.download_url,
                headers={'User-Agent': f'RedMovilPOS/{self.current_version}'}
            )

            # Descargar con progreso
            with urlopen(request, timeout=300) as response:
                total_size = int(response.headers.get('content-length', 0)) or self.update_info.file_size
                downloaded = 0
                chunk_size = 8192

                with open(download_path, 'wb') as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress_callback and total_size > 0:
                            progress_callback(downloaded, total_size)

            logger.info(f"Descarga completada: {download_path}")

            # Verificar integridad si tenemos SHA256
            if self.update_info.sha256:
                if not self._verificar_sha256(download_path, self.update_info.sha256):
                    logger.error("Verificación SHA256 fallida - archivo corrupto")
                    os.remove(download_path)
                    return None
                logger.info("Verificación SHA256 correcta")

            return download_path

        except (sqlite3.Error, OSError, ValueError) as e:
            logger.error(f"Error descargando actualización: {e}", exc_info=True)
            return None

    def _verificar_sha256(self, file_path: str, expected_hash: str) -> bool:
        """Verifica el hash SHA256 de un archivo"""
        sha256_hash = hashlib.sha256()

        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256_hash.update(chunk)

        actual_hash = sha256_hash.hexdigest().lower()
        expected_hash = expected_hash.lower()

        return actual_hash == expected_hash

    def crear_backup_preactualizacion(self) -> tuple:
        """
        Crea un backup de la base de datos antes de actualizar.

        Returns:
            tuple: (exito: bool, ruta_backup: str o mensaje_error: str)
        """
        logger.info("Creando backup de seguridad antes de actualizar...")
        return self.backup_manager.crear_backup(motivo='pre_update')

    def instalar_actualizacion(self, installer_path: str, silent: bool = False) -> bool:
        """
        Ejecuta el instalador de la actualización.

        Args:
            installer_path: Ruta al instalador descargado
            silent: Si True, instala en modo silencioso

        Returns:
            bool: True si se inició la instalación correctamente
        """
        if not os.path.exists(installer_path):
            logger.error(f"Instalador no encontrado: {installer_path}")
            return False

        try:
            logger.info(f"Iniciando instalador: {installer_path}")

            # Construir comando
            if installer_path.endswith('.exe'):
                # Instalador Inno Setup
                args = [installer_path]
                if silent:
                    args.extend(['/SILENT', '/CLOSEAPPLICATIONS'])

                # Ejecutar instalador
                subprocess.Popen(args, shell=False)

                logger.info("Instalador iniciado. La aplicación se cerrará.")
                return True
            else:
                logger.error("Formato de instalador no soportado")
                return False

        except (sqlite3.Error, OSError, ValueError) as e:
            logger.error(f"Error ejecutando instalador: {e}", exc_info=True)
            return False

    def actualizar(self, progress_callback: Callable[[str, int, int], None] = None) -> tuple:
        """
        Proceso completo de actualización.

        Args:
            progress_callback: Función callback(estado: str, progreso: int, total: int)

        Returns:
            tuple: (exito: bool, mensaje: str)
        """
        def notify(estado: str, progreso: int = 0, total: int = 100):
            if progress_callback:
                progress_callback(estado, progreso, total)

        try:
            # 1. Comprobar actualización
            notify("Comprobando actualizaciones...", 0, 100)
            update = self.comprobar_actualizacion()

            if not update:
                return False, "No hay actualizaciones disponibles"

            # 2. Backup de BD
            notify("Creando copia de seguridad...", 10, 100)
            backup_ok, backup_result = self.crear_backup_preactualizacion()

            if not backup_ok:
                return False, f"Error en backup: {backup_result}"

            logger.info(f"Backup creado: {backup_result}")

            # 3. Descargar
            def download_progress(downloaded, total):
                percent = int((downloaded / total) * 70) + 20  # 20-90%
                notify(f"Descargando v{update.version}...", percent, 100)

            notify("Iniciando descarga...", 20, 100)
            installer_path = self.descargar_actualizacion(download_progress)

            if not installer_path:
                return False, "Error descargando actualización"

            # 4. Instalar
            notify("Preparando instalación...", 95, 100)

            return True, installer_path

        except (sqlite3.Error, OSError, ValueError) as e:
            logger.error(f"Error en proceso de actualización: {e}", exc_info=True)
            return False, f"Error: {str(e)}"

    def limpiar_descargas_antiguas(self):
        """Elimina archivos de actualización antiguos"""
        try:
            for filename in os.listdir(self.DOWNLOAD_DIR):
                filepath = os.path.join(self.DOWNLOAD_DIR, filename)
                if os.path.isfile(filepath):
                    # Eliminar archivos de más de 7 días
                    age_days = (datetime.now().timestamp() - os.path.getmtime(filepath)) / 86400
                    if age_days > 7:
                        os.remove(filepath)
                        logger.info(f"Eliminado archivo antiguo: {filename}")
        except (sqlite3.Error, OSError, ValueError) as e:
            logger.warning(f"Error limpiando descargas antiguas: {e}")


# Singleton para uso global
_updater_instance: Optional[Updater] = None

def get_updater() -> Updater:
    """Obtiene la instancia global del updater"""
    global _updater_instance
    if _updater_instance is None:
        _updater_instance = Updater()
    return _updater_instance


def comprobar_actualizacion_async(callback: Callable[[Optional[UpdateInfo]], None]):
    """
    Comprueba actualizaciones en un hilo separado.

    Args:
        callback: Función a llamar con el resultado (UpdateInfo o None)
    """
    import threading

    def check():
        updater = get_updater()
        result = updater.comprobar_actualizacion()
        callback(result)

    thread = threading.Thread(target=check, daemon=True)
    thread.start()
