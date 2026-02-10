"""
Sistema de licencias por hardware
Vincula la licencia al ID único de la máquina
"""
import os
import hashlib
import platform
import subprocess
import json
from datetime import datetime
from app.utils.logger import get_logger

logger = get_logger('license')

# Flag para ocultar ventana de consola en Windows
SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0

# Importar módulo de derivación de secreto (ofuscado)
from app.modules.license_secret import obtener_secreto_licencia, generar_hash_licencia


class LicenseManager:
    """Gestiona la verificación de licencias"""

    # Archivo donde se guarda la licencia activada
    LICENSE_FILE = os.path.join(
        os.environ.get('PROGRAMDATA', 'C:\\ProgramData'),
        'Facturar', 'license.dat'
    )

    # Archivo donde se guarda el ID de máquina (persistente)
    MACHINE_ID_FILE = os.path.join(
        os.environ.get('PROGRAMDATA', 'C:\\ProgramData'),
        'Facturar', 'machine.id'
    )

    def __init__(self, db=None):
        self.machine_id = self._get_or_create_machine_id()
        self.db = db
        # Obtener secreto de forma ofuscada
        self._secret = obtener_secreto_licencia()

    def _get_or_create_machine_id(self):
        """
        Obtiene el ID de máquina guardado, o lo genera y guarda si no existe.
        Una vez guardado, SIEMPRE usa el mismo ID.

        Prioridad:
        1. Si existe machine.id → usarlo
        2. Si existe license.dat con machine_id → usarlo y guardarlo (migración)
        3. Si ninguno existe → generar nuevo y guardarlo
        """
        # 1. Intentar leer ID guardado en machine.id
        try:
            if os.path.exists(self.MACHINE_ID_FILE):
                with open(self.MACHINE_ID_FILE, 'r') as f:
                    saved_id = f.read().strip()
                    if saved_id and saved_id.startswith('RMPV-'):
                        return saved_id
        except (OSError, IOError):
            pass

        # 2. Migración: si hay licencia existente, usar ese ID
        try:
            if os.path.exists(self.LICENSE_FILE):
                with open(self.LICENSE_FILE, 'r') as f:
                    data = json.load(f)
                    license_machine_id = data.get('machine_id', '')
                    if license_machine_id and license_machine_id.startswith('RMPV-'):
                        # Guardar el ID de la licencia como ID fijo
                        self._save_machine_id(license_machine_id)
                        return license_machine_id
        except (OSError, json.JSONDecodeError, KeyError):
            pass

        # 3. No existe nada, generar nuevo ID
        new_id = self._generate_machine_id()
        self._save_machine_id(new_id)
        return new_id

    def _save_machine_id(self, machine_id):
        """Guarda el ID de máquina en archivo permanente"""
        try:
            os.makedirs(os.path.dirname(self.MACHINE_ID_FILE), exist_ok=True)
            with open(self.MACHINE_ID_FILE, 'w') as f:
                f.write(machine_id)
        except OSError as e:
            logger.warning(f"No se pudo guardar ID de máquina: {e}")

    def _generate_machine_id(self):
        """
        Genera un ID único basado en hardware FIJO del PC.
        Usa SOLO componentes que NUNCA cambian:
        - UUID del sistema (BIOS/UEFI)
        - Serial de placa base
        - Procesador

        NO usa componentes inestables como MAC o disco.
        """
        components = []

        # 1. UUID del sistema (BIOS/UEFI) - EL MÁS ESTABLE
        try:
            if platform.system() == 'Windows':
                result = subprocess.run(
                    ['wmic', 'csproduct', 'get', 'uuid'],
                    capture_output=True, text=True, timeout=5,
                    creationflags=SUBPROCESS_FLAGS
                )
                for line in result.stdout.strip().split('\n'):
                    line = line.strip()
                    if line and line != 'UUID' and len(line) > 10:
                        components.append(line)
                        break
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
            pass

        # 2. Serial de placa base (respaldo)
        try:
            if platform.system() == 'Windows':
                result = subprocess.run(
                    ['wmic', 'baseboard', 'get', 'serialnumber'],
                    capture_output=True, text=True, timeout=5,
                    creationflags=SUBPROCESS_FLAGS
                )
                for line in result.stdout.strip().split('\n'):
                    line = line.strip()
                    if line and line != 'SerialNumber' and line != 'To be filled by O.E.M.':
                        components.append(line)
                        break
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
            pass

        # 3. Procesador (respaldo adicional)
        components.append(platform.processor())

        # Combinar todo y generar hash
        combined = '|'.join(components)
        hash_bytes = hashlib.sha256(combined.encode()).digest()

        # Convertir a formato legible: XXXX-XXXX-XXXX-XXXX
        hex_str = hash_bytes.hex()[:16].upper()
        machine_id = f"RMPV-{hex_str[:4]}-{hex_str[4:8]}-{hex_str[8:12]}-{hex_str[12:16]}"

        return machine_id

    def get_machine_id(self):
        """Devuelve el ID de máquina formateado"""
        return self.machine_id

    def verify_license_key(self, license_key):
        """
        Verifica si una clave de licencia es válida para esta máquina.

        Args:
            license_key: Clave introducida por el usuario

        Returns:
            bool: True si la clave es válida
        """
        if not license_key:
            return False

        # Limpiar la clave
        license_key = license_key.strip().upper().replace(' ', '')

        # La clave válida se genera con el mismo algoritmo que usa el keygen
        expected_key = self._generate_expected_key()

        return license_key == expected_key

    def _generate_expected_key(self):
        """
        Genera la clave esperada para esta máquina.
        IMPORTANTE: Este algoritmo debe coincidir EXACTAMENTE con el del keygen.
        """
        # Combinar machine_id con secreto (ahora ofuscado)
        data = f"{self.machine_id}|{self._secret}"
        hash_bytes = hashlib.sha256(data.encode()).digest()

        # Formato: XXXX-XXXX-XXXX-XXXX
        hex_str = hash_bytes.hex()[:16].upper()
        key = f"{hex_str[:4]}-{hex_str[4:8]}-{hex_str[8:12]}-{hex_str[12:16]}"

        return key

    def is_activated(self):
        """
        Verifica si el programa ya está activado.

        Returns:
            bool: True si hay una licencia válida guardada
        """
        try:
            if not os.path.exists(self.LICENSE_FILE):
                return False

            with open(self.LICENSE_FILE, 'r') as f:
                data = json.load(f)

            saved_key = data.get('license_key', '')
            saved_machine_id = data.get('machine_id', '')

            # Verificar que la licencia es para esta máquina
            if saved_machine_id != self.machine_id:
                return False

            # Verificar que la clave es válida
            return self.verify_license_key(saved_key)

        except (OSError, json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error verificando licencia: {e}")
            return False

    def activate(self, license_key):
        """
        Activa el programa con una clave de licencia.

        Args:
            license_key: Clave de licencia

        Returns:
            tuple: (éxito, mensaje)
        """
        if not license_key:
            return False, "Introduce una clave de licencia"

        license_key = license_key.strip().upper()

        if not self.verify_license_key(license_key):
            return False, "Clave de licencia inválida"

        try:
            # Crear directorio si no existe
            os.makedirs(os.path.dirname(self.LICENSE_FILE), exist_ok=True)

            # Guardar licencia
            data = {
                'license_key': license_key,
                'machine_id': self.machine_id,
                'activated_at': datetime.now().isoformat(),
                'version': '1.0'
            }

            with open(self.LICENSE_FILE, 'w') as f:
                json.dump(data, f, indent=2)

            return True, "Programa activado correctamente"

        except OSError as e:
            return False, f"Error guardando licencia: {e}"

    def get_license_info(self):
        """
        Obtiene información de la licencia actual.

        Returns:
            dict o None
        """
        try:
            if not os.path.exists(self.LICENSE_FILE):
                return None

            with open(self.LICENSE_FILE, 'r') as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

    def deactivate(self):
        """Desactiva la licencia (elimina el archivo)"""
        try:
            if os.path.exists(self.LICENSE_FILE):
                os.remove(self.LICENSE_FILE)
            return True, "Licencia desactivada"
        except OSError as e:
            return False, f"Error: {e}"
