"""
Excepciones personalizadas para RedMovilPOS

Jerarquía de excepciones:
- RedMovilError (base)
  - AuthenticationError (login, password, sesión)
  - DatabaseError (conexión, queries)
  - LicenseError (activación, validación)
  - CryptoError (encriptación, DPAPI)
  - ValidationError (datos de entrada)
"""


class RedMovilError(Exception):
    """Excepción base para todas las excepciones de RedMovilPOS"""
    
    def __init__(self, message: str, code: str = None, details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)
    
    def __str__(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message


# =============================================================================
# Excepciones de Autenticación
# =============================================================================

class AuthenticationError(RedMovilError):
    """Error durante el proceso de autenticación"""
    pass


class LoginFailedError(AuthenticationError):
    """Error de login: credenciales incorrectas"""
    
    def __init__(self, username: str, reason: str = "Credenciales inválidas"):
        super().__init__(
            message=f"Login fallido para '{username}': {reason}",
            code="AUTH_LOGIN_FAILED",
            details={"username": username, "reason": reason}
        )


class AccountLockedError(AuthenticationError):
    """Error: cuenta bloqueada por exceso de intentos"""
    
    def __init__(self, username: str, minutes_remaining: int):
        super().__init__(
            message=f"Cuenta '{username}' bloqueada. Espera {minutes_remaining} minutos.",
            code="AUTH_ACCOUNT_LOCKED",
            details={"username": username, "minutes_remaining": minutes_remaining}
        )


class SessionExpiredError(AuthenticationError):
    """Error: sesión expirada por inactividad"""
    
    def __init__(self, username: str = None):
        super().__init__(
            message="Sesión expirada por inactividad",
            code="AUTH_SESSION_EXPIRED",
            details={"username": username}
        )


class WeakPasswordError(AuthenticationError):
    """Error: contraseña no cumple requisitos de seguridad"""
    
    def __init__(self, requirements: str):
        super().__init__(
            message=f"Contraseña débil. Requisitos: {requirements}",
            code="AUTH_WEAK_PASSWORD",
            details={"requirements": requirements}
        )


# =============================================================================
# Excepciones de Base de Datos
# =============================================================================

class DatabaseError(RedMovilError):
    """Error de base de datos genérico"""
    pass


class DatabaseConnectionError(DatabaseError):
    """Error al conectar con la base de datos"""
    
    def __init__(self, db_path: str, original_error: str = None):
        super().__init__(
            message=f"No se pudo conectar a la base de datos: {db_path}",
            code="DB_CONNECTION_FAILED",
            details={"db_path": db_path, "original_error": original_error}
        )


class DatabaseQueryError(DatabaseError):
    """Error al ejecutar una query"""
    
    def __init__(self, query: str = None, original_error: str = None):
        super().__init__(
            message=f"Error ejecutando query en la base de datos",
            code="DB_QUERY_FAILED",
            details={"query": query[:100] if query else None, "original_error": original_error}
        )


# =============================================================================
# Excepciones de Licencia
# =============================================================================

class LicenseError(RedMovilError):
    """Error relacionado con licencias"""
    pass


class LicenseInvalidError(LicenseError):
    """Licencia inválida para este equipo"""
    
    def __init__(self, machine_id: str = None):
        super().__init__(
            message="La clave de licencia no es válida para este equipo",
            code="LICENSE_INVALID",
            details={"machine_id": machine_id}
        )


class LicenseExpiredError(LicenseError):
    """Licencia expirada"""
    
    def __init__(self, expiration_date: str = None):
        super().__init__(
            message="La licencia ha expirado",
            code="LICENSE_EXPIRED",
            details={"expiration_date": expiration_date}
        )


class LicenseNotFoundError(LicenseError):
    """No se encontró archivo de licencia"""
    
    def __init__(self):
        super().__init__(
            message="No se encontró licencia activada",
            code="LICENSE_NOT_FOUND"
        )


# =============================================================================
# Excepciones de Criptografía
# =============================================================================

class CryptoError(RedMovilError):
    """Error de criptografía genérico"""
    pass


class EncryptionError(CryptoError):
    """Error al encriptar datos"""
    
    def __init__(self, original_error: str = None):
        super().__init__(
            message="Error al encriptar datos",
            code="CRYPTO_ENCRYPT_FAILED",
            details={"original_error": original_error}
        )


class DecryptionError(CryptoError):
    """Error al desencriptar datos"""
    
    def __init__(self, original_error: str = None):
        super().__init__(
            message="Error al desencriptar datos. ¿Datos corruptos o clave incorrecta?",
            code="CRYPTO_DECRYPT_FAILED",
            details={"original_error": original_error}
        )


class DPAPIError(CryptoError):
    """Error de DPAPI (Windows Data Protection)"""
    
    def __init__(self, operation: str = "unknown", original_error: str = None):
        super().__init__(
            message=f"Error de DPAPI durante {operation}",
            code="CRYPTO_DPAPI_FAILED",
            details={"operation": operation, "original_error": original_error}
        )


# =============================================================================
# Excepciones de Validación
# =============================================================================

class ValidationError(RedMovilError):
    """Error de validación de datos de entrada"""
    pass


class InvalidNIFError(ValidationError):
    """NIF/CIF/NIE inválido"""
    
    def __init__(self, document: str, reason: str = None):
        super().__init__(
            message=f"Documento '{document}' no válido: {reason or 'formato incorrecto'}",
            code="VALIDATION_INVALID_NIF",
            details={"document": document, "reason": reason}
        )


class InvalidEmailError(ValidationError):
    """Email inválido"""
    
    def __init__(self, email: str):
        super().__init__(
            message=f"Email '{email}' no tiene un formato válido",
            code="VALIDATION_INVALID_EMAIL",
            details={"email": email}
        )


class InvalidPhoneError(ValidationError):
    """Teléfono inválido"""
    
    def __init__(self, phone: str):
        super().__init__(
            message=f"Teléfono '{phone}' no es válido",
            code="VALIDATION_INVALID_PHONE",
            details={"phone": phone}
        )


class InvalidIMEIError(ValidationError):
    """IMEI inválido"""

    def __init__(self, imei: str, reason: str = None):
        super().__init__(
            message=f"IMEI '{imei}' no válido: {reason or 'checksum incorrecto'}",
            code="VALIDATION_INVALID_IMEI",
            details={"imei": imei, "reason": reason}
        )


# =============================================================================
# Excepciones de Hardware/Dispositivos
# =============================================================================

class HardwareError(RedMovilError):
    """Error de hardware genérico (impresoras, escáneres)"""
    pass


class PrinterError(HardwareError):
    """Error de impresión"""

    def __init__(self, message: str, original_error: str = None):
        super().__init__(
            message=message,
            code="HW_PRINTER_ERROR",
            details={"original_error": original_error}
        )


class ScannerError(HardwareError):
    """Error de escaneo"""

    def __init__(self, message: str, original_error: str = None):
        super().__init__(
            message=message,
            code="HW_SCANNER_ERROR",
            details={"original_error": original_error}
        )


# =============================================================================
# Excepciones de Generación de Documentos
# =============================================================================

class PDFGenerationError(RedMovilError):
    """Error al generar un documento PDF"""

    def __init__(self, message: str, original_error: str = None):
        super().__init__(
            message=message,
            code="PDF_GENERATION_FAILED",
            details={"original_error": original_error}
        )


# =============================================================================
# Excepciones de Caja
# =============================================================================

class CajaError(RedMovilError):
    """Error relacionado con el estado de la caja"""

    def __init__(self, message: str, estado: str = None):
        super().__init__(
            message=message,
            code="CAJA_STATE_ERROR",
            details={"estado": estado}
        )
