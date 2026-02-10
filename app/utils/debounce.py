"""
Utilidad de debounce para PyQt5
Retrasa la ejecución de funciones para evitar llamadas excesivas
Útil para búsquedas en tiempo real mientras el usuario escribe
"""
import sqlite3
from PyQt5.QtCore import QTimer
from app.utils.logger import logger


class Debouncer:
    """
    Clase que implementa debounce para funciones.

    Ejemplo de uso:
        # En __init__ del widget:
        self.search_debouncer = Debouncer(300)  # 300ms de delay

        # Conectar señal:
        self.txt_buscar.textChanged.connect(
            lambda text: self.search_debouncer.debounce(self.realizar_busqueda, text)
        )

        def realizar_busqueda(self, texto):
            # Esta función solo se ejecuta 300ms después
            # de que el usuario deja de escribir
            resultados = self.buscar_en_bd(texto)
            self.mostrar_resultados(resultados)
    """

    def __init__(self, delay_ms: int = 300):
        """
        Inicializa el debouncer.

        Args:
            delay_ms: Milisegundos de espera antes de ejecutar (default: 300ms)
        """
        self.delay_ms = delay_ms
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self._pending_func = None
        self._pending_args = None
        self._pending_kwargs = None

        self.timer.timeout.connect(self._ejecutar)

    def debounce(self, func, *args, **kwargs):
        """
        Agenda la ejecución de una función con debounce.

        Si se llama de nuevo antes de que expire el timer,
        el timer se reinicia y solo se ejecuta la última llamada.

        Args:
            func: Función a ejecutar
            *args: Argumentos posicionales
            **kwargs: Argumentos con nombre
        """
        # Guardar función y argumentos pendientes
        self._pending_func = func
        self._pending_args = args
        self._pending_kwargs = kwargs

        # Reiniciar timer
        self.timer.stop()
        self.timer.start(self.delay_ms)

    def _ejecutar(self):
        """Ejecuta la función pendiente"""
        if self._pending_func:
            try:
                self._pending_func(*self._pending_args, **self._pending_kwargs)
            except (sqlite3.Error, OSError, ValueError) as e:
                logger.error(f"Error ejecutando función debounce: {e}")
            finally:
                # Limpiar
                self._pending_func = None
                self._pending_args = None
                self._pending_kwargs = None

    def cancel(self):
        """Cancela cualquier ejecución pendiente"""
        self.timer.stop()
        self._pending_func = None
        self._pending_args = None
        self._pending_kwargs = None

    def flush(self):
        """Ejecuta inmediatamente si hay algo pendiente"""
        if self.timer.isActive():
            self.timer.stop()
            self._ejecutar()


class ThrottledDebouncer:
    """
    Combina throttle y debounce.

    - Throttle: Ejecuta máximo una vez cada X ms (garantiza feedback rápido)
    - Debounce: Espera X ms después de la última llamada (para resultado final)

    Útil cuando quieres mostrar resultados parciales mientras escribes,
    pero también quieres una búsqueda final completa.
    """

    def __init__(self, throttle_ms: int = 500, debounce_ms: int = 300):
        """
        Args:
            throttle_ms: Intervalo mínimo entre ejecuciones throttled
            debounce_ms: Delay para la ejecución final
        """
        self.throttle_ms = throttle_ms
        self.debounce_ms = debounce_ms

        self.throttle_timer = QTimer()
        self.throttle_timer.setSingleShot(True)

        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)

        self._pending_func = None
        self._pending_args = None
        self._pending_kwargs = None
        self._can_throttle = True

        self.throttle_timer.timeout.connect(self._reset_throttle)
        self.debounce_timer.timeout.connect(self._ejecutar_debounce)

    def call(self, func, *args, **kwargs):
        """
        Llama a la función con throttle + debounce.

        Args:
            func: Función a ejecutar
            *args: Argumentos posicionales
            **kwargs: Argumentos con nombre
        """
        self._pending_func = func
        self._pending_args = args
        self._pending_kwargs = kwargs

        # Throttle: ejecutar inmediatamente si es posible
        if self._can_throttle:
            self._can_throttle = False
            self.throttle_timer.start(self.throttle_ms)
            self._ejecutar_throttle()

        # Debounce: siempre reiniciar el timer
        self.debounce_timer.stop()
        self.debounce_timer.start(self.debounce_ms)

    def _ejecutar_throttle(self):
        """Ejecuta con throttle (resultados parciales)"""
        if self._pending_func:
            try:
                self._pending_func(*self._pending_args, **self._pending_kwargs)
            except (sqlite3.Error, OSError, ValueError) as e:
                logger.error(f"Error en throttle: {e}")

    def _ejecutar_debounce(self):
        """Ejecuta con debounce (resultado final)"""
        if self._pending_func:
            try:
                self._pending_func(*self._pending_args, **self._pending_kwargs)
            except (sqlite3.Error, OSError, ValueError) as e:
                logger.error(f"Error en debounce: {e}")
            finally:
                self._pending_func = None
                self._pending_args = None
                self._pending_kwargs = None

    def _reset_throttle(self):
        """Permite el siguiente throttle"""
        self._can_throttle = True

    def cancel(self):
        """Cancela todas las ejecuciones pendientes"""
        self.throttle_timer.stop()
        self.debounce_timer.stop()
        self._can_throttle = True
        self._pending_func = None


def create_debounced_handler(func, delay_ms: int = 300):
    """
    Factory function para crear un handler con debounce.

    Ejemplo:
        # Crear handler
        buscar_debounced = create_debounced_handler(self.buscar_productos, 300)

        # Conectar
        self.txt_buscar.textChanged.connect(buscar_debounced)

    Args:
        func: Función a ejecutar
        delay_ms: Delay en milisegundos

    Returns:
        Callable: Handler con debounce
    """
    debouncer = Debouncer(delay_ms)

    def handler(*args, **kwargs):
        debouncer.debounce(func, *args, **kwargs)

    return handler
