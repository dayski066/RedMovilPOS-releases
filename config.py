# Configuración de la aplicación
import os
from app_paths import DB_PATH, PDF_DIR, LOGOS_DIR, APP_DATA_DIR

# Versión de la aplicación
APP_VERSION = "5.0.5"
APP_NAME = "RedMovilPOS"

# Configuración de la base de datos SQLite
# IMPORTANTE: Ahora usa carpetas externas (ProgramData) como programa instalado
# DB_PATH viene de app_paths.py

# Configuración de la empresa (valores por defecto vacíos)
# Los datos reales se cargan desde la base de datos (Ajustes > Empresa)
COMPANY_INFO = {
    'name': '',
    'nif': '',
    'address': '',
    'city': '',
    'phone': ''
}

# Configuración de IVA
IVA_RATE = 0.21  # 21%

def calcular_desglose_iva(precio_con_iva):
    """
    Extrae el IVA de un precio que YA incluye IVA.
    El usuario introduce precios finales (con IVA incluido).
    
    Args:
        precio_con_iva: Precio final introducido por el usuario
        
    Returns:
        tuple: (subtotal, iva, total)
        
    Ejemplo con IVA 21%:
        precio_con_iva = 121€
        subtotal = 100€
        iva = 21€
        total = 121€
    """
    total = precio_con_iva
    subtotal = total / (1 + IVA_RATE)
    iva = total - subtotal
    return round(subtotal, 2), round(iva, 2), round(total, 2)

# Prefijo de numeración de facturas
INVOICE_PREFIX = 'UB'

# PDF_DIR ahora viene de app_paths.py (carpeta externa en ProgramData)

# Purchase configuration
PURCHASE_PREFIX = 'COM'

# Repair order configuration
REPAIR_PREFIX = 'SAT'

# Cash categories
CASH_INCOME_CATEGORIES = [
    'Venta Mostrador',
    'Cobro Reparación',
    'Otros Ingresos'
]

CASH_EXPENSE_CATEGORIES = [
    'Compra Mercancía',
    'Gastos Operativos',
    'Servicios',
    'Impuestos',
    'Otros Gastos'
]

# Tipos de egresos detallados para gestión de caja
EXPENSE_TYPES = {
    'gastos': [
        'Alquiler Local',
        'Suministros (Luz, Agua, Gas)',
        'Teléfono e Internet',
        'Material de Oficina',
        'Limpieza y Mantenimiento',
        'Seguros',
        'Gastos Bancarios',
        'Otros Gastos'
    ],
    'retiros': [
        'Retiro Efectivo Caja',
        'Retiro para Banco'
    ],
    'pagos': [
        'Pago a Proveedores',
        'Pago Nóminas',
        'Pago Autónomos',
        'Pago Hacienda/Impuestos',
        'Otros Pagos'
    ]
}

# Tolerancia máxima permitida en diferencia de cierre de caja
# Si la diferencia excede este monto, se requiere autenticación con contraseña
CIERRE_TOLERANCIA_MAXIMA = 50.0  # Euros

# Repair statuses (value, label, color)
REPAIR_STATUSES = [
    ('pendiente', 'Pendiente', '#EBCB8B'),
    ('en_proceso', 'En Proceso', '#5E81AC'),
    ('reparado', 'Reparado', '#A3BE8C'),
    ('entregado', 'Entregado', '#7B88A0'),
    ('cancelado', 'Cancelado', '#BF616A')
]

# =============================================================================
# CONFIGURACIÓN DE SEGURIDAD
# =============================================================================

# Rate Limiting - Protección contra intentos de login
AUTH_MAX_INTENTOS_LOGIN = 5           # Máximo intentos antes de bloquear
AUTH_VENTANA_INTENTOS_MINUTOS = 15    # Ventana de tiempo para contar intentos
AUTH_BLOQUEO_CUENTA_MINUTOS = 30      # Tiempo de bloqueo tras exceder intentos
AUTH_SESION_EXPIRA_MINUTOS = 480      # 8 horas de inactividad = cierre sesión

# Requisitos de contraseña
AUTH_PASSWORD_MIN_LENGTH = 8
AUTH_PASSWORD_REQUIERE_MAYUSCULA = True
AUTH_PASSWORD_REQUIERE_NUMERO = True
AUTH_PASSWORD_REQUIERE_ESPECIAL = False  # Opcional por ahora

