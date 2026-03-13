# RedMovilPOS v4.2.0

Sistema de gestion integral para tiendas de telefonia movil y servicios de reparacion (SAT).

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15+-green.svg)
![PyQt-Fluent-Widgets](https://img.shields.io/badge/Fluent_Widgets-1.11+-5E81AC.svg)
![SQLite](https://img.shields.io/badge/SQLite-3-lightgrey.svg)
![License](https://img.shields.io/badge/License-Propietario-red.svg)

## Caracteristicas Principales

### Punto de Venta (TPV)
- Interfaz táctil optimizada para ventas rápidas
- Productos favoritos con acceso directo
- Escaneo de códigos de barras (EAN/IMEI)
- Cobro en efectivo, tarjeta, Bizum y transferencia
- Cálculo automático de cambio
- Tickets térmicos y facturas A4

### Facturacion
- Facturas con desglose de IVA (21%)
- Detección automática de clientes
- Generación de PDF profesional
- Impresión automática o guardar sin imprimir
- Historial completo con filtros avanzados

### Servicio Tecnico (SAT)
- Órdenes de reparación con código QR
- Gestión multi-dispositivo por orden
- Catálogo de averías y soluciones predefinidas
- Estados: Pendiente → En proceso → Reparado → Entregado
- Código de patrón de desbloqueo del cliente
- Cobro automático al entregar

### Gestion de Compras
- Registro de compras a particulares
- Escaneo obligatorio de DNI del vendedor
- Contrato de compra generado automáticamente
- Actualización automática de stock
- Trazabilidad completa por IMEI

### Gestion de Caja
- Apertura/cierre diario con cuadre
- Movimientos automáticos por ventas/reparaciones/compras
- Ingresos y egresos manuales
- Devoluciones con reintegro a caja
- Historial detallado por día

### Inventario
- Productos con marca, modelo, RAM, almacenamiento
- Control de stock automático
- Estados: Nuevo, KM0, Usado
- Categorías personalizables
- Gestión de marcas y modelos

### Clientes
- Base de datos de clientes
- Historial de compras y reparaciones
- Imagen de DNI adjunta
- Búsqueda por NIF/teléfono

### Seguridad y Usuarios
- Sistema de login con autenticación segura
- Roles y permisos granulares (Admin, Vendedor, Técnico)
- Contraseñas hasheadas con salt
- Confirmación con contraseña para acciones sensibles
- **Auditoria de operaciones**: registro de quien crea, modifica o elimina

### Estadisticas
- Dashboard con métricas clave
- Ventas del día/mes
- Reparaciones activas
- Stock bajo mínimo

### Multi-Establecimiento
- Gestión de múltiples tiendas
- Datos fiscales por establecimiento
- Logo personalizado en documentos

### Internacionalizacion (i18n)
- Espanol (es)
- Ingles (en)
- Portugues (pt)
- Frances (fr)

### Impresion
- Facturas A4 en PDF
- Tickets térmicos (80mm)
- Órdenes de reparación
- Contratos de compra

---

## Estructura del Proyecto

```
facturar-gemini/
├── main.py                        # Punto de entrada
├── config.py                      # Configuracion global (IVA, estados)
├── requirements.txt               # Dependencias
├── app/
│   ├── db/
│   │   └── database.py            # Conexion y migraciones SQLite
│   ├── modules/
│   │   ├── auth_manager.py        # Autenticacion y sesiones
│   │   ├── factura_manager.py     # Logica de ventas
│   │   ├── compra_manager.py      # Logica de compras
│   │   ├── reparacion_manager.py  # Logica SAT
│   │   ├── caja_manager.py        # Gestion de caja
│   │   ├── caja_tpv_manager.py    # Logica TPV
│   │   ├── devolucion_manager.py  # Devoluciones
│   │   ├── permission_manager.py  # Roles y permisos
│   │   ├── auditoria_manager.py   # Historial de operaciones
│   │   ├── pdf_generator.py       # Generacion de PDFs (paleta Nord)
│   │   └── ...
│   ├── ui/
│   │   ├── main_window.py         # Ventana principal (sidebar fluent)
│   │   ├── login_dialog.py        # Pantalla de acceso
│   │   ├── transparent_buttons.py # Estilos centralizados de botones
│   │   ├── styles.py              # Estilos globales
│   │   ├── factura_tab_mejorada.py # Nueva venta
│   │   ├── caja_tpv_tab.py        # TPV tactil
│   │   ├── reparaciones_*.py      # Modulo SAT
│   │   ├── compras_*.py           # Modulo compras
│   │   ├── configuracion_tab.py   # Ajustes del sistema
│   │   ├── operaciones_tab.py     # Historial de auditoria
│   │   └── ...
│   ├── i18n/                      # Traducciones (es, en, pt, fr)
│   └── utils/
│       ├── notify.py              # Notificaciones InfoBar centralizadas
│       ├── log_config.py          # Configuracion de logging
│       ├── qr_generator.py        # Codigos QR para SAT
│       └── printer.py             # Utilidades de impresion
├── tests/                         # 242 tests unitarios (pytest)
├── data/                          # Archivos de datos
├── assets/                        # Recursos graficos
└── migrations/                    # Scripts de migracion
```

---

## Instalacion

### Requisitos
- Python 3.8 o superior
- Windows 10/11 (probado)

### Pasos

```bash
# Clonar repositorio
git clone <repo-url>
cd facturar-gemini

# Crear entorno virtual
python -m venv venv
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
python main.py
```

### Dependencias principales
- PyQt5 - Interfaz grafica
- PyQt-Fluent-Widgets - Componentes UI modernos (sidebar, SearchLineEdit, InfoBar, FluentIcon)
- ReportLab - Generacion de PDFs
- qrcode - Codigos QR
- Pillow - Procesamiento de imagenes
- pycryptodome - Encriptacion

---

## Primer Inicio

1. La aplicación crea un usuario administrador por defecto:
   - **Usuario**: `admin`
   - **Contraseña**: `admin`

2. **¡Importante!** Cambiar la contraseña inmediatamente desde Ajustes → Usuarios

3. Configurar datos del establecimiento en Ajustes → Establecimientos

---

## Modulos del Sistema

| Módulo | Descripción |
|--------|-------------|
| **Home** | Dashboard con estadísticas |
| **Ventas** | Nueva venta + Historial |
| **Compras** | Nueva compra + Historial |
| **Caja** | TPV, Movimientos, Cierre, Devoluciones, Historial |
| **SAT** | Nueva reparación + Historial |
| **Inventario** | Productos + Categorías |
| **Clientes** | Base de datos de clientes |
| **Ajustes** | Establecimiento, Usuarios, Roles, Impresoras, Operaciones |

---

## Sistema de Auditoria

Todas las operaciones criticas quedan registradas:
- Creacion de ventas/compras/reparaciones
- Eliminacion de registros
- Cambios de estado en reparaciones
- Usuario, fecha y datos modificados

Acceso: **Ajustes -> Operaciones** (solo administradores, protegido por contrasena)

---

## Desarrollo

### Base de datos
SQLite con migraciones automaticas al iniciar. No requiere instalacion adicional.

### Temas
- Tema oscuro por defecto (paleta Nord completa)
- Tema claro disponible en Ajustes

### Logs
Sistema de logging estructurado con `logging` de Python (sin `print()`). Los errores se registran en `error.log`.

### Tests
242 tests unitarios con pytest cubriendo los modulos principales:
- `test_factura_manager.py` - Logica de ventas
- `test_compra_manager.py` - Logica de compras
- `test_producto_manager.py` - Gestion de productos
- `test_reparacion_manager.py` - Logica SAT
- `test_devolucion_manager.py` - Devoluciones
- `test_permission_manager.py` - Roles y permisos
- `test_validators.py` - Validacion de datos

```bash
python -m pytest tests -v
```

---

## Novedades v4.2.0

### UI/UX
- Sidebar fluent con NavigationInterface (estilo Windows 11)
- Notificaciones InfoBar en lugar de QMessageBox modales
- Botones transparentes con bordes Nord y iconos FluentIcon
- Campos de busqueda SearchLineEdit con lupa integrada
- Paleta de colores Nord unificada en toda la app (UI, PDFs, datos)
- Tablas con filas de altura uniforme y alineacion centrada

### Arquitectura
- Sistema de logging centralizado (`app/utils/log_config.py`)
- Notificaciones centralizadas (`app/utils/notify.py`)
- Estilos de botones centralizados (`app/ui/transparent_buttons.py`)
- Excepciones tipadas con `ValidationError` en managers
- 242 tests unitarios con pytest

### Seguridad
- Contrasenas hasheadas con PBKDF2 + salt
- Confirmacion con contrasena para acciones sensibles
- Auditoria completa de operaciones criticas
- Roles y permisos granulares

---

## Licencia

Software propietario. Requiere clave de activacion valida.

---

## Autor

Desarrollado para la gestion profesional de tiendas de telefonia.
