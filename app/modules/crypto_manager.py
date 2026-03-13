"""
Gestor de encriptación para datos sensibles (DNI, documentos)
Usa Fernet (AES-128) para encriptación simétrica
La clave maestra se protege con DPAPI (Windows) para vincularla al ordenador
"""
import os
import base64
from cryptography.fernet import Fernet
from app.utils.logger import get_logger
from app.exceptions import DPAPIError, DecryptionError

logger = get_logger('crypto')

# DPAPI para Windows - Protege la clave maestra vinculándola al PC
try:
    import win32crypt
    import pywintypes
    DPAPI_DISPONIBLE = True
except ImportError:
    DPAPI_DISPONIBLE = False
    pywintypes = None
    logger.error("pywin32 no disponible. Instalar: pip install pywin32")


class CryptoManager:
    """Gestiona la encriptación/desencriptación de datos sensibles"""

    def __init__(self, db):
        self.db = db
        self._cipher = None

    def _obtener_clave_maestra(self):
        """
        Obtiene o genera la clave maestra de encriptación.
        La clave se protege con DPAPI (Windows) para vincularla a este ordenador.
        Solo este PC/usuario puede desencriptar la clave.
        """
        if not DPAPI_DISPONIBLE:
            raise DPAPIError(
                operation="inicialización",
                original_error="pywin32 no disponible. Instalar con: pip install pywin32"
            )

        # Intentar obtener clave protegida con DPAPI (nuevo formato)
        result = self.db.fetch_one(
            "SELECT valor FROM configuracion WHERE clave = 'crypto_master_key_encrypted'"
        )

        if result:
            # Desencriptar con DPAPI (solo funciona en este PC/usuario)
            clave_encriptada = base64.b64decode(result['valor'])
            try:
                clave_desencriptada = win32crypt.CryptUnprotectData(
                    clave_encriptada,
                    None,  # Descripción opcional
                    None,  # Entropy opcional
                    None,  # Reserved
                    0      # Flags
                )
                # CryptUnprotectData retorna (descripción, datos)
                return clave_desencriptada[1].decode('utf-8')
            except pywintypes.error as e:
                raise DPAPIError(
                    operation="desencriptación de clave maestra",
                    original_error=(
                        f"Posibles causas: BD copiada de otro PC, "
                        f"Windows reinstalado, o cambio de usuario. "
                        f"Error técnico: {e}"
                    )
                )

        # Si existe clave antigua sin protección DPAPI, migrarla automáticamente
        result_antiguo = self.db.fetch_one(
            "SELECT valor FROM configuracion WHERE clave = 'crypto_master_key'"
        )

        if result_antiguo:
            logger.info("Detectada clave antigua sin protección DPAPI")
            logger.info("Migrando a formato seguro protegido por DPAPI...")

            # Tomar la clave existente
            clave_existente = result_antiguo['valor'].encode('utf-8')

            # Encriptarla con DPAPI
            clave_encriptada_dpapi = win32crypt.CryptProtectData(
                clave_existente,
                'REDMOVILPOS Master Key',  # Descripción
                None,  # Entropy
                None,  # Reserved
                None,  # PromptStruct
                0      # Flags (0 = solo este usuario en este PC)
            )

            # Guardar versión encriptada
            clave_base64 = base64.b64encode(clave_encriptada_dpapi).decode('utf-8')
            self.db.execute_query(
                """INSERT INTO configuracion (clave, valor, descripcion)
                   VALUES (?, ?, ?)""",
                (
                    'crypto_master_key_encrypted',
                    clave_base64,
                    'Clave maestra protegida con DPAPI - Solo desencriptable en este PC/usuario'
                )
            )

            # Eliminar clave antigua insegura
            self.db.execute_query(
                "DELETE FROM configuracion WHERE clave = 'crypto_master_key'"
            )

            logger.info("Migración completada - Clave ahora protegida con DPAPI")
            logger.info("Esta clave solo funciona en este ordenador")

            return clave_existente.decode('utf-8')

        # Primera vez: generar nueva clave protegida con DPAPI
        logger.info("Generando nueva clave maestra protegida con DPAPI...")
        nueva_clave = Fernet.generate_key()

        # Encriptar con DPAPI (vinculada a este PC/usuario)
        clave_encriptada_dpapi = win32crypt.CryptProtectData(
            nueva_clave,
            'REDMOVILPOS Master Key',  # Descripción
            None,  # Entropy (podría añadirse para más seguridad)
            None,  # Reserved
            None,  # PromptStruct
            0      # Flags (0 = solo este usuario)
        )

        # Guardar en BD (encriptada)
        clave_base64 = base64.b64encode(clave_encriptada_dpapi).decode('utf-8')
        self.db.execute_query(
            """INSERT INTO configuracion (clave, valor, descripcion)
               VALUES (?, ?, ?)""",
            (
                'crypto_master_key_encrypted',
                clave_base64,
                'Clave maestra protegida con DPAPI - Solo desencriptable en este PC/usuario'
            )
        )

        logger.info("Nueva clave maestra generada y protegida con DPAPI")
        logger.info("Esta clave solo funciona en este ordenador")
        logger.info("Los datos encriptados NO podrán abrirse si copias la BD a otro PC")

        return nueva_clave.decode('utf-8')

    def _obtener_cipher(self):
        """Obtiene el objeto Fernet para encriptación"""
        if self._cipher is None:
            clave = self._obtener_clave_maestra()
            self._cipher = Fernet(clave.encode('utf-8'))
        return self._cipher

    def encriptar(self, texto):
        """
        Encripta un texto plano.

        Args:
            texto (str): Texto a encriptar

        Returns:
            str: Texto encriptado en base64
        """
        if not texto:
            return None

        cipher = self._obtener_cipher()
        texto_bytes = texto.encode('utf-8')
        encriptado = cipher.encrypt(texto_bytes)
        return encriptado.decode('utf-8')

    def desencriptar(self, texto_encriptado):
        """
        Desencripta un texto encriptado.

        Args:
            texto_encriptado (str): Texto encriptado en base64

        Returns:
            str: Texto desencriptado, o None si falla
        """
        if not texto_encriptado:
            return None

        try:
            cipher = self._obtener_cipher()
            encriptado_bytes = texto_encriptado.encode('utf-8')
            desencriptado = cipher.decrypt(encriptado_bytes)
            return desencriptado.decode('utf-8')
        except (ValueError, TypeError) as e:
            logger.error(f"Error al desencriptar: {e}")
            return None

    def encriptar_ruta_dni(self, ruta_archivo):
        """
        Encripta la ruta de un archivo DNI.
        Útil para almacenar rutas de imágenes de DNI de forma segura.

        Args:
            ruta_archivo (str): Ruta del archivo

        Returns:
            str: Ruta encriptada
        """
        return self.encriptar(ruta_archivo)

    def desencriptar_ruta_dni(self, ruta_encriptada):
        """
        Desencripta la ruta de un archivo DNI.

        Args:
            ruta_encriptada (str): Ruta encriptada

        Returns:
            str: Ruta original del archivo
        """
        return self.desencriptar(ruta_encriptada)

    def migrar_dnis_existentes(self):
        """
        Migra DNIs existentes sin encriptar a formato encriptado.

        Returns:
            tuple: (total_migrados, errores)
        """
        migrados = 0
        errores = 0

        # Migrar clientes
        clientes = self.db.fetch_all(
            "SELECT id, dni_imagen FROM clientes WHERE dni_imagen IS NOT NULL AND dni_imagen != ''"
        )

        for cliente in clientes:
            dni_original = cliente['dni_imagen']

            # Si ya está encriptado (tiene caracteres no válidos para rutas), saltar
            if self._parece_encriptado(dni_original):
                continue

            try:
                dni_encriptado = self.encriptar_ruta_dni(dni_original)
                self.db.execute_query(
                    "UPDATE clientes SET dni_imagen = ? WHERE id = ?",
                    (dni_encriptado, cliente['id'])
                )
                migrados += 1
            except (ValueError, TypeError) as e:
                logger.error(f"Error migrando cliente {cliente['id']}: {e}")
                errores += 1

        # Migrar compras
        compras = self.db.fetch_all(
            "SELECT id, dni_imagen FROM compras WHERE dni_imagen IS NOT NULL AND dni_imagen != ''"
        )

        for compra in compras:
            dni_original = compra['dni_imagen']

            if self._parece_encriptado(dni_original):
                continue

            try:
                dni_encriptado = self.encriptar_ruta_dni(dni_original)
                self.db.execute_query(
                    "UPDATE compras SET dni_imagen = ? WHERE id = ?",
                    (dni_encriptado, compra['id'])
                )
                migrados += 1
            except (ValueError, TypeError) as e:
                logger.error(f"Error migrando compra {compra['id']}: {e}")
                errores += 1

        return migrados, errores

    def _parece_encriptado(self, texto):
        """
        Determina si un texto parece estar ya encriptado.
        Los textos encriptados con Fernet tienen caracteres específicos.
        """
        if not texto:
            return False

        # Las rutas de archivo contienen \ o / y extensiones
        # Los textos encriptados con Fernet contienen = y caracteres base64
        es_ruta = ('\\' in texto or '/' in texto) and '.' in texto
        tiene_base64 = '=' in texto[-5:]  # Fernet termina con padding =

        return tiene_base64 and not es_ruta
