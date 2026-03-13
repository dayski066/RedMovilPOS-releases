"""
Utilidades para escaneo de documentos usando WIA (Windows Image Acquisition)
"""
import sqlite3  # Solo para consultas BD en obtener_escaner/config
import os
import platform
from datetime import datetime
from app.utils.logger import logger
from app.exceptions import ScannerError


def obtener_escaner_configurado(db):
    """Obtiene el nombre del escáner configurado en la BD"""
    try:
        res = db.fetch_one("SELECT valor FROM configuracion WHERE clave = 'scanner_device'")
        if res and res['valor'] and "---" not in res['valor'] and "No se detectaron" not in res['valor']:
            return res['valor']
    except sqlite3.Error:
        pass
    return None


def obtener_config_escaneo(db):
    """Obtiene la configuración de escaneo"""
    config = {
        'dpi': 200,
        'format': 'JPG',
        'color': 'Color',
        'folder': 'data/escaneos'
    }
    try:
        dpi_str = db.fetch_one("SELECT valor FROM configuracion WHERE clave = 'scanner_dpi'")
        if dpi_str and dpi_str['valor']:
            # Extraer número del string "200 DPI (Normal)"
            config['dpi'] = int(dpi_str['valor'].split()[0])
        
        fmt = db.fetch_one("SELECT valor FROM configuracion WHERE clave = 'scanner_format'")
        if fmt and fmt['valor']:
            config['format'] = fmt['valor']
            
        color = db.fetch_one("SELECT valor FROM configuracion WHERE clave = 'scanner_color'")
        if color and color['valor']:
            config['color'] = color['valor']
            
        folder = db.fetch_one("SELECT valor FROM configuracion WHERE clave = 'scanner_folder'")
        if folder and folder['valor']:
            config['folder'] = folder['valor']
    except sqlite3.Error:
        pass

    return config


def escanear_documento(scanner_name, dpi=200, color_mode='Color'):
    """
    Escanea un documento usando WIA y devuelve la ruta de la imagen.
    
    Args:
        scanner_name: Nombre del escáner WIA
        dpi: Resolución (150, 200, 300, 600)
        color_mode: 'Color', 'Escala de Grises', 'Blanco y Negro'
        
    Returns:
        str: Ruta al archivo de imagen escaneado, o None si falla
    """
    if platform.system() != 'Windows':
        raise ScannerError("El escaneo WIA solo está disponible en Windows")
    
    try:
        import win32com.client
        from PIL import Image
        import tempfile
        
        # Crear carpeta temporal
        temp_dir = os.path.join(tempfile.gettempdir(), 'redmovilpos_scans')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Conectar con WIA
        device_manager = win32com.client.Dispatch("WIA.DeviceManager")
        
        # Buscar el dispositivo por nombre
        device = None
        for i in range(1, device_manager.DeviceInfos.Count + 1):
            info = device_manager.DeviceInfos(i)
            if info.Properties("Name").Value == scanner_name:
                device = info.Connect()
                break
        
        if not device:
            raise ScannerError(f"No se encontró el escáner: {scanner_name}")
        
        # Obtener el primer item de escaneo (scanner bed)
        item = device.Items(1)
        
        # Configurar propiedades de escaneo
        # WIA Property IDs:
        # 6146 = Color Intent (1=Color, 2=Grayscale, 4=B&W)
        # 6147 = Horizontal Resolution (DPI)
        # 6148 = Vertical Resolution (DPI)
        
        try:
            # Resolución
            item.Properties("6147").Value = dpi  # Horizontal DPI
            item.Properties("6148").Value = dpi  # Vertical DPI
            
            # Modo de color
            if color_mode == 'Escala de Grises':
                item.Properties("6146").Value = 2
            elif color_mode == 'Blanco y Negro':
                item.Properties("6146").Value = 4
            else:  # Color
                item.Properties("6146").Value = 1
        except Exception as e:
            logger.warning(f"No se pudieron configurar todas las propiedades WIA: {e}")
        
        # Escanear
        image = item.Transfer()
        
        # Guardar imagen temporal
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        temp_file = os.path.join(temp_dir, f"scan_{timestamp}.bmp")
        image.SaveFile(temp_file)
        
        # Convertir a JPG para menor tamaño
        jpg_file = temp_file.replace('.bmp', '.jpg')
        img = Image.open(temp_file)
        img = img.convert('RGB')
        img.save(jpg_file, 'JPEG', quality=90)
        
        # Eliminar BMP temporal
        try:
            os.remove(temp_file)
        except OSError:
            pass
        
        return jpg_file
        
    except ImportError:
        raise ScannerError("Falta pywin32. Instala con: pip install pywin32")
    except Exception as e:
        raise ScannerError(f"Error al escanear: {str(e)}", original_error=str(e))


def listar_escaneres():
    """Lista los escáneres WIA disponibles"""
    if platform.system() != 'Windows':
        return []
    
    try:
        import win32com.client
        device_manager = win32com.client.Dispatch("WIA.DeviceManager")
        scanners = []
        for i in range(1, device_manager.DeviceInfos.Count + 1):
            device = device_manager.DeviceInfos(i)
            scanners.append(device.Properties("Name").Value)
        return scanners
    except Exception:
        return []












