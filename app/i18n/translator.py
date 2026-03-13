"""
Clase Translator para gestionar traducciones
"""
from app.db.database import Database
import importlib
import sys

# Instancia global del traductor
_translator = None


def get_translator():
    """Obtiene la instancia global del traductor"""
    global _translator
    if _translator is None:
        _translator = Translator()
    return _translator


def tr(key, **kwargs):
    """
    Función de traducción rápida.

    Uso:
        tr("Guardar")  -> "Save" (si idioma es inglés)
        tr("Hola {nombre}", nombre="Juan")  -> "Hola Juan"
    """
    return get_translator().translate(key, **kwargs)


class Translator:
    """Gestor de traducciones multi-idioma"""

    # Idiomas disponibles
    LANGUAGES = {
        'es': 'Español',
        'en': 'English',
        'fr': 'Français',
        'pt': 'Português'
    }

    def __init__(self):
        self.current_language = self._load_language_preference()
        self.translations = self._load_translations()

    def refresh_language(self):
        """Recarga el idioma desde la base de datos"""
        lang = self._load_language_preference()
        
        if lang:
            self.current_language = lang
            # Recargar traducciones para asegurar que están frescas
            self.translations = self._load_translations()
            return True
        return False

    def _load_language_preference(self):
        """Carga el idioma preferido desde la BD"""
        try:
            db = Database()
            db.connect()
            result = db.fetch_one(
                "SELECT valor FROM configuracion WHERE clave = 'idioma'"
            )
            db.disconnect()
            
            if result and result['valor'] in self.LANGUAGES:
                return result['valor']
        except Exception:
            pass
        return 'es'  # Español por defecto

    def _load_translations(self):
        """Carga los diccionarios de traducción"""
        translations = {}
        
        # Helper para recargar módulos
        def load_module(module_path):
            try:
                if module_path in sys.modules:
                    return importlib.reload(sys.modules[module_path])
                else:
                    return importlib.import_module(module_path)
            except Exception:
                return None

        # Español
        mod = load_module('app.i18n.es')
        translations['es'] = getattr(mod, 'TRANSLATIONS', {}) if mod else {}

        # English
        mod = load_module('app.i18n.en')
        translations['en'] = getattr(mod, 'TRANSLATIONS', {}) if mod else {}

        # Francés
        mod = load_module('app.i18n.fr')
        translations['fr'] = getattr(mod, 'TRANSLATIONS', {}) if mod else {}

        # Portugués
        mod = load_module('app.i18n.pt')
        translations['pt'] = getattr(mod, 'TRANSLATIONS', {}) if mod else {}

        return translations

    def set_language(self, lang_code):
        """Cambia el idioma actual y recarga las traducciones"""
        if lang_code in self.LANGUAGES:
            self.current_language = lang_code
            self.translations = self._load_translations()
            return True
        return False

    def get_language(self):
        """Obtiene el código del idioma actual"""
        return self.current_language

    def get_language_name(self):
        """Obtiene el nombre del idioma actual"""
        return self.LANGUAGES.get(self.current_language, 'Español')

    def translate(self, key, **kwargs):
        """
        Traduce una cadena al idioma actual.

        Args:
            key: Texto a traducir (en español como clave base)
            **kwargs: Variables para interpolación

        Returns:
            str: Texto traducido o la clave original si no hay traducción
        """
        # DEBUG
        # print(f"[DEBUG i18n] Translating '{key}' | Lang: {self.current_language}")
        
        # Si el idioma es español, buscar en el diccionario (fallback a la clave)
        if self.current_language == 'es':
            es_dict = self.translations.get('es', {})
            text = es_dict.get(key, key)
        else:
            # Buscar traducción en el diccionario del idioma actual
            lang_dict = self.translations.get(self.current_language, {})
            text = lang_dict.get(key, key)  # Si no existe, usar la clave (español)

        # Aplicar interpolación de variables
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError):
                pass

        # print(f"[DEBUG i18n] Result: '{text}'")
        return text

    def get_available_languages(self):
        """Devuelve lista de idiomas disponibles"""
        return list(self.LANGUAGES.items())
