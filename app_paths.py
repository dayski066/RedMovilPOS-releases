"""
Configuración de rutas para modo instalado
Todos los datos se guardan en %PROGRAMDATA%\\Facturar\\
"""
import os
import sys

# Nombre de la aplicación
APP_NAME = "Facturar"

# Obtener la ruta base para datos (ProgramData en Windows)
if sys.platform == 'win32':
    # Windows: C:\ProgramData\Facturar\
    PROGRAMDATA = os.environ.get('PROGRAMDATA', 'C:\\ProgramData')
    APP_DATA_DIR = os.path.join(PROGRAMDATA, APP_NAME)
else:
    # Linux/Mac: /var/lib/facturar o ~/facturar
    APP_DATA_DIR = f'/var/lib/{APP_NAME.lower()}'

# Crear directorio principal si no existe
os.makedirs(APP_DATA_DIR, exist_ok=True)

# Subdirectorios para datos
DATA_DIR = os.path.join(APP_DATA_DIR, 'data')
PDF_DIR = os.path.join(APP_DATA_DIR, 'data', 'pdfs')
LOGOS_DIR = os.path.join(APP_DATA_DIR, 'data', 'logos')
DB_PATH = os.path.join(DATA_DIR, 'facturacion.db')

# Crear todos los subdirectorios
for directory in [DATA_DIR, PDF_DIR, LOGOS_DIR]:
    os.makedirs(directory, exist_ok=True)

# Imprimir rutas para debug
if __name__ == '__main__':
    print(f"Directorio de datos: {APP_DATA_DIR}")
    print(f"Base de datos: {DB_PATH}")
    print(f"PDFs: {PDF_DIR}")
    print(f"Logos: {LOGOS_DIR}")
