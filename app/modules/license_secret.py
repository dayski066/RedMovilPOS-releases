"""
Módulo de derivación de secreto para el sistema de licencias
============================================================
El secreto se almacena cifrado con DPAPI (Windows) vinculado al PC.
En la primera ejecución se genera y cifra automáticamente.

ADVERTENCIA: Cambiar este algoritmo INVALIDARÁ todas las licencias existentes.
"""
import os
import hashlib
import base64

# Ruta del secreto cifrado con DPAPI
_SECRET_FILE = os.path.join(
    os.environ.get('PROGRAMDATA', 'C:\\ProgramData'),
    'Facturar', 'data', 'license.key.enc'
)

# Cache en memoria para no descifrar en cada llamada
_cached_secret = None


def _cifrar_con_dpapi(datos_bytes):
    """Cifra bytes con DPAPI (solo funciona en este PC/usuario)"""
    try:
        import win32crypt
        encrypted = win32crypt.CryptProtectData(
            datos_bytes, "RedMovilPOS License", None, None, None, 0
        )
        return encrypted
    except ImportError:
        return None


def _descifrar_con_dpapi(datos_cifrados):
    """Descifra bytes con DPAPI (solo funciona en este PC/usuario)"""
    try:
        import win32crypt
        _, decrypted = win32crypt.CryptUnprotectData(
            datos_cifrados, None, None, None, 0
        )
        return decrypted
    except (ImportError, Exception):
        return None


def _derivar_componentes():
    """
    Deriva los componentes del secreto.
    Solo se usa una vez para migración inicial.
    """
    _c1 = base64.b64decode(b'UmVkTW92aWxQT1M=').decode()
    _c2 = base64.b64decode(b'MjAyNA==').decode()
    _c3 = base64.b64decode(b'TGljZW5zZUtleQ==').decode()
    _c4 = base64.b64decode(b'U2VjcmV0').decode()
    _c5 = base64.b64decode(b'U2FsdA==').decode()
    _c6 = base64.b64decode(b'WDlLMg==').decode()

    return f"{_c1}_{_c2}_{_c3}_{_c4}_{_c5}_{_c6}"


def _guardar_secreto_cifrado(secreto):
    """Cifra el secreto con DPAPI y lo guarda en disco"""
    try:
        datos_cifrados = _cifrar_con_dpapi(secreto.encode('utf-8'))
        if datos_cifrados:
            os.makedirs(os.path.dirname(_SECRET_FILE), exist_ok=True)
            with open(_SECRET_FILE, 'wb') as f:
                f.write(datos_cifrados)
            return True
    except (OSError, IOError):
        pass
    return False


def _cargar_secreto_cifrado():
    """Lee y descifra el secreto desde el archivo DPAPI"""
    try:
        if os.path.exists(_SECRET_FILE):
            with open(_SECRET_FILE, 'rb') as f:
                datos_cifrados = f.read()
            datos = _descifrar_con_dpapi(datos_cifrados)
            if datos:
                return datos.decode('utf-8')
    except (OSError, IOError, UnicodeDecodeError):
        pass
    return None


def obtener_secreto_licencia():
    """
    Obtiene el secreto para la generación/verificación de licencias.
    Prioridad:
    1. Cache en memoria
    2. Archivo cifrado con DPAPI
    3. Derivación + migración (primera vez)

    Returns:
        str: El secreto para el sistema de licencias

    IMPORTANTE: Este secreto DEBE ser idéntico en:
        - app/modules/license_manager.py
        - generador_claves/keygen.py
        - generador_claves/keygen_gui.py
    """
    global _cached_secret

    if _cached_secret:
        return _cached_secret

    # Intentar cargar desde archivo cifrado DPAPI
    secreto = _cargar_secreto_cifrado()
    if secreto:
        _cached_secret = secreto
        return secreto

    # Primera ejecución: derivar y cifrar para futuras cargas
    secreto = _derivar_componentes()
    _guardar_secreto_cifrado(secreto)
    _cached_secret = secreto
    return secreto


def generar_hash_licencia(machine_id: str) -> str:
    """
    Genera la clave de licencia para un ID de máquina.

    Args:
        machine_id: ID de máquina (formato: RMPV-XXXX-XXXX-XXXX-XXXX)

    Returns:
        str: Clave de licencia (formato: XXXX-XXXX-XXXX-XXXX)
    """
    machine_id = machine_id.strip().upper()
    secret = obtener_secreto_licencia()

    data = f"{machine_id}|{secret}"
    hash_bytes = hashlib.sha256(data.encode()).digest()

    hex_str = hash_bytes.hex()[:16].upper()
    key = f"{hex_str[:4]}-{hex_str[4:8]}-{hex_str[8:12]}-{hex_str[12:16]}"

    return key
