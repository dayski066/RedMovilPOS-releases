"""
Sistema de Facturación - RABI EL-OUAHIDI Y OTROS ESPJ
Aplicación de escritorio para gestión de facturas con autenticación
"""
import sys
import os
import atexit
import subprocess
import platform

# Flag para ocultar ventana de consola en Windows
SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0

# IMPORTANTE: Configurar atributos Qt ANTES de crear QApplication
# Esto soluciona problemas de renderizado en Windows
from PyQt5.QtCore import Qt, QTimer, QEventLoop
from PyQt5.QtWidgets import QApplication, QMessageBox, QSplashScreen, QLabel, QVBoxLayout, QWidget
from PyQt5.QtGui import QPixmap, QFont, QColor, QPainter

# Forzar renderizado por software para evitar glitches de GPU
QApplication.setAttribute(Qt.AA_UseSoftwareOpenGL, True)
# Habilitar escalado de alto DPI
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

from app.ui.main_window import MainWindow
from app.ui.login_dialog import LoginDialog
from app.ui.loading_dialog import LoadingDialog
from app.db.database import init_database, Database
from app.modules.auth_manager import AuthManager
from app.modules.license_manager import LicenseManager
from app.ui.activation_dialog import ActivationDialog
from app.modules.backup_manager import realizar_backup_inicial
from app.utils.cleanup import limpiar_temporales_silencioso
from config import DB_PATH, APP_VERSION, APP_NAME

# Archivo de lock para detectar instancia única
LOCK_FILE = os.path.join(os.path.dirname(__file__), '.app.lock')


def crear_lock():
    """Crea el archivo de lock"""
    try:
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
        return True
    except (OSError, IOError):
        return False


def eliminar_lock():
    """Elimina el archivo de lock"""
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except (OSError, IOError):
        pass


def verificar_instancia_unica():
    """Verifica si ya hay una instancia corriendo"""
    if os.path.exists(LOCK_FILE):
        # Verificar si el proceso aún existe
        try:
            with open(LOCK_FILE, 'r') as f:
                pid = int(f.read().strip())

            # En Windows, intentar verificar si el proceso existe
            result = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'],
                                  capture_output=True, text=True,
                                  creationflags=SUBPROCESS_FLAGS)

            if str(pid) in result.stdout:
                # El proceso aún existe
                return False
            else:
                # El archivo quedó huérfano, eliminarlo
                eliminar_lock()
                return True
        except (OSError, ValueError, subprocess.SubprocessError):
            # Error al leer el archivo, eliminarlo por seguridad
            eliminar_lock()
            return True
    return True


