"""
Gestor de autenticación y usuarios
Con protecciones de seguridad: rate limiting, bloqueo de cuentas, expiración de sesión
"""
import bcrypt
import secrets
import string
import re
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Optional, Union
from app.utils.logger import get_logger
from app.i18n import tr

# Importar configuración centralizada
from config import (
    AUTH_MAX_INTENTOS_LOGIN,
    AUTH_VENTANA_INTENTOS_MINUTOS,
    AUTH_BLOQUEO_CUENTA_MINUTOS,
    AUTH_SESION_EXPIRA_MINUTOS,
    AUTH_PASSWORD_MIN_LENGTH,
    AUTH_PASSWORD_REQUIERE_MAYUSCULA,
    AUTH_PASSWORD_REQUIERE_NUMERO,
    AUTH_PASSWORD_REQUIERE_ESPECIAL,
)

# Logger para autenticación
logger = get_logger('auth')


class AuthManager:
    """
    Gestor de autenticación con protecciones de seguridad:
    - Rate limiting: máximo de intentos por ventana de tiempo
    - Bloqueo de cuenta: tras múltiples intentos fallidos
    - Expiración de sesión: cierre automático por inactividad
    - Logging de intentos: registro de todos los intentos de login
    """

    # Configuración de seguridad (desde config.py)
    MAX_INTENTOS_LOGIN = AUTH_MAX_INTENTOS_LOGIN
    VENTANA_INTENTOS_MINUTOS = AUTH_VENTANA_INTENTOS_MINUTOS
    BLOQUEO_CUENTA_MINUTOS = AUTH_BLOQUEO_CUENTA_MINUTOS
    SESION_EXPIRA_MINUTOS = AUTH_SESION_EXPIRA_MINUTOS

    # Requisitos de contraseña (desde config.py)
    PASSWORD_MIN_LENGTH = AUTH_PASSWORD_MIN_LENGTH
    PASSWORD_REQUIERE_MAYUSCULA = AUTH_PASSWORD_REQUIERE_MAYUSCULA
    PASSWORD_REQUIERE_NUMERO = AUTH_PASSWORD_REQUIERE_NUMERO
    PASSWORD_REQUIERE_ESPECIAL = AUTH_PASSWORD_REQUIERE_ESPECIAL

    def __init__(self, db: Any) -> None:
        self.db = db
        self.usuario_actual = None
        self.ultima_actividad = None  # Para control de expiración
        self._crear_tabla_intentos_login()

    def _crear_tabla_intentos_login(self) -> None:
        """Crea la tabla para registrar intentos de login (rate limiting)"""
        try:
            self.db.execute_query("""
                CREATE TABLE IF NOT EXISTS intentos_login (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    ip_address TEXT,
                    exitoso INTEGER DEFAULT 0,
                    mensaje TEXT,
                    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.db.execute_query(
                "CREATE INDEX IF NOT EXISTS idx_intentos_login_username ON intentos_login(username)"
            )
            self.db.execute_query(
                "CREATE INDEX IF NOT EXISTS idx_intentos_login_fecha ON intentos_login(fecha)"
            )
        except sqlite3.Error as e:
            logger.error(f"Error creando tabla intentos_login: {e}")

    def _registrar_intento_login(self, username: str, exitoso: bool, mensaje: str, ip_address: str = None):
        """Registra un intento de login en la base de datos"""
        try:
            self.db.execute_query(
                """INSERT INTO intentos_login (username, ip_address, exitoso, mensaje)
                   VALUES (?, ?, ?, ?)""",
                (username, ip_address or '127.0.0.1', 1 if exitoso else 0, mensaje)
            )

            # Log según resultado
            if exitoso:
                logger.info(f"Login exitoso: {username} desde {ip_address or 'local'}")
            else:
                logger.warning(f"Login fallido: {username} - {mensaje} desde {ip_address or 'local'}")

        except sqlite3.Error as e:
            logger.error(f"Error registrando intento de login: {e}")

    def _contar_intentos_fallidos(self, username: str) -> int:
        """Cuenta los intentos fallidos en la ventana de tiempo"""
        try:
            resultado = self.db.fetch_one(
                """SELECT COUNT(*) as count FROM intentos_login
                   WHERE username = ?
                   AND exitoso = 0
                   AND datetime(fecha) > datetime('now', ?)""",
                (username, f'-{self.VENTANA_INTENTOS_MINUTOS} minutes')
            )
            return resultado['count'] if resultado else 0
        except sqlite3.Error as e:
            logger.error(f"Error contando intentos: {e}")
            return 0

    def _esta_cuenta_bloqueada(self, username: str) -> tuple[bool, int]:
        """
        Verifica si la cuenta está bloqueada por exceso de intentos.
        Retorna: (bloqueada: bool, minutos_restantes: int)
        """
        intentos = self._contar_intentos_fallidos(username)

        if intentos >= self.MAX_INTENTOS_LOGIN:
            # Obtener el último intento fallido
            ultimo = self.db.fetch_one(
                """SELECT fecha FROM intentos_login
                   WHERE username = ? AND exitoso = 0
                   ORDER BY fecha DESC LIMIT 1""",
                (username,)
            )

            if ultimo:
                # Calcular tiempo restante de bloqueo
                try:
                    fecha_ultimo = datetime.strptime(ultimo['fecha'], '%Y-%m-%d %H:%M:%S')
                    fin_bloqueo = fecha_ultimo + timedelta(minutes=self.BLOQUEO_CUENTA_MINUTOS)
                    ahora = datetime.now()

                    if ahora < fin_bloqueo:
                        minutos_restantes = int((fin_bloqueo - ahora).total_seconds() / 60) + 1
                        return True, minutos_restantes
                except (ValueError, KeyError) as e:
                    logger.error(f"Error calculando bloqueo: {e}")

        return False, 0

    def _limpiar_intentos_antiguos(self) -> None:
        """Limpia intentos de login antiguos (más de 24 horas)"""
        try:
            self.db.execute_query(
                "DELETE FROM intentos_login WHERE datetime(fecha) < datetime('now', '-24 hours')"
            )
        except sqlite3.Error as e:
            logger.error(f"Error limpiando intentos antiguos: {e}")

    def validar_fortaleza_password(self, password: str) -> tuple[bool, str]:
        """
        Valida que una contraseña cumpla los requisitos de seguridad.

        Requisitos:
        - Mínimo 8 caracteres
        - Al menos una mayúscula
        - Al menos un número
        - (Opcional) Al menos un carácter especial

        Args:
            password: Contraseña a validar

        Returns:
            tuple: (valida: bool, mensaje: str)
        """
        errores = []

        # Longitud mínima
        if len(password) < self.PASSWORD_MIN_LENGTH:
            errores.append(f"mínimo {self.PASSWORD_MIN_LENGTH} caracteres")

        # Requiere mayúscula
        if self.PASSWORD_REQUIERE_MAYUSCULA and not re.search(r'[A-Z]', password):
            errores.append("al menos una mayúscula")

        # Requiere número
        if self.PASSWORD_REQUIERE_NUMERO and not re.search(r'\d', password):
            errores.append("al menos un número")

        # Requiere carácter especial (opcional)
        if self.PASSWORD_REQUIERE_ESPECIAL and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errores.append("al menos un carácter especial (!@#$%...)")

        if errores:
            return False, f"La contraseña debe tener: {', '.join(errores)}"

        return True, "Contraseña válida"

    def obtener_requisitos_password(self) -> str:
        """Retorna los requisitos de contraseña en formato legible"""
        requisitos = [f"Mínimo {self.PASSWORD_MIN_LENGTH} caracteres"]

        if self.PASSWORD_REQUIERE_MAYUSCULA:
            requisitos.append("al menos una mayúscula")

        if self.PASSWORD_REQUIERE_NUMERO:
            requisitos.append("al menos un número")

        if self.PASSWORD_REQUIERE_ESPECIAL:
            requisitos.append("al menos un carácter especial")

        return ", ".join(requisitos)

    # --- Funciones básicas de existencia de usuarios ---
    def hay_usuarios(self) -> bool:
        """Verifica si existen usuarios en el sistema."""
        resultado = self.db.fetch_one("SELECT COUNT(*) as count FROM usuarios")
        return resultado and resultado['count'] > 0

    def crear_usuario_inicial(
        self, username: str, password: str, nombre_completo: str
    ) -> tuple[bool, Optional[str], str, Optional[int]]:
        """Crea el primer usuario administrador si no hay usuarios.
        Retorna: (exito, llave, mensaje, usuario_id)
        """
        if self.hay_usuarios():
            return False, None, "Ya existen usuarios en el sistema", None
        if len(username) < 3:
            return False, None, "El usuario debe tener al menos 3 caracteres", None

        # Validar fortaleza de contraseña
        pwd_valida, pwd_mensaje = self.validar_fortaleza_password(password)
        if not pwd_valida:
            return False, None, pwd_mensaje, None

        password_hash = self.hash_password(password)

        # Generar llave de recuperación
        llave_plana = self._generar_llave_recuperacion()
        llave_hash = self.hash_password(llave_plana)

        usuario_id = self.db.execute_query(
            """INSERT INTO usuarios (username, password_hash, nombre_completo, rol, activo, recovery_key)
               VALUES (?, ?, ?, 'admin', 1, ?)""",
            (username, password_hash, nombre_completo, llave_hash)
        )
        if usuario_id:
            return True, llave_plana, f"Usuario administrador '{username}' creado correctamente", usuario_id
        return False, None, "Error al crear usuario", None

    def asignar_establecimiento_usuario(self, usuario_id, establecimiento_id):
        """Asigna un establecimiento a un usuario"""
        result = self.db.execute_query(
            "UPDATE usuarios SET establecimiento_id = ? WHERE id = ?",
            (establecimiento_id, usuario_id)
        )
        return result is not None

    def _generar_llave_recuperacion(self):
        """Genera una llave de recuperación en formato XXXX-XXXX-XXXX-XXXX"""
        caracteres = string.ascii_uppercase + string.digits
        partes = []
        for _ in range(4):
            parte = ''.join(secrets.choice(caracteres) for _ in range(4))
            partes.append(parte)
        return '-'.join(partes)

    def hash_password(self, password: str) -> str:
        """Genera un hash seguro de la contraseña"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def verificar_password(
        self, password_o_id: Union[str, int], password_hash_o_password: Optional[str] = None
    ) -> bool:
        """
        Verifica si una contraseña es correcta.

        Uso 1 (legacy): verificar_password(password, password_hash)
        Uso 2 (nuevo):  verificar_password(usuario_id, password)
        """
        # Si el primer arg es int, es usuario_id
        if isinstance(password_o_id, int):
            usuario_id = password_o_id
            password = password_hash_o_password
            usuario = self.db.fetch_one(
                "SELECT password_hash FROM usuarios WHERE id = ?",
                (usuario_id,)
            )
            if not usuario:
                return False
            try:
                return bcrypt.checkpw(password.encode('utf-8'), usuario['password_hash'].encode('utf-8'))
            except (ValueError, AttributeError):
                return False
        else:
            # Uso legacy: password, password_hash
            password = password_o_id
            password_hash = password_hash_o_password
            try:
                return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
            except (ValueError, AttributeError):
                return False

    def login(
        self, username: str, password: str, ip_address: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        Intenta hacer login con usuario y contraseña.

        Incluye protecciones de seguridad:
        - Rate limiting: bloqueo tras múltiples intentos fallidos
        - Logging de intentos: registro de todos los intentos
        - Limpieza automática de intentos antiguos

        Args:
            username: Nombre de usuario
            password: Contraseña
            ip_address: IP del cliente (opcional, para logging)

        Returns:
            tuple: (exito: bool, mensaje: str)
        """
        # Limpiar intentos antiguos periódicamente
        self._limpiar_intentos_antiguos()

        # Verificar si la cuenta está bloqueada
        bloqueada, minutos_restantes = self._esta_cuenta_bloqueada(username)
        if bloqueada:
            mensaje = tr("Cuenta bloqueada por exceso de intentos. Espera {minutos} minutos.", minutos=minutos_restantes)
            self._registrar_intento_login(username, False, "Cuenta bloqueada", ip_address)
            logger.warning(f"Intento de login en cuenta bloqueada: {username}")
            return False, mensaje

        # Buscar usuario
        usuario = self.db.fetch_one(
            "SELECT * FROM usuarios WHERE username = ? AND activo = 1",
            (username,)
        )

        if not usuario:
            self._registrar_intento_login(username, False, "Usuario no encontrado", ip_address)
            return False, tr("Usuario no encontrado o inactivo")

        # Verificar contraseña
        if not self.verificar_password(password, usuario['password_hash']):
            intentos_restantes = self.MAX_INTENTOS_LOGIN - self._contar_intentos_fallidos(username) - 1
            self._registrar_intento_login(username, False, "Contraseña incorrecta", ip_address)

            if intentos_restantes > 0:
                return False, tr("Contraseña incorrecta. {intentos} intentos restantes.", intentos=intentos_restantes)
            else:
                return False, tr("Contraseña incorrecta. Cuenta bloqueada por {minutos} minutos.", minutos=self.BLOQUEO_CUENTA_MINUTOS)

        # Login exitoso - registrar y actualizar
        self._registrar_intento_login(username, True, "Login exitoso", ip_address)

        # Actualizar último acceso
        self.db.execute_query(
            "UPDATE usuarios SET ultimo_acceso = CURRENT_TIMESTAMP WHERE id = ?",
            (usuario['id'],)
        )

        # Guardar usuario actual (sin el hash de contraseña)
        self.usuario_actual = {
            'id': usuario['id'],
            'username': usuario['username'],
            'nombre_completo': usuario['nombre_completo'],
            'rol': usuario['rol'],
            'establecimiento_id': usuario.get('establecimiento_id')
        }

        # Registrar tiempo de actividad para expiración de sesión
        self.ultima_actividad = datetime.now()

        return True, tr("Bienvenido, {usuario}", usuario=usuario['nombre_completo'])

    def verificar_sesion_activa(self) -> bool:
        """
        Verifica si la sesión sigue activa (no ha expirado por inactividad).

        Returns:
            bool: True si la sesión está activa, False si expiró
        """
        if not self.usuario_actual:
            return False

        if not self.ultima_actividad:
            return True  # Sin control de actividad, asumir activa

        tiempo_inactivo = datetime.now() - self.ultima_actividad
        minutos_inactivo = tiempo_inactivo.total_seconds() / 60

        if minutos_inactivo > self.SESION_EXPIRA_MINUTOS:
            logger.info(f"Sesión expirada por inactividad: {self.usuario_actual['username']}")
            self.logout()
            return False

        return True

    def registrar_actividad(self):
        """Registra actividad del usuario para renovar tiempo de sesión"""
        if self.usuario_actual:
            self.ultima_actividad = datetime.now()

    def logout(self):
        """Cierra la sesión actual"""
        self.usuario_actual = None

    def is_admin(self):
        """Verifica si el usuario actual es administrador"""
        return self.usuario_actual and self.usuario_actual['rol'] == 'admin'

    def obtener_usuario_actual(self):
        """Obtiene el usuario actualmente logueado"""
        return self.usuario_actual

    def obtener_todos_usuarios(self):
        """Obtiene todos los usuarios (solo admin)"""
        if not self.is_admin():
            return []

        return self.db.fetch_all(
            "SELECT id, username, nombre_completo, rol, establecimiento_id, activo, fecha_creacion, ultimo_acceso, totp_habilitado FROM usuarios ORDER BY username"
        )

    def crear_usuario(self, username, password, nombre_completo, rol='usuario', establecimiento_id=None):
        """Crea un nuevo usuario (solo admin)"""
        if not self.is_admin():
            return False, "No tienes permisos para crear usuarios"

        # Verificar que no exista
        existe = self.db.fetch_one("SELECT id FROM usuarios WHERE username = ?", (username,))
        if existe:
            return False, "El nombre de usuario ya existe"

        # Validar fortaleza de contraseña
        pwd_valida, pwd_mensaje = self.validar_fortaleza_password(password)
        if not pwd_valida:
            return False, pwd_mensaje

        # Validar establecimiento
        if not establecimiento_id:
            return False, "Debe seleccionar un establecimiento"

        # Hash de contraseña
        password_hash = self.hash_password(password)

        # Crear usuario
        usuario_id = self.db.execute_query(
            """INSERT INTO usuarios (username, password_hash, nombre_completo, rol, establecimiento_id)
               VALUES (?, ?, ?, ?, ?)""",
            (username, password_hash, nombre_completo, rol, establecimiento_id)
        )

        if usuario_id:
            return True, f"Usuario {username} creado correctamente"
        return False, "Error al crear usuario"

    def obtener_establecimientos(self):
        """Obtiene todos los establecimientos activos"""
        return self.db.fetch_all(
            "SELECT id, nombre FROM establecimientos WHERE activo = 1 ORDER BY nombre"
        )

    def actualizar_usuario(self, usuario_id, datos):
        """Actualiza un usuario existente (solo admin)"""
        if not self.is_admin():
            return False, "No tienes permisos para actualizar usuarios"

        # Verificar que no sea el mismo usuario tratando de quitarse admin
        if usuario_id == self.usuario_actual['id'] and datos.get('rol') != 'admin':
            return False, "No puedes quitarte el rol de administrador"

        # Construir query
        campos = []
        valores = []

        if 'nombre_completo' in datos:
            campos.append("nombre_completo = ?")
            valores.append(datos['nombre_completo'])

        if 'rol' in datos:
            campos.append("rol = ?")
            valores.append(datos['rol'])

        if 'activo' in datos:
            campos.append("activo = ?")
            valores.append(datos['activo'])

        if 'establecimiento_id' in datos:
            campos.append("establecimiento_id = ?")
            valores.append(datos['establecimiento_id'])

        if 'password' in datos and datos['password']:
            es_valida, msg_validacion = self.validar_fortaleza_password(datos['password'])
            if not es_valida:
                return False, msg_validacion
            campos.append("password_hash = ?")
            valores.append(self.hash_password(datos['password']))

        if not campos:
            return False, "No hay datos para actualizar"

        valores.append(usuario_id)
        query = f"UPDATE usuarios SET {', '.join(campos)} WHERE id = ?"

        result = self.db.execute_query(query, valores)

        if result is not None:
            return True, "Usuario actualizado correctamente"
        return False, "Error al actualizar usuario"

    def cambiar_password(self, password_actual, password_nueva):
        """Permite al usuario cambiar su propia contraseña"""
        if not self.usuario_actual:
            return False, "No hay sesión activa"

        # Verificar contraseña actual
        usuario = self.db.fetch_one(
            "SELECT password_hash FROM usuarios WHERE id = ?",
            (self.usuario_actual['id'],)
        )

        if not usuario:
            return False, "Usuario no encontrado"

        if not self.verificar_password(password_actual, usuario['password_hash']):
            return False, "La contraseña actual es incorrecta"

        # Validar fortaleza de nueva contraseña
        pwd_valida, pwd_mensaje = self.validar_fortaleza_password(password_nueva)
        if not pwd_valida:
            return False, pwd_mensaje

        # Actualizar contraseña
        password_hash = self.hash_password(password_nueva)
        result = self.db.execute_query(
            "UPDATE usuarios SET password_hash = ? WHERE id = ?",
            (password_hash, self.usuario_actual['id'])
        )

        if result is not None:
            return True, "Contraseña cambiada correctamente"
        return False, "Error al cambiar contraseña"

    def desactivar_usuario(self, usuario_id):
        """Desactiva un usuario (no lo elimina)"""
        if not self.is_admin():
            return False, "No tienes permisos para desactivar usuarios"

        # No permitir desactivarse a sí mismo
        if usuario_id == self.usuario_actual['id']:
            return False, "No puedes desactivarte a ti mismo"

        result = self.db.execute_query(
            "UPDATE usuarios SET activo = 0 WHERE id = ?",
            (usuario_id,)
        )

        if result is not None:
            return True, "Usuario desactivado correctamente"
        return False, "Error al desactivar usuario"

    def activar_usuario(self, usuario_id):
        """Activa un usuario desactivado"""
        if not self.is_admin():
            return False, "No tienes permisos para activar usuarios"

        result = self.db.execute_query(
            "UPDATE usuarios SET activo = 1 WHERE id = ?",
            (usuario_id,)
        )

        if result is not None:
            return True, "Usuario activado correctamente"
        return False, "Error al activar usuario"

    def recuperar_password_con_llave(self, username, llave, nueva_password):
        """Recupera la contraseña usando la llave de recuperación"""
        # Buscar usuario
        usuario = self.db.fetch_one(
            "SELECT id, recovery_key FROM usuarios WHERE username = ? AND activo = 1",
            (username,)
        )

        if not usuario:
            return False, "Usuario no encontrado o inactivo"

        if not usuario['recovery_key']:
            return False, "Este usuario no tiene llave de recuperación configurada"

        # Verificar llave de recuperación
        llave_limpia = llave.strip().upper().replace(' ', '')
        try:
            if not bcrypt.checkpw(llave_limpia.encode('utf-8'), usuario['recovery_key'].encode('utf-8')):
                return False, "Llave de recuperación incorrecta"
        except (ValueError, AttributeError):
            return False, "Error al verificar la llave"

        # Validar nueva contraseña con misma política que creación
        es_valida, msg_validacion = self.validar_fortaleza_password(nueva_password)
        if not es_valida:
            return False, msg_validacion

        # Actualizar contraseña
        password_hash = self.hash_password(nueva_password)
        result = self.db.execute_query(
            "UPDATE usuarios SET password_hash = ? WHERE id = ?",
            (password_hash, usuario['id'])
        )

        if result is not None:
            return True, "Contraseña actualizada correctamente. Ya puedes iniciar sesión."
        return False, "Error al actualizar contraseña"

    # ═══════════════════════════════════════════════════════════════
    # TOTP 2FA (Autenticación en Dos Pasos)
    # ═══════════════════════════════════════════════════════════════

    def _get_crypto_manager(self):
        """Obtiene una instancia de CryptoManager para cifrar/descifrar secretos TOTP"""
        from app.modules.crypto_manager import CryptoManager
        return CryptoManager(self.db)

    def tiene_totp(self, usuario_id: int) -> bool:
        """Comprueba si el usuario tiene 2FA activado"""
        usuario = self.db.fetch_one(
            "SELECT totp_habilitado FROM usuarios WHERE id = ?",
            (usuario_id,)
        )
        return bool(usuario and usuario.get('totp_habilitado'))

    def generar_totp_secret(self, usuario_id: int) -> tuple:
        """
        Genera un secreto TOTP y lo guarda cifrado en la BD.
        No activa 2FA todavía (se activa al verificar el primer código).

        Returns:
            tuple: (exito, secret_plaintext, provisioning_uri) o (False, None, mensaje_error)
        """
        import pyotp

        usuario = self.db.fetch_one(
            "SELECT username FROM usuarios WHERE id = ?",
            (usuario_id,)
        )
        if not usuario:
            return False, None, tr("Usuario no encontrado")

        secret = pyotp.random_base32()

        # Cifrar el secreto antes de guardar
        try:
            crypto = self._get_crypto_manager()
            secret_cifrado = crypto.encriptar(secret)
        except Exception as e:
            logger.error(f"Error al cifrar secreto TOTP: {e}")
            return False, None, tr("Error al generar secreto 2FA")

        # Guardar secreto cifrado (sin activar todavía)
        result = self.db.execute_query(
            "UPDATE usuarios SET totp_secret = ?, totp_habilitado = 0 WHERE id = ?",
            (secret_cifrado, usuario_id)
        )

        if result is None:
            return False, None, tr("Error al guardar secreto 2FA")

        # Generar URI para el QR
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=usuario['username'],
            issuer_name="RedMovilPOS"
        )

        logger.info(f"Secreto TOTP generado para usuario {usuario_id}")
        return True, secret, provisioning_uri

    def activar_totp(self, usuario_id: int, codigo_otp: str) -> tuple:
        """
        Verifica el primer código OTP y activa 2FA si es correcto.

        Returns:
            tuple: (exito, mensaje)
        """
        import pyotp

        usuario = self.db.fetch_one(
            "SELECT totp_secret FROM usuarios WHERE id = ?",
            (usuario_id,)
        )
        if not usuario or not usuario.get('totp_secret'):
            return False, tr("No hay secreto 2FA configurado")

        # Descifrar secreto
        try:
            crypto = self._get_crypto_manager()
            secret = crypto.desencriptar(usuario['totp_secret'])
        except Exception as e:
            logger.error(f"Error al descifrar secreto TOTP: {e}")
            return False, tr("Error al verificar código")

        if not secret:
            return False, tr("Error al descifrar secreto 2FA")

        # Verificar código
        totp = pyotp.TOTP(secret)
        if not totp.verify(codigo_otp, valid_window=1):
            return False, tr("Código incorrecto. Inténtalo de nuevo.")

        # Activar 2FA
        result = self.db.execute_query(
            "UPDATE usuarios SET totp_habilitado = 1 WHERE id = ?",
            (usuario_id,)
        )

        if result is None:
            return False, tr("Error al activar 2FA")

        logger.info(f"TOTP 2FA activado para usuario {usuario_id}")
        return True, tr("Autenticación en dos pasos activada correctamente")

    def verificar_totp(self, usuario_id: int, codigo_otp: str) -> bool:
        """
        Verifica un código TOTP durante el login.
        valid_window=1 permite códigos del periodo anterior/siguiente (tolerancia +-30s).
        """
        import pyotp

        usuario = self.db.fetch_one(
            "SELECT totp_secret, totp_habilitado FROM usuarios WHERE id = ?",
            (usuario_id,)
        )
        if not usuario or not usuario.get('totp_habilitado') or not usuario.get('totp_secret'):
            return False

        try:
            crypto = self._get_crypto_manager()
            secret = crypto.desencriptar(usuario['totp_secret'])
        except Exception as e:
            logger.error(f"Error al descifrar secreto TOTP para login: {e}")
            return False

        if not secret:
            return False

        totp = pyotp.TOTP(secret)
        return totp.verify(codigo_otp, valid_window=1)

    def desactivar_totp(self, usuario_id: int) -> tuple:
        """Desactiva 2FA y borra el secreto"""
        result = self.db.execute_query(
            "UPDATE usuarios SET totp_secret = NULL, totp_habilitado = 0 WHERE id = ?",
            (usuario_id,)
        )
        if result is None:
            return False, tr("Error al desactivar 2FA")

        logger.info(f"TOTP 2FA desactivado para usuario {usuario_id}")
        return True, tr("Autenticación en dos pasos desactivada")