def main():
    # Verificar instancia única
    if not verificar_instancia_unica():
        # Crear una QApplication temporal solo para mostrar el mensaje
        app = QApplication(sys.argv)
        QMessageBox.warning(
            None,
            "Aplicación ya abierta",
            "Ya hay una instancia de RedMovilpos ejecutándose.\n\n"
            "Por favor, usa la ventana ya abierta o ciérrala antes de abrir una nueva."
        )
        sys.exit(1)

    # Crear archivo de lock
    if not crear_lock():
        print("ERROR: No se pudo crear el archivo de bloqueo")
        sys.exit(1)

    # Registrar función de limpieza
    atexit.register(eliminar_lock)

    # Inicializar base de datos
    print("=" * 60)
    print(f"  {APP_NAME} v{APP_VERSION}")
    print("  RABI EL-OUAHIDI Y OTROS ESPJ")
    print("=" * 60)
    print("\nInicializando base de datos...")

    if not init_database():
        print("ERROR: No se pudo inicializar la base de datos")
        print("Verifica los permisos de escritura en la carpeta de datos")
        print("Revisa la configuración en config.py")
        input("\nPresiona Enter para salir...")
        sys.exit(1)

    print("[OK] Base de datos inicializada correctamente\n")

    # Realizar backup automático de la BD (si corresponde)
    print("Verificando backup automático...")
    realizar_backup_inicial(DB_PATH)
    
    # Limpiar archivos temporales huérfanos (PDFs, etc.)
    limpiar_temporales_silencioso()

    # Crear aplicación
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Estilo moderno

    # Aplicar Tema (por defecto dark, pero preparado para configuración)
    from app.ui.styles import apply_theme
    
    # Intentar leer preferencia de tema de la base de datos
    tema_inicial = "dark"
    try:
        # Mini conexión rápida solo para leer esto
        db_temp = Database()
        if db_temp.connect():
            res = db_temp.fetch_one("SELECT valor FROM configuracion WHERE clave = 'tema'")
            if res:
                tema_inicial = res['valor']
            db_temp.disconnect()
            
        # IMPORTANTE: Recargar idioma preferido ahora que la BD está lista
        from app.i18n import get_translator
        get_translator().refresh_language()
        
    except Exception as e:
        print(f"No se pudo leer preferencia de tema/idioma: {e}")

    apply_theme(app, tema_inicial)

    # Verificar licencia antes de continuar
    license_manager = LicenseManager()
    if not license_manager.is_activated():
        print("[!] Programa no activado - mostrando ventana de activación\n")
        activation_dialog = ActivationDialog()
        if not activation_dialog.exec_() or not activation_dialog.is_activated():
            print("[X] Activación cancelada o fallida\n")
            sys.exit(0)
        print("[OK] Programa activado correctamente\n")
    else:
        print("[OK] Licencia válida verificada\n")

    # Conectar a base de datos
    db = Database()
    if not db.connect():
        QMessageBox.critical(
            None,
            "Error de Conexión",
            "No se pudo conectar a la base de datos.\n\nVerifica la configuración en config.py"
        )
        sys.exit(1)

    # Crear gestor de autenticación
    auth_manager = AuthManager(db)

    # Bucle de login - permitir múltiples intentos
    primera_vez = True  # Auto-login solo en la primera apertura
    
    from app.i18n import get_translator

    while True:
        # Refrescar idioma por si cambió en la sesión anterior
        get_translator().refresh_language()

        # Mostrar ventana de login
        # permitir_autologin=True solo la primera vez, no cuando se cierra sesión
        login_dialog = LoginDialog(db, auth_manager, permitir_autologin=primera_vez)
        primera_vez = False  # Las siguientes veces NO hacer auto-login

        if login_dialog.exec_():
            # Login exitoso - obtener usuario
            usuario = auth_manager.obtener_usuario_actual()

            if usuario:
                print(f"[OK] Usuario autenticado: {usuario['nombre_completo']} ({usuario['rol']})\n")

                # Mostrar diálogo de carga mientras se inicializa la ventana principal
                loading = LoadingDialog()
                loading.show()

                # Procesar eventos múltiples veces para asegurar que el loading
                # se renderice completamente y las animaciones comiencen
                for _ in range(5):
                    app.processEvents()

                # Pequeño delay para que el usuario vea el loading antes del bloqueo
                # Esto permite que las animaciones se muestren correctamente
                loop = QEventLoop()
                QTimer.singleShot(150, loop.quit)
                loop.exec_()

                # Crear ventana principal (puede tardar - el loading ya está visible)
                window = MainWindow(auth_manager)

                # Procesar eventos para asegurar que MainWindow está lista
                app.processEvents()

                # Cerrar loading y mostrar ventana principal
                loading.close()
                app.processEvents()  # Asegurar que el loading se cerró
                window.show()

                # Ejecutar aplicación
                exit_code = app.exec_()

                # Si se cerró sesión (no cerró la app), volver al login
                if auth_manager.obtener_usuario_actual() is None:
                    print("\n[OK] Sesión cerrada\n")
                    continue  # Volver a mostrar login
                else:
                    # Usuario cerró la aplicación
                    db.disconnect()
                    sys.exit(exit_code)
            else:
                # No se obtuvo usuario (error inesperado)
                QMessageBox.critical(
                    None,
                    "Error",
                    "Error al obtener información del usuario"
                )
                db.disconnect()
                sys.exit(1)
        else:
            # Usuario canceló el login
            print("[X] Login cancelado\n")
            db.disconnect()
            sys.exit(0)


if __name__ == "__main__":
    main()
